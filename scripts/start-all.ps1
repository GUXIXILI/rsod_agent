#Requires -Version 5.1

<#
.SYNOPSIS
    Start the full RSOD Agent development environment.
.DESCRIPTION
    1. Ensure Docker Desktop is running.
    2. Stop conflicting Docker containers (backend, frontend).
    3. Start PostgreSQL, Redis and MinIO via docker compose.
    4. Wait for infrastructure ports to be ready.
    5. Launch backend uvicorn and frontend npm run dev in the background.
    6. HTTP health-check for both backend and frontend.
    7. Write backend/frontend output to log files for later inspection.
    8. Use scripts/stop-all.ps1 to shut everything down.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Remove SSLKEYLOGFILE from this process to prevent aiohttp/langchain
# from throwing PermissionError during initialization.
Remove-Item Env:\SSLKEYLOGFILE -ErrorAction SilentlyContinue

# Project root = parent of the scripts folder
$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
}
$projectRoot = Resolve-Path (Join-Path $scriptDir "..") | Select-Object -ExpandProperty Path

# ── 工具函数 ────────────────────────────────────────────────────
function Write-Step {
    param([string]$Msg)
    Write-Host ">>> $Msg" -ForegroundColor Yellow
}

function Write-Ok {
    param([string]$Msg)
    Write-Host "  [OK]  $Msg" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Msg)
    Write-Host "  [WARN] $Msg" -ForegroundColor Magenta
}

function Write-ErrorMsg {
    param([string]$Msg)
    Write-Host "  [ERR]  $Msg" -ForegroundColor Red
}

function Write-Info {
    param([string]$Msg)
    Write-Host "  [INFO] $Msg" -ForegroundColor Gray
}

function Test-DockerRunning {
    try {
        $null = cmd /c "docker info 2>&1"
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Wait-ForPort {
    <#
    .SYNOPSIS
        轮询等待指定的 TCP 端口变为可连接状态。
    .DESCRIPTION
        使用 .NET TcpClient 直接 TCP 连接探测端口，比 Test-NetConnection 快 20-40 倍
        （Test-NetConnection 会做 DNS/Ping/路由跟踪，单次 1-2s；TcpClient 仅 ~50ms），
        且不会出现 Test-NetConnection 对 localhost 的假阴性问题。
    #>
    param(
        [string]$HostName = "127.0.0.1",
        [int]$Port,
        [int]$TimeoutSeconds = 60
    )
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $asyncResult = $tcp.BeginConnect($HostName, $Port, $null, $null)
            if ($asyncResult.AsyncWaitHandle.WaitOne(500, $false)) {
                $tcp.EndConnect($asyncResult)
                $tcp.Close()
                return $true
            }
            $tcp.Close()
        }
        catch {
            # 端口未就绪，继续轮询
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Test-PortInUse {
    <#
    .SYNOPSIS
        使用 TcpClient 实际连接测试端口是否被占用。
        netstat 可能误报僵尸端口（进程已退出但 TCP 栈未释放），
        TcpClient 连接成功才说明端口真正被占用。
    #>
    param([int]$Port)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $asyncResult = $tcp.BeginConnect("127.0.0.1", $Port, $null, $null)
        if ($asyncResult.AsyncWaitHandle.WaitOne(500, $false)) {
            $tcp.EndConnect($asyncResult)
            $tcp.Close()
            return $true
        }
        $tcp.Close()
        return $false
    }
    catch {
        return $false
    }
}

function Wait-ForHttp {
    <#
    .SYNOPSIS
        轮询 HTTP 端点直到返回 200。
    #>
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 60
    )
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                return $true
            }
        }
        catch {
            # 端点未就绪，继续轮询
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Format-Elapsed {
    param([System.Diagnostics.Stopwatch]$Stopwatch)
    $elapsed = $Stopwatch.Elapsed
    if ($elapsed.TotalSeconds -lt 1) {
        return "$([math]::Round($elapsed.TotalMilliseconds))ms"
    }
    elseif ($elapsed.TotalSeconds -lt 60) {
        return "$([math]::Round($elapsed.TotalSeconds, 1))s"
    }
    else {
        return "$([math]::Floor($elapsed.TotalMinutes))m $([math]::Round($elapsed.TotalSeconds % 60))s"
    }
}

# ── 环境变量检查 ────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RSOD Agent 开发环境启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Info "Project root: $projectRoot"

# ── 步骤 1/6: 检查 Docker ────────────────────────────────────────
$stepTimer = [System.Diagnostics.Stopwatch]::StartNew()
Write-Host ""
Write-Step "步骤 1/6: 检查 Docker 是否运行..."
if (Test-DockerRunning) {
    Write-Ok "Docker 运行正常"
}
else {
    Write-Warn "Docker 未运行，尝试自动启动 Docker Desktop..."
    $dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $dockerExe)) {
        Write-ErrorMsg "Docker Desktop 未找到: $dockerExe"
        Write-Error "Docker Desktop not found at $dockerExe"
        exit 1
    }

    try {
        Start-Process -FilePath $dockerExe -NoNewWindow -ErrorAction Stop
    }
    catch {
        Write-ErrorMsg "无法自动启动 Docker Desktop（可能需要管理员权限）"
        Write-ErrorMsg "请手动启动 Docker Desktop 后重新运行此脚本"
        exit 1
    }

    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        if (Test-DockerRunning) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) {
        Write-ErrorMsg "Docker Desktop 在 60 秒内未就绪"
        exit 1
    }
    Write-Ok "Docker Desktop 已就绪"
}
Write-Info "步骤 1 完成，耗时: $(Format-Elapsed $stepTimer)"

# ── 步骤 2/6: 停止冲突容器 + 启动基础设施 ───────────────────────
$stepTimer = [System.Diagnostics.Stopwatch]::StartNew()
Write-Host ""
Write-Step "步骤 2/6: 停止可能冲突的 Docker 容器..."

Push-Location $projectRoot
try {
    # SubTask 1.1: 先停止可能冲突的 backend/frontend 容器
    $stopResult = cmd /c "docker compose stop backend frontend 2>&1"
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "已停止冲突容器 (backend, frontend)"
    }
    else {
        Write-Info "无需停止冲突容器（可能未运行）"
    }

    Write-Info "正在启动 Docker 基础设施 (postgres, redis, minio)..."
    cmd /c "docker compose up -d postgres redis minio 2>&1"
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Docker 基础设施启动失败"
        Pop-Location
        exit 1
    }
    Write-Ok "Docker 基础设施已启动"
}
finally {
    Pop-Location
}
Write-Info "步骤 2 完成，耗时: $(Format-Elapsed $stepTimer)"

# ── 步骤 3/6: 等待基础设施端口就绪 ──────────────────────────────
$stepTimer = [System.Diagnostics.Stopwatch]::StartNew()
Write-Host ""
Write-Step "步骤 3/6: 等待基础设施就绪..."
$services = @(
    @{ Name = "PostgreSQL"; Port = 5433 },
    @{ Name = "Redis";      Port = 6379 },
    @{ Name = "MinIO";      Port = 9000 }
)
$allReady = $true
foreach ($svc in $services) {
    Write-Host "  等待 $($svc.Name) (端口 $($svc.Port))..." -NoNewline
    $ok = Wait-ForPort -Port $svc.Port -TimeoutSeconds 60
    if ($ok) {
        Write-Host " 就绪" -ForegroundColor Green
    }
    else {
        Write-Host " 超时" -ForegroundColor Red
        Write-ErrorMsg "$($svc.Name) 端口 $($svc.Port) 未在 60 秒内就绪"
        $allReady = $false
    }
}
if (-not $allReady) {
    Write-ErrorMsg "部分基础设施未就绪，请检查 Docker 容器日志"
    exit 1
}
Write-Ok "所有基础设施已就绪"
Write-Info "步骤 3 完成，耗时: $(Format-Elapsed $stepTimer)"

# ── 步骤 4/6: 启动后端 ───────────────────────────────────────────
$stepTimer = [System.Diagnostics.Stopwatch]::StartNew()
Write-Host ""
Write-Step "步骤 4/6: 启动后端 (uvicorn, 热重载)..."

# 端口 8000 占用时先尝试释放（Docker 容器 + 本地进程）
if (Test-PortInUse -Port 8000) {
    Write-Warn "端口 8000 已被占用，尝试释放..."

    # 1) 尝试停止 Docker backend 容器
    Push-Location $projectRoot
    try {
        cmd /c "docker compose stop backend 2>&1" | Out-Null
        Write-Info "已执行 docker compose stop backend"
    }
    finally {
        Pop-Location
    }
    Start-Sleep -Seconds 2

    # 2) 如果 Docker 停止后仍被占用，查找并杀掉占用端口的本地进程
    if (Test-PortInUse -Port 8000) {
        $lines = netstat -ano | Select-String ":8000\s"
        $killed = $false
        foreach ($line in $lines) {
            $parts = $line.Line -split "\s+" | Where-Object { $_ -ne "" }
            if ($parts.Length -ge 5) {
                $localAddr = $parts[1]
                $state = $parts[3]
                $procId = $parts[4]
                if ($localAddr -match ":8000$" -and $state -eq "LISTENING" -and $procId -match "^\d+$") {
                    $procId = [int]$procId
                    try {
                        $proc = Get-Process -Id $procId -ErrorAction Stop
                        Write-Warn "发现本地进程占用端口 8000: $($proc.ProcessName) (PID $procId)，正在终止..."
                        Stop-Process -Id $procId -Force -ErrorAction Stop
                        Write-Ok "已终止进程 PID $procId"
                        Start-Sleep -Seconds 1
                        $killed = $true
                    }
                    catch {
                        # 进程不存在（僵尸端口），无法 kill，但端口可能已被 OS 回收
                        Write-Warn "端口 8000 被僵尸进程 PID $procId 占用（进程已不存在），尝试继续启动..."
                    }
                }
            }
        }
        if ($killed) {
            if (-not (Test-PortInUse -Port 8000)) {
                Write-Ok "端口 8000 已释放"
            }
        }
    }
    else {
        Write-Ok "端口 8000 已释放"
    }
}

# 验证 Python 和 uvicorn 可用
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-ErrorMsg "系统 'python' 命令未找到，请确保 Python 已安装并在 PATH 中"
    exit 1
}
try {
    $null = & python -c "import uvicorn" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "uvicorn import failed" }
}
catch {
    Write-ErrorMsg "uvicorn 模块未安装，请执行: python -m pip install uvicorn"
    exit 1
}

$backendDir = Join-Path $projectRoot "backend"
$backendLogDir = Join-Path $backendDir "logs"
if (-not (Test-Path $backendLogDir)) {
    New-Item -ItemType Directory -Path $backendLogDir -Force | Out-Null
}
$backendOutLog = Join-Path $backendLogDir "startup_backend.log"
$backendErrLog = Join-Path $backendLogDir "startup_backend_err.log"

# 静默后台启动（不弹窗），日志写入文件
$backendCommand = "Set-Location '$backendDir'; python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"
$backendProc = Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand
) -WindowStyle Hidden -RedirectStandardOutput $backendOutLog -RedirectStandardError $backendErrLog -PassThru

Write-Ok "后端进程已启动 (PID: $($backendProc.Id))"
Write-Info "后端日志: $backendOutLog"

# 等待端口就绪
Write-Host "  等待后端端口 8000..." -NoNewline
$backendReady = Wait-ForPort -Port 8000 -TimeoutSeconds 60
if ($backendReady) {
    Write-Host " 就绪" -ForegroundColor Green
}
else {
    Write-Host " 超时" -ForegroundColor Red
    Write-ErrorMsg "后端端口 8000 未在 60 秒内就绪，请检查日志: $backendOutLog"
    Write-Info "步骤 4 未完全就绪，耗时: $(Format-Elapsed $stepTimer)"
    # 继续执行，不退出 —— 进程已启动，可能只是启动较慢
}

# SubTask 1.3: HTTP 健康检查（独立于端口检查，即使端口检测超时也尝试）
Write-Host "  执行后端 HTTP 健康检查 (http://localhost:8000/docs)..." -NoNewline
$httpOk = Wait-ForHttp -Url "http://localhost:8000/docs" -TimeoutSeconds 120
if ($httpOk) {
    Write-Host " 通过" -ForegroundColor Green
    Write-Ok "后端 HTTP 健康检查通过"
}
else {
    Write-Host " 超时" -ForegroundColor Red
    Write-Warn "后端 HTTP 健康检查超时，但进程已启动，请检查日志: $backendOutLog"
}
Write-Info "步骤 4 完成，耗时: $(Format-Elapsed $stepTimer)"

# ── 步骤 5/6: 检查 npm + 前端依赖 ───────────────────────────────
$stepTimer = [System.Diagnostics.Stopwatch]::StartNew()
Write-Host ""
Write-Step "步骤 5/6: 检查前端环境..."

# 检查 npm
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCmd) {
    Write-ErrorMsg "npm 命令未找到，请安装 Node.js: https://nodejs.org/"
    exit 1
}
Write-Ok "npm 可用 (版本: $(npm --version 2>&1))"

# SubTask 1.4: 检查 node_modules
$frontendDir = Join-Path $projectRoot "frontend"
if (-not (Test-Path (Join-Path $frontendDir "package.json"))) {
    Write-ErrorMsg "前端 package.json 未找到: $frontendDir"
    exit 1
}

$nodeModulesDir = Join-Path $frontendDir "node_modules"
if (-not (Test-Path $nodeModulesDir)) {
    Write-Warn "node_modules 目录不存在，正在安装前端依赖..."
    Write-Info "执行: npm install (目录: $frontendDir)"
    Push-Location $frontendDir
    try {
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-ErrorMsg "npm install 失败"
            Pop-Location
            exit 1
        }
        Write-Ok "前端依赖安装完成"
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Ok "前端依赖已存在 (node_modules)"
}

# ── 步骤 6/6: 启动前端 ───────────────────────────────────────────
Write-Host ""
Write-Step "步骤 6/6: 启动前端 (Vite, 热重载)..."

# SubTask 1.2 类似逻辑：端口 5173 占用处理
if (Test-PortInUse -Port 5173) {
    Write-Warn "端口 5173 已被占用，尝试停止 Docker frontend 容器..."
    Push-Location $projectRoot
    try {
        cmd /c "docker compose stop frontend 2>&1" | Out-Null
        Write-Info "已执行 docker compose stop frontend"
    }
    finally {
        Pop-Location
    }

    Start-Sleep -Seconds 2
    if (Test-PortInUse -Port 5173) {
        Write-Warn "端口 5173 仍被占用，但将继续尝试启动前端"
    }
    else {
        Write-Ok "端口 5173 已释放"
    }
}

$frontendLogDir = Join-Path $frontendDir "logs"
if (-not (Test-Path $frontendLogDir)) {
    New-Item -ItemType Directory -Path $frontendLogDir -Force | Out-Null
}
$frontendOutLog = Join-Path $frontendLogDir "startup_frontend.log"
$frontendErrLog = Join-Path $frontendLogDir "startup_frontend_err.log"

# 静默后台启动（不弹窗），日志写入文件
$frontendCommand = "Set-Location '$frontendDir'; npm run dev"
$frontendProc = Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand
) -WindowStyle Hidden -RedirectStandardOutput $frontendOutLog -RedirectStandardError $frontendErrLog -PassThru

Write-Ok "前端进程已启动 (PID: $($frontendProc.Id))"
Write-Info "前端日志: $frontendOutLog"

# 等待端口就绪
Write-Host "  等待前端端口 5173..." -NoNewline
$frontendReady = Wait-ForPort -Port 5173 -TimeoutSeconds 60
if ($frontendReady) {
    Write-Host " 就绪" -ForegroundColor Green
}
else {
    Write-Host " 超时" -ForegroundColor Red
    Write-Warn "前端端口 5173 未在 60 秒内就绪，请检查日志: $frontendOutLog"
}

# SubTask 1.5: HTTP 健康检查
if ($frontendReady) {
    Write-Host "  执行前端 HTTP 健康检查 (http://localhost:5173)..." -NoNewline
    $httpOk = Wait-ForHttp -Url "http://localhost:5173" -TimeoutSeconds 30
    if ($httpOk) {
        Write-Host " 通过" -ForegroundColor Green
        Write-Ok "前端 HTTP 健康检查通过"
    }
    else {
        Write-Host " 超时" -ForegroundColor Red
        Write-Warn "前端 HTTP 健康检查超时（30 秒），但进程已启动，请检查日志: $frontendOutLog"
    }
}
Write-Info "步骤 6 完成，耗时: $(Format-Elapsed $stepTimer)"

# ── 完成 ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  开发环境启动完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  前端:  http://localhost:5173" -ForegroundColor Cyan
Write-Host "  后端:  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  MinIO: http://localhost:9001" -ForegroundColor Cyan
Write-Host ""
Write-Host "  日志文件:" -ForegroundColor Cyan
Write-Host "    后端 stdout:  $backendOutLog" -ForegroundColor Gray
Write-Host "    后端 stderr:  $backendErrLog" -ForegroundColor Gray
Write-Host "    前端 stdout:  $frontendOutLog" -ForegroundColor Gray
Write-Host "    前端 stderr:  $frontendErrLog" -ForegroundColor Gray
Write-Host ""
Write-Host "  停止开发环境: 运行 scripts/stop-all.ps1" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
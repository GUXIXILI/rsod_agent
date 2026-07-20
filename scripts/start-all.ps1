#Requires -Version 5.1

<#
.SYNOPSIS
    Start the full RSOD Agent development environment.
.DESCRIPTION
    1. Ensure Docker Desktop is running.
    2. Start PostgreSQL, Redis and MinIO via docker compose.
    3. Wait for infrastructure ports to be ready.
    4. Launch backend uvicorn and frontend npm run dev in the background.
    5. Write backend/frontend output to log files for later inspection.
    6. Use scripts/stop-all.ps1 to shut everything down.
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

function Test-DockerRunning {
    try {
        $null = docker info 2>&1
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
        使用 PowerShell 内置的 Test-NetConnection 探测端口，避免直接操作 .NET Socket
        在不同 PowerShell 版本下的兼容性问题和偶发卡死。
    #>
    param(
        [string]$HostName = "127.0.0.1",
        [int]$Port,
        [int]$TimeoutSeconds = 60
    )
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        try {
            $result = Test-NetConnection -ComputerName $HostName -Port $Port -WarningAction SilentlyContinue
            if ($result.TcpTestSucceeded) {
                return $true
            }
        }
        catch {
            # 端口未就绪，继续轮询
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

Write-Host "Project root: $projectRoot" -ForegroundColor Cyan

# 1. Docker Desktop
Write-Host "`n[1/5] Checking Docker Desktop..." -ForegroundColor Cyan
if (Test-DockerRunning) {
    Write-Host "Docker Desktop is running." -ForegroundColor Green
}
else {
    Write-Host "Docker Desktop is not running, trying to start..." -ForegroundColor Yellow
    $dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $dockerExe)) {
        Write-Error "Docker Desktop not found at $dockerExe"
        exit 1
    }

    try {
        Start-Process -FilePath $dockerExe -NoNewWindow -ErrorAction Stop
    }
    catch {
        Write-Warning "Unable to start Docker Desktop automatically (may require admin rights)."
        Write-Warning "Please start Docker Desktop manually and run this script again."
        exit 1
    }

    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        if (Test-DockerRunning) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) {
        Write-Error "Docker Desktop did not become ready within 60 seconds."
        exit 1
    }
    Write-Host "Docker Desktop is ready." -ForegroundColor Green
}

# 2. Infrastructure (only PostgreSQL, Redis, MinIO; backend/frontend run locally)
Write-Host "`n[2/5] Starting Docker Compose infrastructure..." -ForegroundColor Cyan
Push-Location $projectRoot
try {
    docker compose up -d postgres redis minio
    if ($LASTEXITCODE -ne 0) { throw "docker compose up -d postgres redis minio failed" }
    Write-Host "Docker Compose infrastructure started." -ForegroundColor Green
}
finally {
    Pop-Location
}

# 3. Wait for ports
Write-Host "`n[3/5] Waiting for infrastructure ports..." -ForegroundColor Cyan
$services = @(
    @{ Name = "PostgreSQL"; Port = 5433 },
    @{ Name = "Redis";      Port = 6379 },
    @{ Name = "MinIO";      Port = 9000 }
)
foreach ($svc in $services) {
    Write-Host "  Waiting for $($svc.Name) port $($svc.Port)..." -NoNewline
    $ok = Wait-ForPort -Port $svc.Port -TimeoutSeconds 60
    if ($ok) {
        Write-Host " ready" -ForegroundColor Green
    }
    else {
        Write-Host " timeout" -ForegroundColor Red
        Write-Error "$($svc.Name) port $($svc.Port) did not become ready within 60 seconds."
        exit 1
    }
}

# 4. Backend
Write-Host "`n[4/5] Starting backend service..." -ForegroundColor Cyan
$backendDir = Join-Path $projectRoot "backend"

# Verify system Python and uvicorn are available
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "System 'python' command not found. Please ensure Python is installed and on PATH."
    exit 1
}
try {
    $null = & python -c "import uvicorn" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "uvicorn import failed" }
}
catch {
    Write-Error "The 'uvicorn' module is not installed for the system Python. Install it with: python -m pip install uvicorn"
    exit 1
}

$backendLogDir = Join-Path $backendDir "logs"
if (-not (Test-Path $backendLogDir)) {
    New-Item -ItemType Directory -Path $backendLogDir -Force | Out-Null
}
$backendOutLog = Join-Path $backendLogDir "startup_backend.log"
$backendErrLog = Join-Path $backendLogDir "startup_backend_err.log"

# Silent background version (default): run in a hidden window and redirect output to log file.
$backendCommand = "Set-Location '$backendDir'; python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"
Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand
) -WindowStyle Hidden -RedirectStandardOutput $backendOutLog -RedirectStandardError $backendErrLog

# Popup window version (kept for reference):
# $backendCommand = "Set-Location '$backendDir'; python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"
# Start-Process -FilePath "powershell.exe" -ArgumentList @(
#     "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand
# ) -WindowStyle Normal

Write-Host "  Waiting for backend port 8000..." -NoNewline
$backendReady = Wait-ForPort -Port 8000 -TimeoutSeconds 60
if ($backendReady) {
    Write-Host " ready" -ForegroundColor Green
}
else {
    Write-Host " still starting" -ForegroundColor Yellow
}

# 5. Frontend
Write-Host "`n[5/5] Starting frontend dev server..." -ForegroundColor Cyan
$frontendDir = Join-Path $projectRoot "frontend"
if (-not (Test-Path (Join-Path $frontendDir "package.json"))) {
    Write-Error "Frontend package.json not found: $frontendDir"
    exit 1
}

$frontendLogDir = Join-Path $frontendDir "logs"
if (-not (Test-Path $frontendLogDir)) {
    New-Item -ItemType Directory -Path $frontendLogDir -Force | Out-Null
}
$frontendOutLog = Join-Path $frontendLogDir "startup_frontend.log"
$frontendErrLog = Join-Path $frontendLogDir "startup_frontend.err.log"

# Silent background version (default): run in a hidden window and redirect output to log file.
$frontendCommand = "Set-Location '$frontendDir'; npm run dev"
Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand
) -WindowStyle Hidden -RedirectStandardOutput $frontendOutLog -RedirectStandardError $frontendErrLog

# Popup window version (kept for reference):
# $frontendCommand = "Set-Location '$frontendDir'; npm run dev"
# Start-Process -FilePath "powershell.exe" -ArgumentList @(
#     "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand
# ) -WindowStyle Normal

Write-Host "  Waiting for frontend port 5173..." -NoNewline
$frontendReady = Wait-ForPort -Port 5173 -TimeoutSeconds 60
if ($frontendReady) {
    Write-Host " ready" -ForegroundColor Green
}
else {
    Write-Host " still starting" -ForegroundColor Yellow
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "RSOD Agent started successfully" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173/" -ForegroundColor Green
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "`nLog files:" -ForegroundColor Cyan
Write-Host "  Backend stdout:  $backendOutLog" -ForegroundColor Gray
Write-Host "  Backend stderr:  $backendErrLog" -ForegroundColor Gray
Write-Host "  Frontend stdout: $frontendOutLog" -ForegroundColor Gray
Write-Host "  Frontend stderr: $frontendErrLog" -ForegroundColor Gray
Write-Host "`nTip: Run scripts/stop-all.ps1 to stop all services." -ForegroundColor Yellow

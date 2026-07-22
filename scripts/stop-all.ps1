#Requires -Version 5.1

<#
.SYNOPSIS
    Stop the full RSOD Agent development environment.
.DESCRIPTION
    1. Find and stop the frontend dev-server process by port 5173.
    2. Find and stop the backend uvicorn process by port 8000.
    3. Clean up any remaining uvicorn / python and node / vite processes.
    4. Run docker compose stop + docker compose down to stop all infrastructure services.
    5. Does not require administrator privileges.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# Project root = parent of the scripts folder
$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
}
$projectRoot = Resolve-Path (Join-Path $scriptDir "..") | Select-Object -ExpandProperty Path

$script:stoppedBackendPids = @()
$script:localProcessCount = 0
$script:dockerContainerCount = 0

function Get-ProcessIdByPort {
    param([int]$Port)
    $lines = netstat -ano | Select-String ":$Port\s"
    foreach ($line in $lines) {
        $parts = $line.Line -split "\s+" | Where-Object { $_ -ne "" }
        if ($parts.Length -ge 5) {
            $localAddr = $parts[1]
            $state = $parts[3]
            $procId = $parts[4]
            if ($localAddr -match ":$Port$" -and $state -eq "LISTENING" -and $procId -match "^\d+$") {
                $procName = (Get-Process -Id ([int]$procId) -ErrorAction SilentlyContinue).ProcessName
                return [PSCustomObject]@{
                    ProcessId   = [int]$procId
                    ProcessName = $procName
                }
            }
        }
    }
    return $null
}

function Stop-ProcessByPort {
    param(
        [int]$Port,
        [string]$ServiceName
    )
    Write-Host "`nStopping $ServiceName (port $Port)..." -ForegroundColor Cyan

    $stoppedAny = $false
    for ($i = 1; $i -le 3; $i++) {
        $processInfo = Get-ProcessIdByPort -Port $Port
        if (-not $processInfo) {
            if ($i -eq 1) {
                Write-Host "  $ServiceName is not running (no process on port $Port)" -ForegroundColor DarkGray
            }
            else {
                Write-Host "  $ServiceName has stopped (port $Port released)" -ForegroundColor Green
            }
            return $stoppedAny
        }

        $procName = $processInfo.ProcessName
        if ($procName -eq 'com.docker.backend' -or $procName -eq 'wslrelay' -or $procName -like 'docker*') {
            Write-Host "  Port $Port is managed by Docker (process: $procName), skipping" -ForegroundColor DarkGray
            return $stoppedAny
        }

        $procId = $processInfo.ProcessId
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if (-not $proc) {
            Write-Host "  Process already exited" -ForegroundColor DarkGray
            continue
        }
        try {
            Write-Host "  Stopping $($proc.ProcessName) (PID $procId)..." -NoNewline
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Write-Host " stopped" -ForegroundColor Green
            $script:stoppedBackendPids += $procId
            $script:localProcessCount++
            $stoppedAny = $true
        }
        catch {
            Write-Host " failed: $_" -ForegroundColor Red
        }

        Start-Sleep -Milliseconds 500
    }

    return $stoppedAny
}

function Stop-UvicornProcesses {
    Write-Host "`nCleaning up uvicorn / python processes..." -ForegroundColor Cyan

    $stoppedAny = $false
    for ($i = 1; $i -le 3; $i++) {
        $found = $false
        $pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
        foreach ($proc in $pythonProcesses) {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)").CommandLine
            if (($cmdLine -match "uvicorn main:app" -or $cmdLine -match " main:app") -and $cmdLine -notmatch "docker") {
                if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
                    continue
                }
                Write-Host "  Stopping uvicorn python process (PID $($proc.Id))..." -NoNewline
                Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                Write-Host " stopped" -ForegroundColor Green
                $script:stoppedBackendPids += $proc.Id
                $script:localProcessCount++
                $found = $true
                $stoppedAny = $true
            }
        }

        if (-not $found) {
            if ($i -eq 1) {
                Write-Host "  No uvicorn processes found" -ForegroundColor DarkGray
            }
            else {
                Write-Host "  All uvicorn processes cleaned up" -ForegroundColor Green
            }
            return $stoppedAny
        }

        Start-Sleep -Milliseconds 500
    }

    return $stoppedAny
}

function Stop-OrphanUvicornChildren {
    Write-Host "`nCleaning up uvicorn multiprocessing orphan children..." -ForegroundColor Cyan

    $orphans = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq 'python.exe' -and
        $_.CommandLine -match 'multiprocessing-fork' -and
        $script:stoppedBackendPids -contains $_.ParentProcessId
    }

    if (-not $orphans) {
        Write-Host "  No orphan uvicorn children found" -ForegroundColor DarkGray
        return
    }

    $count = 0
    foreach ($orphan in $orphans) {
        $orphanId = $orphan.ProcessId
        if (-not (Get-Process -Id $orphanId -ErrorAction SilentlyContinue)) {
            continue
        }
        try {
            Write-Host "  Stopping orphan multiprocessing child (PID $orphanId)..." -NoNewline
            Stop-Process -Id $orphanId -Force -ErrorAction Stop
            Write-Host " stopped" -ForegroundColor Green
            $script:localProcessCount++
            $count++
        }
        catch {
            Write-Host " failed or already exited: $_" -ForegroundColor Red
        }
    }

    if ($count -gt 0) {
        Write-Host "  Cleaned up $count orphan children" -ForegroundColor Green
    }
}

function Stop-NodeProcesses {
    Write-Host "`nCleaning up node / vite processes..." -ForegroundColor Cyan

    $frontendPath = Join-Path $projectRoot "frontend"

    $stoppedAny = $false
    for ($i = 1; $i -le 3; $i++) {
        $found = $false
        $nodeProcesses = Get-Process node -ErrorAction SilentlyContinue
        foreach ($proc in $nodeProcesses) {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)").CommandLine
            if ($cmdLine -match "vite" -or $cmdLine -match [regex]::Escape($frontendPath)) {
                if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
                    continue
                }
                Write-Host "  Stopping frontend node process (PID $($proc.Id))..." -NoNewline
                Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                Write-Host " stopped" -ForegroundColor Green
                $script:localProcessCount++
                $found = $true
                $stoppedAny = $true
            }
        }

        if (-not $found) {
            if ($i -eq 1) {
                Write-Host "  No frontend node processes found" -ForegroundColor DarkGray
            }
            else {
                Write-Host "  All frontend node processes cleaned up" -ForegroundColor Green
            }
            return $stoppedAny
        }

        Start-Sleep -Milliseconds 500
    }

    return $stoppedAny
}

$stopped = @()

# 1. Frontend
if (Stop-ProcessByPort -Port 5173 -ServiceName "frontend dev-server") {
    $stopped += "frontend dev-server (port 5173)"
}

# 2. Backend
if (Stop-ProcessByPort -Port 8000 -ServiceName "backend uvicorn") {
    $stopped += "backend uvicorn (port 8000)"
}

# 3. Clean up any remaining uvicorn / python processes
if (Stop-UvicornProcesses) {
    $stopped += "uvicorn / python fallback cleanup"
}

Stop-OrphanUvicornChildren

# 4. Clean up any remaining node / vite processes
if (Stop-NodeProcesses) {
    $stopped += "node / vite fallback cleanup"
}

# 5. Docker Compose: stop all containers first, then remove them
Write-Host "`nStopping Docker Compose infrastructure..." -ForegroundColor Cyan
Push-Location $projectRoot
try {
    Write-Host "  Stopping all Docker Compose containers..." -ForegroundColor Gray
    $stopOutput = cmd /c "docker compose stop 2>&1"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  docker compose stop: no running containers or already stopped" -ForegroundColor DarkGray
    }
    else {
        $stopLines = ($stopOutput | Out-String).Trim() -split "`n" | Where-Object { $_ -match "Stopping|stopped" }
        $script:dockerContainerCount = $stopLines.Count
        if ($script:dockerContainerCount -gt 0) {
            Write-Host "  Stopped $($script:dockerContainerCount) container(s)" -ForegroundColor Green
        }
    }

    Write-Host "  Removing Docker Compose containers..." -ForegroundColor Gray
    $downOutput = cmd /c "docker compose down 2>&1"
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose down failed"
    }
    $stopped += "Docker Compose infrastructure"
    Write-Host "  Docker Compose infrastructure stopped and removed" -ForegroundColor Green
}
catch {
    Write-Host "  Docker Compose stop/down encountered an issue: $_" -ForegroundColor Yellow
}
finally {
    Pop-Location
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  RSOD Agent 已停止" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

$totalLocal = $script:localProcessCount
$totalDocker = $script:dockerContainerCount

if ($stopped.Count -gt 0) {
    Write-Host "已停止的服务:" -ForegroundColor White
    foreach ($svc in $stopped) {
        Write-Host "  - $svc" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "汇总:" -ForegroundColor White
$localColor = @("DarkGray", "Yellow")[$totalLocal -gt 0]
$dockerColor = @("DarkGray", "Yellow")[$totalDocker -gt 0]
Write-Host "  本地进程: $totalLocal 个" -ForegroundColor $localColor
Write-Host "  Docker 容器: $totalDocker 个" -ForegroundColor $dockerColor

if ($totalLocal -eq 0 -and $totalDocker -eq 0) {
    Write-Host "`n所有服务均已处于停止状态，无需操作。" -ForegroundColor DarkGray
}
else {
    Write-Host "`n开发环境已完全停止。" -ForegroundColor Green
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
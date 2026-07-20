#Requires -Version 5.1

<#
.SYNOPSIS
    Stop the full RSOD Agent development environment.
.DESCRIPTION
    1. Find and stop the frontend dev-server process by port 5173.
    2. Find and stop the backend uvicorn process by port 8000.
    3. Clean up any remaining uvicorn / python and node / vite processes.
    4. Run docker compose down to stop all infrastructure services.
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

function Get-ProcessIdByPort {
    param([int]$Port)
    # Use netstat to get the PID for a listening port; no admin rights needed.
    $lines = netstat -ano | Select-String ":$Port\s"
    foreach ($line in $lines) {
        $parts = $line.Line -split "\s+" | Where-Object { $_ -ne "" }
        if ($parts.Length -ge 5) {
            $localAddr = $parts[1]
            $state = $parts[3]
            $procId = $parts[4]
            if ($localAddr -match ":$Port$" -and $state -eq "LISTENING" -and $procId -match "^\d+$") {
                return [int]$procId
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
        $procId = Get-ProcessIdByPort -Port $Port
        if (-not $procId) {
            if ($i -eq 1) {
                Write-Host "  No process found on port $Port" -ForegroundColor Yellow
            }
            else {
                Write-Host "  Port $Port is no longer in use" -ForegroundColor Green
            }
            return $stoppedAny
        }

        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if (-not $proc) {
            Write-Host " process already exited" -ForegroundColor Yellow
            continue
        }
        try {
            Write-Host "  Found $($proc.ProcessName) (PID $procId), stopping..." -NoNewline
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Write-Host " stopped" -ForegroundColor Green
            $script:stoppedBackendPids += $procId
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
            if ($cmdLine -match "uvicorn main:app" -or $cmdLine -match " main:app") {
                if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
                    continue
                }
                Write-Host "  Found uvicorn python process (PID $($proc.Id)), stopping..." -NoNewline
                Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                Write-Host " stopped" -ForegroundColor Green
                $script:stoppedBackendPids += $proc.Id
                $found = $true
                $stoppedAny = $true
            }
        }

        if (-not $found) {
            if ($i -eq 1) {
                Write-Host "  No uvicorn processes found" -ForegroundColor Yellow
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
        Write-Host "  No orphan uvicorn children found" -ForegroundColor Yellow
        return
    }

    foreach ($orphan in $orphans) {
        $orphanId = $orphan.ProcessId
        if (-not (Get-Process -Id $orphanId -ErrorAction SilentlyContinue)) {
            continue
        }
        try {
            Write-Host "  Found orphan multiprocessing child (PID $orphanId), stopping..." -NoNewline
            Stop-Process -Id $orphanId -Force -ErrorAction Stop
            Write-Host " stopped" -ForegroundColor Green
        }
        catch {
            Write-Host " failed or already exited: $_" -ForegroundColor Red
        }
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
                Write-Host "  Found frontend node process (PID $($proc.Id)), stopping..." -NoNewline
                Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                Write-Host " stopped" -ForegroundColor Green
                $found = $true
                $stoppedAny = $true
            }
        }

        if (-not $found) {
            if ($i -eq 1) {
                Write-Host "  No frontend node processes found" -ForegroundColor Yellow
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

# 5. Docker Compose (stop all services defined in docker-compose.yml)
Write-Host "`nStopping Docker Compose infrastructure..." -ForegroundColor Cyan
Push-Location $projectRoot
try {
    docker compose down
    if ($LASTEXITCODE -ne 0) { throw "docker compose down failed" }
    $stopped += "Docker Compose infrastructure"
    Write-Host "Docker Compose infrastructure stopped." -ForegroundColor Green
}
finally {
    Pop-Location
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "RSOD Agent stopped" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
if ($stopped.Count -gt 0) {
    Write-Host "Stopped services:" -ForegroundColor Green
    foreach ($svc in $stopped) {
        Write-Host "  - $svc" -ForegroundColor Green
    }
}
else {
    Write-Host "No running services were found." -ForegroundColor Yellow
}

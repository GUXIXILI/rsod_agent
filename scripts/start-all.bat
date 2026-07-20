@echo off
chcp 65001 >nul 2>&1

REM Start the full RSOD Agent development environment.
REM This batch file is a wrapper for start-all.ps1.

setlocal
set "SCRIPT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%start-all.ps1" %*
endlocal

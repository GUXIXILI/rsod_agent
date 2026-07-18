@echo off
chcp 65001 >nul 2>&1

REM Stop the full RSOD Agent development environment.
REM This batch file is a wrapper for stop-all.ps1.

setlocal
set "SCRIPT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%stop-all.ps1" %*
endlocal

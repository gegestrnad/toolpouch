@echo off
REM IP Config Viewer - Shows Windows network configuration
REM Demonstrates: .bat tool with dropdown parameter, cmd.exe runtime,
REM and the stdout protocol ([OK]/[WARN]/[ERROR] + PROGRESS:N).
setlocal enabledelayedexpansion

echo PROGRESS:10
echo [OK] Gathering network information...

set "COMPONENT=%~1"
if "%COMPONENT%"=="--component" set "COMPONENT=%~2"

echo PROGRESS:30
echo.

if /i "%COMPONENT%"=="all" (
    echo [OK] === Full IP Configuration ===
    echo.
    ipconfig /all
) else if /i "%COMPONENT%"=="ipconfig" (
    echo [OK] === Basic IP Configuration ===
    echo.
    ipconfig
) else if /i "%COMPONENT%"=="dns" (
    echo [OK] === DNS Cache ===
    echo.
    ipconfig /displaydns
) else if /i "%COMPONENT%"=="adapter" (
    echo [OK] === Network Adapters ===
    echo.
    netsh interface show interface
) else (
    echo [WARN] Unknown component: %COMPONENT%
    echo [OK] Showing full config instead.
    echo.
    ipconfig /all
)

echo.
echo PROGRESS:100
echo [OK] Network information gathered successfully.
endlocal
exit /b 0

@echo off
REM ==========================================================================
REM Tool Pouch v3 — Force-embed icon using rcedit
REM ==========================================================================
REM
REM PURPOSE:
REM   PyInstaller's --icon flag can silently fail to embed the icon in
REM   the exe, especially with Python 3.14 (PyInstaller 6.x doesn't
REM   fully support 3.14 yet). This script uses rcedit.exe (the same
REM   tool PyInstaller uses internally) to FORCE-embed the icon into
REM   the exe after PyInstaller finishes.
REM
REM This is the nuclear option — it always works because it directly
REM   modifies the exe's PE resource section, bypassing PyInstaller's
REM   icon-copying logic entirely.
REM
REM PREREQ:
REM   - rcedit.exe on PATH, OR
REM   - Download from https://github.com/electron/rcedit/releases
REM     and place next to this script or in PATH
REM
REM USAGE:
REM   force_icon.bat
REM   force_icon.bat "D:\custom\path\ToolPouch.exe"
REM ==========================================================================

setlocal enabledelayedexpansion

set "EXE_PATH=%~1"
if "%EXE_PATH%"=="" set "EXE_PATH=%~dp0dist\ToolPouch\ToolPouch.exe"
set "ICO_PATH=%~dp0assets\icon.ico"

echo ============================================
echo  Tool Pouch — Force Icon Embed
echo ============================================
echo.
echo Exe: %EXE_PATH%
echo Ico: %ICO_PATH%
echo.

if not exist "%EXE_PATH%" (
    echo [ERROR] Exe not found: %EXE_PATH%
    echo         Run build.bat first.
    pause
    exit /b 1
)

if not exist "%ICO_PATH%" (
    echo [ERROR] Icon not found: %ICO_PATH%
    pause
    exit /b 1
)

REM Find rcedit.exe
set "RCEDIT=rcedit.exe"
where rcedit.exe >nul 2>nul
if errorlevel 1 (
    REM Check common locations
    if exist "%~dp0rcedit.exe" (
        set "RCEDIT=%~dp0rcedit.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\rcedit\rcedit.exe" (
        set "RCEDIT=%LOCALAPPDATA%\Programs\rcedit\rcedit.exe"
    ) else (
        echo [ERROR] rcedit.exe not found on PATH or next to this script.
        echo.
        echo To install rcedit:
        echo   1. Download from https://github.com/electron/rcedit/releases
        echo      (get rcedit-x64.exe for 64-bit Windows)
        echo   2. Rename it to rcedit.exe
        echo   3. Place it next to force_icon.bat, OR add it to PATH
        echo.
        echo Alternatively, install via npm:  npm install -g rcedit
        echo Or via chocolatey:  choco install rcedit
        pause
        exit /b 1
    )
)

echo Using rcedit: %RCEDIT%
echo.

echo Force-embedding icon...
"%RCEDIT%" "%EXE_PATH%" --set-icon "%ICO_PATH%"
if errorlevel 1 (
    echo [ERROR] rcedit failed to embed icon.
    pause
    exit /b 1
)

echo.
echo [OK] Icon force-embedded into exe.
echo.
echo Verifying...
powershell -NoProfile -Command "Add-Type -AssemblyName System.Drawing; $ico = [System.Drawing.Icon]::ExtractAssociatedIcon('%EXE_PATH%'); if ($ico -ne $null -and $ico.Width -ge 32) { Write-Host '  [OK] Icon verified: ' $ico.Width 'x' $ico.Height -ForegroundColor Green; $ico.Dispose() } else { Write-Host '  [WARNING] Icon verification failed' -ForegroundColor Yellow }"

echo.
echo ============================================
echo  Done! Icon force-embedded.
echo ============================================
echo.
echo If Explorer still shows the old icon:
echo   1. Run clear_icon_cache.bat as Administrator
echo   2. Restart your computer
echo   3. OR copy ToolPouch.exe to a new filename
echo.
pause
exit /b 0

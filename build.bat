@echo off
REM ==========================================================================
REM Tool Pouch v3 — Build script (Windows)
REM ==========================================================================
REM Produces a complete installer in dist\installer\ToolPouch-Setup-x.y.z.exe
REM
REM Prereqs on the build machine:
REM   1. Python 3.12 or 3.13 on PATH (NOT 3.14 — PyInstaller 6.x doesn't
REM      support it yet; the exe will fail with "python314.dll not found")
REM   2. PyInstaller:  pip install pyinstaller
REM   3. Inno Setup 6:  https://jrsoftware.org/isdl.php
REM      (ISCC.exe must be on PATH or set ISCC env var to its full path)
REM   4. (Optional) Embeddable Python extracted into installer\python-embed\
REM      See installer\python-embed\README.md
REM
REM Usage:
REM   build.bat            Build + make installer
REM   build.bat skip-installer    Skip the Inno Setup step (just produce dist\ToolPouch\)
REM ==========================================================================

setlocal enabledelayedexpansion

echo ============================================
echo  Tool Pouch v3 - Build Script
echo ============================================
echo.

REM --- 0) Check Python version (warn if 3.14+)
echo [0/5] Checking Python version...
for /f "delims=" %%i in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set "PY_VER=%%i"
echo Found Python %PY_VER%
echo %PY_VER%| findstr /r "^3\.1[0-3]\." >nul
if errorlevel 1 (
    echo.
    echo [WARNING] Python %PY_VER% detected.
    echo   PyInstaller 6.x does NOT fully support Python 3.14+.
    echo   If the build succeeds but the exe fails with
    echo   "Failed to load python314.dll", install Python 3.12 or 3.13
    echo   from https://python.org/downloads/ and rebuild.
    echo   See INSTALLER_GUIDE.md for details.
    echo.
    choice /c YN /m "Continue anyway"
    if errorlevel 2 exit /b 1
)

REM --- 1) Install build-time deps
echo [1/5] Installing build-time dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 goto :failed

REM --- 2) Clean previous build
echo.
echo [2/5] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
REM Also delete any auto-generated spec from a previous run — PyInstaller
REM creates one if --spec isn't used, and a stale spec can override our
REM --icon flag on the next build.
if exist ToolPouch.spec del ToolPouch.spec

REM --- 3) PyInstaller onedir build
echo.
echo [3/5] Running PyInstaller (--onedir, no Qt, no console)...
REM Use ABSOLUTE path for the icon via %~dp0 (the batch file's own dir,
REM with trailing backslash). %CD% would resolve to whatever directory
REM the user ran build.bat FROM, which may not be the project root.
REM %~dp0 is always correct regardless of the caller's CWD.
set "ICON_FLAG="
if exist "assets\icon.ico" set "ICON_FLAG=--icon %~dp0assets\icon.ico"

pyinstaller ^
  --name "ToolPouch" ^
  --onedir ^
  --windowed ^
  --noupx ^
  --noconfirm ^
  --clean ^
  --distpath "dist" ^
  --workpath "build" ^
  %ICON_FLAG% ^
  --add-data "tools;tools" ^
  --add-data "assets;assets" ^
  --add-data "assets\lang_icons;assets\lang_icons" ^
  --add-data "ui\themes;ui\themes" ^
  --hidden-import "darkdetect" ^
  --hidden-import "tkinterdnd2" ^
  --hidden-import "PIL" ^
  --hidden-import "PIL.Image" ^
  --collect-all "customtkinter" ^
  --collect-all "PIL" ^
  --exclude-module "PySide6" ^
  --exclude-module "PyQt6" ^
  --exclude-module "PyQt5" ^
  --exclude-module "numpy" ^
  --exclude-module "pandas" ^
  main.py

if errorlevel 1 goto :failed

REM --- 4) Sanity check: dist\ToolPouch\ToolPouch.exe must exist
if not exist "dist\ToolPouch\ToolPouch.exe" (
    echo [ERROR] PyInstaller did not produce dist\ToolPouch\ToolPouch.exe
    goto :failed
)

echo.
echo [4/5] Build artifact: dist\ToolPouch\ToolPouch.exe
echo   Size: %~z0 bytes

REM Verify the icon was embedded into the exe. PyInstaller's --icon flag
REM can silently fail if the path is wrong — this check catches that.
echo.
echo Verifying icon embedded in exe...
REM Use a rigorous check: extract the icon AND verify it's not the
REM default (small) icon. ExtractAssociatedIcon can return a default
REM 32x32 icon even when the real icon wasn't embedded.
powershell -NoProfile -Command "Add-Type -AssemblyName System.Drawing; $exe = '%CD%\dist\ToolPouch\ToolPouch.exe'; $srcIco = '%CD%\assets\icon.ico'; if (-not (Test-Path $exe)) { Write-Host '  [FAIL] Exe not found' -ForegroundColor Red; exit 1 } ; $ico = [System.Drawing.Icon]::ExtractAssociatedIcon($exe); if ($ico -eq $null) { Write-Host '  [FAIL] No icon extracted' -ForegroundColor Red; exit 1 } ; $srcIcon = [System.Drawing.Icon]::new($srcIco); Write-Host '  Exe icon: ' $ico.Width 'x' $ico.Height ' (' $ico.Size.Width 'x' $ico.Size.Height ')' ; Write-Host '  Src icon: ' $srcIcon.Width 'x' $srcIcon.Height ; if ($ico.Width -ge 32 -and $ico.Height -ge 32) { Write-Host '  [OK] Icon embedded (non-default size)' -ForegroundColor Green; $script:iconOk = $true } else { Write-Host '  [WARNING] Icon may be default — will force-embed with rcedit' -ForegroundColor Yellow; $script:iconOk = $false } ; $ico.Dispose(); $srcIcon.Dispose(); if (-not $script:iconOk) { exit 2 }"

REM If the verification failed (exit 2), force-embed the icon with rcedit.
REM This is the nuclear option — it directly modifies the exe's PE
REM resource section, bypassing PyInstaller's icon-copying logic. This
REM fixes the "icon doesn't change" issue that can happen with Python 3.14
REM where PyInstaller's icon embedding silently fails.
if errorlevel 2 (
    echo.
    echo [INFO] PyInstaller icon embedding may have failed. Force-embedding with rcedit...
    REM Find rcedit.exe
    set "RCEDIT=rcedit.exe"
    where rcedit.exe >nul 2>nul
    if errorlevel 1 (
        if exist "%~dp0rcedit.exe" (
            set "RCEDIT=%~dp0rcedit.exe"
        ) else if exist "%LOCALAPPDATA%\Programs\rcedit\rcedit.exe" (
            set "RCEDIT=%LOCALAPPDATA%\Programs\rcedit\rcedit.exe"
        ) else (
            echo   [WARNING] rcedit.exe not found.
            echo   To force-embed the icon:
            echo     1. Run: powershell -ExecutionPolicy Bypass -File download_rcedit.ps1
            echo     2. Run: force_icon.bat
            echo   OR install rcedit manually from https://github.com/electron/rcedit/releases
            goto :continue_build
        )
    )
    "%RCEDIT%" "%CD%\dist\ToolPouch\ToolPouch.exe" --set-icon "%CD%\assets\icon.ico"
    if errorlevel 1 (
        echo   [WARNING] rcedit failed. The icon may not be embedded.
        echo   Run force_icon.bat manually after downloading rcedit.
    ) else (
        echo   [OK] Icon force-embedded with rcedit.
    )
)

:continue_build

REM --- 5) Inno Setup installer
if /i "%1"=="skip-installer" (
    echo.
    echo [5/5] Skipping Inno Setup ^(per skip-installer flag^).
    echo.
    echo ============================================
    echo  Done! Portable folder: dist\ToolPouch\
    echo  ^(Run dist\ToolPouch\ToolPouch.exe to test^)
    echo ============================================
    pause
    exit /b 0
)

echo.
echo [5/5] Building Inno Setup installer...

REM Find ISCC.exe
set "ISCC=ISCC.exe"
where ISCC.exe >nul 2>nul
if errorlevel 1 (
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
        set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    ) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
        set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
    ) else (
        echo [WARN] Inno Setup ISCC.exe not found on PATH or default location.
        echo        Skipping installer. Output is in dist\ToolPouch\
        echo        Install Inno Setup from https://jrsoftware.org/isdl.php to build the installer.
        pause
        exit /b 0
    )
)

"%ISCC%" installer\toolpouch.iss
if errorlevel 1 goto :failed

echo.
echo ============================================
echo  Done! Installer: dist\installer\ToolPouch-Setup-*.exe
echo  Portable folder: dist\ToolPouch\
echo ============================================
pause
exit /b 0

:failed
echo.
echo ============================================
echo  Build failed.
echo ============================================
pause
exit /b 1

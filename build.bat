@echo off
setlocal
echo ============================================
echo  Tool Pouch -- Build Script
echo ============================================
echo.

REM Install build-time dependencies for PyInstaller and local validation.
pip install -r requirements.txt

echo.
echo Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist ToolPouch.spec del ToolPouch.spec

echo.
echo Locating Python runtime to bundle...
for /f "delims=" %%i in ('python -c "import sys; print(sys.executable)"') do set "PYTHON_EXE=%%i"
for /f "delims=" %%i in ('python -c "import sys; print(sys.base_prefix)"') do set "PYTHON_HOME=%%i"
echo Found Python: %PYTHON_EXE%
echo Python home: %PYTHON_HOME%

echo.
echo Building executable...
echo.

set ICON_FLAG=
if exist "assets\icon.ico" set ICON_FLAG=--icon "assets\icon.ico"

pyinstaller ^
  --name "ToolPouch" ^
  --onedir ^
  --windowed ^
  --noupx ^
  %ICON_FLAG% ^
  --add-data "tools;tools" ^
  --add-data "assets;assets" ^
  --hidden-import "PySide6.QtSvg" ^
  --hidden-import "PySide6.QtXml" ^
  --collect-all "deep_translator" ^
  --noconfirm ^
  main.py

if errorlevel 1 goto :failed

echo.
echo Creating portable Python runtime...
set "APP_DIR=dist\ToolPouch"
set "RUNTIME_DIR=%APP_DIR%\runtime"
set "SITE_PACKAGES=%RUNTIME_DIR%\Lib\site-packages"

echo Copying editable tools and assets into portable folder...
robocopy "tools" "%APP_DIR%\tools" /E /XD __pycache__ /XF *.pyc >nul
if errorlevel 8 goto :failed

if exist "assets" (
  robocopy "assets" "%APP_DIR%\assets" /E /XD __pycache__ /XF *.pyc >nul
  if errorlevel 8 goto :failed
)

if exist "%RUNTIME_DIR%" rmdir /s /q "%RUNTIME_DIR%"
mkdir "%RUNTIME_DIR%"
mkdir "%SITE_PACKAGES%"

copy /y "%PYTHON_EXE%" "%RUNTIME_DIR%\python.exe" >nul
copy /y "%PYTHON_HOME%\python*.dll" "%RUNTIME_DIR%\" >nul
copy /y "%PYTHON_HOME%\vcruntime*.dll" "%RUNTIME_DIR%\" >nul 2>nul

if exist "%PYTHON_HOME%\DLLs" (
  robocopy "%PYTHON_HOME%\DLLs" "%RUNTIME_DIR%\DLLs" /E /XF *.pyc >nul
  if errorlevel 8 goto :failed
)

robocopy "%PYTHON_HOME%\Lib" "%RUNTIME_DIR%\Lib" /E /XD __pycache__ site-packages test tests tkinter idlelib ensurepip /XF *.pyc >nul
if errorlevel 8 goto :failed

echo Installing included tool dependencies into portable runtime...
python -m pip install ^
  --upgrade ^
  --target "%SITE_PACKAGES%" ^
  --no-cache-dir ^
  requests ^
  beautifulsoup4 ^
  reportlab ^
  deep-translator

if errorlevel 1 goto :failed

echo.
echo ============================================
echo  Done! Output in: dist\ToolPouch\
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

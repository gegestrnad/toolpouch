@echo off
echo ============================================
echo  Tool Pouch -- Build Script
echo ============================================
echo.

REM Install dependencies
pip install -r requirements.txt

echo.
echo Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist ToolPouch.spec del ToolPouch.spec

echo.
echo Locating Python executable to bundle...
for /f "delims=" %%i in ('where python') do set PYTHON_EXE=%%i & goto :found_python
:found_python
echo Found Python: %PYTHON_EXE%

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
  --add-binary "%PYTHON_EXE%;_internal" ^
  --hidden-import "PySide6.QtSvg" ^
  --hidden-import "PySide6.QtXml" ^
  --collect-all "deep_translator" ^
  --noconfirm ^
  main.py

echo.
echo ============================================
echo  Done! Output in: dist\ToolPouch\
echo ============================================
pause

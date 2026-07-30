@echo off
REM ==========================================================================
REM Tool Pouch v3 — Nuclear Windows Icon Cache Clear
REM ==========================================================================
REM
REM PURPOSE:
REM   Windows Explorer caches .exe icons VERY aggressively. Even after
REM   rebuilding an exe with a new icon, Explorer may still show the OLD
REM   icon from its cache. ``ie4uinit.exe -show`` is a soft refresh that
REM   often isn't enough.
REM
REM This script does the NUCLEAR option:
REM   1. Kills explorer.exe (your taskbar will disappear — that's normal)
REM   2. Deletes ALL icon cache files (IconCache.db + the Explorer
REM      iconcache_*.db files)
REM   3. Restarts explorer.exe (taskbar comes back)
REM   4. The icon cache is rebuilt from scratch on next access
REM
REM After running this, navigate to your ToolPouch.exe in Explorer —
REM it will show the correct embedded icon.
REM
REM NOTE: This does NOT delete any user data. It only clears the
REM Windows icon cache, which is safe to delete — Windows rebuilds it
REM automatically.
REM
REM USAGE:
REM   1. Close Tool Pouch if it's running
REM   2. Run this script as Administrator (right-click → Run as admin)
REM   3. Your screen will flash — that's explorer.exe restarting
REM   4. Navigate to your ToolPouch.exe — the icon should now be correct
REM ==========================================================================

echo ============================================
echo  Tool Pouch — Icon Cache Clear
echo ============================================
echo.
echo This will restart Windows Explorer (your taskbar will disappear briefly).
echo Save your work in other apps before continuing.
echo.
pause

echo.
echo [1/4] Stopping Explorer...
taskkill /f /im explorer.exe
timeout /t 1 /nobreak >nul

echo [2/4] Deleting IconCache.db...
if exist "%LOCALAPPDATA%\IconCache.db" (
    attrib -h -s -r "%LOCALAPPDATA%\IconCache.db"
    del /f /q "%LOCALAPPDATA%\IconCache.db"
    echo   Deleted IconCache.db
) else (
    echo   IconCache.db not found (already cleared)
)

echo [3/4] Deleting Explorer iconcache files...
set "DELETED=0"
for %%f in ("%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*.db") do (
    attrib -h -s -r "%%f"
    del /f /q "%%f"
    set /a DELETED+=1
)
if %DELETED% gtr 0 (
    echo   Deleted %DELETED% iconcache files
) else (
    echo   No iconcache files found (already cleared)
)

echo [4/4] Restarting Explorer...
start explorer.exe

echo.
echo ============================================
echo  Done! Icon cache cleared.
echo ============================================
echo.
echo Now navigate to your ToolPouch.exe in Explorer.
echo The correct icon should appear immediately.
echo.
echo If it STILL shows the wrong icon:
echo   1. Restart your computer (some icons are cached in memory)
echo   2. Copy ToolPouch.exe to a NEW filename (e.g. ToolPouch2.exe)
echo      — this forces Explorer to read the icon fresh
echo   3. Check if the icon is actually embedded:
echo      Right-click ToolPouch.exe → Properties
echo      The icon should appear in the top-left of the Properties dialog
echo      If it does, the icon IS embedded — it's purely a cache issue
echo      If it doesn't, PyInstaller failed to embed it (rebuild needed)
echo.
pause

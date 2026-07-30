@echo off
REM Environment Inspector - Lists environment variables, optionally filtered.
REM Demonstrates: .bat tool with a text parameter (substring filter),
REM and batch string manipulation with delayed expansion.
setlocal enabledelayedexpansion

echo PROGRESS:10
echo [OK] Inspecting environment variables...

REM The --filter value is the 2nd argument (after --filter itself)
set "FILTER="
:parse
if "%~1"=="" goto run
if /i "%~1"=="--filter" (
    set "FILTER=%~2"
    shift
    shift
    goto parse
)
shift
goto parse

:run
echo PROGRESS:30

if "!FILTER!"=="" (
    echo [OK] Showing ALL environment variables ^(no filter^)
    echo.
    set
) else (
    echo [OK] Filtering for: "!FILTER!"
    echo.
    set "FOUND=0"
    for /f "usebackq tokens=1,* delims==" %%a in (`set`) do (
        set "VARNAME=%%a"
        set "VARVAL=%%b"
        REM Case-insensitive substring check using findstr
        echo !VARNAME! | findstr /i "!FILTER!" >nul
        if !errorlevel! equ 0 (
            echo !VARNAME!=!VARVAL!
            set /a FOUND+=1
        )
    )
    echo.
    if !FOUND! equ 0 (
        echo [WARN] No environment variables matching "!FILTER!"
    ) else (
        echo [OK] Found !FOUND! matching variable^(s^).
    )
)

echo.
echo PROGRESS:100
echo [OK] Environment inspection complete.
endlocal
exit /b 0

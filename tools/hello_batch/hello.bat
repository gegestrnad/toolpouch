@echo off
REM Hello-world test tool for the Batch runtime.
REM Spec §6 Phase 6 checkpoint: test arg-with-spaces passing.
REM
REM Args arrive as --path VALUE (two separate argv items). We loop to find them.
REM This is robust against the host passing the script path with spaces.
REM
REM NOTE: We use ``setlocal enabledelayedexpansion`` and ``!VAR!`` syntax
REM (instead of ``%VAR%``) inside blocks so that variables set inside an
REM ``if (...)`` block are visible immediately. Without delayed expansion,
REM ``%VAR%`` inside a block expands to the value at PARSE time (empty),
REM not at RUNTIME (the value just set).

setlocal enabledelayedexpansion

set "PATH_ARG="

:parse
if "%~1"=="" goto run
if /i "%~1"=="--path" (
    set "PATH_ARG=%~2"
    shift
    shift
    goto parse
)
shift
goto parse

:run
echo PROGRESS:0
echo [OK] Hello from Batch
echo [OK] path_arg:   !PATH_ARG!
echo PROGRESS:50

REM Check for spaces using string substitution (robust against backslashes).
REM findstr chokes on backslashes in paths like D:\New folder because it
REM treats \N as escape sequences. String substitution doesn't have that issue.
set "STRIPPED=!PATH_ARG: =!"
if not "!STRIPPED!"=="!PATH_ARG!" (
    echo [OK] Path contains spaces - preserved correctly.
) else (
    echo [WARN] Path has no spaces - try a path with spaces to really test.
)

echo PROGRESS:100
echo [OK] Done.
endlocal
exit /b 0

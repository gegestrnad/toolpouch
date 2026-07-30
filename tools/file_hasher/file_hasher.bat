@echo off
REM File Hasher - Calculate MD5 and SHA256 hashes of a file
setlocal enabledelayedexpansion

echo PROGRESS:10
echo [OK] Starting file hash calculation

set "FILE=%~1"

if "%FILE%"=="" (
    echo [ERROR] No file specified
    exit /b 1
)

if not exist "%FILE%" (
    echo [ERROR] File not found: %FILE%
    exit /b 1
)

echo PROGRESS:30
echo File: %FILE%

REM Get file size
for %%A in ("%FILE%") do set "SIZE=%%~zA"
echo Size: %SIZE% bytes

echo PROGRESS:50
echo [OK] Calculating MD5...

REM Calculate MD5 using certutil
certutil -hashfile "%FILE%" MD5 2>nul | findstr /v "hash" | findstr /v "certutil"

echo.
echo PROGRESS:70
echo [OK] Calculating SHA256...

REM Calculate SHA256 using certutil
certutil -hashfile "%FILE%" SHA256 2>nul | findstr /v "hash" | findstr /v "certutil"

echo.
echo PROGRESS:90
echo [OK] Calculating SHA1...

REM Calculate SHA1 using certutil
certutil -hashfile "%FILE%" SHA1 2>nul | findstr /v "hash" | findstr /v "certutil"

echo.
echo PROGRESS:100
echo [OK] Hash calculation complete

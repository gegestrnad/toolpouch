# ==========================================================================
# Tool Pouch v3 — Download rcedit.exe (for force_icon.bat)
# ==========================================================================
#
# Downloads rcedit-x64.exe from the official Electron GitHub release,
# renames it to rcedit.exe, and places it next to this script so that
# force_icon.bat can find it.
#
# USAGE:
#   powershell -ExecutionPolicy Bypass -File download_rcedit.ps1
# ==========================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Tool Pouch — Download rcedit.exe" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$destDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$destPath = Join-Path $destDir "rcedit.exe"

if (Test-Path $destPath) {
    Write-Host "rcedit.exe already exists at: $destPath" -ForegroundColor Green
    $response = Read-Host "Re-download? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Keeping existing rcedit.exe."
        exit 0
    }
}

# rcedit is published by the Electron project. The latest release is
# on GitHub. We download rcedit-x64.exe (64-bit Windows).
$url = "https://github.com/electron/rcedit/releases/download/v2.0.0/rcedit-x64.exe"

Write-Host "Downloading from: $url"
Write-Host "Saving to:        $destPath"
Write-Host ""

try {
    # Use TLS 1.2 for GitHub downloads
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    $ProgressPreference = 'SilentlyContinue'  # speed up download
    Invoke-WebRequest -Uri $url -OutFile $destPath -UseBasicParsing
    $ProgressPreference = 'Continue'

    $fileInfo = Get-Item $destPath
    Write-Host "[OK] Downloaded rcedit.exe ($($fileInfo.Length) bytes)" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now run:  force_icon.bat" -ForegroundColor White
    Write-Host ""
} catch {
    Write-Host "[ERROR] Download failed: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual download:" -ForegroundColor Yellow
    Write-Host "  1. Go to https://github.com/electron/rcedit/releases"
    Write-Host "  2. Download rcedit-x64.exe"
    Write-Host "  3. Rename it to rcedit.exe"
    Write-Host "  4. Place it in: $destDir"
    Write-Host ""
    exit 1
}

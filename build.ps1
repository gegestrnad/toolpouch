# ==========================================================================
# Tool Pouch v3 — Build script (PowerShell, optional alternative to build.bat)
# ==========================================================================
# Same outcome as build.bat: produces dist\installer\ToolPouch-Setup-*.exe
#
# Usage from PowerShell:
#     .\build.ps1
#     .\build.ps1 -SkipInstaller
#
# Why a PowerShell version when build.bat exists? PowerShell has cleaner
# error handling and is easier to call from CI (Azure Pipelines / GH Actions
# windows-latest runners). The .bat version remains the primary path for
# developers who want a one-click build from Explorer.
# ==========================================================================

[CmdletBinding()]
param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Step($n, $msg) {
    Write-Host ""
    Write-Host "[$n/5] $msg" -ForegroundColor Cyan
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Tool Pouch v3 - Build Script (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# --- 1) Install build-time deps
Step 1 "Installing build-time dependencies..."
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

# --- 2) Clean previous build
Step 2 "Cleaning previous build..."
foreach ($dir in @("build", "dist")) {
    if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
}

# --- 3) PyInstaller onedir build
Step 3 "Running PyInstaller (--onedir, no Qt, no console)..."
$iconFlag = @()
if (Test-Path "assets\icon.ico") { $iconFlag = @("--icon", "assets\icon.ico") }

pyinstaller `
    --name "ToolPouch" `
    --onedir `
    --windowed `
    --noupx `
    --noconfirm `
    --clean `
    --distpath "dist" `
    --workpath "build" `
    --add-data "tools;tools" `
    --add-data "assets;assets" `
    --add-data "ui\themes;ui\themes" `
    --hidden-import "darkdetect" `
    --hidden-import "tkinterdnd2" `
    --hidden-import "PIL" `
    --hidden-import "PIL.Image" `
    --collect-all "customtkinter" `
    --collect-all "PIL" `
    --exclude-module "PySide6" `
    --exclude-module "PyQt6" `
    --exclude-module "PyQt5" `
    --exclude-module "numpy" `
    --exclude-module "pandas" `
    @iconFlag `
    main.py

if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

if (-not (Test-Path "dist\ToolPouch\ToolPouch.exe")) {
    throw "PyInstaller did not produce dist\ToolPouch\ToolPouch.exe"
}

$size = (Get-Item "dist\ToolPouch\ToolPouch.exe").Length
Step 4 "Build artifact: dist\ToolPouch\ToolPouch.exe ($size bytes)"

# --- 5) Inno Setup installer
if ($SkipInstaller) {
    Write-Host ""
    Write-Host "[5/5] Skipping Inno Setup (per -SkipInstaller flag)." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host " Done! Portable folder: dist\ToolPouch\" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    exit 0
}

Step 5 "Building Inno Setup installer..."

$isccCandidates = @(
    "ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)
$iscc = $null
foreach ($cand in $isccCandidates) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) {
        $iscc = (Get-Command $cand).Source
        break
    }
    if (Test-Path $cand) {
        $iscc = $cand
        break
    }
}

if (-not $iscc) {
    Write-Host "[WARN] Inno Setup ISCC.exe not found." -ForegroundColor Yellow
    Write-Host "       Skipping installer. Output is in dist\ToolPouch\" -ForegroundColor Yellow
    Write-Host "       Install Inno Setup from https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    exit 0
}

& $iscc "installer\toolpouch.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " Done!" -ForegroundColor Green
Write-Host " Installer:   dist\installer\ToolPouch-Setup-*.exe" -ForegroundColor Green
Write-Host " Portable:    dist\ToolPouch\" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

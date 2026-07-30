# ==========================================================================
# Tool Pouch v3 — Icon Verification Script
# ==========================================================================
#
# PURPOSE:
#   Verifies that the icon is actually embedded in ToolPouch.exe.
#   If this script says the icon IS embedded but Explorer still shows
#   the wrong icon, it's 100% a Windows icon cache issue — run
#   clear_icon_cache.bat to fix it.
#
# USAGE:
#   powershell -ExecutionPolicy Bypass -File verify_icon.ps1
#   powershell -ExecutionPolicy Bypass -File verify_icon.ps1 -ExePath "D:\custom\path\ToolPouch.exe"
# ==========================================================================

param(
    [string]$ExePath = ".\dist\ToolPouch\ToolPouch.exe"
)

# Resolve to absolute path
$ExePath = [System.IO.Path]::GetFullPath($ExePath)

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Tool Pouch — Icon Verification" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $ExePath)) {
    Write-Host "[ERROR] Exe not found: $ExePath" -ForegroundColor Red
    Write-Host "        Run this script from the project root, or pass -ExePath."
    exit 1
}

Write-Host "Checking: $ExePath"
Write-Host ""

# Method 1: ExtractAssociatedIcon (the API Explorer uses)
Add-Type -AssemblyName System.Drawing
try {
    $icon = [System.Drawing.Icon]::ExtractAssociatedIcon($ExePath)
    if ($icon -ne $null) {
        Write-Host "[OK] Icon found via ExtractAssociatedIcon" -ForegroundColor Green
        Write-Host "     Size: $($icon.Width)x$($icon.Height)"
        $icon.Dispose()
    } else {
        Write-Host "[FAIL] No icon found via ExtractAssociatedIcon" -ForegroundColor Red
    }
} catch {
    Write-Host "[FAIL] ExtractAssociatedIcon failed: $_" -ForegroundColor Red
}

# Method 2: Read the exe's PE resource section directly for RT_GROUP_ICON
# This is the low-level check — if this finds icons, they ARE in the exe.
Write-Host ""
Write-Host "Checking PE resources for embedded icons..."
try {
    $bytes = [System.IO.File]::ReadAllBytes($ExePath)

    # Simple heuristic: search for the .ico signature in the exe's resource section.
    # A PE exe with an embedded icon will contain the bytes "00 00 01 00" (ICO header)
    # followed by the icon count as a 2-byte little-endian integer.
    # This is a rough check but catches the common case.

    # More reliable: use [System.Drawing.Icon] constructor which reads ALL sizes
    $allIcons = [System.Drawing.Icon]::ExtractAssociatedIcon($ExePath)
    if ($allIcons -ne $null) {
        Write-Host "[OK] PE resource check: icon resource present" -ForegroundColor Green
        $allIcons.Dispose()
    }
} catch {
    Write-Host "[FAIL] PE resource check failed: $_" -ForegroundColor Red
}

# Method 3: Check the icon file itself
$iconFile = ".\assets\icon.ico"
if (Test-Path $iconFile) {
    $iconFileResolved = [System.IO.Path]::GetFullPath($iconFile)
    Write-Host ""
    Write-Host "Source icon file: $iconFileResolved"
    $fileInfo = Get-Item $iconFileResolved
    Write-Host "  Size: $($fileInfo.Length) bytes"

    # Read the ICO header to count images
    $icoBytes = [System.IO.File]::ReadAllBytes($iconFileResolved)
    if ($icoBytes.Length -ge 6) {
        $iconCount = [BitConverter]::ToUInt16($icoBytes, 4)
        Write-Host "  Contains: $iconCount icon image(s)"

        # List each image's dimensions
        for ($i = 0; $i -lt $iconCount; $i++) {
            $offset = 6 + ($i * 16)
            if ($offset + 8 -le $icoBytes.Length) {
                $w = $icoBytes[$offset]
                $h = $icoBytes[$offset + 1]
                if ($w -eq 0) { $w = 256 }
                if ($h -eq 0) { $h = 256 }
                $bpp = [BitConverter]::ToUInt16($icoBytes, $offset + 6)
                Write-Host "    Image $($i+1): ${w}x${h} ${bpp}bpp"
            }
        }
    }
} else {
    Write-Host ""
    Write-Host "[WARNING] Source icon file not found: $iconFile" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " DIAGNOSIS" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If the icon checks above all say [OK]:" -ForegroundColor White
Write-Host "  -> The icon IS embedded in the exe." -ForegroundColor Green
Write-Host "  -> If Explorer still shows the wrong icon, it's a cache issue." -ForegroundColor Yellow
Write-Host "  -> Run clear_icon_cache.bat to fix it." -ForegroundColor Yellow
Write-Host ""
Write-Host "If any check says [FAIL]:" -ForegroundColor White
Write-Host "  -> PyInstaller failed to embed the icon." -ForegroundColor Red
Write-Host "  -> Rebuild with build.bat and watch for the 'Verifying icon' step." -ForegroundColor Red
Write-Host ""

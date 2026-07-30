# Hello-world test tool for the PowerShell runtime.
# Spec §6 Phase 6 checkpoint: test arg-with-spaces passing.

param(
    [Parameter(Mandatory=$true)]
    [string]$Path
)

Write-Output "PROGRESS:0"
Write-Output "[OK] Hello from PowerShell $($PSVersionTable.PSVersion.ToString())"
Write-Output "[OK] path_arg:   $Path"
Write-Output "PROGRESS:50"

if ($Path -match ' ') {
    Write-Output "[OK] Path contains spaces - preserved correctly."
} else {
    Write-Output "[WARN] Path has no spaces - try a path with spaces to really test."
}

Write-Output "PROGRESS:100"
Write-Output "[OK] Done."

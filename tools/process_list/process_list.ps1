# Process List - Lists running Windows processes sorted by memory/CPU/name.
# Demonstrates: .ps1 tool with text + dropdown parameters, PowerShell runtime,
# and the stdout protocol ([OK]/[WARN]/[ERROR] + PROGRESS:N).

param(
    [string]$Count = "20",
    [string]$SortBy = "memory"
)

Write-Output "PROGRESS:10"
Write-Output "[OK] Gathering process list..."

# Parse count — default to 20 if not a valid number
$n = 20
if ([int]::TryParse($Count, [ref]$n)) {
    if ($n -lt 1) { $n = 20 }
    if ($n -gt 500) { $n = 500 }
} else {
    Write-Output "[WARN] Invalid count '$Count', using 20"
    $n = 20
}

Write-Output "PROGRESS:30"
Write-Output "[OK] Showing top $n processes sorted by $SortBy"
Write-Output ""

$processes = Get-Process

Write-Output "PROGRESS:60"

switch ($SortBy) {
    "memory" {
        $sorted = $processes | Sort-Object WorkingSet64 -Descending | Select-Object -First $n
        $format = "{0,-35} {1,12:N0} MB  PID:{2,8}"
        Write-Output ("{0,-35} {1,12}  {2}" -f "Process Name", "Memory (MB)", "PID")
        Write-Output ("{0,-35} {1,12}  {2}" -f "------------", "-----------", "---")
        foreach ($p in $sorted) {
            $memMB = [math]::Round($p.WorkingSet64 / 1MB, 0)
            Write-Output ("{0,-35} {1,12:N0}  PID:{2,8}" -f $p.ProcessName, $memMB, $p.Id)
        }
    }
    "cpu" {
        $sorted = $processes | Sort-Object CPU -Descending | Select-Object -First $n
        Write-Output ("{0,-35} {1,12}  {2}" -f "Process Name", "CPU (sec)", "PID")
        Write-Output ("{0,-35} {1,12}  {2}" -f "------------", "---------", "---")
        foreach ($p in $sorted) {
            Write-Output ("{0,-35} {1,12:N1}  PID:{2,8}" -f $p.ProcessName, $p.CPU, $p.Id)
        }
    }
    "name" {
        $sorted = $processes | Sort-Object ProcessName | Select-Object -First $n
        Write-Output ("{0,-35} {1,12}  {2}" -f "Process Name", "Memory (MB)", "PID")
        Write-Output ("{0,-35} {1,12}  {2}" -f "------------", "-----------", "---")
        foreach ($p in $sorted) {
            $memMB = [math]::Round($p.WorkingSet64 / 1MB, 0)
            Write-Output ("{0,-35} {1,12:N0}  PID:{2,8}" -f $p.ProcessName, $memMB, $p.Id)
        }
    }
}

Write-Output ""
Write-Output "PROGRESS:100"
Write-Output "[OK] Process list complete."

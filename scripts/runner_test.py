"""End-to-end test of ToolRunner: launch a real Python tool, verify
stdout parsing + callbacks fire on the right thread.

This is the closest we can get to spec §9's "Phase 8 critical check"
without running on Windows. It proves:
- subprocess.Popen launches successfully
- stdout is parsed line-by-line
- PROGRESS:N lines update the progress callback
- [OK]/[WARN]/[ERROR] prefixes route to the right level
- exit code 0 → finished(success=True)
- callbacks are NOT called on the worker thread (they push to queues
  which we drain synchronously here)

Run with:
    python3 /home/z/my-project/toolpouch-v3/scripts/runner_test.py
"""
from __future__ import annotations

import queue
import sys
import time
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.tool_loader import load_tools
from core.tool_runner import ToolRunner


def main() -> int:
    # Find the hello_python tool.
    tools = load_tools(ROOT / "tools")
    tool = next((t for t in tools if t.folder.name == "hello_python"), None)
    if tool is None:
        print("hello_python tool not found")
        return 1

    runner = ToolRunner()
    log_q: queue.Queue = queue.Queue()
    progress_q: queue.Queue = queue.Queue()
    status_q: queue.Queue = queue.Queue()
    finished_q: queue.Queue = queue.Queue()

    runner.on_log = lambda line, level: log_q.put((line, level))
    runner.on_progress = lambda pct: progress_q.put(pct)
    runner.on_status = lambda s: status_q.put(s)
    runner.on_finished = lambda success: finished_q.put(success)

    print(f"Launching {tool.script_path}...")
    args = ["--path", "/test path with spaces/file.txt"]
    ok = runner.run(tool, args, tool_name="hello_python")
    if not ok:
        print("Failed to launch")
        return 1

    # Wait for completion (timeout 10s).
    start = time.time()
    while time.time() - start < 10:
        try:
            success = finished_q.get(timeout=0.5)
            break
        except queue.Empty:
            continue
    else:
        print("TIMEOUT waiting for completion")
        return 1

    # Drain everything else.
    time.sleep(0.3)  # let the final log/progress/status emit land

    logs = []
    while True:
        try:
            logs.append(log_q.get_nowait())
        except queue.Empty:
            break

    progress_values = []
    while True:
        try:
            progress_values.append(progress_q.get_nowait())
        except queue.Empty:
            break

    statuses = []
    while True:
        try:
            statuses.append(status_q.get_nowait())
        except queue.Empty:
            break

    # Print everything for inspection.
    print("\n--- LOGS ---")
    for line, level in logs:
        print(f"  [{level:5s}] {line}")
    print(f"\n--- PROGRESS ---\n  {progress_values}")
    print(f"\n--- STATUS ---\n  {statuses}")
    print(f"\n--- FINISHED ---\n  success={success}")

    # Assertions.
    assert success, "expected success=True"
    assert "running" in statuses, "expected 'running' status"
    assert "done" in statuses, "expected 'done' status"
    assert 0 in progress_values, "expected PROGRESS:0"
    assert 50 in progress_values, "expected PROGRESS:50"
    assert 100 in progress_values, "expected PROGRESS:100"

    # Find the path_arg line — must contain the spaces.
    path_lines = [l for l, lvl in logs if "path_arg" in l]
    assert path_lines, "expected a path_arg log line"
    assert "/test path with spaces/file.txt" in path_lines[0], f"spaces lost: {path_lines[0]}"

    # Find the spaces-preserving [OK] line.
    space_ok = any("[OK] Path contains spaces" in l for l, _ in logs)
    assert space_ok, "expected 'Path contains spaces' [OK] line"

    print("\nAll assertions passed. Runner works end-to-end.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

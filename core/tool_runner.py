"""Tool execution subprocess wrapper.

REWRITTEN for v3 (was a ``QProcess``-based Qt object in v2). The new
version is pure Python and uses ``subprocess.Popen`` directly so it has
no Qt dependency. The threading pattern is critical (spec §5):

- A **worker thread** reads ``proc.stdout`` line-by-line and pushes
  parsed ``(line, level)`` tuples and ``pct`` ints onto a ``queue.Queue``.
- The **UI thread** polls that queue via ``widget.after(50, ...)`` and
  applies the updates to CTk widgets.
- The worker thread NEVER touches a CTk widget directly. This is the
  single most common CustomTkinter bug class — call it out, don't
  shortcut it.

The parsed stdout protocol is unchanged from v2 (spec §1.2):

- ``PROGRESS:N``           → progress bar update (0-100).
- ``[OK]`` prefix          → green/success log line.
- ``[WARN]`` prefix        → yellow/warning log line.
- ``[ERROR]`` prefix       → red/error log line.
- anything else            → plain info line.
- exit code 0 = success, non-zero = failure.
"""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from core.config import ConfigManager
from core.runtime_resolver import LaunchSpec, RuntimeResolver, RuntimeResolutionError


# Type aliases for the callbacks the UI registers.
LogCallback = Callable[[str, str], None]          # (line, level) -> None
ProgressCallback = Callable[[int], None]           # (pct) -> None
StatusCallback = Callable[[str], None]             # ("idle"|"running"|"done"|"error") -> None
FinishedCallback = Callable[[bool], None]          # (success) -> None


@dataclass
class _RunState:
    """Per-run scratch pad. Held by the worker thread, NOT touched by UI."""
    output_buffer: list[str] = field(default_factory=list)


class ToolRunner:
    """Run a tool script as a child OS process.

    The runner is framework-agnostic: it does not import any UI library.
    The UI registers callbacks (``on_log``, ``on_progress``, ``on_status``,
    ``on_finished``) and is responsible for marshalling them onto its own
    thread (in CustomTkinter that means ``widget.after(...)``).
    """

    def __init__(
        self,
        config: Optional[ConfigManager] = None,
        resolver: Optional[RuntimeResolver] = None,
    ) -> None:
        self.config = config or ConfigManager()
        self.resolver = resolver or RuntimeResolver()
        self._process: Optional[subprocess.Popen] = None
        self._worker: Optional[threading.Thread] = None
        self._state: _RunState = _RunState()
        self._stop_requested = False

        # Callbacks. All optional; the UI registers whichever it needs.
        self.on_log: Optional[LogCallback] = None
        self.on_progress: Optional[ProgressCallback] = None
        self.on_status: Optional[StatusCallback] = None
        self.on_finished: Optional[FinishedCallback] = None

    # ------------------------------------------------------------------ public API
    def is_running(self) -> bool:
        if self._process is None:
            return False
        return self._process.poll() is None

    def run(self, tool, args: list[str], tool_name: str = "") -> bool:
        """Launch ``tool.script_path`` with ``args`` (already in
        ``--param_id value`` form).

        Returns ``True`` if launched, ``False`` if already running or
        resolution failed. Errors during resolution are delivered through
        ``on_log``/``on_finished`` so the UI shows them in the console
        instead of raising into the event handler.
        """
        if self.is_running():
            return False

        self._stop_requested = False
        self._state = _RunState()

        # 1) Resolve interpreter.
        try:
            spec = self.resolver.resolve(tool)
        except RuntimeResolutionError as e:
            self._emit_log(f"[ERROR] {e}", "error")
            self._emit_status("error")
            self._emit_finished(False)
            return False

        # 2) Build argv (list form — NEVER string-join, spec §4).
        cmd = spec.build_command(Path(tool.script_path), list(args))
        env = self._build_env()

        # 3) Launch.
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # merge stderr into stdout for one stream
                stdin=subprocess.DEVNULL,
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,  # line-buffered
                # On Windows, create no console window for the child:
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )
        except OSError as e:
            self._emit_log(f"[ERROR] Failed to launch {tool.script_path.name}: {e}", "error")
            self._emit_status("error")
            self._emit_finished(False)
            return False

        # 4) Spawn worker thread to read stdout without blocking the UI.
        self._emit_status("running")
        self._emit_progress(0)
        self._worker = threading.Thread(
            target=self._reader_loop,
            args=(self._process, tool_name),
            name=f"ToolRunner-{tool.script_path.stem}",
            daemon=True,
        )
        self._worker.start()
        return True

    def stop(self) -> None:
        """Kill the running process tree. Idempotent."""
        if not self.is_running():
            return
        self._stop_requested = True
        proc = self._process
        if proc is None:
            return
        try:
            # On Windows, kill the whole process tree (children included)
            # so a batch script that spawned subprocesses doesn't leak.
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                proc.kill()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        self._emit_status("idle")

    # ------------------------------------------------------------------ worker
    def _reader_loop(self, proc: subprocess.Popen, tool_name: str) -> None:
        """Runs on worker thread. Reads stdout line-by-line, parses the
        protocol, pushes UI updates via callbacks. NEVER touches CTk
        widgets directly — callbacks are expected to marshal onto the
        UI thread themselves (see ``tool_panel.py``).
        """
        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                line = line.rstrip("\r\n")
                if not line:
                    continue
                self._state.output_buffer.append(line)
                self._dispatch_line(line)
                if self._stop_requested:
                    break
        except Exception as e:
            self._emit_log(f"[ERROR] Reader thread crashed: {e}", "error")
        finally:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except Exception:
                    pass
            success = proc.returncode == 0
            if tool_name:
                # Keep last 200 lines for the log file (v2 used 100; bumped
                # for richer post-mortem on long-running tools).
                output = "\n".join(self._state.output_buffer[-200:])
                try:
                    self.config.log_execution(tool_name, success, output)
                except Exception:
                    pass
            self._emit_progress(100 if success else 0)
            self._emit_status("done" if success else "error")
            self._emit_finished(success)

    # ------------------------------------------------------------------ parse
    def _dispatch_line(self, line: str) -> None:
        # Progress lines are parsed and NOT logged as text (matches v2).
        if line.startswith("PROGRESS:"):
            try:
                pct = int(line.split(":", 1)[1].strip())
                self._emit_progress(max(0, min(100, pct)))
            except ValueError:
                pass
            return

        level = "info"
        if line.startswith("[OK]"):
            level = "ok"
        elif line.startswith("[WARN]") or line.startswith("Warning"):
            level = "warn"
        elif line.startswith("[ERROR]") or line.startswith("ERROR") or line.startswith("Traceback"):
            level = "error"
        self._emit_log(line, level)

    # ------------------------------------------------------------------ emit helpers
    def _emit_log(self, line: str, level: str) -> None:
        if self.on_log is not None:
            try:
                self.on_log(line, level)
            except Exception:
                pass  # never let a UI callback crash the worker

    def _emit_progress(self, pct: int) -> None:
        if self.on_progress is not None:
            try:
                self.on_progress(pct)
            except Exception:
                pass

    def _emit_status(self, status: str) -> None:
        if self.on_status is not None:
            try:
                self.on_status(status)
            except Exception:
                pass

    def _emit_finished(self, success: bool) -> None:
        if self.on_finished is not None:
            try:
                self.on_finished(success)
            except Exception:
                pass

    # ------------------------------------------------------------------ env
    def _build_env(self) -> dict[str, str]:
        from core.runtime_resolver import build_subprocess_env
        return build_subprocess_env()

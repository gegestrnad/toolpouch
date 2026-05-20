from __future__ import annotations
import sys
import os
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from core.config import ConfigManager


def _get_python_and_env() -> tuple[str, dict]:
    env = os.environ.copy()

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent

        # PyInstaller 6+ puts python.exe inside _internal/
        candidates = [
            exe_dir / "python.exe",
            exe_dir / "_internal" / "python.exe",
        ]
        python = "python"
        for p in candidates:
            if p.exists():
                python = str(p)
                break

        # Inject packages/ into PYTHONPATH so scripts find requests, reportlab, etc.
        packages_dir = exe_dir / "packages"
        if packages_dir.exists():
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = str(packages_dir) + (os.pathsep + existing if existing else "")

        # Clear PYTHONHOME -- the bundled python.exe sets its own
        env.pop("PYTHONHOME", None)
    else:
        python = sys.executable

    return python, env


class ToolRunner(QObject):
    log_line = Signal(str, str)
    progress = Signal(int)
    status_changed = Signal(str)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: QProcess | None = None
        self.config = ConfigManager()
        self._output_buffer = []

    def run(self, script_path: Path, args: list[str], tool_name: str = ""):
        if self._process and self._process.state() != QProcess.NotRunning:
            return

        self._output_buffer = []
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.finished.connect(lambda code, status: self._on_finished(code, status, tool_name))

        python, env = _get_python_and_env()

        qenv = QProcessEnvironment()
        for k, v in env.items():
            qenv.insert(k, v)
        self._process.setProcessEnvironment(qenv)

        self.status_changed.emit("running")
        self.progress.emit(0)
        self._process.start(python, [str(script_path)] + args)

    def stop(self):
        if self._process and self._process.state() == QProcess.Running:
            self._process.kill()
            self.status_changed.emit("idle")

    def _on_output(self):
        raw = self._process.readAllStandardOutput().toStdString()
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            
            self._output_buffer.append(line)

            if line.startswith("PROGRESS:"):
                try:
                    pct = int(line.split(":", 1)[1].strip())
                    self.progress.emit(max(0, min(100, pct)))
                except ValueError:
                    pass
                continue

            level = "info"
            if line.startswith("[OK]"):
                level = "ok"
            elif line.startswith("[WARN]") or line.startswith("Warning"):
                level = "warn"
            elif line.startswith("[ERROR]") or line.startswith("ERROR") or line.startswith("Traceback"):
                level = "error"

            self.log_line.emit(line, level)

    def _on_finished(self, exit_code: int, _exit_status, tool_name: str = ""):
        success = exit_code == 0
        
        # FIX: Log full output without truncation
        if tool_name:
            output = "\n".join(self._output_buffer[-100:])  # Keep last 100 lines
            self.config.log_execution(tool_name, success, output)
        
        self.progress.emit(100 if success else 0)
        self.status_changed.emit("done" if success else "error")
        self.finished.emit(success)

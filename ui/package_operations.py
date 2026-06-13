from __future__ import annotations

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal


class PackageOperation(QObject):
    started = Signal(str)
    output = Signal(str, str)
    finished = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: QProcess | None = None
        self._operation = ""

    def is_running(self) -> bool:
        return bool(self._process and self._process.state() != QProcess.NotRunning)

    def install(self, python: str, env: dict[str, str], package_specs: list[str]) -> bool:
        return self._start(
            python,
            env,
            ["-m", "pip", "install", *package_specs],
            f"python -m pip install {' '.join(package_specs)}",
            "install",
        )

    def uninstall(self, python: str, env: dict[str, str], packages: list[str]) -> bool:
        return self._start(
            python,
            env,
            ["-m", "pip", "uninstall", "-y", *packages],
            f"python -m pip uninstall -y {' '.join(packages)}",
            "uninstall",
        )

    def _start(
        self,
        python: str,
        env: dict[str, str],
        args: list[str],
        display_command: str,
        operation: str,
    ) -> bool:
        if self.is_running():
            self.output.emit("[WARN] Package operation is still running.", "warn")
            return False

        self._operation = operation
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.finished.connect(self._on_finished)

        qenv = QProcessEnvironment()
        for key, value in env.items():
            qenv.insert(key, value)
        self._process.setProcessEnvironment(qenv)

        self.started.emit(display_command)
        self._process.start(python, args)
        return True

    def _on_output(self):
        if not self._process:
            return
        raw = self._process.readAllStandardOutput().toStdString()
        for line in raw.splitlines():
            line = line.strip()
            if line:
                self.output.emit(line, "info")

    def _on_finished(self, exit_code: int, _exit_status):
        success = exit_code == 0
        operation = self._operation
        self.finished.emit(success, operation)

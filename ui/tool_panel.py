from __future__ import annotations
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QMimeData
from PySide6.QtGui import QColor, QTextCursor, QFont, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFileDialog, QProgressBar,
    QTextEdit, QFrame, QListView, QTreeView, QAbstractItemView,
    QMessageBox,
)

from core.dependency_checker import (
    MissingDependency,
    dependency_statuses_for_tools,
    python_supports_pip,
)
from core.tool_loader import ToolDefinition, ToolParam
from core.tool_runner import ToolRunner, _get_python_and_env
from ui.package_operations import PackageOperation


LEVEL_COLORS = {
    "ok":    "#1D9E75",
    "warn":  "#BA7517",
    "error": "#E24B4A",
    "info":  None,  # default text color
}


class FieldWidget(QWidget):
    def __init__(self, param: ToolParam, parent=None):
        super().__init__(parent)
        self.param = param
        self._selected_paths: list[str] = []
        self._drop_enabled = param.type in ("folder", "folders", "file", "files")
        self.setAcceptDrops(self._drop_enabled)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        label = QLabel(param.label + (" *" if param.required else ""))
        label.setObjectName("field_label")
        lay.addWidget(label)

        row = QHBoxLayout()
        row.setSpacing(6)

        if param.type == "dropdown":
            self._input = QComboBox()
            self._input.addItems(param.options)
            if param.default in param.options:
                self._input.setCurrentText(param.default)
            row.addWidget(self._input)
        else:
            self._input = QLineEdit()
            self._input.setAcceptDrops(False)
            self._input.setPlaceholderText(param.placeholder)
            if param.type in ("files", "folders"):
                self._input.setReadOnly(True)
            row.addWidget(self._input)

            if param.type in ("folder", "folders", "file", "files", "save"):
                btn = QPushButton("Browse…")
                btn.setObjectName("browse_btn")
                btn.setFixedWidth(80)
                btn.setAcceptDrops(False)
                btn.clicked.connect(self._browse)
                row.addWidget(btn)

        lay.addLayout(row)

    def _browse(self):
        if self.param.type == "folder":
            path = QFileDialog.getExistingDirectory(self, f"Select {self.param.label}")
        elif self.param.type == "folders":
            paths = self._get_existing_directories()
            if paths:
                self._apply_selected_paths(paths, "folder")
            return
        elif self.param.type == "file":
            filt = self.param.filter or "All files (*)"
            path, _ = QFileDialog.getOpenFileName(self, f"Select {self.param.label}", "", filt)
        elif self.param.type == "files":
            filt = self.param.filter or "All files (*)"
            paths, _ = QFileDialog.getOpenFileNames(self, f"Select {self.param.label}", "", filt)
            if paths:
                self._apply_selected_paths(paths, "file")
            return
        else:  # save
            filt = self.param.filter or "All files (*)"
            path, _ = QFileDialog.getSaveFileName(self, "Save as", "", filt)

        if path:
            self._input.setText(path)

    def _get_existing_directories(self) -> list[str]:
        dialog = QFileDialog(self, f"Select {self.param.label}")
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)

        for view_type in (QListView, QTreeView):
            view = dialog.findChild(view_type)
            if view:
                view.setSelectionMode(QAbstractItemView.ExtendedSelection)

        if dialog.exec():
            return dialog.selectedFiles()
        return []

    def dragEnterEvent(self, event: QDragEnterEvent):
        if self._drop_enabled and self._can_apply_dropped_paths(
            self._local_paths_from_mime_data(event.mimeData())
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if self._apply_dropped_paths(self._local_paths_from_mime_data(event.mimeData())):
            event.acceptProposedAction()
        else:
            event.ignore()

    def _local_paths_from_mime_data(self, mime_data: QMimeData) -> list[str]:
        paths = []
        for url in mime_data.urls():
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        return paths

    def _can_apply_dropped_paths(self, paths: list[str]) -> bool:
        if not paths:
            return False
        if self.param.type == "folder":
            return len(paths) == 1 and Path(paths[0]).is_dir()
        if self.param.type == "folders":
            return all(Path(path).is_dir() for path in paths)
        if self.param.type == "file":
            return len(paths) == 1 and Path(paths[0]).is_file()
        if self.param.type == "files":
            return all(Path(path).is_file() for path in paths)
        return False

    def _apply_dropped_paths(self, paths: list[str]) -> bool:
        if not self._can_apply_dropped_paths(paths):
            return False
        if self.param.type == "files":
            self._apply_selected_paths(paths, "file")
        elif self.param.type == "folders":
            self._apply_selected_paths(paths, "folder")
        else:
            self._input.setText(paths[0])
        return True

    def _apply_selected_paths(self, paths: list[str], singular_label: str):
        self._selected_paths = paths
        count = len(paths)
        label = singular_label if count == 1 else f"{singular_label}s"
        self._input.setText(f"{count} {label} selected")

    def value(self) -> str:
        if isinstance(self._input, QComboBox):
            return self._input.currentText()
        if self.param.type in ("files", "folders"):
            return "\n".join(self._selected_paths)
        return self._input.text().strip()

    def reset(self):
        if isinstance(self._input, QComboBox):
            if self.param.default in self.param.options:
                self._input.setCurrentText(self.param.default)
            elif self._input.count():
                self._input.setCurrentIndex(0)
            return

        self._selected_paths = []
        self._input.clear()

    def is_valid(self) -> bool:
        if not self.param.required:
            return True
        return bool(self.value())


class ToolPanel(QWidget):
    def __init__(self, tool: ToolDefinition, parent=None):
        super().__init__(parent)
        self.tool = tool
        self.runner = ToolRunner(self)
        self._package_operation = PackageOperation(self)
        self._field_widgets: list[FieldWidget] = []
        self._build_ui()
        self._connect_runner()
        self._connect_package_operation()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("tool_header")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 16, 20, 14)

        title_area = QVBoxLayout()
        name_lbl = QLabel(self.tool.name)
        name_lbl.setObjectName("tool_name")
        desc_lbl = QLabel(self.tool.description)
        desc_lbl.setObjectName("tool_desc")
        desc_lbl.setWordWrap(True)
        title_area.addWidget(name_lbl)
        title_area.addWidget(desc_lbl)

        self.run_btn = QPushButton("  Run")
        self.run_btn.setObjectName("run_btn")
        self.run_btn.setFixedHeight(34)
        self.run_btn.clicked.connect(self._run)

        self.stop_btn = QPushButton("  Stop")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setFixedHeight(34)
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self.runner.stop)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("clear_btn")
        self.reset_btn.setFixedHeight(28)
        self.reset_btn.clicked.connect(self._reset_form)

        h_lay.addLayout(title_area)
        h_lay.addStretch()
        h_lay.addWidget(self.reset_btn)
        h_lay.addWidget(self.stop_btn)
        h_lay.addWidget(self.run_btn)
        root.addWidget(header)

        # Params
        params_frame = QFrame()
        params_frame.setObjectName("params_frame")
        p_lay = QVBoxLayout(params_frame)
        p_lay.setContentsMargins(20, 14, 20, 14)
        p_lay.setSpacing(12)

        for param in self.tool.params:
            fw = FieldWidget(param)
            self._field_widgets.append(fw)
            p_lay.addWidget(fw)

        root.addWidget(params_frame)

        # Progress
        progress_frame = QFrame()
        progress_frame.setObjectName("progress_frame")
        prog_lay = QVBoxLayout(progress_frame)
        prog_lay.setContentsMargins(20, 10, 20, 10)
        prog_lay.setSpacing(6)

        prog_top = QHBoxLayout()
        self.progress_label = QLabel("Ready")
        self.progress_label.setObjectName("progress_label")
        self.progress_pct = QLabel("0%")
        self.progress_pct.setObjectName("progress_pct")
        prog_top.addWidget(self.progress_label)
        prog_top.addStretch()
        prog_top.addWidget(self.progress_pct)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)

        prog_lay.addLayout(prog_top)
        prog_lay.addWidget(self.progress_bar)
        root.addWidget(progress_frame)

        # Log
        log_frame = QFrame()
        log_frame.setObjectName("log_frame")
        log_lay = QVBoxLayout(log_frame)
        log_lay.setContentsMargins(0, 0, 0, 0)
        log_lay.setSpacing(0)

        log_header = QFrame()
        log_header.setObjectName("log_header")
        lh_lay = QHBoxLayout(log_header)
        lh_lay.setContentsMargins(20, 7, 12, 7)

        log_title = QLabel("Output log")
        log_title.setObjectName("log_title")
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("clear_btn")
        clear_btn.setFixedHeight(24)
        clear_btn.clicked.connect(self._clear_log)

        lh_lay.addWidget(log_title)
        lh_lay.addStretch()
        lh_lay.addWidget(clear_btn)
        log_lay.addWidget(log_header)

        self.log_console = QTextEdit()
        self.log_console.setObjectName("log_console")
        self.log_console.setReadOnly(True)
        font = QFont("Consolas", 11)
        if not font.exactMatch():
            font = QFont("Courier New", 11)
        self.log_console.setFont(font)
        log_lay.addWidget(self.log_console)

        root.addWidget(log_frame)
        root.setStretch(root.count() - 1, 1)

    def _connect_runner(self):
        self.runner.log_line.connect(self._append_log)
        self.runner.progress.connect(self._update_progress)
        self.runner.status_changed.connect(self._on_status)
        self.runner.finished.connect(self._on_finished)

    def _connect_package_operation(self):
        self._package_operation.started.connect(self._on_package_operation_started)
        self._package_operation.output.connect(self._append_log)
        self._package_operation.finished.connect(self._on_install_finished)

    def _run(self):
        if self._package_operation.is_running():
            self._append_log("[WARN] Package installation is still running.", "warn")
            return

        missing = [fw.param.label for fw in self._field_widgets if not fw.is_valid()]
        if missing:
            self._append_log(f"[ERROR] Required fields missing: {', '.join(missing)}", "error")
            return

        missing_dependencies = self._find_missing_dependencies()
        if missing_dependencies and not self._handle_missing_dependencies(missing_dependencies):
            return

        args = []
        for fw in self._field_widgets:
            v = fw.value()
            if v:
                args.extend([f"--{fw.param.id}", v])

        self._clear_log()
        self.runner.run(self.tool.script_path, args)

    def _reset_form(self):
        if self.runner.is_running():
            return
        for fw in self._field_widgets:
            fw.reset()

    def _find_missing_dependencies(self) -> list[MissingDependency]:
        try:
            python, env = _get_python_and_env()
            statuses = dependency_statuses_for_tools([self.tool], python, env)
            return [
                MissingDependency(status.import_name, status.package_name, status.version)
                for status in statuses
                if status.status == "missing"
            ]
        except Exception as exc:
            self._append_log(f"[WARN] Could not check Python dependencies: {exc}", "warn")
            return []

    def _handle_missing_dependencies(self, missing: list[MissingDependency]) -> bool:
        package_names = sorted({dependency.install_spec for dependency in missing}, key=str.casefold)
        import_names = ", ".join(dependency.import_name for dependency in missing)
        package_list = " ".join(package_names)
        command = f"python -m pip install {package_list}"

        self._append_log(
            f"[ERROR] Missing Python package(s) for imports: {import_names}",
            "error",
        )

        python, env = _get_python_and_env()
        if not python_supports_pip(python, env):
            self._append_log(
                "[ERROR] The active ToolPouch Python does not have pip available.",
                "error",
            )
            self._append_log(
                f"[INFO] Install manually or rebuild/update the runtime with: {command}",
                "info",
            )
            QMessageBox.information(
                self,
                "Missing Python packages",
                "ToolPouch found missing Python packages, but the active Python runtime "
                "does not have pip available.\n\n"
                f"Packages: {package_list}\n\n"
                "Install them manually or rebuild/update the portable runtime.",
            )
            return False

        reply = QMessageBox.question(
            self,
            "Install missing packages?",
            "ToolPouch found missing Python packages for this tool.\n\n"
            f"Imports: {import_names}\n"
            f"Packages: {package_list}\n\n"
            "Install them into the active ToolPouch Python environment now?\n\n"
            "You can also manage packages from the Dependencies page.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            self._append_log(f"[INFO] Install skipped. Suggested command: {command}", "info")
            return False

        self._start_package_install(python, env, package_names)
        return False

    def _start_package_install(self, python: str, env: dict[str, str], packages: list[str]):
        self.run_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.progress_label.setText("Installing packages...")
        self._package_operation.install(python, env, packages)

    def _on_package_operation_started(self, command: str):
        self._append_log(f"[INFO] Running: {command}", "info")

    def _on_install_finished(self, success: bool, _operation: str):
        self.run_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)
        self.progress_label.setText("Ready" if success else "Finished with errors")
        if success:
            self._append_log("[OK] Package installation completed. Click Run again.", "ok")
        else:
            self._append_log("[ERROR] Package installation failed. Check the log above.", "error")

    def _clear_log(self):
        self.log_console.clear()

    def _append_log(self, text: str, level: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = LEVEL_COLORS.get(level)

        cursor = self.log_console.textCursor()
        cursor.movePosition(QTextCursor.End)

        ts_format = self.log_console.currentCharFormat()
        ts_format.setForeground(QColor("#888780"))
        cursor.setCharFormat(ts_format)
        cursor.insertText(f"{timestamp}  ")

        msg_format = self.log_console.currentCharFormat()
        if color:
            msg_format.setForeground(QColor(color))
        else:
            msg_format.clearForeground()
        cursor.setCharFormat(msg_format)
        cursor.insertText(text + "\n")

        self.log_console.setTextCursor(cursor)
        self.log_console.ensureCursorVisible()

    def _update_progress(self, value: int):
        self.progress_bar.setValue(value)
        self.progress_pct.setText(f"{value}%")

    def _on_status(self, status: str):
        labels = {
            "running": "Running...",
            "done":    "Done",
            "error":   "Finished with errors",
            "idle":    "Stopped",
        }
        self.progress_label.setText(labels.get(status, "Ready"))
        is_running = status == "running"
        self.run_btn.setVisible(not is_running)
        self.stop_btn.setVisible(is_running)
        self.reset_btn.setEnabled(not is_running)

    def _on_finished(self, success: bool):
        msg = "Completed successfully." if success else "Finished with errors. Check the log above."
        level = "ok" if success else "error"
        self._append_log(f"--- {msg} ---", level)

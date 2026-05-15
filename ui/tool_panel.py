from __future__ import annotations
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFileDialog, QProgressBar,
    QTextEdit, QSizePolicy, QFrame, QScrollArea,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QTextCursor, QFont

from core.tool_loader import ToolDefinition, ToolParam
from core.tool_runner import ToolRunner


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
            self._input.setPlaceholderText(param.placeholder)
            row.addWidget(self._input)

            if param.type in ("folder", "file", "save"):
                btn = QPushButton("Browse…")
                btn.setObjectName("browse_btn")
                btn.setFixedWidth(80)
                btn.clicked.connect(self._browse)
                row.addWidget(btn)

        lay.addLayout(row)

    def _browse(self):
        if self.param.type == "folder":
            path = QFileDialog.getExistingDirectory(self, f"Select {self.param.label}")
        elif self.param.type == "file":
            filt = self.param.filter or "All files (*)"
            path, _ = QFileDialog.getOpenFileName(self, f"Select {self.param.label}", "", filt)
        else:  # save
            filt = self.param.filter or "All files (*)"
            path, _ = QFileDialog.getSaveFileName(self, f"Save as", "", filt)

        if path:
            self._input.setText(path)

    def value(self) -> str:
        if isinstance(self._input, QComboBox):
            return self._input.currentText()
        return self._input.text().strip()

    def is_valid(self) -> bool:
        if not self.param.required:
            return True
        return bool(self.value())


class ToolPanel(QWidget):
    def __init__(self, tool: ToolDefinition, parent=None):
        super().__init__(parent)
        self.tool = tool
        self.runner = ToolRunner(self)
        self._field_widgets: list[FieldWidget] = []
        self._build_ui()
        self._connect_runner()

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

        h_lay.addLayout(title_area)
        h_lay.addStretch()
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

    def _run(self):
        missing = [fw.param.label for fw in self._field_widgets if not fw.is_valid()]
        if missing:
            self._append_log(f"[ERROR] Required fields missing: {', '.join(missing)}", "error")
            return

        args = []
        for fw in self._field_widgets:
            v = fw.value()
            if v:
                args.extend([f"--{fw.param.id}", v])

        self._clear_log()
        self.runner.run(self.tool.script_path, args)

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

    def _on_finished(self, success: bool):
        msg = "Completed successfully." if success else "Finished with errors. Check the log above."
        level = "ok" if success else "error"
        self._append_log(f"--- {msg} ---", level)

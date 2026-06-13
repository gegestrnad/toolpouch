from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.dependency_checker import (
    DependencyStatus,
    dependency_statuses_for_tools,
    python_supports_pip,
)
from core.tool_runner import _get_python_and_env
from ui.package_operations import PackageOperation


class DependencyManagerPage(QWidget):
    def __init__(self, tools=None, parent=None):
        super().__init__(parent)
        self._tools = list(tools or [])
        self._statuses: list[DependencyStatus] = []
        self._pip_available = False
        self._package_operation = PackageOperation(self)
        self._build_ui()
        self._connect_package_operation()

    def set_tools(self, tools, refresh: bool = False):
        self._tools = list(tools)
        if refresh or self.isVisible():
            self.refresh()

    def refresh(self):
        try:
            python, env = _get_python_and_env()
            self._pip_available = python_supports_pip(python, env)
            self._statuses = dependency_statuses_for_tools(self._tools, python, env)
        except Exception as exc:
            self._statuses = []
            self.status_label.setText(f"Could not scan dependencies: {exc}")
            self._populate_table()
            self._update_actions()
            return

        if not self._statuses:
            self.status_label.setText("No Python package dependencies detected.")
        elif self._pip_available:
            self.status_label.setText("Packages are checked against the active ToolPouch Python runtime.")
        else:
            self.status_label.setText(
                "The active ToolPouch Python runtime does not have pip available."
            )
        self._populate_table()
        self._update_actions()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("tool_header")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 14)
        header_layout.setSpacing(4)

        title = QLabel("Dependencies")
        title.setObjectName("tool_name")
        subtitle = QLabel("Review and manage Python packages used by your tools.")
        subtitle.setObjectName("tool_desc")
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        body = QFrame()
        body.setObjectName("params_frame")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 14, 20, 14)
        body_layout.setSpacing(10)

        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("clear_btn")
        self.refresh_btn.clicked.connect(self.refresh)
        self.install_btn = QPushButton("Install missing")
        self.install_btn.setObjectName("run_btn")
        self.install_btn.clicked.connect(self._install_missing)
        self.uninstall_btn = QPushButton("Uninstall selected")
        self.uninstall_btn.setObjectName("stop_btn")
        self.uninstall_btn.clicked.connect(self._uninstall_selected)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.uninstall_btn)
        toolbar.addWidget(self.install_btn)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("progress_label")
        self.status_label.setWordWrap(True)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Tool",
            "Import",
            "Package",
            "Status",
            "Source",
            "Version",
            "Notes",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._update_actions)

        body_layout.addLayout(toolbar)
        body_layout.addWidget(self.status_label)
        body_layout.addWidget(self.table)
        root.addWidget(body)
        root.setStretch(root.count() - 1, 1)

    def _connect_package_operation(self):
        self._package_operation.started.connect(self._on_package_operation_started)
        self._package_operation.output.connect(self._on_package_output)
        self._package_operation.finished.connect(self._on_package_finished)

    def _populate_table(self):
        self.table.setRowCount(0)
        for status in self._statuses:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                status.tool_name,
                status.import_name,
                status.package_name,
                status.status,
                status.source,
                status.version,
                status.notes,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 3:
                    item.setForeground(QColor("#1D9E75" if value == "installed" else "#E24B4A"))
                self.table.setItem(row, column, item)

    def _install_missing(self):
        if self._package_operation.is_running():
            return
        if not self._pip_available:
            QMessageBox.information(
                self,
                "pip unavailable",
                "The active ToolPouch Python runtime does not have pip available.",
            )
            return

        packages = sorted(
            {status.install_spec for status in self._statuses if status.status == "missing"},
            key=str.casefold,
        )
        if not packages:
            self.status_label.setText("No missing packages to install.")
            return

        python, env = _get_python_and_env()
        self._set_busy(True)
        self._package_operation.install(python, env, packages)

    def _uninstall_selected(self):
        if self._package_operation.is_running():
            return
        if not self._pip_available:
            QMessageBox.information(
                self,
                "pip unavailable",
                "The active ToolPouch Python runtime does not have pip available.",
            )
            return

        packages = self._selected_installed_packages()
        if not packages:
            self.status_label.setText("Select installed package rows to uninstall.")
            return

        reply = QMessageBox.question(
            self,
            "Uninstall packages?",
            "Uninstalling packages can affect multiple tools that share them.\n\n"
            f"Packages: {', '.join(packages)}\n\n"
            "Uninstall these packages from the active ToolPouch Python runtime?",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply != QMessageBox.Yes:
            return

        python, env = _get_python_and_env()
        self._set_busy(True)
        self._package_operation.uninstall(python, env, packages)

    def _selected_installed_packages(self) -> list[str]:
        rows = {index.row() for index in self.table.selectionModel().selectedRows()}
        packages = {
            self._statuses[row].package_name
            for row in rows
            if 0 <= row < len(self._statuses) and self._statuses[row].status == "installed"
        }
        return sorted(packages, key=str.casefold)

    def _update_actions(self):
        running = self._package_operation.is_running()
        has_missing = any(status.status == "missing" for status in self._statuses)
        has_installed_selection = bool(self._selected_installed_packages()) if self._statuses else False
        self.refresh_btn.setEnabled(not running)
        self.install_btn.setEnabled(not running and self._pip_available and has_missing)
        self.uninstall_btn.setEnabled(not running and self._pip_available and has_installed_selection)

    def _set_busy(self, busy: bool):
        self.refresh_btn.setEnabled(not busy)
        self.install_btn.setEnabled(False)
        self.uninstall_btn.setEnabled(False)

    def _on_package_operation_started(self, command: str):
        self.status_label.setText(f"Running: {command}")

    def _on_package_output(self, text: str, _level: str):
        self.status_label.setText(text)

    def _on_package_finished(self, success: bool, operation: str):
        self.status_label.setText(
            f"Package {operation} completed." if success else f"Package {operation} failed."
        )
        self.refresh()


class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("tool_header")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 14)
        header_layout.setSpacing(4)

        title = QLabel("About Me")
        title.setObjectName("tool_name")
        subtitle = QLabel("Tool Pouch is a local desktop workspace for small Python utilities.")
        subtitle.setObjectName("tool_desc")
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        body = QFrame()
        body.setObjectName("params_frame")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 18, 20, 18)
        body_layout.setSpacing(8)
        body_layout.setAlignment(Qt.AlignTop)

        link = QLabel(
            '<a href="https://github.com/gegestrnad/toolpouch">'
            "github.com/gegestrnad/toolpouch"
            "</a>"
        )
        link.setOpenExternalLinks(True)
        link.setTextFormat(Qt.RichText)
        link.setObjectName("tool_desc")
        body_layout.addWidget(link)
        root.addWidget(body)
        root.setStretch(root.count() - 1, 1)

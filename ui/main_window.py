from __future__ import annotations
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QStackedWidget,
    QScrollArea, QSizePolicy, QMessageBox, QMenu,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon

from core.tool_loader import ToolDefinition, load_tools
from ui.tool_panel import ToolPanel
from ui.wizard_dialog import WizardDialog


ACCENT = "#534AB7"
ACCENT_HOVER = "#3C3489"

STYLESHEET = f"""
QMainWindow, QWidget {{
    background: palette(window);
    color: palette(windowText);
    font-family: "Segoe UI", "SF Pro Display", sans-serif;
    font-size: 13px;
}}

/* Sidebar */
#sidebar {{
    background: palette(alternateBase);
    border-right: 1px solid palette(mid);
    min-width: 210px;
    max-width: 210px;
}}

#app_title {{
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}

#app_version {{
    font-size: 10px;
    color: palette(placeholderText);
}}

/* Search */
#search_input {{
    border: 1px solid palette(mid);
    border-radius: 6px;
    padding: 5px 10px;
    background: palette(base);
    font-size: 12px;
}}

#search_input:focus {{
    border: 1px solid {ACCENT};
    outline: none;
}}

/* Tool items */
.tool_item {{
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0;
    text-align: left;
    padding: 8px 14px;
    font-size: 13px;
    color: palette(placeholderText);
    background: transparent;
}}

.tool_item:hover {{
    background: palette(base);
    color: palette(windowText);
}}

.tool_item_active {{
    border: none;
    border-left: 2px solid {ACCENT};
    border-radius: 0;
    text-align: left;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 600;
    color: palette(windowText);
    background: palette(base);
}}

/* Add tool button */
#add_tool_btn {{
    border: 1px dashed palette(mid);
    border-radius: 6px;
    padding: 7px;
    font-size: 12px;
    color: palette(placeholderText);
    background: transparent;
    margin: 8px;
}}

#add_tool_btn:hover {{
    border-color: {ACCENT};
    color: {ACCENT};
}}

/* Tool header */
#tool_header {{
    border-bottom: 1px solid palette(mid);
}}

#tool_name {{
    font-size: 16px;
    font-weight: 600;
}}

#tool_desc {{
    font-size: 12px;
    color: palette(placeholderText);
}}

/* Run / Stop buttons */
#run_btn {{
    background: {ACCENT};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 0 18px;
    font-size: 13px;
    font-weight: 600;
    min-width: 90px;
}}

#run_btn:hover {{
    background: {ACCENT_HOVER};
}}

#run_btn:pressed {{
    background: #26215C;
}}

#stop_btn {{
    background: #A32D2D;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 0 18px;
    font-size: 13px;
    font-weight: 600;
    min-width: 90px;
}}

#stop_btn:hover {{
    background: #791F1F;
}}

/* Params */
#params_frame {{
    border-bottom: 1px solid palette(mid);
}}

#field_label {{
    font-size: 12px;
    font-weight: 600;
    color: palette(placeholderText);
}}

QLineEdit {{
    border: 1px solid palette(mid);
    border-radius: 6px;
    padding: 6px 10px;
    background: palette(base);
    font-size: 13px;
}}

QLineEdit:focus {{
    border: 1px solid {ACCENT};
}}

QComboBox {{
    border: 1px solid palette(mid);
    border-radius: 6px;
    padding: 5px 10px;
    background: palette(base);
}}

QComboBox:focus {{
    border: 1px solid {ACCENT};
}}

#browse_btn {{
    border: 1px solid palette(mid);
    border-radius: 6px;
    padding: 5px 10px;
    background: palette(alternateBase);
    font-size: 12px;
}}

#browse_btn:hover {{
    border-color: {ACCENT};
    color: {ACCENT};
}}

/* Progress */
#progress_frame {{
    border-bottom: 1px solid palette(mid);
}}

#progress_label {{
    font-size: 12px;
    color: palette(placeholderText);
}}

#progress_pct {{
    font-size: 12px;
    font-weight: 600;
    color: {ACCENT};
}}

QProgressBar {{
    border: none;
    border-radius: 2px;
    background: palette(mid);
}}

QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 2px;
}}

/* Log */
#log_header {{
    border-bottom: 1px solid palette(mid);
    background: palette(alternateBase);
}}

#log_title {{
    font-size: 12px;
    font-weight: 600;
    color: palette(placeholderText);
}}

#clear_btn {{
    border: 1px solid palette(mid);
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 11px;
    background: transparent;
    color: palette(placeholderText);
}}

#clear_btn:hover {{
    color: palette(windowText);
}}

#log_console {{
    background: palette(alternateBase);
    border: none;
    font-size: 12px;
}}

/* Welcome */
#welcome_label {{
    font-size: 15px;
    color: palette(placeholderText);
}}

/* Section header */
#section_label {{
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    color: palette(placeholderText);
    padding: 10px 16px 4px;
}}

#no_results {{
    font-size: 12px;
    color: palette(placeholderText);
    padding: 10px 16px;
}}

#remove_btn {{
    background: transparent;
    border: 1px solid palette(mid);
    border-radius: 4px;
    color: palette(placeholderText);
    font-size: 11px;
}}

#remove_btn:hover {{
    border-color: #E24B4A;
    color: #E24B4A;
}}

/* Context menu */
QMenu {{
    background: palette(alternateBase);
    border: 1px solid palette(mid);
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 20px;
    border-radius: 4px;
    font-size: 13px;
}}

QMenu::item:selected {{
    background: {ACCENT};
    color: white;
}}

QMenu::separator {{
    height: 1px;
    background: palette(mid);
    margin: 3px 8px;
}}
"""


class ToolButton(QPushButton):
    def __init__(self, tool: ToolDefinition, parent=None):
        super().__init__(tool.name, parent)
        self.tool = tool
        self.setProperty("class", "tool_item")
        self.setMinimumHeight(36)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

    def set_active(self, active: bool):
        self.setProperty("class", "tool_item_active" if active else "tool_item")
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    def __init__(self, tools_dir: Path):
        super().__init__()
        self.tools_dir = tools_dir
        self.setWindowTitle("Tool Pouch")
        self.setMinimumSize(QSize(860, 580))
        self.resize(1000, 680)
        self._set_window_icon()

        self._tools: list[ToolDefinition] = []
        self._tool_buttons: list[ToolButton] = []
        self._panels: dict[str, ToolPanel] = {}
        self._active_btn: ToolButton | None = None

        self._build_ui()
        self._load_tools()

    def _set_window_icon(self):
        import sys
        from pathlib import Path
        # Resolve icon path whether running frozen or from source
        if getattr(sys, 'frozen', False):
            base = Path(sys.executable).parent
        else:
            base = Path(__file__).parent.parent
        icon_path = base / 'assets' / 'icon.ico'
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _build_ui(self):
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)

        # Sidebar header
        hdr = QWidget()
        hdr_lay = QVBoxLayout(hdr)
        hdr_lay.setContentsMargins(16, 14, 16, 10)
        hdr_lay.setSpacing(2)

        title_lbl = QLabel("Tool Pouch")
        title_lbl.setObjectName("app_title")
        self.version_lbl = QLabel("0 tools loaded")
        self.version_lbl.setObjectName("app_version")
        hdr_lay.addWidget(title_lbl)
        hdr_lay.addWidget(self.version_lbl)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setObjectName("search_input")
        self.search_input.setPlaceholderText("Search tools...")
        self.search_input.textChanged.connect(self._filter_tools)
        hdr_lay.addSpacing(8)
        hdr_lay.addWidget(self.search_input)

        sb_lay.addWidget(hdr)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sb_lay.addWidget(sep)

        # Tool list (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        self.tool_list_widget = QWidget()
        self.tool_list_layout = QVBoxLayout(self.tool_list_widget)
        self.tool_list_layout.setContentsMargins(0, 4, 0, 4)
        self.tool_list_layout.setSpacing(0)
        self.tool_list_layout.setAlignment(Qt.AlignTop)

        self.section_label = QLabel("TOOLS")
        self.section_label.setObjectName("section_label")
        self.tool_list_layout.addWidget(self.section_label)

        self.no_results_label = QLabel("No tools match your search.")
        self.no_results_label.setObjectName("no_results")
        self.no_results_label.setVisible(False)
        self.tool_list_layout.addWidget(self.no_results_label)

        scroll.setWidget(self.tool_list_widget)
        sb_lay.addWidget(scroll)

        # Add tool button
        add_btn = QPushButton("+ Add new tool")
        add_btn.setObjectName("add_tool_btn")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._open_wizard)
        sb_lay.addWidget(add_btn)

        root.addWidget(sidebar)

        # Main content area (stacked)
        self.stack = QStackedWidget()

        welcome = QWidget()
        wl = QVBoxLayout(welcome)
        wl.setAlignment(Qt.AlignCenter)
        wlbl = QLabel("Select a tool from the sidebar to get started.")
        wlbl.setObjectName("welcome_label")
        wlbl.setAlignment(Qt.AlignCenter)
        wl.addWidget(wlbl)
        self.stack.addWidget(welcome)

        root.addWidget(self.stack)

    def _load_tools(self):
        self._tools = load_tools(self.tools_dir)
        self.version_lbl.setText(f"{len(self._tools)} tool{'s' if len(self._tools) != 1 else ''} loaded")

        for btn in self._tool_buttons:
            btn.setParent(None)
        self._tool_buttons.clear()

        for tool in self._tools:
            btn = ToolButton(tool)
            btn.clicked.connect(lambda checked, t=tool, b=btn: self._select_tool(t, b))
            btn.customContextMenuRequested.connect(
                lambda pos, t=tool, b=btn: self._show_tool_context_menu(pos, t, b)
            )
            self.tool_list_layout.addWidget(btn)
            self._tool_buttons.append(btn)

    def _select_tool(self, tool: ToolDefinition, btn: ToolButton):
        if self._active_btn:
            self._active_btn.set_active(False)
        btn.set_active(True)
        self._active_btn = btn

        key = tool.name
        if key not in self._panels:
            panel = ToolPanel(tool)
            self._panels[key] = panel
            self.stack.addWidget(panel)

        self.stack.setCurrentWidget(self._panels[key])

    def _filter_tools(self, text: str):
        q = text.strip().lower()
        any_visible = False
        for btn in self._tool_buttons:
            match = not q or q in btn.tool.name.lower() or q in btn.tool.description.lower()
            btn.setVisible(match)
            if match:
                any_visible = True
        self.no_results_label.setVisible(bool(q) and not any_visible)

    def _show_tool_context_menu(self, pos, tool, btn):
        menu = QMenu(self)
        edit_action = menu.addAction("Edit tool...")
        menu.addSeparator()
        delete_action = menu.addAction("Delete tool")
        delete_action.setProperty("danger", True)

        action = menu.exec(btn.mapToGlobal(pos))
        if action == edit_action:
            self._edit_tool(tool)
        elif action == delete_action:
            self._delete_tool(tool, btn)

    def _edit_tool(self, tool):
        dlg = WizardDialog(self.tools_dir, self, edit_tool=tool)
        if dlg.exec():
            # Clear cached panel so it rebuilds with updated config
            if tool.name in self._panels:
                old_panel = self._panels.pop(tool.name)
                self.stack.removeWidget(old_panel)
                old_panel.deleteLater()
            self._active_btn = None
            self._load_tools()

    def _delete_tool(self, tool, btn):
        reply = QMessageBox.question(
            self,
            "Delete tool",
            f"Permanently delete <b>{tool.name}</b> and all its files?<br><br>"
            f"<small>Folder: {tool.folder}</small>",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply != QMessageBox.Yes:
            return

        import shutil
        try:
            shutil.rmtree(tool.folder)
        except Exception as e:
            QMessageBox.critical(self, "Delete failed", f"Could not delete tool folder:\n{e}")
            return

        # Clear cached panel
        if tool.name in self._panels:
            old_panel = self._panels.pop(tool.name)
            self.stack.removeWidget(old_panel)
            old_panel.deleteLater()

        if self._active_btn is btn:
            self._active_btn = None
            self.stack.setCurrentIndex(0)  # back to welcome screen

        self._load_tools()

    def _open_wizard(self):
        dlg = WizardDialog(self.tools_dir, self)
        if dlg.exec():
            self._load_tools()
            QMessageBox.information(self, "Tool added", "Tool created successfully. It now appears in the sidebar.")

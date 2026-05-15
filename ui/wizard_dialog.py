from __future__ import annotations
import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QComboBox, QScrollArea, QWidget,
    QFileDialog, QGroupBox, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt

from core.wizard import PARAM_TYPES, ICONS, generate_toml, write_tool


class ParamRow(QFrame):
    def __init__(self, parent=None, data: dict | None = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(6)

        self.id_edit = QLineEdit(placeholderText="id (no spaces)")
        self.id_edit.setFixedWidth(110)
        self.label_edit = QLineEdit(placeholderText="Label")
        self.label_edit.setFixedWidth(130)
        self.type_combo = QComboBox()
        self.type_combo.addItems(PARAM_TYPES)
        self.type_combo.setFixedWidth(90)
        self.placeholder_edit = QLineEdit(placeholderText="Placeholder text")
        self.required_cb = QCheckBox("Required")
        self.required_cb.setFixedWidth(75)

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(26, 26)
        remove_btn.setObjectName("remove_btn")
        remove_btn.clicked.connect(self._remove)

        for w in [self.id_edit, self.label_edit, self.type_combo,
                  self.placeholder_edit, self.required_cb, remove_btn]:
            lay.addWidget(w)

        # Pre-fill if editing existing param
        if data:
            self.id_edit.setText(data.get("id", ""))
            self.label_edit.setText(data.get("label", ""))
            t = data.get("type", "text")
            if t in PARAM_TYPES:
                self.type_combo.setCurrentText(t)
            self.placeholder_edit.setText(data.get("placeholder", ""))
            self.required_cb.setChecked(data.get("required", False))

    def _remove(self):
        self.setParent(None)
        self.deleteLater()

    def to_dict(self) -> dict:
        return {
            "id": self.id_edit.text().strip(),
            "label": self.label_edit.text().strip(),
            "type": self.type_combo.currentText(),
            "placeholder": self.placeholder_edit.text().strip(),
            "required": self.required_cb.isChecked(),
            "icon": "ti-settings",
        }


class WizardDialog(QDialog):
    def __init__(self, tools_dir: Path, parent=None, edit_tool=None):
        """
        edit_tool: ToolDefinition to edit, or None for create mode.
        """
        super().__init__(parent)
        self.tools_dir = tools_dir
        self.edit_tool = edit_tool
        self.script_path: Path | None = None
        self._edit_mode = edit_tool is not None

        title = f"Edit tool — {edit_tool.name}" if self._edit_mode else "Add new tool"
        self.setWindowTitle(title)
        self.setMinimumWidth(720)
        self._build_ui()

        if self._edit_mode:
            self._prefill(edit_tool)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(20, 20, 20, 20)

        root.addWidget(QLabel("<b>Tool metadata</b>"))

        meta_box = QGroupBox()
        meta_lay = QVBoxLayout(meta_box)
        meta_lay.setSpacing(8)

        def row(label, widget):
            h = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(120)
            h.addWidget(lbl)
            h.addWidget(widget)
            meta_lay.addLayout(h)

        self.name_edit = QLineEdit(placeholderText="e.g. My Scraper")
        self.desc_edit = QLineEdit(placeholderText="One-line description")
        self.folder_edit = QLineEdit(placeholderText="e.g. my_scraper (no spaces)")

        self.icon_combo = QComboBox()
        self.icon_combo.addItems(ICONS)
        self.long_cb = QCheckBox("Long-running (shows active progress bar)")

        row("Display name *", self.name_edit)
        row("Description *", self.desc_edit)

        if self._edit_mode:
            # Folder is locked in edit mode -- renaming a tool folder is
            # more trouble than it's worth (breaks cached panels, etc.)
            self.folder_edit.setReadOnly(True)
            self.folder_edit.setToolTip("Folder name cannot be changed after creation.")
            folder_note = QLabel("Folder name (locked)")
        else:
            folder_note = QLabel("Folder name *")
        row(folder_note.text(), self.folder_edit)

        row("Icon", self.icon_combo)
        meta_lay.addWidget(self.long_cb)

        # Script row
        script_h = QHBoxLayout()
        script_lbl = QLabel("Script file" + (" *" if not self._edit_mode else ""))
        script_lbl.setFixedWidth(120)
        self.script_edit = QLineEdit(
            readOnly=True,
            placeholderText="Select .py file..." if not self._edit_mode else "Leave blank to keep existing script",
        )
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_script)
        script_h.addWidget(script_lbl)
        script_h.addWidget(self.script_edit)
        script_h.addWidget(browse_btn)
        meta_lay.addLayout(script_h)

        root.addWidget(meta_box)

        root.addWidget(QLabel("<b>Parameters</b>"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(200)
        self.params_widget = QWidget()
        self.params_layout = QVBoxLayout(self.params_widget)
        self.params_layout.setAlignment(Qt.AlignTop)
        self.params_layout.setSpacing(4)
        scroll.setWidget(self.params_widget)
        root.addWidget(scroll)

        add_param_btn = QPushButton("+ Add parameter")
        add_param_btn.clicked.connect(self._add_param)
        root.addWidget(add_param_btn)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        label = "Save changes" if self._edit_mode else "Create tool"
        self.create_btn = QPushButton(label)
        self.create_btn.setDefault(True)
        self.create_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.create_btn)
        root.addLayout(btn_row)

    def _prefill(self, tool):
        """Populate all fields from existing ToolDefinition."""
        self.name_edit.setText(tool.name)
        self.desc_edit.setText(tool.description)
        self.folder_edit.setText(tool.folder.name)

        if tool.icon in ICONS:
            self.icon_combo.setCurrentText(tool.icon)
        self.long_cb.setChecked(tool.long_running)

        # Show existing script name (read-only display)
        self.script_edit.setText(tool.script_path.name)
        # Keep a reference to the existing script so we don't require re-selection
        self.script_path = tool.script_path

        # Pre-fill param rows
        for param in tool.params:
            row = ParamRow(data={
                "id": param.id,
                "label": param.label,
                "type": param.type,
                "placeholder": param.placeholder,
                "required": param.required,
            })
            self.params_layout.addWidget(row)

    def _browse_script(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select script", "", "Python files (*.py)")
        if path:
            self.script_path = Path(path)
            self.script_edit.setText(path)
            if not self._edit_mode and not self.folder_edit.text():
                self.folder_edit.setText(self.script_path.stem.lower().replace(" ", "_"))

    def _add_param(self):
        self.params_layout.addWidget(ParamRow())

    def _save(self):
        name = self.name_edit.text().strip()
        desc = self.desc_edit.text().strip()
        folder = self.folder_edit.text().strip()

        if not name or not desc or not folder:
            QMessageBox.warning(self, "Missing fields", "Name, description, and folder are all required.")
            return

        if not self._edit_mode and not self.script_path:
            QMessageBox.warning(self, "Missing fields", "Please select a script file.")
            return

        params = []
        for i in range(self.params_layout.count()):
            w = self.params_layout.itemAt(i).widget()
            if isinstance(w, ParamRow):
                d = w.to_dict()
                if d["id"] and d["label"]:
                    params.append(d)

        toml = generate_toml(
            name=name,
            description=desc,
            icon=self.icon_combo.currentText(),
            script_filename=self.script_path.name if self.script_path else "",
            long_running=self.long_cb.isChecked(),
            params=params,
        )

        if self._edit_mode:
            # Overwrite the existing tool.toml in place
            toml_path = self.edit_tool.folder / "tool.toml"
            toml_path.write_text(toml, encoding="utf-8")
            # If user picked a new script, copy it over
            if self.script_path and self.script_path != self.edit_tool.script_path:
                shutil.copy2(self.script_path, self.edit_tool.folder / self.script_path.name)
        else:
            write_tool(self.tools_dir, folder, toml, self.script_path)

        self.accept()

from __future__ import annotations
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFileDialog, QCheckBox, QScrollArea,
    QWidget, QMessageBox, QSpinBox, QTabWidget, QTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

from core.tool_loader import ToolDefinition
from core.wizard import PARAM_TYPES, ICONS, generate_toml, write_tool


class ParameterEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.params = []
        self._build_ui()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.add_param_btn = QPushButton("+ Add Parameter")
        self.add_param_btn.clicked.connect(self._add_param)
        self.layout.addWidget(self.add_param_btn)
        self.layout.addStretch()

    def _add_param(self):
        param_widget = ParameterWidget(len(self.params), self._remove_param)
        self.layout.insertWidget(self.layout.count() - 1, param_widget)
        self.params.append(param_widget)

    def _remove_param(self, index: int):
        if 0 <= index < len(self.params):
            widget = self.params.pop(index)
            widget.setParent(None)
            # Re-index remaining params
            for i, param in enumerate(self.params):
                param.set_index(i)

    def get_params(self) -> list[dict]:
        return [p.get_data() for p in self.params]


class ParameterWidget(QWidget):
    def __init__(self, index: int, on_remove_callback, parent=None):
        super().__init__(parent)
        self.index = index
        self.on_remove_callback = on_remove_callback
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        header = QHBoxLayout()
        title_label = QLabel(f"Parameter #{self.index + 1}")
        title_label.setFont(QFont("Arial", 11, QFont.Bold))
        header.addWidget(title_label)
        header.addStretch()
        remove_btn = QPushButton("Remove")
        remove_btn.setMaximumWidth(80)
        remove_btn.setStyleSheet("background: #E24B4A; color: white; border: none; border-radius: 4px; padding: 4px;")
        remove_btn.clicked.connect(lambda: self.on_remove_callback(self.index))
        header.addWidget(remove_btn)
        lay.addLayout(header)

        # Param ID
        id_lay = QHBoxLayout()
        id_label = QLabel("Parameter ID:")
        id_label.setStyleSheet("font-weight: bold;")
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("e.g., input_file (use underscores)")
        self.id_input.setToolTip("Unique identifier used as --param_id in scripts")
        id_lay.addWidget(id_label)
        id_lay.addWidget(self.id_input)
        lay.addLayout(id_lay)

        # Label
        label_lay = QHBoxLayout()
        label_label = QLabel("Display Label:")
        label_label.setStyleSheet("font-weight: bold;")
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("e.g., Input File")
        label_lay.addWidget(label_label)
        label_lay.addWidget(self.label_input)
        lay.addLayout(label_lay)

        # Type
        type_lay = QHBoxLayout()
        type_label = QLabel("Type:")
        type_label.setStyleSheet("font-weight: bold;")
        self.type_combo = QComboBox()
        self.type_combo.addItems(PARAM_TYPES)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        type_lay.addWidget(type_label)
        type_lay.addWidget(self.type_combo)
        lay.addLayout(type_lay)

        # Placeholder
        placeholder_lay = QHBoxLayout()
        placeholder_label = QLabel("Placeholder:")
        placeholder_label.setStyleSheet("font-weight: bold;")
        self.placeholder_input = QLineEdit()
        self.placeholder_input.setPlaceholderText("Optional hint text")
        placeholder_lay.addWidget(placeholder_label)
        placeholder_lay.addWidget(self.placeholder_input)
        lay.addLayout(placeholder_lay)

        # Icon
        icon_lay = QHBoxLayout()
        icon_label = QLabel("Icon:")
        icon_label.setStyleSheet("font-weight: bold;")
        self.icon_combo = QComboBox()
        self.icon_combo.addItems(ICONS)
        icon_lay.addWidget(icon_label)
        icon_lay.addWidget(self.icon_combo)
        lay.addLayout(icon_lay)

        # Required
        self.required_check = QCheckBox("Required parameter")
        lay.addWidget(self.required_check)

        # Options (for dropdowns)
        self.options_lay = QHBoxLayout()
        options_label = QLabel("Options (comma-separated):")
        options_label.setStyleSheet("font-weight: bold;")
        self.options_input = QLineEdit()
        self.options_input.setPlaceholderText("e.g., option1, option2, option3")
        self.options_input.setVisible(False)
        self.options_lay.addWidget(options_label)
        self.options_lay.addWidget(self.options_input)
        lay.addLayout(self.options_lay)

        # Default
        default_lay = QHBoxLayout()
        default_label = QLabel("Default Value:")
        default_label.setStyleSheet("font-weight: bold;")
        self.default_input = QLineEdit()
        self.default_input.setPlaceholderText("Optional default value")
        default_lay.addWidget(default_label)
        default_lay.addWidget(self.default_input)
        lay.addLayout(default_lay)

        lay.addSpacing(10)
        sep = QWidget()
        sep.setStyleSheet("background: #3D3D3D; min-height: 1px;")
        lay.addWidget(sep)

    def _on_type_changed(self, type_name: str):
        self.options_input.setVisible(type_name == "dropdown")

    def set_index(self, index: int):
        self.index = index

    def get_data(self) -> dict:
        return {
            "id": self.id_input.text().strip(),
            "label": self.label_input.text().strip(),
            "type": self.type_combo.currentText(),
            "placeholder": self.placeholder_input.text().strip(),
            "icon": self.icon_combo.currentText(),
            "required": self.required_check.isChecked(),
            "options": [o.strip() for o in self.options_input.text().split(",") if o.strip()],
            "default": self.default_input.text().strip(),
        }


class WizardDialog(QDialog):
    def __init__(self, tools_dir: Path, parent=None, edit_tool: ToolDefinition | None = None):
        super().__init__(parent)
        self.tools_dir = tools_dir
        self.edit_tool = edit_tool
        self.selected_script = None
        
        if edit_tool:
            self.setWindowTitle(f"Edit Tool: {edit_tool.name}")
        else:
            self.setWindowTitle("Create New Tool")
        
        self.setMinimumWidth(600)
        self._build_ui()
        
        if edit_tool:
            self._load_tool_data(edit_tool)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Title
        title = QLabel("Tool Configuration Wizard" if not self.edit_tool else "Edit Tool")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Create a powerful tool by configuring its metadata and parameters. "
            "Each parameter becomes a field in the tool's UI."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888888; font-size: 12px;")
        layout.addWidget(desc)

        # Tool Info Tab
        tabs = QTabWidget()
        
        # Basic Info
        basic_widget = QWidget()
        basic_lay = QVBoxLayout(basic_widget)
        basic_lay.setSpacing(10)

        # Tool Name
        name_lay = QHBoxLayout()
        name_label = QLabel("Tool Name:")
        name_label.setStyleSheet("font-weight: bold; min-width: 120px;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., My Awesome Tool")
        self.name_input.setToolTip("The name displayed in the sidebar")
        name_lay.addWidget(name_label)
        name_lay.addWidget(self.name_input)
        basic_lay.addLayout(name_lay)

        # Description
        desc_lay = QVBoxLayout()
        desc_label = QLabel("Description:")
        desc_label.setStyleSheet("font-weight: bold;")
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("One-line description of what this tool does")
        self.desc_input.setMaximumHeight(60)
        self.desc_input.setToolTip("Brief description shown in the UI")
        desc_lay.addWidget(desc_label)
        desc_lay.addWidget(self.desc_input)
        basic_lay.addLayout(desc_lay)

        # Icon
        icon_lay = QHBoxLayout()
        icon_label = QLabel("Icon:")
        icon_label.setStyleSheet("font-weight: bold; min-width: 120px;")
        self.icon_combo = QComboBox()
        self.icon_combo.addItems(ICONS)
        icon_lay.addWidget(icon_label)
        icon_lay.addWidget(self.icon_combo)
        basic_lay.addLayout(icon_lay)

        # Script File
        script_lay = QHBoxLayout()
        script_label = QLabel("Script File:")
        script_label.setStyleSheet("font-weight: bold; min-width: 120px;")
        self.script_input = QLineEdit()
        self.script_input.setReadOnly(True)
        self.script_input.setPlaceholderText("Click Browse to select your Python script")
        browse_btn = QPushButton("Browse...")
        browse_btn.setMaximumWidth(100)
        browse_btn.clicked.connect(self._select_script)
        script_lay.addWidget(script_label)
        script_lay.addWidget(self.script_input)
        script_lay.addWidget(browse_btn)
        basic_lay.addLayout(script_lay)

        # Long Running
        self.long_running_check = QCheckBox("This tool runs for a long time (show progress bar)")
        basic_lay.addWidget(self.long_running_check)

        basic_lay.addStretch()
        tabs.addTab(basic_widget, "Basic Info")

        # Parameters Tab
        param_widget = QWidget()
        param_lay = QVBoxLayout(param_widget)
        
        param_info = QLabel("Define input parameters for your tool. Each will become a field in the UI.")
        param_info.setWordWrap(True)
        param_info.setStyleSheet("color: #888888; font-size: 11px;")
        param_lay.addWidget(param_info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.param_editor = ParameterEditor()
        scroll.setWidget(self.param_editor)
        param_lay.addWidget(scroll)
        
        tabs.addTab(param_widget, "Parameters")

        layout.addWidget(tabs)

        # Buttons
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        btn_lay.addWidget(cancel_btn)
        
        create_btn = QPushButton("Create Tool" if not self.edit_tool else "Update Tool")
        create_btn.setMinimumWidth(100)
        create_btn.setStyleSheet("background: #534AB7; color: white; border: none; border-radius: 4px; font-weight: bold;")
        create_btn.clicked.connect(self._create_tool)
        btn_lay.addWidget(create_btn)
        
        layout.addLayout(btn_lay)

    def _select_script(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Python Script",
            "",
            "Python Files (*.py);;All Files (*)"
        )
        if file_path:
            self.selected_script = Path(file_path)
            self.script_input.setText(self.selected_script.name)

    def _load_tool_data(self, tool: ToolDefinition):
        self.name_input.setText(tool.name)
        self.desc_input.setText(tool.description)
        self.icon_combo.setCurrentText(tool.icon)
        self.script_input.setText(tool.script_path.name)
        self.long_running_check.setChecked(tool.long_running)
        
        for param in tool.params:
            self.param_editor._add_param()
            param_widget = self.param_editor.params[-1]
            param_widget.id_input.setText(param.id)
            param_widget.label_input.setText(param.label)
            param_widget.type_combo.setCurrentText(param.type)
            param_widget.placeholder_input.setText(param.placeholder)
            param_widget.icon_combo.setCurrentText(param.icon)
            param_widget.required_check.setChecked(param.required)
            param_widget.options_input.setText(", ".join(param.options))
            param_widget.default_input.setText(param.default)
            param_widget._on_type_changed(param.type)

    def _create_tool(self):
        # Validation
        errors = []
        
        if not self.name_input.text().strip():
            errors.append("Tool name is required")
        if not self.desc_input.toPlainText().strip():
            errors.append("Description is required")
        
        if self.edit_tool:
            if not self.selected_script and not self.edit_tool.script_path.exists():
                errors.append("Script file is required")
        else:
            if not self.selected_script:
                errors.append("You must select a script file")

        # Validate parameters
        for i, param_widget in enumerate(self.param_editor.params):
            data = param_widget.get_data()
            if not data["id"].replace("_", "").isalnum():
                errors.append(f"Parameter #{i+1}: ID must be alphanumeric with underscores")
            if not data["label"]:
                errors.append(f"Parameter #{i+1}: Label is required")
            if data["type"] == "dropdown" and not data["options"]:
                errors.append(f"Parameter #{i+1}: Dropdown must have options")

        if errors:
            QMessageBox.warning(self, "Validation Error", "\n".join(errors))
            return

        # Create tool
        try:
            name = self.name_input.text().strip()
            folder_name = name.lower().replace(" ", "_")
            
            script_path = self.selected_script if self.selected_script else self.edit_tool.script_path
            
            toml_content = generate_toml(
                name=name,
                description=self.desc_input.toPlainText().strip(),
                icon=self.icon_combo.currentText(),
                script_filename=script_path.name,
                long_running=self.long_running_check.isChecked(),
                params=self.param_editor.get_params(),
            )

            if self.edit_tool:
                # Update existing tool
                tool_dir = self.edit_tool.folder
                toml_file = tool_dir / "tool.toml"
                toml_file.write_text(toml_content, encoding="utf-8")
                if self.selected_script:
                    import shutil
                    shutil.copy2(self.selected_script, tool_dir / self.selected_script.name)
            else:
                # Create new tool
                write_tool(self.tools_dir, folder_name, toml_content, script_path)
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create tool:\n{e}")

"""Add/Edit Tool wizard (CTkToplevel modal).

Three steps, matching v2's wizard:
  1. Metadata: name, description, icon, long_running, runtime.
  2. Script selection: pick the .py/.ps1/.bat/.js file to bundle.
  3. Parameter editor: id, label, type, options, default, required.

Validation (unchanged from v2):
- Tool name and description required.
- Script file must be selected.
- Parameter IDs must be alphanumeric + underscores.
- Dropdowns require at least one option.

On save: calls ``core.wizard.write_tool()`` which writes the tool.toml
and copies the script into a new ``tools/<folder>/`` directory, then
``app.reload()`` to make the new tool appear in the sidebar.
"""
from __future__ import annotations

import re
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from core.wizard import ICONS, PARAM_TYPES, generate_toml, write_tool
from ui.script_types import SCRIPT_TYPES, script_language_name

if TYPE_CHECKING:
    from ui.app import App


_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class WizardDialog(ctk.CTkToplevel):
    """Modal Add-Tool wizard. Blocks input to the main window."""

    def __init__(self, master, app: "App", edit_tool_id: Optional[str] = None) -> None:
        super().__init__(master)
        self.app = app
        self.edit_tool_id = edit_tool_id
        self.transient(master)  # stay on top of parent
        self.grab_set()  # modal

        self.title("Edit Tool" if edit_tool_id else "Add New Tool")
        self.geometry("700x720")
        self.minsize(640, 680)

        # Set our custom icon BEFORE CTk's 200ms timer overrides it.
        from ui.window_icon import set_window_icon
        set_window_icon(self)

        self._build()

        # If editing, pre-fill from existing tool.
        if edit_tool_id:
            tool = app.get_tool(edit_tool_id)
            if tool:
                self._prefill(tool)

    # ------------------------------------------------------------------ build
    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self)
        scroll.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        scroll.grid_columnconfigure(1, weight=1)

        row = [0]

        def sep_label(text):
            ctk.CTkLabel(scroll, text=text, font=ctk.CTkFont(size=15, weight="bold")).grid(row=row[0], column=0, columnspan=2, sticky="w", pady=(10, 4))
            row[0] += 1

        def field(label_text):
            ctk.CTkLabel(scroll, text=label_text, anchor="w").grid(row=row[0], column=0, padx=(0, 10), pady=4, sticky="w")
            row[0] += 1

        # ---- Step 1: Metadata
        sep_label("1. Tool metadata")

        field("Name *")
        self.name_var = ctk.StringVar()
        ctk.CTkEntry(scroll, textvariable=self.name_var).grid(row=row[0]-1, column=1, sticky="ew", pady=4)

        field("Description *")
        self.desc_var = ctk.StringVar()
        ctk.CTkEntry(scroll, textvariable=self.desc_var).grid(row=row[0]-1, column=1, sticky="ew", pady=4)

        field("Icon")
        self.icon_var = ctk.StringVar(value="ti-tool")
        icon_row = ctk.CTkFrame(scroll, fg_color="transparent")
        icon_row.grid(row=row[0]-1, column=1, sticky="ew", pady=4)
        icon_row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(icon_row, textvariable=self.icon_var).grid(row=0, column=0, sticky="ew")
        # Quick-pick common icons
        ctk.CTkOptionMenu(icon_row, values=ICONS[:10], width=120, command=lambda v: self.icon_var.set(v)).grid(row=0, column=1, padx=(6, 0))

        field("Long-running")
        self.long_running_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(scroll, text="Show active progress bar", variable=self.long_running_var).grid(row=row[0]-1, column=1, sticky="w", pady=4)

        field("Runtime override")
        self.runtime_var = ctk.StringVar(value="")
        runtime_row = ctk.CTkFrame(scroll, fg_color="transparent")
        runtime_row.grid(row=row[0]-1, column=1, sticky="ew", pady=4)
        runtime_row.grid_columnconfigure(0, weight=1)
        ctk.CTkOptionMenu(
            runtime_row,
            values=["(auto-detect)", "python", "pwsh", "powershell", "cmd", "node"],
            variable=self.runtime_var,
            width=160,
        ).grid(row=0, column=0, sticky="w")
        # Hint label updated when a script is picked — shows the detected
        # language so the user knows the override is optional.
        self.runtime_hint = ctk.CTkLabel(runtime_row, text="Pick a script first to auto-detect", text_color="gray60", font=ctk.CTkFont(size=11))
        self.runtime_hint.grid(row=0, column=1, padx=(12, 0), sticky="w")

        field("Category")
        self.category_var = ctk.StringVar()
        category_row = ctk.CTkFrame(scroll, fg_color="transparent")
        category_row.grid(row=row[0]-1, column=1, sticky="ew", pady=4)
        category_row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(category_row, textvariable=self.category_var, placeholder_text="e.g., File Utilities").grid(row=0, column=0, sticky="ew")
        # Quick-pick common categories
        ctk.CTkOptionMenu(category_row, values=["File Utilities", "Text Processing", "Data Processing", "Image Processing", "System", "Network"], width=140, command=lambda v: self.category_var.set(v)).grid(row=0, column=1, padx=(6, 0))

        field("Tags (comma-separated)")
        self.tags_var = ctk.StringVar()
        ctk.CTkEntry(scroll, textvariable=self.tags_var, placeholder_text="e.g., batch, automation").grid(row=row[0]-1, column=1, sticky="ew", pady=4)

        # ---- Step 2: Script
        sep_label("2. Script file")
        field("Script *")
        script_row = ctk.CTkFrame(scroll, fg_color="transparent")
        script_row.grid(row=row[0]-1, column=1, sticky="ew", pady=4)
        script_row.grid_columnconfigure(0, weight=1)
        self.script_path_var = ctk.StringVar()
        self.script_path_var.trace_add("write", self._on_script_change)
        ctk.CTkEntry(script_row, textvariable=self.script_path_var, state="readonly").grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(script_row, text="Browse...", width=90, command=self._pick_script).grid(row=0, column=1, padx=(6, 0))

        # Language info panel — shows the detected language + a minimal
        # stdout-protocol code snippet so the user knows how to write a
        # compatible script in that language.
        self.lang_info = ctk.CTkFrame(scroll, fg_color=("gray92", "gray18"), corner_radius=6)
        self.lang_info.grid(row=row[0], column=0, columnspan=2, sticky="ew", pady=(4, 8))
        self.lang_info.grid_columnconfigure(0, weight=1)
        self.lang_info_label = ctk.CTkLabel(self.lang_info, text="", anchor="w", justify="left", font=ctk.CTkFont(size=11))
        self.lang_info_label.grid(row=0, column=0, padx=12, pady=8, sticky="w")
        row[0] += 1

        # ---- Step 3: Parameters
        sep_label("3. Parameters")
        ctk.CTkLabel(scroll, text="Add one row per parameter the script accepts.", text_color="gray60").grid(row=row[0], column=0, columnspan=2, sticky="w", pady=(0, 6))
        row[0] += 1

        self.params_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.params_frame.grid(row=row[0], column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.params_frame.grid_columnconfigure(0, weight=1)
        row[0] += 1

        ctk.CTkButton(scroll, text="+ Add parameter", command=self._add_param_row, fg_color="transparent", border_width=1).grid(row=row[0], column=0, columnspan=2, pady=(0, 12), sticky="w")
        row[0] += 1

        # Pre-seed one empty param row so the user sees the layout.
        self._param_rows: list[_ParamRow] = []
        self._add_param_row()

        # ---- Save / Cancel
        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.grid(row=row[0], column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ctk.CTkButton(btn_row, text="Cancel", width=90, fg_color="transparent", border_width=1, command=self.destroy).pack(side="right", padx=(6, 0))
        ctk.CTkButton(btn_row, text="Save tool", width=110, command=self._on_save, fg_color="#16a34a", hover_color="#15803d").pack(side="right")

    # ------------------------------------------------------------------ param rows
    def _add_param_row(self, prefill: dict | None = None) -> None:
        idx = len(self._param_rows)
        row = _ParamRow(self.params_frame, idx, self._remove_param_row, prefill)
        row.grid(row=idx, column=0, sticky="ew", pady=2)
        self._param_rows.append(row)

    def _remove_param_row(self, idx: int) -> None:
        if len(self._param_rows) <= 1:
            return  # keep at least one row
        row = self._param_rows.pop(idx)
        row.destroy()
        # Re-index remaining rows
        for i, r in enumerate(self._param_rows):
            r.index = i
            r.grid(row=i, column=0, sticky="ew", pady=2)

    # ------------------------------------------------------------------ actions
    def _pick_script(self) -> None:
        path = filedialog.askopenfilename(
            title="Select script",
            filetypes=[
                ("All supported scripts", "*.py *.ps1 *.bat *.cmd *.js"),
                ("Python", "*.py"),
                ("PowerShell", "*.ps1"),
                ("Batch", "*.bat *.cmd"),
                ("JavaScript", "*.js"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.script_path_var.set(path)
            # Auto-derive a name from the script if name is empty
            if not self.name_var.get().strip():
                stem = Path(path).stem.replace("_", " ").replace("-", " ").title()
                self.name_var.set(stem)

    def _on_script_change(self, *_args) -> None:
        """Called when the script path changes. Updates the runtime hint
        and the language info panel with a per-language code snippet
        showing the stdout protocol (PROGRESS:N, [OK], [WARN], [ERROR])."""
        path = self.script_path_var.get().strip()
        if not path:
            self.runtime_hint.configure(text="Pick a script first to auto-detect")
            self.lang_info_label.configure(text="")
            return

        suffix = Path(path).suffix.lower()
        lang = script_language_name(Path(path))
        info = SCRIPT_TYPES.get(suffix)

        if info is None:
            self.runtime_hint.configure(text=f"Unknown extension {suffix!r} — set runtime override", text_color="#eab308")
            self.lang_info_label.configure(text="")
            return

        self.runtime_hint.configure(text=f"Auto-detected: {lang} (override optional)", text_color="#22c55e")
        snippet = _LANG_SNIPPETS.get(suffix, "")
        self.lang_info_label.configure(text=snippet)

    def _prefill(self, tool) -> None:
        self.name_var.set(tool.name)
        self.desc_var.set(tool.description)
        self.icon_var.set(tool.icon)
        self.long_running_var.set(bool(tool.long_running))
        self.runtime_var.set(tool.runtime or "(auto-detect)")
        self.category_var.set(tool.category)
        self.tags_var.set(", ".join(tool.tags))
        # Script path: we can't easily resolve the original; use the
        # in-place script_path so user can see what's there.
        self.script_path_var.set(str(tool.script_path))
        # Clear the seeded empty row and rebuild from tool.params
        for r in self._param_rows:
            r.destroy()
        self._param_rows = []
        for p in tool.params:
            self._add_param_row({
                "id": p.id,
                "label": p.label,
                "type": p.type,
                "placeholder": p.placeholder,
                "required": p.required,
                "options": p.options,
                "default": p.default,
            })

    def _on_save(self) -> None:
        # Validate
        name = self.name_var.get().strip()
        desc = self.desc_var.get().strip()
        script_path_str = self.script_path_var.get().strip()
        icon = self.icon_var.get().strip() or "ti-tool"

        if not name:
            messagebox.showerror("Validation", "Tool name is required.", parent=self)
            return
        if not desc:
            messagebox.showerror("Validation", "Description is required.", parent=self)
            return
        if not script_path_str:
            messagebox.showerror("Validation", "Script file is required.", parent=self)
            return
        script_path = Path(script_path_str)
        if not script_path.exists():
            messagebox.showerror("Validation", f"Script file not found:\n{script_path}", parent=self)
            return

        # Validate param rows
        params: list[dict] = []
        seen_ids: set[str] = set()
        for i, prow in enumerate(self._param_rows):
            pdata = prow.collect()
            if pdata is None:
                # empty row, skip silently
                continue
            pid = pdata["id"]
            if not _ID_RE.match(pid):
                messagebox.showerror("Validation", f"Parameter {i+1}: ID must be alphanumeric + underscore, starting with a letter or underscore.", parent=self)
                return
            if pid in seen_ids:
                messagebox.showerror("Validation", f"Parameter {i+1}: duplicate ID '{pid}'. Each parameter must have a unique ID.", parent=self)
                return
            seen_ids.add(pid)
            if pdata["type"] == "dropdown" and not pdata.get("options"):
                messagebox.showerror("Validation", f"Parameter {pid}: dropdown type requires at least one option.", parent=self)
                return
            params.append(pdata)

        # Folder name: slugify name; if editing, reuse existing folder name.
        if self.edit_tool_id:
            folder_name = self.edit_tool_id
        else:
            folder_name = _slugify(name)
            # Avoid collision
            base = folder_name
            n = 2
            while (self.app.tools_dir / folder_name).exists():
                folder_name = f"{base}_{n}"
                n += 1

        runtime_val = self.runtime_var.get().strip().lower()
        if runtime_val in ("", "(auto-detect)", "auto-detect", "auto"):
            runtime_val = ""

        category_val = self.category_var.get().strip()
        tags_raw = self.tags_var.get().strip()
        tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

        toml = generate_toml(
            name=name,
            description=desc,
            icon=icon,
            script_filename=script_path.name,
            long_running=bool(self.long_running_var.get()),
            params=params,
            runtime=runtime_val,
            category=category_val,
            tags=tags_list,
        )

        try:
            write_tool(self.app.tools_dir, folder_name, toml, script_source=script_path)
        except Exception as e:
            messagebox.showerror("Save failed", str(e), parent=self)
            return

        self.app.reload()
        self.app.sidebar.select_by_id(folder_name)
        self.destroy()


# =========================================================================== param row
class _ParamRow(ctk.CTkFrame):
    """One parameter row in the wizard's step 3."""

    def __init__(self, master, index: int, on_remove, prefill: dict | None = None) -> None:
        super().__init__(master, fg_color=("gray92", "gray18"), corner_radius=6)
        self.index = index
        self.grid_columnconfigure(1, weight=1)

        # Row 1: id, label, type, remove button
        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.grid(row=0, column=0, columnspan=2, padx=8, pady=(8, 4), sticky="ew")
        row1.grid_columnconfigure(1, weight=1)
        row1.grid_columnconfigure(3, weight=1)
        row1.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(row1, text="ID", width=30).grid(row=0, column=0, padx=(0, 4))
        self.id_var = ctk.StringVar(value=prefill.get("id", "") if prefill else "")
        ctk.CTkEntry(row1, textvariable=self.id_var, width=140).grid(row=0, column=1, sticky="ew", padx=(0, 8))

        ctk.CTkLabel(row1, text="Label", width=40).grid(row=0, column=2, padx=(0, 4))
        self.label_var = ctk.StringVar(value=prefill.get("label", "") if prefill else "")
        ctk.CTkEntry(row1, textvariable=self.label_var).grid(row=0, column=3, sticky="ew", padx=(0, 8))

        ctk.CTkLabel(row1, text="Type", width=40).grid(row=0, column=4, padx=(0, 4))
        self.type_var = ctk.StringVar(value=prefill.get("type", "text") if prefill else "text")
        ctk.CTkOptionMenu(row1, values=PARAM_TYPES, variable=self.type_var, width=110).grid(row=0, column=5, sticky="w")

        ctk.CTkButton(row1, text="✕", width=28, fg_color="transparent", hover_color="#dc2626", command=lambda: on_remove(self.index)).grid(row=0, column=6, padx=(8, 0))

        # Row 2: placeholder, default, required, options
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.grid(row=1, column=0, columnspan=2, padx=8, pady=(0, 8), sticky="ew")
        row2.grid_columnconfigure(1, weight=1)
        row2.grid_columnconfigure(3, weight=1)
        row2.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(row2, text="Placeholder", width=70).grid(row=0, column=0, padx=(0, 4))
        self.placeholder_var = ctk.StringVar(value=prefill.get("placeholder", "") if prefill else "")
        ctk.CTkEntry(row2, textvariable=self.placeholder_var).grid(row=0, column=1, sticky="ew", padx=(0, 8))

        ctk.CTkLabel(row2, text="Default", width=50).grid(row=0, column=2, padx=(0, 4))
        self.default_var = ctk.StringVar(value=prefill.get("default", "") if prefill else "")
        ctk.CTkEntry(row2, textvariable=self.default_var).grid(row=0, column=3, sticky="ew", padx=(0, 8))

        ctk.CTkLabel(row2, text="Options (comma)", width=120).grid(row=0, column=4, padx=(0, 4))
        opts = prefill.get("options", []) if prefill else []
        self.options_var = ctk.StringVar(value=", ".join(opts) if isinstance(opts, list) else str(opts))
        ctk.CTkEntry(row2, textvariable=self.options_var).grid(row=0, column=5, sticky="ew")

        self.required_var = ctk.BooleanVar(value=bool(prefill.get("required", False)) if prefill else False)
        ctk.CTkCheckBox(self, text="Required", variable=self.required_var).grid(row=2, column=0, padx=8, pady=(0, 8), sticky="w")

    def collect(self) -> dict | None:
        """Return the row's data as a dict, or ``None`` if the row is
        empty (no id and no label)."""
        pid = self.id_var.get().strip()
        label = self.label_var.get().strip()
        if not pid and not label:
            return None
        opts_str = self.options_var.get().strip()
        options = [o.strip() for o in opts_str.split(",") if o.strip()] if opts_str else []
        return {
            "id": pid or _slugify(label),
            "label": label or pid,
            "type": self.type_var.get().strip() or "text",
            "placeholder": self.placeholder_var.get().strip(),
            "required": bool(self.required_var.get()),
            "options": options,
            "default": self.default_var.get().strip(),
        }


def _slugify(name: str) -> str:
    """Turn a display name into a filesystem-safe folder name."""
    s = re.sub(r"[^A-Za-z0-9_]+", "_", name.strip())
    s = re.sub(r"_+", "_", s).strip("_").lower()
    return s or "tool"


# ---------------------------------------------------------------------------
# Per-language code snippets showing the stdout protocol.
#
# Shown in the wizard's Step 2 info panel when a script is picked, so the
# user knows how to make their script emit progress / colored log lines
# that Tool Pouch will recognize. Each snippet is a minimal "hello world"
# that demonstrates all four protocol tokens (PROGRESS:N, [OK], [WARN],
# [ERROR]) and the --param_id argument convention.
# ---------------------------------------------------------------------------
_LANG_SNIPPETS = {
    ".py": (
        "Python — accept params via argparse, print PROGRESS:N and [OK]/[WARN]/[ERROR] prefixes:\n\n"
        "  import argparse\n"
        "  parser = argparse.ArgumentParser()\n"
        "  parser.add_argument('--input_dir', required=True)\n"
        "  args = parser.parse_args()\n"
        "  print('PROGRESS:0', flush=True)\n"
        "  print('[OK] Starting...', flush=True)\n"
        "  print('PROGRESS:100', flush=True)"
    ),
    ".ps1": (
        "PowerShell — accept params via param(), use Write-Output for protocol lines:\n\n"
        "  param([string]$InputDir)\n"
        "  Write-Output 'PROGRESS:0'\n"
        "  Write-Output '[OK] Starting...'\n"
        "  Write-Output 'PROGRESS:100'"
    ),
    ".bat": (
        "Batch — loop to parse --param_id value pairs, use echo for output:\n\n"
        "  @echo off\n"
        "  :parse\n"
        "  if \"%~1\"==\"\" goto run\n"
        "  if /i \"%~1\"==\"--input_dir\" set \"INPUT_DIR=%~2\"\n"
        "  shift & shift & goto parse\n"
        "  :run\n"
        "  echo PROGRESS:0\n"
        "  echo [OK] Starting...\n"
        "  echo PROGRESS:100\n"
        "  exit /b 0"
    ),
    ".cmd": (
        "Batch — same protocol as .bat:\n\n"
        "  @echo off\n"
        "  echo PROGRESS:0\n"
        "  echo [OK] Done.\n"
        "  exit /b 0"
    ),
    ".js": (
        "JavaScript — parse process.argv, use console.log for protocol lines:\n\n"
        "  function parseArgs(argv) {\n"
        "    const p = {};\n"
        "    for (let i = 2; i < argv.length; i += 2)\n"
        "      p[argv[i].replace(/^--/, '')] = argv[i+1] || '';\n"
        "    return p;\n"
        "  }\n"
        "  const args = parseArgs(process.argv);\n"
        "  console.log('PROGRESS:0');\n"
        "  console.log('[OK] Starting...');\n"
        "  console.log('PROGRESS:100');"
    ),
}

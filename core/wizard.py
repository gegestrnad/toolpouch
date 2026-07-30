"""TOML generator + tool-folder writer for the Add/Edit Tool wizard.

Ported VERBATIM from v2 — the spec §5 says "port wizard as
``CTkToplevel`` modal with the same dynamic parameter-row editing", which
means the underlying TOML generator and writer logic is unchanged; only
the UI shell above it changes (PySide6 → CustomTkinter).

Additions:
- ``runtime`` field is now written when set (spec §2 manifest schema).
- ``ecosystem`` is now written on each ``[[dependencies]]`` entry.
"""
from __future__ import annotations

from pathlib import Path


PARAM_TYPES = ["text", "folder", "folders", "file", "files", "save", "dropdown"]

ICONS = [
    "ti-tool", "ti-file", "ti-folder", "ti-world-download", "ti-language",
    "ti-file-type-pdf", "ti-eraser", "ti-replace", "ti-file-type-html",
    "ti-download", "ti-upload", "ti-settings", "ti-link", "ti-search",
    "ti-file-zip", "ti-file-export", "ti-regex", "ti-chart-bar",
]


def _escape_toml_string(s: str) -> str:
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    s = s.replace("\t", "\\t")
    return s


def generate_toml(
    name: str,
    description: str,
    icon: str,
    script_filename: str,
    long_running: bool,
    params: list[dict],
    runtime: str = "",
    dependencies: list[dict] | None = None,
) -> str:
    name = _escape_toml_string(name)
    description = _escape_toml_string(description)

    lines = [
        "[tool]",
        f'name = "{name}"',
        f'description = "{description}"',
        f'icon = "{icon}"',
        f'script = "{_escape_toml_string(script_filename)}"',
        f"long_running = {'true' if long_running else 'false'}",
    ]
    if runtime and runtime in {"python", "pwsh", "powershell", "cmd", "node"}:
        lines.append(f'runtime = "{runtime}"')
    lines.append("")

    for p in params:
        lines.append("[[params]]")
        lines.append(f'id = "{_escape_toml_string(p["id"])}"')
        lines.append(f'label = "{_escape_toml_string(p["label"])}"')
        lines.append(f'type = "{p["type"]}"')
        if p.get("placeholder"):
            lines.append(f'placeholder = "{_escape_toml_string(p["placeholder"])}"')
        if p.get("required"):
            lines.append("required = true")
        if p.get("icon"):
            lines.append(f'icon = "{p["icon"]}"')
        if p.get("filter"):
            lines.append(f'filter = "{_escape_toml_string(p["filter"])}"')
        if p.get("options"):
            opts = ", ".join(f'"{_escape_toml_string(o)}"' for o in p["options"])
            lines.append(f"options = [{opts}]")
        if p.get("default"):
            lines.append(f'default = "{_escape_toml_string(p["default"])}"')
        lines.append("")

    if dependencies:
        for d in dependencies:
            import_name = d.get("import", "").strip()
            if not import_name:
                continue
            lines.append("[[dependencies]]")
            lines.append(f'import = "{_escape_toml_string(import_name)}"')
            if d.get("package"):
                lines.append(f'package = "{_escape_toml_string(d["package"])}"')
            if d.get("version"):
                lines.append(f'version = "{_escape_toml_string(d["version"])}"')
            ecosystem = d.get("ecosystem", "python").strip().lower() or "python"
            if ecosystem not in {"python", "node", "powershell", "none"}:
                ecosystem = "python"
            lines.append(f'ecosystem = "{ecosystem}"')
            if d.get("notes"):
                lines.append(f'notes = "{_escape_toml_string(d["notes"])}"')
            lines.append("")

    return "\n".join(lines)


def write_tool(
    tools_dir: Path,
    folder_name: str,
    toml_content: str,
    script_source: Path | None = None,
) -> Path:
    import shutil

    tool_dir = tools_dir / folder_name
    tool_dir.mkdir(parents=True, exist_ok=True)

    toml_path = tool_dir / "tool.toml"
    toml_path.write_text(toml_content, encoding="utf-8")

    if script_source and script_source.exists():
        shutil.copy2(script_source, tool_dir / script_source.name)

    return tool_dir

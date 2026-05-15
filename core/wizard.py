from __future__ import annotations
from pathlib import Path


PARAM_TYPES = ["text", "folder", "file", "save", "dropdown"]

ICONS = [
    "ti-tool", "ti-file", "ti-folder", "ti-world-download", "ti-language",
    "ti-file-type-pdf", "ti-eraser", "ti-replace", "ti-file-type-html",
    "ti-download", "ti-upload", "ti-settings", "ti-link", "ti-search",
    "ti-file-zip", "ti-file-export", "ti-regex", "ti-chart-bar",
]


def generate_toml(
    name: str,
    description: str,
    icon: str,
    script_filename: str,
    long_running: bool,
    params: list[dict],
) -> str:
    lines = [
        "[tool]",
        f'name = "{name}"',
        f'description = "{description}"',
        f'icon = "{icon}"',
        f'script = "{script_filename}"',
        f"long_running = {'true' if long_running else 'false'}",
        "",
    ]

    for p in params:
        lines.append("[[params]]")
        lines.append(f'id = "{p["id"]}"')
        lines.append(f'label = "{p["label"]}"')
        lines.append(f'type = "{p["type"]}"')
        if p.get("placeholder"):
            lines.append(f'placeholder = "{p["placeholder"]}"')
        if p.get("required"):
            lines.append(f'required = true')
        if p.get("icon"):
            lines.append(f'icon = "{p["icon"]}"')
        if p.get("filter"):
            lines.append(f'filter = "{p["filter"]}"')
        if p.get("options"):
            opts = ", ".join(f'"{o}"' for o in p["options"])
            lines.append(f"options = [{opts}]")
        if p.get("default"):
            lines.append(f'default = "{p["default"]}"')
        lines.append("")

    return "\n".join(lines)


def write_tool(
    tools_dir: Path,
    folder_name: str,
    toml_content: str,
    script_source: Path | None = None,
) -> Path:
    tool_dir = tools_dir / folder_name
    tool_dir.mkdir(parents=True, exist_ok=True)

    toml_path = tool_dir / "tool.toml"
    toml_path.write_text(toml_content, encoding="utf-8")

    if script_source and script_source.exists():
        import shutil
        shutil.copy2(script_source, tool_dir / script_source.name)

    return tool_dir

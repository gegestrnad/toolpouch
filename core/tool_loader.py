from __future__ import annotations
import sys
from dataclasses import dataclass, field
from pathlib import Path

# tomllib is stdlib in Python 3.11+; use tomli backport on 3.10
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        raise ImportError(
            "Python 3.10 detected. Please install the 'tomli' backport:\n"
            "    pip install tomli"
        )


@dataclass
class ToolParam:
    id: str
    label: str
    type: str  # text | folder | file | save | dropdown
    placeholder: str = ""
    required: bool = False
    icon: str = "ti-settings"
    filter: str = ""
    options: list[str] = field(default_factory=list)
    default: str = ""


@dataclass
class ToolDefinition:
    name: str
    description: str
    icon: str
    script_path: Path
    long_running: bool
    params: list[ToolParam]
    folder: Path
    script_exists: bool = True
    errors: list[str] = field(default_factory=list)


def load_tools(tools_dir: Path) -> list[ToolDefinition]:
    tools = []

    if not tools_dir.exists():
        return tools

    for tool_folder in sorted(tools_dir.iterdir()):
        if not tool_folder.is_dir():
            continue

        toml_file = tool_folder / "tool.toml"
        if not toml_file.exists():
            continue

        try:
            with open(toml_file, "rb") as f:
                data = tomllib.load(f)

            tool_data = data.get("tool", {})
            params_data = data.get("params", [])

            script_name = tool_data.get("script", "")
            script_path = tool_folder / script_name

            # FIX: Validate script existence
            script_exists = script_path.exists()
            errors = []
            if not script_exists:
                errors.append(f"Script not found: {script_name}")

            params = [
                ToolParam(
                    id=p.get("id", ""),
                    label=p.get("label", ""),
                    type=p.get("type", "text"),
                    placeholder=p.get("placeholder", ""),
                    required=p.get("required", False),
                    icon=p.get("icon", "ti-settings"),
                    filter=p.get("filter", ""),
                    options=p.get("options", []),
                    default=p.get("default", ""),
                )
                for p in params_data
            ]

            tools.append(ToolDefinition(
                name=tool_data.get("name", tool_folder.name),
                description=tool_data.get("description", ""),
                icon=tool_data.get("icon", "ti-tool"),
                script_path=script_path,
                long_running=tool_data.get("long_running", False),
                params=params,
                folder=tool_folder,
                script_exists=script_exists,
                errors=errors,
            ))

        except Exception as e:
            print(f"[ToolLoader] Failed to load {toml_file}: {e}")

    return tools

"""TOML manifest loader.

Ported from v2 with these changes:
- Added ``runtime`` field on ``ToolDefinition`` (spec §2 — optional override
  selecting the interpreter for this tool's script).
- Added ``ecosystem`` field on ``ToolDependency`` (spec §2 — python | node |
  powershell | none, defaults to ``"python"`` if omitted).
- Added **backward-compatible normalization** for the v2 tool.toml files
  that ship in the same Tools/ folder. Specifically tolerates:
    * ``type = "File"`` / ``"Folder"`` / ``"Text"`` / ``"Number"`` /
      ``"Select"`` (capitalized) → mapped to the v3 lowercase vocabulary.
    * ``default_value = "..."`` (used by some v2 manifests) → ``default``.
    * ``options = "a,b,c"`` (comma string) → ``options = ["a","b","c"]``.
    * ``[[dependencies]] id = "Pillow"`` (wrong key) and
      ``min_version = "..."`` → normalized into ``import`` / ``version``.
  This is the spec §2 compatibility bar: every existing ``tool.toml``
  parses without raising.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

# tomllib is stdlib in Python 3.11+; use tomli backport on 3.10
if sys.version_info >= (3, 11):
    import tomllib  # type: ignore[import-not-found]
else:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore[import-not-found]
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "Python 3.10 detected. Please install the 'tomli' backport:\n"
            "    pip install tomli"
        ) from e


# --------------------------------------------------------------------------- types
VALID_PARAM_TYPES = {"text", "folder", "folders", "file", "files", "save", "dropdown"}

# v2 used a mix of capitalized forms — normalize them here so the UI only
# ever sees the canonical lowercase vocabulary from spec §2.
_PARAM_TYPE_ALIASES = {
    "text": "text",
    "string": "text",
    "input": "text",
    "folder": "folder",
    "dir": "folder",
    "directory": "folder",
    "folders": "folders",
    "dirs": "folders",
    "file": "file",
    "files": "files",
    "save": "save",
    "output": "save",
    "dropdown": "dropdown",
    "select": "dropdown",
    "choice": "dropdown",
    "combo": "dropdown",
    # number is not in the v3 vocabulary but some v2 manifests use it;
    # treat as text — the script itself parses the number.
    "number": "text",
    "int": "text",
    "integer": "text",
    "bool": "dropdown",
    "boolean": "dropdown",
}

VALID_RUNTIMES = {"", "python", "pwsh", "powershell", "cmd", "node"}
VALID_ECOSYSTEMS = {"python", "node", "powershell", "none"}


@dataclass
class ToolParam:
    id: str
    label: str
    type: str  # text | folder | folders | file | files | save | dropdown
    placeholder: str = ""
    required: bool = False
    icon: str = "ti-settings"
    filter: str = ""
    options: list[str] = field(default_factory=list)
    default: str = ""


@dataclass
class ToolDependency:
    import_name: str
    package_name: str = ""
    version: str = ""
    notes: str = ""
    ecosystem: str = "python"  # python | node | powershell | none


@dataclass
class ToolDefinition:
    name: str
    description: str
    icon: str
    script_path: Path
    long_running: bool
    params: list[ToolParam]
    folder: Path
    runtime: str = ""  # "" | "python" | "pwsh" | "powershell" | "cmd" | "node"
    dependencies: list[ToolDependency] = field(default_factory=list)
    script_exists: bool = True
    errors: list[str] = field(default_factory=list)
    category: str = ""
    tags: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- helpers
def _normalize_param_type(raw: str) -> str:
    if not isinstance(raw, str):
        return "text"
    key = raw.strip().lower()
    return _PARAM_TYPE_ALIASES.get(key, "text")


def _normalize_options(raw) -> list[str]:
    """Accept either ``["a","b"]`` (list) or ``"a,b,c"`` (comma string).

    Some v2 manifests used the string form; spec §2 mandates the list form.
    """
    if isinstance(raw, list):
        return [str(o).strip() for o in raw if str(o).strip()]
    if isinstance(raw, str):
        return [o.strip() for o in raw.split(",") if o.strip()]
    return []


def _normalize_param(p: dict) -> ToolParam:
    raw_type = p.get("type", "text")
    # ``default`` is the v3 key; some v2 manifests used ``default_value``.
    default = p.get("default", p.get("default_value", ""))
    return ToolParam(
        id=str(p.get("id", "")).strip(),
        label=str(p.get("label", "")).strip(),
        type=_normalize_param_type(raw_type),
        placeholder=str(p.get("placeholder", "")).strip(),
        required=bool(p.get("required", False)),
        icon=str(p.get("icon", "ti-settings")).strip() or "ti-settings",
        filter=str(p.get("filter", "")).strip(),
        options=_normalize_options(p.get("options", [])),
        default=str(default).strip() if default is not None else "",
    )


def _normalize_dependency(d: dict) -> ToolDependency | None:
    """Tolerate all dependency-key variants across v2 and v3:

    Priority for import name (first non-empty wins):
      1. ``import``         — v3 canonical (spec §2)
      2. ``import_name``    — v2 form (e.g. ``import_name = "bs4"``)
      3. ``id``             — broken v2 form (e.g. ``id = "Pillow"``);
                              used as LAST RESORT when neither ``import``
                              nor ``import_name`` is present.

    Priority for package name:
      1. ``package``        — v3 canonical
      2. ``package_name``   — v2 form
      3. fall back to the import name, then to ``id``.

    Priority for version:
      1. ``version``        — v3 canonical
      2. ``min_version``    — v2 form

    Returns ``None`` if no import name can be determined from any key.
    """
    if not isinstance(d, dict):
        return None

    # Import name: check all three keys in priority order.
    import_name = (
        str(d.get("import", "")).strip()
        or str(d.get("import_name", "")).strip()
        or str(d.get("id", "")).strip()
    )
    if not import_name:
        return None

    # Package name: check both keys, fall back to import_name.
    package_name = (
        str(d.get("package", "")).strip()
        or str(d.get("package_name", "")).strip()
    )
    if not package_name:
        # If we fell through to ``id`` for the import name, the package
        # name is also likely the id value (e.g. ``id = "Pillow"``).
        # Otherwise package name defaults to the import name (pip's
        # default convention for most packages).
        package_name = str(d.get("id", "")).strip() or import_name

    version = str(d.get("version", d.get("min_version", ""))).strip()
    notes = str(d.get("notes", "")).strip()
    ecosystem = str(d.get("ecosystem", "python")).strip().lower()
    if ecosystem not in VALID_ECOSYSTEMS:
        ecosystem = "python"
    return ToolDependency(
        import_name=import_name,
        package_name=package_name or import_name,
        version=version,
        notes=notes,
        ecosystem=ecosystem,
    )


# --------------------------------------------------------------------------- public
def load_tools(tools_dir: Path) -> list[ToolDefinition]:
    """Discover every ``<tools_dir>/<tool>/tool.toml`` and parse it.

    Malformed manifests are skipped with a printed warning, NOT raised —
    one bad tool must never break the whole sidebar. (Unchanged from v2.)
    """
    tools: list[ToolDefinition] = []
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
            dependencies_data = data.get("dependencies", [])

            script_name = str(tool_data.get("script", "")).strip()
            script_path = tool_folder / script_name if script_name else tool_folder
            script_exists = bool(script_name) and script_path.exists()
            errors: list[str] = []
            if not script_name:
                errors.append("tool.toml does not define a script file.")
            elif not script_exists:
                errors.append(f"Script not found: {script_name}")

            params = [_normalize_param(p) for p in params_data if isinstance(p, dict)]

            dependencies: list[ToolDependency] = []
            for d in dependencies_data:
                norm = _normalize_dependency(d)
                if norm is not None:
                    dependencies.append(norm)

            runtime = str(tool_data.get("runtime", "")).strip().lower()
            if runtime not in VALID_RUNTIMES:
                # Unknown override → ignore silently, fall back to extension-based
                # resolution in RuntimeResolver. Log nothing — this is benign.
                runtime = ""

            category = str(tool_data.get("category", "")).strip()
            tags_raw = tool_data.get("tags", [])
            if isinstance(tags_raw, str):
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            elif isinstance(tags_raw, list):
                tags = [str(t).strip() for t in tags_raw if str(t).strip()]
            else:
                tags = []

            tools.append(
                ToolDefinition(
                    name=str(tool_data.get("name", tool_folder.name)).strip(),
                    description=str(tool_data.get("description", "")).strip(),
                    icon=str(tool_data.get("icon", "ti-tool")).strip() or "ti-tool",
                    script_path=script_path,
                    long_running=bool(tool_data.get("long_running", False)),
                    params=params,
                    folder=tool_folder,
                    runtime=runtime,
                    dependencies=dependencies,
                    script_exists=script_exists,
                    errors=errors,
                    category=category,
                    tags=tags,
                )
            )
        except Exception as e:
            print(f"[ToolLoader] Failed to load {toml_file}: {e}")

    return tools

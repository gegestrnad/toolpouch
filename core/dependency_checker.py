"""Dependency checker (Python ecosystem).

Ported NEAR-VERBATIM from v2 — this module had zero Qt dependencies in v2
and the spec §6 explicitly says: "port v2's ``ast``-based import scanner
directly (it's already pure Python, this is a straight copy, not a
rewrite)".

The only additions:
- ``DependencyStatus`` gains an ``ecosystem`` field so the multi-ecosystem
  Dependency Manager view can render a single unified table.
- ``dependency_specs_for_tool`` now also exposes ``ecosystem`` from each
  ``ToolDependency`` declared in tool.toml (defaults to ``"python"``).
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from sysconfig import get_paths
from typing import Callable


IMPORT_TO_PACKAGE = {
    "bs4": "beautifulsoup4",
    "cv2": "opencv-python",
    "deep_translator": "deep-translator",
    "fitz": "PyMuPDF",
    "PIL": "pillow",
    "yaml": "PyYAML",
}

AvailabilityChecker = Callable[[str, dict[str, str] | None, str], bool]


@dataclass(frozen=True)
class MissingDependency:
    import_name: str
    package_name: str
    version: str = ""

    @property
    def install_spec(self) -> str:
        return f"{self.package_name}{self.version}" if self.version else self.package_name


@dataclass(frozen=True)
class DependencySpec:
    import_name: str
    package_name: str
    version: str = ""
    notes: str = ""
    source: str = "auto-detected"
    ecosystem: str = "python"

    @property
    def install_spec(self) -> str:
        return f"{self.package_name}{self.version}" if self.version else self.package_name


@dataclass(frozen=True)
class DependencyStatus:
    tool_name: str
    tool_id: str
    import_name: str
    package_name: str
    version: str
    notes: str
    source: str
    status: str
    ecosystem: str = "python"

    @property
    def install_spec(self) -> str:
        return f"{self.package_name}{self.version}" if self.version else self.package_name


def imported_modules_from_script(script_path: str | Path) -> list[str]:
    script = Path(script_path)
    tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
    modules: set[str] = set()

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".", 1)[0]
                if _is_third_party_module(module, script):
                    modules.add(module)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            if not node.module:
                continue
            module = node.module.split(".", 1)[0]
            if _is_third_party_module(module, script):
                modules.add(module)

    return sorted(modules, key=str.casefold)


def dependency_specs_for_tool(tool) -> list[DependencySpec]:
    specs: dict[str, DependencySpec] = {}

    for dependency in getattr(tool, "dependencies", []):
        import_name = getattr(dependency, "import_name", "").strip()
        if not import_name:
            continue
        package_name = getattr(dependency, "package_name", "").strip() or package_name_for_import(import_name)
        ecosystem = getattr(dependency, "ecosystem", "python").strip().lower() or "python"
        specs[import_name] = DependencySpec(
            import_name=import_name,
            package_name=package_name,
            version=getattr(dependency, "version", "").strip(),
            notes=getattr(dependency, "notes", "").strip(),
            source="tool.toml",
            ecosystem=ecosystem,
        )

    # Only auto-scan Python scripts for imports — scanning a .bat or .js for
    # ``import`` statements makes no sense.
    script_path = getattr(tool, "script_path", None)
    suffix = Path(script_path).suffix.lower() if script_path else ""
    if suffix == ".py":
        try:
            detected_modules = imported_modules_from_script(script_path)
        except (OSError, SyntaxError, TypeError, ValueError):
            # ValueError catches UnicodeDecodeError (raised when a .py
            # file saved as cp1252 is read as utf-8 — common on Windows).
            detected_modules = []
        for module in detected_modules:
            if module in specs:
                continue
            specs[module] = DependencySpec(
                import_name=module,
                package_name=package_name_for_import(module),
                source="auto-detected",
                ecosystem="python",
            )

    return sorted(specs.values(), key=lambda spec: spec.import_name.casefold())


def dependency_statuses_for_tools(
    tools,
    python_executable: str,
    env: dict[str, str] | None = None,
    availability_checker: AvailabilityChecker | None = None,
) -> list[DependencyStatus]:
    checker = availability_checker or module_is_available
    statuses: list[DependencyStatus] = []

    for tool in tools:
        tool_id = getattr(getattr(tool, "folder", None), "name", "")
        for spec in dependency_specs_for_tool(tool):
            # Only check availability for the python ecosystem here;
            # node/powershell statuses come from the other providers.
            installed = (
                checker(python_executable, env, spec.import_name)
                if spec.ecosystem == "python"
                else False
            )
            statuses.append(
                DependencyStatus(
                    tool_name=getattr(tool, "name", tool_id),
                    tool_id=tool_id,
                    import_name=spec.import_name,
                    package_name=spec.package_name,
                    version=spec.version,
                    notes=spec.notes,
                    source=spec.source,
                    status=("installed" if installed else ("declared" if spec.ecosystem != "python" else "missing")),
                    ecosystem=spec.ecosystem,
                )
            )

    return statuses


def package_name_for_import(import_name: str) -> str:
    return IMPORT_TO_PACKAGE.get(import_name, import_name)


# Cache for module_is_available results. Keyed by (python_executable, module_name).
# Cleared at the start of each Dependency Manager scan so re-scans after install
# pick up newly-installed packages. Without this, scanning 36 tools with
# overlapping deps would spawn ~100 identical subprocesses.
_module_available_cache: dict[tuple[str, str], bool] = {}


def clear_module_cache() -> None:
    """Clear the module-availability cache. Called by the Dependency
    Manager before each re-scan so fresh installs are detected."""
    _module_available_cache.clear()


def module_is_available(
    python_executable: str,
    env: dict[str, str] | None,
    module_name: str,
) -> bool:
    key = (python_executable, module_name)
    if key in _module_available_cache:
        return _module_available_cache[key]
    try:
        result = subprocess.run(
            [python_executable, "-c", f"import {module_name}"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=15,
            # CREATE_NO_WINDOW: on Windows, don't flash a cmd window for
            # each check. The Dependency Manager calls this function
            # dozens of times during a scan — without this flag, the user
            # sees rapid cmd-window flashing.
            creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
        )
        available = result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        available = False
    _module_available_cache[key] = available
    return available


def python_supports_pip(python_executable: str, env: dict[str, str] | None) -> bool:
    try:
        result = subprocess.run(
            [python_executable, "-m", "pip", "--version"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=15,
            creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


# --------------------------------------------------------------------------- internals (unchanged from v2)
def _is_third_party_module(module_name: str, script_path: Path) -> bool:
    return (
        module_name not in _stdlib_modules()
        and module_name not in sys.builtin_module_names
        and not _is_local_module(module_name, script_path)
    )


def _stdlib_modules() -> set[str]:
    # sys.stdlib_module_names exists in Python 3.10+. We require 3.10+
    # (see requirements.txt), so no fallback needed.
    return set(sys.stdlib_module_names)


def _is_local_module(module_name: str, script_path: Path) -> bool:
    script_dir = script_path.parent
    return (
        (script_dir / f"{module_name}.py").exists()
        or (script_dir / module_name / "__init__.py").exists()
        or module_name in _project_module_names(script_dir)
    )


def _project_module_names(script_dir: Path) -> set[str]:
    """Return the set of sibling module/package names in the tool's own
    folder (NOT the host app's launch cwd).

    Previously this used ``Path.cwd()`` which scanned wherever the user
    happened to launch Tool Pouch from — a bug that caused false
    negatives (e.g. if launched from a dev folder containing a
    ``requests.py``, the scanner would think ``requests`` was a local
    module and not report it as missing). Now scoped to the tool's
    parent directory, which is the correct semantic: we're checking
    for sibling .py files that ship alongside the tool script.
    """
    parent = script_dir.parent
    names = set()
    try:
        for child in parent.iterdir():
            if child == script_dir:
                continue
            if child.is_dir() and (child / "__init__.py").exists():
                names.add(child.name)
            elif child.suffix == ".py":
                names.add(child.stem)
    except (OSError, PermissionError):
        pass
    return names

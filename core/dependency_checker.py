from __future__ import annotations

import ast
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
        specs[import_name] = DependencySpec(
            import_name=import_name,
            package_name=package_name,
            version=getattr(dependency, "version", "").strip(),
            notes=getattr(dependency, "notes", "").strip(),
            source="tool.toml",
        )

    try:
        detected_modules = imported_modules_from_script(getattr(tool, "script_path"))
    except (OSError, SyntaxError, TypeError):
        detected_modules = []

    for module in detected_modules:
        if module in specs:
            continue
        specs[module] = DependencySpec(
            import_name=module,
            package_name=package_name_for_import(module),
            source="auto-detected",
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
            installed = checker(python_executable, env, spec.import_name)
            statuses.append(
                DependencyStatus(
                    tool_name=getattr(tool, "name", tool_id),
                    tool_id=tool_id,
                    import_name=spec.import_name,
                    package_name=spec.package_name,
                    version=spec.version,
                    notes=spec.notes,
                    source=spec.source,
                    status="installed" if installed else "missing",
                )
            )

    return statuses


def find_missing_dependencies(
    script_path: str | Path,
    python_executable: str,
    env: dict[str, str] | None = None,
    availability_checker: AvailabilityChecker | None = None,
) -> list[MissingDependency]:
    checker = availability_checker or module_is_available
    missing = []

    for module in imported_modules_from_script(script_path):
        if not checker(python_executable, env, module):
            missing.append(MissingDependency(module, package_name_for_import(module)))

    return missing


def package_name_for_import(import_name: str) -> str:
    return IMPORT_TO_PACKAGE.get(import_name, import_name)


def module_is_available(
    python_executable: str,
    env: dict[str, str] | None,
    module_name: str,
) -> bool:
    try:
        result = subprocess.run(
            [python_executable, "-c", f"import {module_name}"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=15,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def python_supports_pip(python_executable: str, env: dict[str, str] | None) -> bool:
    try:
        result = subprocess.run(
            [python_executable, "-m", "pip", "--version"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=15,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _is_third_party_module(module_name: str, script_path: Path) -> bool:
    return (
        module_name not in _stdlib_modules()
        and module_name not in sys.builtin_module_names
        and not _is_local_module(module_name, script_path)
    )


def _stdlib_modules() -> set[str]:
    if hasattr(sys, "stdlib_module_names"):
        return set(sys.stdlib_module_names)

    stdlib = Path(get_paths().get("stdlib", ""))
    if not stdlib.exists():
        return set()
    return {path.stem for path in stdlib.glob("*.py")} | {
        path.name for path in stdlib.iterdir() if path.is_dir()
    }


def _is_local_module(module_name: str, script_path: Path) -> bool:
    script_dir = script_path.parent
    return (
        (script_dir / f"{module_name}.py").exists()
        or (script_dir / module_name / "__init__.py").exists()
        or module_name in _project_module_names(script_dir)
    )


def _project_module_names(script_dir: Path) -> set[str]:
    cwd = Path.cwd()
    names = set()
    for child in cwd.iterdir():
        if child == script_dir:
            continue
        if child.is_dir() and (child / "__init__.py").exists():
            names.add(child.name)
        elif child.suffix == ".py":
            names.add(child.stem)
    return names

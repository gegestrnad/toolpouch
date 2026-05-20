from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class ToolImportError(Exception):
    """Raised when a .toolpouch archive cannot be imported safely."""


def import_tool_package(package_path: Path, tools_dir: Path) -> Path:
    if not package_path.exists():
        raise ToolImportError(f"File not found: {package_path}")
    if package_path.suffix.lower() != ".toolpouch":
        raise ToolImportError("Tool packages must use the .toolpouch extension.")

    tools_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(package_path, "r") as archive:
            members = _validated_members(archive)
            root_name = _single_root_folder(members)
            tool_toml = PurePosixPath(root_name) / "tool.toml"
            if str(tool_toml) not in members:
                raise ToolImportError("Archive does not contain a tool.toml file.")

            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                archive.extractall(tmp_dir)
                source_dir = tmp_dir / root_name
                _validate_tool_definition(source_dir)

                dest_dir = _next_available_tool_dir(tools_dir, root_name)
                shutil.copytree(source_dir, dest_dir)
                return dest_dir
    except zipfile.BadZipFile as exc:
        raise ToolImportError("The selected file is not a valid .toolpouch archive.") from exc


def _validated_members(archive: zipfile.ZipFile) -> set[str]:
    members: set[str] = set()
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts:
            raise ToolImportError("Archive contains unsafe paths.")
        if not path.parts:
            continue
        members.add(str(path))
    if not members:
        raise ToolImportError("Archive is empty.")
    return members


def _single_root_folder(members: set[str]) -> str:
    roots = {PurePosixPath(member).parts[0] for member in members}
    if len(roots) != 1:
        raise ToolImportError("Archive must contain exactly one tool folder.")
    root_name = next(iter(roots))
    if root_name in {"", ".", ".."}:
        raise ToolImportError("Archive has an invalid tool folder name.")
    return root_name


def _validate_tool_definition(source_dir: Path) -> None:
    toml_file = source_dir / "tool.toml"
    if not toml_file.exists():
        raise ToolImportError("Archive does not contain a tool.toml file.")

    try:
        with toml_file.open("rb") as f:
            data = tomllib.load(f)
    except Exception as exc:
        raise ToolImportError(f"tool.toml could not be read: {exc}") from exc

    script_name = data.get("tool", {}).get("script", "")
    if not script_name:
        raise ToolImportError("tool.toml does not define a script file.")

    script_path = (source_dir / script_name).resolve()
    try:
        script_path.relative_to(source_dir.resolve())
    except ValueError as exc:
        raise ToolImportError("tool.toml points outside the tool folder.") from exc

    if not script_path.exists() or not script_path.is_file():
        raise ToolImportError(f"Script not found in archive: {script_name}")


def _next_available_tool_dir(tools_dir: Path, folder_name: str) -> Path:
    candidate = tools_dir / folder_name
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        candidate = tools_dir / f"{folder_name}_{index}"
        if not candidate.exists():
            return candidate
        index += 1

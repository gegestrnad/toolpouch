""".toolpouch zip importer / exporter.

Ported VERBATIM from v2 — spec §5 explicitly says: "keep v2's exact
path-traversal guard logic (this is a straight port, don't weaken it)".
The only changes are cosmetic (typing imports consolidated, ``Path`` import
order).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

if sys.version_info >= (3, 11):
    import tomllib  # type: ignore[import-not-found]
else:  # pragma: no cover
    import tomli as tomllib  # type: ignore[import-not-found]


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


def export_tool_package(tool_folder: Path, output_path: Path) -> Path:
    """Bundle a single tool folder into a ``.toolpouch`` zip.

    Skips ``__pycache__`` and ``*.pyc`` — those are build artifacts that
    shouldn't travel with the tool. The archive root is the tool folder
    name so the importer can extract it cleanly into ``tools/``.
    """
    if not tool_folder.is_dir():
        raise ToolImportError(f"Tool folder not found: {tool_folder}")
    if not (tool_folder / "tool.toml").exists():
        raise ToolImportError(f"Tool folder has no tool.toml: {tool_folder}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    root_name = tool_folder.name

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(tool_folder.rglob("*")):
            if "__pycache__" in path.parts:
                continue
            if path.suffix == ".pyc":
                continue
            if path.is_file():
                arcname = str(Path(root_name) / path.relative_to(tool_folder))
                archive.write(path, arcname)
    return output_path


# --------------------------------------------------------------------------- internals
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

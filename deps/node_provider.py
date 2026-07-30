"""Node.js ecosystem provider.

Spec §6: "``npm ls`` / ``npm install`` against a tool's ``package.json``
if present; skip scanning for ``.js`` tools with no manifest rather than
guessing."
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ecosystem = "node"


def scan(tool) -> list[dict]:
    """Read dependencies from the tool's ``package.json`` if present.

    A ``.js`` tool with no ``package.json`` returns an empty list — we
    do NOT try to parse ``require()`` calls from the script (too noisy,
    too many false positives from conditional/requires-in-comments).
    """
    tool_folder = getattr(tool, "folder", None)
    if tool_folder is None:
        return []
    pkg_path = Path(tool_folder) / "package.json"
    if not pkg_path.exists():
        return []

    try:
        data = json.loads(pkg_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    deps: dict = {}
    deps.update(data.get("dependencies", {}) or {})
    deps.update(data.get("devDependencies", {}) or {})

    npm = _find_npm()
    statuses: list[dict] = []
    for name, version_spec in deps.items():
        installed = _is_installed_locally(Path(tool_folder), name) if npm else False
        statuses.append(
            {
                "tool_name": getattr(tool, "name", tool_folder.name),
                "tool_id": tool_folder.name,
                "import_name": name,
                "package_name": name,
                "version": str(version_spec),
                "notes": "from package.json",
                "source": "package.json",
                "status": "installed" if installed else "missing",
                "ecosystem": "node",
            }
        )
    return statuses


def install(missing: list[dict]) -> tuple[int, str]:
    """``npm install`` each missing package into the user's global prefix
    (so the tool can ``require()`` it next time without a per-tool
    install). Returns ``(n_installed, log_text)``.
    """
    npm = _find_npm()
    if not npm:
        return 0, "[ERROR] npm not found on PATH. Install Node.js LTS from https://nodejs.org/\n"

    log_lines: list[str] = []
    n_installed = 0
    for m in missing:
        pkg = m.get("package_name") or m.get("import_name", "")
        log_lines.append(f"[OK] npm install -g {pkg} ...")
        try:
            result = subprocess.run(
                [npm, "install", "-g", pkg],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )
            if result.returncode == 0:
                n_installed += 1
                log_lines.append(f"[OK] {pkg} installed globally.")
            else:
                log_lines.append(f"[ERROR] npm failed for {pkg}:")
                log_lines.append(result.stderr.strip() or result.stdout.strip())
        except subprocess.TimeoutExpired:
            log_lines.append(f"[ERROR] npm install timed out for {pkg}.")
        except Exception as e:
            log_lines.append(f"[ERROR] {pkg}: {e}")
    return n_installed, "\n".join(log_lines) + "\n"


# --------------------------------------------------------------------------- helpers
def _find_npm() -> str | None:
    return shutil.which("npm") or shutil.which("npm.exe")


def _is_installed_locally(tool_folder: Path, package_name: str) -> bool:
    """Check ``node_modules/<name>`` in the tool folder. Falls back to a
    ``npm ls --global`` check if no local install exists."""
    local = tool_folder / "node_modules" / package_name
    if local.exists():
        return True
    npm = _find_npm()
    if not npm:
        return False
    try:
        result = subprocess.run(
            [npm, "ls", "-g", package_name, "--depth", "0", "--json"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
        )
        if result.returncode != 0:
            return False
        data = json.loads(result.stdout or "{}")
        return bool(data.get("dependencies"))
    except Exception:
        return False

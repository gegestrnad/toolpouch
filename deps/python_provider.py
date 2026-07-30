"""Python ecosystem provider.

This is a thin wrapper around v2's ``core.dependency_checker`` functions,
exposing them through the provider protocol so the DependencyManager UI
can treat all ecosystems uniformly.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from core.dependency_checker import (
    DependencySpec,
    DependencyStatus,
    dependency_specs_for_tool,
    module_is_available,
    package_name_for_import,
    python_supports_pip,
)
from core.runtime_resolver import RuntimeResolver, build_subprocess_env


ecosystem = "python"


def scan(tool) -> list[dict]:
    """Return one status dict per Python dependency declared-in-or-detected-from ``tool``."""
    spec = _resolve_python_executable()
    env = build_subprocess_env()
    statuses: list[dict] = []
    for dep in dependency_specs_for_tool(tool):
        if dep.ecosystem != "python":
            continue
        installed = module_is_available(spec, env, dep.import_name) if spec else False
        statuses.append(
            {
                "tool_name": getattr(tool, "name", getattr(tool, "folder", Path()).name),
                "tool_id": getattr(getattr(tool, "folder", None), "name", ""),
                "import_name": dep.import_name,
                "package_name": dep.package_name,
                "version": dep.version,
                "notes": dep.notes,
                "source": dep.source,
                "status": "installed" if installed else "missing",
                "ecosystem": "python",
            }
        )
    return statuses


def install(missing: list[dict]) -> tuple[int, str]:
    """``pip install`` each missing spec. Returns ``(n_installed, log_text)``."""
    spec = _resolve_python_executable()
    if not spec:
        return 0, "[ERROR] No Python interpreter found on PATH.\n"
    env = build_subprocess_env()
    if not python_supports_pip(spec, env):
        return 0, "[ERROR] Python on PATH does not have pip. Install pip first.\n"

    log_lines: list[str] = []
    n_installed = 0
    for m in missing:
        install_spec = m.get("package_name") or m.get("import_name", "")
        version = str(m.get("version", "") or "").strip()
        if version:
            # Version may be a bare number ("4.12") from v2's
            # ``min_version`` field, OR a full specifier (">=4.12",
            # "==1.2.3", "~=2.0"). pip requires an operator prefix;
            # if the user just wrote a number, assume "at least".
            if version[0] not in "=<>!~":
                version = ">=" + version
            install_spec = f"{install_spec}{version}"
        log_lines.append(f"[OK] Installing {install_spec} ...")
        try:
            result = subprocess.run(
                [spec, "-m", "pip", "install", "--upgrade", install_spec],
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )
            if result.returncode == 0:
                n_installed += 1
                log_lines.append(f"[OK] {install_spec} installed.")
            else:
                log_lines.append(f"[ERROR] pip failed for {install_spec}:")
                log_lines.append(result.stderr.strip() or result.stdout.strip())
        except subprocess.TimeoutExpired:
            log_lines.append(f"[ERROR] pip install timed out for {install_spec}.")
        except Exception as e:
            log_lines.append(f"[ERROR] {install_spec}: {e}")
    return n_installed, "\n".join(log_lines) + "\n"


# --------------------------------------------------------------------------- helpers
def _resolve_python_executable() -> str | None:
    """Find a Python on PATH for dependency checks. Uses the same resolver
    as the tool runner but bypasses the frozen-app fallback (we want to
    check what the *user* has installed, not the bundled interpreter).
    """
    import shutil

    for candidate in ("python3", "python", "py.exe", "py"):
        found = shutil.which(candidate)
        if found:
            return found
    return None

"""PowerShell ecosystem provider.

Spec §6: "``Get-Module -ListAvailable`` / ``Install-Module`` for module
deps declared in ``tool.toml``."
"""
from __future__ import annotations

import os
import shutil
import subprocess


ecosystem = "powershell"


def scan(tool) -> list[dict]:
    """For each ``[[dependencies]]`` entry with ``ecosystem = "powershell"``
    declared in ``tool.toml``, check whether the module is importable via
    ``Get-Module -ListAvailable``.
    """
    pwsh = _find_powershell()
    statuses: list[dict] = []
    tool_folder = getattr(tool, "folder", None)
    for dep in getattr(tool, "dependencies", []):
        if getattr(dep, "ecosystem", "python") != "powershell":
            continue
        module_name = getattr(dep, "import_name", "").strip()
        if not module_name:
            continue
        installed = _is_module_available(pwsh, module_name) if pwsh else False
        statuses.append(
            {
                "tool_name": getattr(tool, "name", getattr(tool_folder, "name", "")),
                "tool_id": getattr(tool_folder, "name", ""),
                "import_name": module_name,
                "package_name": getattr(dep, "package_name", "") or module_name,
                "version": getattr(dep, "version", ""),
                "notes": getattr(dep, "notes", ""),
                "source": "tool.toml",
                "status": "installed" if installed else "missing",
                "ecosystem": "powershell",
            }
        )
    return statuses


def install(missing: list[dict]) -> tuple[int, str]:
    pwsh = _find_powershell()
    if not pwsh:
        return 0, "[ERROR] PowerShell not found. Install PowerShell 7+ from https://aka.ms/powershell-release\n"

    log_lines: list[str] = []
    n_installed = 0
    for m in missing:
        module = m.get("package_name") or m.get("import_name", "")
        log_lines.append(f"[OK] Install-Module {module} -Force -Scope CurrentUser ...")
        try:
            # -Force: skip the "already installed, overwrite?" prompt.
            # -Scope CurrentUser: no admin elevation needed.
            # -AllowClobber: some modules clobber existing cmdlets; that's OK
            #   for a local dev tool, the user explicitly asked to install.
            result = subprocess.run(
                [
                    pwsh,
                    "-NoProfile",
                    "-Command",
                    f"Install-Module -Name {module!r} -Force -Scope CurrentUser -AllowClobber",
                ],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )
            if result.returncode == 0:
                n_installed += 1
                log_lines.append(f"[OK] {module} installed.")
            else:
                log_lines.append(f"[ERROR] Install-Module failed for {module}:")
                log_lines.append(result.stderr.strip() or result.stdout.strip())
        except subprocess.TimeoutExpired:
            log_lines.append(f"[ERROR] Install-Module timed out for {module}.")
        except Exception as e:
            log_lines.append(f"[ERROR] {module}: {e}")
    return n_installed, "\n".join(log_lines) + "\n"


# --------------------------------------------------------------------------- helpers
def _find_powershell() -> str | None:
    pwsh = shutil.which("pwsh") or shutil.which("pwsh.exe")
    if pwsh:
        return pwsh
    return shutil.which("powershell") or shutil.which("powershell.exe")


def _is_module_available(pwsh: str, module_name: str) -> bool:
    try:
        result = subprocess.run(
            [pwsh, "-NoProfile", "-Command", f"Get-Module -ListAvailable -Name {module_name!r} | Select-Object -First 1"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False

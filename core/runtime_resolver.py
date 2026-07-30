"""Multi-language runtime resolver (spec §4).

Decides which interpreter launches a tool script:

    .py         -> explicit ``tool.runtime`` override, else system
                   ``python``/``py`` on PATH, else the bundled fallback
                   interpreter under ``installer/python-embed/``.
    .ps1        -> ``pwsh`` if found, else ``powershell.exe``
                   (always present on Windows).
    .bat/.cmd   -> ``cmd.exe /c`` (always present on Windows).
    .js         -> system ``node`` on PATH; if absent, raise a clear,
                   actionable error — do NOT bundle a Node fallback
                   (would break the spec §1.7 footprint goal).

**Critical (spec §7):** when the host app is frozen with PyInstaller, the
Python interpreter bundled inside the frozen app is for the *UI process
only*. ``resolve()`` for ``.py`` tools must still look for a separate
system Python on PATH first, and only fall back to a *distinct, minimal*
embeddable interpreter under ``installer/python-embed/`` (NOT the
PyInstaller-bundled one) if none is found. ``_frozen_python()`` returns
``None`` precisely so this fallback path is never silently taken.
"""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path


class RuntimeResolutionError(RuntimeError):
    """Raised when no usable interpreter can be found for a script."""


@dataclass
class LaunchSpec:
    """Resolved launch command — passed verbatim to ``subprocess.Popen`` as a
    list, never string-joined. Popen's list form handles Windows quoting
    correctly; building a string and using ``shell=True`` is the source of
    most path-with-spaces bugs and is explicitly forbidden by spec §4.
    """

    executable: str
    args_prefix: list[str] = field(default_factory=list)
    ecosystem: str = "python"  # for the DependencyManager UI

    def build_command(self, script_path: Path, user_args: list[str]) -> list[str]:
        """Return the full argv list to pass to ``Popen``.

        Order: ``[executable] + args_prefix + [script_path] + user_args``.
        E.g. for a .bat tool: ``["cmd.exe", "/c", "C:\\path\\tool.bat", "--foo", "bar"]``.
        """
        return [self.executable] + list(self.args_prefix) + [str(script_path)] + list(user_args)


# --------------------------------------------------------------------------- helpers
def _which(name: str) -> str | None:
    """``shutil.which`` wrapper that returns ``None`` instead of raising on
    platforms where PATH lookups are unsupported.
    """
    try:
        return shutil.which(name)
    except Exception:
        return None


def _is_windows() -> bool:
    return os.name == "nt" or sys.platform.startswith("win")


def _frozen_app_dir() -> Path | None:
    """Return the directory the frozen .exe lives in, or ``None`` if running
    from source.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return None


def _bundled_embed_python() -> Path | None:
    """Locate the *separate, minimal* embeddable Python shipped alongside the
    frozen app for tool execution fallback (spec §7). This is distinct from
    the PyInstaller-bundled interpreter that runs the UI.
    """
    exe_dir = _frozen_app_dir()
    if exe_dir is None:
        return None
    candidates = [
        exe_dir / "python-embed" / "python.exe",
        exe_dir / "python_embed" / "python.exe",
        exe_dir / "embed" / "python.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _system_python() -> str | None:
    """Find a Python on PATH. Prefer ``py`` launcher on Windows (it picks the
    latest installed version), then plain ``python``. On POSIX prefer
    ``python3`` then ``python``.
    """
    if _is_windows():
        for candidate in ("py.exe", "py", "python.exe", "python"):
            found = _which(candidate)
            if found:
                return found
        return None
    for candidate in ("python3", "python"):
        found = _which(candidate)
        if found:
            return found
    return None


def _system_powershell() -> str | None:
    """Prefer ``pwsh`` (PowerShell 7+, side-by-side install), fall back to
    ``powershell`` (Windows PowerShell 5.1, always present on Windows)."""
    pwsh = _which("pwsh") or _which("pwsh.exe")
    if pwsh:
        return pwsh
    if _is_windows():
        # powershell.exe is in System32, always present on Win10+
        sys32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        if sys32.exists():
            return str(sys32)
        found = _which("powershell.exe") or _which("powershell")
        if found:
            return found
    return None


def _system_node() -> str | None:
    return _which("node") or _which("node.exe")


def _system_cmd() -> str | None:
    if not _is_windows():
        return None
    sysroot = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    cmd = sysroot / "System32" / "cmd.exe"
    if cmd.exists():
        return str(cmd)
    return _which("cmd.exe") or _which("cmd")


# --------------------------------------------------------------------------- resolver
class RuntimeResolver:
    """Resolve a ``ToolDefinition`` to a ``LaunchSpec``.

    Stateless and safe to instantiate once and reuse, but tests instantiate
    per-case for isolation.
    """

    def resolve(self, tool) -> LaunchSpec:
        """``tool`` is any object with ``.script_path`` (Path), ``.runtime``
        (str override), and ``.folder`` (Path, used for fallback resolution
        diagnostics)."""
        runtime_override = getattr(tool, "runtime", "").strip().lower()
        script_path = Path(getattr(tool, "script_path", ""))
        suffix = script_path.suffix.lower()

        # 1) Explicit override always wins.
        if runtime_override == "python":
            return self._resolve_python(tool)
        if runtime_override in ("pwsh", "powershell"):
            return self._resolve_powershell()
        if runtime_override == "cmd":
            return self._resolve_cmd()
        if runtime_override == "node":
            return self._resolve_node()

        # 2) Infer from extension.
        if suffix == ".py":
            return self._resolve_python(tool)
        if suffix == ".ps1":
            return self._resolve_powershell()
        if suffix in (".bat", ".cmd"):
            return self._resolve_cmd()
        if suffix == ".js":
            return self._resolve_node()

        # 3) Unknown extension. Give a clear, actionable error.
        raise RuntimeResolutionError(
            f"Cannot determine runtime for {script_path.name!r}: "
            f"unknown extension {suffix!r}. "
            f"Set an explicit ``runtime`` in tool.toml "
            f"(one of: python, pwsh, powershell, cmd, node)."
        )

    # ------------------------------------------------------------------ .py
    def _resolve_python(self, tool) -> LaunchSpec:
        sys_py = _system_python()
        if sys_py:
            return LaunchSpec(executable=sys_py, args_prefix=[], ecosystem="python")

        embed = _bundled_embed_python()
        if embed:
            return LaunchSpec(executable=str(embed), args_prefix=[], ecosystem="python")

        raise RuntimeResolutionError(
            "No Python interpreter found. Install Python 3.10+ from "
            "https://python.org and restart Tool Pouch, or add a "
            "minimal embeddable Python under the app's "
            "``python-embed/`` folder (see installer/python-embed/README.md)."
        )

    # ------------------------------------------------------------------ .ps1
    def _resolve_powershell(self) -> LaunchSpec:
        pwsh = _system_powershell()
        if not pwsh:
            raise RuntimeResolutionError(
                "No PowerShell found. Windows PowerShell is built into "
                "Windows 10/11; if you removed it, install PowerShell 7+ "
                "from https://aka.ms/powershell-release"
            )
        # -NoProfile: skip user profile load (faster, no side-effects)
        # -ExecutionPolicy Bypass: allow this one script to run without
        #   interactive prompts. This is safe because tool scripts are
        #   local user-owned files (spec §10: same trust model as v2).
        # -File: run the script file (not a -Command string).
        return LaunchSpec(
            executable=pwsh,
            args_prefix=["-NoProfile", "-ExecutionPolicy", "Bypass", "-File"],
            ecosystem="powershell",
        )

    # ------------------------------------------------------------------ .bat/.cmd
    def _resolve_cmd(self) -> LaunchSpec:
        cmd = _system_cmd()
        if not cmd:
            raise RuntimeResolutionError(
                "cmd.exe not found — this should never happen on Windows. "
                "If you are running on Wine/ReactOS, cmd.exe may be missing."
            )
        # /c: run the command and terminate. /k would leave the shell open.
        # Do NOT use /S — let cmd.exe do its own quoting on the script path.
        return LaunchSpec(
            executable=cmd,
            args_prefix=["/c"],
            ecosystem="none",
        )

    # ------------------------------------------------------------------ .js
    def _resolve_node(self) -> LaunchSpec:
        node = _system_node()
        if not node:
            raise RuntimeResolutionError(
                "No Node.js found on PATH. Install Node.js LTS from "
                "https://nodejs.org/ and restart Tool Pouch. "
                "(Tool Pouch intentionally does NOT bundle Node — see "
                "spec §1.7 footprint goal.)"
            )
        return LaunchSpec(executable=node, args_prefix=[], ecosystem="node")


# --------------------------------------------------------------------------- env helper
def build_subprocess_env() -> dict[str, str]:
    """Build the environment dict to pass to ``subprocess.Popen`` for tool
    execution.

    Copies the current environment and removes ``PYTHONHOME``/``PYTHONPATH``
    if they were set by a frozen PyInstaller host — those vars would
    *force* the system Python to use the frozen app's stdlib, which is the
    exact silent regression spec §7 warns about. Tool scripts must use
    their *own* interpreter's stdlib.

    Also forces UTF-8 for Python tool stdout — Windows defaults to cp1252
    and would crash with ``UnicodeEncodeError`` the moment a tool prints
    any non-ASCII character (e.g. a CJK char from a translated file).
    Fixes the "html_to_text" crash reported by the user.
    """
    env = os.environ.copy()
    if getattr(sys, "frozen", False):
        # If frozen, the host process set these to point at its bundled
        # stdlib. Strip them so the tool's interpreter (system Python, Node,
        # PowerShell, etc.) uses its own defaults.
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
        # PYTHONNOUSERSITE was set by v2 to disable user site-packages;
        # we keep that behavior so tool scripts don't accidentally pull
        # in packages from the host UI's user site.
        env["PYTHONNOUSERSITE"] = "1"
    # Force Python 3.7+ UTF-8 mode for tool scripts. This makes stdin/
    # stdout/stderr use UTF-8 instead of the platform default (cp1252 on
    # Western Windows). Without this, any tool that prints a non-ASCII
    # char (CJK chars, smart quotes, em-dashes, etc.) crashes with
    # UnicodeEncodeError. Only affects the spawned tool process, not the
    # host UI.
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env

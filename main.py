"""Tool Pouch v3 entrypoint.

The frozen-app asset seeding logic seeds bundled ``tools/`` into the
USER-WRITABLE ``~/.toolpouch/tools/`` directory (NOT the install dir —
``C:\\Program Files\\`` is read-only for non-admin users). Assets
(icon, lang_icons) are read directly from the PyInstaller bundle
(``_MEIPASS``) since they're read-only and never need user editing.

This file is framework-bootstrap-only. All UI structure lives in
``ui.app``.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

# Ensure the project root is on sys.path even when frozen, so
# ``from core...`` and ``from ui...`` resolve correctly.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).parent))


def _exe_dir() -> Path:
    """Return the directory the app runs from.

    When frozen with PyInstaller ``--onedir``, this is the folder
    containing ``ToolPouch.exe``. When running from source, it's the
    project root (where main.py lives).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def _user_data_dir() -> Path:
    """Return the user-writable data directory.

    On Windows this is ``%USERPROFILE%\\.toolpouch`` (same as
    ConfigManager's ``config_dir``). On other platforms it's
    ``~/.toolpouch``. This is where user-editable data lives: tools,
    config, logs. The install dir (``C:\\Program Files\\Tool Pouch``)
    is read-only for non-admin users, so we NEVER write there.
    """
    return Path.home() / ".toolpouch"


def _bundled_dir(subdir: str) -> Path | None:
    """Return the path to a bundled data subdir (``assets``, ``tools``)
    inside the PyInstaller bundle, or ``None`` if not frozen / not present.

    When frozen, read-only resources live under ``sys._MEIPASS``. When
    running from source, they live next to ``main.py``.
    """
    if getattr(sys, "frozen", False):
        p = Path(sys._MEIPASS) / subdir  # type: ignore[attr-defined]
    else:
        p = Path(__file__).parent / subdir
    return p if p.exists() else None


def _load_deleted_tools() -> set[str]:
    """Load the set of tool folder names the user has explicitly deleted.

    Stored as JSON at ``~/.toolpouch/deleted_tools.json``. Tools in this
    set are NOT re-seeded from the bundle on launch — this is what makes
    deletions "stick" across restarts. Without this, every launch would
    re-copy bundled tools that the user deleted.
    """
    import json
    path = _user_data_dir() / "deleted_tools.json"
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {str(s) for s in data}
    except Exception:
        pass
    return set()


def _save_deleted_tools(deleted: set[str]) -> None:
    """Persist the deleted-tools set so deletions survive app restarts."""
    import json
    path = _user_data_dir() / "deleted_tools.json"
    try:
        path.write_text(json.dumps(sorted(deleted), indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[_save_deleted_tools] Failed: {e}")


def record_tool_deletion(tool_folder_name: str) -> None:
    """Record that the user deleted a tool, so it doesn't get re-seeded.

    Called by the sidebar's delete handler after successfully removing
    the tool folder. Writes the folder name to ``deleted_tools.json``.
    """
    deleted = _load_deleted_tools()
    deleted.add(tool_folder_name)
    _save_deleted_tools(deleted)


def unrecord_tool_deletion(tool_folder_name: str) -> None:
    """Remove a tool from the deleted set (e.g. if the user re-imports it).

    Called by the import handler after successfully importing a tool.
    """
    deleted = _load_deleted_tools()
    deleted.discard(tool_folder_name)
    _save_deleted_tools(deleted)


def seed_tools() -> Path:
    """Seed bundled ``tools/`` into the user-writable data dir.

    Returns the writable tools dir (``~/.toolpouch/tools``). The bundled
    copy under ``_MEIPASS`` is read-only (extracted from the PyInstaller
    zip), so we copy each tool folder into the user's data dir on first
    launch. Existing folders are NOT overwritten — the user may have
    edited them or added their own.

    Tools the user has explicitly deleted are NOT re-seeded — their
    folder names are tracked in ``deleted_tools.json``. This is the fix
    for the "deleted tools reappear after restart" bug.
    """
    tools_dir = _user_data_dir() / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)

    bundled = _bundled_dir("tools")
    if bundled is None:
        return tools_dir

    deleted = _load_deleted_tools()

    for tool_folder in bundled.iterdir():
        if not tool_folder.is_dir():
            continue
        # Skip __pycache__ and similar build artifacts.
        if tool_folder.name.startswith("__"):
            continue
        # Skip tools the user has explicitly deleted — don't re-seed them.
        if tool_folder.name in deleted:
            continue
        dest = tools_dir / tool_folder.name
        if not dest.exists():
            try:
                shutil.copytree(tool_folder, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            except Exception as e:
                print(f"[seed_tools] Failed to copy {tool_folder.name}: {e}")
    return tools_dir


def find_icon() -> Path | None:
    """Find the app icon (.ico) in any of the possible locations.

    Search order:
      1. User data dir (``~/.toolpouch/assets/icon.ico``) — if the user
         replaced the icon.
      2. Bundled (``_MEIPASS/assets/icon.ico`` when frozen, or
         ``<project>/assets/icon.ico`` when running from source).
      3. Install dir (``exe_dir/assets/icon.ico``) — legacy fallback.

    Returns ``None`` if no icon file is found.
    """
    candidates = [
        _user_data_dir() / "assets" / "icon.ico",
        _bundled_dir("assets") / "icon.ico" if _bundled_dir("assets") else None,
        _exe_dir() / "assets" / "icon.ico",
    ]
    for c in candidates:
        if c is not None and c.exists():
            return c
    return None


def _check_for_toolpouch_import() -> Path | None:
    """Check if the app was launched by double-clicking a .toolpouch file.

    When Windows opens a .toolpouch file with Tool Pouch, it passes the
    file path as the first argument (``sys.argv[1]``). This function
    detects that case and returns the path so the caller can import it.

    Returns ``None`` if no .toolpouch file was passed (normal launch).
    """
    if len(sys.argv) < 2:
        return None
    arg = sys.argv[1]
    if not isinstance(arg, str):
        return None
    arg = arg.strip()
    if not arg.lower().endswith(".toolpouch"):
        return None
    p = Path(arg)
    if p.exists() and p.is_file():
        return p
    return None


def _import_and_select_tool(app, package_path: Path) -> None:
    """Import a .toolpouch package and select the newly imported tool.

    Called AFTER the App's mainloop has started (via ``app.after(...)``)
    so the sidebar is already populated and the selection can work.

    Shows a messagebox on success or failure so the user gets feedback
    when they double-click a .toolpouch file.
    """
    from core.tool_importer import import_tool_package, ToolImportError
    from tkinter import messagebox

    try:
        dest = import_tool_package(package_path, app.tools_dir)
        # Un-record any previous deletion so it doesn't get blocked.
        try:
            unrecord_tool_deletion(dest.name)
        except Exception:
            pass
        app.reload()
        app.sidebar.select_by_id(dest.name)
        # Show success feedback.
        tool = app.get_tool(dest.name)
        tool_name = tool.name if tool else dest.name
        messagebox.showinfo(
            "Tool imported",
            f"Successfully imported '{tool_name}'.\n\n"
            f"Location: {dest}\n\n"
            f"The tool is now selected in the sidebar and ready to use.",
            parent=app,
        )
    except ToolImportError as e:
        messagebox.showerror(
            "Import failed",
            f"Could not import the .toolpouch package:\n\n{e}",
            parent=app,
        )
    except Exception as e:
        messagebox.showerror(
            "Import failed",
            f"An unexpected error occurred while importing:\n\n{e}",
            parent=app,
        )


def main() -> None:
    # HiDPI: CustomTkinter handles scaling automatically on Windows via
    # Tk 8.6+. We just set the rounding policy to PassThrough so 1.5x
    # displays don't round to 2x.
    import customtkinter as ctk

    ctk.set_widget_scaling(1.0)  # user can override via config in future
    ctk.deactivate_automatic_dpi_awareness = False  # default: active

    # Set a Windows AppUserModelID so the taskbar shows OUR icon instead
    # of the default Python/Tk icon. This is the standard Windows
    # requirement for any app that wants its own taskbar grouping.
    # MUST be called before any Tk window is created.
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ToolPouch.App.v3")
        except Exception:
            pass  # not critical — title-bar icon still works

    # Seed tools into the USER-WRITABLE data dir (NOT the install dir,
    # which is read-only under ``C:\Program Files\``).
    tools_dir = seed_tools()

    # Check if we were launched by double-clicking a .toolpouch file.
    pending_import = _check_for_toolpouch_import()

    # Import after seeding so theme JSON files exist on disk.
    from ui.app import App

    app = App(tools_dir=tools_dir, exe_dir=_exe_dir())

    # Set the taskbar + title-bar icon.
    _set_window_icon(app)

    # If launched via a .toolpouch file, schedule the import after the
    # UI is ready (500ms gives the sidebar time to populate).
    if pending_import is not None:
        app.after(500, lambda: _import_and_select_tool(app, pending_import))

    app.mainloop()


def _set_window_icon(app) -> None:
    """Set the window icon for BOTH the title bar AND the Windows taskbar.

    On Windows, ``iconbitmap(default=True)`` sets all icon variants
    (small, large, taskbar) from a single .ico file. Combined with the
    ``SetCurrentProcessExplicitAppUserModelID`` call above, this gives
    us a custom taskbar icon instead of the default Python/Tk feather.

    The icon is searched via ``find_icon()`` which checks the user data
    dir, the PyInstaller bundle, and the install dir in that order.
    """
    icon_path = find_icon()
    if icon_path is None:
        return

    try:
        if os.name == "nt":
            # iconbitmap with default=True sets ALL icon sizes from the
            # .ico (which contains 16/32/48/64/128/256 resolutions).
            # This is the most reliable way to set both the title-bar
            # icon AND the taskbar icon on Windows.
            try:
                app.wm_iconbitmap(default=str(icon_path))
            except Exception:
                # Fallback: plain iconbitmap (title bar only).
                try:
                    app.iconbitmap(str(icon_path))
                except Exception:
                    pass
        else:
            # On Linux/macOS, .ico isn't supported by PhotoImage. Skip
            # silently — the window manager will use a default icon.
            pass
    except Exception:
        pass


if __name__ == "__main__":
    main()

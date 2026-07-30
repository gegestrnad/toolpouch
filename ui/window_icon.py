"""Shared helpers for setting window icons on CTkToplevel windows.

CustomTkinter's ``CTkToplevel`` auto-sets its own icon (CustomTkinter_icon_Windows.ico)
200ms after creation if the user hasn't called ``iconbitmap`` yet. To use
OUR icon instead, we must call ``iconbitmap`` in the Toplevel's
``__init__`` BEFORE that 200ms timer fires.

This module provides ``set_window_icon()`` which finds the icon file
(same search logic as ``main.py::find_icon()``) and applies it to any
CTk or CTkToplevel window.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _find_icon() -> Path | None:
    """Find the app icon (.ico). Mirrors main.py::find_icon() but kept
    separate to avoid importing main.py (which would trigger the full
    app bootstrap) from Toplevel windows.
    """
    candidates: list[Path | None] = []

    if getattr(sys, "frozen", False):
        # Frozen: check _MEIPASS first, then exe dir.
        candidates.append(Path(sys._MEIPASS) / "assets" / "icon.ico")  # type: ignore[attr-defined]
        candidates.append(Path(sys.executable).parent / "assets" / "icon.ico")
    else:
        # Source: project root / assets / icon.ico
        candidates.append(Path(__file__).parent.parent / "assets" / "icon.ico")

    for c in candidates:
        if c is not None and c.exists():
            return c
    return None


def set_window_icon(window) -> None:
    """Set the app icon on a CTk or CTkToplevel window.

    Call this in the window's ``__init__`` BEFORE CTk's 200ms
    ``_windows_set_titlebar_icon`` timer fires, otherwise CTk will
    override our icon with its own.

    On Windows, uses ``wm_iconbitmap(default=...)`` which sets ALL icon
    variants (title bar + taskbar + alt-tab) from the .ico file.
    On other platforms, does nothing (.ico isn't supported by PhotoImage).
    """
    if os.name != "nt":
        return  # .ico is Windows-only; other platforms use iconphoto with PNG

    icon_path = _find_icon()
    if icon_path is None:
        return

    try:
        # Mark that iconbitmap was called so CTk doesn't override it.
        window._iconbitmap_method_called = True  # type: ignore[attr-defined]
        window.wm_iconbitmap(default=str(icon_path))
    except Exception:
        try:
            window._iconbitmap_method_called = True  # type: ignore[attr-defined]
            window.iconbitmap(str(icon_path))
        except Exception:
            pass

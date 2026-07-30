"""Shared helpers for displaying script-type information.

Used by the sidebar (icon next to tool name) and the tool panel header
(badge chip next to the title). Centralized so the label vocabulary,
colors, and icon paths stay consistent across the UI.
"""
from __future__ import annotations

from pathlib import Path


# Icon PNGs live under assets/lang_icons/. Resolved at runtime so the
# path works both in dev (source tree) and frozen (PyInstaller _MEIPASS).
def _resolve_assets_dir() -> Path:
    """Find the lang_icons directory.

    When frozen with PyInstaller, the bundled data is under
    ``sys._MEIPASS / "assets" / "lang_icons"``. When running from source,
    it's ``<project_root>/assets/lang_icons`` (two parents up from this
    file: ui/script_types.py → ui/ → project_root/).
    """
    import sys
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "assets" / "lang_icons"  # type: ignore[attr-defined]
        if base.exists():
            return base
        # Fallback: the exe dir (assets are seeded there on first launch).
        exe_dir = Path(sys.executable).parent
        candidate = exe_dir / "assets" / "lang_icons"
        if candidate.exists():
            return candidate
    return Path(__file__).parent.parent / "assets" / "lang_icons"


_ASSETS_DIR = _resolve_assets_dir()


# Extension → (short label, full name, badge color, icon filename).
# Colors are chosen for legibility on both dark and light themes.
SCRIPT_TYPES: dict[str, tuple[str, str, str, str]] = {
    ".py":  ("PY",  "Python",     "#3776ab", "python.png"),
    ".ps1": ("PS1", "PowerShell", "#012456", "powershell.png"),
    ".bat": ("BAT", "Batch",      "#4c5256", "batch.png"),
    ".cmd": ("BAT", "Batch",      "#4c5256", "batch.png"),
    ".js":  ("JS",  "JavaScript", "#339933", "node.png"),
    ".rb":  ("RB",  "Ruby",       "#dc2626", "unknown.png"),    # not yet supported
    ".sh":  ("SH",  "Shell",      "#10b981", "unknown.png"),    # not yet supported on Windows
}


def script_badge(script_path: Path, runtime: str = "") -> tuple[str, str]:
    """Return ``(label, color)`` for a tool's script.

    ``label`` is a short 2-3 char tag like ``"PY"`` or ``"JS"``.
    ``color`` is a hex color string for the badge background.

    If the script extension is unknown, returns ``("?", "#6b7280")`` so
    the user can see at a glance that something is off.
    """
    suffix = Path(script_path).suffix.lower() if script_path else ""
    info = SCRIPT_TYPES.get(suffix)
    if info is None:
        return ("?", "#6b7280")
    return (info[0], info[2])


def script_language_name(script_path: Path, runtime: str = "") -> str:
    """Return the full language name, e.g. ``"Python"`` or ``"Batch"``."""
    suffix = Path(script_path).suffix.lower() if script_path else ""
    info = SCRIPT_TYPES.get(suffix)
    if info is None:
        return "Unknown"
    return info[1]


def icon_path(script_path: Path, runtime: str = "") -> Path:
    """Return the PNG icon path for a tool's script language.

    Falls back to ``unknown.png`` for unrecognized extensions (so the
    sidebar row still renders with an icon rather than a blank gap).
    """
    suffix = Path(script_path).suffix.lower() if script_path else ""
    info = SCRIPT_TYPES.get(suffix)
    icon_name = info[3] if info else "unknown.png"
    return _ASSETS_DIR / icon_name


# Cache of loaded CTkImage objects so we don't re-load the PNG on every
# sidebar rebuild. Keyed by filename. CRITICAL: the sidebar keeps its
# own reference to each returned image (via ``_icon_images``) — Tk
# garbage-collects PhotoImages that have no Python-side reference, so
# the cache alone isn't enough.
_IMAGE_CACHE: dict[str, object] = {}


def load_icon_image(script_path: Path, runtime: str = "", size: int = 16):
    """Return a cached image for the script's language icon.

    Tries ``ctk.CTkImage`` (PIL-based, HiDPI-crisp) first. If PIL isn't
    available (e.g. not bundled in a frozen build), falls back to plain
    ``tk.PhotoImage`` (which supports PNG in Tk 8.6+ without PIL).

    Returns ``None`` if the PNG file is missing AND both image-loading
    methods fail.
    """
    path = icon_path(script_path, runtime)
    cache_key = f"{path.name}:{size}"
    if cache_key in _IMAGE_CACHE:
        return _IMAGE_CACHE[cache_key]
    if not path.exists():
        return None

    # Try CTkImage first (needs PIL, but gives HiDPI-crisp scaling).
    try:
        import customtkinter as ctk
        from PIL import Image
        pil_img = Image.open(str(path))
        img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(size, size))
        _IMAGE_CACHE[cache_key] = img
        return img
    except ImportError:
        # PIL not available — fall back to plain tk.PhotoImage.
        # This works without PIL on Tk 8.6+ (PNG is built-in).
        pass
    except Exception:
        # Other PIL error — also fall back.
        pass

    # Fallback: plain tk.PhotoImage (no PIL needed, PNG supported in 8.6+).
    try:
        import tkinter as tk
        img = tk.PhotoImage(file=str(path))
        if size > 16:
            scale = max(1, size // 16)
            img = img.zoom(scale, scale)
        elif size < 16:
            scale = max(1, 16 // size)
            img = img.subsample(scale, scale)
        _IMAGE_CACHE[cache_key] = img
        return img
    except Exception:
        return None


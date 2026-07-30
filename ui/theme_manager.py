"""Theme bootstrap for CustomTkinter.

Maps the 5 v2 palette names to the JSON theme files under ``ui/themes/``.
``set_default_color_theme`` accepts a path to a JSON file — we resolve
the user's chosen palette name → path on startup and on every switch.

Spec §5 note: CustomTkinter's theming is less granular than Qt's
QPalette. The following v2 color roles have NO clean CTk equivalent and
are dropped silently:
  - QPalette.ToolTipBase / ToolTipText  (CTk has no tooltip widget)
  - QPalette.BrightText                 (no bright-text role)
  - QPalette.PlaceholderText            (folded into CTkEntry's
                                          placeholder_text_color)
  - per-state alternate row colors      (CTkScrollableFrame is flat)
These are flagged in DECISIONS.md so they're not silently lost.
"""
from __future__ import annotations

from pathlib import Path

import customtkinter as ctk


THEMES_DIR = Path(__file__).parent / "themes"

# Display name -> JSON file basename.
THEMES = {
    "Modern Dark": "modern_dark.json",
    "Moonlit Slate": "moonlit_slate.json",
    "Paper Daylight": "paper_daylight.json",
    "Mist Garden": "mist_garden.json",
    "Clear Contrast": "clear_contrast.json",
}


def theme_path(display_name: str) -> Path | None:
    """Resolve a display name to a JSON theme file path. Returns ``None``
    if the name is unknown (caller falls back to default)."""
    basename = THEMES.get(display_name)
    if not basename:
        return None
    path = THEMES_DIR / basename
    return path if path.exists() else None


def apply_theme(display_name: str) -> str:
    """Apply a theme by display name. Returns the name actually applied
    (may differ from input if the requested theme file is missing — we
    fall back to ``Modern Dark`` rather than crash).
    """
    path = theme_path(display_name)
    if path is None:
        # Fall back silently. Log it so the user can spot a typo.
        print(f"[theme] Unknown theme {display_name!r}, falling back to Modern Dark")
        path = theme_path("Modern Dark")
        display_name = "Modern Dark"
    if path is None:  # pragma: no cover
        # Both the requested theme AND Modern Dark are missing — let
        # CTk use its built-in default. This is a deployment bug.
        return ctk.get_default_color_theme() or "blue"
    ctk.set_default_color_theme(str(path))
    return display_name

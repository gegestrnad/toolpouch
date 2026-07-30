"""One-shot generator that writes the 5 CTk theme JSON files using the
default ``blue.json`` as a structural template and substituting palette
colors in the ``["light", "dark"]`` list form CTk expects.

Re-run any time the palettes change:
    python3 scripts/build_themes.py
"""
from __future__ import annotations

import json
from pathlib import Path

THEMES_DIR = Path(__file__).parent.parent / "ui" / "themes"

# CTk's default blue theme is the structural template. We copy every
# non-color key (corner_radius, border_width, button_length, etc.) from
# it unchanged, and override only the color keys per palette below.
def _find_ctk_template() -> Path | None:
    """Locate CTk's default ``blue.json`` theme file dynamically.

    CustomTkinter stores its theme JSONs under ``assets/themes/`` next
    to its ``__init__.py``. We resolve the path at runtime so this
    script works on any machine, not just the original developer's.
    """
    try:
        import customtkinter as ctk
        ctk_dir = Path(ctk.__file__).parent
        candidates = [
            ctk_dir / "assets" / "themes" / "blue.json",
            ctk_dir.parent / "assets" / "themes" / "blue.json",
        ]
        for c in candidates:
            if c.exists():
                return c
    except Exception:
        pass
    return None


_TEMPLATE_PATH = _find_ctk_template()
TEMPLATE = json.loads(_TEMPLATE_PATH.read_text()) if _TEMPLATE_PATH else None


# Each palette defines a light-mode and dark-mode variant. The two modes
# must be visually distinguishable (CTk picks one based on system setting
# or ``set_appearance_mode``), but the palette identity stays the same
# (e.g. "Modern Dark" is primarily a dark theme but has a usable light
# variant for users who run CTk in light mode).
#
# Color keys per palette:
#   bg_root        - CTk + CTkToplevel fg_color
#   bg_frame       - CTkFrame fg_color
#   bg_frame_top   - CTkFrame top_fg_color
#   border         - border_color
#   accent         - primary button accent
#   accent_hover   - button hover
#   accent_border  - button border
#   on_accent      - text on accent (button text)
#   on_accent_dis  - disabled button text
#   input_bg       - entry/input background
#   input_text     - entry text color
#   placeholder    - entry placeholder text color
#   text           - default label text
#   text_disabled  - disabled label text
#   log_bg         - log textbox background (darker than input_bg)
#   progress_track - progress bar empty track
PALETTES = {
    "modern_dark": {
        "light": {"bg_root": "#efeafe", "bg_frame": "#e7e2f8", "bg_frame_top": "#ffffff", "border": "#c7c0e6",
                  "accent": "#7c3aed", "accent_hover": "#6d28d9", "accent_border": "#5b21b6",
                  "on_accent": "#ffffff", "on_accent_dis": "#9ca3af",
                  "input_bg": "#ffffff", "input_text": "#1e1e2e", "placeholder": "#9ca3af",
                  "text": "#1e1e2e", "text_disabled": "#9ca3af",
                  "log_bg": "#f5f3fb", "progress_track": "#d6cdf2"},
        "dark":  {"bg_root": "#1e1e2e", "bg_frame": "#1e1e2e", "bg_frame_top": "#2a2a3c", "border": "#3a3a4e",
                  "accent": "#7c3aed", "accent_hover": "#6d28d9", "accent_border": "#5b21b6",
                  "on_accent": "#ffffff", "on_accent_dis": "#6b7280",
                  "input_bg": "#2a2a3c", "input_text": "#e5e7eb", "placeholder": "#6b7280",
                  "text": "#e5e7eb", "text_disabled": "#6b7280",
                  "log_bg": "#181828", "progress_track": "#2a2a3c"},
    },
    "moonlit_slate": {
        "light": {"bg_root": "#e8f0fa", "bg_frame": "#d9e6f5", "bg_frame_top": "#ffffff", "border": "#a5c4e3",
                  "accent": "#0ea5e9", "accent_hover": "#0284c7", "accent_border": "#0369a1",
                  "on_accent": "#ffffff", "on_accent_dis": "#94a3b8",
                  "input_bg": "#ffffff", "input_text": "#0f172a", "placeholder": "#94a3b8",
                  "text": "#0f172a", "text_disabled": "#94a3b8",
                  "log_bg": "#f1f5f9", "progress_track": "#c9d8ec"},
        "dark":  {"bg_root": "#0f172a", "bg_frame": "#0f172a", "bg_frame_top": "#1e293b", "border": "#334155",
                  "accent": "#0ea5e9", "accent_hover": "#0284c7", "accent_border": "#0369a1",
                  "on_accent": "#ffffff", "on_accent_dis": "#64748b",
                  "input_bg": "#1e293b", "input_text": "#f1f5f9", "placeholder": "#64748b",
                  "text": "#f1f5f9", "text_disabled": "#64748b",
                  "log_bg": "#020617", "progress_track": "#1e293b"},
    },
    "paper_daylight": {
        "light": {"bg_root": "#fafaf7", "bg_frame": "#f5f4f0", "bg_frame_top": "#ffffff", "border": "#e7e5e4",
                  "accent": "#1f2937", "accent_hover": "#374151", "accent_border": "#111827",
                  "on_accent": "#ffffff", "on_accent_dis": "#9ca3af",
                  "input_bg": "#ffffff", "input_text": "#1c1917", "placeholder": "#78716c",
                  "text": "#1c1917", "text_disabled": "#9ca3af",
                  "log_bg": "#ffffff", "progress_track": "#e7e5e4"},
        "dark":  {"bg_root": "#1c1917", "bg_frame": "#1c1917", "bg_frame_top": "#292524", "border": "#44403c",
                  "accent": "#e7e5e4", "accent_hover": "#d6d3d1", "accent_border": "#a8a29e",
                  "on_accent": "#1c1917", "on_accent_dis": "#78716c",
                  "input_bg": "#292524", "input_text": "#fafaf7", "placeholder": "#78716c",
                  "text": "#fafaf7", "text_disabled": "#78716c",
                  "log_bg": "#0c0a09", "progress_track": "#44403c"},
    },
    "mist_garden": {
        "light": {"bg_root": "#f3f7f4", "bg_frame": "#e3efe7", "bg_frame_top": "#ffffff", "border": "#d1ead7",
                  "accent": "#10b981", "accent_hover": "#059669", "accent_border": "#047857",
                  "on_accent": "#ffffff", "on_accent_dis": "#9ca3af",
                  "input_bg": "#ffffff", "input_text": "#064e3b", "placeholder": "#6ee7b7",
                  "text": "#064e3b", "text_disabled": "#9ca3af",
                  "log_bg": "#ffffff", "progress_track": "#d1ead7"},
        "dark":  {"bg_root": "#0c1f17", "bg_frame": "#0c1f17", "bg_frame_top": "#14302a", "border": "#1f4d3c",
                  "accent": "#10b981", "accent_hover": "#059669", "accent_border": "#047857",
                  "on_accent": "#ffffff", "on_accent_dis": "#6b7280",
                  "input_bg": "#14302a", "input_text": "#a7f3d0", "placeholder": "#6ee7b7",
                  "text": "#a7f3d0", "text_disabled": "#6b7280",
                  "log_bg": "#06120e", "progress_track": "#1f4d3c"},
    },
    "clear_contrast": {
        "light": {"bg_root": "#ffffff", "bg_frame": "#ffffff", "bg_frame_top": "#f5f5f5", "border": "#000000",
                  "accent": "#000000", "accent_hover": "#1a1a1a", "accent_border": "#000000",
                  "on_accent": "#ffffff", "on_accent_dis": "#666666",
                  "input_bg": "#ffffff", "input_text": "#000000", "placeholder": "#666666",
                  "text": "#000000", "text_disabled": "#666666",
                  "log_bg": "#ffffff", "progress_track": "#cccccc"},
        "dark":  {"bg_root": "#000000", "bg_frame": "#000000", "bg_frame_top": "#0a0a0a", "border": "#ffffff",
                  "accent": "#ffffff", "accent_hover": "#e5e5e5", "accent_border": "#ffffff",
                  "on_accent": "#000000", "on_accent_dis": "#666666",
                  "input_bg": "#0a0a0a", "input_text": "#ffffff", "placeholder": "#999999",
                  "text": "#ffffff", "text_disabled": "#666666",
                  "log_bg": "#000000", "progress_track": "#1a1a1a"},
    },
}


def c(palette: dict, key: str) -> list[str]:
    """Return ``[light, dark]`` list for a color key."""
    return [palette["light"][key], palette["dark"][key]]


def build_theme(name: str) -> dict:
    """Build a complete CTk theme dict by overlaying the palette onto
    the default blue theme's structural keys (corner_radius, etc.).
    """
    p = PALETTES[name]
    base = json.loads(json.dumps(TEMPLATE)) if TEMPLATE else {}

    # Root + Toplevel
    base["CTk"]["fg_color"] = c(p, "bg_root")
    base["CTkToplevel"]["fg_color"] = c(p, "bg_root")

    # Frame
    base["CTkFrame"]["fg_color"] = c(p, "bg_frame")
    base["CTkFrame"]["top_fg_color"] = c(p, "bg_frame_top")
    base["CTkFrame"]["border_color"] = c(p, "border")

    # Button
    base["CTkButton"]["fg_color"] = c(p, "accent")
    base["CTkButton"]["hover_color"] = c(p, "accent_hover")
    base["CTkButton"]["border_color"] = c(p, "accent_border")
    base["CTkButton"]["text_color"] = c(p, "on_accent")
    base["CTkButton"]["text_color_disabled"] = c(p, "on_accent_dis")

    # Label
    base["CTkLabel"]["text_color"] = c(p, "text")

    # Entry
    base["CTkEntry"]["fg_color"] = c(p, "input_bg")
    base["CTkEntry"]["border_color"] = c(p, "border")
    base["CTkEntry"]["text_color"] = c(p, "input_text")
    base["CTkEntry"]["placeholder_text_color"] = c(p, "placeholder")

    # OptionMenu
    base["CTkOptionMenu"]["fg_color"] = c(p, "input_bg")
    base["CTkOptionMenu"]["button_color"] = c(p, "accent")
    base["CTkOptionMenu"]["button_hover_color"] = c(p, "accent_hover")
    base["CTkOptionMenu"]["text_color"] = c(p, "input_text")
    base["CTkOptionMenu"]["text_color_disabled"] = c(p, "text_disabled")
    base["DropdownMenu"]["fg_color"] = c(p, "input_bg")
    base["DropdownMenu"]["hover_color"] = c(p, "bg_frame_top")
    base["DropdownMenu"]["text_color"] = c(p, "input_text")

    # ProgressBar
    base["CTkProgressBar"]["fg_color"] = c(p, "progress_track")
    base["CTkProgressBar"]["progress_color"] = c(p, "accent")
    base["CTkProgressBar"]["border_color"] = c(p, "border")

    # Textbox (log console)
    base["CTkTextbox"]["fg_color"] = c(p, "log_bg")
    base["CTkTextbox"]["border_color"] = c(p, "border")
    base["CTkTextbox"]["text_color"] = c(p, "text")
    base["CTkTextbox"]["scrollbar_button_color"] = c(p, "border")
    base["CTkTextbox"]["scrollbar_button_hover_color"] = c(p, "accent")

    # ScrollableFrame
    base["CTkScrollableFrame"]["label_fg_color"] = c(p, "bg_frame_top")

    # CheckBox
    base["CTkCheckBox"]["fg_color"] = c(p, "accent")
    base["CTkCheckBox"]["border_color"] = c(p, "border")
    base["CTkCheckBox"]["hover_color"] = c(p, "accent_hover")
    base["CTkCheckBox"]["checkmark_color"] = c(p, "on_accent")
    base["CTkCheckBox"]["text_color"] = c(p, "text")
    base["CTkCheckBox"]["text_color_disabled"] = c(p, "text_disabled")

    # Switch
    base["CTkSwitch"]["fg_color"] = c(p, "progress_track")
    base["CTkSwitch"]["progress_color"] = c(p, "accent")
    base["CTkSwitch"]["border_color"] = c(p, "border")
    base["CTkSwitch"]["button_color"] = c(p, "text")
    base["CTkSwitch"]["button_hover_color"] = c(p, "text_disabled")
    base["CTkSwitch"]["text_color"] = c(p, "text")
    base["CTkSwitch"]["text_color_disabled"] = c(p, "text_disabled")

    # SegmentedButton
    base["CTkSegmentedButton"]["fg_color"] = c(p, "input_bg")
    base["CTkSegmentedButton"]["selected_color"] = c(p, "accent")
    base["CTkSegmentedButton"]["selected_hover_color"] = c(p, "accent_hover")
    base["CTkSegmentedButton"]["unselected_color"] = c(p, "input_bg")
    base["CTkSegmentedButton"]["unselected_hover_color"] = c(p, "bg_frame_top")
    base["CTkSegmentedButton"]["text_color"] = c(p, "input_text")
    base["CTkSegmentedButton"]["text_color_disabled"] = c(p, "text_disabled")

    # Scrollbar
    base["CTkScrollbar"]["button_color"] = c(p, "border")
    base["CTkScrollbar"]["button_hover_color"] = c(p, "accent")

    # ComboBox (not used but kept for completeness)
    base["CTkComboBox"]["fg_color"] = c(p, "input_bg")
    base["CTkComboBox"]["border_color"] = c(p, "border")
    base["CTkComboBox"]["button_color"] = c(p, "border")
    base["CTkComboBox"]["button_hover_color"] = c(p, "accent")
    base["CTkComboBox"]["text_color"] = c(p, "input_text")
    base["CTkComboBox"]["text_color_disabled"] = c(p, "text_disabled")

    # Slider (not used but kept for completeness)
    base["CTkSlider"]["fg_color"] = c(p, "progress_track")
    base["CTkSlider"]["progress_color"] = c(p, "border")
    base["CTkSlider"]["button_color"] = c(p, "accent")
    base["CTkSlider"]["button_hover_color"] = c(p, "accent_hover")

    # RadioButton (not used but kept for completeness)
    base["CTkRadioButton"]["fg_color"] = c(p, "accent")
    base["CTkRadioButton"]["border_color"] = c(p, "border")
    base["CTkRadioButton"]["hover_color"] = c(p, "accent_hover")
    base["CTkRadioButton"]["text_color"] = c(p, "text")
    base["CTkRadioButton"]["text_color_disabled"] = c(p, "text_disabled")

    return base


def main() -> None:
    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    for name in PALETTES:
        path = THEMES_DIR / f"{name}.json"
        theme = build_theme(name)
        path.write_text(json.dumps(theme, indent=2), encoding="utf-8")
        print(f"wrote {path}")
    print(f"\nAll {len(PALETTES)} themes rebuilt.")


if __name__ == "__main__":
    main()

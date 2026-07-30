"""Generate PNG language icons from SVG definitions.

Each icon is a 16x16 rounded square with the language's brand color
background and a white monogram letter. Used in the sidebar next to
each tool name instead of the ``[PY]`` / ``[BAT]`` text badges.

Run any time the icon definitions change:
    python3 scripts/build_lang_icons.py
"""
from __future__ import annotations

import cairosvg
from pathlib import Path

OUT_DIR = Path(__file__).parent.parent / "assets" / "lang_icons"


# Each icon: (filename, bg_color, letter, letter_color)
# Colors loosely match each language's official brand identity.
ICONS = [
    ("python.png",   "#3776ab", "Py", "#ffd43b"),  # Python blue + yellow
    ("powershell.png", "#012456", "PS", "#ffffff"),  # PowerShell navy + white
    ("batch.png",    "#4c5256", "BAT", "#ffffff"),  # neutral dark gray
    ("node.png",     "#339933", "JS", "#ffffff"),   # green (Node's brand is green)
    ("unknown.png",  "#6b7280", "?",  "#ffffff"),   # gray fallback
]


SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
  <rect width="16" height="16" rx="3" ry="3" fill="{bg}"/>
  <text x="8" y="11" text-anchor="middle"
        font-family="Segoe UI, Arial, sans-serif"
        font-size="{font_size}"
        font-weight="bold"
        fill="{fg}">{letter}</text>
</svg>"""


def font_size_for(letter: str) -> int:
    """Smaller font for 3-letter monograms so they fit in 16x16."""
    if len(letter) >= 3:
        return 5
    if len(letter) == 2:
        return 7
    return 9


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, bg, letter, fg in ICONS:
        svg = SVG_TEMPLATE.format(
            bg=bg,
            fg=fg,
            letter=letter,
            font_size=font_size_for(letter),
        )
        out_path = OUT_DIR / filename
        cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(out_path), output_width=16, output_height=16)
        print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")
    print(f"\nAll {len(ICONS)} language icons generated in {OUT_DIR}")


if __name__ == "__main__":
    main()

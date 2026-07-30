"""
Regex Extractor
Usage: python regex_extractor.py --input_dir <path> [--file_glob <glob>] --preset <preset> [--pattern <regex>]
"""
import argparse
import csv
import re
import sys
from pathlib import Path


PRESETS = {
    "emails": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "urls": r"https?://[^\s<>\"]+",
    "markdown headings": r"^(#{1,6})\s+(.+)$",
}


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Extract regex matches from text files")
    parser.add_argument("--input_dir", required=True, help="Folder containing files")
    parser.add_argument("--file_glob", default="*.txt", help="File glob, for example *.txt or *.md")
    parser.add_argument("--preset", default="emails", choices=["custom", "emails", "urls", "markdown headings"])
    parser.add_argument("--pattern", default="", help="Custom regex used when preset is custom")
    parser.add_argument("--output_file", default="", help="Output CSV file")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"[ERROR] Folder not found: {input_dir}")
        sys.exit(1)

    pattern = args.pattern if args.preset == "custom" else PRESETS[args.preset]
    if not pattern:
        print("[ERROR] Custom preset requires a regex pattern.")
        sys.exit(1)

    try:
        regex = re.compile(pattern, flags=re.MULTILINE)
    except re.error as e:
        print(f"[ERROR] Invalid regex pattern: {e}")
        sys.exit(1)

    files = sorted(path for path in input_dir.glob(args.file_glob or "*.txt") if path.is_file())
    if not files:
        print(f"[ERROR] No files matching '{args.file_glob or '*.txt'}' found in {input_dir}")
        sys.exit(1)

    output_file = Path(args.output_file) if args.output_file else input_dir / "extracted_matches.csv"
    print(f"Found {len(files)} file(s). Writing matches to {output_file}", flush=True)
    progress(0)

    rows = []
    for i, path in enumerate(files):
        pct = int(((i + 1) / len(files)) * 100)
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            file_matches = 0
            for match in regex.finditer(text):
                line_number = text.count("\n", 0, match.start()) + 1
                value = match.group(0)
                groups = " | ".join(group for group in match.groups() if group is not None)
                rows.append([path.name, line_number, value, groups])
                file_matches += 1
            print(f"[OK] {path.name}: {file_matches} match(es)", flush=True)
        except Exception as e:
            print(f"[ERROR] {path.name}: {e}", flush=True)
        progress(pct)

    try:
        with output_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["file", "line", "match", "groups"])
            writer.writerows(rows)
    except Exception as e:
        print(f"[ERROR] Could not write output CSV: {e}")
        sys.exit(1)

    print(f"[OK] Done. Extracted {len(rows)} match(es).", flush=True)


if __name__ == "__main__":
    main()

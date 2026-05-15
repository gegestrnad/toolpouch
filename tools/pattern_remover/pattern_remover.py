"""
Pattern Remover
Usage: python pattern_remover.py --input_dir <path> --pattern <regex> [--replacement <str>] [--file_glob <glob>]
"""
import re
import sys
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Remove or replace regex patterns in text files")
    parser.add_argument("--input_dir", required=True, help="Folder containing files")
    parser.add_argument("--pattern", required=True, help="Regex pattern to match")
    parser.add_argument("--replacement", default="", help="Replacement string (default: delete match)")
    parser.add_argument("--file_glob", default="*.txt", help="File glob: *.txt | *.md | *.txt and *.md")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"[ERROR] Folder not found: {input_dir}")
        sys.exit(1)

    try:
        pattern = re.compile(args.pattern)
    except re.error as e:
        print(f"[ERROR] Invalid regex pattern: {e}")
        sys.exit(1)

    glob_str = args.file_glob
    if glob_str == "*.txt and *.md":
        files = list(input_dir.glob("*.txt")) + list(input_dir.glob("*.md"))
    else:
        files = list(input_dir.glob(glob_str))

    if not files:
        print(f"[ERROR] No files matching '{glob_str}' found in {input_dir}")
        sys.exit(1)

    replacement = args.replacement
    print(f"Pattern: {args.pattern}", flush=True)
    print(f"Replacement: '{replacement}' ({'delete' if not replacement else replacement})", flush=True)
    print(f"Found {len(files)} file(s).", flush=True)
    progress(0)

    changed = 0
    for i, path in enumerate(files):
        pct = int(((i + 1) / len(files)) * 100)
        try:
            text = path.read_text(encoding="utf-8")
            new_text = pattern.sub(replacement, text)
            if new_text != text:
                path.write_text(new_text, encoding="utf-8")
                print(f"[OK] Updated: {path.name}", flush=True)
                changed += 1
            else:
                print(f"[OK] No match: {path.name}", flush=True)
        except Exception as e:
            print(f"[ERROR] {path.name}: {e}", flush=True)
        progress(pct)

    print(f"Done. {changed}/{len(files)} file(s) modified.", flush=True)


if __name__ == "__main__":
    main()

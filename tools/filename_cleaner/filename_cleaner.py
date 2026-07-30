"""
Filename Cleaner
Usage: python filename_cleaner.py --input_dir <path> [--file_glob <glob>] [--style <style>] [--mode <preview|rename>]
"""
import argparse
import re
import sys
from pathlib import Path


RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def clean_stem(stem: str, style: str) -> str:
    cleaned = stem.strip()

    if style == "spaces to underscores only":
        cleaned = re.sub(r"\s+", "_", cleaned)
    else:
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
        cleaned = cleaned.replace(" ", "_")
        cleaned = re.sub(r"_+", "_", cleaned)
        if style == "safe lowercase":
            cleaned = cleaned.lower()

    if not cleaned:
        cleaned = "file"
    if cleaned.upper() in RESERVED_NAMES:
        cleaned = f"{cleaned}_file"
    return cleaned


def unique_target(path: Path, new_name: str) -> Path:
    candidate = path.with_name(new_name)
    if candidate == path or not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        numbered = path.with_name(f"{stem}_{counter}{suffix}")
        if not numbered.exists():
            return numbered
        counter += 1


def main():
    parser = argparse.ArgumentParser(description="Clean filenames in a folder")
    parser.add_argument("--input_dir", required=True, help="Folder containing files to rename")
    parser.add_argument("--file_glob", default="*.*", help="File glob, for example *.txt")
    parser.add_argument(
        "--style",
        default="safe preserve case",
        choices=["safe preserve case", "safe lowercase", "spaces to underscores only"],
    )
    parser.add_argument("--mode", default="preview", choices=["preview", "rename"])
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"[ERROR] Folder not found: {input_dir}")
        sys.exit(1)

    files = sorted(path for path in input_dir.glob(args.file_glob or "*.*") if path.is_file())
    if not files:
        print(f"[ERROR] No files matching '{args.file_glob or '*.*'}' found in {input_dir}")
        sys.exit(1)

    print(f"Found {len(files)} file(s). Mode: {args.mode}.", flush=True)
    progress(0)

    changed = 0
    for i, path in enumerate(files):
        pct = int(((i + 1) / len(files)) * 100)
        try:
            cleaned_name = clean_stem(path.stem, args.style) + path.suffix.strip()
            target = unique_target(path, cleaned_name)

            if target == path:
                print(f"[OK] Already clean: {path.name}", flush=True)
            elif args.mode == "preview":
                print(f"[OK] Preview: {path.name} -> {target.name}", flush=True)
                changed += 1
            else:
                path.rename(target)
                print(f"[OK] Renamed: {path.name} -> {target.name}", flush=True)
                changed += 1
        except Exception as e:
            print(f"[ERROR] {path.name}: {e}", flush=True)

        progress(pct)

    action = "would change" if args.mode == "preview" else "changed"
    print(f"[OK] Done. {changed}/{len(files)} file(s) {action}.", flush=True)


if __name__ == "__main__":
    main()

"""
TXT Splitter
Usage: python txt_splitter.py --input_file <path> [--output_dir <path>] --split_by <mode>
"""
import argparse
import math
import re
import sys
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def write_part(output_dir: Path, stem: str, index: int, content: str) -> Path:
    output_path = output_dir / f"{stem}_part_{index:03d}.txt"
    output_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return output_path


def split_by_lines(text: str, size: int) -> list[str]:
    lines = text.splitlines()
    return ["\n".join(lines[i:i + size]) for i in range(0, len(lines), size)]


def split_by_characters(text: str, size: int) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)]


def split_by_chapter_marker(text: str, pattern: str) -> list[str]:
    regex = re.compile(pattern, flags=re.MULTILINE)
    matches = list(regex.finditer(text))
    if not matches:
        return []

    parts = []
    if matches[0].start() > 0 and text[:matches[0].start()].strip():
        parts.append(text[:matches[0].start()])

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        parts.append(text[start:end])

    return parts


def main():
    parser = argparse.ArgumentParser(description="Split a TXT file into smaller files")
    parser.add_argument("--input_file", required=True, help="TXT file to split")
    parser.add_argument("--output_dir", default="", help="Output folder")
    parser.add_argument("--split_by", default="lines", choices=["lines", "characters", "chapter marker"])
    parser.add_argument("--size", default="1000", help="Lines or characters per part")
    parser.add_argument("--chapter_pattern", default=r"^Chapter\s+\d+", help="Regex used for chapter marker mode")
    args = parser.parse_args()

    input_file = Path(args.input_file)
    if not input_file.exists():
        print(f"[ERROR] File not found: {input_file}")
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else input_file.with_name(f"{input_file.stem}_parts")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        text = input_file.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"[ERROR] Could not read {input_file.name}: {e}")
        sys.exit(1)

    if args.split_by in ("lines", "characters"):
        try:
            size = max(1, int(args.size or "1000"))
        except ValueError:
            print("[ERROR] Size must be a whole number.")
            sys.exit(1)
        parts = split_by_lines(text, size) if args.split_by == "lines" else split_by_characters(text, size)
    else:
        try:
            parts = split_by_chapter_marker(text, args.chapter_pattern or r"^Chapter\s+\d+")
        except re.error as e:
            print(f"[ERROR] Invalid chapter regex: {e}")
            sys.exit(1)
        if not parts:
            print("[ERROR] No chapter markers matched the selected regex.")
            sys.exit(1)

    parts = [part for part in parts if part.strip()]
    if not parts:
        print("[ERROR] No content found to split.")
        sys.exit(1)

    print(f"Writing {len(parts)} part(s) to {output_dir}", flush=True)
    progress(0)

    total = max(1, len(parts))
    for index, part in enumerate(parts, start=1):
        try:
            output_path = write_part(output_dir, input_file.stem, index, part)
            print(f"[OK] Created: {output_path.name}", flush=True)
        except Exception as e:
            print(f"[ERROR] Part {index}: {e}", flush=True)
        progress(math.floor((index / total) * 100))

    print(f"[OK] Done. Created {len(parts)} file(s).", flush=True)


if __name__ == "__main__":
    main()

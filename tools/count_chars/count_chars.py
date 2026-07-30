"""Count Characters - Count characters, words, and lines."""
import sys
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Count characters, words, lines")
    parser.add_argument("--input_file", required=True, help="Input file")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    progress(10)

    text = input_path.read_text(encoding="utf-8", errors="ignore")
    progress(50)

    lines = text.splitlines()
    total_lines = len(lines)
    non_empty_lines = sum(1 for l in lines if l.strip())
    words = text.split()
    total_words = len(words)
    total_chars = len(text)
    chars_no_spaces = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))

    progress(90)

    print(f"File: {input_path.name}", flush=True)
    print(f"  Lines:           {total_lines:>10}", flush=True)
    print(f"  Non-empty lines: {non_empty_lines:>10}", flush=True)
    print(f"  Words:           {total_words:>10}", flush=True)
    print(f"  Characters:      {total_chars:>10}", flush=True)
    print(f"  Chars (no space):{chars_no_spaces:>10}", flush=True)
    print(f"  File size:       {input_path.stat().st_size:>8} bytes", flush=True)

    progress(100)
    print(f"[OK] Counts complete for {input_path.name}", flush=True)


if __name__ == "__main__":
    main()

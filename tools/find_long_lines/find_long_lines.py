"""Find Long Lines - Detect lines exceeding a character limit."""
import sys
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Find lines exceeding max length")
    parser.add_argument("--file", required=True, help="Input text file")
    parser.add_argument("--max_length", type=int, default=80, help="Max line length")
    args = parser.parse_args()

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    progress(10)

    lines = input_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    total = len(lines)

    if total == 0:
        print("[WARN] File is empty")
        progress(100)
        return

    progress(20)

    long_lines = []
    for i, line in enumerate(lines):
        if len(line) > args.max_length:
            long_lines.append((i + 1, len(line), line[:120]))
        pct = 20 + int((i / total) * 70)
        progress(pct)

    progress(95)

    if not long_lines:
        print(f"[OK] No lines exceed {args.max_length} characters")
    else:
        print(f"[WARN] Found {len(long_lines)} lines exceeding {args.max_length} chars:")
        for line_num, length, preview in long_lines[:50]:
            print(f"  Line {line_num} ({length} chars): {preview}...")
        if len(long_lines) > 50:
            print(f"  ... and {len(long_lines) - 50} more")

    progress(100)
    print(f"[OK] Scanned {total} lines in {input_path.name}", flush=True)


if __name__ == "__main__":
    main()

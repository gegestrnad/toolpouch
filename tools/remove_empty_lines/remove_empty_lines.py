"""Remove Empty Lines - Strip blank lines from text files."""
import sys
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Remove empty lines from text file")
    parser.add_argument("--input_file", required=True, help="Input text file")
    parser.add_argument("--output_file", default="", help="Output file (empty = overwrite)")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    progress(10)

    text = input_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    total = len(lines)

    progress(30)

    non_empty = [line for line in lines if line.strip()]
    removed = total - len(non_empty)

    progress(70)

    output_path = Path(args.output_file) if args.output_file.strip() else input_path
    output_path.write_text("\n".join(non_empty) + "\n", encoding="utf-8")

    progress(100)
    print(f"[OK] Removed {removed} empty lines ({total} -> {len(non_empty)})", flush=True)
    print(f"[OK] Output: {output_path.name}", flush=True)


if __name__ == "__main__":
    main()

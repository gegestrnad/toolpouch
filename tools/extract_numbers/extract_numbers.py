"""Extract Numbers - Pull all numbers from a text file."""
import sys
import re
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Extract numbers from text")
    parser.add_argument("--input_file", required=True, help="Input text file")
    parser.add_argument("--output_file", default="numbers_extracted.txt", help="Output file")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    progress(10)

    text = input_path.read_text(encoding="utf-8", errors="ignore")
    progress(30)

    # Match integers and decimals (including negatives)
    numbers = re.findall(r'-?\d+\.?\d*', text)
    progress(60)

    if not numbers:
        print("[WARN] No numbers found in the file")
        output_path = Path(args.output_file) if args.output_file.strip() else input_path.with_name("numbers_extracted.txt")
        output_path.write_text("", encoding="utf-8")
        progress(100)
        return

    progress(80)

    output_path = Path(args.output_file) if args.output_file.strip() else input_path.with_name("numbers_extracted.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        for num in numbers:
            f.write(num + "\n")

    progress(100)
    print(f"[OK] Extracted {len(numbers)} numbers to {output_path.name}", flush=True)


if __name__ == "__main__":
    main()

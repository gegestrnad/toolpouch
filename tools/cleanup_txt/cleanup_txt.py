"""
Cleanup TXT
Usage: python cleanup_txt.py --input_dir <path>
"""
import re
import sys
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Clean whitespace and blank lines from TXT files")
    parser.add_argument("--input_dir", required=True, help="Folder containing .txt files")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"[ERROR] Folder not found: {input_dir}")
        sys.exit(1)

    txt_files = list(input_dir.glob("*.txt"))
    if not txt_files:
        print("[ERROR] No .txt files found in the specified folder.")
        sys.exit(1)

    print(f"Found {len(txt_files)} file(s).", flush=True)
    progress(0)

    for i, txt_file in enumerate(txt_files):
        pct = int(((i + 1) / len(txt_files)) * 100)
        try:
            with txt_file.open("r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            cleaned = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                line = re.sub(r"\s+", " ", line)
                cleaned.append(line)

            with txt_file.open("w", encoding="utf-8") as f:
                f.write("\n".join(cleaned))

            print(f"[OK] Cleaned: {txt_file.name}", flush=True)

        except Exception as e:
            print(f"[ERROR] {txt_file.name}: {e}", flush=True)

        progress(pct)

    print("Done.", flush=True)


if __name__ == "__main__":
    main()

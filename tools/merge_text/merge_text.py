"""
Merge Text
Usage: python merge_text.py --input_dir <path> [--output_file <filename>]
"""
import sys
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Merge all TXT files in a folder into one")
    parser.add_argument("--input_dir", required=True, help="Folder containing .txt files")
    parser.add_argument("--output_file", default="_merged.txt", help="Output filename (not full path)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"[ERROR] Folder not found: {input_dir}")
        sys.exit(1)

    output_name = args.output_file.strip() or "_merged.txt"
    output_path = input_dir / output_name

    txt_files = sorted(
        f for f in input_dir.glob("*.txt")
        if f.name != output_name
    )

    if not txt_files:
        print("[ERROR] No TXT files found in the specified folder.")
        sys.exit(1)

    print(f"Found {len(txt_files)} file(s). Merging into {output_name}...", flush=True)
    progress(0)

    with open(output_path, "w", encoding="utf-8") as outfile:
        for i, file in enumerate(txt_files):
            pct = int(((i + 1) / len(txt_files)) * 100)

            try:
                content = file.read_text(encoding="utf-8", errors="ignore").strip()
                outfile.write(f"===== {file.name} =====\n\n")
                outfile.write(content)
                outfile.write("\n\n")
                print(f"[OK] Merged: {file.name}", flush=True)
            except Exception as e:
                print(f"[ERROR] {file.name}: {e}", flush=True)

            progress(pct)

    print(f"[OK] Done. Created: {output_path}", flush=True)


if __name__ == "__main__":
    main()
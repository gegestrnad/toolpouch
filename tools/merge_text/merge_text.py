"""Merge Text - Combine multiple text files into one."""
import sys
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Merge text files into one")
    parser.add_argument("--input_dir", required=True, help="Directory with text files")
    parser.add_argument("--output_file", default="_merged.txt", help="Output filename")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"[ERROR] Directory not found: {input_dir}")
        sys.exit(1)

    progress(5)

    valid_suffixes = {".txt", ".md"}
    output_name = args.output_file.strip() or "_merged.txt"
    output_path = input_dir / output_name

    txt_files = sorted(
        f for f in input_dir.iterdir()
        if f.is_file()
        and f.suffix.lower() in valid_suffixes
        and f.resolve() != output_path.resolve()
    )

    if not txt_files:
        print("[ERROR] No TXT or Markdown files found")
        sys.exit(1)

    total = len(txt_files)
    print(f"[OK] Found {total} files to merge", flush=True)
    progress(10)

    with open(output_path, "w", encoding="utf-8") as out:
        for i, file in enumerate(txt_files):
            try:
                content = file.read_text(encoding="utf-8", errors="ignore").strip()
                out.write(f"===== {file.name} =====\n\n")
                out.write(content)
                out.write("\n\n")
                print(f"[OK] Merged: {file.name}", flush=True)
            except Exception as e:
                print(f"[ERROR] {file.name}: {e}", flush=True)

            pct = 10 + int(((i + 1) / total) * 80)
            progress(pct)

    progress(100)
    print(f"[OK] Created {output_path.name} ({output_path.stat().st_size} bytes)", flush=True)


if __name__ == "__main__":
    main()

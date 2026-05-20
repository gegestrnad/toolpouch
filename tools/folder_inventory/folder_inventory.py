"""
Folder Inventory
Usage: python folder_inventory.py --input_dir <path> --output_format <csv|md>
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def collect_files(input_dir: Path, include_subfolders: bool) -> list[Path]:
    pattern = "**/*" if include_subfolders else "*"
    return sorted(path for path in input_dir.glob(pattern) if path.is_file())


def file_row(input_dir: Path, path: Path) -> dict[str, str]:
    stat = path.stat()
    relative_path = path.relative_to(input_dir)
    return {
        "name": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": str(stat.st_size),
        "size_kb": f"{stat.st_size / 1024:.2f}",
        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "relative_path": str(relative_path),
        "full_path": str(path),
    }


def write_csv(output_file: Path, rows: list[dict[str, str]]):
    fieldnames = ["name", "extension", "size_bytes", "size_kb", "modified", "relative_path", "full_path"]
    with output_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(output_file: Path, rows: list[dict[str, str]], input_dir: Path):
    lines = [
        f"# Folder Inventory: {input_dir.name}",
        "",
        f"Generated for `{input_dir}`.",
        "",
        "| Name | Extension | Size KB | Modified | Relative Path |",
        "|---|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['name']} | {row['extension']} | {row['size_kb']} | "
            f"{row['modified']} | {row['relative_path']} |"
        )
    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export a folder inventory report")
    parser.add_argument("--input_dir", required=True, help="Folder to inventory")
    parser.add_argument("--output_format", default="csv", choices=["csv", "md"])
    parser.add_argument("--include_subfolders", default="yes", choices=["yes", "no"])
    parser.add_argument("--output_file", default="", help="Output report path")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"[ERROR] Folder not found: {input_dir}")
        sys.exit(1)

    include_subfolders = args.include_subfolders == "yes"
    files = collect_files(input_dir, include_subfolders)
    if not files:
        print("[ERROR] No files found in the selected folder.")
        sys.exit(1)

    output_file = Path(args.output_file) if args.output_file else input_dir / f"folder_inventory.{args.output_format}"
    print(f"Found {len(files)} file(s). Writing {args.output_format.upper()} report to {output_file}", flush=True)
    progress(0)

    rows = []
    for i, path in enumerate(files):
        try:
            rows.append(file_row(input_dir, path))
            print(f"[OK] Indexed: {path.relative_to(input_dir)}", flush=True)
        except Exception as e:
            print(f"[ERROR] {path.name}: {e}", flush=True)
        progress(int(((i + 1) / len(files)) * 100))

    try:
        if args.output_format == "csv":
            write_csv(output_file, rows)
        else:
            write_markdown(output_file, rows, input_dir)
    except Exception as e:
        print(f"[ERROR] Could not write report: {e}")
        sys.exit(1)

    print(f"[OK] Done. Created: {output_file}", flush=True)


if __name__ == "__main__":
    main()

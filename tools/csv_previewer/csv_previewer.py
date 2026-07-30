"""CSV Previewer - Display CSV contents in a formatted table."""
import sys
import csv
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Preview CSV files")
    parser.add_argument("--input_file", required=True, help="CSV file")
    parser.add_argument("--max_rows", type=int, default=10, help="Max rows to show")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    progress(10)

    with open(input_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            print("[WARN] CSV file is empty")
            progress(100)
            return

        rows = []
        for i, row in enumerate(reader):
            if i >= args.max_rows:
                break
            rows.append(row)

    progress(50)

    num_cols = len(headers)

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for j, cell in enumerate(row):
            if j < num_cols:
                col_widths[j] = max(col_widths[j], min(len(cell), 30))

    progress(70)

    # Print header
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * col_widths[i] for i in range(num_cols))

    print(header_line, flush=True)
    print(sep_line, flush=True)

    # Print rows
    for row in rows:
        line = " | ".join(row[j].ljust(col_widths[j]) if j < num_cols else "" for j in range(num_cols))
        print(line, flush=True)

    progress(100)

    # Count total rows
    with open(input_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        total_rows = sum(1 for _ in csv.reader(f)) - 1  # minus header

    print(f"\n[OK] Showing {len(rows)} of {total_rows} rows ({num_cols} columns)", flush=True)


if __name__ == "__main__":
    main()

"""JSON Formatter - Pretty-print or compact JSON."""
import sys
import json
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Format JSON files")
    parser.add_argument("--input_file", required=True, help="JSON file")
    parser.add_argument("--indent", type=int, default=4, help="Indentation spaces")
    parser.add_argument("--compact", action="store_true", help="Compact output")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    progress(10)

    raw = input_path.read_text(encoding="utf-8", errors="ignore")
    progress(30)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON: {e}")
        sys.exit(1)

    progress(60)

    if args.compact:
        output = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    else:
        output = json.dumps(data, indent=args.indent, ensure_ascii=False)

    progress(80)

    output_path = input_path.with_name(input_path.stem + "_formatted.json")
    output_path.write_text(output, encoding="utf-8")

    progress(100)

    mode = "compact" if args.compact else f"pretty (indent={args.indent})"
    print(f"[OK] Formatted {input_path.name} ({mode})", flush=True)
    print(f"[OK] Output: {output_path.name} ({len(output)} bytes)", flush=True)


if __name__ == "__main__":
    main()

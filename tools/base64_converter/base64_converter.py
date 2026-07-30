"""Base64 Converter - Encode or decode files using Base64."""
import sys
import base64
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Base64 encode/decode files")
    parser.add_argument("--input_file", required=True, help="Input file")
    parser.add_argument("--action", choices=["encode", "decode"], default="encode")
    parser.add_argument("--output_file", default="", help="Output file")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    progress(10)

    raw = input_path.read_bytes()
    progress(30)

    if args.action == "encode":
        result = base64.b64encode(raw).decode("ascii")
        suffix = ".b64"
        print(f"[OK] Encoded {len(raw)} bytes", flush=True)
    else:
        try:
            result = base64.b64decode(raw).decode("utf-8", errors="replace")
        except Exception:
            # Try raw bytes output
            decoded = base64.b64decode(raw)
            output_path = Path(args.output_file) if args.output_file.strip() else input_path.with_suffix("")
            output_path.write_bytes(decoded)
            progress(100)
            print(f"[OK] Decoded {len(raw)} bytes -> {output_path.name} ({len(decoded)} bytes)", flush=True)
            return
        suffix = ".decoded"
        print(f"[OK] Decoded {len(raw)} bytes", flush=True)

    progress(70)

    output_path = Path(args.output_file) if args.output_file.strip() else input_path.with_suffix(suffix)
    output_path.write_text(result, encoding="utf-8")

    progress(100)
    print(f"[OK] Output: {output_path.name} ({len(result)} chars)", flush=True)


if __name__ == "__main__":
    main()

"""HTML to Text - Convert HTML to plain text."""
import sys
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Convert HTML to plain text")
    parser.add_argument("--input_file", required=True, help="HTML file")
    parser.add_argument("--output_file", default="", help="Output file")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    progress(10)

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("[ERROR] beautifulsoup4 is required: pip install beautifulsoup4")
        sys.exit(1)

    html = input_path.read_text(encoding="utf-8", errors="ignore")
    progress(30)

    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for tag in soup(["script", "style"]):
        tag.decompose()

    progress(60)

    text = soup.get_text(separator="\n", strip=True)

    # Clean up excessive blank lines
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    cleaned = "\n".join(lines)

    progress(80)

    output_path = Path(args.output_file) if args.output_file.strip() else input_path.with_suffix(".txt")
    output_path.write_text(cleaned, encoding="utf-8")

    progress(100)
    print(f"[OK] Converted {input_path.name} -> {output_path.name}", flush=True)
    print(f"[OK] Extracted {len(cleaned)} characters of text", flush=True)


if __name__ == "__main__":
    main()

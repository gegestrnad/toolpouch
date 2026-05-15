"""
XHTML/HTML to TXT/MD Converter
Usage: python xhtml_converter.py --input_dir <path> --output_format <txt|md>
"""
import os
import re
import sys
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def convert_to_plain_text(content: str) -> str:
    content = re.sub(r'<\?xml[^>]*\?>', '', content)
    content = re.sub(r'<!DOCTYPE[^>]*>', '', content, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', content)
    text = re.sub(r'&[a-zA-Z]+;', '', text)
    text = re.sub(r'&#\d+;', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(line for line in lines if line)


def convert_to_markdown(content: str) -> str:
    content = re.sub(r'<\?xml[^>]*\?>', '', content)
    content = re.sub(r'<!DOCTYPE[^>]*>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.IGNORECASE | re.DOTALL)

    for i in range(6, 0, -1):
        content = re.sub(
            f'<h{i}[^>]*>(.*?)</h{i}>',
            lambda m: '\n' + '#' * i + ' ' + m.group(1).strip() + '\n',
            content, flags=re.IGNORECASE
        )

    content = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<br\s*/?>', '\n', content, flags=re.IGNORECASE)
    content = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<div[^>]*>(.*?)</div>', r'\1\n', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<[^>]+>', '', content)
    content = re.sub(r'&nbsp;', ' ', content)
    content = re.sub(r'&amp;', '&', content)
    content = re.sub(r'&lt;', '<', content)
    content = re.sub(r'&gt;', '>', content)
    content = re.sub(r'&[a-zA-Z]+;', '', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    lines = [line.rstrip() for line in content.split('\n')]
    return '\n'.join(line for line in lines if line)


def main():
    parser = argparse.ArgumentParser(description="Convert HTML/XHTML files to TXT or Markdown")
    parser.add_argument("--input_dir", required=True, help="Folder containing HTML/XHTML files")
    parser.add_argument("--output_format", default="txt", choices=["txt", "md"], help="Output format")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"[ERROR] Folder not found: {input_dir}")
        sys.exit(1)

    html_files = (
        list(input_dir.glob("*.html")) +
        list(input_dir.glob("*.htm")) +
        list(input_dir.glob("*.xhtml"))
    )

    if not html_files:
        print("[ERROR] No HTML, HTM, or XHTML files found in the specified folder.")
        sys.exit(1)

    out_format = args.output_format
    output_dir = input_dir / out_format
    output_dir.mkdir(exist_ok=True)

    print(f"Found {len(html_files)} file(s). Converting to .{out_format}...", flush=True)
    progress(0)

    for i, html_file in enumerate(html_files):
        pct = int(((i + 1) / len(html_files)) * 100)
        output_file = output_dir / (html_file.stem + f".{out_format}")

        try:
            content = html_file.read_text(encoding="utf-8", errors="replace")
            text = convert_to_plain_text(content) if out_format == "txt" else convert_to_markdown(content)
            output_file.write_text(text.strip(), encoding="utf-8")
            print(f"[OK] {html_file.name} -> {output_file.name}", flush=True)
        except Exception as e:
            print(f"[ERROR] {html_file.name}: {e}", flush=True)

        progress(pct)

    print(f"[OK] Done. {len(html_files)} file(s) converted to .{out_format} in {output_dir}", flush=True)


if __name__ == "__main__":
    main()

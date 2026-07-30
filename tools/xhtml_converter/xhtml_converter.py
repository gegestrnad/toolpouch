"""
XHTML/HTML to TXT/MD Converter
Usage: python xhtml_converter.py --input_dir <path> --output_format <txt|md>
"""
import re
import sys
import argparse
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString, Tag


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
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    root = soup.body or soup
    return normalize_markdown(render_blocks(root))


def normalize_inline(text: str, strip: bool = True) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip() if strip else text


def normalize_markdown(text: str) -> str:
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def render_inline(node) -> str:
    if isinstance(node, NavigableString):
        return normalize_inline(str(node), strip=False)
    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()
    if name == "br":
        return "\n"
    if name in {"strong", "b"}:
        text = render_inline_children(node)
        return f"**{text}**" if text else ""
    if name in {"em", "i"}:
        text = render_inline_children(node)
        return f"*{text}*" if text else ""
    if name == "code":
        text = node.get_text(" ", strip=True)
        return f"`{text}`" if text else ""
    if name == "a":
        href = (node.get("href") or "").strip()
        text = render_inline_children(node) or href
        return f"[{text}]({href})" if href and text else text
    if name == "img":
        alt = normalize_inline(node.get("alt") or "")
        return f"![{alt}]({node.get('src')})" if node.get("src") else alt

    return render_inline_children(node)


def render_inline_children(tag: Tag) -> str:
    return normalize_inline("".join(render_inline(child) for child in tag.children))


def render_blocks(container: Tag) -> str:
    blocks = []
    for child in container.children:
        block = render_block(child)
        if block:
            blocks.append(block)
    return "\n\n".join(blocks)


def render_block(node) -> str:
    if isinstance(node, NavigableString):
        return normalize_inline(str(node))
    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()
    if name in {"html", "body", "main", "article", "section", "div", "header", "footer"}:
        return render_blocks(node)
    if re.fullmatch(r"h[1-6]", name):
        level = int(name[1])
        text = render_inline_children(node)
        return f"{'#' * level} {text}" if text else ""
    if name == "p":
        return render_inline_children(node)
    if name == "blockquote":
        text = render_blocks(node) or render_inline_children(node)
        return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())
    if name == "pre":
        text = node.get_text("\n").rstrip()
        return f"```\n{text}\n```" if text else ""
    if name == "hr":
        return "---"
    if name in {"ul", "ol"}:
        return render_list(node, ordered=name == "ol")
    if name == "li":
        return f"- {render_inline_children(node)}"
    if name == "table":
        return render_table(node)
    if name == "br":
        return ""

    block_text = render_blocks(node)
    return block_text or render_inline_children(node)


def render_list(tag: Tag, ordered: bool) -> str:
    lines = []
    for index, item in enumerate(tag.find_all("li", recursive=False), start=1):
        prefix = f"{index}. " if ordered else "- "
        text = render_blocks(item) or render_inline_children(item)
        item_lines = text.splitlines() or [""]
        lines.append(prefix + item_lines[0])
        lines.extend("  " + line for line in item_lines[1:])
    return "\n".join(lines)


def render_table(tag: Tag) -> str:
    rows = []
    for row in tag.find_all("tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        if cells:
            rows.append([render_inline_children(cell).replace("|", "\\|") for cell in cells])
    if not rows:
        return render_blocks(tag)

    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    header = rows[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines)


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

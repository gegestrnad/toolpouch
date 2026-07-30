"""
Text/Markdown Cleanup
Usage: python cleanup_txt.py --input_dir <path> [--file_type <txt|md|txt and md>]
"""
import re
import sys
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def selected_files(input_dir: Path, file_type: str) -> list[Path]:
    if file_type == "txt":
        return sorted(input_dir.glob("*.txt"))
    if file_type == "md":
        return sorted(input_dir.glob("*.md"))
    return sorted(list(input_dir.glob("*.txt")) + list(input_dir.glob("*.md")))


def clean_text(content: str, blank_lines: str) -> str:
    cleaned = []
    previous_blank = False

    for raw_line in content.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line.strip())
        is_blank = not line

        if is_blank:
            if blank_lines == "collapse to one" and cleaned and not previous_blank:
                cleaned.append("")
            previous_blank = True
            continue

        cleaned.append(line)
        previous_blank = False

    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    return "\n".join(cleaned)


def normalize_markdown_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""

    heading = re.match(r"^(#{1,6})\s*(.*?)\s*#*$", stripped)
    if heading:
        return f"{heading.group(1)} {heading.group(2).strip()}"

    bullet = re.match(r"^([*+])\s+(.*)$", stripped)
    if bullet:
        return f"- {bullet.group(2).strip()}"

    numbered = re.match(r"^(\d+)[.)]\s+(.*)$", stripped)
    if numbered:
        return f"{numbered.group(1)}. {numbered.group(2).strip()}"

    return re.sub(r"[ \t]+", " ", stripped)


def clean_markdown(content: str, blank_lines: str, markdown_mode: str) -> str:
    cleaned = []
    previous_blank = False
    in_code_block = False

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if line.lstrip().startswith("```"):
            in_code_block = not in_code_block
            cleaned.append(line)
            previous_blank = False
            continue

        if in_code_block or markdown_mode == "preserve":
            line = line.rstrip()
        else:
            line = normalize_markdown_line(line)

        is_blank = not line.strip()
        if is_blank:
            if blank_lines == "collapse to one" and cleaned and not previous_blank:
                cleaned.append("")
            previous_blank = True
            continue

        cleaned.append(line)
        previous_blank = False

    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    return "\n".join(cleaned)


def main():
    parser = argparse.ArgumentParser(description="Clean whitespace and blank lines from text files")
    parser.add_argument("--input_dir", required=True, help="Folder containing .txt or .md files")
    parser.add_argument("--file_type", default="txt and md", choices=["txt", "md", "txt and md"])
    parser.add_argument("--blank_lines", default="collapse to one", choices=["remove all", "collapse to one"])
    parser.add_argument("--markdown_mode", default="normalize", choices=["preserve", "normalize"])
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"[ERROR] Folder not found: {input_dir}")
        sys.exit(1)

    files = selected_files(input_dir, args.file_type)
    if not files:
        print(f"[ERROR] No {args.file_type} files found in the specified folder.")
        sys.exit(1)

    print(f"Found {len(files)} file(s).", flush=True)
    progress(0)

    changed = 0
    for i, path in enumerate(files):
        pct = int(((i + 1) / len(files)) * 100)
        try:
            original = path.read_text(encoding="utf-8", errors="ignore")
            if path.suffix.lower() == ".md":
                cleaned = clean_markdown(original, args.blank_lines, args.markdown_mode)
            else:
                cleaned = clean_text(original, args.blank_lines)

            if cleaned != original:
                path.write_text(cleaned + "\n", encoding="utf-8")
                changed += 1
                print(f"[OK] Cleaned: {path.name}", flush=True)
            else:
                print(f"[OK] Already clean: {path.name}", flush=True)

        except Exception as e:
            print(f"[ERROR] {path.name}: {e}", flush=True)

        progress(pct)

    print(f"[OK] Done. {changed}/{len(files)} file(s) updated.", flush=True)


if __name__ == "__main__":
    main()

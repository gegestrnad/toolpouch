from __future__ import annotations

import argparse
import html
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup


SUPPORTED_EXTENSIONS = {".pdf", ".epub", ".txt", ".md", ".html", ".htm", ".xhtml"}
TEXT_EXTENSIONS = {".txt", ".md"}
HTML_EXTENSIONS = {".html", ".htm", ".xhtml"}
MAX_MATCHES_PER_KEYWORD_PER_FILE = 20
DEFAULT_CONTEXT_CHARS = 700


@dataclass(frozen=True)
class TextSegment:
    label: str
    text: str
    line_offset: int = 0


@dataclass(frozen=True)
class Match:
    file_path: Path
    file_type: str
    keyword: str
    location: str
    snippet: str


def progress(pct: int) -> None:
    print(f"PROGRESS:{max(0, min(100, pct))}", flush=True)


def warn(message: str) -> None:
    print(f"[WARN] {message}", flush=True)


def normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def parse_keywords(value: str) -> list[str]:
    raw_parts = re.split(r"[,;\n]+", normalize_newlines(value))
    keywords: list[str] = []
    seen: set[str] = set()
    for part in raw_parts:
        keyword = " ".join(part.strip().split())
        key = keyword.casefold()
        if keyword and key not in seen:
            keywords.append(keyword)
            seen.add(key)
    return keywords


def parse_selected_files(value: str) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    warnings: list[str] = []
    for raw_path in normalize_newlines(value).split("\n"):
        raw_path = raw_path.strip().strip('"')
        if not raw_path:
            continue
        path = Path(raw_path)
        if not path.exists():
            warnings.append(f"Selected file does not exist: {path}")
            continue
        if not path.is_file():
            warnings.append(f"Selected path is not a file: {path}")
            continue
        files.append(path)
    return files, warnings


def collect_folder_files(input_dir: str, scan_scope: str) -> tuple[list[Path], str | None]:
    if not input_dir.strip():
        return [], None

    folder = Path(input_dir.strip().strip('"'))
    if not folder.exists():
        return [], f"Book folder does not exist: {folder}"
    if not folder.is_dir():
        return [], f"Book folder is not a folder: {folder}"

    iterator = folder.rglob("*") if scan_scope == "include subfolders" else folder.glob("*")
    return [path for path in iterator if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS], None


def unique_supported_files(folder_files: list[Path], selected_files: list[Path]) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    seen: set[Path] = set()
    warnings: list[str] = []

    for path in [*folder_files, *selected_files]:
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            warnings.append(f"Unsupported file type skipped: {path}")
            continue
        try:
            key = path.resolve()
        except OSError:
            key = path.absolute()
        if key in seen:
            continue
        seen.add(key)
        files.append(path)

    return files, warnings


def read_text_file(path: Path) -> str:
    encodings = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise UnicodeError(f"Could not decode text file with common encodings: {last_error}")


def html_to_text(markup: str) -> str:
    soup = BeautifulSoup(markup, "html.parser")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    return html.unescape(soup.get_text("\n"))


def extract_text_segments(path: Path) -> list[TextSegment]:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return [TextSegment("text", read_text_file(path), 0)]
    if suffix in HTML_EXTENSIONS:
        return [TextSegment(path.name, html_to_text(read_text_file(path)), 0)]
    if suffix == ".epub":
        return extract_epub_segments(path)
    if suffix == ".pdf":
        return extract_pdf_segments(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def extract_epub_segments(path: Path) -> list[TextSegment]:
    segments: list[TextSegment] = []
    with zipfile.ZipFile(path) as archive:
        names = sorted(
            name
            for name in archive.namelist()
            if Path(name).suffix.lower() in HTML_EXTENSIONS and not name.endswith("/")
        )
        for name in names:
            data = archive.read(name)
            text = html_to_text(data.decode("utf-8", errors="replace"))
            if text.strip():
                segments.append(TextSegment(name, text, 0))
    return segments


def extract_pdf_segments(path: Path) -> list[TextSegment]:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF support requires PyMuPDF in the ToolPouch runtime.") from exc

    segments: list[TextSegment] = []
    with fitz.open(path) as document:
        for index, page in enumerate(document, start=1):
            text = page.get_text("text")
            if text.strip():
                segments.append(TextSegment(f"page {index}", text, 0))
    return segments


def line_number_for_offset(text: str, offset: int, line_offset: int) -> int:
    return line_offset + text.count("\n", 0, offset) + 1


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def build_snippet(text: str, start: int, end: int, context_chars: int) -> str:
    left = max(0, start - context_chars)
    right = min(len(text), end + context_chars)
    snippet = compact_text(text[left:right])
    if left > 0:
        snippet = "... " + snippet
    if right < len(text):
        snippet += " ..."
    return snippet


def find_matches(path: Path, segments: list[TextSegment], keywords: list[str], context_chars: int) -> list[Match]:
    file_matches: list[Match] = []
    file_type = path.suffix.lower().lstrip(".").upper()

    for keyword in keywords:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        matches_for_keyword = 0

        for segment in segments:
            for match in pattern.finditer(segment.text):
                if matches_for_keyword >= MAX_MATCHES_PER_KEYWORD_PER_FILE:
                    break

                if path.suffix.lower() in TEXT_EXTENSIONS:
                    location = f"line {line_number_for_offset(segment.text, match.start(), segment.line_offset)}"
                else:
                    location = segment.label

                file_matches.append(
                    Match(
                        file_path=path,
                        file_type=file_type,
                        keyword=keyword,
                        location=location,
                        snippet=build_snippet(segment.text, match.start(), match.end(), context_chars),
                    )
                )
                matches_for_keyword += 1

            if matches_for_keyword >= MAX_MATCHES_PER_KEYWORD_PER_FILE:
                break

    return file_matches


def resolve_output_file(output_file: str, input_dir: str, selected_files: list[Path]) -> Path:
    if output_file.strip():
        path = Path(output_file.strip().strip('"'))
        if path.suffix.lower() != ".md":
            path = path.with_suffix(".md")
        return path

    if input_dir.strip():
        output_root = Path(input_dir.strip().strip('"'))
    elif selected_files:
        output_root = selected_files[0].parent
    else:
        output_root = Path.cwd()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_root / f"book_context_report_{stamp}.md"


def markdown_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("`", "\\`")


def write_report(
    output_file: Path,
    matches: list[Match],
    keywords: list[str],
    files: list[Path],
    warnings: list[str],
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Book Context Finder Report",
        "",
        f"- Generated: {now}",
        f"- Keywords: {', '.join(keywords)}",
        f"- Files scanned: {len(files)}",
        f"- Matches found: {len(matches)}",
        "",
    ]

    if warnings:
        lines.extend(["## Warnings", ""])
        for message in warnings:
            lines.append(f"- {message}")
        lines.append("")

    if not matches:
        lines.extend(["## Matches", "", "No matches found.", ""])
    else:
        lines.extend(["## Matches", ""])
        current_file: Path | None = None
        for item in matches:
            if current_file != item.file_path:
                current_file = item.file_path
                lines.extend([f"### {current_file.name}", "", f"`{current_file}`", ""])
            lines.extend(
                [
                    f"**Keyword:** `{markdown_escape(item.keyword)}`",
                    f"**Type:** {item.file_type}",
                    f"**Location:** {markdown_escape(item.location)}",
                    "",
                    f"> {item.snippet}",
                    "",
                ]
            )

    output_file.write_text("\n".join(lines), encoding="utf-8")


def parse_context_chars(value: str) -> int:
    if not value.strip():
        return DEFAULT_CONTEXT_CHARS
    try:
        parsed = int(value.strip())
    except ValueError:
        warn(f"Invalid context character count '{value}'. Using {DEFAULT_CONTEXT_CHARS}.")
        return DEFAULT_CONTEXT_CHARS
    return max(100, min(parsed, 5000))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Find keyword context in books and text files")
    parser.add_argument("--input_dir", default="", help="Optional folder containing book/text files")
    parser.add_argument("--selected_files", default="", help="Selected file paths separated by new lines")
    parser.add_argument("--keywords", required=True, help="Keywords separated by comma, semicolon, or new lines")
    parser.add_argument("--context_chars", default=str(DEFAULT_CONTEXT_CHARS), help="Characters around each match")
    parser.add_argument(
        "--scan_scope",
        default="include subfolders",
        choices=["selected folder only", "include subfolders"],
        help="Whether folder scans include subfolders",
    )
    parser.add_argument("--output_file", default="", help="Optional output Markdown path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    progress(0)

    keywords = parse_keywords(args.keywords)
    if not keywords:
        print("[ERROR] Enter at least one keyword.", flush=True)
        return 1

    selected_files, selected_warnings = parse_selected_files(args.selected_files)
    folder_files, folder_error = collect_folder_files(args.input_dir, args.scan_scope)
    if folder_error:
        print(f"[ERROR] {folder_error}", flush=True)
        return 1

    files, support_warnings = unique_supported_files(folder_files, selected_files)
    warnings = [*selected_warnings, *support_warnings]
    for message in warnings:
        warn(message)

    if not files:
        print("[ERROR] No supported files found. Choose a folder or select PDF, EPUB, TXT, MD, HTML, HTM, or XHTML files.", flush=True)
        return 1

    context_chars = parse_context_chars(args.context_chars)
    output_file = resolve_output_file(args.output_file, args.input_dir, selected_files)
    all_matches: list[Match] = []
    read_warnings: list[str] = []

    print(f"Found {len(files)} supported file(s). Searching {len(keywords)} keyword(s).", flush=True)

    for index, path in enumerate(files, start=1):
        progress(int(((index - 1) / len(files)) * 95))
        try:
            segments = extract_text_segments(path)
            if not segments:
                read_warnings.append(f"No readable text found in: {path}")
                continue
            all_matches.extend(find_matches(path, segments, keywords, context_chars))
        except Exception as exc:
            read_warnings.append(f"Could not read {path}: {exc}")

    for message in read_warnings:
        warn(message)

    write_report(output_file, all_matches, keywords, files, [*warnings, *read_warnings])
    progress(100)
    print(f"[OK] Found {len(all_matches)} match(es). Report saved to: {output_file}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

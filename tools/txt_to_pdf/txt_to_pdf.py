"""
TXT to PDF Merger
Usage: python txt_to_pdf.py --input_dir <path> [--output_file <path>]
"""
import sys
import os
import argparse
from pathlib import Path

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Merge TXT files into a single PDF")
    parser.add_argument("--input_dir", required=True, help="Folder containing .txt files")
    parser.add_argument("--output_file", default="", help="Output PDF path")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"[ERROR] Folder not found: {input_dir}")
        sys.exit(1)

    txt_files = sorted(input_dir.glob("*.txt"))
    if not txt_files:
        print("[ERROR] No .txt files found in the specified folder.")
        sys.exit(1)

    output_file = args.output_file if args.output_file else str(input_dir / "_merged_output.pdf")
    print(f"Found {len(txt_files)} file(s). Merging into {output_file}...", flush=True)
    progress(5)

    try:
        arial_path = r"C:\Windows\Fonts\arial.ttf"
        if os.path.exists(arial_path):
            pdfmetrics.registerFont(TTFont("Arial", arial_path))
            font_name = "Arial"
        else:
            font_name = "Helvetica"
    except Exception:
        font_name = "Helvetica"

    doc = SimpleDocTemplate(
        output_file,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    normal_style = styles["BodyText"]
    normal_style.fontName = font_name
    normal_style.fontSize = 10
    normal_style.leading = 14

    title_style = styles["Heading1"]
    title_style.fontName = font_name

    story = []

    for index, txt_file in enumerate(txt_files):
        pct = 5 + int((index / len(txt_files)) * 90)
        progress(pct)
        print(f"[OK] Processing: {txt_file.name}", flush=True)

        try:
            text = txt_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"[WARN] UTF-8 failed for {txt_file.name}, trying latin-1...", flush=True)
            text = txt_file.read_text(encoding="latin-1")

        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(txt_file.name, title_style))
        story.append(Spacer(1, 5 * mm))

        for line in text.splitlines():
            story.append(Paragraph(line.strip() or "&nbsp;", normal_style))

        if index < len(txt_files) - 1:
            story.append(PageBreak())

    doc.build(story)
    progress(100)
    print(f"[OK] Done. Created: {output_file}", flush=True)


if __name__ == "__main__":
    main()

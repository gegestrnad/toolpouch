"""
JSON Translator (Chinese -> English)
Usage: python translate_jsons.py --input_zip <path> [--output_zip <path>]
"""
import json
import re
import sys
import zipfile
import argparse
import tempfile
from pathlib import Path

from deep_translator import GoogleTranslator

CHINESE_RE = re.compile(r"[\u4e00-\u9fff]+")
translator = GoogleTranslator(source="zh-CN", target="en")
cache = {}


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def contains_chinese(text):
    return bool(CHINESE_RE.search(text))


def translate_text(text):
    if not isinstance(text, str) or not contains_chinese(text):
        return text
    if text in cache:
        return cache[text]
    try:
        translated = translator.translate(text)
        cache[text] = translated
        print(f"[OK] {text[:60]} -> {translated[:60]}", flush=True)
        return translated
    except Exception as e:
        print(f"[WARN] {text[:60]} | {e}", flush=True)
        return text


def translate_obj(obj):
    if isinstance(obj, dict):
        return {
            (translate_text(k) if isinstance(k, str) else k): translate_obj(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [translate_obj(item) for item in obj]
    if isinstance(obj, str):
        return translate_text(obj)
    return obj


def main():
    parser = argparse.ArgumentParser(description="Translate Chinese JSON fields to English")
    parser.add_argument("--input_zip", required=True, help="Input ZIP containing JSON files")
    parser.add_argument("--output_zip", default="", help="Output ZIP path")
    args = parser.parse_args()

    input_zip = Path(args.input_zip)
    if not input_zip.exists():
        print(f"[ERROR] Input file not found: {input_zip}")
        sys.exit(1)

    output_zip = Path(args.output_zip) if args.output_zip else input_zip.parent / (input_zip.stem + "_translated.zip")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        print(f"Extracting {input_zip.name}...", flush=True)
        with zipfile.ZipFile(input_zip, "r") as zf:
            zf.extractall(tmp_path)

        json_files = list(tmp_path.rglob("*.json"))
        print(f"Found {len(json_files)} JSON file(s).", flush=True)
        progress(5)

        for i, json_file in enumerate(json_files):
            pct = 5 + int((i / len(json_files)) * 90)
            progress(pct)
            print(f"\n=== Processing: {json_file.name} ===", flush=True)

            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                translated = translate_obj(data)

                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(translated, f, ensure_ascii=False, indent=2)

                print(f"[OK] {json_file.name}", flush=True)

            except Exception as e:
                print(f"[ERROR] {json_file.name}: {e}", flush=True)

        print(f"\nRepacking to {output_zip.name}...", flush=True)
        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in tmp_path.rglob("*"):
                if file_path.is_file():
                    zf.write(file_path, file_path.relative_to(tmp_path))

    progress(100)
    print(f"[OK] Done. Output written to: {output_zip}", flush=True)


if __name__ == "__main__":
    main()

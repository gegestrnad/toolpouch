"""
Music Artist Organizer
Usage:
    python music_artist_organizer.py [--input_dir <path>]
        [--selected_files <newline-separated paths>] [--file_glob <patterns>]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from mutagen import File as MutagenFile
    from mutagen.id3 import ID3
except ImportError:
    MutagenFile = None
    ID3 = None


DEFAULT_GLOB = "*.mp3;*.flac;*.m4a;*.ogg;*.opus;*.wav;*.wma;*.aac"
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}
ARTIST_KEYS = (
    "artist",
    "albumartist",
    "album artist",
    "tpe1",
    "tpe2",
    "\xa9ART",
    "aART",
    "Author",
    "WM/Artist",
    "WM/AlbumArtist",
)
FEAT_RE = re.compile(r"\s+(?:feat\.?|ft\.?|featuring|with)\s+.+$", re.IGNORECASE)
MULTI_ARTIST_SPLIT_RE = re.compile(r"\s*(?:,|;)\s*|\s+(?:/|&|\+|\band\b)\s+", re.IGNORECASE)


@dataclass
class MovePlan:
    source: Path
    artist: str
    target_dir: Path
    target: Path


def progress(pct: int) -> None:
    print(f"PROGRESS:{max(0, min(100, pct))}", flush=True)


def glob_patterns(raw_value: str) -> list[str]:
    return [part.strip() for part in (raw_value or DEFAULT_GLOB).split(";") if part.strip()]


def collect_folder_files(input_dir: Path, file_glob: str) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for pattern in glob_patterns(file_glob):
        for path in sorted(input_dir.glob(pattern)):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(path)
    return files


def selected_file_values(selected_files: str) -> list[str]:
    values: list[str] = []
    normalized = selected_files.replace("\r\n", "\n").replace("\r", "\n")
    for part in re.split(r"[;\n]+", normalized):
        value = part.strip().strip('"')
        if value:
            values.append(value)
    return values


def collect_selected_files(selected_files: str) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    warnings: list[str] = []
    seen: set[Path] = set()

    for value in selected_file_values(selected_files):
        path = Path(value)
        if not path.exists():
            warnings.append(f"Selected file not found: {path}")
            continue
        if not path.is_file():
            warnings.append(f"Selected path is not a file: {path}")
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        files.append(path)

    return files, warnings


def merge_files(folder_files: list[Path], selected_files: list[Path]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for path in [*folder_files, *selected_files]:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        files.append(path)
    return files


def resolve_output_root(input_dir: str, selected_files: list[Path]) -> tuple[Path | None, str | None]:
    raw_input_dir = input_dir.strip()
    if raw_input_dir:
        folder = Path(raw_input_dir)
        if not folder.exists():
            return None, f"Folder not found: {folder}"
        if not folder.is_dir():
            return None, f"Input path is not a folder: {folder}"
        return folder, None

    if not selected_files:
        return None, "Choose Music folder or select at least one valid music file."

    parent_dirs = {path.parent.resolve() for path in selected_files}
    if len(parent_dirs) > 1:
        return None, "Selected files come from multiple folders; choose Music folder as the output destination."

    return next(iter(parent_dirs)), None


def text_from_tag_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return str(value[0]).strip() if value else ""
    if hasattr(value, "text"):
        text = getattr(value, "text")
        if isinstance(text, (list, tuple)):
            return str(text[0]).strip() if text else ""
        return str(text).strip()
    return str(value).strip()


def first_tag_value(tags: Any, keys: tuple[str, ...]) -> str:
    if not tags:
        return ""

    for key in keys:
        try:
            value = tags.get(key)
        except AttributeError:
            value = None
        text = text_from_tag_value(value)
        if text:
            return text

    lowered = {str(key).lower(): key for key in tags.keys()} if hasattr(tags, "keys") else {}
    for key in keys:
        original = lowered.get(key.lower())
        if original is None:
            continue
        text = text_from_tag_value(tags.get(original))
        if text:
            return text

    return ""


def normalize_artist(raw_artist: str) -> str:
    artist = FEAT_RE.sub("", raw_artist).strip()
    parts = [part.strip() for part in MULTI_ARTIST_SPLIT_RE.split(artist) if part.strip()]
    if parts:
        artist = parts[0]
    return artist


def read_artist(path: Path) -> tuple[str | None, str | None]:
    if MutagenFile is None:
        return None, "mutagen is not installed in this Python runtime."

    try:
        audio = MutagenFile(path, easy=True)
    except Exception as exc:
        if ID3 is None or path.suffix.lower() != ".mp3":
            return None, f"Could not read metadata: {exc}"
        try:
            raw_artist = first_tag_value(ID3(path), ARTIST_KEYS)
        except Exception:
            return None, f"Could not read metadata: {exc}"
        if not raw_artist:
            return None, "No artist metadata found."
        artist = normalize_artist(raw_artist)
        if not artist:
            return None, "Artist metadata was empty after cleanup."
        return artist, None

    if audio is None:
        return None, "Unsupported or unreadable music file."

    raw_artist = first_tag_value(getattr(audio, "tags", None), ARTIST_KEYS)
    if not raw_artist:
        return None, "No artist metadata found."

    artist = normalize_artist(raw_artist)
    if not artist:
        return None, "Artist metadata was empty after cleanup."

    return artist, None


def clean_folder_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        cleaned = "Unknown Artist"
    if cleaned.upper() in RESERVED_NAMES:
        cleaned = f"{cleaned}_artist"
    return cleaned


def unique_target(target: Path) -> Path:
    if not target.exists():
        return target

    counter = 2
    while True:
        candidate = target.with_name(f"{target.stem}_{counter}{target.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def create_move_plans(output_root: Path, files: list[Path]) -> tuple[list[MovePlan], int]:
    plans: list[MovePlan] = []
    skipped = 0

    for path in files:
        artist, warning = read_artist(path)
        if artist is None:
            skipped += 1
            print(f"[WARN] Skipped {path.name}: {warning}", flush=True)
            continue

        folder_name = clean_folder_name(artist)
        target_dir = output_root / folder_name
        target = unique_target(target_dir / path.name)
        if path.resolve() == target.resolve():
            print(f"[OK] Already organized: {path.name} -> {folder_name}\\{path.name}", flush=True)
            continue

        plans.append(MovePlan(source=path, artist=folder_name, target_dir=target_dir, target=target))

    return plans, skipped


def move_files(plans: list[MovePlan]) -> int:
    moved = 0
    total = max(1, len(plans))

    for index, plan in enumerate(plans, start=1):
        try:
            plan.target_dir.mkdir(parents=True, exist_ok=True)
            target = unique_target(plan.target_dir / plan.source.name)
            shutil.move(str(plan.source), str(target))
            print(f"[OK] Moved: {plan.source.name} -> {plan.artist}\\{target.name}", flush=True)
            moved += 1
        except Exception as exc:
            print(f"[ERROR] {plan.source.name}: {exc}", flush=True)

        progress(int((index / total) * 100))

    return moved


def main() -> None:
    parser = argparse.ArgumentParser(description="Organize music files into artist folders")
    parser.add_argument("--input_dir", default="", help="Folder containing unorganized music files")
    parser.add_argument("--selected_files", default="", help="Selected file paths separated by new lines")
    parser.add_argument("--file_glob", default=DEFAULT_GLOB, help="Semicolon-separated glob patterns")
    args = parser.parse_args()

    progress(0)
    selected_files, selected_warnings = collect_selected_files(args.selected_files)
    output_root, input_error = resolve_output_root(args.input_dir, selected_files)
    if input_error:
        for warning in selected_warnings:
            print(f"[WARN] {warning}", flush=True)
        print(f"[ERROR] {input_error}", flush=True)
        sys.exit(1)

    folder_files = collect_folder_files(output_root, args.file_glob) if args.input_dir.strip() else []
    files = merge_files(folder_files, selected_files)
    for warning in selected_warnings:
        print(f"[WARN] {warning}", flush=True)

    if not files:
        print(
            f"[ERROR] No files matching '{args.file_glob or DEFAULT_GLOB}' found, "
            "and no valid selected files were provided.",
            flush=True,
        )
        sys.exit(1)

    print(
        f"Found {len(folder_files)} scanned file(s), {len(selected_files)} selected file(s), "
        f"{len(files)} unique file(s).",
        flush=True,
    )

    plans, skipped = create_move_plans(output_root, files)
    if not plans:
        print(f"[ERROR] No files were moved. Skipped {skipped} file(s).", flush=True)
        sys.exit(1)

    moved = move_files(plans)
    print(f"[OK] Done. Moved {moved}/{len(plans)} file(s). Skipped {skipped} file(s).", flush=True)


if __name__ == "__main__":
    main()

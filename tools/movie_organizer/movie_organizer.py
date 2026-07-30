"""
Movie Organizer
Usage:
    python movie_organizer.py [--input_dir <path>] [--file_glob <patterns>]
        [--selected_files <paths>] [--manual_folder_name <name>]
        [--matching_strategy <strategy>] [--scan_scope <scope>] [--mode preview|organize]
"""
import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_GLOB = "*.mkv;*.mp4;*.avi;*.mov;*.wmv;*.srt;*.ass;*.ssa;*.sub;*.idx;*.nfo;*.jpg;*.jpeg;*.png"
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".m4v", ".webm"}
SIDEcar_EXTENSIONS = {".srt", ".ass", ".ssa", ".sub", ".idx", ".nfo", ".jpg", ".jpeg", ".png"}
SUBTITLE_TAGS = {
    "ar", "ara", "chs", "cht", "cn", "da", "dan", "de", "deu", "dk", "dut", "en", "eng",
    "es", "esp", "fi", "fin", "forced", "fr", "fre", "ger", "hearingimpaired", "hi", "id",
    "ind", "ita", "it", "jp", "jpn", "kr", "kor", "nl", "no", "nor", "pt", "por", "ro",
    "sdh", "spa", "sub", "subs", "sv", "swe", "tr", "tur", "vi", "vie",
}
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}
YEAR_RE = re.compile(r"(?P<title>.*?)(?:\((?P<paren_year>19\d{2}|20\d{2})\)|\b(?P<bare_year>19\d{2}|20\d{2})\b)")


@dataclass
class MovePlan:
    source: Path
    target_dir: Path
    target: Path
    group_name: str


def progress(pct: int) -> None:
    print(f"PROGRESS:{max(0, min(100, pct))}", flush=True)


def clean_folder_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        cleaned = "Movie"
    if cleaned.upper() in RESERVED_NAMES:
        cleaned = f"{cleaned}_movie"
    return cleaned


def glob_patterns(raw_value: str) -> list[str]:
    return [part.strip() for part in (raw_value or DEFAULT_GLOB).split(";") if part.strip()]


def collect_files(input_dir: Path, file_glob: str, include_subfolders: bool) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []

    for pattern in glob_patterns(file_glob):
        iterator = input_dir.rglob(pattern) if include_subfolders else input_dir.glob(pattern)
        for path in sorted(iterator):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(path)

    return files


def manual_path_values(selected_files: str, manual_file: str, manual_extra_files: str) -> list[str]:
    values: list[str] = []
    normalized_selected = selected_files.replace("\r\n", "\n").replace("\r", "\n")
    for part in re.split(r"[;\n]+", normalized_selected):
        value = part.strip().strip('"')
        if value:
            values.append(value)

    if manual_file.strip():
        values.append(manual_file.strip())

    normalized = manual_extra_files.replace("\r\n", "\n").replace("\r", "\n")
    for part in re.split(r"[;\n]+", normalized):
        value = part.strip().strip('"')
        if value:
            values.append(value)

    return values


def collect_manual_files(
    selected_files: str,
    manual_file: str,
    manual_extra_files: str,
) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    warnings: list[str] = []
    seen: set[Path] = set()

    for value in manual_path_values(selected_files, manual_file, manual_extra_files):
        path = Path(value)
        if not path.exists():
            warnings.append(f"Manual file not found: {path}")
            continue
        if not path.is_file():
            warnings.append(f"Manual path is not a file: {path}")
            continue

        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        files.append(path)

    return files, warnings


def merge_files(scanned_files: list[Path], manual_files: list[Path]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for path in [*scanned_files, *manual_files]:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        files.append(path)
    return files


def strip_subtitle_tags(stem: str) -> str:
    parts = re.split(r"([._ -]+)", stem)
    while len(parts) >= 3:
        token = parts[-1].lower()
        if token not in SUBTITLE_TAGS:
            break
        parts = parts[:-2]
    return "".join(parts).rstrip("._ -") or stem


def smart_subtitle_key(path: Path, video_stems: set[str]) -> str:
    stem = path.stem
    if path.suffix.lower() not in SIDEcar_EXTENSIONS:
        return stem

    candidates = [video_stem for video_stem in video_stems if stem == video_stem or stem.startswith(f"{video_stem}.")]
    candidates.extend(video_stem for video_stem in video_stems if stem.startswith(f"{video_stem} "))
    if candidates:
        return max(candidates, key=len)

    return strip_subtitle_tags(stem)


def title_year_identity(stem: str) -> str | None:
    match = YEAR_RE.search(stem)
    if not match:
        return None

    year = match.group("paren_year") or match.group("bare_year")
    title = re.sub(r"[._]+", " ", match.group("title")).strip(" ._-")
    title = re.sub(r"\s+", " ", title).casefold()
    return f"{title} ({year})" if title else None


def build_groups(files: list[Path], strategy: str) -> tuple[dict[str, list[Path]], list[str]]:
    warnings: list[str] = []
    video_stems = {path.stem for path in files if path.suffix.lower() in VIDEO_EXTENSIONS}

    raw_groups: dict[str, list[Path]] = {}
    for path in files:
        if strategy == "exact stem":
            key = path.stem
        elif strategy == "smart subtitle match":
            key = smart_subtitle_key(path, video_stems)
        else:
            identity = title_year_identity(path.stem)
            key = identity or smart_subtitle_key(path, video_stems)
            if identity is None:
                warnings.append(f"{path.name}: no year detected; used filename stem matching.")

        raw_groups.setdefault(key, []).append(path)

    if strategy != "year-based smart":
        return {clean_folder_name(key): paths for key, paths in raw_groups.items()}, warnings

    final_groups: dict[str, list[Path]] = {}
    for key, paths in raw_groups.items():
        video_names = sorted({path.stem for path in paths if path.suffix.lower() in VIDEO_EXTENSIONS})
        if len(video_names) > 1:
            warnings.append(f"{key}: multiple video releases found; kept exact release folders.")
            for path in paths:
                final_groups.setdefault(clean_folder_name(smart_subtitle_key(path, set(video_names))), []).append(path)
            continue

        folder_name = video_names[0] if video_names else max((path.stem for path in paths), key=len)
        final_groups.setdefault(clean_folder_name(folder_name), []).extend(paths)

    return final_groups, warnings


def manual_group_name(manual_files: list[Path], manual_folder_name: str) -> str:
    explicit_name = manual_folder_name.strip()
    if explicit_name:
        return clean_folder_name(explicit_name)

    video_names = [path.stem for path in manual_files if path.suffix.lower() in VIDEO_EXTENSIONS]
    if video_names:
        return clean_folder_name(max(video_names, key=len))

    return clean_folder_name(max((path.stem for path in manual_files), key=len))


def apply_manual_group(
    groups: dict[str, list[Path]],
    manual_files: list[Path],
    manual_folder_name: str,
) -> dict[str, list[Path]]:
    if not manual_files:
        return groups

    if not manual_folder_name.strip() and len(manual_files) == 1:
        return groups

    manual_resolved = {path.resolve() for path in manual_files}
    adjusted: dict[str, list[Path]] = {}
    for group_name, paths in groups.items():
        remaining = [path for path in paths if path.resolve() not in manual_resolved]
        if remaining:
            adjusted[group_name] = remaining

    adjusted.setdefault(manual_group_name(manual_files, manual_folder_name), []).extend(manual_files)
    return adjusted


def unique_target(target: Path) -> Path:
    if not target.exists():
        return target

    counter = 2
    while True:
        candidate = target.with_name(f"{target.stem}_{counter}{target.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def create_move_plans(input_dir: Path, groups: dict[str, list[Path]]) -> list[MovePlan]:
    plans: list[MovePlan] = []
    for group_name in sorted(groups):
        target_dir = input_dir / group_name
        for source in sorted(groups[group_name]):
            target = unique_target(target_dir / source.name)
            if source.resolve() == target.resolve():
                continue
            plans.append(MovePlan(source=source, target_dir=target_dir, target=target, group_name=group_name))
    return plans


def resolve_output_root(input_dir: str, manual_files: list[Path]) -> tuple[Path | None, str | None]:
    raw_input_dir = input_dir.strip()
    if raw_input_dir:
        folder = Path(raw_input_dir)
        if not folder.exists():
            return None, f"Folder not found: {folder}"
        if not folder.is_dir():
            return None, f"Input path is not a folder: {folder}"
        return folder, None

    if not manual_files:
        return None, "Choose Movie folder or select at least one valid file."

    parent_dirs = {path.parent.resolve() for path in manual_files}
    if len(parent_dirs) > 1:
        return None, "Selected files come from multiple folders; choose Movie folder as output destination."

    return next(iter(parent_dirs)), None


def run_plans(plans: list[MovePlan], mode: str) -> int:
    moved = 0
    total = max(1, len(plans))

    for index, plan in enumerate(plans, start=1):
        try:
            if mode == "preview":
                print(f"[OK] Preview: {plan.source.name} -> {plan.group_name}\\{plan.target.name}", flush=True)
            else:
                plan.target_dir.mkdir(parents=True, exist_ok=True)
                target = unique_target(plan.target_dir / plan.source.name)
                shutil.move(str(plan.source), str(target))
                print(f"[OK] Moved: {plan.source.name} -> {plan.group_name}\\{target.name}", flush=True)
            moved += 1
        except Exception as exc:
            print(f"[ERROR] {plan.source.name}: {exc}", flush=True)

        progress(int((index / total) * 100))

    return moved


def main() -> None:
    parser = argparse.ArgumentParser(description="Organize movie files into per-movie folders")
    parser.add_argument("--input_dir", default="", help="Folder containing mixed movie files")
    parser.add_argument("--file_glob", default=DEFAULT_GLOB, help="Semicolon-separated glob patterns")
    parser.add_argument("--selected_files", default="", help="Selected file paths separated by new lines")
    parser.add_argument("--manual_file", default="", help="Optional single file to add manually")
    parser.add_argument(
        "--manual_extra_files",
        default="",
        help="Optional extra file paths separated by semicolons or new lines",
    )
    parser.add_argument("--manual_folder_name", default="", help="Optional folder name for manual files")
    parser.add_argument(
        "--matching_strategy",
        default="exact stem",
        choices=["exact stem", "smart subtitle match", "year-based smart"],
    )
    parser.add_argument(
        "--scan_scope",
        default="selected folder only",
        choices=["selected folder only", "include subfolders"],
    )
    parser.add_argument("--mode", default="preview", choices=["preview", "organize"])
    args = parser.parse_args()

    include_subfolders = args.scan_scope == "include subfolders"
    manual_files, manual_warnings = collect_manual_files(
        args.selected_files,
        args.manual_file,
        args.manual_extra_files,
    )
    input_dir, input_error = resolve_output_root(args.input_dir, manual_files)
    if input_error:
        for warning in manual_warnings:
            print(f"[WARN] {warning}", flush=True)
        print(f"[ERROR] {input_error}", flush=True)
        sys.exit(1)

    scanned_files = collect_files(input_dir, args.file_glob, include_subfolders) if args.input_dir.strip() else []
    files = merge_files(scanned_files, manual_files)
    if not files:
        for warning in manual_warnings:
            print(f"[WARN] {warning}", flush=True)
        print(
            f"[ERROR] No files matching '{args.file_glob or DEFAULT_GLOB}' found in {input_dir}, "
            "and no valid manual files were provided.",
            flush=True,
        )
        sys.exit(1)

    groups, warnings = build_groups(files, args.matching_strategy)
    groups = apply_manual_group(groups, manual_files, args.manual_folder_name)
    warnings = manual_warnings + warnings
    plans = create_move_plans(input_dir, groups)
    if not plans:
        print("[ERROR] No files need organizing.", flush=True)
        sys.exit(1)

    print(
        f"Found {len(scanned_files)} scanned file(s), {len(manual_files)} manual file(s), "
        f"{len(groups)} group(s), {len(plans)} move(s). "
        f"Mode: {args.mode}.",
        flush=True,
    )
    for warning in warnings:
        print(f"[WARN] {warning}", flush=True)

    progress(0)
    changed = run_plans(plans, args.mode)
    action = "would move" if args.mode == "preview" else "moved"
    print(f"[OK] Done. {changed}/{len(plans)} file(s) {action}.", flush=True)


if __name__ == "__main__":
    main()

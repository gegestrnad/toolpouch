"""Duplicate Finder - Find files with identical content using hashing."""
import sys
import hashlib
import argparse
from pathlib import Path
from collections import defaultdict


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def file_hash(filepath: Path, hash_type: str) -> str:
    h = hashlib.new(hash_type)
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Find duplicate files")
    parser.add_argument("--folder", required=True, help="Folder to scan")
    parser.add_argument("--hash_type", choices=["md5", "sha256", "sha1"], default="md5")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        print(f"[ERROR] Not a valid directory: {folder}")
        sys.exit(1)

    progress(5)

    # Collect all files
    all_files = [f for f in folder.rglob("*") if f.is_file()]
    total = len(all_files)

    if total == 0:
        print("[WARN] No files found in the directory")
        progress(100)
        return

    print(f"[OK] Scanning {total} files with {args.hash_type.upper()}...", flush=True)
    progress(10)

    # Group by size first (fast pre-filter)
    size_groups = defaultdict(list)
    for i, f in enumerate(all_files):
        try:
            size_groups[f.stat().st_size].append(f)
        except (OSError, PermissionError):
            pass
        if i % 100 == 0:
            progress(10 + int((i / total) * 30))

    progress(40)

    # Hash only files that share a size
    hash_groups = defaultdict(list)
    candidates = [f for fs, files in size_groups.items() if len(files) > 1 for f in files]
    print(f"[OK] {len(candidates)} files share sizes, hashing...", flush=True)

    for i, f in enumerate(candidates):
        try:
            h = file_hash(f, args.hash_type)
            hash_groups[h].append(f)
        except (OSError, PermissionError):
            pass
        if i % 50 == 0:
            progress(40 + int((i / max(len(candidates), 1)) * 50))

    progress(90)

    # Find actual duplicates
    duplicates = {h: files for h, files in hash_groups.items() if len(files) > 1}

    if not duplicates:
        print("[OK] No duplicate files found")
    else:
        dup_count = sum(len(files) for files in duplicates.values())
        print(f"[WARN] Found {len(duplicates)} groups of duplicates ({dup_count} files total):")
        for i, (h, files) in enumerate(duplicates.items(), 1):
            print(f"\n  Group {i} ({h[:12]}..., {files[0].stat().st_size} bytes):")
            for f in files:
                print(f"    {f.relative_to(folder)}")

    progress(100)
    print(f"[OK] Scan complete: {total} files, {len(duplicates)} duplicate groups", flush=True)


if __name__ == "__main__":
    main()

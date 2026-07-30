"""File Stats - Show detailed file/directory statistics."""
import sys
import stat
import argparse
from pathlib import Path
from datetime import datetime


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_mode(mode: int) -> str:
    """Format a stat mode as a Unix-style rwx string.

    On Windows, ``st_mode`` doesn't carry meaningful Unix permission bits
    (the S_IRUSR/S_IWUSR/etc. constants exist but are always set the same
    way). We detect Windows and return a synthetic representation based
    on the file's read-only attribute instead, which is the only
    permission concept Windows actually has at the filesystem level.
    """
    import os
    if os.name == "nt":
        # Windows: only read-only vs read-write is meaningful.
        # stat.FILE_ATTRIBUTE_READONLY = 0x1
        is_readonly = bool(mode & 0x1)
        user = "r" + ("-" if is_readonly else "w") + "-"
        return user + "------"
    # POSIX: full Unix permission string.
    perms = ""
    for flag, char in [(stat.S_IRUSR, "r"), (stat.S_IWUSR, "w"), (stat.S_IXUSR, "x"),
                        (stat.S_IRGRP, "r"), (stat.S_IWGRP, "w"), (stat.S_IXGRP, "x"),
                        (stat.S_IROTH, "r"), (stat.S_IWOTH, "w"), (stat.S_IXOTH, "x")]:
        perms += char if mode & flag else "-"
    return perms


def main():
    parser = argparse.ArgumentParser(description="Show file/folder stats")
    parser.add_argument("--path", required=True, help="File or folder path")
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"[ERROR] Path not found: {target}")
        sys.exit(1)

    progress(10)

    st = target.stat()

    print(f"{'Name:':<20} {target.name}", flush=True)
    print(f"{'Full Path:':<20} {target.resolve()}", flush=True)
    print(f"{'Type:':<20} {'Directory' if target.is_dir() else 'File'}", flush=True)
    print(f"{'Size:':<20} {format_size(st.st_size)} ({st.st_size:,} bytes)", flush=True)
    print(f"{'Permissions:':<20} {format_mode(st.st_mode)}", flush=True)
    print(f"{'Created:':<20} {datetime.fromtimestamp(st.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"{'Modified:':<20} {datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"{'Accessed:':<20} {datetime.fromtimestamp(st.st_atime).strftime('%Y-%m-%d %H:%M:%S')}", flush=True)

    progress(50)

    if target.is_dir():
        file_count = 0
        dir_count = 0
        total_size = 0
        for item in target.rglob("*"):
            if item.is_file():
                file_count += 1
                try:
                    total_size += item.stat().st_size
                except (OSError, PermissionError):
                    pass
            elif item.is_dir():
                dir_count += 1

        progress(80)
        print(f"{'Subdirs:':<20} {dir_count}", flush=True)
        print(f"{'Files:':<20} {file_count}", flush=True)
        print(f"{'Total Size:':<20} {format_size(total_size)}", flush=True)

    progress(100)
    print(f"[OK] Stats complete for {target.name}", flush=True)


if __name__ == "__main__":
    main()

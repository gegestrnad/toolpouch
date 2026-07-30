"""Hello-world test tool for the Python runtime.

Spec §6 Phase 6 checkpoint: "test argument passing with a path containing
spaces (``C:\\Test Folder (2026)\\``) for each language."

Prints the protocol tokens (PROGRESS:N, [OK], etc.) so the host UI can
exercise its full parsing path end-to-end.
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    args = parser.parse_args()

    print("PROGRESS:0", flush=True)
    print(f"[OK] Hello from Python {sys.version.split()[0]}", flush=True)
    print(f"[OK] python_exe: {sys.executable}", flush=True)
    print(f"[OK] path_arg:   {args.path}", flush=True)
    print("PROGRESS:50", flush=True)

    if " " in args.path:
        print(f"[OK] Path contains spaces — preserved correctly.", flush=True)
    else:
        print(f"[WARN] Path has no spaces — try a path with spaces to really test.", flush=True)

    print("PROGRESS:100", flush=True)
    print("[OK] Done.", flush=True)


if __name__ == "__main__":
    main()

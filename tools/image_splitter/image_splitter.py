"""Image Splitter - Split an image into a grid of smaller pieces."""
import sys
import argparse
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Split image into grid")
    parser.add_argument("--image", required=True, help="Image file path")
    parser.add_argument("--rows", type=int, required=True, help="Number of rows")
    parser.add_argument("--cols", type=int, required=True, help="Number of columns")
    parser.add_argument("--output_dir", required=True, help="Output directory")
    args = parser.parse_args()

    input_path = Path(args.image)
    if not input_path.exists():
        print(f"[ERROR] Image not found: {input_path}")
        sys.exit(1)

    if args.rows < 1 or args.cols < 1:
        print("[ERROR] Rows and columns must be at least 1")
        sys.exit(1)

    progress(10)

    try:
        from PIL import Image
    except ImportError:
        print("[ERROR] Pillow is required: pip install Pillow")
        sys.exit(1)

    img = Image.open(str(input_path))
    width, height = img.size
    print(f"[OK] Loaded image: {width}x{height}px", flush=True)

    progress(30)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cell_w = width // args.cols
    cell_h = height // args.rows
    total_pieces = args.rows * args.cols

    stem = input_path.stem
    ext = input_path.suffix

    count = 0
    for r in range(args.rows):
        for c in range(args.cols):
            left = c * cell_w
            top = r * cell_h
            right = left + cell_w if c < args.cols - 1 else width
            bottom = top + cell_h if r < args.rows - 1 else height

            piece = img.crop((left, top, right, bottom))
            filename = f"{stem}_r{r+1}c{c+1}{ext}"
            piece.save(str(out_dir / filename))
            count += 1

            pct = 30 + int((count / total_pieces) * 60)
            progress(pct)

    progress(100)
    print(f"[OK] Split into {count} pieces ({cell_w}x{cell_h}px each)", flush=True)
    print(f"[OK] Output: {out_dir}", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Copyright (c) OpenAI. All rights reserved.
Modified by Boeing AI.

Ensures input images are rasterized, converting to PNG when needed. Primarily used to
preview image assets extracted from PowerPoint files.


Dependencies used by this tool:
- Ghostscript: PDF/EPS/PS rasterization (first page)
- libheif-examples: heif-convert for HEIC/HEIF → PNG

Install (Ubuntu/Debian):
  sudo apt-get update
  sudo apt-get install -y ghostscript libheif-examples

Verify:
  gs -v
  heif-convert -h
"""

import argparse
import gzip
import shutil
from os import listdir
from os.path import basename, dirname, expanduser, isfile, join, splitext
from subprocess import run

RASTER_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".webp",
}

CONVERTIBLE_EXTS = {
    # HEIF family
    ".heic",
    ".heif",
    # Page-description formats (rasterize first page)
    ".pdf",
    ".eps",
    ".ps",
}

SUPPORTED_EXTS = RASTER_EXTS | CONVERTIBLE_EXTS


def ensure_raster_image(path: str, out_dir: str | None = None) -> str:
    """Return a raster image path for the given input, converting when needed.

    Raises ValueError if the extension is not supported.
    """
    base, ext = splitext(path)
    ext_lower = ext.lower()
    out_dir = out_dir or dirname(path)
    out_path = join(out_dir, basename(base) + ".png")

    if ext_lower in (".heic", ".heif"):
        # Use libheif's CLI for robust conversion
        heif_convert = shutil.which("heif-convert") or "heif-convert"
        run([heif_convert, path, out_path], check=True)
        if isfile(out_path):
            return out_path
        raise RuntimeError("heif-convert reported success but output file not found: " + out_path)

    if ext_lower in (".pdf", ".eps", ".ps"):
        # Rasterize first page via Ghostscript
        gs = shutil.which("gs") or "gs"
        run(
            [
                gs,
                "-dSAFER",
                "-dBATCH",
                "-dNOPAUSE",
                "-sDEVICE=pngalpha",
                "-dFirstPage=1",
                "-dLastPage=1",
                "-r200",
                "-o",
                out_path,
                path,
            ],
            check=True,
        )
        if isfile(out_path):
            return out_path
        raise RuntimeError("Ghostscript reported success but output file not found: " + out_path)

    if ext_lower in RASTER_EXTS:
        return path

    raise ValueError(f"Unsupported image format for montage: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=("Ensure input images are rasterized; convert to PNG if needed.")
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input_files", nargs="+", help="List of input image file paths")
    group.add_argument("--input_dir", help="Directory containing input images")
    parser.add_argument(
        "--output_dir",
        default=None,
        help=(
            "Directory to write converted PNGs. If omitted, converted files are written next to inputs."
        ),
    )
    args = parser.parse_args()

    if args.input_files:
        paths = [expanduser(p) for p in args.input_files]
    else:
        input_dir = expanduser(args.input_dir)
        names = listdir(input_dir)
        paths = [
            join(input_dir, f)
            for f in names
            if isfile(join(input_dir, f)) and splitext(f)[1].lower() in SUPPORTED_EXTS
        ]
        if not paths:
            raise SystemExit("No files with supported extensions in input_dir")

    out_dir = expanduser(args.output_dir) if args.output_dir else None
    converted_paths = []
    for p in paths:
        if ensure_raster_image(p, out_dir) != p:
            converted_paths.append(p)

    if converted_paths:
        print("Converted the following files to PNG:\n" + "\n".join(converted_paths))


if __name__ == "__main__":
    main()

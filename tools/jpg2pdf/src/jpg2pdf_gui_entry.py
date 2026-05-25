"""PyInstaller entry script for the GUI binary.

This binary must open the Tk UI directly.  Older builds delegated to the CLI
entry point and only showed the window when `--gui` was present; shortcuts or
Explorer commands that launched `jpg2pdf-gui.exe` with no args looked like they
did nothing because the windowed process had no console for argparse errors.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jpg2pdf_app.core import __version__
from jpg2pdf_app.gui import run


def _read_paths_file(path: str) -> list[str]:
    """Read one path per line from a context-menu queue file."""
    p = Path(path).expanduser()
    try:
        text = p.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        fallback = "mbcs" if sys.platform == "win32" else "utf-8"
        text = p.read_text(encoding=fallback, errors="replace")
    out: list[str] = []
    for line in text.splitlines():
        item = line.strip().strip('"')
        if item and not item.startswith("#"):
            out.append(item)
    return out


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open the jpg2pdf desktop UI.")
    parser.add_argument("--version", action="version", version=f"jpg2pdf {__version__}")
    parser.add_argument("--gui", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--files", nargs="+", default=None,
                        help="Pre-load these files into the UI.")
    parser.add_argument("--files-from", default=None,
                        help="Pre-load paths from a text file, one per line.")
    parser.add_argument("paths", nargs="*",
                        help="Optional files or folders to pre-load.")
    return parser


def main() -> None:
    args, _unknown = _build_parser().parse_known_args()
    initial_paths: list[str] = []
    if args.files_from:
        try:
            initial_paths.extend(_read_paths_file(args.files_from))
        except OSError:
            pass
    if args.files:
        initial_paths.extend(args.files)
    if args.paths:
        initial_paths.extend(args.paths)
    raise SystemExit(run(initial_paths=initial_paths or None))


if __name__ == "__main__":
    main()

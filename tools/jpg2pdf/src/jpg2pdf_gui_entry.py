"""PyInstaller entry script for the GUI binary.

Uses an absolute import so PyInstaller's `--onefile` mode (which loads the
entry script as a top-level module, not as part of a package) doesn't blow
up with `attempted relative import with no known parent package`.
"""
from __future__ import annotations

from jpg2pdf_app.cli import main


if __name__ == "__main__":
    main()

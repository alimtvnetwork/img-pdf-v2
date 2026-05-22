"""CLI entry-point shim — delegates to the canonical script's `main()`."""
from __future__ import annotations

from .core import engine


def main() -> None:
    """Run the jpg2pdf command-line interface."""
    engine.main()


if __name__ == "__main__":
    main()

"""jpg2pdf — importable package facade.

Step 3 of the GUI roadmap (.lovable/plan.md): expose the CLI engine as an
importable module so the upcoming GUI (Step 7) can reuse it without
shelling out. The single-file `jpg2pdf.py` script remains the canonical
source of truth and PyInstaller build target; this package is a thin
re-export shim around it. A full file-split refactor is intentionally
deferred to avoid touching 950+ lines in one go.
"""
from .core import __version__  # noqa: F401

"""Engine re-exports from the canonical `jpg2pdf.py` script.

Imports the sibling single-file CLI script as a regular module so PyInstaller
statically analyses its dependencies (json, PIL, pypdf, etc.) and bundles them.
In non-frozen source/dev checkouts only, falls back to importlib by file path.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent.parent
if not getattr(sys, "frozen", False) and str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

try:
    import jpg2pdf as _engine  # type: ignore[import-not-found]
except ImportError:
    if getattr(sys, "frozen", False):
        raise
    import importlib.util
    _SCRIPT = _SRC_DIR / "jpg2pdf.py"
    _spec = importlib.util.spec_from_file_location("jpg2pdf", _SCRIPT)
    if _spec is None or _spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Could not load jpg2pdf engine from {_SCRIPT}")
    _engine = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_engine)

# Public re-exports — keep this list in sync with the symbols the GUI uses.
__version__ = _engine.__version__

kind_of = _engine.kind_of
natural_key = _engine.natural_key
collect_from_folder = _engine.collect_from_folder
collect_from_list = _engine.collect_from_list
html_to_pdf = _engine.html_to_pdf
word_to_pdf = _engine.word_to_pdf
images_to_pdf_chunk = _engine.images_to_pdf_chunk
merge_pdfs = _engine.merge_pdfs
apply_pencil = _engine.apply_pencil
make_page = _engine.make_page
format_pdf_name = _engine.format_pdf_name
load_prefs = _engine.load_prefs
save_prefs = _engine.save_prefs

# Raw engine module — escape hatch for callers that need symbols not
# explicitly re-exported above (e.g. future GUI experiments).
engine = _engine

__all__ = [
    "__version__",
    "engine",
    "kind_of",
    "natural_key",
    "collect_from_folder",
    "collect_from_list",
    "html_to_pdf",
    "word_to_pdf",
    "images_to_pdf_chunk",
    "merge_pdfs",
    "apply_pencil",
    "make_page",
    "format_pdf_name",
    "load_prefs",
    "save_prefs",
]

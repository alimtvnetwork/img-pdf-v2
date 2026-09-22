# Completed Milestone: YouTube Thumbnail Ingestion Engine, GitMap CI/CD & Backend Hardening

**Shipped Version:** v2.2.0
**Date:** 2026-09-22
**Status:** Completed & Verified

## Accomplishments
- **YouTube Ingestion Engine (`tools/jpg2pdf/src/jpg2pdf_app/youtube.py`):**
  - Native standard library URL parser extracting 11-char video IDs from standard, short, embed, live, and share URLs.
  - Video title resolution via public YouTube oEmbed without requiring any API keys.
  - Slug generation formatting titles into strictly lowercase, filesystem-safe filenames (`^[a-z0-9]+(-[a-z0-9]+)*$`).
  - Multi-resolution thumbnail cascading (`maxresdefault.jpg` -> `sddefault.jpg` -> `hqdefault.jpg` -> `mqdefault.jpg` -> `default.jpg`) with payload length checks (>1200 bytes) to automatically discard YouTube's ~1000 byte missing placeholder images.
  - Target/temp directory resolution with collision-safe naming (`<slug>-2.jpg`) and OS file manager opening (`open_directory_in_explorer`).
- **CLI Flags (`tools/jpg2pdf/src/jpg2pdf.py`):**
  - Added `--youtube` (multiple URLs or IDs) for direct thumbnail downloading into the conversion queue.
  - Added `--open-dir` to open the output/thumbnail directory in Explorer/Finder.
  - Added `--download-only` to download thumbnails without triggering PDF/image conversion.
- **Desktop GUI Integration (`tools/jpg2pdf/src/jpg2pdf_app/gui.py`):**
  - Added `File -> Add YouTube URL(s)...` menubar command and a `+ YouTube` toolbar button.
  - Added modal URL input dialog with multi-line support and background worker thread downloading.
  - Added automatic clipboard detection on `<Control-v>` opening the pre-filled prompt when a YouTube link is copied.
  - Tagged downloaded thumbnails as `[yt]` in the reorderable listbox.
- **Backend Encoding & Robustness:**
  - Removed all non-ASCII em-dashes and Unicode artifacts across `jpg2pdf.py`, `core.py`, and `gui.py` to eliminate Windows cp1252 `UnicodeDecodeError`.
  - Added single-chunk direct copy fast-path in `jpg2pdf.py` (`merge_pdfs` and `main()`) allowing image-only PDF generation without requiring `pypdf`.
- **GitMap Release Architecture:**
  - Created `.gitmap/release/v2.1.4.json` and `.gitmap/release/v2.2.0.json`.
  - Updated `.gitmap/release/latest.json` to version `2.2.0`.
- **Rule R3 7-File Minor Version Bump (v2.2.0):**
  - Bumped in lockstep: `tools/jpg2pdf/VERSION`, `tools/jpg2pdf/src/jpg2pdf.py`, `install.ps1`, `install.sh`, `readme.md`, `tools/jpg2pdf/README.md`, and `CHANGELOG.md`.

## Verification
- Verified Python bytecode compilation: `python -m py_compile` on all updated modules passed cleanly.
- Verified zero non-ASCII characters across `jpg2pdf.py`, `core.py`, and `gui.py`.
- Verified CLI argument parser: `python tools/jpg2pdf/src/jpg2pdf.py --help` shows `--youtube`, `--open-dir`, and `--download-only`.
- Verified GUI method: `assert hasattr(g.Jpg2PdfApp, 'on_add_youtube')` passed.
- Verified GitMap metadata: `.gitmap/release/latest.json` points to `2.2.0`.
- Verified 7 synchronized version locations: all 7 files match `2.2.0` / `v2.2.0`.

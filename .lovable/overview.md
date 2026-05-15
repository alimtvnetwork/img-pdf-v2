# Project Overview

**Project:** `jpg2pdf` — Python CLI tool that merges images, PDFs, HTML, and Word documents into a single PDF.

**Location:** `tools/jpg2pdf/` (the TanStack scaffold under `src/` is unused boilerplate — do NOT modify for feature work).

**Current version:** `1.1.0` (tracked in `tools/jpg2pdf/VERSION` and `__version__` in `tools/jpg2pdf/src/jpg2pdf.py` — bump together).

**Platforms:** Windows 10/11 (primary; `run.ps1` bootstraps install + Explorer context menu), macOS, Linux.

**Distribution:** Prebuilt binaries via GitHub Releases (`.github/workflows/release.yml`). One-liner installers: `install.ps1` (Windows), `install.sh` (macOS/Linux).

**Key features:**
- Mixed-input merge in selection order (images, `.pdf`, `.html`/`.htm`, `.docx`/`.doc`).
- Pencil-sketch style for images; default strength is **subtle**.
- Explorer right-click integration on Windows (folders + image/pdf/html/docx files).
- `run.ps1` builds a single-file `.exe` with PyInstaller and registers context menus under HKCU.

**Constraints:**
- PowerShell scripts must be ASCII-only OR saved with UTF-8 BOM (Windows PS 5.1 misreads em-dashes / arrows otherwise).
- The TanStack/Vite project files exist only because of the Lovable template; ignore for jpg2pdf work.

# Plan

Single source of truth for the active roadmap.

## Active

### ⏳ Drop in real Windows screenshots
- Capture real `tools/jpg2pdf/docs/context-menu.png` (Explorer right-click submenu showing "Images to PDF" entries).
- Capture real `tools/jpg2pdf/docs/demo.gif` (screen recording of selecting mixed files → "Combine into PDF").
- Replace the placeholder mockups currently committed.
- **Owner:** user (Windows-only; sandbox cannot capture).

### ⏳ Rebuild + re-register on Windows
- Run `git pull && .\run.ps1 -Force -ShowVerbose` from PowerShell.
- Smoke-test mixed selection: `jpg2pdf --files .\a.jpg .\b.pdf .\c.docx .\d.html --out test.pdf`.
- If `run.ps1` still crashes, send `jpg2pdf-crash.log` (created next to `run.ps1`) or last 30 lines of `%TEMP%\jpg2pdf-logs\*.log`.
- **Owner:** user.

### ⏳ Tag release v1.1.0
- After smoke test passes: `git tag v1.1.0 && git push origin v1.1.0`.
- GitHub Actions (`.github/workflows/release.yml`) will build and publish binaries.
- **Owner:** user.

## Completed

### ✅ Subtle as default pencil strength (v1.1.0)
- `prompt_pencil_strength()` default → `"subtle"`.
- Doc strings + `--ask-strength` help text updated.
- `args.pencil_strength` fallback → `"subtle"`.

### ✅ Bump version to 1.1.0
- `tools/jpg2pdf/VERSION` → `1.1.0`.
- `__version__` in `tools/jpg2pdf/src/jpg2pdf.py` → `1.1.0`.

### ✅ Update root README.md
- Pinned-version examples → `v1.1.0`.
- Added mixed-input table (images/PDF/HTML/Word).
- Added `--ask-strength` live preview example.
- Pencil strength section calls out subtle as default.

### ✅ Harden `run.ps1` (v0.3.0 of run.ps1)
- Top-level `trap` writes `jpg2pdf-crash.log` and pauses on error.
- `Invoke-Logged` wraps `Start-Process` in try/catch for friendly missing-binary messages.

### ✅ Mixed-input merge (images + PDF + HTML + Word)
- `pypdf` for PDF embedding, `xhtml2pdf` for HTML, `docx2pdf` for Word.
- Merged in selection order; consecutive images batched.
- Context menus registered for `.pdf`, `.html`, `.docx`.
- SPEC.md and `tools/jpg2pdf/README.md` updated.

### ✅ Add context-menu.png + demo.gif placeholders
- Created `tools/jpg2pdf/docs/context-menu.png` and `demo.gif` placeholders.
- Wired into root `README.md`.

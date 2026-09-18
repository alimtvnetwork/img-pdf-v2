# Suggestions

## Active Suggestions

### Add `--quality` flag for image compression tuning
- **Status:** Pending
- **Priority:** Low
- **Description:** Currently quality is binary (re-encode vs `--fit original`). A `--quality 1-100` flag would let users trade size for fidelity without forcing original-fit.
- **Added:** 2026-05-15

### Auto-detect LibreOffice on macOS for `.docx`
- **Status:** Pending
- **Priority:** Medium
- **Description:** `docx2pdf` requires MS Word on Windows or LibreOffice on macOS. If `soffice` is on PATH, fall back to it automatically with a clear error if neither is present.
- **Added:** 2026-05-15

### CI smoke test for mixed-input merge
- **Status:** Pending
- **Priority:** Medium
- **Description:** Add a GitHub Actions job that runs `jpg2pdf --files sample.jpg sample.pdf sample.html --out out.pdf` on each platform and asserts the output is a valid multi-page PDF.
- **Added:** 2026-05-15

## Implemented Suggestions

### Subtle as default pencil strength
- **Implemented:** 2026-05-15 (v1.1.0)
- **Notes:** Changed `prompt_pencil_strength()` default and `args.pencil_strength` fallback in `tools/jpg2pdf/src/jpg2pdf.py`.

### Top-level error handler in `run.ps1`
- **Implemented:** 2026-05-15 (run.ps1 v0.3.0)
- **Notes:** Trap writes `jpg2pdf-crash.log` and pauses; `Invoke-Logged` reports missing binaries gracefully.

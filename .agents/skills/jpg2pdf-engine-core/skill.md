---
name: jpg2pdf-engine-core
description: Modifying, maintaining, and extending the core conversion, rendering, and merge engine in tools/jpg2pdf/src/jpg2pdf.py and jpg2pdf_app/core.py.
---

# jpg2pdf Engine Core Skill

This skill governs all development, optimization, and bug fixing inside the core image/document conversion and merge pipeline.

## Architectural Anchors
- Primary Engine: `tools/jpg2pdf/src/jpg2pdf.py`
- Modular Re-export Wrapper: `tools/jpg2pdf/src/jpg2pdf_app/core.py`
- Specification: `tools/jpg2pdf/spec/SPEC.md`
- Tests: `tools/jpg2pdf/tests/test_smoke.py`

## Supported Formats & Dispatch Pipeline
1. **Classification (`kind_of(p)`):**
   - Images (`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif`, `.tiff`): Processed via Pillow (`PIL.Image`).
   - PDFs (`.pdf`): Embedded as-is via `pypdf`, preserving original vector geometry and text.
   - HTML (`.html`, `.htm`): Rendered via `xhtml2pdf`.
   - Word Documents (`.docx`, `.doc`): Converted via `docx2pdf` (requires MS Word on Windows or LibreOffice on macOS).
2. **Batch Chunking for Mixed Selections:**
   - Consecutive images in the input list are batched into a single multi-page intermediate PDF via `images_to_pdf_chunk()` to minimize overhead.
   - Intermediate PDFs and non-image PDFs are assembled into the final output using `merge_pdfs()` via `pypdf.PdfWriter`.

## Non-Negotiable Core Rules
1. **Quality Preservation with `--fit original`:**
   - Never re-encode or compress image streams when `--fit original` is specified. Embed the original JPEG bytes directly.
2. **Pencil-Sketch Effect & Default (`apply_pencil`):**
   - The default pencil strength preset MUST be `subtle`. Never change the default to `normal` or `extra` without explicit user instruction.
   - Pencil presets are defined in module constant `PENCIL_PRESETS`:
     - `subtle`: opacity=0.32, ink_threshold=105, ink_darken=0.52, brightness=1.0 (keeps paper texture visible).
     - `normal`: opacity=0.20, ink_threshold=128, ink_darken=0.32, brightness=1.0.
     - `extra`: opacity=0.10, ink_threshold=165, ink_darken=0.12, brightness=1.02.
3. **Lazy / Local Dependency Imports:**
   - Heavy dependencies (`from pypdf import PdfWriter`, `xhtml2pdf`, `docx2pdf`) must be imported locally inside execution functions (`merge_pdfs`, `html_to_pdf`, `word_to_pdf`) to ensure CLI startup and `--help` execute in under 100ms.
4. **Strict ASCII in Code Comments & Strings:**
   - Use double hyphens `--` instead of Unicode em-dashes `—`. Windows environments (cp1252) will fail or trigger `UnicodeDecodeError` if non-ASCII characters leak into stdout/stderr.
5. **Page Geometry & Sizing (`make_page`):**
   - Sizing standards: `a4` (595x842 pt), `letter` (612x792 pt), `legal` (612x1008 pt).
   - Fitting strategies: `contain`, `cover`, `stretch`, `original`.
   - Auto-rotation honors image aspect ratios while respecting explicit `--rotate` flags.
6. **Stacked Image Mode (`stack_images_to_image`):**
   - Concatenates images vertically or horizontally into a single `.png`/`.jpg`.
   - Non-image inputs are skipped with a user warning in image-only modes.

## Verification Checklist
- Run pytest smoke test:
  ```bash
  python -m pytest -q tools/jpg2pdf/tests
  ```
- Test CLI PNG to PDF conversion:
  ```bash
  python tools/jpg2pdf/src/jpg2pdf.py --files tools/jpg2pdf/docs/context-menu.png --size a4 --out test_out.pdf
  ```
- Verify version flag:
  ```bash
  python tools/jpg2pdf/src/jpg2pdf.py --version
  ```

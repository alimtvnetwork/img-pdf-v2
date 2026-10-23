# 02 — No Smoke Test for Mixed-Input Merge in CI

## Description
`.github/workflows/release.yml` builds binaries but does not invoke them on sample inputs (image + PDF + HTML + Word) to verify the multi-format merge works.

## Status
**Fixed in v2.3.0.** `tools/jpg2pdf/tests/test_merge_mixed.py` runs the mixed merge (image + PDF + HTML + DOCX) in the Ubuntu tests job on every push/PR, via both `--files` and positional paths.

## Risk
A regression in `pypdf`/`xhtml2pdf`/`docx2pdf` integration could ship to users without detection until someone manually tests a mixed selection.

## Proposed fix
Add a CI job per platform that:
1. Creates `sample.jpg`, `sample.pdf`, `sample.html` (no `.docx` on Linux — `docx2pdf` needs Word/LibreOffice).
2. Runs `jpg2pdf --files sample.jpg sample.pdf sample.html --out out.pdf`.
3. Asserts `out.pdf` exists and has ≥ 3 pages via `pypdf`.

## Blockers
- `docx2pdf` smoke on Linux requires installing LibreOffice headless (`apt install libreoffice`) — adds workflow time.
- Windows runner already has Word? Need to verify.

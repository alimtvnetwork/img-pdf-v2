# Plan: GUI & Image Merge/Pencil Modes

**Status:** Active (v2.1.4 in field; pending final asset capture and CI smoke testing)
**Governing Specs:** `spec/00-AI-INSTRUCTIONS.md`, `tools/jpg2pdf/spec/GUI.md`, `tools/jpg2pdf/spec/SPEC.md`

## Summary
Cross-platform desktop GUI for `jpg2pdf`, restructured Windows Explorer context menus with `PDF` / `Image` / `UI` submenus, and image output modes alongside existing PDF output.

## Remaining Steps
1. Capture real `context-menu.png` + `demo.gif` on Windows to replace placeholders.
2. Add CI smoke test for mixed-input merge in `.github/workflows/release.yml`.
3. Add `--quality` flag for image compression tuning.
4. Auto-detect LibreOffice on macOS for `.docx`.
5. Architectural fix for installer context-menu script pinning (`05-installer-pins-ctx-script-to-tag.md`).

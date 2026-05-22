# Plan

Single source of truth for the active roadmap.

## Active — GUI + Image Merge/Pencil Modes (v1.5.0 → v1.6.0)

**Goal:** ship a cross-platform desktop GUI for jpg2pdf, restructured
context menus with `PDF` / `Image` submenus, and a new image-output mode
(merge images into a single stacked image, optionally pencil-styled),
alongside the existing PDF output.

Execute in 20 ordered steps. Do ONE step per "next" from the user. Bump
version + CHANGELOG at every shipping step per `spec/04-versioning.md`.

### Step 1 — Spec + UX sketch
- Write `tools/jpg2pdf/spec/GUI.md`: window layout (drop zone, reorderable
  list, options panel, output mode toggle, convert button), supported drops
  (images/PDF/HTML/DOCX), sorting modes (selection / name / date / folder),
  output modes (PDF / Stacked Image / Pencil Image / Pencil PDF), platform
  launch points (Start menu, Applications, .desktop, context menu "Open
  jpg2pdf…").
- Update `tools/jpg2pdf/spec/SPEC.md` cross-references.
- No code changes yet.

### Step 2 — GUI framework decision + dependency wiring
- Pick Tkinter (stdlib, no extra deps) as the GUI framework — runs on
  Win/mac/Linux with the bundled Python; PyInstaller-friendly.
- Add `tkinterdnd2` to `tools/jpg2pdf/requirements.txt` for native
  drag-and-drop support.
- Decision doc: `.lovable/memory/decisions/03-gui-tkinter.md`.

### Step 3 — Refactor CLI core into importable library
- Split `tools/jpg2pdf/src/jpg2pdf.py` into:
  - `core.py` — file classification, merge engine, pencil renderer,
    image-stacking renderer, sort helpers.
  - `cli.py` — argparse + entry point (current behavior preserved).
  - `__main__.py` — `python -m jpg2pdf` shim.
- No behavior change; CLI smoke tests must pass.

### Step 4 — Implement image-stacking output mode (CLI)
- New flag `--output-mode {pdf,image}` (default `pdf`).
- `--output-mode image` stacks all input images vertically (or
  `--stack horizontal`) into one PNG/JPG, honoring `--size`/`--fit`.
- Skip non-image inputs with a warning in image mode.
- Update CHANGELOG, bump to `1.5.0`.

### Step 5 — Image-mode sorting options (CLI)
- New flag `--sort {selection,name,date,folder}` (default `selection` for
  `--files`, `name` for folder mode).
- Apply uniformly to PDF and image modes.
- Add unit-style smoke tests in `tools/jpg2pdf/tests/`.

### Step 6 — Pencil-image output mode (CLI)
- `--output-mode pencil-image` → stacked image with pencil filter applied
  per input frame before stacking.
- `--output-mode pencil-pdf` alias for current `--style pencil` + PDF.
- Document in `tools/jpg2pdf/README.md`.

### Step 7 — GUI skeleton window
- New file `tools/jpg2pdf/src/gui.py`: main window, menubar (File / Mode /
  Help), empty drop zone, status bar.
- Entry point: `jpg2pdf --gui` and a new `jpg2pdf-gui` console script.
- Launches on all three OSes; closes cleanly.

### Step 8 — Drop zone + reorderable file list
- tkinterdnd2 drop target accepts files/folders.
- Listbox with up/down/remove buttons and drag-to-reorder.
- Shows kind icon (img/pdf/html/doc) and resolved path.

### Step 9 — Options panel
- Output mode radio: PDF / Stacked Image / Pencil PDF / Pencil Image.
- Sort dropdown (selection/name/date/folder).
- Page size, orientation, fit, pencil strength (enabled per mode).
- Output path picker with sensible default.

### Step 10 — Convert action wired to core
- "Convert" button calls `core.run(...)` in a worker thread.
- Progress bar + log pane; success opens output folder.
- Errors surface via dialog, also written to `%LOCALAPPDATA%/jpg2pdf/gui.log`
  (or `~/.local/state/jpg2pdf/gui.log`).

### Step 11 — PyInstaller GUI binary
- Update `.github/workflows/release.yml` to also build
  `jpg2pdf-gui-<platform>` (windowed mode: `--noconsole` on Win/mac).
- Keep existing CLI binaries.
- Update SHA256SUMS + assets table.

### Step 12 — Windows Start-menu + Desktop shortcut
- `install.ps1` (and `run.ps1`) create
  `%APPDATA%\Microsoft\Windows\Start Menu\Programs\jpg2pdf.lnk` pointing
  to `jpg2pdf-gui.exe`.
- Optional `-NoShortcut` flag. `uninstall.ps1` removes it.

### Step 13 — macOS .app bundle + Applications install
- Wrap `jpg2pdf-gui-macos-*` in a minimal `.app` via PyInstaller
  `--windowed`.
- `install.sh` copies to `/Applications/jpg2pdf.app` on macOS.

### Step 14 — Linux .desktop entry
- `install.sh` writes `~/.local/share/applications/jpg2pdf.desktop` with
  `Exec=jpg2pdf-gui` and an icon.
- Update `update-desktop-database` if available.

### Step 15 — Restructured Explorer context menu (Windows)
- Top level: `jpg2pdf ▸`
  - `Open in jpg2pdf…` → launches GUI with selection pre-loaded.
  - `PDF ▸` → all current PDF verbs (A4/Letter/Legal/Pencil/etc.).
  - `Image ▸` → `Merge to single image`, `Pencil image`, sort submenu.
- Update `register-context-menu.ps1` + `unregister-…` + runner.
- Update `spec/SPEC.md` context-menu section.

### Step 16 — macOS / Linux context-menu equivalents
- macOS: ship an Automator Quick Action (`.workflow`) that calls
  `jpg2pdf-gui --files "$@"`; `install.sh` copies to
  `~/Library/Services/`.
- Linux: Nautilus/Dolphin/Thunar action files installed under the right
  XDG paths.

### Step 17 — GUI preset persistence + recent files
- Save last-used options + recent input lists in
  `~/.config/jpg2pdf/settings.json` (XDG / `%APPDATA%`).
- "File ▸ Recent" menu repopulates the drop zone.

### Step 18 — End-to-end smoke tests + CI
- Add `tools/jpg2pdf/tests/test_core.py` covering: PDF merge order,
  stacked-image vertical/horizontal, pencil-image, each sort mode.
- Run on the existing CI matrix (Win/mac/Linux) headless (no GUI test).

### Step 19 — Docs + screenshots
- README sections: "GUI", "Image output mode", "New context-menu layout".
- New screenshots: `docs/gui-window.png`, `docs/context-menu-v2.png`,
  `docs/stacked-image-example.png` (placeholders → user replaces on
  Windows/mac).
- Update `tools/jpg2pdf/README.md` and root `README.md`.

### Step 20 — Release v1.6.0
- Bump VERSION, `__version__`, installer pins, README pins, CHANGELOG.
- Tag `v1.6.0`, push, verify release workflow produces CLI + GUI binaries
  for all five platform/arch combos, plus installer scripts stamped with
  the new repo.
- Update `.gitmap/release/latest.json` + `v1.6.0.json`.
- Smoke-test the published GUI on Windows; close out the plan.

## Completed

Prior milestones (v1.1.0 → v1.4.7) archived. See `CHANGELOG.md` for the
full history: mixed-input merge, subtle pencil default, `run.ps1`
hardening, rich release notes, selected-files context-menu fix,
installer repo stamping.

# jpg2pdf GUI — Specification & UX Sketch

Status: design (Step 1 of the GUI roadmap in `.lovable/plan.md`).

## Goal
Cross-platform desktop GUI for `jpg2pdf` so users can drag-drop mixed
inputs (images, PDF, HTML, DOCX), reorder them, pick an output mode, and
convert — without touching the CLI. Same engine as the CLI; the GUI is
just a thin shell on top of the refactored `core` module (Step 3).

## Non-goals
- No file editing beyond reorder/remove.
- No OCR, no per-page editing, no cloud sync.
- Not a replacement for the CLI — both ship side by side.

## Supported platforms & launch points

| Platform | Binary                        | Launchers installed                                                  |
|----------|-------------------------------|----------------------------------------------------------------------|
| Windows  | `jpg2pdf-gui.exe` (windowed)  | Start-menu shortcut, optional Desktop shortcut, context-menu "Open in jpg2pdf…" |
| macOS    | `jpg2pdf.app` (windowed)      | `/Applications/jpg2pdf.app`, Finder Quick Action under Services      |
| Linux    | `jpg2pdf-gui` ELF             | `~/.local/share/applications/jpg2pdf.desktop`, file-manager actions  |

CLI keeps its existing entry points. The GUI binary is built in the same
release workflow.

## Framework
Tkinter + `tkinterdnd2` for native drag-and-drop. Reasons:
- Stdlib (no heavy runtime), bundles cleanly with PyInstaller.
- Already a dependency-free target on all three OSes.
- Sufficient for our widget set (listbox, radios, dropdowns, progress).

Decision tracked in `.lovable/memory/decisions/03-gui-tkinter.md` (Step 2).

## Window layout

```
+--------------------------------------------------------------+
|  File   Mode   Help                                          |  menubar
+--------------------------------------------------------------+
|  +-- Drop zone -------------------------+  +-- Options ----+ |
|  | Drag files or folders here, or       |  | Output mode  | |
|  | click to browse.                     |  |  ( ) PDF      | |
|  |                                      |  |  ( ) Stacked  | |
|  | [ img] photo-01.jpg     [^][v][x]    |  |  ( ) Pencil PDF|
|  | [ pdf] cover.pdf        [^][v][x]    |  |  ( ) Pencil img|
|  | [ doc] notes.docx       [^][v][x]    |  |              | |
|  | ...                                  |  | Sort: [sel v]| |
|  +--------------------------------------+  | Size: [A4 v] | |
|                                            | Fit:  [contain]|
|                                            | Pencil: [subtle]
|                                            | Output: [...]| |
|                                            +--------------+ |
+--------------------------------------------------------------+
|  Progress: [============>          ]   [ Convert ]           |
+--------------------------------------------------------------+
|  log: queued 5 files... done. -> C:\...\out.pdf              |  status bar
+--------------------------------------------------------------+
```

## Output modes
1. **PDF** — current behavior; merges images/PDF/HTML/DOCX in list order.
2. **Stacked Image** — concatenates images into one PNG/JPG vertically
   (default) or horizontally. Non-image inputs are skipped with a
   warning.
3. **Pencil PDF** — equivalent to current `--style pencil` + PDF.
4. **Pencil Image** — pencil filter per frame, then stacked image.

## Sorting modes
Applies to both PDF and image modes:
- `selection` (default when user drops/selects explicit files)
- `name` (natural sort; default for folder drops)
- `date` (file mtime ascending)
- `folder` (preserve OS folder enumeration order)

User can switch sort at any time; list reorders in place. Manual
up/down/drag overrides revert sort to `selection`.

## Options panel rules
- Pencil strength dropdown is enabled only for Pencil PDF / Pencil
  Image modes.
- Page size / orientation / fit are disabled in Stacked / Pencil Image
  modes (no PDF page geometry).
- Output path defaults to:
  - PDF modes: `<first-input-dir>/jpg2pdf-output.pdf`
  - Image modes: `<first-input-dir>/jpg2pdf-output.png`

## Persistence
`~/.config/jpg2pdf/settings.json` (XDG) / `%APPDATA%\jpg2pdf\settings.json`
stores last-used options + recent input lists. Step 17.

## Logging
GUI logs to `%LOCALAPPDATA%\jpg2pdf\gui.log` (Win) or
`~/.local/state/jpg2pdf/gui.log` (mac/Linux). Rotated at 1 MB, keep 3.

## Context-menu integration (preview — full detail in Step 15/16)
Top-level submenu becomes `jpg2pdf ▸` with:
- `Open in jpg2pdf…` (launches GUI with the current selection).
- `PDF ▸` — current verbs (A4/Letter/Legal, recursive, pencil).
- `Image ▸` — Merge to single image, Pencil image, sort sub-options.

## Cross-references
- `tools/jpg2pdf/spec/SPEC.md` — CLI behavior + current context menu.
- `spec/04-versioning.md` — bump rules (every shipping step).
- `.lovable/plan.md` — 20-step roadmap.

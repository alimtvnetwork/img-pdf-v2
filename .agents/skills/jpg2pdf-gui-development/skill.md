---
name: jpg2pdf-gui-development
description: Developing, styling, debugging, and maintaining the cross-platform Tkinter desktop GUI in tools/jpg2pdf/src/jpg2pdf_app/gui.py, settings.py, and jpg2pdf_gui_entry.py.
---

# jpg2pdf Desktop GUI Development Skill

This skill governs development, UI layout refinements, drag-and-drop wiring, threading, and settings persistence for the `jpg2pdf` desktop GUI.

## Architectural Anchors
- Main UI Application: `tools/jpg2pdf/src/jpg2pdf_app/gui.py` (`Jpg2PdfApp`)
- Persisted Settings: `tools/jpg2pdf/src/jpg2pdf_app/settings.py`
- Dedicated GUI Entry: `tools/jpg2pdf/src/jpg2pdf_gui_entry.py`
- GUI Launch Shim: `tools/jpg2pdf/scripts/register-context-menu.ps1` (`Write-GuiLaunchScript`)
- Specification: `tools/jpg2pdf/spec/GUI.md`

## Key Architecture & Components
1. **Framework Choice:**
   - Tkinter (Python stdlib) with `tkinterdnd2` for native drag-and-drop.
   - Designed to run without heavy external runtimes (no Qt, Electron, or web views), packaging directly into single-file PyInstaller binaries.
2. **Layout Structure (`Jpg2PdfApp`):**
   - **Menubar:** `File` (Add Files, Add Folder, Clear, Recent Inputs, Exit), `Mode` (PDF, Stacked Image, Pencil PDF, Pencil Image), `Help` (About).
   - **Left Pane (Drop Zone & Queue):** Drag-and-drop target accepting files and directories. Reorderable listbox showing kind tag (`[img]`, `[pdf]`, `[html]`, `[doc]`), basename, and action buttons (`Move Up`, `Move Down`, `Remove`).
   - **Right Pane (Options Panel):** Output mode radio buttons, natural/selection sort dropdown, page size (`A4`, `Letter`, `Legal`), orientation, fit mode, pencil strength toggle/dropdown, and output path picker.
   - **Bottom Bar:** Progress bar (`ttk.Progressbar`), log/status label, and `[ Convert ]` button.
3. **Execution Threading (`on_convert`):**
   - The conversion engine must run in a dedicated background daemon thread (`threading.Thread`) to keep the Tkinter UI loop fully responsive.
   - All UI updates (progress bar, log messages, completion alerts) must be marshaled back to the main thread via `root.after()`.
4. **Settings Persistence (`settings.py`):**
   - Locations:
     - Windows: `%APPDATA%\jpg2pdf\settings.json`
     - Linux: `$XDG_CONFIG_HOME/jpg2pdf/settings.json` (fallback `~/.config/jpg2pdf/settings.json`)
     - macOS: `~/Library/Application Support/jpg2pdf/settings.json`
   - Stored keys: `mode`, `sort`, `size`, `orient`, `fit`, `stack`, `pencil`, `strength`, `output`, `recent`.
   - Recent items deduplicated and capped at `MAX_RECENT = 12`.
5. **Window Detached Launching (Past Bug Fix v2.1.4):**
   - `jpg2pdf_gui_entry.py` MUST invoke `run(initial_paths=...)` directly instead of delegating to CLI argument parsers that error without a console.
   - From Windows Explorer context menus, GUI must be spawned via `jpg2pdf-gui-launch.vbs` using `Shell.Application.ShellExecute(..., show=1)` so the window surfaces detached from any hidden queueing cmd process.

## Important Constraints
- Default pencil strength must ALWAYS initialize to `"subtle"`.
- Never attempt to convert TanStack scaffold in `src/` into a web GUI; the product GUI is Tkinter in `tools/jpg2pdf/src/jpg2pdf_app/`.

## Verification Checklist
- Run settings unit tests:
  ```bash
  python -m pytest -q tools/jpg2pdf/tests -k test_settings
  ```
- Test GUI entry argument parser:
  ```bash
  python tools/jpg2pdf/src/jpg2pdf_gui_entry.py --help
  ```

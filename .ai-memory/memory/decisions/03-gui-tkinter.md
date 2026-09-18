# Decision: Tkinter + tkinterdnd2 for the GUI

**Date:** 2026-05-22
**Status:** Accepted (Step 2 of `.lovable/plan.md` GUI roadmap)

## Decision
Use **Tkinter** (Python stdlib) as the GUI framework for `jpg2pdf-gui`,
with **`tkinterdnd2`** for native OS drag-and-drop. No other GUI deps.

## Alternatives considered

| Option       | Pros                                 | Cons (why rejected)                                                |
|--------------|--------------------------------------|--------------------------------------------------------------------|
| **Tkinter**  | Stdlib, PyInstaller-friendly, cross-OS, tiny binary | Plain look — acceptable for a utility |
| PyQt6/PySide6 | Beautiful widgets, native DnD       | +60-100 MB binary, LGPL/commercial nuance, heavier build matrix    |
| wxPython     | Native look                          | Big build deps, slower CI, fewer maintainers                       |
| Web (Tauri / Electron) | Modern UI                  | Adds JS toolchain to a Python repo, defeats single-binary goal     |
| Toga / Beeware | Pure Python, modern                | Immature on Windows DnD, smaller ecosystem                         |

Tkinter wins on the constraint that matters most here: **a single
PyInstaller binary per OS with no extra runtime install**, same shape
as the existing CLI binary.

## Implications
- New dep added to `tools/jpg2pdf/requirements.txt`: `tkinterdnd2>=0.4.2`.
- `tkinterdnd2` ships small native Tcl extensions; PyInstaller picks them
  up automatically via its hook. Verified hook list will be revisited in
  Step 11 when wiring the GUI binary into the release workflow.
- On Linux the system `python3-tk` package must be present at build
  time. `install.sh` will add a `python3-tk` install hint in Step 14.
- On macOS the system Python's Tk is used; no extra brew packages needed
  for the bundled `.app`.

## Non-implications
- CLI behavior unchanged. The GUI is a thin shell on top of the
  refactored `core` module landing in Step 3.
- No web UI, no Lovable Cloud, no TanStack scaffold work.

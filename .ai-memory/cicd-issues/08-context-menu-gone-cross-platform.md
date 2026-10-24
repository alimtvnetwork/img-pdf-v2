# 08 - "Combine into PDF" right-click option gone / does nothing, per OS

**Status:** Fixed in v2.3.0 (see plan 02). Supersedes the open parts of 02 and 05.

## Symptom (user report, 2026-10-24)

Select multiple PDFs / images in the file manager, right-click: there is no
merge option at all on some machines, and on others clicking it does nothing.
Mixed selections (image + PDF + Word) are supposed to merge into one PDF on
Windows, macOS and Linux.

## Root causes found (all verified in code, not guessed)

1. **Windows 11 hides every legacy verb this app registers.**
   `register-context-menu.ps1` only creates legacy `HKCU\...\shell` verbs
   (grouped via two levels of `ExtendedSubCommandsKey`). Windows 11's modern
   context menu shows only packaged `IExplorerCommand` handlers; legacy verbs
   are demoted to "Show more options". To the user the option is *gone*.
   There was not even a simple flat verb as a fallback, and nothing in the
   docs told the user where the entry went.

2. **Installer pinning made fixes invisible (issue 05, architectural part).**
   When `install.ps1` is run the normal way (`irm ... | iex`), `$PSScriptRoot`
   is empty, so the installer *downloads* `register-context-menu.ps1` from
   `raw.githubusercontent.com/<repo>/<latest-release-tag>/...` instead of
   using the registrar that belongs to the code just installed. Registrar
   fixes that were not in the latest tagged release silently never arrived.
   `install.sh` had the same class of bug by re-implementing registration
   inline in heredocs that drifted away from the tested code.

3. **KDE Dolphin servicemenu called the CLI wrong - guaranteed failure.**
   `install.sh` generated `Exec=jpg2pdf --size a4 %F`. `%F` expands to the
   selected files as separate positional arguments, but the CLI accepted
   exactly ONE positional argument (`folder`, `nargs="?"`), so argparse
   exited with code 2 ("unrecognized arguments") and nothing happened.
   Any other launcher that passes a file list positionally (shell
   extensions, `xdg` actions, scripts) hit the same wall.

4. **Word merge silently dropped files on macOS/Linux.**
   `word_to_pdf()` only tried `docx2pdf`, which needs MS Word on Windows /
   macOS and does not work on Linux at all. On Linux (and macOS without
   Word) every `.docx`/`.doc` in a mixed selection was skipped with a
   stderr line nobody sees from a right-click launch; a Word-only
   selection failed with "Nothing was successfully converted".
   No LibreOffice (`soffice --headless`) fallback existed, although
   issue 02 already flagged it.

5. **Zero CI coverage for any of this.**
   The only context-menu test (`tests/test_context_menu.py`) is
   `skipif(sys.platform != "win32")`, and CI tests run on Ubuntu, so the
   suite that gates releases never executed a single context-menu
   assertion. There was also no mixed-input (image+PDF+HTML+Word) merge
   test (issue 02, open since v1.x). Regressions shipped undetected.

6. **Smaller traps in the same path**
   - macOS Quick Actions and Linux Nautilus/KDE entries existed only as
     `install.sh` heredocs - untestable, and diverged from the Windows
     verb set (no Nemo / Thunar coverage at all).
   - The selected-files queue name is the bare verb id, and `a4-pencil`
     exists in both the PDF and Image groups (same args, so harmless,
     but it shows the id namespace was never audited).

## Fix in v2.3.0

- The **binary registers its own context menu**: new
  `--install-context-menu` / `--uninstall-context-menu` flags in
  `jpg2pdf.py` (stdlib only, so they work in the PyInstaller CLI build).
  The registrar now always matches the installed binary version - root
  cause 2 is closed architecturally, not by another tag workaround.
  Both installers run the binary's registrar during installation;
  the old download/inline paths remain as the richer grouped-menu
  layer (Windows) and as fallback for old binaries, but a working
  merge entry no longer depends on them.
- **Windows:** the in-binary registrar writes the runner/launcher files
  and registers a *flat* top-level `Combine into PDF` verb (A4) under
  `*\shell`, every `SystemFileAssociations\<ext>\shell`, and folder /
  folder-background roots, in addition to the grouped menu the
  PowerShell registrar installs. Docs now state plainly: on Windows 11
  the entries live under "Show more options" unless/until an MSIX
  sparse package ships (tracked as follow-up, needs a signed package).
  `register-context-menu.ps1` gains the same flat verb;
  `unregister-context-menu.ps1` removes it.
- **CLI accepts any number of positional paths**: `jpg2pdf a.png b.pdf
  c.docx` merges them in order; a single folder still means folder mode.
  This fixes Dolphin `%F`, Thunar/Nemo `%F`-style actions, and scripts.
- **Word conversion is now truly cross-platform**, in order:
  MS Word via `docx2pdf` (Windows/macOS) -> LibreOffice `soffice
  --headless` (all OSes, handles `.doc` and `.docx`) -> built-in
  dependency-free `.docx` text fallback (stdlib zip/XML -> simple PDF),
  so a `.docx` is never silently dropped again.
- **macOS:** in-binary registrar writes the four Finder Quick Action
  `.workflow` bundles to `~/Library/Services` and flushes `pbs`.
  **Linux:** writes Nautilus scripts, Nemo actions, a Thunar action
  (merged into `uca.xml`), and the KDE Dolphin servicemenu with the
  corrected `Exec=... --files %F`.
- Registration logic is split into pure builders (registry plan /
  file contents) separated from applying them, so it is unit-testable
  on any OS.
- **Tests (run in Ubuntu CI):** mixed merge image+PDF+HTML+DOCX page
  count, positional multi-file merge, DOCX-only merge, context-menu
  builders for Windows/macOS/Linux against a temp HOME, static checks
  on the PowerShell registrar + `install.sh` KDE Exec line.
- Issue 02's CI smoke test is now covered by `test_merge_mixed.py`.

## How to verify

```powershell
# Windows
jpg2pdf.exe --install-context-menu
# right-click 2+ PDFs/images -> Show more options -> Combine into PDF
```

```bash
# macOS / Linux
jpg2pdf --install-context-menu
python -m pytest -q tools/jpg2pdf/tests   # includes the new suites
jpg2pdf a.png b.pdf c.docx --out merged.pdf
```

## Follow-up v2.4.0: visualizer + selection order (2026-10-25)

User question answered by this release: yes, multiple PDFs can be
marked from the right-click menu, and yes, there is now a visualizer
to correct the sequence and the page size before merging.

- New verb "Review & merge in visualizer..." on every OS (Windows
  flat Jpg2PdfVisualizer + PowerShell registrar, macOS Quick Action,
  Linux Nautilus / Nemo / Thunar / KDE). It opens the desktop GUI
  with the selection pre-loaded in delivered order.
- Selection order is the merge contract: CLI --sort selection for
  file selections, GUI forces Sort=selection on preload and on any
  manual reorder (a persisted Sort=name used to silently undo a
  reorder at Convert time), web merges strictly in list order.
- Page size (A4 / Letter / Legal) + orientation + rotation are
  visualizer controls on desktop and web; they lay out image / HTML /
  Word pages only. Embedded PDF pages keep their native size.
- Honest limit, unchanged: a file manager itself may deliver a
  multi-selection in an order other than click order (Explorer's
  per-file verb invocations, %F expansion). The visualizer exists
  precisely to correct that before Convert; the CLI cannot recover
  a click order the file manager never reported.
- Universal installer: install.py (stdlib-only Python one-liner)
  beside install.ps1 / install.sh.
- Tests: tools/jpg2pdf/tests/test_visualizer_order.py and
  tools/jpg2pdf/tests/test_install_py.py, run in Ubuntu CI.

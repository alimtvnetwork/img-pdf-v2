# Plan: Cross-platform right-click "Combine into PDF" fix (v2.3.0)

**Status:** Shipped in v2.3.0 (2026-10-24) - commit 5a78277, tag v2.3.0, GitHub Release published with all platform binaries; CI green on main and on the tag (pytest + 4 build targets). Release binary verified end-to-end: --install-context-menu plus positional mixed merge (image+PDF+DOCX = 4 pages).
**Root-cause record:** .ai-memory/cicd-issues/08-context-menu-gone-cross-platform.md
**Governing specs:** tools/jpg2pdf/spec/SPEC.md, .ai-memory/memory/03-mixed-input-merge.md,
.ai-memory/memory/08-selected-files-hidden-launcher.md

## User requirement

- Select multiple files, right-click, choose merge -> one combined PDF.
- Must work on Windows, macOS, and other OSes (Linux file managers).
- A mixed selection of images + PDFs + Word docs merges into a single PDF,
  in selection order.

## Root causes (summary; full evidence in issue 08)

1. Windows 11 demotes all legacy HKCU shell verbs to "Show more options";
   no flat fallback verb existed, so the entry looked gone.
2. Installers fetched/re-implemented the registrar separately from the
   binary (tag pinning in install.ps1, drifting heredocs in install.sh),
   so registrar fixes did not reliably reach installed machines.
3. KDE Dolphin entry passed selected files positionally (`%F`) but the
   CLI accepted only one positional argument -> argparse exit 2.
4. Word conversion depended on docx2pdf/MS Word only -> `.docx`/`.doc`
   silently dropped on Linux and on macOS without Word.
5. No CI coverage: context-menu test was Windows-only, CI is Ubuntu;
   no mixed-input merge test existed.

## Design

### One merge contract for every OS

`jpg2pdf [options] <path> [<path> ...]`

- 1 path that is a folder -> folder mode (unchanged).
- 1+ file paths -> selection mode, order preserved (new).
- `--files` / `--files-from` keep working unchanged (Windows queue
  runner and macOS Quick Actions already use `--files-from`).

Every file-manager integration on every OS ultimately calls this CLI,
so fixing the contract fixes all launchers at once.

### The binary owns registration

New flags in tools/jpg2pdf/src/jpg2pdf.py (stdlib only, PyInstaller-safe):

- `--install-context-menu` / `--uninstall-context-menu`
- Builders are pure functions returning a plan (registry entries for
  Windows; file path -> content for macOS/Linux) so tests can verify
  every OS on a Linux CI runner; thin appliers do the actual writes.
- Installers (install.ps1 / install.sh) invoke the installed binary's
  own registrar during installation, so a working merge entry never
  depends on the downloaded registrar again; the grouped-menu
  PowerShell registrar and the install.sh inline entries remain as
  the richer/fallback layer on top.

### Per-OS registration

| OS / file manager | Mechanism | Entry |
|---|---|---|
| Windows Explorer | HKCU legacy verbs: flat `Jpg2PdfMerge` + grouped menu from register-context-menu.ps1 | "Combine into PDF" (Win11: under "Show more options") |
| macOS Finder | `~/Library/Services/*.workflow` Quick Actions + `pbs -flush` | Quick Actions -> "Combine into PDF (A4)" etc. |
| Linux GNOME Files | `~/.local/share/nautilus/scripts/` | Scripts -> "jpg2pdf - Combine to PDF (A4)" etc. |
| Linux Cinnamon Nemo | `~/.local/share/nemo/actions/*.nemo_action` | "Combine into PDF (A4)" etc. |
| Linux XFCE Thunar | action merged into `~/.config/Thunar/uca.xml` | "Combine into PDF (A4)" |
| Linux KDE Dolphin | `~/.local/share/kio/servicemenus/jpg2pdf.desktop` | Submenu "Combine into PDF", `Exec=... --files %F` |

Windows 11 top-level menu note: a first-tier Win11 entry requires a
signed MSIX sparse package with an `IExplorerCommand` handler. That is
a separate follow-up (signing + package identity); v2.3.0 guarantees
the entry exists and works via the classic menu and documents this.

### Word conversion chain (word_to_pdf)

1. `docx2pdf` (MS Word) - Windows/macOS, best fidelity.
2. LibreOffice `soffice --headless --convert-to pdf` - all OSes,
   isolated user-profile dir, handles `.doc` + `.docx`.
3. Built-in `.docx` fallback - stdlib zip/XML text extraction rendered
   to a simple PDF with a dependency-free writer; formatting is
   simplified but content is never dropped.

### Tests (all runnable on Ubuntu CI)

- tools/jpg2pdf/tests/test_merge_mixed.py - image+PDF+HTML+DOCX merged
  page count; positional multi-file merge; DOCX-only merge.
- tools/jpg2pdf/tests/test_context_menu_cross_platform.py - builders
  for win32/darwin/linux against a temp HOME; install/uninstall round
  trip for file-based platforms; Windows registry plan contents;
  static checks on register-context-menu.ps1, unregister script and
  the install.sh KDE Exec line.

## Steps

1. [x] Root-cause record (issue 08) + this plan.
2. [x] jpg2pdf.py: positional paths, Word chain, context-menu flags.
3. [x] register-context-menu.ps1 flat verb; unregister updated.
4. [x] install.ps1 / install.sh prefer `jpg2pdf --install-context-menu`;
       fix inline KDE Exec to `--files %F`.
5. [x] New tests; full suite green in a local venv (21 passed, 1 Windows-only skip); CI verification on push.
6. [x] Version 2.3.0 (VERSION, __version__, CHANGELOG, .gitmap/release),
       README + SPEC updates, issue 02/05 status updates.
7. [x] Commit + push (only this work, not the unrelated sync edits in
       the working tree); verify CI green; tag v2.3.0; verify release.

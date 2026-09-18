# Coding Guidelines & Agent Rules

## Core Rules
1. **Strict Boolean Naming:** Use `is_*` and `has_*` only. Never use `can_*`, `should_*`, `was_*`.
2. **Defensive Installers:** Always wrap startup in `install.ps1` and `install.sh` in guards. Never read `$env:TEMP` or `$HOME` without a fallback. Master try/catch or trap handler mandatory.
3. **Always Preserve Fallbacks:** Release binary -> main-branch artifact -> Python source install. Never remove or short-circuit fallbacks.
4. **ASCII-Only in PowerShell:** Windows PowerShell 5.1 mis-parses non-ASCII characters without BOM. Plain ASCII only in `.ps1` files (`->`, `--`, `'`).
5. **Strict Version Synchronization (Rule R3):** Any change to shipping code MUST update all 7 version locations synchronously:
   - `tools/jpg2pdf/VERSION`
   - `tools/jpg2pdf/src/jpg2pdf.py` (`__version__`)
   - `install.ps1` (`$env:JPG2PDF_VERSION`)
   - `install.sh` (`JPG2PDF_VERSION`)
   - `readme.md` (pinned references)
   - `tools/jpg2pdf/README.md` (pinned references)
   - `CHANGELOG.md` (newest entry)
6. **No Scaffold Modification:** Never modify the unused TanStack scaffold in `src/` for `jpg2pdf` product work.
7. **Pencil Default:** Default pencil strength is strictly `subtle`.
8. **5-8 Files Micro-Batching:** All refactors and changes broken into bounded subtasks.

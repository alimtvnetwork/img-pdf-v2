# Coding Guidelines & Technical Standards

Master single source of truth for code standards across Python, PowerShell, Bash, and documentation.

## 1. Zero Tolerance Core Rules (CODE RED)
- **ASCII-Only in PowerShell:** Windows PowerShell 5.1 mis-parses non-ASCII characters without BOM. Stick to ASCII (`->`, `--`, `'`).
- **Defensive Installer Startup:** First executable lines in `install.ps1` and `install.sh` MUST be guarded (no bare `Set-StrictMode`, no bare `set -euo pipefail`, no unguarded reads of `$env:TEMP` or `$HOME`). Wrap in a master try/catch or trap handler.
- **Always Preserve Release -> Main -> Python Source Fallback:** When a release binary is not available, fall back to main-branch artifacts, then to local Python source installation. Never abort without trying source fallback.
- **Strict Version Synchronization (Rule R3):** Any change to shipping code MUST synchronously update 7 locations:
  1. `tools/jpg2pdf/VERSION`
  2. `tools/jpg2pdf/src/jpg2pdf.py` (`__version__`)
  3. `install.ps1` (`$env:JPG2PDF_VERSION`)
  4. `install.sh` (`JPG2PDF_VERSION`)
  5. `readme.md` (pinned examples)
  6. `tools/jpg2pdf/README.md` (pinned examples)
  7. `CHANGELOG.md` (newest entry in Keep-a-Changelog format)
- **TanStack Scaffold Prohibition:** `src/` is unused web boilerplate from the original template. Do NOT modify or refactor `src/` for `jpg2pdf` product work.
- **Quality Preservation:** Never re-encode images when `--fit original` is specified.
- **Pencil Strength Default:** Default pencil strength is strictly `subtle`. Never change to `normal` without user consent.
- **Registry Defaults:** Use `Set-Item -Value` for Explorer context menu command keys; never use literal `(default)` property name.

## 2. Python Conventions
- Functions: Prefer concise, single-purpose functions.
- Envelopes & Types: Explicit returns, proper error capture and logging.
- Booleans: Use positive prefixes (`is_*`, `has_*`).
- Local Imports: Heavy dependencies (e.g. `pypdf`, `xhtml2pdf`, `docx2pdf`) imported locally in execution functions to keep startup sub-second.
- Encoding: Always specify `encoding="utf-8"` when opening files.

## 3. PowerShell Conventions
- Target runtimes: Windows PowerShell 5.1 and PowerShell 7+.
- Helpers: `Get-SafeTempDir`, `Get-GitHubJson`, `Invoke-Logged`.
- Crash Reporting: Always log errors to `%TEMP%\jpg2pdf-install-*.log` or `jpg2pdf-crash.log`.

## 4. Bash Conventions
- Target shells: Bash 3.2+ (macOS default) and Bash 5.x (Linux).
- Startup: Use `set -eo pipefail`, provide fallbacks before `set -u`.
- Error handler: Trap `ERR`, `INT`, `TERM` to print user-friendly error and log path.

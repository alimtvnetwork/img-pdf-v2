---
name: jpg2pdf-installer-and-runner
description: Maintaining, hardening, and testing the cross-platform installers (install.ps1, install.sh), local runner (run.ps1), and uninstaller (uninstall.ps1).
---

# jpg2pdf Installer & Runner Skill

This skill governs the installation, local bootstrapping, and uninstallation scripts for Windows, macOS, and Linux.

## Architectural Anchors
- Windows One-Liner Installer: `install.ps1`
- macOS / Linux Installer: `install.sh`
- Local Developer Runner & PyInstaller Builder: `run.ps1`
- System Uninstaller: `uninstall.ps1`
- PowerShell Spec: `spec/02-powershell.md`
- Bash Spec: `spec/03-bash-installer.md`

## The 3-Tier Fallback Chain (Non-Negotiable Core Rule)
Every installer MUST attempt installation in this exact order, without early exits:
1. **GitHub Release Binary Asset:**
   - Query GitHub API for release tag matching `$JPG2PDF_VERSION` (or `/releases/latest`).
   - Download prebuilt executable (`jpg2pdf-windows-x64.exe`, `jpg2pdf-linux-x64`, etc.).
2. **Main-Branch Workflow Artifact:**
   - If no Release asset is available, attempt to download the latest artifact from `main`.
   - Anonymous download returns `401 Unauthorized` without `GITHUB_TOKEN`, so installers must warn and immediately continue to Tier 3.
3. **Python Source / Wrapper Fallback:**
   - Download the source tarball from GitHub (`main` or release tag).
   - Perform best-effort dependency installation (`python -m pip install -r requirements.txt`).
   - Write a lightweight executable wrapper (`jpg2pdf` or `jpg2pdf.cmd`) pointing to the local `tools/jpg2pdf/src/jpg2pdf.py`.
   - **Crucial Rule:** If the wrapper is created but verification (`jpg2pdf --version`) fails because Python packages are missing, the installer MUST NOT delete the wrapper or exit with failure. It logs a warning, prints the log path, and keeps the wrapper in place for manual dependency resolution.

## Bulletproof Startup Architecture
The user complaint "the install script is still crashing" must never recur:
1. **PowerShell (`install.ps1`, `run.ps1`):**
   - NEVER use `Set-StrictMode` at script startup.
   - Set `$ErrorActionPreference = 'Continue'` at the very top.
   - Wrap the entire script body in a master `try { ... } catch { ... }` block.
   - Safe environment variable reads: Never read `$env:TEMP` or `$HOME` directly without fallback helpers (`Get-SafeTempDir`, `Get-SafeEnv`).
   - Dedicated crash report table generated in the verbose log (`%TEMP%\jpg2pdf-install-*.log`).
2. **Bash (`install.sh`):**
   - Use `set -eo pipefail` initially.
   - Set safe defaults (`HOME_DIR="${HOME:-$PWD}"`, `TMP_DIR="${TMPDIR:-/tmp}"`) BEFORE enabling `set -u` (nounset).
   - Register traps: `trap on_error ERR`, `trap on_error INT TERM`.
   - On macOS: Automatically strip quarantine flag (`xattr -dr com.apple.quarantine`).

## PowerShell Encoding (Windows PS 5.1 Compatibility)
- **ASCII Only:** All `.ps1` files must contain only standard 7-bit ASCII characters.
- Non-ASCII characters (em-dashes `—`, arrows `→`, smart quotes `'`) will fail to parse under Windows 10/11 default PowerShell 5.1 unless saved with a UTF-8 BOM. Prefer ASCII (`--`, `->`, `'`).

## Local Dev Runner (`run.ps1`)
- Bootstraps local environment: checks/installs Python 3 and Git via `winget`.
- Runs PyInstaller `--onefile` to produce `jpg2pdf.exe`.
- Deploys executable to `%USERPROFILE%\Tools\bin` and adds it to User `PATH`.
- Registers context menus via `register-context-menu.ps1`.
- Top-level `trap` handler prints last 40 log lines, creates `jpg2pdf-crash.log`, and pauses so double-clicked windows do not vanish.

## Verification Checklist
- Validate PowerShell parser on Linux/macOS/Windows:
  ```powershell
  pwsh -NoProfile -Command "[System.Management.Automation.Language.Parser]::ParseFile('install.ps1', [ref]$null, [ref]$null)"
  pwsh -NoProfile -Command "[System.Management.Automation.Language.Parser]::ParseFile('run.ps1', [ref]$null, [ref]$null)"
  ```
- Validate Bash syntax:
  ```bash
  bash -n install.sh
  ```
- Check ASCII cleanliness:
  ```bash
  rg '[^\x00-\x7F]' install.ps1 run.ps1 uninstall.ps1
  ```

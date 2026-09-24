---
name: jpg2pdf-scaffold-and-architecture-boundary
description: Enforcing architectural boundaries between the Lovable TanStack web scaffold and the Python jpg2pdf desktop/CLI product.
---

# jpg2pdf Architecture & Repository Boundary Skill

This skill enforces the architectural boundaries of the repository, preventing confusion between web template scaffolding and production Python tools.

## Architectural Anchors
- Real Product Code: `tools/jpg2pdf/` (Python CLI, Tkinter GUI, installers, scripts, tests)
- Web Scaffold / Lovable Template: `src/` (TanStack Router, React, Tailwind, Vite, Cloudflare Wrangler)
- Repository Metadata: `.ai-memory/`, `02-spec/`, `.agents/skills/`, `.github/workflows/`

## Non-Negotiable Core Directives

### 1. The `src/` Web Scaffold Isolation Rule (CODE RED)
- The files under `src/` (`src/routes/`, `src/components/`, `src/routeTree.gen.ts`, `wrangler.jsonc`, `package.json`, etc.) originate from the Lovable application template.
- **Strict Prohibition:** NEVER modify or refactor the web scaffold under `src/` when implementing, fixing, or extending `jpg2pdf` features. All real features, bug fixes, and tests for `jpg2pdf` live under `tools/jpg2pdf/` and root installer scripts (`install.ps1`, `install.sh`, `run.ps1`, `uninstall.ps1`).
- Only modify `src/` if the user explicitly instructs you to update the web landing page, web UI, or Lovable frontend.

### 2. Multi-Platform Delivery Strategy
- **CLI Binary:** Standalone PyInstaller executable (`jpg2pdf-windows-x64.exe`, `jpg2pdf-linux-x64`, `jpg2pdf-macos-x64`).
- **Desktop GUI Binary:** Standalone windowed executable (`jpg2pdf-gui.exe`, `jpg2pdf-gui-linux-x64`, `jpg2pdf-gui-macos.zip`).
- **Installers:** Zero-dependency shell scripts (`install.ps1` for Windows, `install.sh` for Linux/macOS) with a 3-tier fallback chain: Release binary -> Main artifact -> Python source install.
- **Local Runner:** `run.ps1` for local development, building PyInstaller binaries, and testing context menu registration.

### 3. Strict 7-File Version Synchronization (Rule R3)
Any release or shipping code update MUST synchronously update all 7 canonical version locations:
1. `tools/jpg2pdf/VERSION`
2. `tools/jpg2pdf/src/jpg2pdf.py` (`__version__ = "X.Y.Z"`)
3. `install.ps1` (`$env:JPG2PDF_VERSION = "vX.Y.Z"`)
4. `install.sh` (`JPG2PDF_VERSION="${JPG2PDF_VERSION:-vX.Y.Z}"`)
5. `readme.md` (pinned examples)
6. `tools/jpg2pdf/README.md` (pinned examples)
7. `CHANGELOG.md` (new entry in Keep-a-Changelog format)

### 4. PowerShell & Cross-Platform Encoding Rules
- All `.ps1`, `.cmd`, and `.vbs` files MUST be strictly ASCII-only (no Unicode em-dashes `—`, arrows `→`, or smart quotes). Windows PowerShell 5.1 mis-parses non-ASCII files without a UTF-8 BOM.
- Use plain ASCII replacements: `--` instead of `—`, `->` instead of `→`, `'` instead of curly quotes.
- Python files must always open text files with explicit `encoding="utf-8"`.

### 5. Windows Registry Conventions
- Under `HKCU:\Software\Classes`, Explorer static verbs execute only the default (unnamed) value of a `command` key.
- ALWAYS use `Set-Item -Value "..."` in PowerShell.
- NEVER use `Set-ItemProperty -Name "(default)"`.

## Verification Checklist
- Verify no inadvertent edits to `src/`:
  ```bash
  git status -- src/
  ```
- Check version synchronization:
  ```bash
  V=$(cat tools/jpg2pdf/VERSION)
  grep -c "$V" tools/jpg2pdf/src/jpg2pdf.py CHANGELOG.md
  grep -c "v$V" readme.md tools/jpg2pdf/README.md install.ps1 install.sh
  ```
- Check ASCII cleanliness in shell scripts:
  ```bash
  rg '[^\x00-\x7F]' install.ps1 run.ps1 uninstall.ps1 tools/jpg2pdf/scripts/
  ```

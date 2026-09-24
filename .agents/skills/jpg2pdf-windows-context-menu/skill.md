---
name: jpg2pdf-windows-context-menu
description: Registering, debugging, hardening, and maintaining Windows Explorer context menus, batch queue runners, and VBS shims in tools/jpg2pdf/scripts/.
---

# jpg2pdf Windows Context Menu Skill

This skill governs the Explorer right-click integration on Windows, registration under `HKCU:\Software\Classes`, selection batching, and runner shims.

## Architectural Anchors
- Registrar Script: `tools/jpg2pdf/scripts/register-context-menu.ps1`
- Uninstaller Script: `tools/jpg2pdf/scripts/unregister-context-menu.ps1`
- Integration Tests: `tools/jpg2pdf/tests/test_context_menu.py`
- Hidden Launcher Generator: `Write-SelectedFilesLauncher` (`jpg2pdf-selected-launcher.vbs`)
- GUI Launcher Generator: `Write-GuiLaunchScript` (`jpg2pdf-gui-launch.vbs`)
- Queue Runner Generator: `Write-SelectedFilesRunnerV2` (`jpg2pdf-selected-runner.cmd`)
- Registry Root: `HKCU:\Software\Classes` (Zero admin elevation required)

## Context Menu Registry Structure
1. **Target Roots:**
   - Folders: `Directory\shell\Jpg2PdfMenu` and `Directory\Background\shell\Jpg2PdfMenu`
   - Files: `HKCU:\Software\Classes\*\shell\Jpg2PdfMenu`
     - Uses `AppliesTo` filter: `System.FileExtension:=.jpg OR System.FileExtension:=.jpeg OR System.FileExtension:=.png OR System.FileExtension:=.webp OR System.FileExtension:=.bmp OR System.FileExtension:=.tif OR System.FileExtension:=.tiff OR System.FileExtension:=.pdf OR System.FileExtension:=.html OR System.FileExtension:=.htm OR System.FileExtension:=.docx OR System.FileExtension:=.doc`
2. **Submenu Structure (Top level: `Combine into PDF ▸`):**
   - **`PDF ▸`:** Convert to A4, Convert to Letter, Convert to Legal, Convert to A4 (pencil/paper look).
   - **`Image ▸`:** Merge to single image (vertical/horizontal), Merge to pencil image.
   - **`UI ▸`:** `Open in jpg2pdf UI...` (launches desktop GUI with selection pre-loaded).

## Selection Queueing & Batching Architecture (CRITICAL UX)
When a user selects multiple files in Explorer and clicks a context-menu verb, Explorer invokes the static verb **once per file**, passing `%1`.
Without batching, this pops up multiple separate console windows.
The multi-tier batching mechanism solves this:
1. **The Hidden VBS Shim (`jpg2pdf-selected-launcher.vbs`):**
   - Invoked via `wscript.exe //nologo "...\jpg2pdf-selected-launcher.vbs" "<verb>" "%1"`.
   - Runs `jpg2pdf-selected-runner.cmd :queue <verb> "%1"` completely hidden (`intWindowStyle=0`).
2. **The Batched Runner (`jpg2pdf-selected-runner.cmd`):**
   - Appends each path to `%LOCALAPPDATA%\jpg2pdf\queue\<verb>.lst`.
   - Starts a watcher process (`:run`) that polls for queue stability using `ping -n 2 127.0.0.1 >nul` (DO NOT use `timeout /t` because stdin is redirected under wscript and timeout immediately errors).
   - Once the queue size stabilizes over 2 consecutive iterations, the winning process atomically renames the queue file (`ren <queue> <queue>.active`).
   - Only the winner opens **ONE visible console window** (`cmd.exe /d /c ... :exec`) running `jpg2pdf --files-from <queue>.active` and pauses on completion or failure.
   - Logs operations to `%LOCALAPPDATA%\jpg2pdf\context.log`.

## Strict Prohibitions & Hard Rules
1. **Registry Default Values:**
   - Explorer ONLY executes the unnamed/default value of a `command` key.
   - ALWAYS use `Set-Item -Value "..."` in PowerShell.
   - NEVER use `Set-ItemProperty -Name "(default)"` -- this creates a literal named property that Explorer ignores, resulting in silent click failures.
2. **MultiSelectModel:**
   - Always set `MultiSelectModel=Player` on leaf verb registry keys.
3. **ASCII-Only:**
   - Plain ASCII characters only in `register-context-menu.ps1`, `unregister-context-menu.ps1`, `.cmd`, and `.vbs` files (`->`, `--`, `'`). PS 5.1 will mis-parse em-dashes and smart quotes.

## Verification Checklist
- Run context menu integration test suite:
  ```bash
  python -m pytest -q tools/jpg2pdf/tests/test_context_menu.py
  ```
- Parse script syntax in PowerShell:
  ```powershell
  pwsh -NoProfile -Command "[System.Management.Automation.Language.Parser]::ParseFile('tools/jpg2pdf/scripts/register-context-menu.ps1', [ref]$null, [ref]$null)"
  ```
- Check ASCII compliance:
  ```bash
  rg '[^\x00-\x7F]' tools/jpg2pdf/scripts/
  ```
- Verify unregister script cleans up all generated `.vbs` and `.cmd` shims from `%USERPROFILE%\Tools\bin`.

# Windows PowerShell Notes

## PS 5.1 vs PS 7.x

The default Windows PowerShell is 5.1, NOT 7.x. It is much stricter:
- Refuses to parse non-ASCII chars (em-dash `—`, arrow `→`, smart quotes) UNLESS the file is saved with a UTF-8 BOM.
- Different `Start-Process` behavior; missing binaries throw raw .NET stack traces.
- No `$PSStyle`, no ternaries, no `??` operator.

**Rule:** all `.ps1` files in this repo must be ASCII-only, OR explicitly saved with UTF-8 BOM. Default to ASCII.

## `run.ps1` architecture (v0.3.0)

1. **Top-level `trap`** — catches any unhandled error, prints message + source position + last 40 log lines, writes `jpg2pdf-crash.log` next to the script, pauses with "Press Enter to close" so a double-clicked window does not vanish.
2. **`Invoke-Logged`** — wraps `Start-Process` in its own try/catch so missing `winget`/`git`/`python` produces a friendly "Could not launch '<name>': ..." message.
3. **Steps:** install python+git via winget → pull/clone repo → pip install → PyInstaller `--onefile` → copy to `%USERPROFILE%\Tools\bin` → add to User PATH → register context menus.
4. **Switches:** `-NoCompile`, `-NoContextMenu`, `-Unregister`, `-Force`, `-ShowVerbose`.

## Logs

- Per-step: `%TEMP%\jpg2pdf-logs\*.log`.
- Crash dump: `jpg2pdf-crash.log` next to `run.ps1`.
- `-ShowVerbose` streams every subprocess's output live.

## Context menu registration

`tools/jpg2pdf/scripts/register-context-menu.ps1` writes under HKCU (no admin). Uses `MultiSelectModel=Player` for multi-file selections.

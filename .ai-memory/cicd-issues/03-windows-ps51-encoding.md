# 03 — PowerShell 5.1 Mis-parses Non-ASCII Characters

## Description
Windows PowerShell 5.1 (the default on Windows 10/11) refuses to parse `.ps1` files that contain em-dashes (`—`), arrows (`→`, `▸`), or smart quotes UNLESS the file is saved with a UTF-8 BOM. PowerShell 7.x handles them fine, masking the issue during dev.

## Status
**Mitigated by convention.** All `.ps1` files in this repo are ASCII-only.

## Symptoms when violated
- `.\run.ps1` exits with no output before any logging starts.
- Or: parser errors like "Unexpected token" pointing at a fancy quote.

## Prevention
- See `.lovable/strictly-avoid.md` and `.lovable/memory/05-windows-powershell.md`.
- Code review check: `rg '[^\x00-\x7F]' run.ps1 uninstall.ps1 install.ps1 tools/jpg2pdf/scripts/*.ps1` should return nothing.

## When to revisit
If PowerShell 7.x becomes default on Windows, this can be downgraded to "obsolete."

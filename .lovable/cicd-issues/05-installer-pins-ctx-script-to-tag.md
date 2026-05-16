# 05 — Installer pins context-menu script to release tag

**Status:** Fixed in v1.4.3 (workaround); architectural fix pending

## Symptom
User fixes the context-menu registrar on `main`, bumps version, but reinstalls keep getting the OLD broken script. "Nothing happens" persists across multiple "fixes."

## Root cause
`install.ps1` fetches `register-context-menu.ps1` from `https://raw.githubusercontent.com/$Repo/$ctxRef/...` where `$ctxRef` = the resolved release tag (e.g. `v1.4.1`), NOT `main`. So any fix that hasn't been tagged-and-pushed is invisible to end users even though `main` has it.

```powershell
$ctxRef = $(if ($script:Version) { $script:Version } else { "main" })
$ctxUrl = "https://raw.githubusercontent.com/$script:Repo/$ctxRef/tools/jpg2pdf/scripts/register-context-menu.ps1"
```

When `$script:Version` is set by `Get-GitHubJson .../releases/latest`, it's always the latest tag — never `main`.

## Workaround in v1.4.3
- Bump version + push tag immediately after every context-menu fix.
- Memory updated to flag this in `.lovable/memory/02-versioning.md`.

## Proper fix (TODO)
Add `JPG2PDF_CTX_REF` env var or `--ctx-ref main` flag so testers can override. Or fetch the registrar from the same place the binary came from (release asset, not raw main/tag).

## How to verify
After tagging, run:
```powershell
$env:JPG2PDF_VERSION = "v1.4.3"; irm https://raw.githubusercontent.com/alimtvnetwork/img-pdf/main/install.ps1 | iex
```
Then check `%USERPROFILE%\Tools\bin\jpg2pdf-files-a4-pencil.cmd` exists.

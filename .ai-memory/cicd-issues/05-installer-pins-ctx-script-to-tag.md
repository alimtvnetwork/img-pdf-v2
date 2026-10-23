# 05 — Installer pins context-menu script to release tag

**Status:** Fixed in v1.4.4 (workaround); architectural fix shipped in v2.3.0 -- the binary registers its own context menu via `--install-context-menu` and both installers call it first, so the registrar always matches the installed binary (see issue 08). Grouped-registrar ref override (JPG2PDF_CTX_REF) and post-registration verification added afterwards (see Resolution).

## Symptom
User fixes the context-menu registrar on `main`, bumps version, but reinstalls keep getting the OLD broken script. "Nothing happens" persists across multiple "fixes."

## Root cause
`install.ps1` fetches `register-context-menu.ps1` from `https://raw.githubusercontent.com/$Repo/$ctxRef/...` where `$ctxRef` = the resolved release tag (e.g. `v1.4.1`), NOT `main`. So any fix that hasn't been tagged-and-pushed is invisible to end users even though `main` has it.

```powershell
$ctxRef = $(if ($script:Version) { $script:Version } else { "main" })
$ctxUrl = "https://raw.githubusercontent.com/$script:Repo/$ctxRef/tools/jpg2pdf/scripts/register-context-menu.ps1"
```

When `$script:Version` is set by `Get-GitHubJson .../releases/latest`, it's always the latest tag — never `main`.

## Workaround in v1.4.4
- Bump version + push tag immediately after every context-menu fix.
- Memory updated to flag this in `.lovable/memory/02-versioning.md`.

## Proper fix (TODO)
Add `JPG2PDF_CTX_REF` env var or `--ctx-ref main` flag so testers can override. Or fetch the registrar from the same place the binary came from (release asset, not raw main/tag).

## How to verify
After tagging, run:
```powershell
$env:JPG2PDF_VERSION = "v1.4.4"; irm https://raw.githubusercontent.com/alimtvnetwork/img-pdf-v2/main/install.ps1 | iex
```
Then check `%USERPROFILE%\Tools\bin\jpg2pdf-files-a4-pencil.cmd` exists.

## Resolution (registrar ref override + verification)

- `install.ps1` now honors the `JPG2PDF_CTX_REF` environment variable as the top-priority ref for the grouped registrar download, ahead of the installed version tag and `main`, so testers can pin the registrar independently of the binary.
- The installer verifies registration afterwards (`Test-ContextMenuRegistration` in `install.ps1`): parent menu keys with `ExtendedSubCommandsKey`, the leaf `command` values under the `Jpg2Pdf.FolderMenu.PDF` / `Jpg2Pdf.FilesMenu.PDF` classes, the flat `Jpg2PdfMerge` verb, and the selected-files launcher/runner files beside the binary. The binary path is accepted only when the flat verb is actually present (`Test-FlatVerbRegistered`); a failed verification records a crash-report entry and a warning instead of a false success.
- `tools/jpg2pdf/tests/test_context_menu.py` now asserts the full click chain (flat verb, leaf command values, launcher/runner files), not just the parent keys, plus a platform-independent source contract for the override and the verification.

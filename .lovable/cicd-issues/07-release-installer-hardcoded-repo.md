# 07 - Release installer used the old repository

**Status:** Fixed in v1.4.7

## Symptom
Running the installer from the `img-pdf-v2` release page still downloaded assets from `alimtvnetwork/img-pdf`:

```powershell
irm https://github.com/alimtvnetwork/img-pdf-v2/releases/download/v1.4.6/install.ps1 | iex
```

The installer then logged:

```text
Downloading https://github.com/alimtvnetwork/img-pdf/releases/download/v1.4.6/jpg2pdf-windows-x64.exe
Release download failed safely: Not Found
```

## Root cause
`install.ps1` and `install.sh` had a hardcoded fallback repository of `alimtvnetwork/img-pdf`. Release assets were copied into `dist/` unchanged, so an installer downloaded from `img-pdf-v2` did not know which repository hosted it unless the user manually set `JPG2PDF_REPO`.

After the `404`, the installer tried GitHub Actions main-branch artifacts. GitHub's artifact archive download endpoint requires authentication, so anonymous users repeatedly saw `401 Requires authentication` for each fallback run.

## Fix in v1.4.7
- Default repo changed to `alimtvnetwork/img-pdf-v2` in source installers.
- Release notes now set `JPG2PDF_REPO={{REPO}}` in exact-version install snippets.
- The release workflow stamps `github.repository` and the release tag into packaged `install.ps1` / `install.sh` before uploading them.
- Main-branch artifact fallback now short-circuits with one clear warning unless `GITHUB_TOKEN` is set.

## How to verify
After publishing `v1.4.7`, run:

```powershell
& { $env:JPG2PDF_REPO = "alimtvnetwork/img-pdf-v2"; $env:JPG2PDF_VERSION = "v1.4.7"; irm https://github.com/alimtvnetwork/img-pdf-v2/releases/download/v1.4.7/install.ps1 | iex }
```

Expected first binary URL:

```text
https://github.com/alimtvnetwork/img-pdf-v2/releases/download/v1.4.7/jpg2pdf-windows-x64.exe
```
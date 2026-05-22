# Versioning

## Files that MUST stay in sync

| File | Format |
|------|--------|
| `tools/jpg2pdf/VERSION` | `1.1.0` (raw, no `v` prefix, no newline issues) |
| `tools/jpg2pdf/src/jpg2pdf.py` `__version__` | `__version__ = "1.1.0"` |

Bump both in the same edit batch. The CLI's `--version` output reads `__version__`; the installer reads `VERSION`.

## `run.ps1` has its own version

Independent of `jpg2pdf` itself. Currently `RunPs1Version = "0.3.0"`. Bump when changing installer behavior so users can see if they have the latest bootstrap.

## Release tags

- Format: `vMAJOR.MINOR.PATCH` (e.g. `v1.1.0`).
- Pushing a tag triggers `.github/workflows/release.yml` to build and publish binaries.
- Pinned-version examples in root `README.md` reference the latest tag — update them on each release.

## Current state (2026-05-16)

- jpg2pdf: `1.4.7` (not yet tagged). MUST be tagged & pushed — installer pulls `register-context-menu.ps1` from the latest release tag, so untagged fixes never reach end users.
- run.ps1: `0.3.0`.
- Last published tag in release map: `v1.3.4` (per `.gitmap/release/`).

## Release-hosted installers

Packaged release installers must resolve assets from the repository that published the release. The source default is currently `alimtvnetwork/img-pdf-v2`, and `.github/workflows/release.yml` stamps `github.repository` plus the release tag into `dist/install.ps1` and `dist/install.sh` before upload. Release notes exact-version snippets must also set `JPG2PDF_REPO={{REPO}}`. Do not ship release installers that silently fall back to the old `alimtvnetwork/img-pdf-v2` repo.

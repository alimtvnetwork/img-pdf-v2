---
name: jpg2pdf-version-and-release
description: Executing version bumps, changelog synchronization, and CI/CD GitHub Actions release pipeline management.
---

# jpg2pdf Version & Release Management Skill

This skill governs SemVer version bumping, changelog entries, packaging, and the GitHub Actions release workflow.

## Architectural Anchors
- Version Specification: `spec/04-versioning.md`
- CI/CD Specification: `spec/01-cicd.md`
- GitHub Actions Pipeline: `.github/workflows/release.yml`
- Canonical Version File: `tools/jpg2pdf/VERSION`
- Changelog: `CHANGELOG.md`

## Rule R3: Strict 7-File Version Synchronization
Every PR or change that modifies shipping code (CLI, GUI, installers, runners, workflow) MUST update all 7 files in lockstep:

| # | File | Format / Pattern |
|---|------|------------------|
| 1 | `tools/jpg2pdf/VERSION` | `2.1.4` (plain semver, no leading `v`) |
| 2 | `tools/jpg2pdf/src/jpg2pdf.py` | `__version__ = "2.1.4"` |
| 3 | `install.ps1` | `[string]$Version = $env:JPG2PDF_VERSION = "v2.1.4"` |
| 4 | `install.sh` | `JPG2PDF_VERSION="${JPG2PDF_VERSION:-v2.1.4}"` |
| 5 | `readme.md` | Pinned example snippets (e.g. `JPG2PDF_VERSION = "v2.1.4"`) |
| 6 | `tools/jpg2pdf/README.md` | Pinned example snippets |
| 7 | `CHANGELOG.md` | `## [2.1.4] - YYYY-MM-DD` |

## SemVer Decision Guide
- **PATCH (`x.y.Z`):** Bug fixes, documentation tweaks, installer defensive hardening, CI adjustments.
- **MINOR (`x.Y.0`):** New user-visible features (e.g. new input formats, new output modes, GUI additions).
- **MAJOR (`X.0.0`):** Breaking CLI argument changes, breaking binary rename, dropped OS support.

## Changelog Guidelines
- Follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
- Structure: `### Added`, `### Changed`, `### Fixed`, `### Removed`.
- Write in user-visible past tense ("Added option to...", "Fixed context menu..."). Avoid internal implementation noise.

## Release Pipeline (`.github/workflows/release.yml`)
1. **Triggers:**
   - Push to `main` or PR: Runs `tests` job (pytest on Linux) and `ci` job (builds Linux binary and tests). Does NOT publish.
   - Push of tag `v*.*.*`: Runs `tests`, builds 5-platform matrix (Linux x64/arm64, macOS, Windows x64), generates SHA256SUMS, and publishes GitHub Release.
   - `workflow_dispatch`: Supports manual publishing or `notes_only` changelog refresh.
2. **Packaged Installer Stamping:**
   - Before uploading release assets, the workflow stamps `github.repository` and the release tag into `install.ps1` and `install.sh` so downloaded release installers never target stale repository forks.
3. **Multi-line Release Notes:**
   - Always pass changelog body through the step's `env:` block. NEVER pipe `toJSON(...)` directly into a shell `export` (prevents literal `\n` escapes, Issue 04).

## Verification Commands
```bash
# Verify version sync across all 7 locations:
V=$(cat tools/jpg2pdf/VERSION)
grep -c "$V" CHANGELOG.md tools/jpg2pdf/src/jpg2pdf.py
grep -c "v$V" readme.md tools/jpg2pdf/README.md install.ps1 install.sh
```

# 01 — macOS Binaries Not Apple-Notarized

## Description
The `release.yml` workflow ad-hoc signs macOS binaries but does not submit them to Apple's notarization service. Users who download the `.zip` manually trigger Gatekeeper warnings.

## Status
**Accepted limitation.** Notarization requires a paid Apple Developer ID and adds workflow complexity.

## Mitigation
- `install.sh` runs `xattr -dr com.apple.quarantine` automatically after download.
- `tools/jpg2pdf/README.md` documents the manual `xattr` command for users who download the `.zip` directly.

## When to revisit
If the project gains traction with macOS users and someone donates an Apple Developer ID.

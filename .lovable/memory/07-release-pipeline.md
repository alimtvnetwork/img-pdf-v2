# Release Pipeline

## Trigger

Push a semver tag: `git tag v1.1.0 && git push origin v1.1.0`.

## Workflow

`.github/workflows/release.yml` builds on tag push:
- Windows x64 → `jpg2pdf-windows-x64.exe`
- Linux x64 + arm64 → `jpg2pdf-linux-x64`, `jpg2pdf-linux-arm64`
- macOS x64 + arm64 → `jpg2pdf-macos-x64`, `jpg2pdf-macos-arm64` (ad-hoc signed, NOT notarized)
- `SHA256SUMS.txt`

Then publishes a GitHub Release with all assets.

## macOS quarantine

Binaries are ad-hoc signed. The `install.sh` auto-strips `com.apple.quarantine`. Manual `.zip` downloads need:
```
xattr -dr com.apple.quarantine ~/.local/bin/jpg2pdf
```

## After release

Update root `README.md` pinned-version examples to the new tag (`$env:JPG2PDF_VERSION = "v1.1.0"`).

## Release index

`.gitmap/release/*.json` tracks past releases. Latest known: `v0.12.4`. Next planned: `v1.1.0`.

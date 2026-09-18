# Project Structure

This repo contains TWO unrelated things:

1. **`tools/jpg2pdf/`** — the actual product. A Python CLI + PowerShell installer.
2. **`src/`, `vite.config.ts`, `wrangler.jsonc`, etc.** — TanStack Start scaffold from the Lovable template. **Unused.** Do NOT modify for jpg2pdf feature work.

## jpg2pdf layout

```
tools/jpg2pdf/
├── VERSION                          # "1.1.0" — keep in sync with __version__
├── README.md                        # tool-specific docs
├── requirements.txt                 # pillow, pypdf, xhtml2pdf, docx2pdf, pyinstaller
├── spec/SPEC.md                     # full specification
├── src/jpg2pdf.py                   # the CLI (single file)
├── scripts/
│   ├── register-context-menu.ps1
│   └── unregister-context-menu.ps1
└── docs/
    ├── context-menu.png             # placeholder; user must replace with real screenshot
    └── demo.gif                     # placeholder; user must replace with real recording
```

## Top-level installer scripts

- `run.ps1` — Windows bootstrap (winget python+git, build .exe, register context menus).
- `install.ps1` — one-liner Windows installer (downloads prebuilt .exe from Releases).
- `install.sh` — one-liner macOS/Linux installer.
- `uninstall.ps1` — Windows uninstall.

## Release artifacts

`.github/workflows/release.yml` builds on tag push:
- `jpg2pdf-windows-x64.exe`
- `jpg2pdf-linux-x64`, `jpg2pdf-linux-arm64`
- `jpg2pdf-macos-x64`, `jpg2pdf-macos-arm64`
- `SHA256SUMS.txt`

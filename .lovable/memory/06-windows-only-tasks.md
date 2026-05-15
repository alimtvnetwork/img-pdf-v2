# Windows-Only Tasks (Cannot Run in Sandbox)

The AI runs in a Linux sandbox with no remote-desktop, no Windows VM, no file-upload from user disk. The following MUST be delegated to the user with clear instructions:

## 1. Capture screenshots / screen recordings
- `tools/jpg2pdf/docs/context-menu.png` — real Explorer right-click submenu.
- `tools/jpg2pdf/docs/demo.gif` — screen recording of mixed-file selection → "Combine into PDF".
- Tools: Snipping Tool / ScreenToGif / ShareX.

## 2. Rebuild `.exe` + re-register context menu
- Command: `git pull && .\run.ps1 -Force -ShowVerbose` from PowerShell.
- Smoke test: `jpg2pdf --files a.jpg b.pdf c.docx d.html --out test.pdf`.
- On crash: collect `jpg2pdf-crash.log` (next to `run.ps1`) or last 30 lines from `%TEMP%\jpg2pdf-logs\*.log`.

## 3. Tag and push releases
- `git tag v1.1.0 && git push origin v1.1.0`.
- Triggers `.github/workflows/release.yml` to build cross-platform binaries.

## 4. Verify install on a clean Windows VM (optional but recommended)
- The one-liner `irm https://.../install.ps1 | iex` should drop `.exe` into `%USERPROFILE%\Tools\bin` and register menus.

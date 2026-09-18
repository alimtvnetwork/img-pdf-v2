# Strictly Avoid (CODE RED)

Hard prohibitions for `img-pdf-v2`:
- Never commit non-ASCII characters to PowerShell `.ps1` files without UTF-8 BOM.
- Never modify `src/` for `jpg2pdf` product features.
- Never bump `VERSION` without bumping `__version__` in `jpg2pdf.py`.
- Never replace `run.ps1` with a version lacking top-level trap handler.
- Never re-encode images when `--fit original`.
- Never use unguarded `Start-Process` for `winget`/`git`/`python`.
- Never change the default pencil strength from `subtle`.
- Never disable CI/CD checks or GitHub Actions workflows to force a pipeline to pass.
- Never use literal `(default)` property in PowerShell registry commands; use `Set-Item -Value`.

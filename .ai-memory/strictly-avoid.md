# Strictly Avoid

Hard prohibitions for this project. Violating these causes user-visible breakage.

- **Non-ASCII chars in PowerShell scripts** without UTF-8 BOM: PS 5.1 mojibake's em-dashes (—), arrows (→, ▸), and smart quotes. Use plain ASCII (`-`, `->`, `>`) or save the file with UTF-8 BOM.
- **Modifying the TanStack scaffold under `src/`** for `jpg2pdf` feature work: it's unused boilerplate from the Lovable template. All real code lives under `tools/jpg2pdf/`.
- **Bumping `VERSION` without bumping `__version__` in `jpg2pdf.py`** (or vice versa): they must stay in sync.
- **Replacing `run.ps1` with a version that lacks the top-level `trap` handler**: without it, double-clicked windows close instantly on error and users get no log.
- **Re-encoding images when `--fit original`**: quality must be preserved.
- **Using `Start-Process` for `winget`/`git`/`python` without try/catch in `Invoke-Logged`**: a missing binary then prints a raw .NET stack trace.
- **Replacing the pencil-strength default with anything other than `subtle`**: user explicitly chose subtle as the default.

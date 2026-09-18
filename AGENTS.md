# AGENTS.md — Agent Operating Contract

## Repository Identity & Purpose
- Project: `img-pdf-v2` (`jpg2pdf`)
- Real product location: `tools/jpg2pdf/` (CLI and Tkinter GUI)
- Unused template: `src/` (TanStack scaffold) — DO NOT EDIT

## Hard Constraints
- Enforce strict boolean standard: `is_*` and `has_*` only.
- Preserve ASCII-only characters in `.ps1` files.
- Never break installer startup in `install.ps1` or `install.sh`.
- Always preserve release -> main -> source fallbacks.
- Keep root readme strictly lowercase `readme.md`.
- Never disable CI/CD checks.

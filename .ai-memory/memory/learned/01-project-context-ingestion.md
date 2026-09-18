# Learned 01: Project Context & Architecture Ingestion

**Date:** 2026-09-19
**Scope:** Full repository onboarding, git history, specs, memory, and runtime validation.

## Repository Overview
- **Product:** `jpg2pdf` — Cross-platform desktop CLI and Tkinter GUI tool for combining images, PDFs, HTML, and Word docs into a single PDF or stacked image.
- **Location:** `tools/jpg2pdf/` (CLI `src/jpg2pdf.py`, GUI `src/jpg2pdf_app/gui.py`, launchers, tests).
- **Auxiliary:** Root installers `install.ps1` and `install.sh`, local packager `run.ps1`.
- **Ignored:** `src/` (unused TanStack scaffold).

## File Counts & Catalog
- Specifications read: 6 (`spec/00-AI-INSTRUCTIONS.md`, `spec/01-cicd.md`, `spec/02-powershell.md`, `spec/03-bash-installer.md`, `spec/04-versioning.md`, `spec/README.md`) + 2 feature specs (`tools/jpg2pdf/spec/SPEC.md`, `tools/jpg2pdf/spec/GUI.md`).
- Memory files indexed: 13 topic & decision documents.
- CI/CD issues absorbed: 7 past failure analyses.
- Recent Git Commits: 10 commits inspected. Root `README.md` renamed to lowercase `readme.md`, committed, and pushed.

## Key Rules Enforced
- ASCII-only in PowerShell scripts.
- Guarded installer startup with release -> main -> source fallbacks.
- Strict 7-file version synchronization (Rule R3).
- Default pencil strength `subtle`.

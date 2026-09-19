# Retrospectives

## Retrospective 01: Windows Encoding & PS 5.1 Quirks
- **Failure:** PowerShell 5.1 crashed on non-ASCII characters without BOM.
- **Root Cause:** PS 5.1 default text encoding assumption.
- **Learning:** Mandate ASCII-only for all `.ps1` files.

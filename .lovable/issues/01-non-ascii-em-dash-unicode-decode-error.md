# Issue 01: Non-ASCII Em-Dash in Python Source Causing Subprocess UnicodeDecodeError

**Status:** Open / Documented
**File:** `tools/jpg2pdf/src/jpg2pdf.py` (e.g. line 492: `# local import — heavy dep`) and `tools/jpg2pdf/tests/test_smoke.py`

## Error Description
When running test suites or capturing subprocess output on Windows without explicit UTF-8 decoding, Windows default code page (e.g. cp1252) encounters non-ASCII byte `0x97` (em-dash `—`) in comments/strings, triggering:
`UnicodeDecodeError: 'utf-8' codec can't decode byte 0x97 in position 400: invalid start byte`

## Root Cause Analysis
Python files contained non-ASCII em-dash characters (`—`) in comments and strings. When subprocesses pipe stdout/stderr in Windows environments, default encoding mismatch causes `UnicodeDecodeError` or parser failure. Furthermore, `pypdf` is not installed globally in the environment, which caused `merge_pdfs` to fail with `ModuleNotFoundError: No module named 'pypdf'`.

## Fix Strategy
1. Ensure all Python source files and PowerShell files adhere strictly to ASCII characters (`--` instead of `—`).
2. Ensure test subprocess calls explicitly set `encoding="utf-8", errors="replace"`.
3. Install required packages from `tools/jpg2pdf/requirements.txt` (`pypdf`, `xhtml2pdf`, etc.) in the active virtual environment.

## Prevention Checklist
- Run `rg '[^\x00-\x7F]' tools/` as part of CI linting.
- In tests, always capture subprocess output with UTF-8 or resilient encoding.

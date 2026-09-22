---
name: jpg2pdf-testing-and-qa
description: Running test suites, verifying regressions, handling subprocess encoding edge cases, and conducting quality assurance for jpg2pdf.
---

# jpg2pdf Testing & QA Skill

This skill governs testing protocols, regression prevention, pytest execution, and cross-platform verification for `jpg2pdf`.

## Architectural Anchors
- Pytest Suite: `tools/jpg2pdf/tests/test_smoke.py`
- Requirements: `tools/jpg2pdf/requirements.txt`
- CI Test Job: `.github/workflows/release.yml` (`tests` job)
- Known Issue Log: `.lovable/issues/01-non-ascii-em-dash-unicode-decode-error.md`

## Test Matrix & Capabilities (`test_smoke.py`)
1. **`test_settings_roundtrip_and_push_recent`:**
   - Verifies GUI settings save and load cycle with mocked APPDATA/XDG/HOME.
   - Asserts default pencil strength is strictly `"subtle"`.
   - Tests deduplication and list capping (`MAX_RECENT = 12`).
2. **`test_cli_version_matches_files`:**
   - Asserts `jpg2pdf --version` matches the string in `tools/jpg2pdf/VERSION`.
3. **`test_cli_png_to_pdf`:**
   - Synthesizes a test PNG, executes `jpg2pdf --files ... --size a4 --out out.pdf`.
   - Asserts returncode is 0 and output starts with `%PDF`.
4. **`test_cli_stacked_image`:**
   - Stacks two images into an output image with `--output-mode image --stack vertical`.
   - Asserts valid PNG header bytes (`\x89PNG\r\n\x1a\n`).
5. **`test_cli_html_to_pdf`:**
   - Synthesizes HTML and verifies conversion via `xhtml2pdf`.
   - Skips gracefully if `xhtml2pdf` is unavailable in the environment.

## Encoding & Subprocess Guardrails
1. **Windows cp1252 Decoding Trap:**
   - When running CLI tests or capturing subprocess output in Python on Windows, NEVER rely on system default encoding.
   - Always pass `encoding="utf-8", errors="replace"` to `subprocess.run()`.
   - Code comments in `tools/jpg2pdf/src/` must remain pure ASCII (`--` instead of `—`) to prevent decode failures in parent test runners.
2. **Local Test Virtual Environment:**
   - Running tests requires: `pip install -r tools/jpg2pdf/requirements.txt pytest`.
   - If heavy packages (`pypdf`, `xhtml2pdf`) are missing in the local environment, test suites will report `ModuleNotFoundError`. Verify package presence before running.

## Pre-Release Verification Protocol
Before declaring any task or PR complete, execute the full verification battery:
```bash
# 1. Validate Bash installer
bash -n install.sh

# 2. Validate PowerShell syntax
pwsh -NoProfile -Command "[System.Management.Automation.Language.Parser]::ParseFile('install.ps1', [ref]$null, [ref]$null)"
pwsh -NoProfile -Command "[System.Management.Automation.Language.Parser]::ParseFile('tools/jpg2pdf/scripts/register-context-menu.ps1', [ref]$null, [ref]$null)"

# 3. Verify CLI version
python tools/jpg2pdf/src/jpg2pdf.py --version

# 4. Check 7-file version synchronization
V=$(cat tools/jpg2pdf/VERSION)
grep -c "$V" CHANGELOG.md tools/jpg2pdf/src/jpg2pdf.py
grep -c "v$V" readme.md tools/jpg2pdf/README.md install.ps1 install.sh

# 5. Check ASCII cleanliness in PowerShell files
rg '[^\x00-\x7F]' install.ps1 run.ps1 tools/jpg2pdf/scripts/

# 6. Run pytest
python -m pytest -q tools/jpg2pdf/tests
```

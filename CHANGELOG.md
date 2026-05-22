# Changelog

All notable changes to `jpg2pdf` are documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.0] - 2026-05-22

### Added — Desktop GUI (complete roadmap, Steps 1–19)
- **GUI application** (`jpg2pdf-gui` / `jpg2pdf --gui` / `python -m jpg2pdf_app`) built on tkinter with drag-and-drop (via `tkinterdnd2`), reorderable file list, live options panel, Convert with progress bar, and modal status reporting.
- **Options panel** (Step 9): output mode (PDF / PNG stack), sort order, page size + orientation, image fit, stack direction, pencil-toggle with strength preset (`subtle` default), and output-path picker.
- **Convert engine integration** (Step 10): GUI calls the CLI in a background thread; auto-derives output path; reports success or the last stderr line. When frozen as a PyInstaller bundle, runs the engine in-process.
- **PyInstaller binaries** (Step 11): cross-platform `jpg2pdf-gui-{platform}` one-file builds for Windows x64, Linux x64/arm64, and macOS x64/arm64. macOS `.app` bundles (`jpg2pdf-gui-macos-{x64,arm64}.app.zip`) with ad-hoc code signing.
- **Windows installer enhancements** (Step 12): `install.ps1` downloads the GUI binary, creates Start-menu + Desktop shortcuts, and the uninstaller removes them.
- **macOS release matrix** (Step 13): re-enabled macOS x64 + arm64 CLI + GUI builds after runner availability returned.
- **Linux .desktop entry** (Step 14): registers the GUI in the Applications menu and as a file handler for images, PDFs, HTML and Word documents.
- **Grouped Windows Explorer context menu** (Step 15): restructured from a flat list into `Combine into PDF` -> `PDF` (A4/Letter/Legal + recursive) and `Combine into PDF` -> `Image` (rotations + pencil). Uses `ExtendedSubCommandsKey` with `MultiSelectModel=Player` and a queued `jpg2pdf-selected-runner.cmd` batcher.
- **macOS Quick Actions + Linux file-manager actions** (Step 16): four Automator `.workflow` bundles (A4/Letter/Legal/Pencil) for macOS Finder Services; Nautilus scripts and a KDE Dolphin servicemenu for Linux.
- **GUI preset persistence + recent files** (Step 17): settings saved to OS-standard config dirs (`%APPDATA%`, `~/Library/Application Support`, `$XDG_CONFIG_HOME`). Persisted: all options + last output path. File > Recent submenu with up to 12 deduped paths, populated only after successful conversions.
- **End-to-end smoke tests + CI gating** (Step 18): `pytest` suite for settings round-trip, recent-files logic, and CLI conversions (PNG->PDF, stack, HTML->PDF). CI `tests` job gates the five-platform `build` matrix.
- **Documentation refresh** (Step 19): README rewritten with full GUI, desktop-integration, and installer coverage; new `docs/gui.png` screenshot.

### Changed
- All of the above represents the completion of the GUI roadmap begun in v1.5.0.

## [1.5.11] - 2026-05-22

### Changed
- Documentation refresh for the GUI + desktop integration work (Step 19 of the GUI roadmap).
- `tools/jpg2pdf/README.md` rewritten to cover: the desktop GUI (launch commands, drag-and-drop, preset/recent-files persistence and config locations), the grouped Windows Explorer context menu (PDF / Image submenus), macOS `.app` bundle + Finder Quick Actions, Linux `.desktop` entry + Nautilus scripts + KDE Dolphin servicemenu, full table of installer skip flags (`JPG2PDF_NO_GUI/APP/QUICKACTION/DESKTOP/FM_ACTIONS/SHORTCUTS/CONTEXT_MENU`), updated macOS notes (binaries now built and ad-hoc signed), pytest smoke command, and refreshed release/repo-layout sections.
- New `tools/jpg2pdf/docs/gui.png` screenshot embedded at the top of the README.

## [1.5.10] - 2026-05-22

### Added
- End-to-end smoke test suite + CI gating (Step 18 of the GUI roadmap).
- New `tools/jpg2pdf/tests/test_smoke.py` covers: GUI settings round-trip + recent-files dedupe/cap, CLI `--version` matches `VERSION` file, single-PNG -> PDF (validates `%PDF` magic), 2-PNG vertical stack to PNG (validates PNG magic), and HTML -> PDF (skipped when xhtml2pdf is unavailable).
- New `tests` job in `.github/workflows/release.yml` runs `pytest -q tests` on Linux for every PR, main push, tag push, and manual dispatch (except notes-only mode). Both the existing PR `ci` job and the cross-platform `build` matrix now `needs: [tests]`, so a failing pytest blocks all five-platform binary builds before they consume runner time.

## [1.5.9] - 2026-05-22

### Added
- GUI preset persistence and recent files (Step 17 of the GUI roadmap). New `jpg2pdf_app/settings.py` reads/writes a JSON config at `%APPDATA%\jpg2pdf\settings.json` (Windows), `~/Library/Application Support/jpg2pdf/settings.json` (macOS), or `$XDG_CONFIG_HOME/jpg2pdf/settings.json` (Linux, default `~/.config/jpg2pdf/settings.json`).
- Persisted across sessions: output mode, sort, page size, orientation, fit, stack, pencil toggle, pencil strength (default `subtle` preserved), and last output path.
- New **File > Recent** submenu listing up to 12 most-recent input paths (deduped, truncated for display); selecting one re-adds it to the queue. Includes a `Clear recent` action. Recents are populated only after successful conversions.
- Settings are written on `WM_DELETE_WINDOW` (window close, including the Quit menu item) and after each successful conversion. Any read/write failure degrades silently to in-memory defaults.

## [1.5.8] - 2026-05-22

### Added
- macOS Quick Actions + Linux file-manager actions (Step 16 of the GUI roadmap).
  - **macOS**: `install.sh` writes four Automator `.workflow` bundles to `~/Library/Services/` (`Combine into PDF (A4)`, `(Letter)`, `(Legal)`, `(A4, pencil)`) with `NSSendFileTypes` covering images, PDF, HTML and Word. Each workflow runs a `Run Shell Script` action that funnels selected files through `--files-from`. Flushes the Services menu via `pbs -flush`. Skip with `JPG2PDF_NO_QUICKACTION=1`.
  - **Linux**: Installs four executable Nautilus scripts to `~/.local/share/nautilus/scripts/` (using `$NAUTILUS_SCRIPT_SELECTED_FILE_PATHS`) and a KDE Dolphin servicemenu at `~/.local/share/kio/servicemenus/jpg2pdf.desktop` with a `Combine into PDF` submenu containing A4 / Letter / Legal / Pencil actions. Skip with `JPG2PDF_NO_FM_ACTIONS=1`.
  - Only installs when the CLI binary is actually present at `$PREFIX/jpg2pdf`.

## [1.5.7] - 2026-05-22

### Changed
- Restructured the Windows Explorer context menu into two grouped submenus (Step 15 of the GUI roadmap). The flat `Combine into PDF (A4)`, `(A4, rotate 90 CW)`, etc. list is gone. New shape: `Combine into PDF` -> `PDF` (A4, Letter, Legal, plus `A4 recursive` for folders) and `Combine into PDF` -> `Image` (rotations + `A4 pencil / paper look`). Implemented via new `Jpg2Pdf.{Folder,Files}Menu.{PDF,Image}` registry classes wired through `ExtendedSubCommandsKey`. `MultiSelectModel=Player` and the queued `jpg2pdf-selected-runner.cmd` are preserved on every leaf. `unregister-context-menu.ps1` cleans up the new child classes too. Labels stay ASCII (no chevron glyphs) so the script remains safe for Windows PowerShell 5.1.

## [1.5.6] - 2026-05-22

### Added
- Linux installer now writes a freedesktop `.desktop` entry to `~/.local/share/applications/jpg2pdf.desktop` so the GUI shows up in the Applications menu and as a file-handler for images, PDFs, HTML and Word documents (Step 14 of the GUI roadmap). Uses `Icon=application-pdf`, refreshes the menu via `update-desktop-database` when available, and is skippable with `JPG2PDF_NO_DESKTOP=1`. Only created when the GUI binary was installed successfully.

## [1.5.5] - 2026-05-22

### Added
- macOS is back in the release matrix: `jpg2pdf-macos-x64` (Intel) and `jpg2pdf-macos-arm64` (Apple Silicon) CLI + GUI binaries, plus a packaged `.app` bundle (`jpg2pdf-gui-macos-{x64,arm64}.app.zip`) built from PyInstaller's `--windowed` mode with bundle identifier `dev.jpg2pdf.gui` (Step 13 of the GUI roadmap).
- `install.sh` now also installs the GUI binary to `$PREFIX/jpg2pdf-gui` and, on macOS, downloads the `.app.zip` and unpacks it to `/Applications/jpg2pdf.app` (or `~/Applications/jpg2pdf.app` when the system folder isn't writable). Skip with `JPG2PDF_NO_GUI=1`, `JPG2PDF_NO_APP=1`, or force user-local with `JPG2PDF_APP_USER_ONLY=1`.

## [1.5.4] - 2026-05-22


### Added
- Windows installer (`install.ps1`) now also downloads `jpg2pdf-gui-windows-x64.exe` to `%USERPROFILE%\Tools\bin\jpg2pdf-gui.exe` and creates Start-menu + Desktop shortcuts pointing at it (Step 12 of the GUI roadmap). Skip with `$env:JPG2PDF_NO_GUI = "1"` or `$env:JPG2PDF_NO_SHORTCUTS = "1"`. Falls back to the latest main-branch artifact when no release asset is available, and never aborts the CLI install if the GUI bits are missing.
- `uninstall.ps1` now also removes `jpg2pdf-gui.exe` and both shortcuts.

## [1.5.3] - 2026-05-22


### Added
- Release workflow now compiles a second PyInstaller binary, `jpg2pdf-gui-{platform}` (Windows/Linux x64/Linux arm64), built from `jpg2pdf_app/__main__.py` with `--windowed`, bundled `jpg2pdf.py` data file, and `tkinterdnd2` + `tkinter` hidden imports. Both binaries are smoke-tested with `--version` (GUI smoke skipped on Windows where `--windowed` detaches stdout) and uploaded as separate release assets.
- GUI `Convert` now runs the engine in-process when the GUI is a frozen PyInstaller bundle (no python interpreter on PATH), and stays on subprocess in dev for crash isolation.

## [1.5.2] - 2026-05-22


### Added
- GUI Convert button (Step 10 of the desktop-GUI roadmap): runs the `jpg2pdf` CLI in a background thread with the options panel's current values, auto-derives an output path next to the first input if none is set, and reports success or the last stderr line in the status bar plus a modal. Existing CLI flags (`--output-mode`, `--sort`, `--size`, `--orientation`, `--fit`, `--stack`, `--style pencil`, `--pencil-strength`, `--out`, `--files`) do all the work — no engine changes.

## [1.5.1] - 2026-05-22


### Added
- GUI options panel (Step 9 of the desktop-GUI roadmap): output mode, sort, page size + orientation, image fit, stack direction, pencil toggle with strength preset (defaults to `subtle`), and an output-path picker. The `Mode` menubar entry now syncs the output-mode dropdown. Convert wiring (Step 10) is next.

## [1.5.0] - 2026-05-22


### Added
- New `--output-mode` option with four values: `pdf` (default, current behavior), `image` (stack image inputs into one PNG/JPG), `pencil-pdf` (PDF + forced pencil style), and `pencil-image` (stacked image + forced pencil style). Use `--stack horizontal` for side-by-side instead of the default vertical stack. Non-image inputs (PDF/HTML/DOCX) are skipped with a warning in any `image`/`pencil-image` mode.
- New `--sort {selection,name,date,folder,auto}` option (default `auto`). `auto` picks `selection` for `--files`/`--files-from` and `name` for folder mode. `date` sorts by file mtime ascending; `folder` preserves the OS filesystem enumeration order. Applies to both PDF and image output modes.
- Importable `jpg2pdf_app` Python package (`core`, `cli`, `__main__`) under `tools/jpg2pdf/src/`, exposing the engine for the upcoming desktop GUI.

## [1.4.7] - 2026-05-16

### Fixed
- Release-hosted installers now download binaries from the same repository that published the release instead of falling back to the old `alimtvnetwork/img-pdf` repository. Root cause: the install scripts had a hardcoded default repo, so running the installer from `img-pdf-v2` still looked for `v1.4.6` assets under `img-pdf`, got `404 Not Found`, then repeatedly tried unauthenticated GitHub Actions artifact downloads. The release workflow now stamps the release repo/tag into packaged installers, the release notes pass `JPG2PDF_REPO`, and installers skip the main-artifact fallback unless `GITHUB_TOKEN` is available.

See the full history in [CHANGELOG.md](./CHANGELOG.md).

## [1.4.6] - 2026-05-16

### Fixed
- Selected-files Explorer actions now keep the real runner console visible and avoid stale-lock no-ops. Root cause: the queued runner still used a nested `start`, so the first Explorer-launched process could exit while the worker failed invisibly; a leftover lock could then make every later click append to the queue and exit with no conversion. The runner now executes synchronously in the visible console and atomically claims the queue file before running one `jpg2pdf --files-from` conversion for pencil/A4/rotate selected-file actions.

See the full history in [CHANGELOG.md](./CHANGELOG.md).

## [1.4.5] - 2026-05-16

### Fixed
- Selected-files Explorer actions now batch correctly instead of appearing to do nothing. Root cause: Windows static context-menu verbs do not pass every selected file through `%*`; Explorer starts the command once per selected file and passes that file as `%1`. The selected-files menu now writes a small `jpg2pdf-selected-runner.cmd` next to `jpg2pdf.exe`, queues those per-file invocations for the chosen verb, then runs one visible `jpg2pdf --files-from` conversion. Pencil conversion now opens once, prompts once, and logs failures to `%LOCALAPPDATA%\jpg2pdf\context.log`.

See the full history in [CHANGELOG.md](./CHANGELOG.md).

## [1.4.4] - 2026-05-16

### Fixed
- Selected-files Explorer verbs now write the registry command into the real unnamed/default value instead of a fragile literal `(default)` property. Root cause: the submenu labels could appear because `MUIVerb` was set, but Explorer had no executable command to run for the leaf verb, so clicking selected-image actions looked like nothing happened. Folder and selected-file verbs now use `Set-Item -Value` for registry defaults, selected files run through a direct visible `cmd.exe` command with `MultiSelectModel=Player`, and failures log to `%LOCALAPPDATA%\jpg2pdf\context.log` with a pause on non-zero exit.

### Changed
- Removed the generated per-verb `.cmd` launcher files from the selected-files path; registration also cleans up any stale `jpg2pdf-files-*.cmd` files from older installs.

See the full history in [CHANGELOG.md](./CHANGELOG.md).

## [1.4.3] - 2026-05-16

### Fixed
- Selected-files context menu now reliably runs even where 1.4.2's fix appeared to do nothing. Root cause was two-fold: (1) the 1.4.2 fix only landed on `main` and was never tagged, so the installer (which pulls `register-context-menu.ps1` from the latest **release tag** = `v1.4.1`) kept fetching the broken VBS launcher chain; (2) nested registry quoting + ExecutionPolicy/AV interference made even the direct `cmd.exe /c` verbs flash-and-die with no diagnostics. Now ships per-verb `.cmd` launchers next to `jpg2pdf.exe` (`jpg2pdf-files-a4.cmd`, `...-pencil.cmd`, etc.). Each launcher logs to `%LOCALAPPDATA%\jpg2pdf\context.log` and PAUSES on non-zero exit so users can read errors. Registry entries are now trivially quoted: `cmd.exe /c ""<launcher>" %*"`. Pencil's `--ask-strength` prompt works again.

### Changed
- Old `jpg2pdf-selected-launcher.ps1` / `.vbs` files are auto-removed from the install dir on re-register.

See the full history in [CHANGELOG.md](./CHANGELOG.md).

## [1.4.2] - 2026-05-16

### Fixed
- Selected-files context menu actions ("Combine into PDF (A4)", "...pencil/paper look", etc.) now actually run. Root cause: the previous registration routed every invocation through a hidden VBS -> hidden PowerShell launcher -> mutex/queue -> `Start-Process` of a generated `.cmd`. On common hosts (ExecutionPolicy locked by GPO, AV blocking temp `.cmd`, hidden PowerShell not surfacing a console) the entire chain silently failed and "nothing happened" when clicking the menu. Replaced with a direct `cmd.exe /c` command per leaf verb with `MultiSelectModel=Player`, so Explorer opens a single visible console and runs `jpg2pdf --files %*` once. Pencil's `--ask-strength` prompt is now interactive again.

See the full history in [CHANGELOG.md](./CHANGELOG.md).

## [1.4.1] - 2026-05-16

### Fixed
- GitHub Release body no longer shows literal `\n### Changed\n- ...` escape sequences. Root cause: the workflow piped the changelog through `toJSON(...)` which emits a JSON-encoded string with literal `\n` escapes; bash then assigned that raw to `CHANGELOG` and Python substituted the escaped text verbatim. The changelog body is now passed through the step's `env:` block so real newlines are preserved end-to-end.

See the full history in [CHANGELOG.md](./CHANGELOG.md).

## [1.4.0] - 2026-05-16

### Changed
- Version bump to 1.4.0. Includes the release-notes template cleanup (dynamic `{{REPO}}`, single-line install per platform, link to full CHANGELOG.md at tag) previously staged under 1.3.8.

See the full history in [CHANGELOG.md](./CHANGELOG.md).

## [1.3.8] - 2026-05-16

### Changed
- Release notes template: replaced the three-line "generic installer" snippets with a single one-liner per platform that resolves the repo via the workflow's `{{REPO}}` placeholder (no hardcoded URLs from other projects).
- Release notes now link to the full [CHANGELOG.md](./CHANGELOG.md) at the released tag instead of inlining install variants.
- Dropped macOS rows from the release assets table since macOS binary runners are disabled; macOS users install via `install.sh` Python fallback.

## [1.3.7] - 2026-05-16

### Fixed
- macOS/Linux source fallback: installs Python dependencies into a local vendor directory first and writes wrappers that include that directory on `PYTHONPATH`, so macOS can run from Python source while binary runners are disabled.
- Installers now treat post-install `--version` failures as logged diagnostics, not fatal crashes, leaving the installed binary or Python wrapper in place for repair.
- Verbose logs now preserve guarded crash-report rows outside shell subshells and print the log path when any fallback or verification issue was recorded.

### Changed
- Installer specs and memory now explicitly require source/Python verification failures to be non-fatal once the wrapper has been installed.

## [1.3.6] - 2026-05-15

### Fixed
- Windows installer: preserved installer state across guarded try/catch steps so release, main-artifact, PATH, and context-menu phases cannot lose required variables and crash later.
- macOS/Linux installer: hardened startup, archive extraction, artifact copying, source wrapper writing, pip dependency install, and PATH guidance so failures are logged and continue to the next fallback where possible.

### Changed
- Installer specs and memory now point at the reference installer hardening pattern and require a final crash-report section with the failed variable/step, location, and fallback used.

## [1.3.5] - 2026-05-15

### Added
- macOS/Linux installer: added a final Python source fallback when no release binary or main-branch artifact is available, so macOS can still install while macOS binary runners are disabled.
- Installer specs and memory now require the full release -> main artifact -> source/Python fallback chain with crash-report logging.

### Fixed
- Installers now record guarded failures and the fallback used in a dedicated crash report section instead of exiting without enough diagnostic context.
- Windows installer now falls back to a Python wrapper install when prebuilt binaries cannot be located.

## [1.3.4] - 2026-05-15

### Changed
- CI/CD: dropped the macOS build matrix entries (`macos-13` x64 and `macos-14` arm64). GitHub-hosted macOS runners were stuck queued for hours and blocking every release. The matrix now ships Windows x64 and Linux x64/arm64 only; macOS users can build from source until macOS runners are restored.
- Release job no longer publishes `jpg2pdf-macos-x64` / `jpg2pdf-macos-arm64` assets.

## [1.3.1] - 2026-05-15

### Fixed
- Windows installer: replaced the remaining GitHub JSON reads with guarded HTTP reads plus guarded JSON parsing, so a bad release/API response cannot abort before the main-branch artifact fallback runs.
- Verified the release-missing path continues into main-branch artifact lookup instead of crashing.

### Changed
- Pinned-version install snippets in `README.md`, `tools/jpg2pdf/README.md`, `install.ps1`, and `install.sh` now reference `v1.3.1`.

## [1.3.0] - 2026-05-15

### Fixed
- Windows installer: hardened the very early bootstrap so a hostile host cannot crash the shell before logging is initialized. `$ErrorActionPreference`, the global `trap`, `Stop-Safely`/`Die` lookup, `$args` access, the argument parser loop, and the TLS 1.2 enable call are now each wrapped in their own `try/catch` (or guarded with `Get-Command Die`).
- Argument parsing now reads from a defensive `$InstallerArgs` copy of `$args` so `irm | iex` hosts that do not expose `$args` cannot fault on `.Count`.
- Verified: when no GitHub Release (or no matching asset) is available, both installers continue to fall back to the latest successful `main`-branch workflow artifact.

### Changed
- Pinned-version install snippets in `README.md`, `tools/jpg2pdf/README.md`, `install.ps1`, and `install.sh` now reference `v1.3.0`.

## [1.2.9] - 2026-05-15

### Fixed
- Windows installer: added safe wrappers around the remaining filesystem, archive, path-resolution, download, and context-menu execution reads so failures are caught before they can crash the shell.
- The release download path still falls back to the latest successful `main`-branch artifact when no release or release asset is usable.

### Changed
- Root and tool README pinned-version install snippets now reference `v1.2.9`.

## [1.2.8] - 2026-05-15

### Fixed
- Windows installer: added a guarded environment-read helper and moved repo/version/debug/token/temp/PATH reads through safe fallbacks so host PowerShell profile or environment issues cannot crash before installer error handling.
- macOS/Linux installer: replaced the remaining direct temp-error-file read with a safe read helper while preserving release-to-main-artifact fallback behavior.

### Changed
- Root and tool README pinned-version install snippets now reference `v1.2.8`.

## [1.2.7] - 2026-05-15

### Fixed
- Windows installer: removed the advanced `param` binding block so `irm ... | iex` cannot crash before installer-owned safe handling starts; arguments are now parsed inside the top-level guarded block.
- macOS/Linux installer: moved strict-mode execution inside a guarded `main` wrapper so unexpected startup reads fail through the safe error path instead of aborting the shell.
- Release lookup and pinned-release download still fall back to the latest successful `main`-branch workflow artifact when no usable release asset exists.

### Changed
- Root and tool README pinned-version install snippets now reference `v1.2.7`.

## [1.2.6] - 2026-05-15

### Added
- Installers (`install.sh`, `install.ps1`) now support a `--debug` / `--verbose` flag (and `JPG2PDF_DEBUG=1` env var) that enables verbose tracing, environment diagnostics, and writes a full timestamped log to a temp file. Override the path with `JPG2PDF_LOG`.
- Every installer error and warning now points at the saved log file so crash output can be captured and shared.

### Changed
- Root and tool README pinned-version install snippets now reference `v1.2.6`.

## [1.2.5] - 2026-05-15

### Fixed
- Windows installer: guarded session PATH updates so a missing `$env:Path` cannot crash after a release or main-branch artifact download succeeds.

### Changed
- Root and tool README pinned-version install snippets now reference `v1.2.5`.

## [1.2.4] - 2026-05-15

### Fixed
- Windows installer: guarded every remaining path/temp/home lookup used before and after release download, including context-menu script staging, so failures are caught and reported safely.
- macOS/Linux installer: removed the last `$HOME` assumption from PATH guidance so `set -u` cannot abort after a successful main-branch artifact fallback.

### Changed
- Root and tool README pinned-version install snippets now reference `v1.2.4`.

## [1.2.3] - 2026-05-15

### Fixed
- Windows installer: moved environment/default resolution inside the protected install block and added a top-level trap so failures before any GitHub read/download are reported safely instead of crashing the shell.
- Windows installer: made main-branch artifact extraction resilient when the temp directory variable is missing or cleanup runs after an early failure.
- macOS/Linux installer: added first-line-safe exit/signal traps before reading environment defaults, with a safe prefix fallback when `$HOME` is unavailable.

### Changed
- Root and tool README pinned-version install snippets now reference `v1.2.3`.

## [1.2.2] - 2026-05-15

### Fixed
- Windows installer: wrapped the whole install flow and every GitHub read/download in safe try/catch handling so failures report cleanly instead of crashing the PowerShell session.
- Installers now fall back to the latest successful `main`-branch workflow artifact when no GitHub Release is available or the release asset download fails.

### Changed
- Root and tool README pinned-version install snippets now reference `v1.2.2`.

## [1.2.1] - 2026-05-15

### Changed
- CI/CD: the cross-platform **build matrix** (Windows x64, Linux x64/arm64, macOS x64/arm64) now runs on every push to `main` and every PR — not only on tag pushes. Binaries for all five targets are produced and uploaded as workflow artifacts on every commit, so regressions on any OS are caught immediately.
- The lightweight `ci` job (linux-x64 build + version-sync check) is now PR-only, since `main` pushes already trigger the full matrix.
- Publishing to a GitHub Release still happens **only** on `v*` tag pushes or manual `workflow_dispatch` — regular commits build but don't publish.

## [1.2.0] - 2026-05-15

### Added
- **Rich GitHub release pages** modeled on the gitmap-v19 layout. Every tag push now publishes a release with a Changelog section, **Release Info** table (version, commit, branch, build date, Python version), **Checksums (SHA256)** block, **Install** snippets (Windows PowerShell quick install, Linux/macOS quick install, pinned-version installers, manual download), and an **Assets** table.
- `.github/release-notes-template.md` drives the release body; the workflow renders it via Python placeholder substitution.
- `install.ps1` and `install.sh` are now uploaded as release assets so the "Quick install" URLs in the release body resolve directly from the tag.

### Changed
- `.github/workflows/release.yml` extracts the matching `## [VERSION]` section from `CHANGELOG.md` instead of relying on `generate_release_notes: true`.
- Root `README.md` pinned-version examples bumped to `v1.2.0`.

## [1.1.0] - 2026-05-15

### Added
- **Mixed-input merge**: a single invocation now accepts images (`.jpg/.jpeg/.png/.webp/.bmp/.tif/.tiff`), PDFs (`.pdf`), HTML (`.html/.htm`), and Word documents (`.docx/.doc`) and merges them into one PDF in the order selected. Consecutive images are batched into image pages; PDFs are embedded with `pypdf`; HTML is rendered via `xhtml2pdf`; Word is converted via `docx2pdf` (Windows) with a graceful fallback message elsewhere.
- Context-menu entries on Windows now register for `.pdf`, `.html`, and `.docx` in addition to images, so right-click → "Combine into PDF" works on any supported file type.
- `--ask-strength` live preview flag for interactively choosing pencil strength before render.

### Changed
- Default pencil strength is now `subtle` (was `normal`). Affects `prompt_pencil_strength()`, `--ask-strength` help text, and the `args.pencil_strength` fallback.
- Root `README.md` rewritten: pinned-version install snippets reference `v1.1.0`, mixed-input matrix added, pencil-strength section explicitly documents `subtle` as the default.

### Fixed
- `run.ps1` no longer crashes silently when a child step fails. A top-level `trap` writes `jpg2pdf-crash.log` next to the script and pauses the console so users can read the error before the window closes.
- Friendlier error message when the compiled `jpg2pdf` binary is missing — `Invoke-Logged` wraps `Start-Process` in try/catch and points users at the rebuild command.

### Internal
- Bumped `run.ps1` bootstrap version to `0.3.0`.
- Bootstrapped the `.lovable/` institutional-memory system (overview, plan, suggestions, memory/, pending-issues/, solved-issues/, cicd-issues/, prompts/).

## [0.12.4] - prior
- Last published tag before the 1.1.0 line. See GitHub Releases for older notes.

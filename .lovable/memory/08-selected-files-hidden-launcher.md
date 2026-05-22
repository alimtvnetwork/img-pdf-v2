---
name: Selected-files hidden launcher
description: As of v2.1.2, Selected files context-menu verbs route through jpg2pdf-selected-launcher.vbs (wscript hidden) so per-file Explorer invocations do not flash a cmd window each. Only one visible console opens when the runner wins the queue race and executes jpg2pdf.
type: feature
---

## Why the VBS shim exists

Windows Explorer's legacy verbs invoke the registered command ONCE PER SELECTED FILE.
The old design pointed each invocation at a `.cmd` file, so selecting 7 files produced
7 flashing cmd windows (6 of them losers that exited immediately after appending to a
queue). User reported this as "very disturbing".

## Current flow (v2.1.2+)

1. Registry command per leaf:
   `wscript.exe "...\jpg2pdf-selected-launcher.vbs" "<verb-id>" "<verb-args>" "%1"`
2. `jpg2pdf-selected-launcher.vbs` runs `cmd.exe /d /c "...\jpg2pdf-selected-runner.cmd" ...`
   with `intWindowStyle=0` → fully hidden.
3. The runner appends the path to `%LOCALAPPDATA%\jpg2pdf\queue\<verb>.lst`,
   re-execs itself in `--run` mode, polls until the queue stabilises, and then
   atomically `ren`s the queue file. Only the winner proceeds.
4. The winner uses `start "jpg2pdf - <verb>" cmd.exe /d /c ...--exec...` to open
   ONE visible console that runs `jpg2pdf --files-from <queue>` and pauses on exit.

## Files

- `tools/jpg2pdf/scripts/register-context-menu.ps1`
  - `Write-SelectedFilesLauncher` — emits the `.vbs` shim.
  - `Write-SelectedFilesRunnerV2` — emits the runner with `:queue / :run / :exec` dispatch.
  - `New-SelectedFilesCommand` — produces the `wscript.exe ...` registry string.
- `tools/jpg2pdf/scripts/unregister-context-menu.ps1` — removes the `.vbs` shim too.

## Important

This OVERRIDES the older rule that prohibited hidden VBS/PowerShell launchers.
The prohibition was about chained launcher hacks for selection batching that
were unreliable. This shim is intentionally minimal (only hides the per-file
queueing call) and is required to deliver a non-disturbing UX. Do NOT revert.

# 06 - Selected-files registry command was not a real default value

**Status:** Fixed in v1.4.6

## Symptom
Right-clicking selected images and choosing any selected-files verb, including pencil convert, appears to do nothing.

## Root cause
The selected-files submenu could be visible because `MUIVerb` was present, but the command path was wrong for Windows static verbs: Explorer does not pass every selected file as `%*`. It invokes the command once per selected file and passes that file as `%1`, so direct `jpg2pdf --files %*` never received the complete selection as one conversion.

The v1.4.5 queued runner still had a silent-failure gap: it used nested `start`, so the first visible Explorer process could exit while the worker failed elsewhere. If that worker left the queue lock behind, every future click appended to the queue and exited because the lock already existed.

Explorer only runs the unnamed/default value under each `command` key. If that value is missing or the launcher file is blocked/removed, clicking the menu item silently returns.

## Fix in v1.4.6
- Use `Set-Item -Value` for every registry default value.
- Install one `jpg2pdf-selected-runner.cmd` next to `jpg2pdf.exe`.
- Register selected-files leaf verbs to call the runner with `%1`.
- The runner queues the per-file invocations briefly, then runs one visible `jpg2pdf --files-from <queue>` conversion.
- The first lock owner now runs synchronously in the visible console instead of using nested `start`.
- Stale locks without an `active` marker are removed so future clicks do not silently no-op.
- Keep `MultiSelectModel=Player` on every selected-files leaf verb.
- Log selected-files invocations to `%LOCALAPPDATA%\jpg2pdf\context.log` and pause on non-zero exit.

## How to verify
After reinstalling v1.4.6, right-click multiple selected supported files and choose:
`Combine into PDF (A4, pencil / paper look)`.

Expected:
- One visible console opens.
- The pencil strength prompt appears.
- `%LOCALAPPDATA%\jpg2pdf\context.log` receives a new entry.

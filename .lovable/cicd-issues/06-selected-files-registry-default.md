# 06 - Selected-files registry command was not a real default value

**Status:** Fixed in v1.4.4

## Symptom
Right-clicking selected images and choosing any selected-files verb, including pencil convert, appears to do nothing.

## Root cause
The selected-files submenu could be visible because `MUIVerb` was present, but the command registration was too fragile: prior fixes relied on generated `.cmd` launchers and registry default writes that were easy to mis-register as a literal `(default)` property instead of the unnamed command value Explorer executes.

Explorer only runs the unnamed/default value under each `command` key. If that value is missing or the launcher file is blocked/removed, clicking the menu item silently returns.

## Fix in v1.4.4
- Use `Set-Item -Value` for every registry default value.
- Remove generated per-verb `.cmd` launchers from the selected-files path.
- Register selected-files leaf verbs as direct visible `cmd.exe /v:on /d /c ... jpg2pdf --files %*` commands.
- Keep `MultiSelectModel=Player` on every selected-files leaf verb.
- Log selected-files invocations to `%LOCALAPPDATA%\jpg2pdf\context.log` and pause on non-zero exit.

## How to verify
After reinstalling v1.4.4, right-click multiple selected supported files and choose:
`Combine into PDF (A4, pencil / paper look)`.

Expected:
- One visible console opens.
- The pencil strength prompt appears.
- `%LOCALAPPDATA%\jpg2pdf\context.log` receives a new entry.

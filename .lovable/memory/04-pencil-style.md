# Pencil Style

`--style pencil` applies a faint pencil-on-paper look to image inputs (no effect on PDF/HTML/Word).

## Strength presets

| Preset | Description |
|--------|-------------|
| `subtle` | **Default.** Gentle effect, keeps paper texture visible. |
| `normal` | Balanced. |
| `strong` | Heavy darkening, more sketch-like. |

## Flags

- `--style pencil` — enable.
- `--pencil-strength {subtle|normal|strong}` — pick preset (default `subtle`).
- `--ask-strength` — interactive prompt with live preview before generating final PDF.

## Code anchors (in `tools/jpg2pdf/src/jpg2pdf.py`)

- `prompt_pencil_strength()` — interactive picker, default `"subtle"`.
- `args.pencil_strength` fallback — `"subtle"` if unset.
- `--ask-strength` argparse help text — calls out subtle as default.

## Why subtle by default

User explicitly stated this preference. See [decisions/01-subtle-default.md](./decisions/01-subtle-default.md).

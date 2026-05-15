# Decision: Subtle as Default Pencil Strength

**Date:** 2026-05-15
**Version landed:** 1.1.0

## Decision
`--style pencil` defaults to `--pencil-strength subtle` instead of `normal`.

## Rationale
User explicitly requested it: "I mentioned to have the subtle as a default, uh, preview or default option."

## Implementation
- `prompt_pencil_strength()` default → `"subtle"`.
- `args.pencil_strength` fallback → `"subtle"`.
- Doc strings + `--ask-strength` help text mention "(default, gentle, keeps paper texture)".

## Reversibility
Trivial — change three string literals in `tools/jpg2pdf/src/jpg2pdf.py`. But do NOT revert without an explicit user request.

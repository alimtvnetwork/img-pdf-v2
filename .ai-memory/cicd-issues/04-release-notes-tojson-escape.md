# 04 — Release notes body rendered with literal `\n` escapes

## Symptom

GitHub Release pages (e.g. v1.4.0) displayed the changelog as one wrapped
paragraph containing literal `\n### Changed\n- ...` text instead of proper
markdown headings and bullets.

## Root cause

`.github/workflows/release.yml` passed the multi-line changelog into the
Python templater like this:

```yaml
export CHANGELOG=${{ toJSON(steps.changelog.outputs.body) }}
```

`toJSON` emits a JSON-encoded string, e.g. `"\n### Changed\n- ..."`. After
GitHub Actions substitutes that into the shell script, bash drops the
surrounding quotes but keeps the inner `\n` as the two literal characters
backslash + n. Python's `os.environ["CHANGELOG"]` then contained those
literals, and `str.replace("{{CHANGELOG}}", v)` substituted them verbatim
into the rendered release notes.

## Fix

Pass the changelog through the step's `env:` block instead — GitHub Actions
preserves real newlines in env values:

```yaml
env:
  CHANGELOG_BODY: ${{ steps.changelog.outputs.body }}
```

Then read `os.environ["CHANGELOG_BODY"]` in the Python templater. No
`toJSON`, no JSON decoding step needed.

## Prevention

- Never combine `toJSON(...)` with a plain shell `export VAR=...` unless you
  also `json.loads` the value before using it.
- For multi-line workflow outputs, prefer the `env:` block on the step that
  consumes them.

Fixed in: v1.4.1.

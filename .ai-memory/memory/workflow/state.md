# Workflow State

**Last updated:** 2026-05-16

## ✅ Done
- Mixed-input merge (images + PDF + HTML + Word) shipped.
- Context menus registered for all supported file types.
- `run.ps1` hardened with top-level trap + crash log (v0.3.0).
- Pencil-strength default switched to `subtle`.
- Version bumped to `1.1.0` in both `VERSION` and `__version__`.
- Root `README.md` updated: pinned version `v1.1.0`, mixed-input table, `--ask-strength` example.
- Memory system bootstrapped under `.lovable/`.
- Installer specs/memory require release -> main artifact -> Python source fallback with reference-style guarded crash logging.
- Installer specs/memory require source-wrapper verification failures to be logged as non-fatal so macOS/Linux Python fallback stays installed for diagnosis.
- Selected-files Explorer verbs fixed for v1.4.6: static Explorer verbs are batched through `jpg2pdf-selected-runner.cmd`, then run once with `--files-from`; failures log to `%LOCALAPPDATA%\jpg2pdf\context.log`.
- Release installer repo mismatch fixed for v1.4.7: release-hosted installers are stamped with the publishing repo/tag and anonymous main-artifact fallback no longer loops through 401s.

## 🔄 In Progress
- *(none — awaiting user-side install smoke test)*

## ⏳ Pending
1. Capture real `context-menu.png` + `demo.gif` and replace placeholders.
2. Smoke-test the v1.4.7 installers on Windows/macOS/Linux with debug logging.
3. `git tag v1.4.7 && git push origin v1.4.7` once smoke tests pass.

## 🚫 Blocked
- *(none)*

## Next logical step
Tag and publish v1.4.7, then install from the v1.4.7 release page and confirm the first binary URL uses `alimtvnetwork/img-pdf-v2`.

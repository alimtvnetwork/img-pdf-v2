# CI/CD Issues Index

Summary of known CI/CD issues. Each issue has a detailed file under `.lovable/cicd-issues/`.

| # | File | Status | Summary |
|---|------|--------|---------|
| 01 | [01-macos-notarization.md](./cicd-issues/01-macos-notarization.md) | Accepted limitation | macOS binaries are ad-hoc signed, not Apple-notarized; users see Gatekeeper warning. |
| 02 | [02-no-mixed-input-smoke-test.md](./cicd-issues/02-no-mixed-input-smoke-test.md) | Open | Release workflow does not smoke-test mixed-input merge before publishing. |
| 03 | [03-windows-ps51-encoding.md](./cicd-issues/03-windows-ps51-encoding.md) | Mitigated | PS 5.1 misreads non-ASCII chars in `.ps1` files; mitigated by ASCII-only convention. |
| 04 | [04-release-notes-tojson-escape.md](./cicd-issues/04-release-notes-tojson-escape.md) | Fixed in v1.4.1 | Release body showed literal `\n` escapes because `toJSON()` was piped through bash `export` without JSON-decoding. |
| 05 | [05-installer-pins-ctx-script-to-tag.md](./cicd-issues/05-installer-pins-ctx-script-to-tag.md) | Mitigated in v1.4.4 | Installer fetches `register-context-menu.ps1` from the resolved release tag, so untagged fixes on `main` never reach users. |
| 06 | [06-selected-files-registry-default.md](./cicd-issues/06-selected-files-registry-default.md) | Fixed in v1.4.6 | Selected-files static verbs invoked once per file; the new runner batches those invocations and runs one conversion. |
| 07 | [07-release-installer-hardcoded-repo.md](./cicd-issues/07-release-installer-hardcoded-repo.md) | Fixed in v1.4.7 | Release-hosted installers used the old hardcoded repo and then hit unauthenticated artifact fallback 401s. |

# Recent session — 2026-10-29

This note records what was created and shipped on 2026-10-29. Paths below are relative git paths.

## go-email-reader

- Specifications for warm-up sequences 08 through 13 are in `02-spec/21-app/08-ui-and-warm-up-algorithm-improvements/` through `02-spec/21-app/13-ui-and-warm-up-algorithm-improvements/`.
- Plans are in `.ai-memory/plans/pending/08-ui-and-warm-up-algorithm-improvements.md` through `.ai-memory/plans/pending/13-ui-and-warm-up-algorithm-improvements.md`.
- Sequence 08 is the connector and gate map. Sequence 09 is brakes. Sequence 10 is the send lease and cool-down. Sequence 11 is the shadow compare. Sequence 12 is the pace envelope. Sequence 13 is the shared quiet window.
- The live tick now consults `internal/warmup/gatefeed.go`. A peer can tighten the remaining-send cap and cannot raise it. An absent or stale peer does not stop local warm-up. Local quiet hours hold. A quiet skip does not send. A dry run does not spend the cap. The gate order is health, cadence, connector, theme.
- The reader UI gate map reads `GET /api/warmup/gates`.
- Commit `f3864ee` is on `main` and is pushed. The remote uses SSH.
- Sequences 08 through 13 stay pending as catalogs. Only the gate engine is implemented.
- `user.email` is `local@gitmap`. The name is `gitmap automation`.

## gitmap-v28

- Cursor-like IDE setup landed in `cli/cmdide/ide_setup.go`, `cli/cmdide/setup/`, and `cli/cmdui/ui_server_ide_setup.go`.
- The spec is `02-spec/21-app/352-cursor-like-ide-setup-from-gitmap/`.
- Pushed commits include `3229df9b4`, `864012968`, and `04690b952`.
- `cli/cov` is a coverage profile and was not committed.

## repo-cache

- Commit `f474298` stores heatmap databases, including `.heatmap/06-cursor/go-email-reader/heatmap.db`.
- SQLite `-shm` and `-wal` sidecars were not committed.

## Push denied

These local commits are still unpushed because GitHub denied `alimtvnetwork`:

- `alim.karim.profile` (19 commits)
- `kubernetes-training-v1` (19 commits)
- `common-linux-installer` (1 commit)

## Rules learned

- Do not put a personal access token in a git remote URL. Use SSH.
- Do not commit coverage profiles or SQLite sidecar files.

## Last 30 commits in this repo

```text
c7992db feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts (29-Oct-26 06:31 pm)
265676f feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts (29-Oct-26 04:23 pm)
b105df7 feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts (29-Oct-26 03:16 pm)
0312d31 feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts (29-Oct-26 02:53 pm)
f9d9664 feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts
d3a6a46 fix(installer): expand ~/ prefixes and drop partial GUI downloads in install.py
9a7840b fix(release): remove accidental dry-run commit contents, keep v2.4.0 only
67b7b21 Feature: test dry run
3219b7a feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts
bfcd87a feat(sync): sync canonical prompts, skills, gitmap agent standards, and purge deprecated 46 task manager
8bd333e feat(sync): sync canonical prompts, skills, gitmap agent standards, and purge deprecated 46 task manager
f8577b3 feat(sync): sync canonical prompts, skills, gitmap agent standards, and purge deprecated 46 task manager
b38e708 feat(sync): sync canonical prompts, skills, gitmap agent standards, and purge deprecated 46 task manager
1bfa561 docs(plan): mark cross-platform context-menu plan shipped in v2.3.0
f9b814a fix(installer): honor JPG2PDF_CTX_REF registrar override and verify context-menu registration
5a78277 fix(context-menu): restore Combine into PDF on Windows, macOS and Linux (v2.3.0)
07224a6 feat(sync): sync canonical prompts, skills, gitmap agent standards, and purge deprecated 46 task manager
553da0c feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts
2af5d40 feat(sync): sync canonical prompts, skills, gitmap agent standards, and purge deprecated 46 task manager
8fa92f3 feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts
99d417e feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts
6c5df68 feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts
d6a7908 feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts
9bd4f25 feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts
6d1a0ba feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts
997451f feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts
1b8b525 feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts
f2fdd72 feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts
8fba7e5 feat(sync) - sync canonical v6 execute suite, gitmap heatmap telemetry, skills, and prompts
6674d72 Chore: chore - purge deprecated v4 prompts
```

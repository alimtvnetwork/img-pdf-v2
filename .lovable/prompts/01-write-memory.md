# Write Memory

> **Purpose:** After completing work or at the end of a session, the AI must persist everything it learned, did, and left undone — so the next AI session can pick up seamlessly with zero context loss.
>
> **When to run:** At the end of every session, after completing a task batch, or when explicitly asked to "update memory" or "write memory."

## Core Principle
The memory system is the project's brain. If you did something and didn't write it down, it didn't happen. If something is pending and you didn't record it, it will be lost. Write memory as if the next AI has amnesia — because it does.

## Phases

### Phase 1 — Audit Current State
Internally answer: what was done, what is pending, what was learned, what went wrong.

### Phase 2 — Update Memory Files (`.lovable/memory/`)
1. Read `.lovable/memory/index.md` first.
2. Update existing topic files; preserve history (mark done, never delete).
3. Create new topic files for new knowledge — naming: `XX-descriptive-name.md`, lowercase + hyphens.
4. **Update `index.md` in the same operation** when adding/removing files.
5. Update `.lovable/memory/workflow/state.md` with ✅ / 🔄 / ⏳ / 🚫 markers.

### Phase 3 — Update Plans & Suggestions
- `.lovable/plan.md` — single file, `## Active` and `## Completed` sections.
- `.lovable/suggestions.md` — single file, `## Active Suggestions` and `## Implemented Suggestions`.

### Phase 4 — Update Issues
- `.lovable/pending-issues/XX-name.md` — unresolved bugs.
- `.lovable/solved-issues/XX-name.md` — move here when fixed; add `## Solution`, `## Iteration Count`, `## Learning`, `## What NOT to Repeat`.
- `.lovable/strictly-avoid.md` — anti-patterns that must never recur.

### Phase 5 — Consistency Validation
- Every memory file listed in `index.md`.
- Every `✅ Done` plan item has evidence.
- No file appears in both `pending-issues/` and `solved-issues/`.

### Phase 6 — CI/CD Issues
- `.lovable/cicd-issues/XX-issue-name.md` per issue.
- `.lovable/cicd-index.md` summarizes them. No duplicates.

### Phase 7 — Capture Specs Verbatim
If the user gave a sizeable spec or directive, save it verbatim to the file system (e.g. `tools/<name>/spec/SPEC.md` or `.lovable/memory/specs/`).

## File Naming Rules
- Lowercase, hyphen-separated. Numeric prefix `01-`, `02-`.
- Plans/suggestions → ONE file each. Never split.
- Memory → grouped by topic in subfolders.
- Path is `.lovable/memory/` (NEVER `memories/` with trailing s).

## Anti-Corruption Rules
1. Never delete history — mark done, move to completed sections.
2. Never overwrite blindly — read before write.
3. Never leave orphans — every file indexed, every reference resolves.
4. Never split unified files (plan, suggestions).
5. Never mix states — issue is either pending OR solved.
6. Never skip the index update.
7. Never assume the next AI knows anything.

## Final Confirmation
Respond with a session summary: tasks completed/pending, files created, issues opened/resolved, suggestions, files modified, inconsistencies fixed, and the next logical step.

---
name: write-memory
description: Persist everything learned, done, and pending in .ai-memory/ so the next AI session can resume with zero context loss.
---

# Write Memory Skill

Follow the workflow defined in `.ai-memory/prompts/01-write-memory.md`:
1. Audit current state (what was done, what is pending, what was learned, what went wrong).
2. Update `.ai-memory/memory/` and `.ai-memory/memory/01-index.md`.
3. Update `.ai-memory/plans/` and `.ai-memory/plans/01-index.md`.
4. Update `.ai-memory/issues/` and `.ai-memory/strictly-avoid.md`.
5. Verify consistency and confirm session summary.

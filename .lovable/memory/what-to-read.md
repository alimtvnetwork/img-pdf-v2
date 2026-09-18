# What to Read (Authoritative Reading Priority)

Before touching any code or drafting plans in `img-pdf-v2`, follow this strict sequence:

1. **`tools/jpg2pdf/VERSION`** - Active released version number (source of truth).
2. **`spec/00-AI-INSTRUCTIONS.md`** - Primary rules of engagement, reading order, and non-negotiables.
3. **`.lovable/strictly-avoid.md`** - Hard prohibitions (CODE RED) - append-only, never violate.
4. **`.lovable/coding-guidelines/coding-guidelines.md`** - Cross-language coding guidelines, ASCII in PS1, and defensive patterns.
5. **`spec/04-versioning.md`** - Version bump synchronization across all 7 source files.
6. **`spec/02-powershell.md`** - Windows PowerShell 5.1 compatibility, guarded startup, and ASCII-only rules.
7. **`spec/03-bash-installer.md`** - Bash installer spec, POSIX compatibility, and Python source fallback.
8. **`spec/01-cicd.md`** - CI/CD release workflow triggers, build matrix, and release gates.
9. **`tools/jpg2pdf/spec/SPEC.md`** - Core CLI architecture, input classification, and Windows context menu.
10. **`tools/jpg2pdf/spec/GUI.md`** - Desktop GUI specifications, layout, options, and output modes.
11. **`.lovable/memory/00-index.md`** - Master institutional knowledge index.
12. **`.lovable/plans/index.md`** - Master roadmap and pending plans.
13. **`.lovable/cicd-issues/`** - All historical and active CI/CD failure RCAs.
14. **`.lovable/issues/`** - Known bugs, regressions, and environment caveats.
15. **`readme.md`** (root) - User-facing architecture, installation commands, and examples.

# Canonical Lovable Folder Structure

```text
img-pdf-v2/
├── .lovable/                            # Lovable memory and institutional knowledge
│   ├── ai-fix-scripts/                 # Automated fix scripts & runners
│   ├── ambiguous-questions/            # Open and resolved requirements
│   │   ├── 01-new-ambiguity/           # Currently blocking questions
│   │   └── 02-ambiguity-resolved/      # Answered binding decisions
│   ├── cicd-issues/                    # Historical and active CI/CD failure RCAs
│   ├── coding-guidelines/              # Coding guidelines single source of truth
│   ├── issues/                         # General bugs, regressions, and environment caveats
│   ├── memory/                         # Institutional topics, architectural decisions
│   │   ├── decisions/                  # Key technical and UX decisions
│   │   ├── learned/                    # Session learnings and onboardings
│   │   └── workflow/                   # Active workflow state
│   ├── plans/                          # Execution roadmaps
│   │   ├── completed/                  # Archived shipped milestones
│   │   ├── pending/                    # Active execution plans
│   │   └── subtasks/                   # Granular 5-8 step execution batches
│   ├── lovable-folder-structure.md     # This file
│   ├── strictly-avoid.md               # Hard prohibitions (CODE RED)
│   ├── suggestions.md                  # Active and implemented product suggestions
│   ├── user-preferences.md             # User communication and workflow preferences
│   └── what-to-read.md                 # Authoritative reading order
├── spec/                               # Product & platform specifications
│   ├── 00-AI-INSTRUCTIONS.md           # Engagement rules & non-negotiables
│   ├── 01-cicd.md                      # GitHub Actions workflow spec
│   ├── 02-coding-guidelines/           # Detailed coding standard specs
│   ├── 02-powershell.md                # PowerShell scripts & Windows installer spec
│   ├── 03-bash-installer.md            # Bash installer spec
│   ├── 03-error-manage/                # Error handling philosophy & retrospectives
│   ├── 04-versioning.md                # Version bump synchronization rules
│   ├── 17-consolidated-guidelines/     # Consolidated policy specs
│   └── README.md                       # Spec directory index
├── tools/jpg2pdf/                       # Main Python product codebase
│   ├── docs/                           # Documentation media and screenshots
│   ├── scripts/                        # Context menu registrar and shims
│   ├── spec/                           # Feature specs (CLI SPEC.md, GUI.md)
│   ├── src/                            # Python source code
│   │   ├── jpg2pdf_app/                # Modular application package (core, gui, settings)
│   │   ├── jpg2pdf.py                  # CLI entry point
│   │   └── jpg2pdf_gui_entry.py        # GUI launcher entry point
│   ├── tests/                          # Test suite (smoke and unit tests)
│   ├── README.md                       # Product documentation
│   ├── requirements.txt                # Python dependencies
│   └── VERSION                         # Pinned SemVer string
├── install.ps1                          # Windows one-liner installer
├── install.sh                           # macOS/Linux one-liner installer
├── run.ps1                              # Local development runner & packager
├── uninstall.ps1                        # Uninstaller script
├── CHANGELOG.md                         # Changelog (Keep-a-Changelog)
└── readme.md                            # Repository root documentation (strictly lowercase)
```

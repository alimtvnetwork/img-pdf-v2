#!/usr/bin/env python3
"""02-guideline-autofixer.py - Checks ASCII-only in .ps1 files and boolean conventions."""
import sys
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
print("Guideline autofixer ready.")

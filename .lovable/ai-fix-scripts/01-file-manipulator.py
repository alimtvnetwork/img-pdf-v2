#!/usr/bin/env python3
"""01-file-manipulator.py - Safe file manipulator."""
import sys
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
print("File manipulator ready.")

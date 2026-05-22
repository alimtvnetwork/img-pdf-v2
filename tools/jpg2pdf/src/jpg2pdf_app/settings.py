"""Persisted GUI settings + recent files for jpg2pdf.

Step 17 of the GUI roadmap. Stores user-facing option defaults and a
de-duplicated recent-inputs list as JSON at a platform-appropriate
location.

Locations:
    Windows : %APPDATA%\\jpg2pdf\\settings.json
    macOS   : ~/Library/Application Support/jpg2pdf/settings.json
    Linux   : $XDG_CONFIG_HOME/jpg2pdf/settings.json (default ~/.config/...)

The module is intentionally tolerant: any read/write failure degrades to
in-memory defaults instead of breaking the GUI.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

MAX_RECENT = 12

# Option keys persisted from the GUI's tk variables. Keep this list stable.
PRESET_KEYS = (
    "mode", "sort", "size", "orient", "fit", "stack",
    "pencil", "strength", "output",
)

DEFAULTS: dict[str, Any] = {
    "mode": "pdf",
    "sort": "auto",
    "size": "a4",
    "orient": "portrait",
    "fit": "contain",
    "stack": "vertical",
    "pencil": False,
    "strength": "subtle",  # project default, do not change
    "output": "",
    "recent": [],
}


def config_dir() -> Path:
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData/Roaming")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "jpg2pdf"


def config_path() -> Path:
    return config_dir() / "settings.json"


def load() -> dict[str, Any]:
    """Return persisted settings merged on top of DEFAULTS."""
    data = dict(DEFAULTS)
    try:
        raw = config_path().read_text(encoding="utf-8")
        loaded = json.loads(raw)
        if isinstance(loaded, dict):
            for k, v in loaded.items():
                if k in DEFAULTS:
                    data[k] = v
            # Sanitize recent list.
            r = loaded.get("recent")
            if isinstance(r, list):
                data["recent"] = [str(p) for p in r if isinstance(p, str)][:MAX_RECENT]
    except FileNotFoundError:
        pass
    except Exception:
        # Corrupt file or unreadable: fall back to defaults silently.
        pass
    return data


def save(values: dict[str, Any]) -> bool:
    """Persist a settings dict. Returns True on success."""
    try:
        d = config_dir()
        d.mkdir(parents=True, exist_ok=True)
        merged = {k: values.get(k, DEFAULTS[k]) for k in DEFAULTS}
        # Trim recent and drop empties.
        recent = [p for p in (merged.get("recent") or []) if p]
        merged["recent"] = recent[:MAX_RECENT]
        config_path().write_text(
            json.dumps(merged, indent=2, ensure_ascii=False),
            encoding="utf-8")
        return True
    except Exception:
        return False


def push_recent(recent: list[str], new_items) -> list[str]:
    """Return a new recent list with `new_items` prepended (deduped, capped)."""
    out: list[str] = []
    seen: set[str] = set()
    for p in list(new_items) + list(recent or []):
        if not p:
            continue
        s = str(p)
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= MAX_RECENT:
            break
    return out

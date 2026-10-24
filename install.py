#!/usr/bin/env python3
"""Cross-platform one-liner installer for jpg2pdf (stdlib only).

One command, any OS with Python 3 (Windows, macOS, Linux):

    python3 -c "import urllib.request; exec(urllib.request.urlopen(
        'https://raw.githubusercontent.com/alimtvnetwork/img-pdf-v2/main/install.py'
        ).read().decode())"

Native one-liners are still the primary route (they need no Python):
  Windows PowerShell:  irm https://raw.githubusercontent.com/alimtvnetwork/img-pdf-v2/main/install.ps1 | iex
  macOS / Linux:       curl -fsSL https://raw.githubusercontent.com/alimtvnetwork/img-pdf-v2/main/install.sh | bash

What this script does:
  1. Detects OS + CPU arch and maps it to a GitHub Release asset name.
  2. Resolves the latest release (or JPG2PDF_VERSION, e.g. v2.4.0).
  3. Downloads the CLI binary and, when available, the GUI binary.
  4. Installs into JPG2PDF_PREFIX (default ~/.local/bin on Unix,
     %USERPROFILE%\\Tools\\bin on Windows) and makes them executable.
  5. Runs `jpg2pdf --install-context-menu` so the right-click
     "Combine into PDF" and "Review & merge in visualizer..." entries
     are registered by the installed binary itself.

Flags:  --dry-run   print the install plan without downloading anything
        --version X install release X instead of the latest
        --prefix DIR install into DIR instead of the default
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import stat
import sys
import urllib.request
from pathlib import Path

REPO = os.environ.get("JPG2PDF_REPO", "alimtvnetwork/img-pdf-v2")
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"


def asset_names(os_name: str, arch: str) -> tuple:
    """Map (os, arch) to (cli_asset, gui_asset). Raises ValueError when
    the platform has no release binary (the caller then falls back to
    the native installers, which carry a Python source fallback)."""
    os_name = os_name.lower()
    arch = arch.lower()
    if os_name.startswith("win"):
        return ("jpg2pdf-windows-x64.exe", "jpg2pdf-gui-windows-x64.exe")
    if os_name == "darwin":
        return ("jpg2pdf-macos-arm64", "jpg2pdf-gui-macos-arm64")
    if os_name == "linux":
        if arch in ("arm64", "aarch64"):
            return ("jpg2pdf-linux-arm64", "jpg2pdf-gui-linux-arm64")
        return ("jpg2pdf-linux-x64", "jpg2pdf-gui-linux-x64")
    raise ValueError(f"unsupported OS for install.py: {os_name}")


def default_prefix() -> Path:
    if sys.platform.startswith("win"):
        return Path.home() / "Tools" / "bin"
    return Path(os.environ.get("JPG2PDF_PREFIX", "")) or (Path.home() / ".local" / "bin")


def resolve_tag(version: str | None) -> str:
    if version:
        return version if version.startswith("v") else "v" + version
    req = urllib.request.Request(API_LATEST, headers={"User-Agent": "jpg2pdf-installer"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))["tag_name"]


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "jpg2pdf-installer"})
    with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as out:
        shutil.copyfileobj(resp, out)


def main(argv: list | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dry_run = "--dry-run" in args
    version = os.environ.get("JPG2PDF_VERSION", "")
    prefix = Path(os.environ.get("JPG2PDF_PREFIX", "")) or None
    i = 0
    while i < len(args):
        if args[i] == "--version" and i + 1 < len(args):
            version = args[i + 1]
            i += 2
        elif args[i] == "--prefix" and i + 1 < len(args):
            prefix = Path(args[i + 1])
            i += 2
        else:
            i += 1
    prefix = prefix or default_prefix()
    try:
        cli_asset, gui_asset = asset_names(platform.system(), platform.machine())
    except ValueError as exc:
        print(f"[jpg2pdf] {exc}", file=sys.stderr)
        print("[jpg2pdf] Use install.ps1 on Windows or install.sh on macOS/Linux.",
              file=sys.stderr)
        return 1
    tag = resolve_tag(version) if not dry_run else (version or "latest")
    base = f"https://github.com/{REPO}/releases/download/{tag}"
    cli_dest = prefix / ("jpg2pdf.exe" if cli_asset.endswith(".exe") else "jpg2pdf")
    gui_dest = prefix / ("jpg2pdf-gui.exe" if gui_asset.endswith(".exe") else "jpg2pdf-gui")
    print(f"[jpg2pdf] Installing {tag} into {prefix}")
    print(f"[jpg2pdf]   CLI: {cli_asset} -> {cli_dest}")
    print(f"[jpg2pdf]   GUI: {gui_asset} -> {gui_dest}")
    if dry_run:
        return 0
    prefix.mkdir(parents=True, exist_ok=True)
    download(f"{base}/{cli_asset}", cli_dest)
    try:
        download(f"{base}/{gui_asset}", gui_dest)
    except Exception as exc:  # GUI is optional; CLI + menu still work
        print(f"[jpg2pdf] GUI binary unavailable ({exc}); continuing with CLI only.")
    for dest in (cli_dest, gui_dest):
        if dest.is_file():
            dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    import subprocess
    proc = subprocess.run([str(cli_dest), "--install-context-menu"],
                          capture_output=True, text=True)
    if proc.returncode == 0:
        print("[jpg2pdf] Right-click menu installed (Combine into PDF + visualizer).")
    else:
        print("[jpg2pdf] Context-menu registration needs a re-run:")
        print(f"[jpg2pdf]   {cli_dest} --install-context-menu")
    print(f"[jpg2pdf] Done. Run: {cli_dest} --version")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Cross-platform installer tests (v2.4.0, install.py).

The universal one-liner is `python3 -c "import urllib.request; exec(...install.py)"`
-- it must map every supported OS/arch to the exact GitHub Release asset
name, and --dry-run must print the plan without touching the network
or the disk.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_PY = REPO_ROOT / "install.py"


def _mod():
    spec = importlib.util.spec_from_file_location("jpg2pdf_install", INSTALL_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_asset_names_cover_all_release_platforms():
    mod = _mod()
    assert mod.asset_names("Windows", "AMD64") == (
        "jpg2pdf-windows-x64.exe", "jpg2pdf-gui-windows-x64.exe")
    assert mod.asset_names("Darwin", "arm64") == (
        "jpg2pdf-macos-arm64", "jpg2pdf-gui-macos-arm64")
    assert mod.asset_names("Linux", "x86_64") == (
        "jpg2pdf-linux-x64", "jpg2pdf-gui-linux-x64")
    assert mod.asset_names("Linux", "aarch64") == (
        "jpg2pdf-linux-arm64", "jpg2pdf-gui-linux-arm64")
    with pytest.raises(ValueError):
        mod.asset_names("FreeBSD", "x86_64")


def test_dry_run_prints_plan_without_downloading(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(INSTALL_PY), "--dry-run",
         "--prefix", str(tmp_path / "bin")],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    assert "Installing" in proc.stdout
    assert "jpg2pdf-linux-x64" in proc.stdout
    assert not (tmp_path / "bin").exists()

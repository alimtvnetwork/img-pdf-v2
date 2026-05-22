"""End-to-end smoke tests for jpg2pdf (Step 18 of the GUI roadmap).

Covers:
  * GUI settings persistence + push_recent dedupe/cap.
  * CLI --version reports the same string as VERSION/__version__.
  * CLI end-to-end: one PNG -> PDF, asserting the file is a valid PDF.
  * CLI stacked image output (--output-mode image, vertical stack of 2 PNGs).
  * CLI HTML input is accepted and produces a PDF.

Run with:
    cd tools/jpg2pdf && python -m pytest -q tests
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG_SRC   = REPO_ROOT / "tools" / "jpg2pdf" / "src"
SCRIPT    = PKG_SRC / "jpg2pdf.py"

# Make jpg2pdf_app importable.
sys.path.insert(0, str(PKG_SRC))


def _run_cli(args, cwd):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return proc


# --------------------------------------------------------------------- settings

def test_settings_roundtrip_and_push_recent(tmp_path, monkeypatch):
    # Redirect settings dir into a tmp path.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    # On macOS the module hardcodes ~/Library/...; override HOME so it lands in tmp.
    monkeypatch.setenv("HOME", str(tmp_path))

    # Re-import the module so it re-reads env on import (config_dir is dynamic).
    import importlib
    import jpg2pdf_app.settings as s
    importlib.reload(s)

    data = s.load()
    assert data["strength"] == "subtle", "Pencil default must remain 'subtle'."
    assert data["recent"] == []

    data["mode"] = "image"
    data["recent"] = s.push_recent([], ["/a", "/b", "/a", "/c"])  # dedupe
    assert data["recent"] == ["/a", "/b", "/c"]
    assert s.save(data) is True

    reloaded = s.load()
    assert reloaded["mode"] == "image"
    assert reloaded["recent"] == ["/a", "/b", "/c"]

    # Cap at MAX_RECENT.
    many = [f"/x{i}" for i in range(30)]
    capped = s.push_recent([], many)
    assert len(capped) == s.MAX_RECENT


def test_push_recent_prepends_new():
    import jpg2pdf_app.settings as s
    out = s.push_recent(["/old1", "/old2"], ["/new1", "/old1"])
    assert out[0] == "/new1"
    assert "/old1" in out and "/old2" in out
    assert out.count("/old1") == 1  # deduped


# --------------------------------------------------------------------- CLI smoke

def test_cli_version_matches_files(tmp_path):
    file_ver = (REPO_ROOT / "tools/jpg2pdf/VERSION").read_text().strip()
    proc = _run_cli(["--version"], cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert file_ver in proc.stdout, f"VERSION={file_ver!r} stdout={proc.stdout!r}"


def _make_png(path: Path, size=(64, 48), color=(220, 80, 80)):
    from PIL import Image
    Image.new("RGB", size, color).save(path, "PNG")


def test_cli_png_to_pdf(tmp_path):
    img = tmp_path / "a.png"
    out = tmp_path / "out.pdf"
    _make_png(img)
    proc = _run_cli(
        ["--files", str(img), "--size", "a4", "--out", str(out)],
        cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert out.exists() and out.stat().st_size > 200
    assert out.read_bytes()[:4] == b"%PDF", "Output is not a valid PDF."


def test_cli_stacked_image(tmp_path):
    a = tmp_path / "a.png"; b = tmp_path / "b.png"
    out = tmp_path / "stack.png"
    _make_png(a, color=(50, 200, 50))
    _make_png(b, color=(50, 50, 200))
    proc = _run_cli(
        ["--files", str(a), str(b),
         "--output-mode", "image", "--stack", "vertical",
         "--out", str(out)],
        cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert out.exists() and out.stat().st_size > 50
    # PNG magic bytes.
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_cli_html_to_pdf(tmp_path):
    html = tmp_path / "doc.html"
    html.write_text(
        "<html><body><h1>Hello</h1><p>jpg2pdf html smoke.</p></body></html>",
        encoding="utf-8")
    out = tmp_path / "html.pdf"
    proc = _run_cli(
        ["--files", str(html), "--size", "a4", "--out", str(out)],
        cwd=tmp_path)
    if proc.returncode != 0 and "xhtml2pdf" in (proc.stderr + proc.stdout).lower():
        pytest.skip("xhtml2pdf not available in this environment.")
    assert proc.returncode == 0, proc.stderr
    assert out.exists() and out.read_bytes()[:4] == b"%PDF"

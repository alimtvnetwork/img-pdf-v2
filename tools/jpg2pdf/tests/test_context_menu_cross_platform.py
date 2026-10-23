"""Cross-platform context-menu tests (cicd issue 08).

The pre-v2.3.0 suite had exactly one context-menu test and it was
skipped on every non-Windows machine -- while CI runs on Ubuntu, so
the release gate never executed a single context-menu assertion and
the "Combine into PDF" entry could vanish undetected.

These tests exercise the pure builders in jpg2pdf.py for Windows,
macOS and Linux on ANY host, plus install/uninstall round trips for
the file-based platforms against a temporary HOME, plus static
checks on the PowerShell registrar and the install.sh KDE entry
(the Exec line that used to pass files as bare positionals).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG_SRC = REPO_ROOT / "tools" / "jpg2pdf" / "src"
SCRIPT = PKG_SRC / "jpg2pdf.py"
REGISTER_PS1 = (REPO_ROOT / "tools" / "jpg2pdf" / "scripts"
                / "register-context-menu.ps1")
UNREGISTER_PS1 = (REPO_ROOT / "tools" / "jpg2pdf" / "scripts"
                  / "unregister-context-menu.ps1")
INSTALL_SH = REPO_ROOT / "install.sh"
INSTALL_PS1 = REPO_ROOT / "install.ps1"

sys.path.insert(0, str(PKG_SRC))


def _engine():
    spec = importlib.util.spec_from_file_location("jpg2pdf_ctx_engine",
                                                  SCRIPT)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    return engine


CMD = "/opt/jpg2pdf/jpg2pdf"


# ---------------------------------------------------------------- windows

def test_windows_plan_has_flat_verb_everywhere():
    eng = _engine()
    plan = eng.build_windows_context_menu(
        r"C:\Users\test\Tools\bin\jpg2pdf.exe",
        r"C:\Users\test\Tools\bin")
    entries = plan["entries"]
    flat_keys = {k for k, _n, _v in entries if k.endswith("\\Jpg2PdfMerge")}
    # * + one SystemFileAssociations root per extension + 2 folder roots.
    assert len(flat_keys) == 1 + len(eng.CTX_EXTS) + 2
    commands = {k: v for k, n, v in entries
                if k.endswith("\\Jpg2PdfMerge\\command")}
    assert len(commands) == len(flat_keys)
    for key, value in commands.items():
        assert "jpg2pdf" in value
        if "SystemFileAssociations" in key or key.startswith(
                r"Software\Classes\*"):
            assert "jpg2pdf-selected-launcher.vbs" in value
            assert '"%1"' in value
    # Multi-select must be enabled or Explorer passes only one file.
    assert any(n == "MultiSelectModel" and v == "Player"
               for _k, n, v in entries)
    # The wildcard root must be filtered to supported extensions so the
    # verb does not appear for unrelated files, and pdf/docx are in it.
    applies = [v for _k, n, v in entries if n == "AppliesTo"]
    assert applies and ".pdf" in applies[0] and ".docx" in applies[0]


def test_windows_plan_writes_runner_and_launcher():
    eng = _engine()
    plan = eng.build_windows_context_menu(
        r"C:\Tools\bin\jpg2pdf.exe", r"C:\Tools\bin")
    files = plan["files"]
    runner = [c for p, c in files.items() if p.endswith(".cmd")][0]
    launcher = [c for p, c in files.items() if p.endswith(".vbs")][0]
    assert "--files-from" in runner
    assert "queue" in runner.lower()
    assert r"C:\Tools\bin\jpg2pdf.exe" in runner
    assert "WScript.Shell" in launcher
    assert "jpg2pdf-selected-runner.cmd" in launcher


def test_windows_install_is_host_gated(tmp_path, monkeypatch):
    """On a non-Windows host install returns the plan without writing
    Windows-named files onto the local disk."""
    eng = _engine()
    before = set(tmp_path.iterdir())
    written = eng.install_context_menu(
        platform="windows", command=r"C:\Tools\bin\jpg2pdf.exe")
    assert any("Jpg2PdfMerge" in w for w in written)
    assert set(tmp_path.iterdir()) == before or sys.platform == "win32"


# ------------------------------------------------------------------ macos

def test_macos_quick_actions_cover_all_verbs(tmp_path):
    eng = _engine()
    files = eng.build_macos_context_menu(tmp_path, CMD)
    assert len(files) == len(eng.CTX_VERBS) * 2  # Info.plist + wflow each
    wflows = [c for p, c in files.items() if p.endswith("document.wflow")]
    assert wflows and all("--files-from" in c for c in wflows)
    assert all(CMD in c for c in wflows)
    infos = [c for p, c in files.items() if p.endswith("Info.plist")]
    assert all("com.apple.finder" in c for c in infos)
    assert all("com.adobe.pdf" in c for c in infos)


def test_macos_install_uninstall_roundtrip(tmp_path):
    eng = _engine()
    written = eng.install_context_menu(platform="macos", home=tmp_path,
                                       command=CMD)
    assert written
    workflows = list((tmp_path / "Library" / "Services").glob("*.workflow"))
    assert len(workflows) == len(eng.CTX_VERBS)
    eng.uninstall_context_menu(platform="macos", home=tmp_path, command=CMD)
    assert not list((tmp_path / "Library" / "Services").glob("*.workflow"))


# ------------------------------------------------------------------ linux

def test_linux_builders_cover_file_managers(tmp_path):
    eng = _engine()
    files = eng.build_linux_context_menu(tmp_path, CMD)
    paths = list(files)
    assert any("nautilus" in p and "scripts" in p for p in paths)
    assert any("nemo" in p and p.endswith(".nemo_action") for p in paths)
    kde = [spec["content"] for p, spec in files.items()
           if p.endswith("jpg2pdf.desktop")]
    assert kde, "KDE Dolphin servicemenu missing"
    # Regression test for the Dolphin bug: files must go through
    # --files, never as bare positional arguments.
    assert "--files %F" in kde[0]
    assert "--size a4 %F" not in kde[0]
    for spec in files.values():
        assert "--size a4 %F" not in spec["content"]
    nemo = [spec["content"] for p, spec in files.items()
            if p.endswith(".nemo_action")]
    assert nemo and all("--files %F" in c for c in nemo)
    actions = eng.thunar_actions(CMD)
    assert len(actions) == len(eng.CTX_VERBS)
    assert all("--files %F" in a["command"] for a in actions)
    assert all(".docx" in a["patterns"] for a in actions)


def test_linux_install_uninstall_roundtrip(tmp_path):
    eng = _engine()
    written = eng.install_context_menu(platform="linux", home=tmp_path,
                                       command=CMD)
    assert written
    uca = tmp_path / ".config" / "Thunar" / "uca.xml"
    assert uca.is_file() and "Combine into PDF (A4)" in uca.read_text()
    naut = list((tmp_path / ".local" / "share" / "nautilus"
                 / "scripts").iterdir())
    assert len(naut) == len(eng.CTX_VERBS)
    assert all((p.stat().st_mode & 0o111) for p in naut)  # executable
    eng.uninstall_context_menu(platform="linux", home=tmp_path, command=CMD)
    assert not list((tmp_path / ".local" / "share" / "nautilus"
                     / "scripts").glob("jpg2pdf*"))
    assert "Combine into PDF" not in uca.read_text()


# ------------------------------------------------------- static file checks

def test_powershell_registrar_has_flat_verb():
    text = REGISTER_PS1.read_text(encoding="utf-8", errors="replace")
    assert "Register-FlatVerb" in text
    assert "Jpg2PdfMerge" in text
    assert "MultiSelectModel" in text
    # Default values must be real (default) values, not a property
    # literally named "(default)" (cicd issue 06).
    assert "Set-DefaultValue" in text or "Set-Item -Value" in text \
        or "Set-Item -LiteralPath" in text


def test_powershell_unregister_removes_flat_verb():
    text = UNREGISTER_PS1.read_text(encoding="utf-8", errors="replace")
    assert "Jpg2PdfMerge" in text
    assert "Jpg2PdfMenu" in text


def test_installers_prefer_binary_registrar():
    sh = INSTALL_SH.read_text(encoding="utf-8", errors="replace")
    assert "--install-context-menu" in sh
    # The inline KDE fallback must use --files too.
    assert "--size a4 --files %F" in sh
    assert "--size a4 %F" not in sh
    ps1 = INSTALL_PS1.read_text(encoding="utf-8", errors="replace")
    assert "--install-context-menu" in ps1

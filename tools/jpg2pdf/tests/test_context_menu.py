"""Integration tests for Windows Explorer context menu registration and cleanup."""

import os
import subprocess
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTER_SCRIPT = REPO_ROOT / "tools" / "jpg2pdf" / "scripts" / "register-context-menu.ps1"
UNREGISTER_SCRIPT = REPO_ROOT / "tools" / "jpg2pdf" / "scripts" / "unregister-context-menu.ps1"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Explorer context menu tests require Windows")
def test_context_menu_registration_and_unregistration(tmp_path):
    dummy_exe = tmp_path / "jpg2pdf.exe"
    dummy_exe.write_text("@echo off\necho jpg2pdf dummy\n", encoding="ascii")

    # 1. Run register script
    reg_cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(REGISTER_SCRIPT),
        "-ExePath",
        str(dummy_exe),
    ]
    res_reg = subprocess.run(reg_cmd, capture_output=True, text=True, check=False)
    assert res_reg.returncode == 0, f"register-context-menu.ps1 failed: {res_reg.stdout} {res_reg.stderr}"

    # 2. Check keys in registry via PowerShell Test-Path
    check_ps = (
        "$dirKey = Test-Path -LiteralPath 'HKCU:\\Software\\Classes\\Directory\\shell\\Jpg2PdfMenu'; "
        "$bgKey = Test-Path -LiteralPath 'HKCU:\\Software\\Classes\\Directory\\Background\\shell\\Jpg2PdfMenu'; "
        "$fileKey = Test-Path -LiteralPath 'HKCU:\\Software\\Classes\\*\\shell\\Jpg2PdfMenu'; "
        "$applies = (Get-ItemProperty -LiteralPath 'HKCU:\\Software\\Classes\\*\\shell\\Jpg2PdfMenu' -Name 'AppliesTo' -ErrorAction SilentlyContinue).AppliesTo; "
        "if ($dirKey -and $bgKey -and $fileKey -and ($applies -like '*System.FileExtension:=.jpg*')) { exit 0 } else { exit 1 }"
    )
    res_check = subprocess.run(["powershell.exe", "-NoProfile", "-Command", check_ps], capture_output=True, text=True, check=False)
    assert res_check.returncode == 0, "Registry keys or AppliesTo filter missing after registration"

    # 2b. Check the click chain end-to-end: flat verb + leaf command values + launcher files.
    # Parent keys alone do not prove a click does anything (see cicd issue 06).
    check_chain_ps = (
        "$flat = (Get-Item -LiteralPath 'HKCU:\\Software\\Classes\\*\\shell\\Jpg2PdfMerge\\command' -ErrorAction SilentlyContinue).GetValue(''); "
        "$folderLeaf = (Get-Item -LiteralPath 'HKCU:\\Software\\Classes\\Jpg2Pdf.FolderMenu.PDF\\shell\\01_a4\\command' -ErrorAction SilentlyContinue).GetValue(''); "
        "$filesLeaf = (Get-Item -LiteralPath 'HKCU:\\Software\\Classes\\Jpg2Pdf.FilesMenu.PDF\\shell\\01_a4\\command' -ErrorAction SilentlyContinue).GetValue(''); "
        "if ($flat -and ($folderLeaf -like '*jpg2pdf*') -and ($filesLeaf -like '*jpg2pdf-selected-launcher.vbs*')) { exit 0 } else { exit 1 }"
    )
    res_chain = subprocess.run(["powershell.exe", "-NoProfile", "-Command", check_chain_ps], capture_output=True, text=True, check=False)
    assert res_chain.returncode == 0, "Context-menu click chain incomplete: flat verb or leaf command values missing"
    assert (tmp_path / "jpg2pdf-selected-launcher.vbs").exists(), "Selected-files launcher VBS was not written"
    assert (tmp_path / "jpg2pdf-selected-runner.cmd").exists(), "Selected-files runner CMD was not written"

    # 3. Run unregister script
    unreg_cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(UNREGISTER_SCRIPT),
    ]
    res_unreg = subprocess.run(unreg_cmd, capture_output=True, text=True, check=False)
    assert res_unreg.returncode == 0, f"unregister-context-menu.ps1 failed: {res_unreg.stdout} {res_unreg.stderr}"

    # 4. Check keys removed
    check_unreg_ps = (
        "$fileKey = Test-Path -LiteralPath 'HKCU:\\Software\\Classes\\*\\shell\\Jpg2PdfMenu'; "
        "$dirKey = Test-Path -LiteralPath 'HKCU:\\Software\\Classes\\Directory\\shell\\Jpg2PdfMenu'; "
        "if ($fileKey -or $dirKey) { exit 1 } else { exit 0 }"
    )
    res_check_unreg = subprocess.run(["powershell.exe", "-NoProfile", "-Command", check_unreg_ps], capture_output=True, text=True, check=False)
    assert res_check_unreg.returncode == 0, "Registry keys still present after unregister"


def test_installer_honors_ctx_ref_override_and_verifies_registration():
    """Source contract (runs on any platform): the installer must let testers
    override the registrar ref (cicd issue 05) and must verify the menu
    registration afterwards instead of reporting blind success."""
    install_ps1 = (REPO_ROOT / "install.ps1").read_text(encoding="utf-8", errors="replace")
    assert "JPG2PDF_CTX_REF" in install_ps1
    assert "Test-ContextMenuRegistration" in install_ps1
    assert "Jpg2PdfMerge" in install_ps1

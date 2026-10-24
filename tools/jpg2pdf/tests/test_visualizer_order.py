"""Visualizer + selection-order tests (v2.4.0).

Proves the exact user scenario: select several files (PDF, image,
PDF, Word) in an order, open the visualizer, fix the order / page
size, and merge -- the output PDF must follow the *corrected* order,
not filename order, not folder order.

Headless-safe: the pure reorder / page-size helpers and the CLI are
tested directly. The Tk GUI itself cannot open a display in CI, so
its move handlers are guarded by a source check (a manual reorder
must force --sort selection, otherwise a persisted name-sort would
silently undo the reorder at Convert time -- the v2.3.0 trap).

Run with:
    cd tools/jpg2pdf && python -m pytest -q tests
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG_SRC = REPO_ROOT / "tools" / "jpg2pdf" / "src"
SCRIPT = PKG_SRC / "jpg2pdf.py"
GUI_PY = PKG_SRC / "jpg2pdf_app" / "gui.py"
REGISTER_PS1 = (REPO_ROOT / "tools" / "jpg2pdf" / "scripts"
                / "register-context-menu.ps1")
UNREGISTER_PS1 = (REPO_ROOT / "tools" / "jpg2pdf" / "scripts"
                  / "unregister-context-menu.ps1")

sys.path.insert(0, str(PKG_SRC))


def _engine():
    spec = importlib.util.spec_from_file_location("jpg2pdf_vis_engine",
                                                  SCRIPT)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    return engine


def _run_cli(args, cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8")


def _make_png(path: Path, color=(200, 60, 60)):
    from PIL import Image
    Image.new("RGB", (96, 64), color).save(path, "PNG")


def _make_text_pdf(path: Path, lines):
    """One text page per line, via the engine's own stdlib writer."""
    eng = _engine()
    assert eng.text_to_pdf(lines, path) is not None


def _page_texts(pdf: Path):
    from pypdf import PdfReader
    reader = PdfReader(str(pdf))
    return [(page.extract_text() or "").strip() for page in reader.pages]


def _page_sizes(pdf: Path):
    from pypdf import PdfReader
    reader = PdfReader(str(pdf))
    return [(float(p.mediabox.width), float(p.mediabox.height))
            for p in reader.pages]


# ------------------------------------------------------------------ helpers

def test_resolve_page_size_portrait_and_landscape():
    eng = _engine()
    assert eng.resolve_page_size("a4", "portrait") == (595.28, 841.89)
    assert eng.resolve_page_size("a4", "landscape") == (841.89, 595.28)
    assert eng.resolve_page_size("letter", "landscape") == (792.0, 612.0)
    with pytest.raises(ValueError):
        eng.resolve_page_size("a3", "portrait")
    with pytest.raises(ValueError):
        eng.resolve_page_size("a4", "diagonal")


def test_move_item_up_down_top_bottom():
    eng = _engine()
    items = ["a.pdf", "b.png", "c.pdf", "d.docx"]
    assert eng.move_item(items, 2, -1) == ["a.pdf", "c.pdf", "b.png", "d.docx"]
    assert eng.move_item(items, 1, 1) == ["a.pdf", "c.pdf", "b.png", "d.docx"]
    assert eng.move_item(items, 0, -1) == items  # already first: no-op
    assert eng.move_item(items, 3, 1) == items  # already last: no-op
    assert eng.move_item(items, 99, -1) == items
    assert eng.move_item_to(items, 3, 0) == ["d.docx", "a.pdf", "b.png", "c.pdf"]
    assert eng.move_item_to(items, 0, 3) == ["b.png", "c.pdf", "d.docx", "a.pdf"]
    assert items == ["a.pdf", "b.png", "c.pdf", "d.docx"]  # inputs untouched


def test_collect_from_list_preserves_selection_order():
    eng = _engine()
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for name in ("z.pdf", "a.png", "m.pdf"):
            if name.endswith(".pdf"):
                _make_text_pdf(td / name, ["page " + name])
            else:
                _make_png(td / name)
        got = eng.collect_from_list(
            [str(td / "m.pdf"), str(td / "a.png"), str(td / "z.pdf")])
        assert [p.name for p in got] == ["m.pdf", "a.png", "z.pdf"]


# ------------------------------------------------------- CLI end-to-end order

def test_cli_merges_pdf_image_pdf_in_selection_order_not_name_order(tmp_path):
    """Selection order beats filename order (the --sort selection default).

    Inputs are deliberately named so name-sort would give a different
    sequence: z-first.pdf, a-image.png, m-second.pdf. The merged PDF's
    text pages must read first-page, second-page in selection order,
    with the image page between them.
    """
    first = tmp_path / "z-first.pdf"
    second = tmp_path / "m-second.pdf"
    image = tmp_path / "a-image.png"
    _make_text_pdf(first, ["FIRST-PDF-PAGE"])
    _make_text_pdf(second, ["SECOND-PDF-PAGE"])
    _make_png(image)
    out = tmp_path / "merged.pdf"
    proc = _run_cli(
        ["--files", str(first), str(image), str(second),
         "--out", str(out)], cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    texts = _page_texts(out)
    assert len(texts) == 3
    assert "FIRST-PDF-PAGE" in texts[0]
    assert "SECOND-PDF-PAGE" in texts[2]
    # The image page sits between them and carries no extracted text.
    assert texts[1] == ""


def test_cli_reordered_selection_merges_in_corrected_order(tmp_path):
    """The visualizer's job, replayed headlessly: reorder, then merge.

    The user picked [second, image, first] and corrected it to
    [first, image, second] with Up/Down before Convert. The CLI run
    with the corrected list must produce the corrected PDF.
    """
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    image = tmp_path / "img.png"
    _make_text_pdf(first, ["CORRECT-FIRST"])
    _make_text_pdf(second, ["CORRECT-SECOND"])
    _make_png(image)
    eng = _engine()
    picked = [str(second), str(image), str(first)]
    # Two Up moves, as a user would do: first to the top, then the
    # displaced second file down past the image.
    step1 = eng.move_item_to(picked, 2, 0)
    assert [Path(p).name for p in step1] == [
        "first.pdf", "second.pdf", "img.png"]
    corrected = eng.move_item(step1, 1, 1)
    assert [Path(p).name for p in corrected] == [
        "first.pdf", "img.png", "second.pdf"]
    out = tmp_path / "corrected.pdf"
    proc = _run_cli(
        ["--files", *corrected, "--out", str(out)], cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    texts = _page_texts(out)
    assert "CORRECT-FIRST" in texts[0]
    assert "CORRECT-SECOND" in texts[2]


def test_cli_image_page_size_landscape_applies_only_to_images(tmp_path):
    """--size letter --orientation landscape: image pages are landscape,
    embedded PDF pages keep their own (portrait A4-ish) size."""
    image = tmp_path / "img.png"
    pdf = tmp_path / "doc.pdf"
    _make_png(image)
    _make_text_pdf(pdf, ["KEPT-SIZE-PAGE"])
    out = tmp_path / "sized.pdf"
    proc = _run_cli(
        ["--files", str(image), str(pdf), "--size", "letter",
         "--orientation", "landscape", "--out", str(out)], cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    sizes = _page_sizes(out)
    assert len(sizes) == 2
    assert sizes[0] == (792.0, 612.0)  # letter landscape, image page
    assert sizes[1][0] < sizes[1][1]  # PDF page untouched, still portrait


def test_cli_sort_name_is_opt_in_and_changes_order(tmp_path):
    """--sort name is an explicit choice, never the default for files."""
    first = tmp_path / "z-first.pdf"
    second = tmp_path / "a-second.pdf"
    _make_text_pdf(first, ["NAME-Z"])
    _make_text_pdf(second, ["NAME-A"])
    out = tmp_path / "named.pdf"
    proc = _run_cli(
        ["--files", str(first), str(second), "--sort", "name",
         "--out", str(out)], cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    texts = _page_texts(out)
    assert "NAME-A" in texts[0] and "NAME-Z" in texts[1]


# ------------------------------------------------------------- GUI behaviour

def test_gui_manual_reorder_forces_selection_sort():
    """Regression guard for the v2.3.0 trap: a persisted Sort=name in
    the GUI would otherwise re-sort at Convert and silently undo a
    manual Up/Down reorder. Every move handler must set selection."""
    text = GUI_PY.read_text(encoding="utf-8", errors="replace")
    for handler in ("on_move_up", "on_move_down",
                    "on_move_top", "on_move_bottom"):
        assert handler in text
    assert text.count('self.var_sort.set("selection")') >= 5
    assert "--rotate" in text
    assert "on_move_top" in text and "on_move_bottom" in text


# ------------------------------------------------------- context-menu verbs

def test_visualizer_verb_on_all_os_builders():
    eng = _engine()
    verbs = dict((v[0], v) for v in eng.CTX_VERBS)
    assert verbs["visualizer"][1] == "Review & merge in visualizer..."
    assert verbs["visualizer"][2] == "--gui"

    # Windows flat builder: visualizer key beside the merge key.
    plan = eng.build_windows_context_menu(
        r"C:\Users\test\Tools\bin\jpg2pdf.exe",
        r"C:\Users\test\Tools\bin")
    vis = {k: v for k, n, v in plan["entries"]
           if k.endswith("\\Jpg2PdfVisualizer\\command")}
    assert vis, "no Windows flat visualizer verb"
    for value in vis.values():
        assert "jpg2pdf-selected-launcher.vbs" in value
        assert '"gui"' in value and '"%1"' in value
    assert any(n == "MultiSelectModel" and v == "Player"
               for k, n, v in plan["entries"]
               if k.endswith("\\Jpg2PdfVisualizer"))

    # macOS: workflow runs --gui with the selection list.
    mac = eng.build_macos_context_menu(Path("/tmp/fakehome"),
                                       "/opt/jpg2pdf/jpg2pdf")
    vis_wflow = [c for p, c in mac.items()
                 if "visualizer" in p.lower() and p.endswith("document.wflow")]
    assert vis_wflow and "--gui" in vis_wflow[0]
    assert "--files-from" in vis_wflow[0]

    # Linux: Nemo + KDE + Thunar all carry a --gui verb.
    linux = eng.build_linux_context_menu(Path("/tmp/fakehome"),
                                         "/opt/jpg2pdf/jpg2pdf")
    nemo_vis = [c["content"] for p, c in linux.items()
                if p.endswith(".nemo_action")
                and "visualizer" in p]
    assert nemo_vis and "--gui" in nemo_vis[0] and "--files %F" in nemo_vis[0]
    kde = [c["content"] for p, c in linux.items()
           if p.endswith("jpg2pdf.desktop")][0]
    assert "--gui" in kde
    thunar = eng.thunar_actions("/opt/jpg2pdf/jpg2pdf")
    assert any(a["name"] == "Review & merge in visualizer..."
               and "--gui" in a["command"] for a in thunar)


def test_powershell_registrar_and_unregister_cover_visualizer():
    ps1 = REGISTER_PS1.read_text(encoding="utf-8", errors="replace")
    assert "Register-VisualizerVerb" in ps1
    assert "Jpg2PdfVisualizer" in ps1
    assert 'VerbId "gui"' in ps1
    un = UNREGISTER_PS1.read_text(encoding="utf-8", errors="replace")
    assert "Jpg2PdfVisualizer" in un

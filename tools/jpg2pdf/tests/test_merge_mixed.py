"""Mixed-input merge tests (cicd issue 02): image + PDF + HTML + Word.

These run on every OS in CI (the tests job is Ubuntu) and prove the
exact user scenario from cicd issue 08: select files of different
kinds, merge them into ONE pdf, in selection order -- including the
positional-argument form that file managers pass (``%F``), which the
pre-v2.3.0 CLI rejected because it accepted a single positional only.

Run with:
    cd tools/jpg2pdf && python -m pytest -q tests
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG_SRC = REPO_ROOT / "tools" / "jpg2pdf" / "src"
SCRIPT = PKG_SRC / "jpg2pdf.py"

sys.path.insert(0, str(PKG_SRC))


def _run_cli(args, cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8")


def _make_png(path: Path):
    from PIL import Image
    Image.new("RGB", (96, 64), (200, 60, 60)).save(path, "PNG")


def _make_two_page_pdf(path: Path):
    from PIL import Image
    first = Image.new("RGB", (200, 200), (60, 200, 60))
    second = Image.new("RGB", (200, 200), (60, 60, 200))
    first.save(path, "PDF", save_all=True, append_images=[second])


def _make_html(path: Path):
    path.write_text(
        "<html><body><h1>Html</h1><p>mixed merge html page.</p>"
        "</body></html>", encoding="utf-8")


def _make_docx(path: Path):
    """Minimal valid .docx built with the stdlib only (no python-docx)."""
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
        'content-types"><Default Extension="rels" ContentType='
        '"application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType='
        '"application/vnd.openxmlformats-officedocument.wordprocessingml.'
        'document.main+xml"/></Types>')
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
        '2006/relationships"><Relationship Id="rId1" Type='
        '"http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>')
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main"><w:body>'
        '<w:p><w:r><w:t>Word paragraph one for mixed merge.</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>Word paragraph two.</w:t></w:r></w:p>'
        '</w:body></w:document>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)


def _page_count(pdf: Path) -> int:
    from pypdf import PdfReader
    return len(PdfReader(str(pdf)).pages)


def _fixtures(tmp_path: Path):
    png = tmp_path / "a.png"
    pdf = tmp_path / "b.pdf"
    html = tmp_path / "c.html"
    docx = tmp_path / "d.docx"
    _make_png(png)
    _make_two_page_pdf(pdf)
    _make_html(html)
    _make_docx(docx)
    return png, pdf, html, docx


def test_mixed_merge_files_flag(tmp_path):
    png, pdf, html, docx = _fixtures(tmp_path)
    out = tmp_path / "merged.pdf"
    proc = _run_cli(
        ["--files", str(png), str(pdf), str(html), str(docx),
         "--out", str(out)], cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert out.exists() and out.read_bytes()[:4] == b"%PDF"
    # 1 image page + 2 pdf pages + >=1 html page + >=1 word page.
    assert _page_count(out) >= 5


def test_mixed_merge_positional_paths(tmp_path):
    """The file-manager form: jpg2pdf f1 f2 f3 (KDE/Thunar/Nemo %F)."""
    png, pdf, html, docx = _fixtures(tmp_path)
    out = tmp_path / "merged-positional.pdf"
    proc = _run_cli(
        [str(png), str(pdf), str(html), str(docx), "--out", str(out)],
        cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert _page_count(out) >= 5


def test_docx_only_merge_not_dropped(tmp_path):
    """A Word-only selection must produce a PDF on every OS.

    Pre-v2.3.0 this failed on Linux / macOS-without-Word because
    word_to_pdf only tried docx2pdf and silently skipped the file.
    """
    docx = tmp_path / "only.docx"
    _make_docx(docx)
    out = tmp_path / "word-only.pdf"
    proc = _run_cli(["--files", str(docx), "--out", str(out)], cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert out.exists() and _page_count(out) >= 1


def test_docx_paragraph_extraction_and_text_fallback(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("jpg2pdf_engine", SCRIPT)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)

    docx = tmp_path / "plain.docx"
    _make_docx(docx)
    paras = engine.docx_paragraphs(docx)
    assert any("Word paragraph one" in p for p in paras)

    out = tmp_path / "fallback.pdf"
    assert engine.text_to_pdf(paras, out) is not None
    assert out.read_bytes()[:4] == b"%PDF"
    assert _page_count(out) >= 1


def test_word_to_pdf_chain_succeeds(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("jpg2pdf_engine2", SCRIPT)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)

    docx = tmp_path / "chain.docx"
    _make_docx(docx)
    out = tmp_path / "chain.pdf"
    result = engine.word_to_pdf(docx, out)
    assert result is not None and out.exists()
    assert _page_count(out) >= 1

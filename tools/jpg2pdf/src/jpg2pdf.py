#!/usr/bin/env python3
"""jpg2pdf -- Combine images into a single PDF.

Input modes:
  jpg2pdf <folder> [options]
  jpg2pdf f1 f2 ... [options]               # files, in order (file-manager form)
  jpg2pdf --files f1 f2 ... [options]
  jpg2pdf --files-from list.txt [options]   # one path per line (UTF-8)
  jpg2pdf --install-context-menu            # right-click entries for this OS

See spec/SPEC.md for the full specification.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

try:
    from jpg2pdf_app.youtube import (
        download_thumbnail,
        extract_video_id,
        fetch_video_title,
        get_default_thumbnail_dir,
        open_directory_in_explorer,
        resolve_youtube_thumbnails,
        slugify_title,
    )
except ImportError:
    import sys as _sys
    _app_dir = Path(__file__).resolve().parent
    if str(_app_dir) not in _sys.path:
        _sys.path.insert(0, str(_app_dir))
    try:
        from jpg2pdf_app.youtube import (
            download_thumbnail,
            extract_video_id,
            fetch_video_title,
            get_default_thumbnail_dir,
            open_directory_in_explorer,
            resolve_youtube_thumbnails,
            slugify_title,
        )
    except ImportError:
        download_thumbnail = None
        extract_video_id = None
        fetch_video_title = None
        get_default_thumbnail_dir = None
        open_directory_in_explorer = None
        resolve_youtube_thumbnails = None
        slugify_title = None

__version__ = "2.3.0"


# Pencil presets -- tuned for faint handwritten text.
# Module-scope so prompt_pencil_strength() can render the live preview with
# the same numbers main() will use for the real conversion.
PENCIL_PRESETS = {
    "subtle": dict(opacity=0.32, ink_threshold=105, ink_darken=0.52, brightness=1.0),
    "normal": dict(opacity=0.20, ink_threshold=128, ink_darken=0.32, brightness=1.0),
    "extra":  dict(opacity=0.10, ink_threshold=165, ink_darken=0.12, brightness=1.02),
}

# ---- Persistent user prefs (last chosen pencil strength, etc.) ----
# Honors $JPG2PDF_CONFIG_DIR for tests / portable installs.
CONFIG_DIR  = Path(os.environ.get("JPG2PDF_CONFIG_DIR",
                                  str(Path.home() / ".jpg2pdf")))
CONFIG_PATH = CONFIG_DIR / "config.json"


def load_prefs() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_prefs(prefs: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"  (warning: could not save prefs: {e})", file=sys.stderr)


# ---- Output filename patterns ----
# Available placeholders for --name-pattern (case-insensitive):
#   {folder}    parent folder name (or input folder for folder-mode)
#   {first}     base name of the first input image (no extension)
#   {count}     number of images included
#   {style}     "none" or "pencil"
#   {strength}  pencil strength preset name when --style pencil, else ""
#   {date}      YYYY-MM-DD (local time)
#   {time}      HHMMSS (local time, no separators -- filesystem-safe)
#   {datetime}  YYYY-MM-DD_HHMMSS
#   {y} {m} {d} {hh} {mm} {ss}   individual zero-padded parts
NAME_PATTERN_TOKENS = (
    "folder", "first", "count", "style", "strength",
    "date", "time", "datetime", "y", "m", "d", "hh", "mm", "ss",
)
DEFAULT_NAME_PATTERN = "{folder}"

_INVALID_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _sanitize_filename(name: str) -> str:
    cleaned = _INVALID_FS_CHARS.sub("_", name).strip(" .")
    return cleaned or "images"


def format_pdf_name(pattern: str, *, folder_name: str, first_image: Path,
                    count: int, style: str, strength: str) -> str:
    """Render the user's name pattern into a safe filename (no extension)."""
    import datetime as _dt
    now = _dt.datetime.now()
    values = {
        "folder":   folder_name,
        "first":    first_image.stem,
        "count":    str(count),
        "style":    style,
        "strength": strength if style == "pencil" else "",
        "date":     now.strftime("%Y-%m-%d"),
        "time":     now.strftime("%H%M%S"),
        "datetime": now.strftime("%Y-%m-%d_%H%M%S"),
        "y":  now.strftime("%Y"), "m":  now.strftime("%m"), "d":  now.strftime("%d"),
        "hh": now.strftime("%H"), "mm": now.strftime("%M"), "ss": now.strftime("%S"),
    }
    try:
        rendered = pattern.format(**values)
    except (KeyError, IndexError, ValueError) as e:
        print(f"  (warning: bad --name-pattern {pattern!r}: {e}; "
              f"falling back to '{DEFAULT_NAME_PATTERN}')", file=sys.stderr)
        rendered = DEFAULT_NAME_PATTERN.format(**values)
    # Collapse leftover empty pieces (e.g. "{strength}" when style=none)
    rendered = re.sub(r"_{2,}", "_", rendered).strip("_- ")
    return _sanitize_filename(rendered)



def prompt_pencil_strength(default: str = "subtle", sample_path=None) -> str:
    """Show a Tk dropdown to pick pencil strength, with a LIVE preview.

    When `sample_path` points to a real image, a thumbnail of that image is
    rendered with each preset on the fly -- switching the dropdown immediately
    re-renders the preview so the user can pick the strength that makes
    faint text most readable before any PDF is written.

    Returns the chosen value ('subtle' | 'normal' | 'extra'), or `default`
    if Tk is unavailable or the user cancels.
    """
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        return default

    # ImageTk is part of Pillow's tk extras -- gracefully degrade without it.
    try:
        from PIL import ImageTk
        has_imagetk = True
    except Exception:
        ImageTk = None
        has_imagetk = False

    choices = ["subtle", "normal", "extra"]
    descriptions = {
        "subtle": "Subtle  -- gentle, keeps paper texture (default)",
        "normal": "Normal  -- balanced ink + paper grain",
        "extra":  "Extra visible -- aggressive darkening for very faint pencil",
    }
    result = {"value": default}

    try:
        root = tk.Tk()
    except Exception:
        return default

    root.title("jpg2pdf -- Pencil strength")
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    root.resizable(False, False)

    frm = ttk.Frame(root, padding=16)
    frm.grid(row=0, column=0, sticky="nsew")
    ttk.Label(frm, text="Choose pencil rendering strength:").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

    var = tk.StringVar(value=descriptions.get(default, descriptions["normal"]))
    combo = ttk.Combobox(frm, textvariable=var, state="readonly",
                         values=[descriptions[c] for c in choices], width=46)
    combo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))

    # ---- Live preview ----
    preview_thumb = None     # base RGB thumbnail (PIL Image), small for speed
    preview_label = None
    photo_ref = {"img": None}   # keep PhotoImage reference alive

    if sample_path is not None and has_imagetk:
        try:
            with Image.open(sample_path) as raw:
                base = raw.convert("RGB")
                base.thumbnail((520, 520), Image.LANCZOS)
                preview_thumb = base.copy()
        except Exception:
            preview_thumb = None

    if preview_thumb is not None:
        ttk.Label(frm, text="Live preview (faint text gets clearer ->):").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(4, 4))
        preview_label = ttk.Label(frm, relief="solid", borderwidth=1)
        preview_label.grid(row=3, column=0, columnspan=2, pady=(0, 12))
    elif sample_path is not None:
        ttk.Label(frm,
                  text="(Install Pillow's Tk extras for a live preview)",
                  foreground="#888").grid(row=2, column=0, columnspan=2,
                                          sticky="w", pady=(0, 8))

    def _selected_key():
        sel = var.get()
        for c in choices:
            if descriptions[c] == sel:
                return c
        return default

    def _render_preview(*_):
        if preview_thumb is None or preview_label is None:
            return
        key = _selected_key()
        p = PENCIL_PRESETS[key]
        try:
            rendered = apply_pencil(
                preview_thumb,
                opacity=p["opacity"],
                brightness=p["brightness"],
                ink_threshold=p["ink_threshold"],
                ink_darken=p["ink_darken"],
            )
        except Exception:
            return
        photo_ref["img"] = ImageTk.PhotoImage(rendered)
        preview_label.configure(image=photo_ref["img"])

    combo.bind("<<ComboboxSelected>>", _render_preview)
    _render_preview()  # initial render for `default`

    def _ok(_evt=None):
        result["value"] = _selected_key()
        root.destroy()

    def _cancel(_evt=None):
        root.destroy()

    btns = ttk.Frame(frm)
    btns.grid(row=4, column=0, columnspan=2, sticky="e")
    ttk.Button(btns, text="Cancel", command=_cancel).grid(row=0, column=0, padx=(0, 6))
    ok_btn = ttk.Button(btns, text="Convert", command=_ok)
    ok_btn.grid(row=0, column=1)
    root.bind("<Return>", _ok)
    root.bind("<Escape>", _cancel)
    ok_btn.focus_set()

    # Center on screen
    root.update_idletasks()
    w = root.winfo_width(); h = root.winfo_height()
    sw = root.winfo_screenwidth(); sh = root.winfo_screenheight()
    root.geometry(f"+{(sw - w) // 2}+{max(20, (sh - h) // 4)}")

    root.mainloop()
    return result["value"]


def prompt_thumbnail_grid(images, thumb_px: int = 140, cols: int = 4):
    """Show a scrollable Tk grid of thumbnails so the user can confirm /
    deselect images before the PDF is built.

    Returns: a (filtered, original-order) list of Paths to actually convert,
    or None if the user cancelled. If Tk or Pillow's ImageTk isn't available,
    returns the input unchanged so conversion proceeds without an interactive
    step.
    """
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        return list(images)
    try:
        from PIL import ImageTk
    except Exception:
        return list(images)
    try:
        root = tk.Tk()
    except Exception:
        return list(images)

    root.title(f"jpg2pdf -- confirm {len(images)} image(s)")
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass

    state = {"result": None}
    vars_ = []  # list of (Path, BooleanVar)

    header = ttk.Frame(root, padding=(12, 10, 12, 6))
    header.grid(row=0, column=0, sticky="ew")
    counter = ttk.Label(header, text="")
    counter.grid(row=0, column=0, sticky="w")

    def _refresh_counter(*_):
        n = sum(1 for _, v in vars_ if v.get())
        counter.configure(text=f"{n} of {len(vars_)} selected")

    def _select_all():
        for _, v in vars_: v.set(True)
        _refresh_counter()

    def _select_none():
        for _, v in vars_: v.set(False)
        _refresh_counter()

    ttk.Button(header, text="All",  command=_select_all ).grid(row=0, column=1, padx=(12, 4))
    ttk.Button(header, text="None", command=_select_none).grid(row=0, column=2)
    header.columnconfigure(0, weight=1)

    body = ttk.Frame(root, padding=(8, 4, 8, 4))
    body.grid(row=1, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)

    rows = max(1, (len(images) + cols - 1) // cols)
    canvas = tk.Canvas(body, highlightthickness=0,
                       width=cols * (thumb_px + 24) + 20,
                       height=min(3, rows) * (thumb_px + 60) + 20)
    vbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vbar.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    vbar.grid(row=0, column=1, sticky="ns")
    body.columnconfigure(0, weight=1)
    body.rowconfigure(0, weight=1)

    inner = ttk.Frame(canvas)
    canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>",
               lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind_all("<MouseWheel>",
                    lambda e: canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))

    photos = []  # keep PhotoImage references alive
    for idx, p in enumerate(images):
        cell = ttk.Frame(inner, padding=6, relief="solid", borderwidth=1)
        cell.grid(row=idx // cols, column=idx % cols, padx=4, pady=4, sticky="n")
        kind = kind_of(p)
        photo = None
        if kind == "image":
            try:
                with Image.open(p) as im:
                    im = im.convert("RGB")
                    im.thumbnail((thumb_px, thumb_px), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(im)
            except Exception:
                photo = None
        photos.append(photo)
        if photo is not None:
            ttk.Label(cell, image=photo).grid(row=0, column=0)
        else:
            badge = {"pdf": "PDF", "html": "HTML",
                     "word": "DOC", "image": "(unreadable)"}.get(kind, "FILE")
            ttk.Label(cell, text=badge, width=18,
                      anchor="center").grid(row=0, column=0, ipady=thumb_px // 3)
        var = tk.BooleanVar(value=True)
        vars_.append((p, var))
        name = p.name if len(p.name) <= 22 else p.name[:19] + "..."
        ttk.Checkbutton(cell, text=name, variable=var,
                        command=_refresh_counter).grid(row=1, column=0, sticky="w")

    _refresh_counter()

    footer = ttk.Frame(root, padding=(12, 6, 12, 12))
    footer.grid(row=2, column=0, sticky="ew")
    footer.columnconfigure(0, weight=1)

    def _ok():
        state["result"] = [p for p, v in vars_ if v.get()]
        root.destroy()

    def _cancel():
        state["result"] = None
        root.destroy()

    ttk.Button(footer, text="Cancel",  command=_cancel).grid(row=0, column=1, padx=(0, 6))
    ok_btn = ttk.Button(footer, text="Convert", command=_ok)
    ok_btn.grid(row=0, column=2)
    root.bind("<Return>", lambda _e: _ok())
    root.bind("<Escape>", lambda _e: _cancel())
    ok_btn.focus_set()

    root.update_idletasks()
    w = min(root.winfo_reqwidth(),  root.winfo_screenwidth()  - 80)
    h = min(root.winfo_reqheight(), root.winfo_screenheight() - 120)
    sw = root.winfo_screenwidth(); sh = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(20, (sh - h) // 5)}")

    root.mainloop()
    return state["result"]


PAGE_SIZES = {  # points (1/72 inch)
    "a4":     (595.28, 841.89),
    "letter": (612.00, 792.00),
    "legal":  (612.00, 1008.00),
}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
PDF_EXTS   = {".pdf"}
HTML_EXTS  = {".html", ".htm"}
WORD_EXTS  = {".docx", ".doc"}
SUPPORTED_EXTS = IMAGE_EXTS | PDF_EXTS | HTML_EXTS | WORD_EXTS
# Backwards-compat alias (some older callers / tests imported EXTS).
EXTS = IMAGE_EXTS


def kind_of(p: Path) -> str:
    """Classify an input path: 'image' | 'pdf' | 'html' | 'word' | 'unknown'."""
    ext = p.suffix.lower()
    if ext in IMAGE_EXTS: return "image"
    if ext in PDF_EXTS:   return "pdf"
    if ext in HTML_EXTS:  return "html"
    if ext in WORD_EXTS:  return "word"
    return "unknown"


def natural_key(p: Path):
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", p.name)]


def collect_from_folder(folder: Path, recursive: bool):
    it = folder.rglob("*") if recursive else folder.iterdir()
    files = [p for p in it if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
    files.sort(key=natural_key)
    return files


def collect_from_list(paths):
    """Preserve given order. Skip unsupported / missing files with a warning."""
    out = []
    for raw in paths:
        p = Path(raw).expanduser().resolve()
        if not p.is_file():
            print(f"  skip (not a file): {p}", file=sys.stderr); continue
        if p.suffix.lower() not in SUPPORTED_EXTS:
            print(f"  skip (unsupported): {p}", file=sys.stderr); continue
        out.append(p)
    return out


# ---------- Per-type -> PDF converters ----------
# Each returns a Path to a PDF file (either a freshly-written temp file or
# the original input for already-PDF inputs). They never raise on missing
# optional deps -- they print a warning and return None so the caller can skip.

def html_to_pdf(src: Path, out_pdf: Path) -> Path | None:
    try:
        from xhtml2pdf import pisa  # type: ignore
    except Exception as e:
        print(f"  skip {src.name}: HTML support needs xhtml2pdf ({e})",
              file=sys.stderr)
        return None
    try:
        html = src.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"  skip {src.name}: cannot read HTML ({e})", file=sys.stderr)
        return None
    with open(out_pdf, "wb") as f:
        result = pisa.CreatePDF(src=html, dest=f, encoding="utf-8")
    if result.err:
        print(f"  skip {src.name}: HTML->PDF failed ({result.err} error(s))",
              file=sys.stderr)
        return None
    return out_pdf


def find_soffice() -> str | None:
    """Locate a LibreOffice binary on any OS, or None.

    Checks PATH first, then the standard install locations on macOS,
    Linux and Windows. LibreOffice is the cross-platform Word engine:
    unlike docx2pdf it also works on Linux and on macOS machines
    without MS Word installed.
    """
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    candidates = [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/soffice",
        "/usr/local/bin/soffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for cand in candidates:
        if Path(cand).is_file():
            return cand
    return None


def _word_via_docx2pdf(src: Path, out_pdf: Path) -> bool:
    """Try MS Word via docx2pdf (Windows / macOS with Word installed).

    docx2pdf is not implemented on Linux at all, so skip it there and
    go straight to LibreOffice / the built-in fallback.
    """
    if sys.platform not in ("win32", "darwin"):
        return False
    try:
        from docx2pdf import convert as _docx_convert  # type: ignore
    except Exception:
        return False
    try:
        _docx_convert(str(src), str(out_pdf))
    except Exception as e:
        print(f"  docx2pdf failed for {src.name}: {e}", file=sys.stderr)
        return False
    return out_pdf.is_file()


def _word_via_soffice(src: Path, out_pdf: Path, soffice: str) -> bool:
    """Convert Word -> PDF with headless LibreOffice (any OS).

    Uses an isolated throwaway user profile so a locked or corrupted
    real profile can never block a right-click conversion.
    """
    try:
        with tempfile.TemporaryDirectory(prefix="jpg2pdf-soffice-") as td:
            td_p = Path(td)
            profile = td_p / "profile"
            cmd = [soffice, "--headless", "--norestore", "--nolockcheck",
                   f"-env:UserInstallation={profile.as_uri()}",
                   "--convert-to", "pdf", "--outdir", str(td_p), str(src)]
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=180)
            produced = td_p / (src.stem + ".pdf")
            if proc.returncode == 0 and produced.is_file():
                shutil.copyfile(produced, out_pdf)
                return True
            print(f"  soffice failed for {src.name}: "
                  f"{(proc.stderr or proc.stdout or '').strip()[:200]}",
                  file=sys.stderr)
    except Exception as e:
        print(f"  soffice failed for {src.name}: {e}", file=sys.stderr)
    return False


def docx_paragraphs(src: Path) -> list:
    """Extract paragraph texts from a .docx using only the stdlib."""
    import xml.etree.ElementTree as _et
    import zipfile as _zf
    w_ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        with _zf.ZipFile(src) as z:
            xml_bytes = z.read("word/document.xml")
        root = _et.fromstring(xml_bytes)
    except Exception as e:
        print(f"  cannot read {src.name} as .docx: {e}", file=sys.stderr)
        return []
    paras = []
    for para in root.iter(w_ns + "p"):
        texts = [t.text or "" for t in para.iter(w_ns + "t")]
        paras.append("".join(texts))
    return paras


def _escape_pdf_text(text: str) -> str:
    safe = text.encode("latin-1", "replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_to_pdf(lines, out_pdf: Path) -> Path | None:
    """Write plain-text lines to a simple multi-page PDF (stdlib only).

    Last-resort renderer so a .docx can still be merged on a machine
    with neither MS Word nor LibreOffice. A4, Helvetica, wrapped and
    paginated; formatting is simplified, content is preserved.
    """
    import textwrap as _tw
    wrapped = []
    for line in lines:
        line = str(line).rstrip("\n")
        if line.strip():
            wrapped.extend(_tw.wrap(line, width=92) or [""])
        else:
            wrapped.append("")
    if not wrapped:
        wrapped = [""]
    per_page = 48
    chunks = [wrapped[i:i + per_page]
              for i in range(0, len(wrapped), per_page)]
    objs = {}
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    page_ids = []
    next_id = 4
    for chunk in chunks:
        content_id = next_id
        page_id = next_id + 1
        next_id += 2
        page_ids.append(page_id)
        ops = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
        for line in chunk:
            ops.append(f"({_escape_pdf_text(line)}) Tj")
            ops.append("T*")
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1", "replace")
        objs[content_id] = (b"<< /Length " + str(len(stream)).encode()
                            + b" >>\nstream\n" + stream + b"\nendstream")
        objs[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {content_id} 0 R >>").encode("latin-1")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objs[2] = (f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>"
               ).encode("latin-1")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode("latin-1") + objs[oid] + b"\nendobj\n"
    xref_pos = len(out)
    max_id = max(objs)
    out += f"xref\n0 {max_id + 1}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for oid in range(1, max_id + 1):
        out += f"{offsets[oid]:010d} 00000 n \n".encode("latin-1")
    out += (f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n").encode("latin-1")
    out_pdf.write_bytes(bytes(out))
    return out_pdf


def word_to_pdf(src: Path, out_pdf: Path) -> Path | None:
    """Convert a Word file (.docx / .doc) to PDF, on any OS.

    Conversion chain, best fidelity first:
      1. docx2pdf / MS Word (Windows, macOS with Word).
      2. LibreOffice headless (Windows, macOS, Linux).
      3. Built-in .docx text fallback (any OS, no dependencies).
    A Word input is never silently dropped: None is returned only
    when every converter failed, and the reason is printed.
    """
    if _word_via_docx2pdf(src, out_pdf):
        return out_pdf
    soffice = find_soffice()
    if soffice and _word_via_soffice(src, out_pdf, soffice):
        return out_pdf
    if src.suffix.lower() == ".docx":
        paras = docx_paragraphs(src)
        if paras:
            print(f"  note: {src.name}: no Word/LibreOffice found, using "
                  "built-in text fallback (simplified formatting).",
                  file=sys.stderr)
            try:
                if text_to_pdf(paras, out_pdf):
                    return out_pdf
            except Exception as e:
                print(f"  skip {src.name}: text fallback failed ({e})",
                      file=sys.stderr)
                return None
    print(f"  skip {src.name}: Word->PDF failed. Install Microsoft Word "
          "or LibreOffice to convert .doc/.docx files.", file=sys.stderr)
    return None


def images_to_pdf_chunk(image_paths, out_pdf: Path, *, page_w_pt, page_h_pt,
                        fit, dpi, auto_rotate, rotate, style,
                        pencil_opacity, pencil_brightness,
                        pencil_ink_threshold, pencil_ink_darken) -> Path | None:
    pages = []
    for p in image_paths:
        pages.append(make_page(p, page_w_pt, page_h_pt, fit, dpi,
                               auto_rotate=auto_rotate, rotate=rotate,
                               style=style,
                               pencil_opacity=pencil_opacity,
                               pencil_brightness=pencil_brightness,
                               pencil_ink_threshold=pencil_ink_threshold,
                               pencil_ink_darken=pencil_ink_darken))
    if not pages:
        return None
    pages[0].save(out_pdf, "PDF", resolution=float(dpi),
                  save_all=True, append_images=pages[1:])
    return out_pdf


def merge_pdfs(pdf_paths, out: Path) -> None:
    if len(pdf_paths) == 1:
        import shutil
        shutil.copyfile(pdf_paths[0], out)
        return
    try:
        from pypdf import PdfWriter  # local import -- heavy dep
    except ImportError:
        print("Error: 'pypdf' package is required to merge multiple PDF files.", file=sys.stderr)
        print("Please install it with: pip install pypdf", file=sys.stderr)
        sys.exit(1)
    writer = PdfWriter()
    for p in pdf_paths:
        writer.append(str(p))
    with open(out, "wb") as f:
        writer.write(f)
    writer.close()


# ---------- File-manager (right-click) integration ----------
# The binary registers its OWN context-menu entries via
# --install-context-menu / --uninstall-context-menu. Before v2.3.0 the
# registrar lived outside the binary (a PowerShell script downloaded
# from the latest release tag by install.ps1, plus drifting inline
# heredocs in install.sh), so fixes routinely never reached installed
# machines -- see .ai-memory/cicd-issues/08-context-menu-gone-cross-platform.md.
#
# The builders below are pure functions (registry plan for Windows,
# path -> content maps for macOS/Linux) so the whole matrix can be
# unit-tested on any OS; only the thin appliers touch the real system.

CTX_VERBS = [
    ("a4", "Combine into PDF (A4)", "--size a4"),
    ("letter", "Combine into PDF (Letter)", "--size letter"),
    ("legal", "Combine into PDF (Legal)", "--size legal"),
    ("a4-pencil", "Combine into PDF (A4, pencil look)",
     "--size a4 --style pencil"),
]
CTX_FLAT_LABEL = "Combine into PDF"
CTX_EXTS = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff",
            ".pdf", ".html", ".htm", ".docx", ".doc"]


def _ctx_platform(platform=None) -> str:
    if platform:
        p = str(platform).lower()
        if p.startswith("win"):
            return "windows"
        if p in ("darwin", "mac", "macos", "osx"):
            return "macos"
        return "linux"
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _ctx_self_command(command=None) -> str:
    """Command line prefix that invokes this jpg2pdf install."""
    if command:
        return str(command)
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve())
    found = shutil.which("jpg2pdf")
    if found:
        return str(Path(found).resolve())
    return f"{Path(sys.executable).resolve()} {Path(__file__).resolve()}"


def _desktop_exec(command: str, args: str) -> str:
    """Exec= value for .desktop / .nemo_action files.

    The command prefix may be "interpreter script" (source runs) or a
    single binary path (installed runs); quote each token that needs
    it instead of wrapping the whole prefix in one pair of quotes.
    """
    import shlex as _shlex
    try:
        tokens = _shlex.split(command)
    except ValueError:
        tokens = [command]
    quoted = " ".join(f'"{tok}"' if " " in tok else tok for tok in tokens)
    return f"{quoted} {args}".strip()


def _shell_command(command: str) -> str:
    """Shell-safe rendering of the command prefix (token-wise quoting)."""
    import shlex as _shlex
    try:
        tokens = _shlex.split(command)
    except ValueError:
        tokens = [command]
    return " ".join(_shlex.quote(tok) for tok in tokens)


# ----- Windows -----

_CTX_RUNNER_CMD = r"""@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "JPG2PDF_EXE=__EXE__"
set "JPG2PDF_GUI_EXE=__GUI_EXE__"
set "LOG_DIR=%LOCALAPPDATA%\jpg2pdf"
if not exist "!LOG_DIR!" mkdir "!LOG_DIR!" >nul 2>nul
set "LOG=!LOG_DIR!\context.log"
set "QUEUE_DIR=!LOG_DIR!\queue"
if not exist "!QUEUE_DIR!" mkdir "!QUEUE_DIR!" >nul 2>nul

if /I "%~1"=="--exec" goto exec
if /I "%~1"=="--run"  goto run
goto queue

:queue
set "VERB_ID=%~1"
set "VERB_ARGS=%~2"
set "SELECTED_FILE=%~3"
if "!VERB_ID!"=="" exit /b 1
if "!SELECTED_FILE!"=="" exit /b 1
set "QUEUE=!QUEUE_DIR!\!VERB_ID!.lst"
>>"!LOG!" echo [%DATE% %TIME%] selected verb=!VERB_ID! file=!SELECTED_FILE!
>>"!QUEUE!" echo(!SELECTED_FILE!
call "%~f0" --run "!VERB_ID!" "!VERB_ARGS!" "!QUEUE!" "!LOG!"
exit /b !ERRORLEVEL!

:run
set "VERB_ID=%~2"
set "VERB_ARGS=%~3"
set "QUEUE=%~4"
set "LOG=%~5"
set "LAST_SIZE=-1"
for /L %%I in (1,1,12) do (
  for %%A in ("!QUEUE!") do set "NOW_SIZE=%%~zA"
  if "!NOW_SIZE!"=="!LAST_SIZE!" if %%I GTR 2 goto queue_ready
  set "LAST_SIZE=!NOW_SIZE!"
  ping -n 2 127.0.0.1 >nul 2>nul
)
:queue_ready
set "WORK_NAME=!VERB_ID!-work-%RANDOM%%RANDOM%.lst"
ren "!QUEUE!" "!WORK_NAME!" >nul 2>nul
if errorlevel 1 exit /b 0
set "QUEUE=!QUEUE_DIR!\!WORK_NAME!"
if /I "!VERB_ID!"=="gui" (
  set "TARGET_EXE=!JPG2PDF_GUI_EXE!"
  if not exist "!TARGET_EXE!" set "TARGET_EXE=!JPG2PDF_EXE!"
  start "" "!TARGET_EXE!" --gui --files-from "!QUEUE!"
  exit /b 0
)
>>"!LOG!" echo [%DATE% %TIME%] launching visible console verb=!VERB_ID! queue=!QUEUE!
start "jpg2pdf - !VERB_ID!" cmd.exe /d /c "call ""%~f0"" --exec ""!VERB_ID!"" ""!VERB_ARGS!"" ""!QUEUE!"" ""!LOG!"" "
exit /b 0

:exec
set "VERB_ID=%~2"
set "VERB_ARGS=%~3"
set "QUEUE=%~4"
set "LOG=%~5"
title jpg2pdf !VERB_ID!
echo.
echo [jpg2pdf] Combining selected files (!VERB_ID!)
echo.
>>"!LOG!" echo [%DATE% %TIME%] exec verb=!VERB_ID! queue=!QUEUE!
call "!JPG2PDF_EXE!" !VERB_ARGS! --files-from "!QUEUE!"
set "JPG2PDF_CODE=!ERRORLEVEL!"
>>"!LOG!" echo [%DATE% %TIME%] exit=!JPG2PDF_CODE! verb=!VERB_ID!
if not "!JPG2PDF_CODE!"=="0" (
  echo.
  echo [jpg2pdf] FAILED with exit code !JPG2PDF_CODE!.
  echo [jpg2pdf] Log: "!LOG!"
)
echo.
echo [jpg2pdf] Done. Press any key to close this window.
pause >nul
del "!QUEUE!" >nul 2>nul
exit /b !JPG2PDF_CODE!
"""

_CTX_LAUNCHER_VBS = r"""Option Explicit
Dim sh, args, i, quoted, cmdLine
Set sh = CreateObject("WScript.Shell")
args = ""
For i = 0 To WScript.Arguments.Count - 1
  quoted = Replace(WScript.Arguments(i), Chr(34), Chr(34) & Chr(34))
  args = args & " " & Chr(34) & quoted & Chr(34)
Next
cmdLine = "cmd.exe /d /c " & Chr(34) & Chr(34) & "__RUNNER__" & Chr(34) & args & Chr(34)
sh.Run cmdLine, 0, False
"""


def build_windows_context_menu(exe_path: str, bin_dir: str) -> dict:
    """Pure builder for the Windows flat 'Combine into PDF' verb.

    Returns {"files": {path: content}, "entries": [(key, name, value)]}
    where key is a HKCU-relative path and name None means the key's
    (default) value. The flat verb complements the grouped cascading
    menu installed by scripts/register-context-menu.ps1: it does not
    depend on ExtendedSubCommandsKey, so the merge entry always exists
    (Windows 11 shows legacy verbs under 'Show more options').
    """
    exe_path = str(exe_path)
    bin_dir = str(bin_dir)
    gui_exe = bin_dir + "\\jpg2pdf-gui.exe"
    runner = bin_dir + "\\jpg2pdf-selected-runner.cmd"
    launcher = bin_dir + "\\jpg2pdf-selected-launcher.vbs"
    files = {
        runner: _CTX_RUNNER_CMD.replace("__EXE__", exe_path)
                               .replace("__GUI_EXE__", gui_exe),
        launcher: _CTX_LAUNCHER_VBS.replace("__RUNNER__", runner),
    }
    entries = []

    def add_verb(root, command, applies_to=""):
        base = root + "\\Jpg2PdfMerge"
        entries.append((base, None, CTX_FLAT_LABEL))
        entries.append((base, "MUIVerb", CTX_FLAT_LABEL))
        entries.append((base, "Icon", exe_path))
        entries.append((base, "MultiSelectModel", "Player"))
        if applies_to:
            entries.append((base, "AppliesTo", applies_to))
        entries.append((base + "\\command", None, command))

    applies = " OR ".join(f"System.FileExtension:={ext}" for ext in CTX_EXTS)
    selected_cmd = (f'wscript.exe "{launcher}" "a4" "--size a4" "%1"')
    add_verb(r"Software\Classes\*\shell", selected_cmd, applies)
    for ext in CTX_EXTS:
        add_verb(rf"Software\Classes\SystemFileAssociations\{ext}\shell",
                 selected_cmd)
    folder_cmd = f'"{exe_path}" --size a4 "%V"'
    add_verb(r"Software\Classes\Directory\shell", folder_cmd)
    add_verb(r"Software\Classes\Directory\Background\shell", folder_cmd)
    return {"files": files, "entries": entries}


def _win_delete_tree(root_handle, path: str) -> None:
    import winreg
    try:
        key = winreg.OpenKey(root_handle, path, 0, winreg.KEY_ALL_ACCESS)
    except OSError:
        return
    while True:
        try:
            sub = winreg.EnumKey(key, 0)
        except OSError:
            break
        _win_delete_tree(root_handle, path + "\\" + sub)
    key.Close()
    winreg.DeleteKey(root_handle, path)


# ----- macOS -----

def _macos_workflow_files(label: str, verb_args: str, command: str) -> dict:
    """Contents of one Finder Quick Action .workflow bundle."""
    from xml.sax.saxutils import escape as _xml_escape
    import shlex as _shlex
    shell_lines = [
        'list="$(mktemp -t jpg2pdf-qa)"',
        'for f in "$@"; do printf \'%s\\n\' "$f" >> "$list"; done',
        f"{_shell_command(command)} {verb_args} --files-from \"$list\"",
        "rc=$?",
        'rm -f "$list" 2>/dev/null || true',
        "exit $rc",
    ]
    command_string = _xml_escape("\n".join(shell_lines))
    info_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>NSServices</key>
  <array>
    <dict>
      <key>NSMenuItem</key>
      <dict><key>default</key><string>{label}</string></dict>
      <key>NSMessage</key><string>runWorkflowAsService</string>
      <key>NSRequiredContext</key>
      <dict><key>NSApplicationIdentifier</key><string>com.apple.finder</string></dict>
      <key>NSSendFileTypes</key>
      <array>
        <string>public.image</string>
        <string>com.adobe.pdf</string>
        <string>public.html</string>
        <string>org.openxmlformats.wordprocessingml.document</string>
        <string>com.microsoft.word.doc</string>
      </array>
    </dict>
  </array>
</dict>
</plist>
"""
    wflow = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>AMApplicationBuild</key><string>523</string>
  <key>AMApplicationVersion</key><string>2.10</string>
  <key>AMDocumentVersion</key><string>2</string>
  <key>actions</key>
  <array>
    <dict>
      <key>action</key>
      <dict>
        <key>AMAccepts</key>
        <dict>
          <key>Container</key><string>List</string>
          <key>Optional</key><false/>
          <key>Types</key><array><string>com.apple.cocoa.path</string></array>
        </dict>
        <key>AMActionVersion</key><string>2.0.3</string>
        <key>AMApplication</key><array><string>Automator</string></array>
        <key>AMParameterProperties</key>
        <dict>
          <key>COMMAND_STRING</key><dict/>
          <key>CheckedForUserDefaultShell</key><dict/>
          <key>inputMethod</key><dict/>
          <key>shell</key><dict/>
          <key>source</key><dict/>
        </dict>
        <key>AMProvides</key>
        <dict>
          <key>Container</key><string>List</string>
          <key>Types</key><array><string>com.apple.cocoa.string</string></array>
        </dict>
        <key>ActionBundlePath</key><string>/System/Library/Automator/Run Shell Script.action</string>
        <key>ActionName</key><string>Run Shell Script</string>
        <key>ActionParameters</key>
        <dict>
          <key>COMMAND_STRING</key>
          <string>{command_string}</string>
          <key>CheckedForUserDefaultShell</key><true/>
          <key>inputMethod</key><integer>1</integer>
          <key>shell</key><string>/bin/bash</string>
          <key>source</key><string></string>
        </dict>
        <key>BundleIdentifier</key><string>com.apple.RunShellScript</string>
        <key>CFBundleVersion</key><string>2.0.3</string>
        <key>CanShowSelectedItemsWhenRun</key><false/>
        <key>CanShowWhenRun</key><true/>
        <key>Category</key><array><string>AMCategoryUtilities</string></array>
        <key>Class Name</key><string>RunShellScriptAction</string>
        <key>InputUUID</key><string>00000000-0000-0000-0000-000000000001</string>
        <key>Keywords</key><array><string>Shell</string></array>
        <key>OutputUUID</key><string>00000000-0000-0000-0000-000000000002</string>
        <key>UUID</key><string>00000000-0000-0000-0000-000000000003</string>
        <key>UnlocalizedApplications</key><array><string>Automator</string></array>
        <key>isViewVisible</key><true/>
      </dict>
      <key>isViewVisible</key><true/>
    </dict>
  </array>
  <key>connectors</key><dict/>
  <key>workflowMetaData</key>
  <dict>
    <key>serviceInputTypeIdentifier</key><string>com.apple.Automator.fileSystemObject</string>
    <key>serviceOutputTypeIdentifier</key><string>com.apple.Automator.nothing</string>
    <key>serviceProcessesInput</key><integer>0</integer>
    <key>workflowTypeIdentifier</key><string>com.apple.Automator.servicesMenu</string>
  </dict>
</dict>
</plist>
"""
    return {"Info.plist": info_plist, "document.wflow": wflow}


def build_macos_context_menu(home, command: str) -> dict:
    """Pure builder: {absolute path: content} for Finder Quick Actions."""
    home = Path(home)
    files = {}
    for _verb_id, label, verb_args in CTX_VERBS:
        wf = _macos_workflow_files(label, verb_args, command)
        base = home / "Library" / "Services" / f"{label}.workflow" / "Contents"
        files[str(base / "Info.plist")] = wf["Info.plist"]
        files[str(base / "document.wflow")] = wf["document.wflow"]
    return files


# ----- Linux -----

def build_linux_context_menu(home, command: str) -> dict:
    """Pure builder: {absolute path: {"content", "executable"}}.

    Covers GNOME Files (Nautilus scripts), Cinnamon Nemo actions and
    the KDE Dolphin servicemenu. Thunar is handled separately because
    its actions merge into an existing uca.xml (see thunar helpers).
    All Exec lines pass the selection via --files -- the pre-v2.3.0
    Dolphin entry passed files as bare positionals, which the old
    single-positional CLI rejected with exit code 2.
    """
    home = Path(home)
    files = {}
    quoted = _shell_command(command)
    for _verb_id, label, verb_args in CTX_VERBS:
        naut_path = (home / ".local" / "share" / "nautilus" / "scripts"
                     / f"jpg2pdf - {label}")
        naut = ("#!/usr/bin/env bash\n"
                "set -e\n"
                'list="$(mktemp -t jpg2pdf-naut.XXXXXX)"\n'
                "printf '%s\\n' \"$NAUTILUS_SCRIPT_SELECTED_FILE_PATHS\""
                " | sed '/^$/d' > \"$list\"\n"
                "[ -s \"$list\" ] || exit 0\n"
                f"{quoted} {verb_args} --files-from \"$list\"\n"
                "rc=$?\n"
                'rm -f "$list" 2>/dev/null || true\n'
                "exit $rc\n")
        files[str(naut_path)] = {"content": naut, "executable": True}
        nemo_path = (home / ".local" / "share" / "nemo" / "actions"
                     / f"jpg2pdf-{_verb_id}.nemo_action")
        nemo = ("[Nemo Action]\n"
                f"Name={label}\n"
                "Comment=Merge selected files into one PDF with jpg2pdf\n"
                f"Exec={_desktop_exec(command, verb_args + ' --files %F')}\n"
                "Icon-Name=application-pdf\n"
                "Selection=Any\n"
                "Extensions=" + ";".join(e.lstrip(".") for e in CTX_EXTS)
                + ";\n")
        files[str(nemo_path)] = {"content": nemo, "executable": False}
    kde_path = (home / ".local" / "share" / "kio" / "servicemenus"
                / "jpg2pdf.desktop")
    kde_lines = [
        "[Desktop Entry]",
        "Type=Service",
        "ServiceTypes=KonqPopupMenu/Plugin",
        "MimeType=image/jpeg;image/png;image/webp;image/tiff;image/bmp;"
        "application/pdf;text/html;"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document;"
        "application/msword;",
        "Actions=" + ";".join(f"Jpg2Pdf{_i}" for _i, _ in enumerate(CTX_VERBS))
        + ";",
        "X-KDE-Submenu=Combine into PDF",
        "Icon=application-pdf",
        "X-KDE-Priority=TopLevel",
        "",
    ]
    for i, (_verb_id, label, verb_args) in enumerate(CTX_VERBS):
        short = label.replace("Combine into PDF ", "").strip("()")
        kde_lines += [
            f"[Desktop Action Jpg2Pdf{i}]",
            f"Name={short}",
            "Icon=application-pdf",
            f"Exec={_desktop_exec(command, verb_args + ' --files %F')}",
            "",
        ]
    files[str(kde_path)] = {"content": "\n".join(kde_lines),
                            "executable": False}
    return files


def thunar_actions(command: str) -> list:
    """Thunar custom-action definitions (merged into uca.xml)."""
    patterns = ";".join("*" + ext for ext in CTX_EXTS)
    actions = []
    for verb_id, label, verb_args in CTX_VERBS:
        actions.append({
            "name": label,
            "unique-id": f"jpg2pdf-{verb_id}-1690000000",
            "command": _desktop_exec(command, verb_args + " --files %F"),
            "description": "Merge selected files into one PDF with jpg2pdf",
            "patterns": patterns,
        })
    return actions


def _thunar_uca_path(home) -> Path:
    return Path(home) / ".config" / "Thunar" / "uca.xml"


def _install_thunar(home, command: str) -> str:
    import xml.etree.ElementTree as _et
    path = _thunar_uca_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        try:
            tree = _et.parse(path)
            root = tree.getroot()
        except Exception:
            root = _et.Element("actions")
            tree = _et.ElementTree(root)
    else:
        root = _et.Element("actions")
        tree = _et.ElementTree(root)
    ours = {a["name"] for a in thunar_actions(command)}
    for child in list(root):
        if child.tag == "action":
            name_el = child.find("name")
            if name_el is not None and name_el.text in ours:
                root.remove(child)
    for spec in thunar_actions(command):
        action = _et.SubElement(root, "action")
        _et.SubElement(action, "icon").text = "application-pdf"
        _et.SubElement(action, "name").text = spec["name"]
        _et.SubElement(action, "unique-id").text = spec["unique-id"]
        _et.SubElement(action, "command").text = spec["command"]
        _et.SubElement(action, "description").text = spec["description"]
        _et.SubElement(action, "patterns").text = spec["patterns"]
        _et.SubElement(action, "image-files")
        _et.SubElement(action, "text-files")
        _et.SubElement(action, "other-files")
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return str(path)


def _uninstall_thunar(home) -> str:
    import xml.etree.ElementTree as _et
    path = _thunar_uca_path(home)
    if not path.is_file():
        return str(path)
    try:
        tree = _et.parse(path)
        root = tree.getroot()
    except Exception:
        return str(path)
    ours = {label for _i, label, _a in CTX_VERBS}
    for child in list(root):
        if child.tag == "action":
            name_el = child.find("name")
            if name_el is not None and name_el.text in ours:
                root.remove(child)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return str(path)


# ----- Apply / remove -----

def install_context_menu(platform=None, home=None, command=None) -> list:
    """Register right-click 'Combine into PDF' entries for this OS.

    Returns the list of files/keys written. Safe to re-run: existing
    entries are replaced.
    """
    plat = _ctx_platform(platform)
    cmd = _ctx_self_command(command)
    written = []
    if plat == "windows":
        exe = cmd
        bin_dir = (exe.rsplit("\\", 1)[0] if "\\" in exe
                   else str(Path(exe).parent))
        plan = build_windows_context_menu(exe, bin_dir)
        if sys.platform.startswith("win"):
            for fpath, content in plan["files"].items():
                p = Path(fpath)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="ascii")
                written.append(fpath)
        else:
            # Cross-platform dry surface: builders are what tests verify;
            # never write Windows-named files onto a non-Windows disk.
            written.extend(plan["files"])
        if sys.platform.startswith("win"):
            import winreg
            for key_path, name, value in plan["entries"]:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
                try:
                    if name is None:
                        winreg.SetValue(key, "", winreg.REG_SZ, value)
                    else:
                        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
                finally:
                    key.Close()
                written.append("HKCU\\" + key_path)
        else:
            written.extend("HKCU\\" + k for k, _n, _v in plan["entries"])
        return written
    home_p = Path(home) if home else Path.home()
    if plat == "macos":
        files = build_macos_context_menu(home_p, cmd)
        for fpath, content in files.items():
            p = Path(fpath)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            written.append(fpath)
        if sys.platform == "darwin":
            subprocess.run(["/System/Library/CoreServices/pbs", "-flush"],
                           capture_output=True)
        return written
    files = build_linux_context_menu(home_p, cmd)
    for fpath, spec in files.items():
        p = Path(fpath)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(spec["content"], encoding="utf-8")
        if spec["executable"]:
            p.chmod(0o755)
        written.append(fpath)
    written.append(_install_thunar(home_p, cmd))
    return written


def uninstall_context_menu(platform=None, home=None, command=None) -> list:
    """Remove the entries written by install_context_menu."""
    plat = _ctx_platform(platform)
    cmd = _ctx_self_command(command)
    removed = []
    if plat == "windows":
        exe = cmd
        bin_dir = (exe.rsplit("\\", 1)[0] if "\\" in exe
                   else str(Path(exe).parent))
        plan = build_windows_context_menu(exe, bin_dir)
        for fpath in plan["files"]:
            p = Path(fpath)
            if p.is_file():
                p.unlink()
            removed.append(fpath)
        if sys.platform.startswith("win"):
            roots = set()
            for key_path, _n, _v in plan["entries"]:
                if key_path.endswith("\\Jpg2PdfMerge"):
                    roots.add(key_path)
            import winreg
            for key_path in sorted(roots, reverse=True):
                _win_delete_tree(winreg.HKEY_CURRENT_USER, key_path)
                removed.append("HKCU\\" + key_path)
        return removed
    home_p = Path(home) if home else Path.home()
    if plat == "macos":
        for _verb_id, label, _args in CTX_VERBS:
            wf = home_p / "Library" / "Services" / f"{label}.workflow"
            if wf.is_dir():
                shutil.rmtree(wf)
            removed.append(str(wf))
        if sys.platform == "darwin":
            subprocess.run(["/System/Library/CoreServices/pbs", "-flush"],
                           capture_output=True)
        return removed
    files = build_linux_context_menu(home_p, cmd)
    for fpath in files:
        p = Path(fpath)
        if p.is_file():
            p.unlink()
        removed.append(fpath)
    removed.append(_uninstall_thunar(home_p))
    return removed


def apply_pencil(im: Image.Image, opacity: float, brightness: float,
                 ink_threshold: int = 110, ink_darken: float = 0.45) -> Image.Image:
    """Render the image as crisp pencil writing on clean paper.

    Pipeline:
      1. Flatten onto white (kill any alpha haze) and convert to grayscale
         using luminance -- picks up colored ink/text as well as black.
      2. Auto-stretch the histogram (1% / 99%) so a slightly grey scan is
         pulled to true white-paper range before the LUT runs. This is the
         single biggest quality win versus a naive contrast curve.
      3. Unsharp-mask to recover stroke crispness (graphite edges) before
         we flatten tones.
      4. Smoothstep LUT: anything darker than `dark_point` is treated as
         pure ink (multiplied by `ink_darken` so it stays solid black),
         anything lighter than `light_point` snaps to paper white, and the
         band between them gets an anti-aliased ramp so small text edges
         don't break up.

    opacity:    how aggressive the paper-whitening is (0..1).
                Lower  -> wider whitening band, cleaner page.
                Default 0.25 -> light_point ~= 215, dark_point ~= 70.
    brightness: post brightness multiplier (1.0 = none).
    ink_threshold: pixel value (0..255) that defines "definitely ink".
                   Pixels at or below get the full ink_darken treatment.
    ink_darken: ink multiplier (<1 makes ink blacker; default 0.55).
    """
    opacity    = max(0.0, min(1.0, opacity))
    brightness = max(0.1, brightness)
    ink_darken = max(0.05, min(1.0, ink_darken))

    # 1. Flatten alpha -> white, then luminance-grayscale.
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
        im = bg
    gray = im.convert("L")
    raw_gray = gray

    # 2a. Background flattening -- divide by a heavily-blurred copy of the page
    # to remove uneven lighting / shadow gradients from phone photos. This is
    # the key trick that makes faint pencil pop: paper goes uniformly white,
    # so the LUT below has more room to darken the actual strokes.
    bg_blur = gray.filter(ImageFilter.GaussianBlur(radius=max(gray.size) / 30))
    from PIL import ImageMath
    _eval = getattr(ImageMath, "unsafe_eval", None) or ImageMath.eval
    # Avoid div-by-zero by lifting bg floor to 1 via point().
    bg_safe = bg_blur.point(lambda v: max(v, 1))
    gray = _eval(
        "convert(float(a) * 255.0 / float(b), 'L')",  # convert('L') saturates to 0..255
        a=gray, b=bg_safe,
    )

    # 2a.1 Stroke-lift mask -- recover very faint graphite/text before the
    # histogram stretch can wash it away.  We compare the original pixels with
    # the local paper background; anything slightly darker than nearby paper is
    # amplified into a subtraction mask.  This gives pencil writing actual
    # depth while leaving flat white paper alone.
    depth = max(0.0, min(1.0, (ink_threshold - 90) / 75.0))
    stroke_lift = ImageChops.subtract(bg_blur, raw_gray)
    stroke_lift = ImageEnhance.Contrast(stroke_lift).enhance(1.8 + 2.6 * depth)
    lift_floor = 3 if depth < 0.45 else 2
    lift_gain = 3.2 + 4.8 * depth
    stroke_lift = stroke_lift.point(
        lambda v: 0 if v <= lift_floor else min(255, int(round((v - lift_floor) * lift_gain)))
    )
    lifted = ImageChops.subtract(gray, stroke_lift.point(lambda v: int(round(v * (0.42 + 0.38 * depth)))))
    gray = Image.blend(gray, lifted, 0.28 + 0.42 * depth)

    # 2b. Auto-level (stretch 1%..99% to 0..255) so dingy scans go truly white.
    gray = ImageOps.autocontrast(gray, cutoff=(1, 1))

    # 3. Edge sharpening -- recovers crisp pencil-stroke contours.
    gray = gray.filter(ImageFilter.UnsharpMask(radius=1.4, percent=180, threshold=2))

    # 3b. Stroke-depth pass. A small MinFilter expands only dark strokes, then
    # blends them back into the original so faint pencil/text gains body without
    # turning the paper grey. Stronger presets raise ink_threshold, which also
    # increases this depth pass.
    gray = ImageEnhance.Contrast(gray).enhance(1.08 + 0.20 * depth)
    stroke_shadow = gray.filter(ImageFilter.MinFilter(3))
    if depth > 0.55:
        wider_shadow = gray.filter(ImageFilter.MinFilter(5))
        stroke_shadow = Image.blend(stroke_shadow, wider_shadow, 0.10 + 0.18 * depth)
    gray = Image.blend(gray, stroke_shadow, 0.18 + 0.30 * depth)

    # 3c. Gamma > 1 darkens midtones -- pulls grey graphite toward black without
    # crushing paper (paper is already near 255 from the flatten step).
    gamma = 1.12 + 0.30 * depth
    gamma_lut = [int(round(((v / 255.0) ** gamma) * 255)) for v in range(256)]
    gray = gray.point(gamma_lut)

    # 4. Smoothstep LUT.
    dark_point  = max(0,   min(200, ink_threshold - 20))   # full-ink boundary
    light_point = max(dark_point + 10,
                      int(round(255 - 40 * opacity)))      # paper-white boundary
                                                            # opacity 0 -> 255, opacity 1 -> 215
    span = max(1, light_point - dark_point)

    lut = []
    for v in range(256):
        if v <= dark_point:
            # Solid ink: darken aggressively so writing reads jet black.
            out = int(round(v * ink_darken))
        elif v >= light_point:
            # Paper.
            out = 255
        else:
            # Smoothstep ramp ink -> paper.
            t = (v - dark_point) / span
            s = t * t * (3 - 2 * t)                        # smoothstep
            ink_val   = v * ink_darken
            paper_val = 255
            out = int(round(ink_val + (paper_val - ink_val) * s))
        lut.append(max(0, min(255, out)))

    gray = gray.point(lut)

    if brightness != 1.0:
        gray = ImageEnhance.Brightness(gray).enhance(brightness)

    return gray.convert("RGB")


def make_page(img_path: Path, page_w_pt: float, page_h_pt: float,
              fit: str, dpi: int, auto_rotate: str, rotate: int,
              style: str = "none",
              pencil_opacity: float = 0.25,
              pencil_brightness: float = 1.0,
              pencil_ink_threshold: int = 90,
              pencil_ink_darken: float = 0.55) -> Image.Image:
    """Render one PDF page at `dpi` DPI.

    rotate:      extra rotation applied to every image (0/90/180/270, CCW).
    auto_rotate: 'cw'  -> rotate landscape images 90 deg clockwise to fit portrait page
                 'ccw' -> rotate 90 deg counter-clockwise
                 'off' -> never auto-rotate
    style:       'none' (default) or 'pencil' (text/dark strokes stay black,
                 paper & mid-tones fade out).
    """
    with Image.open(img_path) as im:
        im = im.convert("RGB")

        if rotate:
            im = im.rotate(rotate, expand=True)

        iw, ih = im.size
        if auto_rotate != "off":
            img_landscape  = iw > ih
            page_landscape = page_w_pt > page_h_pt
            if img_landscape != page_landscape:
                # PIL rotates CCW with positive angle.
                angle = 90 if auto_rotate == "ccw" else -90
                im = im.rotate(angle, expand=True)
                iw, ih = im.size

        if style == "pencil":
            im = apply_pencil(im, pencil_opacity, pencil_brightness,
                              ink_threshold=pencil_ink_threshold,
                              ink_darken=pencil_ink_darken)

        scale = dpi / 72.0
        canvas_w = max(1, int(round(page_w_pt * scale)))
        canvas_h = max(1, int(round(page_h_pt * scale)))

        if fit == "original":
            new_w, new_h = iw, ih
        elif fit == "stretch":
            new_w, new_h = canvas_w, canvas_h
        elif fit == "cover":
            s = max(canvas_w / iw, canvas_h / ih)
            new_w, new_h = int(round(iw * s)), int(round(ih * s))
        else:  # contain
            s = min(canvas_w / iw, canvas_h / ih)
            new_w, new_h = int(round(iw * s)), int(round(ih * s))

        if (new_w, new_h) != (iw, ih):
            im = im.resize((new_w, new_h), Image.LANCZOS)

        page = Image.new("RGB", (canvas_w, canvas_h), "white")
        x = (canvas_w - new_w) // 2
        y = (canvas_h - new_h) // 2
        page.paste(im, (x, y))
        return page


def stack_images_to_image(image_paths, out_path: Path, *,
                          direction: str = "vertical",
                          rotate: int = 0,
                          auto_rotate: str = "off",
                          style: str = "none",
                          pencil_opacity: float = 0.25,
                          pencil_brightness: float = 1.0,
                          pencil_ink_threshold: int = 110,
                          pencil_ink_darken: float = 0.45) -> Path:
    """Stack image inputs into a single image file (PNG or JPG).

    All images are normalised to a common width (vertical stack) or a
    common height (horizontal stack) using the largest dimension across
    the batch, then composited onto a white canvas in the given order.
    Honors --rotate / --auto-rotate / --style pencil exactly like the
    PDF pipeline.
    """
    if not image_paths:
        raise ValueError("stack_images_to_image: no images to stack")

    frames: list[Image.Image] = []
    for p in image_paths:
        im = Image.open(p)
        try:
            im = ImageOps.exif_transpose(im)
        except Exception:
            pass
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        if rotate:
            im = im.rotate(rotate, expand=True)
        if auto_rotate in ("cw", "ccw"):
            # Match the PDF path: rotate landscape into portrait orientation.
            if im.width > im.height:
                im = im.rotate(-90 if auto_rotate == "cw" else 90, expand=True)
        if style == "pencil":
            im = apply_pencil(im, opacity=pencil_opacity,
                              brightness=pencil_brightness,
                              ink_threshold=pencil_ink_threshold,
                              ink_darken=pencil_ink_darken)
            if im.mode != "RGB":
                im = im.convert("RGB")
        frames.append(im)

    if direction == "horizontal":
        target_h = max(f.height for f in frames)
        resized = []
        for f in frames:
            if f.height != target_h:
                new_w = max(1, int(round(f.width * target_h / f.height)))
                f = f.resize((new_w, target_h), Image.LANCZOS)
            resized.append(f)
        total_w = sum(f.width for f in resized)
        canvas = Image.new("RGB", (total_w, target_h), "white")
        x = 0
        for f in resized:
            canvas.paste(f, (x, 0)); x += f.width
    else:
        target_w = max(f.width for f in frames)
        resized = []
        for f in frames:
            if f.width != target_w:
                new_h = max(1, int(round(f.height * target_w / f.width)))
                f = f.resize((target_w, new_h), Image.LANCZOS)
            resized.append(f)
        total_h = sum(f.height for f in resized)
        canvas = Image.new("RGB", (target_w, total_h), "white")
        y = 0
        for f in resized:
            canvas.paste(f, (0, y)); y += f.height

    out_path.parent.mkdir(parents=True, exist_ok=True)
    ext = out_path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        canvas.save(out_path, "JPEG", quality=92, optimize=True)
    else:
        canvas.save(out_path, "PNG", optimize=True)
    return out_path


def main():
    ap = argparse.ArgumentParser(
        description="Combine images into a single PDF.")
    ap.add_argument("--version", action="version",
                    version=f"jpg2pdf {__version__}")
    ap.add_argument("--gui", action="store_true",
                    help="Launch the desktop GUI instead of running a CLI "
                         "conversion. All other flags are ignored.")
    ap.add_argument("--install-context-menu", action="store_true",
                    help="Register right-click 'Combine into PDF' entries "
                         "for this OS (Windows Explorer, macOS Finder, "
                         "Linux file managers) and exit. The entries call "
                         "this binary, so they always match its version.")
    ap.add_argument("--uninstall-context-menu", action="store_true",
                    help="Remove the right-click entries installed by "
                         "--install-context-menu and exit.")
    ap.add_argument("paths", nargs="*", default=None,
                    help="A folder (merge everything inside it), or one or "
                         "more files to merge in the given order -- the form "
                         "file managers pass with %F / %* (omit if using "
                         "--files / --files-from / --youtube)")
    ap.add_argument("--files", nargs="+", default=None,
                    help="Explicit list of image files (preserves order)")
    ap.add_argument("--files-from", default=None,
                    help="Text file with one image path per line (UTF-8)")
    ap.add_argument("--youtube", nargs="+", default=None,
                    help="One or more YouTube URLs or video IDs to download thumbnails from")
    ap.add_argument("--open-dir", action="store_true",
                    help="Open output/thumbnail directory in native file explorer after processing")
    ap.add_argument("--download-only", action="store_true",
                    help="Download YouTube thumbnails without converting to PDF or image")
    ap.add_argument("--size", choices=list(PAGE_SIZES), default="a4")
    ap.add_argument("--orientation",
                    choices=["portrait", "landscape"], default="portrait")
    ap.add_argument("--fit",
                    choices=["contain", "cover", "stretch", "original"],
                    default="contain")
    ap.add_argument("--out", default=None,
                    help="Explicit output PDF path (overrides --name-pattern)")
    ap.add_argument("--name-pattern", default=None,
                    help="Pattern for the auto-generated PDF filename when "
                         "--out isn't given. Placeholders: "
                         "{folder} {first} {count} {style} {strength} "
                         "{date} {time} {datetime} {y} {m} {d} {hh} {mm} {ss}. "
                         "Examples: '{folder}', '{folder}_{date}', "
                         "'{folder}-{count}p-{datetime}', "
                         "'{first}_{strength}'. Saved as your default after "
                         "each run (in ~/.jpg2pdf/config.json).")
    ap.add_argument("--recursive", action="store_true",
                    help="Folder mode: include subfolders")
    ap.add_argument("--dpi", type=int, default=300,
                    help="Render DPI for embedded raster (default: 300)")
    ap.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], default=0,
                    help="Rotate every image by N degrees CCW before fitting")
    ap.add_argument("--auto-rotate", choices=["cw", "ccw", "off"], default="cw",
                    help="Auto-rotate landscape images to fit portrait page "
                         "(cw = clockwise, default; ccw = counter-clockwise; off)")
    ap.add_argument("--no-auto-rotate", action="store_true",
                    help="Shortcut for --auto-rotate off")
    ap.add_argument("--style", choices=["none", "pencil"], default="none",
                    help="Rendering style. 'pencil' = pencil-on-paper look "
                         "(text/dark strokes stay black, paper & mid-tones fade out)")
    ap.add_argument("--pencil-strength",
                    choices=["subtle", "normal", "extra"], default=None,
                    help="Pencil preset for faint text: "
                         "'subtle' (default, gentle, keeps paper texture), "
                         "'normal' (balanced ink + paper grain), "
                         "'extra' (extra-visible -- aggressive darkening for very faint pencil). "
                         "Defaults to your last chosen value (saved in "
                         "~/.jpg2pdf/config.json), or 'subtle' on first run. "
                         "Individual --pencil-* flags override the preset.")
    ap.add_argument("--pencil-opacity", type=float, default=None,
                    help="Pencil style: how much non-ink survives (0..1, default 0.25). "
                         "Lower = whiter paper.")
    ap.add_argument("--pencil-ink-threshold", type=int, default=None,
                    help="Pencil style: pixel value (0..255) below which a pixel is "
                         "treated as ink and kept dark.")
    ap.add_argument("--pencil-ink-darken", type=float, default=None,
                    help="Pencil style: ink multiplier (<1 makes ink blacker).")
    ap.add_argument("--pencil-brightness", type=float, default=None,
                    help="Pencil style: post-process brightness multiplier (default 1.0).")
    ap.add_argument("--ask-strength", action="store_true",
                    help="When --style pencil, show a desktop dropdown to pick "
                         "subtle/normal/extra before converting.")
    ap.add_argument("--reset-prefs", action="store_true",
                    help="Forget the saved pencil-strength preference and exit.")
    ap.add_argument("--preview-grid", action="store_true",
                    help="Before converting, open a scrollable thumbnail grid "
                         "so you can confirm / deselect images. Cancel aborts "
                         "the run; uncheck any image to skip it.")
    ap.add_argument("--thumb-size", type=int, default=140,
                    help="--preview-grid: max thumbnail edge in pixels (default 140).")
    ap.add_argument("--thumb-cols", type=int, default=4,
                    help="--preview-grid: number of columns (default 4).")
    ap.add_argument("--output-mode",
                    choices=["pdf", "image", "pencil-pdf", "pencil-image"],
                    default="pdf",
                    help="'pdf' (default) merges inputs into one PDF. "
                         "'image' stacks image inputs into a single PNG/JPG "
                         "(non-image inputs are skipped with a warning). "
                         "'pencil-pdf' = pdf + --style pencil. "
                         "'pencil-image' = image stack + --style pencil. "
                         "The pencil aliases force --style pencil regardless "
                         "of --style.")
    ap.add_argument("--stack", choices=["vertical", "horizontal"],
                    default="vertical",
                    help="--output-mode image: stacking direction "
                         "(default: vertical).")
    ap.add_argument("--sort",
                    choices=["selection", "name", "date", "folder", "auto"],
                    default="auto",
                    help="Ordering of inputs before merging/stacking. "
                         "'auto' (default) = 'selection' for --files / "
                         "--files-from, 'name' for folder mode. "
                         "'name' = natural filename sort. "
                         "'date' = file mtime ascending. "
                         "'folder' = preserve OS folder enumeration order.")
    args = ap.parse_args()

    # --install/--uninstall-context-menu: register file-manager
    # integration for this OS, then exit (no conversion happens).
    if args.install_context_menu:
        for item in install_context_menu():
            print(f"  installed: {item}")
        print("Context menu installed. On Windows 11, look under "
              "'Show more options' when you right-click.")
        return
    if args.uninstall_context_menu:
        for item in uninstall_context_menu():
            print(f"  removed: {item}")
        print("Context menu removed.")
        return

    # --gui short-circuits the CLI and hands control to the Tk shell.
    if args.gui:
        # Local import: only needed in GUI mode, and keeps Tk out of
        # headless server runs.
        from pathlib import Path as _Path
        import sys as _sys
        _pkg_parent = _Path(__file__).resolve().parent
        if str(_pkg_parent) not in _sys.path:
            _sys.path.insert(0, str(_pkg_parent))
        # Gather any paths the caller passed so the context-menu "Open in
        # jpg2pdf UI..." entry pre-loads the selection into the drop zone.
        initial_paths: list[str] = []
        if args.files_from:
            try:
                _lf = _Path(args.files_from).expanduser().resolve()
                for ln in _lf.read_text(encoding="utf-8").splitlines():
                    s = ln.strip()
                    if s and not s.startswith("#"):
                        initial_paths.append(s)
            except OSError:
                pass
        if args.files:
            initial_paths.extend(args.files)
        if args.paths:
            initial_paths.extend(args.paths)
        from jpg2pdf_app.gui import run as _gui_run
        sys.exit(_gui_run(initial_paths=initial_paths or None))

    # Expand pencil-* aliases into base output-mode + style.
    if args.output_mode == "pencil-pdf":
        args.output_mode = "pdf"
        args.style = "pencil"
    elif args.output_mode == "pencil-image":
        args.output_mode = "image"
        args.style = "pencil"

    # Load persisted prefs (last chosen pencil strength).
    prefs = load_prefs()
    if args.reset_prefs:
        try:
            CONFIG_PATH.unlink()
            print(f"Removed {CONFIG_PATH}")
        except FileNotFoundError:
            print("No saved prefs to remove.")
        sys.exit(0)

    # Seed default from saved prefs (CLI value always wins).
    cli_strength_explicit = args.pencil_strength is not None
    if not cli_strength_explicit:
        args.pencil_strength = prefs.get("pencil_strength", "subtle")
        if args.pencil_strength not in PENCIL_PRESETS:
            args.pencil_strength = "subtle"

    # ---- Resolve input mode (BEFORE the strength picker so we can pass a
    # real sample image into the live preview) ----
    images = []
    out_dir = None       # where the PDF will be written
    folder_name = None   # used by {folder} in --name-pattern
    folder_path = None   # set in folder mode (drives --sort folder)
    input_mode = None    # "files" | "folder" (drives --sort auto)

    if args.youtube:
        yt_target_dir = None
        if args.out:
            p = Path(args.out).expanduser()
            if p.is_dir():
                yt_target_dir = p
            elif args.out.endswith(("/", "\\")):
                yt_target_dir = p
            else:
                yt_target_dir = p.parent
        elif args.paths:
            f = Path(args.paths[0]).expanduser()
            if f.is_dir():
                yt_target_dir = f

        if yt_target_dir is None:
            if get_default_thumbnail_dir:
                yt_target_dir = get_default_thumbnail_dir()

        if resolve_youtube_thumbnails:
            if yt_target_dir:
                yt_images = resolve_youtube_thumbnails(args.youtube, out_dir=yt_target_dir)
                images.extend(yt_images)
                out_dir = yt_target_dir
                folder_name = yt_target_dir.name
                input_mode = "files"

    if args.files_from:
        listfile = Path(args.files_from).expanduser().resolve()
        if not listfile.is_file():
            print(f"List file not found: {listfile}", file=sys.stderr)
            sys.exit(1)

        lines = [ln.strip() for ln in listfile.read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.strip().startswith("#")]
        images.extend(collect_from_list(lines))
        input_mode = "files"
        if not out_dir:
            if images:
                out_dir = images[0].parent
                folder_name = images[0].parent.name
    elif args.files:
        images.extend(collect_from_list(args.files))
        input_mode = "files"
        if not out_dir:
            if images:
                out_dir = images[0].parent
                folder_name = images[0].parent.name
    elif args.paths:
        first = Path(args.paths[0]).expanduser().resolve()
        if len(args.paths) == 1 and first.is_dir():
            folder_path = first
            images.extend(collect_from_folder(first, args.recursive))
            input_mode = "folder"
            if not out_dir:
                out_dir = first
                folder_name = first.name
        else:
            # Selection mode from positional arguments: the form file
            # managers use (KDE %F, Thunar/Nemo %F, scripts passing %*).
            # A folder among the paths expands to its contents.
            expanded = []
            for raw_path in args.paths:
                pp = Path(raw_path).expanduser().resolve()
                if pp.is_dir():
                    expanded.extend(
                        str(p) for p in collect_from_folder(pp, False))
                else:
                    expanded.append(str(pp))
            images.extend(collect_from_list(expanded))
            input_mode = "files"
            if not out_dir:
                if images:
                    out_dir = images[0].parent
                    folder_name = images[0].parent.name
    else:
        if not args.youtube:
            ap.error("Provide a folder or files, or --files, or "
                     "--files-from, or --youtube.")

    if not images:
        print("No images to convert.", file=sys.stderr)
        sys.exit(1)

    if args.download_only:
        if args.open_dir:
            if out_dir:
                if open_directory_in_explorer:
                    open_directory_in_explorer(out_dir)

        print(f"Downloaded {len(images)} thumbnail(s). Done.")

        return

    # ---- Apply --sort. 'auto' = selection for files, name for folder mode.
    resolved_sort = args.sort
    if resolved_sort == "auto":
        resolved_sort = "selection" if input_mode == "files" else "name"
    if resolved_sort == "name":
        images = sorted(images, key=natural_key)
    elif resolved_sort == "date":
        images = sorted(images, key=lambda p: p.stat().st_mtime)
    elif resolved_sort == "folder":
        # Preserve enumeration order. For folder mode, re-collect without the
        # implicit natural-sort done by collect_from_folder.
        if input_mode == "folder":
            folder_p = folder_path
            it = folder_p.rglob("*") if args.recursive else folder_p.iterdir()
            images = [p for p in it if p.is_file()
                      and p.suffix.lower() in SUPPORTED_EXTS]
        # For files mode, 'folder' is meaningless -- fall back to selection
        # order (which is what `images` already holds).
    # 'selection' -> leave images as-is.
    args._resolved_sort = resolved_sort


    # Optional: confirm/deselect images via thumbnail grid before conversion.
    if args.preview_grid:
        kept = prompt_thumbnail_grid(images,
                                     thumb_px=max(48, args.thumb_size),
                                     cols=max(1, args.thumb_cols))
        if kept is None:
            print("Cancelled by user.", file=sys.stderr); sys.exit(130)
        if not kept:
            print("No images selected -- nothing to convert.", file=sys.stderr); sys.exit(1)
        if len(kept) != len(images):
            print(f"  preview-grid: kept {len(kept)} of {len(images)} image(s)")
        images = kept

    # Interactive picker with LIVE preview (only meaningful with --style pencil)
    if args.ask_strength and args.style == "pencil":
        cli_overrode = any(v is not None for v in (
            args.pencil_opacity, args.pencil_ink_threshold,
            args.pencil_ink_darken, args.pencil_brightness))
        if not cli_overrode:
            args.pencil_strength = prompt_pencil_strength(
                args.pencil_strength, sample_path=images[0])

    # Persist the resolved strength so the NEXT export reuses it automatically.
    if args.style == "pencil" and args.pencil_strength in PENCIL_PRESETS:
        if prefs.get("pencil_strength") != args.pencil_strength:
            prefs["pencil_strength"] = args.pencil_strength
            save_prefs(prefs)

    # Apply preset (defined at module scope) for any --pencil-* flag the user
    # didn't override on the CLI.
    preset = PENCIL_PRESETS[args.pencil_strength]
    if args.pencil_opacity       is None: args.pencil_opacity       = preset["opacity"]
    if args.pencil_ink_threshold is None: args.pencil_ink_threshold = preset["ink_threshold"]
    if args.pencil_ink_darken    is None: args.pencil_ink_darken    = preset["ink_darken"]
    if args.pencil_brightness    is None: args.pencil_brightness    = preset["brightness"]

    w, h = PAGE_SIZES[args.size]
    if args.orientation == "landscape":
        w, h = h, w

    # Resolve output filename: explicit --out wins, else apply --name-pattern
    # (CLI > saved pref > built-in default), persist if user passed one.
    cli_pattern_explicit = args.name_pattern is not None
    if args.name_pattern is None:
        args.name_pattern = prefs.get("name_pattern", DEFAULT_NAME_PATTERN)

    out_ext = ".png" if args.output_mode == "image" else ".pdf"
    if args.out:
        out = Path(args.out).expanduser().resolve()
    else:
        base = format_pdf_name(
            args.name_pattern,
            folder_name=folder_name or "images",
            first_image=images[0],
            count=len(images),
            style=args.style,
            strength=args.pencil_strength,
        )
        out = (out_dir / f"{base}{out_ext}").resolve()

    if cli_pattern_explicit and prefs.get("name_pattern") != args.name_pattern:
        prefs["name_pattern"] = args.name_pattern
        save_prefs(prefs)

    auto_rot = "off" if args.no_auto_rotate else args.auto_rotate

    print(f"Files:    {len(images)}")
    print(f"Sort:     {args._resolved_sort}")
    print(f"Mode:     {args.output_mode}"
          + (f" ({args.stack} stack)" if args.output_mode == "image" else ""))
    if args.output_mode == "pdf":
        print(f"Page:     {args.size} {args.orientation} ({int(w)}x{int(h)} pt) @ {args.dpi} DPI")
        print(f"Fit:      {args.fit}  rotate: {args.rotate}  auto-rotate: {auto_rot}")
    if args.style == "pencil":
        print(f"Style:    pencil [{args.pencil_strength}] (opacity={args.pencil_opacity}, "
              f"ink<= {args.pencil_ink_threshold} *{args.pencil_ink_darken}, "
              f"brightness={args.pencil_brightness})")
    print(f"Output:   {out}")

    # Image-stacking output mode short-circuits the PDF pipeline.
    if args.output_mode == "image":
        image_only = [p for p in images if kind_of(p) == "image"]
        skipped = len(images) - len(image_only)
        if skipped:
            print(f"  image mode: skipped {skipped} non-image input(s)",
                  file=sys.stderr)
        if not image_only:
            print("No image inputs to stack.", file=sys.stderr); sys.exit(1)
        for k, ip in enumerate(image_only, 1):
            print(f"  [{k}/{len(image_only)}] image: {ip.name}")
        stack_images_to_image(
            image_only, out,
            direction=args.stack,
            rotate=args.rotate, auto_rotate=auto_rot,
            style=args.style,
            pencil_opacity=args.pencil_opacity,
            pencil_brightness=args.pencil_brightness,
            pencil_ink_threshold=args.pencil_ink_threshold,
            pencil_ink_darken=args.pencil_ink_darken,
        )
        if args.open_dir:
            if open_directory_in_explorer:
                open_directory_in_explorer(out.parent)

        print(f"Done -> {out}")

        return


    # Group consecutive inputs by kind so adjacent images become a single
    # image-PDF chunk (efficient + matches user's selection order).
    import tempfile
    with tempfile.TemporaryDirectory(prefix="jpg2pdf-") as td:
        tmp = Path(td)
        chunks = []          # list of Path to PDF chunks (in final order)
        chunk_idx = 0
        i = 0
        n = len(images)
        while i < n:
            p = images[i]
            kind = kind_of(p)
            if kind == "image":
                # Greedily collect consecutive images.
                j = i
                batch = []
                while j < n and kind_of(images[j]) == "image":
                    batch.append(images[j]); j += 1
                for k, ip in enumerate(batch, 1):
                    print(f"  [{i + k}/{n}] image: {ip.name}")
                chunk_idx += 1
                out_chunk = tmp / f"chunk_{chunk_idx:03d}_img.pdf"
                if images_to_pdf_chunk(
                        batch, out_chunk,
                        page_w_pt=w, page_h_pt=h, fit=args.fit, dpi=args.dpi,
                        auto_rotate=auto_rot, rotate=args.rotate,
                        style=args.style,
                        pencil_opacity=args.pencil_opacity,
                        pencil_brightness=args.pencil_brightness,
                        pencil_ink_threshold=args.pencil_ink_threshold,
                        pencil_ink_darken=args.pencil_ink_darken):
                    chunks.append(out_chunk)
                i = j
                continue

            print(f"  [{i + 1}/{n}] {kind}: {p.name}")
            chunk_idx += 1
            if kind == "pdf":
                chunks.append(p)  # use as-is
            elif kind == "html":
                out_chunk = tmp / f"chunk_{chunk_idx:03d}_html.pdf"
                if html_to_pdf(p, out_chunk):
                    chunks.append(out_chunk)
            elif kind == "word":
                out_chunk = tmp / f"chunk_{chunk_idx:03d}_word.pdf"
                if word_to_pdf(p, out_chunk):
                    chunks.append(out_chunk)
            else:
                print(f"  skip (unknown type): {p.name}", file=sys.stderr)
            i += 1

        if not chunks:
            print("Nothing was successfully converted.", file=sys.stderr)
            sys.exit(1)

        if len(chunks) == 1 and chunks[0].suffix.lower() == ".pdf":
            # Single PDF chunk (pre-existing or generated from images) -- copy directly.
            import shutil
            shutil.copyfile(chunks[0], out)
        else:
            merge_pdfs(chunks, out)

    if args.open_dir:
        if open_directory_in_explorer:
            open_directory_in_explorer(out.parent)

    print(f"Done -> {out}")


if __name__ == "__main__":
    main()

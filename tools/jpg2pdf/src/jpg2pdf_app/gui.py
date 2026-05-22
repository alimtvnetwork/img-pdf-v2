"""jpg2pdf GUI — Tkinter shell.

Steps 7-9 of the GUI roadmap (.lovable/plan.md): main window with menubar,
drag-and-drop drop zone, reorderable file list, options panel, and status
bar. Convert wiring (Step 10) lands in the next step.

Launch via:
    jpg2pdf --gui
    python -m jpg2pdf_app
"""

from __future__ import annotations

import os
import shlex
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from jpg2pdf_app.core import __version__
from jpg2pdf_app import settings as _settings


WINDOW_TITLE = f"jpg2pdf {__version__}"
DROP_ZONE_HINT = (
    "Drag files or folders here, or use 'Add files...' / 'Add folder...'.\n"
    "Supports images (jpg/png/webp/...), PDF, HTML, and Word documents."
)
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
KIND_BY_EXT = {
    **{e: "img" for e in IMAGE_EXTS},
    ".pdf": "pdf",
    ".html": "html", ".htm": "html",
    ".docx": "doc", ".doc": "doc",
}


def classify(path: str) -> str:
    p = Path(path)
    if p.is_dir():
        return "dir"
    return KIND_BY_EXT.get(p.suffix.lower(), "???")


def _try_load_dnd():
    """Return (Tk-class, DND_FILES-const) or (None, None) if unavailable."""
    try:
        from tkinterdnd2 import TkinterDnD, DND_FILES  # type: ignore
        return TkinterDnD.Tk, DND_FILES
    except Exception:
        return None, None


def _split_dnd_paths(raw: str) -> list[str]:
    """Parse the platform-dependent DnD payload into a list of paths.

    Windows / Linux: paths separated by spaces, with `{...}` quoting paths
    that contain spaces. macOS: simple whitespace-separated list.
    """
    if not raw:
        return []
    out: list[str] = []
    i = 0
    n = len(raw)
    while i < n:
        c = raw[i]
        if c.isspace():
            i += 1; continue
        if c == "{":
            j = raw.find("}", i + 1)
            if j == -1:
                out.append(raw[i + 1:]); break
            out.append(raw[i + 1:j]); i = j + 1
        else:
            j = i
            while j < n and not raw[j].isspace():
                j += 1
            out.append(raw[i:j]); i = j
    return out


class Jpg2PdfApp:
    """Top-level GUI controller. Owns the root window and all widgets."""

    def __init__(self, root: tk.Tk, dnd_const: str | None = None) -> None:
        self.root = root
        self.dnd_const = dnd_const
        self.root.title(WINDOW_TITLE)
        self.root.geometry("860x540")
        self.root.minsize(680, 440)

        self.inputs: list[str] = []   # ordered list of input paths

        # Load persisted preset (Step 17). Falls back to defaults on any error.
        self._settings = _settings.load()
        s = self._settings

        # Option state (read by Convert; persisted on close + after conversion).
        self.var_mode    = tk.StringVar(value=s.get("mode", "pdf"))
        self.var_sort    = tk.StringVar(value=s.get("sort", "auto"))
        self.var_size    = tk.StringVar(value=s.get("size", "a4"))
        self.var_orient  = tk.StringVar(value=s.get("orient", "portrait"))
        self.var_fit     = tk.StringVar(value=s.get("fit", "contain"))
        self.var_stack   = tk.StringVar(value=s.get("stack", "vertical"))
        self.var_pencil  = tk.BooleanVar(value=bool(s.get("pencil", False)))
        self.var_strength = tk.StringVar(value=s.get("strength", "subtle"))
        self.var_output  = tk.StringVar(value=s.get("output", ""))

        self._recent: list[str] = list(s.get("recent", []) or [])

        self._build_menubar()
        self._build_layout()
        self._refresh_list()
        if dnd_const:
            self._wire_dnd()
            self._set_status(f"Ready. jpg2pdf {__version__}. Drag files in.")
        else:
            self._set_status(
                f"Ready. jpg2pdf {__version__}. "
                "Install 'tkinterdnd2' for drag-and-drop.")

        # Persist preset + recent files when the window closes.
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ UI

    def _build_menubar(self) -> None:
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Add files...", command=self.on_add_files)
        file_menu.add_command(label="Add folder...", command=self.on_add_folder)
        file_menu.add_separator()
        self.recent_menu = tk.Menu(file_menu, tearoff=False)
        file_menu.add_cascade(label="Recent", menu=self.recent_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Clear list", command=self.on_clear)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        mode_menu = tk.Menu(menubar, tearoff=False)
        for label, value in (
            ("PDF",            "pdf"),
            ("Stacked Image",  "image"),
            ("Pencil PDF",     "pencil-pdf"),
            ("Pencil Image",   "pencil-image"),
        ):
            mode_menu.add_command(
                label=label,
                command=lambda v=value, l=label: self._set_output_mode(v, l))
        menubar.add_cascade(label="Mode", menu=mode_menu)


        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="About", command=self.on_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)
        self._refresh_recent_menu()

    # -------------------------------------------------------- recents/preset

    def _refresh_recent_menu(self) -> None:
        try:
            self.recent_menu.delete(0, tk.END)
        except Exception:
            return
        if not self._recent:
            self.recent_menu.add_command(label="(empty)", state=tk.DISABLED)
            return
        for path in self._recent:
            disp = path if len(path) <= 60 else "..." + path[-57:]
            self.recent_menu.add_command(
                label=disp,
                command=lambda p=path: self._add_paths([p]))
        self.recent_menu.add_separator()
        self.recent_menu.add_command(
            label="Clear recent", command=self._on_clear_recent)

    def _on_clear_recent(self) -> None:
        self._recent = []
        self._refresh_recent_menu()
        _settings.save(self._collect_settings())

    def _collect_settings(self) -> dict:
        return {
            "mode":     self.var_mode.get(),
            "sort":     self.var_sort.get(),
            "size":     self.var_size.get(),
            "orient":   self.var_orient.get(),
            "fit":      self.var_fit.get(),
            "stack":    self.var_stack.get(),
            "pencil":   bool(self.var_pencil.get()),
            "strength": self.var_strength.get(),
            "output":   self.var_output.get(),
            "recent":   list(self._recent),
        }

    def _on_close(self) -> None:
        try:
            _settings.save(self._collect_settings())
        finally:
            self.root.destroy()

    def _build_layout(self) -> None:
        body = ttk.Frame(self.root, padding=8)
        body.pack(fill=tk.BOTH, expand=True)

        # Left: drop zone + reorderable list ----------------------------
        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        self.drop_frame = tk.Frame(
            left, bd=2, relief=tk.GROOVE,
            background="#fafafa", highlightthickness=1,
            highlightbackground="#cccccc")
        self.drop_frame.pack(fill=tk.BOTH, expand=True)

        # Listbox + scrollbar live INSIDE the drop frame so the whole
        # area accepts drops.
        list_holder = tk.Frame(self.drop_frame, background="#fafafa")
        list_holder.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.listbox = tk.Listbox(
            list_holder, activestyle="dotbox", selectmode=tk.EXTENDED,
            highlightthickness=0, bd=0, font=("TkFixedFont", 10))
        sb = ttk.Scrollbar(list_holder, orient=tk.VERTICAL,
                           command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        # Empty-state hint sits on top of the list when empty.
        self.empty_hint = tk.Label(
            self.drop_frame, text=DROP_ZONE_HINT, background="#fafafa",
            foreground="#777777", justify=tk.CENTER, wraplength=460)

        # Toolbar: up/down/remove ---------------------------------------
        tools = ttk.Frame(left, padding=(0, 6, 0, 0))
        tools.pack(fill=tk.X)
        ttk.Button(tools, text="Up",     width=6,
                   command=self.on_move_up).pack(side=tk.LEFT)
        ttk.Button(tools, text="Down",   width=6,
                   command=self.on_move_down).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(tools, text="Remove", width=8,
                   command=self.on_remove).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(tools, text="Clear",  width=6,
                   command=self.on_clear).pack(side=tk.RIGHT)

        # Right: options panel -----------------------------------------
        self._build_options_panel(body)


        # Bottom: convert button + status bar ---------------------------
        bottom = ttk.Frame(self.root, padding=(8, 0, 8, 6))
        bottom.pack(fill=tk.X, side=tk.BOTTOM)
        self.convert_btn = ttk.Button(
            bottom, text="Convert", state=tk.DISABLED,
            command=self.on_convert)
        self.convert_btn.pack(side=tk.RIGHT)

        self.status_var = tk.StringVar()
        status = ttk.Label(
            self.root, textvariable=self.status_var, anchor=tk.W,
            relief=tk.SUNKEN, padding=(8, 2))
        status.pack(fill=tk.X, side=tk.BOTTOM)

    def _build_options_panel(self, parent: tk.Misc) -> None:
        right = ttk.LabelFrame(parent, text="Options", padding=10, width=260)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        def row(label: str) -> ttk.Frame:
            ttk.Label(right, text=label).pack(anchor=tk.W, pady=(6, 2))
            f = ttk.Frame(right); f.pack(fill=tk.X)
            return f

        # Output mode
        f = row("Output mode")
        ttk.OptionMenu(
            f, self.var_mode, self.var_mode.get(),
            "pdf", "image", "pencil-pdf", "pencil-image",
            command=lambda v: self._on_mode_changed(v),
        ).pack(fill=tk.X)

        # Sort
        f = row("Sort")
        ttk.OptionMenu(
            f, self.var_sort, self.var_sort.get(),
            "auto", "selection", "name", "date", "folder",
        ).pack(fill=tk.X)

        # Page size + orientation (PDF only)
        f = row("Page size")
        ttk.OptionMenu(
            f, self.var_size, self.var_size.get(), "a4", "letter", "legal",
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.OptionMenu(
            f, self.var_orient, self.var_orient.get(),
            "portrait", "landscape",
        ).pack(side=tk.RIGHT, padx=(6, 0))

        # Fit (PDF only)
        f = row("Image fit (PDF)")
        ttk.OptionMenu(
            f, self.var_fit, self.var_fit.get(),
            "contain", "cover", "stretch", "original",
        ).pack(fill=tk.X)

        # Stack direction (image only)
        f = row("Stack (image)")
        ttk.OptionMenu(
            f, self.var_stack, self.var_stack.get(),
            "vertical", "horizontal",
        ).pack(fill=tk.X)

        # Pencil
        f = row("Pencil style")
        self.chk_pencil = ttk.Checkbutton(
            f, text="Apply pencil sketch", variable=self.var_pencil,
            command=self._on_pencil_toggle)
        self.chk_pencil.pack(anchor=tk.W)
        self.strength_menu = ttk.OptionMenu(
            f, self.var_strength, self.var_strength.get(),
            "subtle", "normal", "extra")
        self.strength_menu.pack(fill=tk.X, pady=(4, 0))

        # Output path
        f = row("Output")
        ttk.Entry(f, textvariable=self.var_output).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(f, text="...", width=3,
                   command=self._on_pick_output).pack(side=tk.RIGHT, padx=(4, 0))

        # Sync derived state
        self._on_mode_changed(self.var_mode.get())

    # -------------------------------------------------------- options helpers

    def _set_output_mode(self, value: str, label: str) -> None:
        self.var_mode.set(value)
        self._on_mode_changed(value)
        self._set_status(f"Mode: {label}")

    def _on_mode_changed(self, value: str) -> None:
        is_pencil_alias = value in ("pencil-pdf", "pencil-image")
        if is_pencil_alias:
            self.var_pencil.set(True)
        self._on_pencil_toggle()

    def _on_pencil_toggle(self) -> None:
        state = (tk.NORMAL if self.var_pencil.get() or
                 self.var_mode.get() in ("pencil-pdf", "pencil-image")
                 else tk.DISABLED)
        try:
            self.strength_menu.configure(state=state)
        except tk.TclError:
            pass

    def _on_pick_output(self) -> None:
        mode = self.var_mode.get()
        if mode in ("pdf", "pencil-pdf"):
            path = filedialog.asksaveasfilename(
                title="Save PDF as",
                defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf")])
        else:
            path = filedialog.asksaveasfilename(
                title="Save image as",
                defaultextension=".png",
                filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")])
        if path:
            self.var_output.set(path)


    # ----------------------------------------------------------- DnD wiring

    def _wire_dnd(self) -> None:
        const = self.dnd_const
        for widget in (self.drop_frame, self.listbox, self.empty_hint):
            try:
                widget.drop_target_register(const)  # type: ignore[attr-defined]
                widget.dnd_bind("<<Drop>>", self._on_drop)  # type: ignore[attr-defined]
            except Exception:
                pass

    def _on_drop(self, event) -> str:
        paths = _split_dnd_paths(event.data)
        if not paths:
            return "break"
        self._add_paths(paths)
        return "break"

    # -------------------------------------------------------------- helpers

    def _set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    def _refresh_convert_enabled(self) -> None:
        self.convert_btn.config(
            state=tk.NORMAL if self.inputs else tk.DISABLED)

    def _refresh_list(self) -> None:
        self.listbox.delete(0, tk.END)
        for p in self.inputs:
            kind = classify(p)
            label = f"[{kind:>4}]  {p}"
            self.listbox.insert(tk.END, label)
        # Toggle the empty-state hint overlay.
        if self.inputs:
            self.empty_hint.place_forget()
        else:
            self.empty_hint.place(relx=0.5, rely=0.5, anchor="center")
        self._refresh_convert_enabled()

    def _add_paths(self, paths) -> None:
        added = 0
        for raw in paths:
            p = raw.strip().strip('"')
            if not p:
                continue
            # Skip duplicates of paths already queued.
            if p in self.inputs:
                continue
            self.inputs.append(p)
            added += 1
        if added:
            self._set_status(f"Added {added}. Total: {len(self.inputs)}.")
        else:
            self._set_status("No new inputs (duplicates skipped).")
        self._refresh_list()

    def _selected_indices(self) -> list[int]:
        try:
            return [int(i) for i in self.listbox.curselection()]
        except Exception:
            return []

    # -------------------------------------------------------------- actions

    def on_add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Add files",
            filetypes=[
                ("All supported",
                 "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff "
                 "*.pdf *.html *.htm *.docx *.doc"),
                ("All files", "*.*"),
            ])
        if paths:
            self._add_paths(paths)

    def on_add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Add folder")
        if folder:
            self._add_paths([folder])

    def on_clear(self) -> None:
        self.inputs.clear()
        self._set_status("Cleared.")
        self._refresh_list()

    def on_remove(self) -> None:
        idxs = sorted(self._selected_indices(), reverse=True)
        if not idxs:
            return
        for i in idxs:
            del self.inputs[i]
        self._set_status(f"Removed {len(idxs)}.")
        self._refresh_list()

    def on_move_up(self) -> None:
        idxs = sorted(self._selected_indices())
        if not idxs or idxs[0] == 0:
            return
        for i in idxs:
            self.inputs[i - 1], self.inputs[i] = self.inputs[i], self.inputs[i - 1]
        self._refresh_list()
        for i in idxs:
            self.listbox.selection_set(i - 1)

    def on_move_down(self) -> None:
        idxs = sorted(self._selected_indices(), reverse=True)
        if not idxs or idxs[0] >= len(self.inputs) - 1:
            return
        for i in idxs:
            self.inputs[i + 1], self.inputs[i] = self.inputs[i], self.inputs[i + 1]
        self._refresh_list()
        for i in idxs:
            self.listbox.selection_set(i + 1)

    def on_convert(self) -> None:
        if not self.inputs:
            return
        if getattr(self, "_worker", None) and self._worker.is_alive():
            return  # already running

        argv = self._build_cli_argv()
        if argv is None:
            return
        self.convert_btn.config(state=tk.DISABLED)
        self._set_status("Converting...")

        import subprocess, threading, io, contextlib

        frozen = getattr(sys, "frozen", False)

        def worker_subprocess():
            try:
                proc = subprocess.run(
                    argv, capture_output=True, text=True,
                    encoding="utf-8", errors="replace")
                ok = proc.returncode == 0
                msg = (proc.stdout or "").strip().splitlines()[-1:] or [""]
                err = (proc.stderr or "").strip().splitlines()[-1:] or [""]
                summary = msg[0] if ok else (err[0] or "Conversion failed.")
                detail = (proc.stderr or proc.stdout or "").strip()
            except Exception as exc:  # pragma: no cover - defensive
                ok, summary, detail = False, f"Error: {exc}", ""
            self.root.after(0, lambda: self._on_convert_done(
                ok, summary, detail))

        def worker_inproc():
            # In frozen builds there is no python interpreter on PATH, so
            # call the engine directly with the argv after the script path.
            from jpg2pdf_app.core import engine
            buf_out, buf_err = io.StringIO(), io.StringIO()
            saved = sys.argv
            sys.argv = ["jpg2pdf", *argv[2:]]
            try:
                with contextlib.redirect_stdout(buf_out), \
                     contextlib.redirect_stderr(buf_err):
                    try:
                        engine.main()
                        ok, summary = True, "Done."
                    except SystemExit as exc:
                        code = exc.code if isinstance(exc.code, int) else 0
                        ok = code == 0
                        summary = "Done." if ok else f"Exit code {code}"
                    except Exception as exc:
                        ok, summary = False, f"{type(exc).__name__}: {exc}"
            finally:
                sys.argv = saved
            detail = (buf_err.getvalue() or buf_out.getvalue()).strip()
            tail = (buf_out.getvalue().strip().splitlines()[-1:] or [""])[0]
            if ok and tail:
                summary = tail
            self.root.after(0, lambda: self._on_convert_done(
                ok, summary, detail))

        target = worker_inproc if frozen else worker_subprocess
        self._worker = threading.Thread(target=target, daemon=True)
        self._worker.start()


    def _build_cli_argv(self) -> list[str] | None:
        """Translate GUI option state into a `jpg2pdf` CLI command."""
        mode = self.var_mode.get()
        out = self.var_output.get().strip()
        if not out:
            # Auto-pick an output path next to the first input.
            first = Path(self.inputs[0])
            base = first.parent / (first.stem + "-jpg2pdf")
            out = str(base.with_suffix(
                ".pdf" if mode in ("pdf", "pencil-pdf") else ".png"))
            self.var_output.set(out)

        script = str(Path(__file__).resolve().parent.parent / "jpg2pdf.py")
        argv = [sys.executable, script,
                "--output-mode", mode,
                "--sort", self.var_sort.get(),
                "--size", self.var_size.get(),
                "--orientation", self.var_orient.get(),
                "--fit", self.var_fit.get(),
                "--stack", self.var_stack.get(),
                "--out", out]

        # Pencil: explicit style + strength when enabled (alias modes also
        # force pencil in the CLI, so this is safe to send either way).
        if (self.var_pencil.get() or
                mode in ("pencil-pdf", "pencil-image")):
            argv += ["--style", "pencil",
                     "--pencil-strength", self.var_strength.get()]

        # Inputs come last via --files for explicit selection order.
        argv += ["--files", *self.inputs]
        return argv

    def _on_convert_done(self, ok: bool, summary: str, detail: str = "") -> None:
        self.convert_btn.config(state=tk.NORMAL if self.inputs else tk.DISABLED)
        if ok:
            self._set_status(f"Done -> {self.var_output.get()}")
            # Push inputs into recent files and persist (Step 17).
            self._recent = _settings.push_recent(self._recent, self.inputs)
            self._refresh_recent_menu()
            _settings.save(self._collect_settings())
            messagebox.showinfo("jpg2pdf", f"Converted.\n\n{self.var_output.get()}")
        else:
            self._set_status(f"Failed: {summary}")
            messagebox.showerror(
                "jpg2pdf — conversion failed",
                f"{summary}\n\n{detail[-1200:]}" if detail else summary)



    def on_about(self) -> None:
        messagebox.showinfo(
            "About jpg2pdf",
            f"jpg2pdf {__version__}\n\n"
            "Combine images, PDFs, HTML, and Word docs into one PDF — "
            "or stack images into a single PNG/JPG, optionally pencil-styled.")


def run() -> int:
    """Entry point — create the root window (DnD-aware if possible)."""
    TkCls, dnd_const = _try_load_dnd()
    try:
        root = TkCls() if TkCls else tk.Tk()
    except tk.TclError as exc:
        print(f"jpg2pdf-gui: cannot open display ({exc}).", file=sys.stderr)
        return 1
    Jpg2PdfApp(root, dnd_const=dnd_const)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

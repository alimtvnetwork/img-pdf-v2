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

    # ------------------------------------------------------------------ UI

    def _build_menubar(self) -> None:
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Add files...", command=self.on_add_files)
        file_menu.add_command(label="Add folder...", command=self.on_add_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Clear list", command=self.on_clear)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.root.destroy)
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

        # Right: options placeholder ------------------------------------
        right = ttk.LabelFrame(body, text="Options", padding=10, width=240)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)
        ttk.Label(
            right, foreground="#777777", justify=tk.LEFT, wraplength=200,
            text="Output mode, sort, page size, pencil strength and the "
                 "output picker land here in Step 9.",
        ).pack(anchor=tk.NW)

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
        messagebox.showinfo(
            "jpg2pdf",
            f"Convert wiring lands in Step 10.\n\n"
            f"Queued inputs ({len(self.inputs)}):\n"
            + "\n".join(f"  {i+1}. {p}" for i, p in enumerate(self.inputs[:8]))
            + ("\n  ..." if len(self.inputs) > 8 else ""))

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

"""jpg2pdf GUI — Tkinter shell.

Step 7 of the GUI roadmap (.lovable/plan.md): minimal window with menubar,
empty drop zone, and status bar. Real drag-and-drop (Step 8), options
panel (Step 9), and convert wiring (Step 10) land in later steps.

Launch via:
    jpg2pdf --gui
    jpg2pdf-gui          (separate console script, future)
    python -m jpg2pdf_app.gui
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from jpg2pdf_app.core import __version__


WINDOW_TITLE = f"jpg2pdf {__version__}"
DROP_ZONE_HINT = (
    "Drag files or folders here, or click 'Add files...'.\n"
    "Supports images (jpg/png/webp/...), PDF, HTML, and Word documents."
)


class Jpg2PdfApp:
    """Top-level GUI controller. Owns the root window and all widgets."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry("820x520")
        self.root.minsize(640, 420)

        # Tracked state — populated by later steps.
        self.inputs: list[str] = []

        self._build_menubar()
        self._build_layout()
        self._set_status(f"Ready. jpg2pdf {__version__}.")

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
        for label in ("PDF", "Stacked Image", "Pencil PDF", "Pencil Image"):
            mode_menu.add_command(
                label=label,
                command=lambda lbl=label: self._set_status(
                    f"Mode '{lbl}' will be wired in Step 9.")
            )
        menubar.add_cascade(label="Mode", menu=mode_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="About", command=self.on_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def _build_layout(self) -> None:
        # Main horizontal split: drop zone (left) + options placeholder (right).
        body = ttk.Frame(self.root, padding=8)
        body.pack(fill=tk.BOTH, expand=True)

        # Left: drop zone with a placeholder label inside a sunken frame.
        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        drop = tk.Frame(
            left, bd=2, relief=tk.GROOVE,
            background="#fafafa", highlightthickness=1,
            highlightbackground="#cccccc",
        )
        drop.pack(fill=tk.BOTH, expand=True)
        self.drop_zone = drop

        self.drop_label = tk.Label(
            drop, text=DROP_ZONE_HINT, background="#fafafa",
            foreground="#555555", justify=tk.CENTER, wraplength=420,
        )
        self.drop_label.pack(expand=True)

        # Right: options placeholder (Steps 8-9 fill this in).
        right = ttk.LabelFrame(body, text="Options", padding=10, width=240)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)
        ttk.Label(
            right, foreground="#777777", justify=tk.LEFT, wraplength=200,
            text="Output mode, sort, page size, pencil strength and the "
                 "output picker will appear here (Step 9).",
        ).pack(anchor=tk.NW)

        # Bottom: convert button + status bar.
        bottom = ttk.Frame(self.root, padding=(8, 0, 8, 6))
        bottom.pack(fill=tk.X, side=tk.BOTTOM)
        self.convert_btn = ttk.Button(
            bottom, text="Convert", state=tk.DISABLED,
            command=self.on_convert,
        )
        self.convert_btn.pack(side=tk.RIGHT)

        self.status_var = tk.StringVar()
        status = ttk.Label(
            self.root, textvariable=self.status_var, anchor=tk.W,
            relief=tk.SUNKEN, padding=(8, 2),
        )
        status.pack(fill=tk.X, side=tk.BOTTOM)

    # -------------------------------------------------------------- helpers

    def _set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    def _refresh_convert_enabled(self) -> None:
        self.convert_btn.config(
            state=tk.NORMAL if self.inputs else tk.DISABLED
        )

    # -------------------------------------------------------------- actions

    def on_add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Add files",
            filetypes=[
                ("All supported",
                 "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff "
                 "*.pdf *.html *.htm *.docx *.doc"),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            return
        self.inputs.extend(paths)
        self._set_status(f"{len(self.inputs)} input(s) queued.")
        self._refresh_convert_enabled()

    def on_add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Add folder")
        if not folder:
            return
        self.inputs.append(folder)
        self._set_status(f"{len(self.inputs)} input(s) queued.")
        self._refresh_convert_enabled()

    def on_clear(self) -> None:
        self.inputs.clear()
        self._set_status("Cleared.")
        self._refresh_convert_enabled()

    def on_convert(self) -> None:
        # Step 10 will wire this into jpg2pdf_app.core.
        messagebox.showinfo(
            "jpg2pdf",
            f"Convert wiring lands in Step 10.\n\n"
            f"Queued inputs: {len(self.inputs)}",
        )

    def on_about(self) -> None:
        messagebox.showinfo(
            "About jpg2pdf",
            f"jpg2pdf {__version__}\n\n"
            "Combine images, PDFs, HTML, and Word docs into one PDF — "
            "or stack images into a single PNG/JPG, optionally pencil-styled.",
        )


def run() -> int:
    """Entry point — create the root window and run the Tk mainloop."""
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"jpg2pdf-gui: cannot open display ({exc}).", file=sys.stderr)
        return 1
    Jpg2PdfApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

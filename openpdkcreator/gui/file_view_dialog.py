"""A real, one-file View -> Edit -> Save dialog over the actual source
file behind whatever's currently shown in a tab (the selected LEF/tech
file, or the .lyp).

Deliberately two-stage, unlike OpenPDKCreator's own
``gui/file_view_dialog.py`` (always editable from the moment it
opens): the files here are real, downloaded third-party PDK data (see
README.md's "IHP data in git" note), so opening one always starts
read-only -- an explicit **Edit** button, inside the dialog, is what
switches it to editable and reveals **Save**. Editing only ever
touches the real, local, gitignored copy under ``data/`` -- never
this project's own committed code.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


def view_file_dialog(
    parent: tk.Widget, path: Path,
    focus_start_line: int | None = None, focus_end_line: int | None = None,
) -> None:
    """*focus_start_line*/*focus_end_line* (1-indexed, both optional):
    when given, scrolls to and highlights that real line range on open
    -- used by ``cell_hub_view.py`` to jump straight to one real cell's
    own block inside a much larger, combined per-family file (e.g. a
    real ``.SUBCKT``/``.ends`` pair 25 lines into an 8000-line
    ``sg13g2_stdcell.cdl``), rather than making the user hunt for it."""

    dialog = tk.Toplevel(parent)
    dialog.title(f"View: {path.name}")
    dialog.geometry("900x700")
    dialog.transient(parent.winfo_toplevel())

    dialog.columnconfigure(0, weight=1)
    dialog.rowconfigure(1, weight=1)

    status_var = tk.StringVar(value=str(path))
    ttk.Label(dialog, textvariable=status_var, font=("TkDefaultFont", 9, "bold")).grid(
        row=0, column=0, sticky="w", padx=8, pady=(8, 4)
    )

    text = tk.Text(dialog, wrap="none", font=("Courier", 10))
    text.grid(row=1, column=0, sticky="nsew", padx=8)
    scroll_y = ttk.Scrollbar(dialog, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=scroll_y.set)
    scroll_y.grid(row=1, column=1, sticky="ns")
    scroll_x = ttk.Scrollbar(dialog, orient="horizontal", command=text.xview)
    text.configure(xscrollcommand=scroll_x.set)
    scroll_x.grid(row=2, column=0, sticky="ew", padx=8)

    text.insert("1.0", path.read_text(encoding="utf-8", errors="replace"))
    text.configure(state="disabled")
    text.edit_modified(False)

    if focus_start_line is not None:
        end = focus_end_line if focus_end_line is not None else focus_start_line
        text.tag_configure("focus_range", background="#fff2a8")
        text.tag_add("focus_range", f"{focus_start_line}.0", f"{end + 1}.0")
        text.see(f"{end}.0")
        text.see(f"{focus_start_line}.0")

    button_row = ttk.Frame(dialog)
    button_row.grid(row=3, column=0, sticky="e", padx=8, pady=8)

    edit_button = ttk.Button(button_row, text="Edit")
    save_button = ttk.Button(button_row, text="Save", state="disabled")

    def _enable_edit():
        text.configure(state="normal")
        edit_button.configure(state="disabled")
        save_button.configure(state="normal")
        status_var.set(f"{path}  (editing -- a real, local, downloaded PDK file)")

    def _save():
        if not messagebox.askyesno(
            "Save changes?",
            f"Overwrite the real, local file\n{path}\nwith these changes?\n\n"
            f"This only touches your local data/ copy (gitignored, never committed).",
            parent=dialog,
        ):
            return
        path.write_text(text.get("1.0", "end-1c"), encoding="utf-8")
        text.edit_modified(False)
        status_var.set(f"{path}  (saved)")

    def _close():
        if text.edit_modified() and not messagebox.askyesno(
            "Discard changes?", "You have unsaved edits. Close without saving?", parent=dialog
        ):
            return
        dialog.destroy()

    edit_button.configure(command=_enable_edit)
    save_button.configure(command=_save)
    edit_button.pack(side="left")
    save_button.pack(side="left", padx=(6, 0))
    ttk.Button(button_row, text="Close", command=_close).pack(side="left", padx=(6, 0))
    dialog.protocol("WM_DELETE_WINDOW", _close)

    dialog.grab_set()
    dialog.wait_window()

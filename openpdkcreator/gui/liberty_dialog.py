"""A small modal dialog wrapping ``liberty_editor.LibertyPinEditor`` --
opened from the By Cell tab's own "Edit Pins/Timing" button, one real
cell's one real corner file at a time. Edits happen live via the same
commit-on-switch pattern every other editor here uses; closing the
dialog just flushes whatever's still mid-edit -- the edited pin/arc
objects are the exact same real, in-memory ones the caller (via
``App.get_parsed_liberty``) already holds a live reference to.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..pdklib import liberty as liberty_mod
from .liberty_editor import LibertyPinEditor


def edit_liberty_dialog(parent, title: str, cell: liberty_mod.LibertyCell):
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry("820x760")
    dialog.transient(parent.winfo_toplevel())

    editor = LibertyPinEditor(dialog)
    editor.pack(fill="both", expand=True, padx=8, pady=8)
    editor.set_cell(cell)

    def _on_close():
        editor.commit_pending_edits()
        dialog.destroy()

    ttk.Button(dialog, text="Close", command=_on_close).pack(pady=(0, 8))
    dialog.protocol("WM_DELETE_WINDOW", _on_close)
    dialog.grab_set()
    dialog.wait_window()

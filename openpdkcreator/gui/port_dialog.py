"""A small modal dialog wrapping ``port_editor.PortEditor`` -- opened
from the By Cell tab's own "Edit CDL/SPICE/Verilog Ports" buttons, one
real cell's one real view's ports at a time. Edits happen live via the
same commit-on-switch pattern every other editor here uses; there's no
separate "Save" inside the dialog -- closing it commits whatever's
mid-edit and is enough, since the edited port objects are the exact
same real, in-memory ones the caller (``CellHubView``, via
``App.get_parsed_netlist``/``get_parsed_verilog``) already holds a
live reference to.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from .port_editor import PortEditor


def edit_ports_dialog(
    parent, title: str, ports: list, port_factory: Callable[[str], object], has_width: bool = False,
):
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry("580x360")
    dialog.transient(parent.winfo_toplevel())

    editor = PortEditor(dialog, port_factory=port_factory, has_width=has_width)
    editor.pack(fill="both", expand=True, padx=8, pady=8)
    editor.set_ports(ports)

    def _on_close():
        editor.commit_pending_edits()
        dialog.destroy()

    ttk.Button(dialog, text="Close", command=_on_close).pack(pady=(0, 8))
    dialog.protocol("WM_DELETE_WINDOW", _on_close)
    dialog.grab_set()
    dialog.wait_window()

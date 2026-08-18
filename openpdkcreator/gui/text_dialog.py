"""A small, read-only modal showing generated (not real-file-backed)
text -- e.g. ``user_models_view.py``'s own ngspice/OSDI wiring
snippet. Distinct from ``file_view_dialog.view_file_dialog``: there's
no real underlying file to view/edit/save here, just text to read and
select/copy by hand (no clipboard access is taken on the user's
behalf).

``wrap="word"`` -- real, dynamic word-wrap to the ``Text`` widget's own
current pixel width, not a fixed column count: Tk re-flows it on every
real resize with no extra code needed here. The previous ``wrap="none"``
had no horizontal scrollbar either, so any real line wider than the
window was genuinely unreachable, not just inconvenient -- a real bug,
not a style choice. Word-wrap never touches the actual, real text
buffer (still exactly what was inserted, still exactly what a real
select/copy grabs); it's purely how it's displayed."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def show_text_dialog(parent: tk.Widget, title: str, text: str) -> None:
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry("720x420")
    dialog.transient(parent.winfo_toplevel())

    dialog.columnconfigure(0, weight=1)
    dialog.rowconfigure(0, weight=1)

    body = tk.Text(dialog, wrap="word", font=("Courier", 10))
    body.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
    scroll_y = ttk.Scrollbar(dialog, orient="vertical", command=body.yview)
    body.configure(yscrollcommand=scroll_y.set)
    scroll_y.grid(row=0, column=1, sticky="ns", pady=8)

    body.insert("1.0", text)
    body.configure(state="disabled")

    ttk.Button(dialog, text="Close", command=dialog.destroy).grid(row=1, column=0, columnspan=2, pady=(0, 8))
    dialog.grab_set()
    dialog.wait_window()

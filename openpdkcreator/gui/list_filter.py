"""A small, reusable live filter/search box for a Treeview-backed
list -- shared across Layers/DRC Rules/LEF Macros/By Cell/Magic Types
so every list gets the exact same case-insensitive substring behavior
on every keystroke, not five subtly different implementations. Each
view still owns its own ``refresh()``/data model; this only supplies
the widget and the match test, since what fields to match against
genuinely differs per list (a DRC Rule's ``rule_id``/description isn't
a Layer's ``name``/``purpose``).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


def build_filter_row(parent: tk.Widget, on_change: Callable[[str], None], label: str = "Filter:") -> tk.StringVar:
    """Packs a Label+Entry pair into *parent* (an existing container,
    e.g. a button row ``Frame``) and wires *on_change* to fire on
    every keystroke with the current query text, lowercased and
    stripped -- so callers never repeat that normalization
    themselves. Returns the backing ``StringVar`` in case a caller
    wants to clear it programmatically (e.g. after Delete removes the
    only matching row)."""

    var = tk.StringVar()

    def _on_write(*_args):
        on_change(var.get().strip().lower())

    var.trace_add("write", _on_write)
    ttk.Label(parent, text=label).pack(side="left", padx=(12, 4))
    ttk.Entry(parent, textvariable=var, width=20).pack(side="left")
    return var


def matches(query: str, *fields: str) -> bool:
    """True if *query* (already lowercased) is a substring of any of
    *fields* (case-insensitively) -- an empty query always matches
    everything, so an untouched filter box never hides real data."""

    if not query:
        return True
    return any(query in (field or "").lower() for field in fields)

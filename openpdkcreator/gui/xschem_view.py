"""Simulation tab: real, parsed xschem symbol data
(``openpdkcreator/ihp/xschem.py``) -- a file picker over all 202 real,
downloaded ``libs.tech/xschem/*/*.sym`` files (mirroring
``lef_view.py``/``spice_models_view.py``'s own file-picker shape for
the same reason -- no small, fixed set of "the real ones" here
either).

Two sub-tabs per symbol: **Device** (the real ``K``-block's own
``type``/``template_params``/``raw_fields``) and **Pins** (the real
``B ... {name=... dir=...}`` pin list). Read-only -- no editor exists
for xschem symbol data, matching every other real, display-only domain
here. "View File" opens the real, selected ``.sym`` file directly
(``file_view_dialog.view_file_dialog``).
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..ihp import xschem as xschem_mod
from .file_view_dialog import view_file_dialog


class XschemView(ttk.Frame):
    def __init__(self, parent, pdk_root: Path):
        super().__init__(parent)
        self.pdk_root = pdk_root
        self.sym_files: dict[str, Path] = {}
        self.current: xschem_mod.XschemSymbol | None = None

        self._build()
        self.load()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="xschem .sym file:").pack(side="left")
        self.file_var = tk.StringVar()
        self.file_combo = ttk.Combobox(top, textvariable=self.file_var, state="readonly", width=50)
        self.file_combo.pack(side="left", padx=(4, 12))
        self.file_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())

        ttk.Button(top, text="View File", command=self._view_file).pack(side="left")

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True)

        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.device_tree = self._make_tree(sub, "Device", ("field", "value"), (200, 640))
        self.pins_tree = self._make_tree(sub, "Pins", ("name", "direction"), (200, 640))

    def _make_tree(self, notebook: ttk.Notebook, title: str, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col, width in zip(columns, widths):
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        return tree

    def _view_file(self):
        path = self.sym_files.get(self.file_var.get())
        if path is not None:
            view_file_dialog(self, path)

    def load(self):
        self.sym_files = {
            str(path.relative_to(self.pdk_root)): path
            for path in xschem_mod.find_sym_files(self.pdk_root)
        }
        names = sorted(self.sym_files)
        self.file_combo["values"] = names
        if names and not self.file_var.get():
            self.file_var.set(names[0])
        self._refresh_all()

    def _refresh_all(self):
        for row in self.device_tree.get_children():
            self.device_tree.delete(row)
        for row in self.pins_tree.get_children():
            self.pins_tree.delete(row)

        path = self.sym_files.get(self.file_var.get())
        if path is None:
            self.summary_var.set("No xschem .sym data loaded -- has ihp/fetch.py been run?")
            self.current = None
            return

        self.current = xschem_mod.parse_sym_file(path)
        symbol = self.current

        self.device_tree.insert("", "end", values=("type", symbol.device_type or "(none)"))
        for key, value in symbol.template_params.items():
            self.device_tree.insert("", "end", values=(f"template.{key}", value))
        for key, value in symbol.raw_fields.items():
            self.device_tree.insert("", "end", values=(key, value))
        for pin in symbol.pins:
            self.pins_tree.insert("", "end", values=(pin.name, pin.direction))

        self.summary_var.set(f"type:{symbol.device_type or '(none)'}  pins:{len(symbol.pins)}")

"""Cells tab: real, parsed LEF data (``openpdkcreator/ihp/lef.py``) --
tech-layer routing rules and real macro/cell footprints (class/size/
site/symmetry, pins with direction/use/port geometry, obstruction
layers). A file picker over all real, downloaded ``.lef`` files (a
tech LEF, two stdcell/io macro LEFs, 28 real SRAM hard-macro LEFs),
since -- unlike Magic's two real technologies -- there's no small,
fixed set of "the real ones" to enumerate; every real ``.lef`` under
``libs.ref/`` is shown.

Two sub-tabs per file: **LEF Layers** (tech-LEF routing/cut layers --
empty for a macro-only LEF, real and correct, not a bug) and
**LEF Macros** (a macro list; selecting one shows its real pins on the
right). The parsed tables stay read-only (no write-back serialization
yet -- see README's Future Work); "View File" opens the real,
selected ``.lef`` file directly (``file_view_dialog.view_file_dialog``),
which *can* be edited.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..ihp import lef as lef_mod
from .file_view_dialog import view_file_dialog


class LefView(ttk.Frame):
    def __init__(self, parent, pdk_root: Path):
        super().__init__(parent)
        self.pdk_root = pdk_root
        self.lef_files: dict[str, Path] = {}
        self.current: lef_mod.LefFile | None = None

        self._build()
        self.load()

    # -- layout -----------------------------------------------------------

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="LEF file:").pack(side="left")
        self.file_var = tk.StringVar()
        self.file_combo = ttk.Combobox(top, textvariable=self.file_var, state="readonly", width=50)
        self.file_combo.pack(side="left", padx=(4, 12))
        self.file_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())

        ttk.Button(top, text="View File", command=self._view_file).pack(side="left")

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True)

        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.layers_tree = self._make_tree(
            sub, "LEF Layers",
            ("name", "type", "direction", "pitch", "width", "spacing", "resistance"),
            (140, 90, 90, 70, 70, 70, 140),
        )
        self._build_macros_tab(sub)

    def _make_tree(self, notebook: ttk.Notebook, title: str, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col, width in zip(columns, widths):
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        return tree

    def _build_macros_tab(self, notebook: ttk.Notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="LEF Macros")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)

        left = ttk.Frame(frame)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        macro_columns = ("name", "class", "size", "site", "pins", "obs_layers")
        self.macros_tree = ttk.Treeview(left, columns=macro_columns, show="headings")
        for col, width in zip(macro_columns, (220, 110, 100, 90, 50, 120)):
            self.macros_tree.heading(col, text=col.replace("_", " ").title())
            self.macros_tree.column(col, width=width, anchor="w")
        self.macros_tree.grid(row=0, column=0, sticky="nsew")
        self.macros_tree.bind("<<TreeviewSelect>>", self._on_macro_select)

        right = ttk.Frame(frame)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        pin_columns = ("name", "direction", "use", "ports")
        self.pins_tree = ttk.Treeview(right, columns=pin_columns, show="headings")
        for col, width in zip(pin_columns, (160, 90, 90, 260)):
            self.pins_tree.heading(col, text=col.replace("_", " ").title())
            self.pins_tree.column(col, width=width, anchor="w")
        self.pins_tree.grid(row=0, column=0, sticky="nsew")

    def _view_file(self):
        path = self.lef_files.get(self.file_var.get())
        if path is not None:
            view_file_dialog(self, path)

    # -- data ---------------------------------------------------------------

    def load(self):
        self.lef_files = {
            str(path.relative_to(self.pdk_root)): path
            for path in lef_mod.find_lef_files(self.pdk_root)
        }
        names = sorted(self.lef_files)
        self.file_combo["values"] = names
        if names and not self.file_var.get():
            self.file_var.set(names[0])
        self._refresh_all()

    def _refresh_all(self):
        for row in self.layers_tree.get_children():
            self.layers_tree.delete(row)
        for row in self.macros_tree.get_children():
            self.macros_tree.delete(row)
        for row in self.pins_tree.get_children():
            self.pins_tree.delete(row)

        path = self.lef_files.get(self.file_var.get())
        if path is None:
            self.summary_var.set("No LEF data loaded -- has ihp/fetch.py been run?")
            self.current = None
            return

        self.current = lef_mod.parse_lef_file(path)
        tech = self.current

        for layer in tech.layers:
            self.layers_tree.insert(
                "", "end",
                values=(
                    layer.name, layer.layer_type, layer.direction,
                    layer.pitch if layer.pitch is not None else "",
                    layer.width if layer.width is not None else "",
                    layer.spacing if layer.spacing is not None else "",
                    layer.resistance,
                ),
            )
        for macro in tech.macros:
            size = f"{macro.size[0]} x {macro.size[1]}" if macro.size else ""
            self.macros_tree.insert(
                "", "end", iid=macro.name,
                values=(macro.name, macro.macro_class, size, macro.site, len(macro.pins), ", ".join(macro.obs_layers)),
            )

        summary = (
            f"version {tech.version} | db_microns:{tech.database_microns} | "
            f"mfg_grid:{tech.manufacturing_grid} | layers:{len(tech.layers)} sites:{len(tech.sites)} "
            f"macros:{len(tech.macros)} vias:{len(tech.via_names)} (bodies not parsed) "
            f"viarules:{len(tech.via_rule_names)} (bodies not parsed)"
        )
        self.summary_var.set(summary)

        if tech.macros:
            self.macros_tree.selection_set(tech.macros[0].name)
            self._show_pins(tech.macros[0])

    def _on_macro_select(self, _event=None):
        if self.current is None:
            return
        selection = self.macros_tree.selection()
        if not selection:
            return
        macro = next((m for m in self.current.macros if m.name == selection[0]), None)
        if macro is not None:
            self._show_pins(macro)

    def _show_pins(self, macro: lef_mod.LefMacro):
        for row in self.pins_tree.get_children():
            self.pins_tree.delete(row)
        for pin in macro.pins:
            ports = ", ".join(f"{p.layer}:{p.rect_count}rect" for p in pin.ports)
            self.pins_tree.insert("", "end", values=(pin.name, pin.direction, pin.use, ports))

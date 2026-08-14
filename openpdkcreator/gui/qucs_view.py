"""Simulation tab: real, parsed Qucs-S data
(``openpdkcreator/ihp/qucs_sym.py``) -- two major sub-tabs, mirroring
``xschem_view.py``'s own Symbols/Schematics split, since this real
directory genuinely holds two different real formats (see
``ihp/qucs_sym.py``'s own docstring):

**Components** (34 real ``.xml`` device definitions): library/
description/models, real **Parameters** (name/unit/show plus a real
default value or equation), and real **Netlists** (the raw
Ngspice/CDL/[Xyce] template strings), plus which real ``.sym``
geometry file each one references.

**Symbols** (22 real ``.sym`` drawn-geometry files): real
``PortSym`` primitives -- position/type/angle/condition, plus a real,
honestly-partial trailing-comment ``hint`` (20 of 66 real lines carry
one) -- this format carries no real port *name* at all, unlike
xschem's own ``.sym``.

Both read-only -- no editor exists for either domain. "View File"
opens the real, selected file directly
(``file_view_dialog.view_file_dialog``).
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..ihp import qucs_sym as qucs_mod
from .file_view_dialog import view_file_dialog


class QucsView(ttk.Frame):
    def __init__(self, parent, pdk_root: Path):
        super().__init__(parent)
        self.pdk_root = pdk_root

        outer = ttk.Notebook(self)
        outer.pack(fill="both", expand=True)

        components_frame = ttk.Frame(outer)
        outer.add(components_frame, text="Components")
        self._components = _ComponentsPane(components_frame, pdk_root)
        self._components.pack(fill="both", expand=True)

        symbols_frame = ttk.Frame(outer)
        outer.add(symbols_frame, text="Symbols")
        self._symbols = _SymbolsPane(symbols_frame, pdk_root)
        self._symbols.pack(fill="both", expand=True)


class _ComponentsPane(ttk.Frame):
    def __init__(self, parent, pdk_root: Path):
        super().__init__(parent)
        self.pdk_root = pdk_root
        self.files: dict[str, Path] = {}
        self.current: qucs_mod.QucsComponent | None = None

        self._build()
        self.load()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="Qucs-S component .xml file:").pack(side="left")
        self.file_var = tk.StringVar()
        self.file_combo = ttk.Combobox(top, textvariable=self.file_var, state="readonly", width=50)
        self.file_combo.pack(side="left", padx=(4, 12))
        self.file_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())

        ttk.Button(top, text="View File", command=self._view_file).pack(side="left")

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True)

        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.overview_tree = _make_tree(sub, "Overview", ("field", "value"), (160, 680))
        self.params_tree = _make_tree(
            sub, "Parameters", ("name", "unit", "show", "default_value", "equation", "description"),
            (100, 60, 60, 120, 200, 260),
        )
        self.netlists_tree = _make_tree(sub, "Netlists", ("kind", "template"), (140, 700))

    def _view_file(self):
        path = self.files.get(self.file_var.get())
        if path is not None:
            view_file_dialog(self, path)

    def load(self):
        self.files = {
            str(path.relative_to(self.pdk_root)): path
            for path in qucs_mod.find_component_files(self.pdk_root)
        }
        names = sorted(self.files)
        self.file_combo["values"] = names
        if names and not self.file_var.get():
            self.file_var.set(names[0])
        self._refresh_all()

    def _refresh_all(self):
        for tree in (self.overview_tree, self.params_tree, self.netlists_tree):
            for row in tree.get_children():
                tree.delete(row)

        path = self.files.get(self.file_var.get())
        if path is None:
            self.summary_var.set("No Qucs-S component data loaded -- has ihp/fetch.py been run?")
            self.current = None
            return

        self.current = qucs_mod.parse_component_file(path)
        component = self.current

        overview_rows = [
            ("library", component.library),
            ("names", component.names),
            ("schematic_id", component.schematic_id),
            ("description", component.description),
            ("default_model", component.default_model),
            ("spice_model", component.spice_model),
            ("symbol_file", component.symbol_file),
            ("symbol resolved?", "yes" if component.resolved_symbol_path is not None else "no (external)"),
        ]
        for field_name, value in overview_rows:
            self.overview_tree.insert("", "end", values=(field_name, value))

        for param in component.parameters:
            attrs = param.raw_attrs
            self.params_tree.insert(
                "", "end", values=(
                    attrs.get("name", ""), attrs.get("unit", ""), attrs.get("show", ""),
                    attrs.get("default_value", ""), attrs.get("equation", ""), param.description,
                ),
            )

        for kind, template in component.netlist_templates.items():
            self.netlists_tree.insert("", "end", values=(kind, template))

        self.summary_var.set(
            f"{component.description or '(no description)'}  --  {len(component.parameters)} real parameter(s)"
        )


class _SymbolsPane(ttk.Frame):
    def __init__(self, parent, pdk_root: Path):
        super().__init__(parent)
        self.pdk_root = pdk_root
        self.files: dict[str, Path] = {}
        self.current: qucs_mod.QucsSymbolGeometry | None = None

        self._build()
        self.load()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="Qucs-S symbol .sym file:").pack(side="left")
        self.file_var = tk.StringVar()
        self.file_combo = ttk.Combobox(top, textvariable=self.file_var, state="readonly", width=50)
        self.file_combo.pack(side="left", padx=(4, 12))
        self.file_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())

        ttk.Button(top, text="View File", command=self._view_file).pack(side="left")

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True)

        self.ports_tree = ttk.Treeview(
            self, columns=("x", "y", "type", "angle", "condition", "hint"), show="headings",
        )
        widths = {"x": 60, "y": 60, "type": 60, "angle": 60, "condition": 160, "hint": 100}
        for col in self.ports_tree["columns"]:
            self.ports_tree.heading(col, text=col.title())
            self.ports_tree.column(col, width=widths[col], anchor="w")
        self.ports_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _view_file(self):
        path = self.files.get(self.file_var.get())
        if path is not None:
            view_file_dialog(self, path)

    def load(self):
        self.files = {
            str(path.relative_to(self.pdk_root)): path
            for path in qucs_mod.find_symbol_geometry_files(self.pdk_root)
        }
        names = sorted(self.files)
        self.file_combo["values"] = names
        if names and not self.file_var.get():
            self.file_var.set(names[0])
        self._refresh_all()

    def _refresh_all(self):
        for row in self.ports_tree.get_children():
            self.ports_tree.delete(row)

        path = self.files.get(self.file_var.get())
        if path is None:
            self.summary_var.set("No Qucs-S symbol data loaded -- has ihp/fetch.py been run?")
            self.current = None
            return

        self.current = qucs_mod.parse_symbol_geometry(path)
        geometry = self.current

        for port in geometry.ports:
            self.ports_tree.insert(
                "", "end", values=(port.x, port.y, port.port_type, port.angle, port.condition, port.hint),
            )

        self.summary_var.set(f"{geometry.primitive_count} real drawing primitive(s), {len(geometry.ports)} real port(s)")


def _make_tree(notebook: ttk.Notebook, title: str, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
    frame = ttk.Frame(notebook)
    notebook.add(frame, text=title)
    tree = ttk.Treeview(frame, columns=columns, show="headings")
    for col, width in zip(columns, widths):
        tree.heading(col, text=col.replace("_", " ").title())
        tree.column(col, width=width, anchor="w")
    tree.pack(fill="both", expand=True)
    return tree

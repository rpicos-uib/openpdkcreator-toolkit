"""Simulation tab: real, parsed xschem data
(``openpdkcreator/ihp/xschem.py``/``ihp/xschem_sch.py``) -- two major
sub-tabs, each with its own file picker (mirroring
``lef_view.py``/``spice_models_view.py``'s own file-picker shape --
no small, fixed set of "the real ones" here either, in either domain):

**Symbols**: all 202 real, downloaded ``libs.tech/xschem/*/*.sym``
files. **Device** (the real ``K``-block's own
``type``/``template_params``/``raw_fields``) and **Pins** (the real
``B ... {name=... dir=...}`` pin list) sub-tabs.

**Schematics**: all 100 real, downloaded ``libs.tech/xschem/`` ``.sch``
files (99 real, one level under a family directory, plus one real
exception, ``start_page.sch``, at the xschem root itself -- see
``ihp/xschem_sch.py``'s own ``find_sch_files``). **Instances** (every
real ``C {...}`` component -- symbol reference, position/rotation/
flip, real ``name=``, and whether that reference actually resolves to
a real file inside the downloaded PDK or is one of xschem's own
external/bundled symbols), **Pins** (just the instances that are
schematic-level ports -- ``ipin``/``opin``/``iopin`` references, real
name/net-label pairs; **not always the same set as the matching
``.sym``'s own Pins tab**, confirmed real for `sg13g2_inv_1` -- see
``ihp/xschem_sch.py``'s own docstring), and **Wires** (every real
``N x1 y1 x2 y2 {lab=...}`` segment).

Both sub-tabs are read-only -- no editor exists for either domain,
matching every other real, display-only domain here. "View File" opens
the real, selected file directly (``file_view_dialog.view_file_dialog``).
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..ihp import xschem as xschem_mod
from ..ihp import xschem_sch as xschem_sch_mod
from .file_view_dialog import view_file_dialog

_STEM_TO_DIRECTION = {"ipin": "in", "opin": "out", "iopin": "inout"}


class XschemView(ttk.Frame):
    def __init__(self, parent, pdk_root: Path):
        super().__init__(parent)
        self.pdk_root = pdk_root

        outer = ttk.Notebook(self)
        outer.pack(fill="both", expand=True)

        symbols_frame = ttk.Frame(outer)
        outer.add(symbols_frame, text="Symbols")
        self._symbols = _SymbolsPane(symbols_frame, pdk_root)
        self._symbols.pack(fill="both", expand=True)

        schematics_frame = ttk.Frame(outer)
        outer.add(schematics_frame, text="Schematics")
        self._schematics = _SchematicsPane(schematics_frame, pdk_root)
        self._schematics.pack(fill="both", expand=True)


class _SymbolsPane(ttk.Frame):
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

        self.device_tree = _make_tree(sub, "Device", ("field", "value"), (200, 640))
        self.pins_tree = _make_tree(sub, "Pins", ("name", "direction"), (200, 640))

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


class _SchematicsPane(ttk.Frame):
    def __init__(self, parent, pdk_root: Path):
        super().__init__(parent)
        self.pdk_root = pdk_root
        self.sch_files: dict[str, Path] = {}
        self.current: xschem_sch_mod.XschemSchematic | None = None

        self._build()
        self.load()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="xschem .sch file:").pack(side="left")
        self.file_var = tk.StringVar()
        self.file_combo = ttk.Combobox(top, textvariable=self.file_var, state="readonly", width=50)
        self.file_combo.pack(side="left", padx=(4, 12))
        self.file_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())

        ttk.Button(top, text="View File", command=self._view_file).pack(side="left")

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True)

        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.instances_tree = _make_tree(
            sub, "Instances", ("name", "symbol_ref", "x", "y", "rot", "flip", "resolved"),
            (100, 260, 60, 60, 40, 40, 70),
        )
        self.pins_tree = _make_tree(sub, "Pins", ("name", "direction", "net"), (100, 80, 160))
        self.wires_tree = _make_tree(sub, "Wires", ("x1", "y1", "x2", "y2", "label"), (70, 70, 70, 70, 200))

    def _view_file(self):
        path = self.sch_files.get(self.file_var.get())
        if path is not None:
            view_file_dialog(self, path)

    def load(self):
        self.sch_files = {
            str(path.relative_to(self.pdk_root)): path
            for path in xschem_sch_mod.find_sch_files(self.pdk_root)
        }
        names = sorted(self.sch_files)
        self.file_combo["values"] = names
        if names and not self.file_var.get():
            self.file_var.set(names[0])
        self._refresh_all()

    def _refresh_all(self):
        for tree in (self.instances_tree, self.pins_tree, self.wires_tree):
            for row in tree.get_children():
                tree.delete(row)

        path = self.sch_files.get(self.file_var.get())
        if path is None:
            self.summary_var.set("No xschem .sch data loaded -- has ihp/fetch.py been run?")
            self.current = None
            return

        self.current = xschem_sch_mod.parse_sch_file(path, xschem_root=self.pdk_root / "libs.tech" / "xschem")
        schematic = self.current

        for inst in schematic.instances:
            resolved = "PDK" if inst.resolved_path is not None else "external"
            self.instances_tree.insert(
                "", "end", values=(inst.name, inst.symbol_ref, inst.x, inst.y, inst.rot, inst.flip, resolved),
            )
        for inst in schematic.pin_instances:
            stem = Path(inst.symbol_ref).stem
            self.pins_tree.insert("", "end", values=(inst.name, _STEM_TO_DIRECTION.get(stem, "?"), inst.pin_label))
        for wire in schematic.wires:
            self.wires_tree.insert("", "end", values=(wire.x1, wire.y1, wire.x2, wire.y2, wire.label))

        self.summary_var.set(
            f"instances:{len(schematic.instances)}  pins:{len(schematic.pin_instances)}  "
            f"wires:{len(schematic.wires)}  nets:{len(schematic.net_names)}"
        )


def _make_tree(notebook: ttk.Notebook, title: str, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
    frame = ttk.Frame(notebook)
    notebook.add(frame, text=title)
    tree = ttk.Treeview(frame, columns=columns, show="headings")
    for col, width in zip(columns, widths):
        tree.heading(col, text=col.replace("_", " ").title())
        tree.column(col, width=width, anchor="w")
    tree.pack(fill="both", expand=True)
    return tree

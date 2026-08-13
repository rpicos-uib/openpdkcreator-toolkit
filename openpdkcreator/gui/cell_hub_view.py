"""By Cell tab: a hierarchical, cell-centric view -- for one real cell
(matched by name across every real view directory under a real
``libs.ref/<family>/``, via ``openpdkcreator/ihp/cells.py``), see which
views actually exist (LEF footprint, CDL/SPICE netlist, Verilog
behavioral model, Liberty timing, GDS layout) and jump straight to
that cell's own real block inside each one -- rather than hunting
through 15 separate per-tool tabs/files for "does this cell even have
a Verilog view."

Real, confirmed structural fact: IHP's own families use two different
real per-view file organizations (one combined file with every real
cell inside, e.g. ``sg13g2_stdcell.cdl``; or one real file per cell,
e.g. ``sg13g2_sram``'s 28 real hard-macro ``.cdl`` files) -- both
handled by ``cells.build_cell_index`` already, this view just displays
its result.

Defaults to only real, top-level cells (ones with a real LEF macro --
the physically instantiable ones); a real netlist can contain many more
internal sub-elements with no LEF of their own (confirmed: IHP's own
``sg13g2_sram`` CDL files alone define 2338 real subckts, only 28 of
which are the real, top-level hard macros) -- a **Show internal
sub-cells too** checkbox reveals the rest, off by default so the list
stays genuinely browsable.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..ihp import cells as cells_mod
from .file_view_dialog import view_file_dialog

_CHECK = "✓"


class CellHubView(ttk.Frame):
    def __init__(self, parent, pdk_root: Path):
        super().__init__(parent)
        self.pdk_root = pdk_root
        self.families: list[str] = []
        self.cell_index: dict[str, cells_mod.CellViews] = {}
        self.current_cell: cells_mod.CellViews | None = None

        self._build()
        self.load()

    # -- layout -----------------------------------------------------------

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="Family:").pack(side="left")
        self.family_var = tk.StringVar()
        self.family_combo = ttk.Combobox(top, textvariable=self.family_var, state="readonly", width=24)
        self.family_combo.pack(side="left", padx=(4, 12))
        self.family_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_cells())

        self.show_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            top, text="Show internal sub-cells too", variable=self.show_all_var,
            command=self._refresh_cells,
        ).pack(side="left")

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True, padx=(12, 0))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        columns = ("name", "lef", "cdl", "spice", "verilog", "liberty", "gds")
        self.cells_tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        widths = {"name": 260, "lef": 40, "cdl": 40, "spice": 50, "verilog": 60, "liberty": 55, "gds": 40}
        for col in columns:
            self.cells_tree.heading(col, text=col.title() if col != "gds" else "GDS")
            self.cells_tree.column(col, width=widths[col], anchor="w" if col == "name" else "center")
        self.cells_tree.grid(row=0, column=0, sticky="nsew")
        self.cells_tree.bind("<<TreeviewSelect>>", self._on_cell_select)
        scroll = ttk.Scrollbar(left, orient="vertical", command=self.cells_tree.yview)
        self.cells_tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        self.detail_var = tk.StringVar(value="Select a cell.")
        ttk.Label(right, textvariable=self.detail_var, font=("TkDefaultFont", 10, "bold"), wraplength=280).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        self.view_buttons: dict[str, ttk.Button] = {}
        for i, key in enumerate(("lef", "cdl", "spice", "verilog"), start=1):
            btn = ttk.Button(right, text=f"View {key.upper()}", command=lambda k=key: self._view(k), state="disabled")
            btn.grid(row=i, column=0, sticky="ew", pady=2)
            self.view_buttons[key] = btn

        ttk.Label(right, text="Liberty (one per real corner file):").grid(
            row=5, column=0, sticky="w", pady=(10, 2)
        )
        self.liberty_list = tk.Listbox(right, height=6)
        self.liberty_list.grid(row=6, column=0, sticky="ew")
        self.liberty_list.bind("<Double-Button-1>", self._view_selected_liberty)

    # -- data ---------------------------------------------------------------

    def load(self):
        self.families = cells_mod.discover_families(self.pdk_root)
        self.family_combo["values"] = self.families
        if self.families and not self.family_var.get():
            self.family_var.set(self.families[0])
        self._refresh_cells()

    def _refresh_cells(self):
        for row in self.cells_tree.get_children():
            self.cells_tree.delete(row)
        family = self.family_var.get()
        if not family:
            self.summary_var.set("No families found -- has ihp/fetch.py been run?")
            self.cell_index = {}
            self._show_cell(None)
            return

        self.cell_index = cells_mod.build_cell_index(self.pdk_root, family)
        show_all = self.show_all_var.get()
        shown = 0
        for name in sorted(self.cell_index):
            cv = self.cell_index[name]
            if not show_all and cv.lef_macro is None:
                continue
            shown += 1
            self.cells_tree.insert(
                "", "end", iid=name,
                values=(
                    name,
                    _CHECK if cv.lef_macro else "",
                    _CHECK if cv.cdl_cell else "",
                    _CHECK if cv.spice_cell else "",
                    _CHECK if cv.verilog_module else "",
                    len(cv.liberty_entries) or "",
                    _CHECK if cv.gds_present else "",
                ),
            )

        total = len(self.cell_index)
        if total == 0:
            note = " (GDS-only family, no real per-cell split exists to index -- see docs/ihp_vs_open_pdks.md)" if family else ""
            self.summary_var.set(f"0 cells found for {family}{note}")
        else:
            self.summary_var.set(f"{shown} of {total} real cell(s) shown for {family}" + ("" if show_all else " (top-level only)"))

        if self.cells_tree.get_children():
            first = self.cells_tree.get_children()[0]
            self.cells_tree.selection_set(first)
            self._show_cell(self.cell_index[first])
        else:
            self._show_cell(None)

    def _on_cell_select(self, _event=None):
        selection = self.cells_tree.selection()
        cv = self.cell_index.get(selection[0]) if selection else None
        self._show_cell(cv)

    def _show_cell(self, cv: cells_mod.CellViews | None):
        self.current_cell = cv
        self.liberty_list.delete(0, "end")
        if cv is None:
            self.detail_var.set("Select a cell.")
            for btn in self.view_buttons.values():
                btn.configure(state="disabled")
            return

        self.detail_var.set(f"{cv.name}  ({cv.family})")
        self.view_buttons["lef"].configure(state="normal" if cv.lef_macro else "disabled")
        self.view_buttons["cdl"].configure(state="normal" if cv.cdl_cell else "disabled")
        self.view_buttons["spice"].configure(state="normal" if cv.spice_cell else "disabled")
        self.view_buttons["verilog"].configure(state="normal" if cv.verilog_module else "disabled")
        for cell_entry, path in cv.liberty_entries:
            self.liberty_list.insert("end", path.name)

    def _view(self, key: str):
        cv = self.current_cell
        if cv is None:
            return
        if key == "lef" and cv.lef_source is not None:
            # LEF is parsed structurally (no real source-line tracking
            # yet -- see README's Future Work), so this opens the real
            # file without a precise scroll target, unlike the other
            # three, which do.
            view_file_dialog(self, cv.lef_source)
        elif key == "cdl" and cv.cdl_cell is not None and cv.cdl_source is not None:
            view_file_dialog(self, cv.cdl_source, cv.cdl_cell.start_line, cv.cdl_cell.end_line)
        elif key == "spice" and cv.spice_cell is not None and cv.spice_source is not None:
            view_file_dialog(self, cv.spice_source, cv.spice_cell.start_line, cv.spice_cell.end_line)
        elif key == "verilog" and cv.verilog_module is not None and cv.verilog_source is not None:
            view_file_dialog(self, cv.verilog_source, cv.verilog_module.start_line, cv.verilog_module.end_line)

    def _view_selected_liberty(self, _event=None):
        cv = self.current_cell
        if cv is None:
            return
        selection = self.liberty_list.curselection()
        if not selection:
            return
        cell_entry, path = cv.liberty_entries[selection[0]]
        view_file_dialog(self, path, cell_entry.start_line, cell_entry.end_line)

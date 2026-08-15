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

**Library Manager-registered entries show up here too**, not just
real ones -- a ``✓`` marks a real view, a ``+`` a project-authored one
registered via the Library Manager with no real ``libs.ref/``
counterpart (only for a cell already known from some real view; a
wholly new, registered-only cell stays the Library Manager's own job,
not this tab's -- see ``ihp/cells.py``'s own docstring).

Defaults to only real, top-level cells (ones with a real LEF macro --
the physically instantiable ones); a real netlist can contain many more
internal sub-elements with no LEF of their own (confirmed: IHP's own
``sg13g2_sram`` CDL files alone define 2338 real subckts, only 28 of
which are the real, top-level hard macros) -- a **Show internal
sub-cells too** checkbox reveals the rest, off by default so the list
stays genuinely browsable.

**Editing**: LEF pins, CDL/SPICE/Verilog ports, and Liberty pins/
timing arcs are all genuinely structured-editable data (see the
Liberty/CDL/SPICE/Verilog sections below) -- Liberty's own real
lookup-table sub-groups (``cell_rise``/``cell_fall``/...) are the one
domain still deliberately read-only, see README's Future Work. The
**Pins** pane reuses
``pin_editor.PinEditor``, the same widget the **LEF** tab's own "LEF
Macros" sub-tab uses -- and, critically, the exact same in-memory
``LefMacro`` object: both tabs parse through ``App.get_parsed_lef``,
a single shared, App-owned cache (``ihp/cells.py``'s own
``build_cell_index`` takes an injectable ``get_lef`` hook for exactly
this), so a pin edited here is immediately visible on the LEF tab too,
and vice versa -- not two independently-drifting copies of the same
real pin list.

**GDS**: real, not just a presence flag, when ``klayout.db`` is
importable (``ihp/gds.py``, lazily imported) -- a real bounding box
and per-layer shape count for the selected cell's own real GDS
structure, shown as a plain text line (not a raw file View, since GDS
is binary) below the View buttons. Degrades honestly, not silently, if
``klayout.db`` isn't installed in this environment: "present, but not
parsed" rather than pretending there's nothing there.

**CDL/SPICE/Verilog ports** are also real, structured-editable data
(``ihp/netlist.py``'s ``NetlistPort``/``ihp/verilog.py``'s
``VerilogPort`` -- real per-port direction from a real CDL
``*.PININFO`` comment or real Verilog ``input``/``output``/``inout``
declarations, honestly blank where the real source has none, e.g.
every real SPICE file or SRAM's own CDL files). An **Edit ... Ports**
button next to each real **View** button opens a small modal dialog
(``port_dialog.edit_ports_dialog``) hosting ``port_editor.PortEditor``,
the same commit-on-switch shape ``pin_editor.PinEditor`` uses. Like
LEF pins, these parse through a shared, App-owned cache
(``App.get_parsed_netlist``/``get_parsed_verilog``) so an edit survives
a family switch -- the exact same real bug class already found and
fixed for LEF pins, applied here from the start rather than
rediscovered.

**Liberty pins/timing arcs** are also editable, via an **Edit Pins/
Timing** button below the Liberty corner-file list -- real per-pin
direction/capacitance/function and, for a selected pin, its own real
timing arcs (related_pin/timing_type/timing_sense/when), *not* the
real lookup tables (``cell_rise``/``cell_fall``/...) those arcs may
carry -- see ``ihp/liberty.py``'s own docstring for why those stay
read-only. Operates on whichever real corner file is selected in the
listbox (or the first one, if none is), through the same kind of
shared cache (``App.get_parsed_liberty``) as every other By Cell
editor here.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .. import export as export_mod
from ..ihp import cells as cells_mod
from ..ihp import library_index as li_mod
from ..ihp import netlist as netlist_mod
from ..ihp import verilog as verilog_mod
from .file_view_dialog import view_file_dialog
from .liberty_dialog import edit_liberty_dialog
from .list_filter import build_filter_row, matches
from .pin_editor import PinEditor
from .port_dialog import edit_ports_dialog

_CHECK = "✓"
_REGISTERED = "+"
"""Shown in a By Cell column when a cell has no *real* view of a given
kind, but does have a project-authored one registered via the Library
Manager (``CellViews.registered_views``) -- distinct from ``_CHECK``,
matching the Library Manager's own "real"/"(project)" tagging."""


class CellHubView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pdk_root = app.pdk_root
        self.families: list[str] = []
        self.cell_index: dict[str, cells_mod.CellViews] = {}
        self.current_cell: cells_mod.CellViews | None = None
        self._filter_query = ""

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
        build_filter_row(top, self._on_filter_changed)

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True, padx=(12, 0))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=2)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        ttk.Label(
            left, foreground="#616161",
            text=f"{_CHECK} real   {_REGISTERED} project (Library Manager, no real libs.ref/ view)",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        columns = ("name", "lef", "cdl", "spice", "verilog", "liberty", "gds", "user")
        self.cells_tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        widths = {"name": 220, "lef": 40, "cdl": 40, "spice": 50, "verilog": 60, "liberty": 55, "gds": 40, "user": 45}
        for col in columns:
            self.cells_tree.heading(col, text=col.title() if col != "gds" else "GDS")
            self.cells_tree.column(col, width=widths[col], anchor="w" if col == "name" else "center")
        self.cells_tree.grid(row=1, column=0, sticky="nsew")
        self.cells_tree.bind("<<TreeviewSelect>>", self._on_cell_select)
        scroll = ttk.Scrollbar(left, orient="vertical", command=self.cells_tree.yview)
        self.cells_tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky="ns")

        middle = ttk.Frame(body)
        middle.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        middle.columnconfigure(0, weight=1)

        self.detail_var = tk.StringVar(value="Select a cell.")
        ttk.Label(middle, textvariable=self.detail_var, font=("TkDefaultFont", 10, "bold"), wraplength=220).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        self.view_buttons: dict[str, ttk.Button] = {}
        self.edit_ports_buttons: dict[str, ttk.Button] = {}
        row = 1
        for key in ("lef", "cdl", "spice", "verilog"):
            row_frame = ttk.Frame(middle)
            row_frame.grid(row=row, column=0, sticky="ew", pady=2)
            btn = ttk.Button(row_frame, text=f"View {key.upper()}", command=lambda k=key: self._view(k), state="disabled")
            btn.pack(side="left")
            self.view_buttons[key] = btn
            if key != "lef":
                # LEF's own structured editing lives in the Pins pane
                # (its pin *content* is editable, not its port list --
                # a macro's real pins aren't added/removed the way a
                # netlist/module's real ports are). CDL/SPICE/Verilog
                # have no such pane, so they get their own small button.
                edit_btn = ttk.Button(
                    row_frame, text="Edit Ports", command=lambda k=key: self._edit_ports(k), state="disabled",
                )
                edit_btn.pack(side="left", padx=(4, 0))
                self.edit_ports_buttons[key] = edit_btn
            row += 1

        self.gds_var = tk.StringVar()
        ttk.Label(middle, textvariable=self.gds_var, foreground="#444", wraplength=220, justify="left").grid(
            row=row, column=0, sticky="w", pady=(6, 0)
        )
        row += 1

        ttk.Label(middle, text="Liberty (one per real corner file, double-click to view):").grid(
            row=row, column=0, sticky="w", pady=(10, 2)
        )
        row += 1
        self.liberty_list = tk.Listbox(middle, height=6)
        self.liberty_list.grid(row=row, column=0, sticky="ew")
        self.liberty_list.bind("<Double-Button-1>", self._view_selected_liberty)
        row += 1
        ttk.Button(middle, text="Edit Pins/Timing", command=self._edit_selected_liberty).grid(
            row=row, column=0, sticky="ew", pady=(2, 0)
        )
        row += 1

        ttk.Label(middle, text="User Models (double-click to view; link in Simulation > User Models):").grid(
            row=row, column=0, sticky="w", pady=(10, 2)
        )
        row += 1
        self.user_models_list = tk.Listbox(middle, height=4)
        self.user_models_list.grid(row=row, column=0, sticky="ew")
        self.user_models_list.bind("<Double-Button-1>", self._view_selected_user_model)

        right = ttk.Frame(body)
        right.grid(row=0, column=2, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self.pins_header_var = tk.StringVar(value="Pins")
        ttk.Label(right, textvariable=self.pins_header_var, font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self.pin_editor = PinEditor(right)
        self.pin_editor.grid(row=1, column=0, sticky="nsew")
        self.no_lef_label = ttk.Label(
            right, text="This cell has no real LEF macro -- nothing to edit here.\n"
            "(A macro-less internal sub-cell, or this family/view has no LEF entry.)",
            foreground="#666", wraplength=260, justify="left",
        )

    # -- persistence hooks (project_io.py) -----------------------------------

    def commit_pending_edits(self):
        """Flushes whatever's mid-edit in the Pins form into its
        ``LefPin`` before the caller reads/saves state -- the same
        underlying ``LefMacro``/``LefPin`` objects the LEF tab saves,
        since both share ``App.lef_cache``."""

        self.pin_editor.commit_pending_edits()

    # -- data ---------------------------------------------------------------

    @staticmethod
    def _mark(cv: cells_mod.CellViews, real_present: bool, view_kind: str) -> str:
        if real_present:
            return _CHECK
        return _REGISTERED if view_kind in cv.registered_views else ""

    def _registered_by_cell(self, family: str) -> dict[str, dict[str, Path]]:
        """This family's own ``library_index.yaml`` entries with
        ``source == "registered"`` -- e.g. a hand-authored LEF/CDL
        registered via the Library Manager's own **Add...**, with no
        real ``libs.ref/`` counterpart -- reshaped from
        ``merged_entries``'s own ``(cell, view_kind) -> ViewEntry``
        into the plain ``cell -> view_kind -> path`` shape
        ``cells.build_cell_index`` expects (see its own docstring for
        why it stays decoupled from ``library_index.py``'s own
        dataclasses)."""

        result: dict[str, dict[str, Path]] = {}
        entries = li_mod.merged_entries(self.pdk_root, export_mod.PROJECT_ROOT, family)
        for (cell, view_kind), entry in entries.items():
            if entry.source != "registered":
                continue
            result.setdefault(cell, {})[view_kind] = entry.path
        return result

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

        self.cell_index = cells_mod.build_cell_index(
            self.pdk_root, family,
            get_lef=self.app.get_parsed_lef,
            get_netlist_cells=self.app.get_parsed_netlist,
            get_verilog_modules=self.app.get_parsed_verilog,
            get_liberty_cells=self.app.get_parsed_liberty,
            user_models_by_cell=self.app.user_models_by_cell(),
            registered_by_cell=self._registered_by_cell(family),
        )
        show_all = self.show_all_var.get()
        shown = 0
        for name in sorted(self.cell_index):
            cv = self.cell_index[name]
            # A wholly new, user-defined cell (a real user model linked
            # to a name with no real LEF macro of its own) stays
            # visible by default too -- it's the whole point of "Show
            # internal sub-cells too" being off shouldn't also hide a
            # cell the user is actively authoring.
            if not show_all and cv.lef_macro is None and not cv.user_models:
                continue
            if not matches(self._filter_query, name):
                continue
            shown += 1
            self.cells_tree.insert(
                "", "end", iid=name,
                values=(
                    name,
                    self._mark(cv, cv.lef_macro is not None, "lef"),
                    self._mark(cv, cv.cdl_cell is not None, "cdl"),
                    self._mark(cv, cv.spice_cell is not None, "spice"),
                    self._mark(cv, cv.verilog_module is not None, "verilog"),
                    len(cv.liberty_entries) or self._mark(cv, False, "liberty"),
                    self._mark(cv, cv.gds_present, "gds"),
                    len(cv.user_models) or "",
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

    def _on_filter_changed(self, query: str):
        self._filter_query = query
        self._refresh_cells()

    def _on_cell_select(self, _event=None):
        selection = self.cells_tree.selection()
        cv = self.cell_index.get(selection[0]) if selection else None
        self._show_cell(cv)

    def _show_cell(self, cv: cells_mod.CellViews | None):
        self.current_cell = cv
        self.liberty_list.delete(0, "end")
        self.user_models_list.delete(0, "end")
        if cv is None:
            self.detail_var.set("Select a cell.")
            for btn in self.view_buttons.values():
                btn.configure(state="disabled")
            for btn in self.edit_ports_buttons.values():
                btn.configure(state="disabled")
            self.gds_var.set("")
            self.pin_editor.set_macro(None)
            self._show_pin_editor(False)
            return

        self.detail_var.set(f"{cv.name}  ({cv.family})")
        self.view_buttons["lef"].configure(state="normal" if cv.lef_macro else "disabled")
        self.view_buttons["cdl"].configure(state="normal" if cv.cdl_cell else "disabled")
        self.view_buttons["spice"].configure(state="normal" if cv.spice_cell else "disabled")
        self.view_buttons["verilog"].configure(state="normal" if cv.verilog_module else "disabled")
        self.edit_ports_buttons["cdl"].configure(state="normal" if cv.cdl_cell else "disabled")
        self.edit_ports_buttons["spice"].configure(state="normal" if cv.spice_cell else "disabled")
        self.edit_ports_buttons["verilog"].configure(state="normal" if cv.verilog_module else "disabled")
        for cell_entry, path in cv.liberty_entries:
            self.liberty_list.insert("end", path.name)
        for module, path, kind in cv.user_models:
            self.user_models_list.insert("end", f"{module.name}  ({kind}, {path.name})")

        if cv.gds_cell is not None:
            l, b, r, t = cv.gds_cell.bbox_microns or (0, 0, 0, 0)
            self.gds_var.set(
                f"GDS: {r - l:.2f} x {t - b:.2f} µm bbox, "
                f"{cv.gds_cell.total_shapes} real shape(s) across {len(cv.gds_cell.shapes_by_layer)} layer(s)"
            )
        elif cv.gds_present:
            self.gds_var.set("GDS: present, but not parsed (klayout.db unavailable here)")
        else:
            self.gds_var.set("GDS: none")

        self.pins_header_var.set(f"Pins -- {cv.name}" if cv.lef_macro else "Pins")
        self.pin_editor.set_macro(cv.lef_macro)
        self._show_pin_editor(cv.lef_macro is not None)

    def _show_pin_editor(self, show: bool):
        if show:
            self.no_lef_label.grid_forget()
            self.pin_editor.grid(row=1, column=0, sticky="nsew")
        else:
            self.pin_editor.grid_forget()
            self.no_lef_label.grid(row=1, column=0, sticky="new")

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

    def _edit_ports(self, key: str):
        cv = self.current_cell
        if cv is None:
            return
        if key == "cdl" and cv.cdl_cell is not None:
            edit_ports_dialog(
                self, f"CDL Ports -- {cv.name}", cv.cdl_cell.ports,
                lambda name: netlist_mod.NetlistPort(name=name),
            )
        elif key == "spice" and cv.spice_cell is not None:
            edit_ports_dialog(
                self, f"SPICE Ports -- {cv.name}", cv.spice_cell.ports,
                lambda name: netlist_mod.NetlistPort(name=name),
            )
        elif key == "verilog" and cv.verilog_module is not None:
            edit_ports_dialog(
                self, f"Verilog Ports -- {cv.name}", cv.verilog_module.ports,
                lambda name: verilog_mod.VerilogPort(name=name), has_width=True,
            )

    def _view_selected_liberty(self, _event=None):
        cv = self.current_cell
        if cv is None:
            return
        selection = self.liberty_list.curselection()
        if not selection:
            return
        cell_entry, path = cv.liberty_entries[selection[0]]
        view_file_dialog(self, path, cell_entry.start_line, cell_entry.end_line)

    def _edit_selected_liberty(self):
        cv = self.current_cell
        if cv is None or not cv.liberty_entries:
            return
        selection = self.liberty_list.curselection()
        index = selection[0] if selection else 0
        cell_entry, path = cv.liberty_entries[index]
        edit_liberty_dialog(self, f"Liberty Pins/Timing -- {cv.name} ({path.name})", cell_entry)

    def _view_selected_user_model(self, _event=None):
        cv = self.current_cell
        if cv is None:
            return
        selection = self.user_models_list.curselection()
        if not selection:
            return
        module, path, _kind = cv.user_models[selection[0]]
        view_file_dialog(self, path, module.start_line, module.end_line)

"""A real Liberty pin/timing-arc editor: three stacked panes, the same
commit-on-switch pattern every editor here uses -- **Pins**
(name/direction/capacitance/function), for whichever pin is currently
selected its own **Timing Arcs** (related_pin/timing_type/
timing_sense/when), and, for whichever arc is currently selected, its
own real **Lookup Tables** (``cell_rise``/``cell_fall``/
``rise_transition``/``fall_transition``, each a real ``index_1``/
``index_2``/``values`` table). The lookup-table pane is **read-only,
no New/Delete, no editable fields** -- see ``pdklib/liberty.py``'s own
docstring for why: display only, the same "bounded, not a full
parser/editor" precedent every other read-only view in this project
already follows (GDS bbox/shape-count, LEF PORT rect geometry).

Switching pins commits whatever's pending in *both* the pin form and
the arc form (a half-edited arc shouldn't survive a pin switch any
more than a half-edited pin should survive a cell switch). Switching
arcs simply reloads the (read-only) lookup-table pane -- there is no
form to commit there.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..pdklib import liberty as liberty_mod


class LibertyPinEditor(ttk.Frame):
    def __init__(self, parent, on_change=None):
        super().__init__(parent)
        self.on_change = on_change
        self.cell: liberty_mod.LibertyCell | None = None
        self.current_pin: liberty_mod.LibertyPin | None = None
        self.current_arc: liberty_mod.LibertyTimingArc | None = None
        self._suspend_pin_trace = False
        self._suspend_arc_trace = False
        self._pin_by_iid: dict[str, liberty_mod.LibertyPin] = {}
        self._arc_by_iid: dict[str, liberty_mod.LibertyTimingArc] = {}
        self._lt_by_iid: dict[str, liberty_mod.LibertyLookupTable] = {}

        self._build()

    # -- layout -----------------------------------------------------------

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        pin_frame = ttk.LabelFrame(self, text="Pins")
        pin_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        pin_frame.columnconfigure(0, weight=1)
        pin_frame.columnconfigure(1, weight=1)
        pin_frame.rowconfigure(1, weight=1)

        pin_btn_row = ttk.Frame(pin_frame)
        pin_btn_row.grid(row=0, column=0, sticky="ew", pady=(4, 2))
        ttk.Button(pin_btn_row, text="New Pin", command=self._new_pin).pack(side="left")
        ttk.Button(pin_btn_row, text="Delete Pin", command=self._delete_pin).pack(side="left", padx=(6, 0))

        pin_columns = ("name", "direction", "capacitance", "function")
        self.pins_tree = ttk.Treeview(pin_frame, columns=pin_columns, show="headings", selectmode="browse", height=6)
        for col, width in zip(pin_columns, (100, 80, 90, 180)):
            self.pins_tree.heading(col, text=col.title())
            self.pins_tree.column(col, width=width, anchor="w")
        self.pins_tree.grid(row=1, column=0, sticky="nsew", padx=(4, 4))
        self.pins_tree.bind("<<TreeviewSelect>>", self._on_pin_select)

        pin_form = ttk.Frame(pin_frame)
        pin_form.grid(row=1, column=1, sticky="new", padx=(0, 4))
        pin_form.columnconfigure(1, weight=1)
        self.pin_vars: dict[str, tk.StringVar] = {}
        for row, (field, label) in enumerate((
            ("name", "Name"), ("direction", "Direction"),
            ("capacitance", "Capacitance"), ("function", "Function"),
        )):
            ttk.Label(pin_form, text=label).grid(row=row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_pin_field_changed)
            ttk.Entry(pin_form, textvariable=var).grid(row=row, column=1, sticky="ew", pady=2)
            self.pin_vars[field] = var

        arc_frame = ttk.LabelFrame(self, text="Timing Arcs (for the selected pin)")
        arc_frame.grid(row=1, column=0, sticky="nsew")
        arc_frame.columnconfigure(0, weight=1)
        arc_frame.columnconfigure(1, weight=1)
        arc_frame.rowconfigure(1, weight=1)

        arc_btn_row = ttk.Frame(arc_frame)
        arc_btn_row.grid(row=0, column=0, sticky="ew", pady=(4, 2))
        ttk.Button(arc_btn_row, text="New Arc", command=self._new_arc).pack(side="left")
        ttk.Button(arc_btn_row, text="Delete Arc", command=self._delete_arc).pack(side="left", padx=(6, 0))

        arc_columns = ("related_pin", "timing_type", "timing_sense", "when")
        self.arcs_tree = ttk.Treeview(arc_frame, columns=arc_columns, show="headings", selectmode="browse", height=6)
        for col, width in zip(arc_columns, (90, 120, 100, 160)):
            self.arcs_tree.heading(col, text=col.replace("_", " ").title())
            self.arcs_tree.column(col, width=width, anchor="w")
        self.arcs_tree.grid(row=1, column=0, sticky="nsew", padx=(4, 4))
        self.arcs_tree.bind("<<TreeviewSelect>>", self._on_arc_select)

        arc_form = ttk.Frame(arc_frame)
        arc_form.grid(row=1, column=1, sticky="new", padx=(0, 4))
        arc_form.columnconfigure(1, weight=1)
        self.arc_vars: dict[str, tk.StringVar] = {}
        for row, (field, label) in enumerate((
            ("related_pin", "Related Pin"), ("timing_type", "Timing Type"),
            ("timing_sense", "Timing Sense"), ("when", "When"),
        )):
            ttk.Label(arc_form, text=label).grid(row=row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_arc_field_changed)
            ttk.Entry(arc_form, textvariable=var).grid(row=row, column=1, sticky="ew", pady=2)
            self.arc_vars[field] = var

        lt_frame = ttk.LabelFrame(self, text="Lookup Tables (for the selected arc) -- read-only")
        lt_frame.grid(row=2, column=0, sticky="nsew", pady=(6, 0))
        lt_frame.columnconfigure(0, weight=1)
        lt_frame.columnconfigure(1, weight=1)
        lt_frame.rowconfigure(0, weight=1)

        lt_columns = ("kind", "template_name", "index_1", "index_2")
        self.lt_tree = ttk.Treeview(lt_frame, columns=lt_columns, show="headings", selectmode="browse", height=4)
        for col, label, width in zip(lt_columns, ("Kind", "Template", "Index 1", "Index 2"), (110, 160, 60, 60)):
            self.lt_tree.heading(col, text=label)
            self.lt_tree.column(col, width=width, anchor="w")
        self.lt_tree.grid(row=0, column=0, sticky="nsew", padx=(4, 4), pady=(4, 4))
        self.lt_tree.bind("<<TreeviewSelect>>", self._on_lt_select)

        self.lt_values_text = tk.Text(lt_frame, height=6, width=50, state="disabled", wrap="none")
        self.lt_values_text.grid(row=0, column=1, sticky="nsew", padx=(0, 4), pady=(4, 4))

    # -- pins -----------------------------------------------------------------

    @staticmethod
    def _pin_iid(pin: liberty_mod.LibertyPin) -> str:
        return str(id(pin))

    def _pin_row_values(self, pin: liberty_mod.LibertyPin) -> tuple:
        return (pin.name, pin.direction, "" if pin.capacitance is None else pin.capacitance, pin.function)

    def set_cell(self, cell: liberty_mod.LibertyCell | None):
        self._commit_pin_form()
        self._commit_arc_form()
        self.cell = cell
        for row in self.pins_tree.get_children():
            self.pins_tree.delete(row)
        self._pin_by_iid = {}
        if cell is None:
            self._load_pin_into_form(None)
            return
        for pin in cell.pins:
            iid = self._pin_iid(pin)
            self._pin_by_iid[iid] = pin
            self.pins_tree.insert("", "end", iid=iid, values=self._pin_row_values(pin))
        if cell.pins:
            self.pins_tree.selection_set(self._pin_iid(cell.pins[0]))
            self._load_pin_into_form(cell.pins[0])
        else:
            self._load_pin_into_form(None)

    def _on_pin_select(self, _event=None):
        self._commit_pin_form()
        self._commit_arc_form()
        selection = self.pins_tree.selection()
        pin = self._pin_by_iid.get(selection[0]) if selection else None
        self._load_pin_into_form(pin)

    def _load_pin_into_form(self, pin: liberty_mod.LibertyPin | None):
        self._suspend_pin_trace = True
        self.current_pin = pin
        if pin is None:
            for var in self.pin_vars.values():
                var.set("")
        else:
            self.pin_vars["name"].set(pin.name)
            self.pin_vars["direction"].set(pin.direction)
            self.pin_vars["capacitance"].set("" if pin.capacitance is None else str(pin.capacitance))
            self.pin_vars["function"].set(pin.function)
        self._suspend_pin_trace = False
        self._load_arcs_for_pin(pin)

    def _commit_pin_form(self):
        pin = self.current_pin
        if pin is None:
            return
        pin.name = self.pin_vars["name"].get().strip() or pin.name
        pin.direction = self.pin_vars["direction"].get()
        raw_cap = self.pin_vars["capacitance"].get().strip()
        try:
            pin.capacitance = float(raw_cap) if raw_cap else None
        except ValueError:
            pass
        pin.function = self.pin_vars["function"].get()

    def commit_pending_edits(self):
        self._commit_pin_form()
        self._commit_arc_form()

    def _on_pin_field_changed(self, *_args):
        if self._suspend_pin_trace:
            return
        self._commit_pin_form()
        if self.current_pin is not None:
            iid = self._pin_iid(self.current_pin)
            if self.pins_tree.exists(iid):
                self.pins_tree.item(iid, values=self._pin_row_values(self.current_pin))
        if self.on_change is not None:
            self.on_change()

    def _new_pin(self):
        if self.cell is None:
            return
        self._commit_pin_form()
        pin = liberty_mod.LibertyPin(name=f"NEW_PIN_{len(self.cell.pins) + 1}")
        self.cell.pins.append(pin)
        iid = self._pin_iid(pin)
        self._pin_by_iid[iid] = pin
        self.pins_tree.insert("", "end", iid=iid, values=self._pin_row_values(pin))
        self.pins_tree.selection_set(iid)
        self.pins_tree.see(iid)
        if self.on_change is not None:
            self.on_change()

    def _delete_pin(self):
        if self.cell is None:
            return
        selection = self.pins_tree.selection()
        if not selection:
            return
        pin = self._pin_by_iid.get(selection[0])
        if pin is None:
            return
        self.cell.pins.remove(pin)
        self.current_pin = None
        self.pins_tree.delete(selection[0])
        del self._pin_by_iid[selection[0]]
        remaining = self.pins_tree.get_children()
        if remaining:
            self.pins_tree.selection_set(remaining[0])
            self._load_pin_into_form(self._pin_by_iid[remaining[0]])
        else:
            self._load_pin_into_form(None)
        if self.on_change is not None:
            self.on_change()

    # -- timing arcs (nested under the current pin) --------------------------

    @staticmethod
    def _arc_iid(arc: liberty_mod.LibertyTimingArc) -> str:
        return str(id(arc))

    def _arc_row_values(self, arc: liberty_mod.LibertyTimingArc) -> tuple:
        return (arc.related_pin, arc.timing_type, arc.timing_sense, arc.when)

    def _load_arcs_for_pin(self, pin: liberty_mod.LibertyPin | None):
        for row in self.arcs_tree.get_children():
            self.arcs_tree.delete(row)
        self._arc_by_iid = {}
        if pin is None:
            self._load_arc_into_form(None)
            return
        for arc in pin.timing_arcs:
            iid = self._arc_iid(arc)
            self._arc_by_iid[iid] = arc
            self.arcs_tree.insert("", "end", iid=iid, values=self._arc_row_values(arc))
        if pin.timing_arcs:
            self.arcs_tree.selection_set(self._arc_iid(pin.timing_arcs[0]))
            self._load_arc_into_form(pin.timing_arcs[0])
        else:
            self._load_arc_into_form(None)

    def _on_arc_select(self, _event=None):
        self._commit_arc_form()
        selection = self.arcs_tree.selection()
        arc = self._arc_by_iid.get(selection[0]) if selection else None
        self._load_arc_into_form(arc)

    def _load_arc_into_form(self, arc: liberty_mod.LibertyTimingArc | None):
        self._suspend_arc_trace = True
        self.current_arc = arc
        if arc is None:
            for var in self.arc_vars.values():
                var.set("")
        else:
            self.arc_vars["related_pin"].set(arc.related_pin)
            self.arc_vars["timing_type"].set(arc.timing_type)
            self.arc_vars["timing_sense"].set(arc.timing_sense)
            self.arc_vars["when"].set(arc.when)
        self._suspend_arc_trace = False
        self._load_lookup_tables_for_arc(arc)

    def _commit_arc_form(self):
        arc = self.current_arc
        if arc is None:
            return
        arc.related_pin = self.arc_vars["related_pin"].get()
        arc.timing_type = self.arc_vars["timing_type"].get()
        arc.timing_sense = self.arc_vars["timing_sense"].get()
        arc.when = self.arc_vars["when"].get()

    def _on_arc_field_changed(self, *_args):
        if self._suspend_arc_trace:
            return
        self._commit_arc_form()
        if self.current_arc is not None:
            iid = self._arc_iid(self.current_arc)
            if self.arcs_tree.exists(iid):
                self.arcs_tree.item(iid, values=self._arc_row_values(self.current_arc))
        if self.on_change is not None:
            self.on_change()

    def _new_arc(self):
        if self.current_pin is None:
            return
        self._commit_arc_form()
        arc = liberty_mod.LibertyTimingArc()
        self.current_pin.timing_arcs.append(arc)
        iid = self._arc_iid(arc)
        self._arc_by_iid[iid] = arc
        self.arcs_tree.insert("", "end", iid=iid, values=self._arc_row_values(arc))
        self.arcs_tree.selection_set(iid)
        self.arcs_tree.see(iid)
        if self.on_change is not None:
            self.on_change()

    def _delete_arc(self):
        if self.current_pin is None:
            return
        selection = self.arcs_tree.selection()
        if not selection:
            return
        arc = self._arc_by_iid.get(selection[0])
        if arc is None:
            return
        self.current_pin.timing_arcs.remove(arc)
        self.current_arc = None
        self.arcs_tree.delete(selection[0])
        del self._arc_by_iid[selection[0]]
        remaining = self.arcs_tree.get_children()
        if remaining:
            self.arcs_tree.selection_set(remaining[0])
            self._load_arc_into_form(self._arc_by_iid[remaining[0]])
        else:
            self._load_arc_into_form(None)
        if self.on_change is not None:
            self.on_change()

    # -- lookup tables (read-only, nested under the current arc) -------------

    @staticmethod
    def _lt_iid(table: liberty_mod.LibertyLookupTable) -> str:
        return str(id(table))

    @staticmethod
    def _lt_row_values(table: liberty_mod.LibertyLookupTable) -> tuple:
        index_1 = "" if table.index_1 is None else f"{len(table.index_1)} pts"
        index_2 = "" if table.index_2 is None else f"{len(table.index_2)} pts"
        return (table.kind, table.template_name, index_1, index_2)

    def _load_lookup_tables_for_arc(self, arc: liberty_mod.LibertyTimingArc | None):
        for row in self.lt_tree.get_children():
            self.lt_tree.delete(row)
        self._lt_by_iid = {}
        if arc is None or not arc.lookup_tables:
            self._show_lt_values(None)
            return
        for table in arc.lookup_tables:
            iid = self._lt_iid(table)
            self._lt_by_iid[iid] = table
            self.lt_tree.insert("", "end", iid=iid, values=self._lt_row_values(table))
        first_iid = self._lt_iid(arc.lookup_tables[0])
        self.lt_tree.selection_set(first_iid)
        self._show_lt_values(arc.lookup_tables[0])

    def _on_lt_select(self, _event=None):
        selection = self.lt_tree.selection()
        table = self._lt_by_iid.get(selection[0]) if selection else None
        self._show_lt_values(table)

    def _show_lt_values(self, table: liberty_mod.LibertyLookupTable | None):
        # Real, confirmed unit variance across this deck's own real
        # .lib files (e.g. sg13g2_stdcell's "1ns"/"(1,pf)" vs.
        # sg13g2_io_dummy's "1ps"/"(1,ff)") -- bare numbers are shown
        # with the cell's own real, declared time_unit, never assumed.
        # index_1/index_2's own real unit depends on which variable the
        # referenced table template binds it to (variable_1/variable_2,
        # a separate real group this parser doesn't resolve -- see
        # pdklib/liberty.py's own docstring), so they're shown unitless
        # rather than guessed.
        self.lt_values_text.config(state="normal")
        self.lt_values_text.delete("1.0", "end")
        if table is not None:
            lines = []
            if table.index_1 is not None:
                lines.append("index_1 (unit per real template, not resolved): " + ", ".join(str(v) for v in table.index_1))
            if table.index_2 is not None:
                lines.append("index_2 (unit per real template, not resolved): " + ", ".join(str(v) for v in table.index_2))
            time_unit = (self.cell.time_unit if self.cell is not None and self.cell.time_unit else "unit unknown")
            lines.append(f"values (real time_unit: {time_unit}):")
            for row in table.values:
                lines.append("  " + ", ".join(str(v) for v in row))
            self.lt_values_text.insert("1.0", "\n".join(lines))
        self.lt_values_text.config(state="disabled")

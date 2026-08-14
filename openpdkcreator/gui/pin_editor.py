"""A reusable macro-pin editor: a pin list + New/Delete buttons + a
Name/Direction/Use form, the same commit-on-switch pattern every other
editable view here uses. Extracted out of ``lef_view.py`` so the LEF
tab's own "LEF Macros" sub-tab and ``cell_hub_view.py``'s per-cell
detail pane can share one real, already-bug-fixed implementation
rather than two copies drifting apart.

**A real bug, found and fixed once, here for good**: a combobox's own
``<<ComboboxSelected>>`` event only fires on a dropdown *pick* -- a
typed or programmatic value change silently never commits without also
tracing the variable's own ``write`` event (confirmed by a real, driven
test while first building this in ``lef_view.py``: ``.set("POWER")``
didn't take effect until a later, unrelated commit-on-switch happened
to read the same, by-then-updated variable). Direction/Use are
deliberately free-typable comboboxes, not ``readonly`` -- IHP's real
data only has 3 real ``USE``/3 real ``DIRECTION`` values, but other
real, standard LEF PDKs can have more (e.g. ``CLOCK``).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..ihp import lef as lef_mod

DIRECTIONS = ("INPUT", "OUTPUT", "INOUT")
USES = ("SIGNAL", "POWER", "GROUND")


class PinEditor(ttk.Frame):
    """Shows/edits one ``LefMacro``'s pins at a time. Call
    ``set_macro(macro)`` to point it at a (possibly ``None``) macro --
    commits any pending edit to the previously-shown macro first, same
    as switching a file/row anywhere else in this project."""

    def __init__(self, parent, on_change=None):
        super().__init__(parent)
        self.macro: lef_mod.LefMacro | None = None
        self.current_pin: lef_mod.LefPin | None = None
        self._suspend_trace = False
        # Optional callback(macro), fired after any pin add/edit/
        # delete -- lets an embedder (CellHubView) refresh its own
        # summary display (e.g. a pin count column) without this
        # widget needing to know anything about that display.
        self.on_change = on_change

        self._build()

    # -- layout -----------------------------------------------------------

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        button_row = ttk.Frame(left)
        button_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(button_row, text="New Pin", command=self._new_pin).pack(side="left")
        ttk.Button(button_row, text="Delete Pin", command=self._delete_pin).pack(side="left", padx=(6, 0))

        pin_columns = ("name", "direction", "use", "ports")
        self.pins_tree = ttk.Treeview(left, columns=pin_columns, show="headings", selectmode="browse")
        for col, width in zip(pin_columns, (140, 80, 80, 220)):
            self.pins_tree.heading(col, text=col.replace("_", " ").title())
            self.pins_tree.column(col, width=width, anchor="w")
        self.pins_tree.grid(row=1, column=0, sticky="nsew")
        self.pins_tree.bind("<<TreeviewSelect>>", self._on_pin_select)

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right.columnconfigure(1, weight=1)

        self.pin_vars: dict[str, tk.StringVar] = {}
        form_row = 0

        def add_entry(field, label):
            nonlocal form_row
            ttk.Label(right, text=label).grid(row=form_row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_pin_field_changed)
            ttk.Entry(right, textvariable=var).grid(row=form_row, column=1, sticky="ew", pady=2)
            self.pin_vars[field] = var
            form_row += 1

        def add_combo(field, label, values):
            nonlocal form_row
            ttk.Label(right, text=label).grid(row=form_row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_pin_field_changed)
            combo = ttk.Combobox(right, textvariable=var, values=values)
            combo.grid(row=form_row, column=1, sticky="ew", pady=2)
            self.pin_vars[field] = var
            form_row += 1

        add_entry("name", "Name")
        add_combo("direction", "Direction", DIRECTIONS)
        add_combo("use", "Use", USES)

        ttk.Label(right, text="Ports (real drawn geometry -- read-only)").grid(
            row=form_row, column=0, columnspan=2, sticky="w", pady=(10, 2)
        )
        form_row += 1
        self.ports_text = tk.Text(right, height=6, width=30, state="disabled", font=("Courier", 9))
        self.ports_text.grid(row=form_row, column=0, columnspan=2, sticky="nsew", pady=2)
        right.rowconfigure(form_row, weight=1)

    # -- macro switching ------------------------------------------------------

    @staticmethod
    def _pin_iid(pin: lef_mod.LefPin) -> str:
        # Identity-based, not name-based: name is an editable field.
        return str(id(pin))

    def _pin_row_values(self, pin: lef_mod.LefPin) -> tuple:
        ports = ", ".join(f"{p.layer}:{p.rect_count}rect" for p in pin.ports)
        return (pin.name, pin.direction, pin.use, ports)

    def set_macro(self, macro: lef_mod.LefMacro | None):
        self._commit_form_to_pin()
        self.macro = macro
        for row in self.pins_tree.get_children():
            self.pins_tree.delete(row)
        self._pin_by_iid = {}
        if macro is None:
            self._load_pin_into_form(None)
            return
        for pin in macro.pins:
            iid = self._pin_iid(pin)
            self._pin_by_iid[iid] = pin
            self.pins_tree.insert("", "end", iid=iid, values=self._pin_row_values(pin))
        if macro.pins:
            self.pins_tree.selection_set(self._pin_iid(macro.pins[0]))
            self._load_pin_into_form(macro.pins[0])
        else:
            self._load_pin_into_form(None)

    def _on_pin_select(self, _event=None):
        self._commit_form_to_pin()
        selection = self.pins_tree.selection()
        pin = self._pin_by_iid.get(selection[0]) if selection else None
        self._load_pin_into_form(pin)

    def _load_pin_into_form(self, pin: lef_mod.LefPin | None):
        self._suspend_trace = True
        self.current_pin = pin
        if pin is None:
            for var in self.pin_vars.values():
                var.set("")
            ports_text = ""
        else:
            self.pin_vars["name"].set(pin.name)
            self.pin_vars["direction"].set(pin.direction)
            self.pin_vars["use"].set(pin.use)
            ports_text = "\n".join(f"{p.layer}: {p.rect_count} rect(s)" for p in pin.ports) or "(none)"
        self.ports_text.configure(state="normal")
        self.ports_text.delete("1.0", "end")
        self.ports_text.insert("1.0", ports_text)
        self.ports_text.configure(state="disabled")
        self._suspend_trace = False

    def _commit_form_to_pin(self):
        pin = self.current_pin
        if pin is None:
            return
        pin.name = self.pin_vars["name"].get().strip() or pin.name
        pin.direction = self.pin_vars["direction"].get()
        pin.use = self.pin_vars["use"].get()

    def commit_pending_edits(self):
        self._commit_form_to_pin()

    def _on_pin_field_changed(self, *_args):
        if self._suspend_trace:
            return
        self._commit_form_to_pin()
        if self.current_pin is not None:
            iid = self._pin_iid(self.current_pin)
            if self.pins_tree.exists(iid):
                self.pins_tree.item(iid, values=self._pin_row_values(self.current_pin))
        if self.on_change is not None:
            self.on_change(self.macro)

    def _new_pin(self):
        if self.macro is None:
            return
        self._commit_form_to_pin()
        pin = lef_mod.LefPin(name=f"NEW_PIN_{len(self.macro.pins) + 1}", direction="INPUT", use="SIGNAL")
        self.macro.pins.append(pin)
        iid = self._pin_iid(pin)
        self._pin_by_iid[iid] = pin
        self.pins_tree.insert("", "end", iid=iid, values=self._pin_row_values(pin))
        self.pins_tree.selection_set(iid)
        self.pins_tree.see(iid)
        if self.on_change is not None:
            self.on_change(self.macro)

    def _delete_pin(self):
        if self.macro is None:
            return
        selection = self.pins_tree.selection()
        if not selection:
            return
        pin = self._pin_by_iid.get(selection[0])
        if pin is None:
            return
        self.macro.pins.remove(pin)
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
            self.on_change(self.macro)

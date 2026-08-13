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
right, editable via New/Delete Pin and a form -- name/direction/use,
the same commit-on-switch pattern ``LayersView``/``RulesView`` already
use. Port geometry (real drawn rectangles) stays display-only -- editing
raw geometry is a real, separate, much bigger feature, out of scope
here). "View File" opens the real, selected ``.lef`` file directly
(``file_view_dialog.view_file_dialog``), which *can* also be edited,
as raw text.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..ihp import lef as lef_mod
from .file_view_dialog import view_file_dialog

DIRECTIONS = ("INPUT", "OUTPUT", "INOUT")
USES = ("SIGNAL", "POWER", "GROUND")


class LefView(ttk.Frame):
    def __init__(self, parent, pdk_root: Path):
        super().__init__(parent)
        self.pdk_root = pdk_root
        self.lef_files: dict[str, Path] = {}
        self.current: lef_mod.LefFile | None = None
        self.current_macro: lef_mod.LefMacro | None = None
        self.current_pin: lef_mod.LefPin | None = None
        self._suspend_trace = False

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
        frame.columnconfigure(2, weight=1)
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

        middle = ttk.Frame(frame)
        middle.grid(row=0, column=1, sticky="nsew", padx=4)
        middle.rowconfigure(1, weight=1)
        middle.columnconfigure(0, weight=1)

        pin_button_row = ttk.Frame(middle)
        pin_button_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(pin_button_row, text="New Pin", command=self._new_pin).pack(side="left")
        ttk.Button(pin_button_row, text="Delete Pin", command=self._delete_pin).pack(side="left", padx=(6, 0))

        pin_columns = ("name", "direction", "use", "ports")
        self.pins_tree = ttk.Treeview(middle, columns=pin_columns, show="headings", selectmode="browse")
        for col, width in zip(pin_columns, (140, 80, 80, 220)):
            self.pins_tree.heading(col, text=col.replace("_", " ").title())
            self.pins_tree.column(col, width=width, anchor="w")
        self.pins_tree.grid(row=1, column=0, sticky="nsew")
        self.pins_tree.bind("<<TreeviewSelect>>", self._on_pin_select)

        right = ttk.Frame(frame)
        right.grid(row=0, column=2, sticky="nsew", padx=(4, 0))
        right.columnconfigure(1, weight=1)

        self.pin_vars: dict[str, tk.StringVar] = {}
        pin_form_row = 0

        def add_entry(field, label):
            nonlocal pin_form_row
            ttk.Label(right, text=label).grid(row=pin_form_row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_pin_field_changed)
            ttk.Entry(right, textvariable=var).grid(row=pin_form_row, column=1, sticky="ew", pady=2)
            self.pin_vars[field] = var
            pin_form_row += 1

        def add_combo(field, label, values):
            nonlocal pin_form_row
            ttk.Label(right, text=label).grid(row=pin_form_row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            # Deliberately NOT state="readonly" (unlike LayersView's/
            # RulesView's own combos): a pin's real DIRECTION/USE could
            # be a value beyond the 3 confirmed in IHP's own data
            # (e.g. CLOCK, a real standard LEF USE keyword). Free typing
            # needs its own commit path -- a var trace, not just
            # <<ComboboxSelected>> (which only fires on a dropdown pick,
            # confirmed by a real test: typed/programmatic changes
            # silently never committed without this).
            var.trace_add("write", self._on_pin_field_changed)
            combo = ttk.Combobox(right, textvariable=var, values=values)
            combo.grid(row=pin_form_row, column=1, sticky="ew", pady=2)
            self.pin_vars[field] = var
            pin_form_row += 1

        add_entry("name", "Name")
        add_combo("direction", "Direction", DIRECTIONS)
        add_combo("use", "Use", USES)

        ttk.Label(right, text="Ports (real drawn geometry -- read-only)").grid(
            row=pin_form_row, column=0, columnspan=2, sticky="w", pady=(10, 2)
        )
        pin_form_row += 1
        self.ports_text = tk.Text(right, height=6, width=30, state="disabled", font=("Courier", 9))
        self.ports_text.grid(row=pin_form_row, column=0, columnspan=2, sticky="nsew", pady=2)
        right.rowconfigure(pin_form_row, weight=1)

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

        path = self.lef_files.get(self.file_var.get())
        if path is None:
            self.summary_var.set("No LEF data loaded -- has ihp/fetch.py been run?")
            self.current = None
            self._show_pins(None)
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
        else:
            self._show_pins(None)

    def _on_macro_select(self, _event=None):
        if self.current is None:
            return
        selection = self.macros_tree.selection()
        if not selection:
            self._show_pins(None)
            return
        macro = next((m for m in self.current.macros if m.name == selection[0]), None)
        self._show_pins(macro)

    # -- pins ---------------------------------------------------------------

    @staticmethod
    def _pin_iid(pin: lef_mod.LefPin) -> str:
        # Identity-based, not name-based: name is an editable field.
        return str(id(pin))

    def _pin_row_values(self, pin: lef_mod.LefPin) -> tuple:
        ports = ", ".join(f"{p.layer}:{p.rect_count}rect" for p in pin.ports)
        return (pin.name, pin.direction, pin.use, ports)

    def _show_pins(self, macro: lef_mod.LefMacro | None):
        self._commit_form_to_pin()
        self.current_macro = macro
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

    def _on_pin_field_changed(self, *_args):
        if self._suspend_trace:
            return
        self._commit_form_to_pin()
        if self.current_pin is not None:
            iid = self._pin_iid(self.current_pin)
            if self.pins_tree.exists(iid):
                self.pins_tree.item(iid, values=self._pin_row_values(self.current_pin))

    def _new_pin(self):
        if self.current_macro is None:
            return
        self._commit_form_to_pin()
        pin = lef_mod.LefPin(name=f"NEW_PIN_{len(self.current_macro.pins) + 1}", direction="INPUT", use="SIGNAL")
        self.current_macro.pins.append(pin)
        iid = self._pin_iid(pin)
        self._pin_by_iid[iid] = pin
        self.pins_tree.insert("", "end", iid=iid, values=self._pin_row_values(pin))
        self.pins_tree.selection_set(iid)
        self.pins_tree.see(iid)
        self.macros_tree.set(self.current_macro.name, "pins", len(self.current_macro.pins))

    def _delete_pin(self):
        if self.current_macro is None:
            return
        selection = self.pins_tree.selection()
        if not selection:
            return
        pin = self._pin_by_iid.get(selection[0])
        if pin is None:
            return
        self.current_macro.pins.remove(pin)
        self.current_pin = None
        self.pins_tree.delete(selection[0])
        del self._pin_by_iid[selection[0]]
        remaining = self.pins_tree.get_children()
        if remaining:
            self.pins_tree.selection_set(remaining[0])
            self._load_pin_into_form(self._pin_by_iid[remaining[0]])
        else:
            self._load_pin_into_form(None)
        self.macros_tree.set(self.current_macro.name, "pins", len(self.current_macro.pins))

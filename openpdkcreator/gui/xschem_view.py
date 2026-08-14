"""Simulation tab: real, parsed xschem data
(``openpdkcreator/ihp/xschem.py``/``ihp/xschem_sch.py``) -- two major
sub-tabs, each with its own file picker (mirroring
``lef_view.py``/``spice_models_view.py``'s own file-picker shape --
no small, fixed set of "the real ones" here either, in either domain):

**Symbols**: all 202 real, downloaded ``libs.tech/xschem/*/*.sym``
files. **Device** (the real ``K``-block's own
``type``/``template_params``/``raw_fields``, read-only), **Pins**
(the real ``B ... {name=... dir=...}`` pin list -- editable, reusing
``port_editor.PortEditor`` directly), and **Graphical** (a real,
interactive canvas -- see below) sub-tabs.

**Schematics**: all 100 real, downloaded ``libs.tech/xschem/`` ``.sch``
files. **Instances** (every real ``C {...}`` component -- editable:
real ``name=``, and, for a real pin instance, its real net-label;
position/rotation/flip stay read-only *here*, moved via the
Graphical tab instead), **Pins** (a real, read-only summary of just
the schematic's own exposed pin instances), **Wires** (every real
``N x1 y1 x2 y2 {lab=...}`` segment -- editable: real ``lab=``), and
**Graphical** sub-tabs.

**Graphical** (both Symbols and Schematics; Qucs-S Symbols has its own
real equivalent, see ``gui/qucs_view.py``): a real, interactive
``geometry_canvas.GeometryCanvas`` rendering every real drawn
primitive (lines/arcs/text/pins-or-ports, plus, for Schematics,
instances/wires) to real scale. **Select** tool: click to select/drag
to move any real shape, ``Delete``/``BackSpace`` to remove it.
**Line**/**Arc**/**Text** tools place a real new shape by clicking (or
click-dragging, for Line/Arc). Schematics additionally get
**Instance** (pick a real ``.sym`` from the whole downloaded symbol
library, then click a position) and **Wire** (click two points) tools
-- unlike this project's own first-pass Schematics editor, "New
Instance/Wire" is now real and supported, since the canvas gives a
real way to choose *where* one actually goes, the real concern that
originally ruled it out. Every canvas edit mutates the exact same
real, live domain object every other tab/writer already shares (see
``gui/geometry_adapters.py``'s own docstring) -- a drag/draw/delete is
immediately reflected in the matching table (Pins/Instances/Wires) and
in a real write-back export, with no separate "commit" step.

Real write-back for everything above -- geometry included -- via
``ihp/xschem_writer.py``/``ihp/xschem_sch_writer.py`` (``File >
Export Edited xschem Symbols``/``Schematics``, ``main.py
export-xschem-sym``/``export-xschem-sch``), including the real,
narrow class of Schematics entries/files that writer safely refuses
to touch (a real, confirmed quote-scanning ambiguity in 27 real
``sg13g2_tests_xyce``-family files -- see that writer's own
docstring).

Both sub-tabs share the parent ``App``'s own per-file cache
(``App.get_parsed_xschem_symbol``/``get_parsed_xschem_schematic``), the
same "switching files and back never silently discards an in-progress
edit" discipline every other editable domain here already uses.
Each file picker's own combobox is now editable, not a closed real-
file list: typing a real, existing relative path and its own button
reads **Edit File** (opens ``file_view_dialog.view_file_dialog``);
typing one that doesn't exist yet reads **Create File** (writes a
real, minimal, valid starting file via ``ihp/xschem.py``'s own
``create_new_sym_file``/``ihp/xschem_sch.py``'s own
``create_new_sch_file``, then reloads and selects it) -- see
``gui/file_picker_utils.py``'s own docstring.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..ihp import xschem as xschem_mod
from ..ihp import xschem_sch as xschem_sch_mod
from . import geometry_adapters
from .file_picker_utils import handle_action, update_action_button
from .geometry_canvas import GeometryCanvas
from .port_editor import PortEditor

_STEM_TO_DIRECTION = {"ipin": "in", "opin": "out", "iopin": "inout"}


class XschemView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.outer = ttk.Notebook(self)
        self.outer.pack(fill="both", expand=True)

        symbols_frame = ttk.Frame(self.outer)
        self.outer.add(symbols_frame, text="Symbols")
        self._symbols = _SymbolsPane(symbols_frame, app)
        self._symbols.pack(fill="both", expand=True)

        schematics_frame = ttk.Frame(self.outer)
        self.outer.add(schematics_frame, text="Schematics")
        self._schematics = _SchematicsPane(schematics_frame, app)
        self._schematics.pack(fill="both", expand=True)

    def load(self):
        self._symbols.load()
        self._schematics.load()

    def commit_pending_edits(self):
        self._symbols.commit_pending_edits()
        self._schematics.commit_pending_edits()


class _SymbolsPane(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pdk_root = app.pdk_root
        self.sym_files: dict[str, Path] = {}
        self.current: xschem_mod.XschemSymbol | None = None

        self._build()
        self.load()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="xschem .sym file:").pack(side="left")
        self.file_var = tk.StringVar()
        self.file_combo = ttk.Combobox(top, textvariable=self.file_var, width=50)
        self.file_combo.pack(side="left", padx=(4, 12))
        self.file_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())
        self.file_combo.bind("<KeyRelease>", lambda _event: self._update_action_button())

        self.action_button = ttk.Button(top, text="Edit File", command=self._on_action)
        self.action_button.pack(side="left")

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True)

        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        device_frame = ttk.Frame(sub)
        sub.add(device_frame, text="Device")
        self.device_tree = ttk.Treeview(device_frame, columns=("field", "value"), show="headings")
        for col, width in zip(("field", "value"), (200, 640)):
            self.device_tree.heading(col, text=col.title())
            self.device_tree.column(col, width=width, anchor="w")
        self.device_tree.pack(fill="both", expand=True)

        pins_frame = ttk.Frame(sub)
        sub.add(pins_frame, text="Pins")
        self.pins_editor = PortEditor(
            pins_frame, port_factory=lambda name: xschem_mod.XschemPin(name=name, direction="in"),
        )
        self.pins_editor.pack(fill="both", expand=True, padx=4, pady=4)

        graphical_frame = ttk.Frame(sub)
        sub.add(graphical_frame, text="Graphical")
        self.canvas_view = GeometryCanvas(
            graphical_frame,
            on_new_line=self._on_new_line, on_new_arc=self._on_new_arc, on_new_text=self._on_new_text,
            on_scene_changed=self._on_canvas_changed,
        )
        self.canvas_view.pack(fill="both", expand=True, padx=4, pady=4)

    def _on_new_line(self, x1, y1, x2, y2):
        if self.current is not None:
            geometry_adapters.new_xschem_line(self.current, x1, y1, x2, y2)
            self._reload_canvas()

    def _on_new_arc(self, x1, y1, x2, y2):
        if self.current is not None:
            geometry_adapters.new_xschem_arc(self.current, x1, y1, x2, y2)
            self._reload_canvas()

    def _on_new_text(self, x, y, content):
        if self.current is not None:
            geometry_adapters.new_xschem_text(self.current, x, y, content)
            self._reload_canvas()

    def _on_canvas_changed(self):
        """A canvas delete can remove a real pin (the canvas' own
        Select tool can select/delete a pin the same as any other real
        shape) -- refresh the Pins table so it never shows a real pin
        no longer in ``XschemSymbol.pins``. Position-only drags don't
        need this (the Pins table shows no position column)."""
        if self.current is not None:
            self.pins_editor.set_ports(self.current.pins)

    def _reload_canvas(self):
        if self.current is not None:
            self.canvas_view.set_scene(geometry_adapters.xschem_symbol_scene(self.current), auto_fit=False)

    def _update_action_button(self):
        update_action_button(self.action_button, self.pdk_root, self.file_var)

    def _on_action(self):
        handle_action(
            self, self.pdk_root, self.file_var,
            create_fn=xschem_mod.create_new_sym_file, on_created=self.load,
        )

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
        self._update_action_button()

    def commit_pending_edits(self):
        self.pins_editor.commit_pending_edits()

    def _refresh_all(self):
        self.commit_pending_edits()
        for row in self.device_tree.get_children():
            self.device_tree.delete(row)

        path = self.sym_files.get(self.file_var.get())
        if path is None:
            self.summary_var.set("No xschem .sym data loaded -- has ihp/fetch.py been run?")
            self.current = None
            self.pins_editor.set_ports(None)
            self.canvas_view.set_scene(geometry_adapters.Scene())
            return

        self.current = self.app.get_parsed_xschem_symbol(path)
        symbol = self.current

        self.device_tree.insert("", "end", values=("type", symbol.device_type or "(none)"))
        for key, value in symbol.template_params.items():
            self.device_tree.insert("", "end", values=(f"template.{key}", value))
        for key, value in symbol.raw_fields.items():
            self.device_tree.insert("", "end", values=(key, value))
        self.pins_editor.set_ports(symbol.pins)
        self.canvas_view.set_scene(geometry_adapters.xschem_symbol_scene(symbol))

        self.summary_var.set(f"type:{symbol.device_type or '(none)'}  pins:{len(symbol.pins)}")


class _SchematicsPane(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pdk_root = app.pdk_root
        self.sch_files: dict[str, Path] = {}
        self.current: xschem_sch_mod.XschemSchematic | None = None
        self._instance_by_iid: dict[str, xschem_sch_mod.XschemInstance] = {}
        self._wire_by_iid: dict[str, xschem_sch_mod.XschemWire] = {}
        self.current_instance: xschem_sch_mod.XschemInstance | None = None
        self.current_wire: xschem_sch_mod.XschemWire | None = None
        self._suspend_trace = False

        self._build()
        self.load()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="xschem .sch file:").pack(side="left")
        self.file_var = tk.StringVar()
        self.file_combo = ttk.Combobox(top, textvariable=self.file_var, width=50)
        self.file_combo.pack(side="left", padx=(4, 12))
        self.file_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())
        self.file_combo.bind("<KeyRelease>", lambda _event: self._update_action_button())

        self.action_button = ttk.Button(top, text="Edit File", command=self._on_action)
        self.action_button.pack(side="left")

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True)

        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._build_instances_tab(sub)
        self._build_pins_tab(sub)
        self._build_wires_tab(sub)
        self._build_graphical_tab(sub)

    def _build_graphical_tab(self, notebook: ttk.Notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Graphical")
        self.canvas_view = GeometryCanvas(
            frame,
            on_new_line=self._on_new_line, on_new_arc=self._on_new_arc, on_new_text=self._on_new_text,
            on_new_instance=self._on_new_instance, on_new_wire=self._on_new_wire,
            on_scene_changed=self._on_canvas_changed, pick_symbol=self._pick_symbol,
        )
        self.canvas_view.pack(fill="both", expand=True, padx=4, pady=4)

    def _on_new_line(self, x1, y1, x2, y2):
        if self.current is not None:
            geometry_adapters.new_xschem_line(self.current, x1, y1, x2, y2)
            self._reload_canvas()

    def _on_new_arc(self, x1, y1, x2, y2):
        if self.current is not None:
            geometry_adapters.new_xschem_arc(self.current, x1, y1, x2, y2)
            self._reload_canvas()

    def _on_new_text(self, x, y, content):
        if self.current is not None:
            geometry_adapters.new_xschem_text(self.current, x, y, content)
            self._reload_canvas()

    def _on_new_wire(self, x1, y1, x2, y2):
        if self.current is not None:
            geometry_adapters.new_xschem_sch_wire(self.current, x1, y1, x2, y2)
            self._reload_canvas()
            self._refresh_wires_tree()

    def _on_new_instance(self, x, y, symbol_ref):
        if self.current is not None:
            geometry_adapters.new_xschem_sch_instance(self.current, x, y, symbol_ref)
            self._reload_canvas()
            self._refresh_instances_tree()

    def _pick_symbol(self) -> str | None:
        return _pick_symbol_dialog(self, self.pdk_root)

    def _on_canvas_changed(self):
        """A canvas drag/delete mutates the real, shared
        ``XschemSchematic`` object in place -- refresh the Instances/
        Wires tables too, since (unlike Symbols' own Pins list) Wires
        shows real position columns that a drag/delete can change."""
        self._refresh_instances_tree()
        self._refresh_wires_tree()

    def _reload_canvas(self):
        if self.current is not None:
            self.canvas_view.set_scene(geometry_adapters.xschem_schematic_scene(self.current), auto_fit=False)

    def _refresh_instances_tree(self):
        for row in self.instances_tree.get_children():
            self.instances_tree.delete(row)
        self._instance_by_iid = {}
        if self.current is None:
            return
        for inst in self.current.instances:
            iid = self._iid(inst)
            self._instance_by_iid[iid] = inst
            self.instances_tree.insert("", "end", iid=iid, values=self._instance_row_values(inst))

    def _refresh_wires_tree(self):
        for row in self.wires_tree.get_children():
            self.wires_tree.delete(row)
        self._wire_by_iid = {}
        if self.current is None:
            return
        for wire in self.current.wires:
            iid = self._iid(wire)
            self._wire_by_iid[iid] = wire
            self.wires_tree.insert("", "end", iid=iid, values=self._wire_row_values(wire))

    def _build_instances_tab(self, notebook: ttk.Notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Instances")
        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Button(frame, text="Delete Instance", command=self._delete_instance).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )

        columns = ("name", "symbol_ref", "x", "y", "rot", "flip", "resolved")
        self.instances_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        widths = {"name": 100, "symbol_ref": 240, "x": 50, "y": 50, "rot": 40, "flip": 40, "resolved": 70}
        for col in columns:
            self.instances_tree.heading(col, text=col.replace("_", " ").title())
            self.instances_tree.column(col, width=widths[col], anchor="w")
        self.instances_tree.grid(row=1, column=0, sticky="nsew")
        self.instances_tree.bind("<<TreeviewSelect>>", self._on_instance_select)

        right = ttk.Frame(frame)
        right.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(8, 0))
        right.columnconfigure(1, weight=1)

        ttk.Label(right, text="Name:").grid(row=0, column=0, sticky="w", pady=2)
        self.instance_name_var = tk.StringVar()
        self.instance_name_var.trace_add("write", self._on_instance_field_changed)
        ttk.Entry(right, textvariable=self.instance_name_var).grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(right, text="Net label (pin instances only):").grid(row=1, column=0, sticky="w", pady=2)
        self.instance_label_var = tk.StringVar()
        self.instance_label_var.trace_add("write", self._on_instance_field_changed)
        self.instance_label_entry = ttk.Entry(right, textvariable=self.instance_label_var)
        self.instance_label_entry.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(
            right,
            text="Symbol reference/position/rotation/flip stay read-only\n"
            "here -- drag an instance on the Graphical tab to move it.",
            foreground="#666", wraplength=260, justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _build_pins_tab(self, notebook: ttk.Notebook):
        """Read-only convenience view: just the schematic's own real
        pin instances (``ipin``/``opin``/``iopin`` references), with
        their real direction and net label at a glance -- editing
        happens in the Instances tab (select the same row there for
        Name/Net label fields); this tab exists so "what does this
        schematic expose as a port" doesn't require scanning the full,
        unfiltered Instances list by eye."""

        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Pins")
        columns = ("name", "direction", "net")
        self.pins_tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col, width in zip(columns, (100, 80, 160)):
            self.pins_tree.heading(col, text=col.title())
            self.pins_tree.column(col, width=width, anchor="w")
        self.pins_tree.pack(fill="both", expand=True)

    def _build_wires_tab(self, notebook: ttk.Notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Wires")
        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Button(frame, text="Delete Wire", command=self._delete_wire).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )

        columns = ("x1", "y1", "x2", "y2", "label")
        self.wires_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        for col, width in zip(columns, (60, 60, 60, 60, 200)):
            self.wires_tree.heading(col, text=col.title())
            self.wires_tree.column(col, width=width, anchor="w")
        self.wires_tree.grid(row=1, column=0, sticky="nsew")
        self.wires_tree.bind("<<TreeviewSelect>>", self._on_wire_select)

        right = ttk.Frame(frame)
        right.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(8, 0))
        right.columnconfigure(1, weight=1)

        ttk.Label(right, text="Label:").grid(row=0, column=0, sticky="w", pady=2)
        self.wire_label_var = tk.StringVar()
        self.wire_label_var.trace_add("write", self._on_wire_field_changed)
        ttk.Entry(right, textvariable=self.wire_label_var).grid(row=0, column=1, sticky="ew", pady=2)

    def _update_action_button(self):
        update_action_button(self.action_button, self.pdk_root, self.file_var)

    def _on_action(self):
        handle_action(
            self, self.pdk_root, self.file_var,
            create_fn=xschem_sch_mod.create_new_sch_file, on_created=self.load,
        )

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
        self._update_action_button()

    def commit_pending_edits(self):
        self._commit_instance_form()
        self._commit_wire_form()

    @staticmethod
    def _iid(obj) -> str:
        return str(id(obj))

    def _instance_row_values(self, inst: xschem_sch_mod.XschemInstance) -> tuple:
        resolved = "PDK" if inst.resolved_path is not None else "external"
        return (inst.name, inst.symbol_ref, inst.x, inst.y, inst.rot, inst.flip, resolved)

    def _wire_row_values(self, wire: xschem_sch_mod.XschemWire) -> tuple:
        return (wire.x1, wire.y1, wire.x2, wire.y2, wire.label)

    def _refresh_all(self):
        self.commit_pending_edits()
        for tree in (self.instances_tree, self.pins_tree, self.wires_tree):
            for row in tree.get_children():
                tree.delete(row)
        self._instance_by_iid = {}
        self._wire_by_iid = {}

        path = self.sch_files.get(self.file_var.get())
        if path is None:
            self.summary_var.set("No xschem .sch data loaded -- has ihp/fetch.py been run?")
            self.current = None
            self._load_instance_into_form(None)
            self._load_wire_into_form(None)
            self.canvas_view.set_scene(geometry_adapters.Scene())
            return

        self.current = self.app.get_parsed_xschem_schematic(path)
        schematic = self.current

        for inst in schematic.instances:
            iid = self._iid(inst)
            self._instance_by_iid[iid] = inst
            self.instances_tree.insert("", "end", iid=iid, values=self._instance_row_values(inst))
        for wire in schematic.wires:
            iid = self._iid(wire)
            self._wire_by_iid[iid] = wire
            self.wires_tree.insert("", "end", iid=iid, values=self._wire_row_values(wire))
        for inst in schematic.pin_instances:
            stem = Path(inst.symbol_ref).stem
            self.pins_tree.insert("", "end", values=(inst.name, _STEM_TO_DIRECTION.get(stem, "?"), inst.pin_label))

        self._load_instance_into_form(None)
        self._load_wire_into_form(None)
        self.canvas_view.set_scene(geometry_adapters.xschem_schematic_scene(schematic))

        self.summary_var.set(
            f"instances:{len(schematic.instances)}  pins:{len(schematic.pin_instances)}  "
            f"wires:{len(schematic.wires)}  nets:{len(schematic.net_names)}"
        )

    # -- instances (editable: name, pin net-label) ---------------------------

    def _on_instance_select(self, _event=None):
        self._commit_instance_form()
        selection = self.instances_tree.selection()
        inst = self._instance_by_iid.get(selection[0]) if selection else None
        self._load_instance_into_form(inst)

    def _load_instance_into_form(self, inst: xschem_sch_mod.XschemInstance | None):
        self._suspend_trace = True
        self.current_instance = inst
        if inst is None:
            self.instance_name_var.set("")
            self.instance_label_var.set("")
            self.instance_label_entry.configure(state="disabled")
        else:
            self.instance_name_var.set(inst.name)
            self.instance_label_var.set(inst.pin_label)
            self.instance_label_entry.configure(state="normal" if inst.is_pin else "disabled")
        self._suspend_trace = False

    def _commit_instance_form(self):
        inst = self.current_instance
        if inst is None:
            return
        inst.name = self.instance_name_var.get().strip() or inst.name
        if inst.is_pin:
            inst.pin_label = self.instance_label_var.get().strip()

    def _on_instance_field_changed(self, *_args):
        if self._suspend_trace:
            return
        self._commit_instance_form()
        if self.current_instance is not None:
            iid = self._iid(self.current_instance)
            if self.instances_tree.exists(iid):
                self.instances_tree.item(iid, values=self._instance_row_values(self.current_instance))

    def _delete_instance(self):
        if self.current is None:
            return
        selection = self.instances_tree.selection()
        if not selection:
            return
        inst = self._instance_by_iid.get(selection[0])
        if inst is None:
            return
        self.current.instances.remove(inst)
        self.current_instance = None
        self.instances_tree.delete(selection[0])
        del self._instance_by_iid[selection[0]]
        self._load_instance_into_form(None)

    # -- wires (editable: label) ----------------------------------------------

    def _on_wire_select(self, _event=None):
        self._commit_wire_form()
        selection = self.wires_tree.selection()
        wire = self._wire_by_iid.get(selection[0]) if selection else None
        self._load_wire_into_form(wire)

    def _load_wire_into_form(self, wire: xschem_sch_mod.XschemWire | None):
        self._suspend_trace = True
        self.current_wire = wire
        self.wire_label_var.set(wire.label if wire is not None else "")
        self._suspend_trace = False

    def _commit_wire_form(self):
        wire = self.current_wire
        if wire is None:
            return
        wire.label = self.wire_label_var.get().strip()

    def _on_wire_field_changed(self, *_args):
        if self._suspend_trace:
            return
        self._commit_wire_form()
        if self.current_wire is not None:
            iid = self._iid(self.current_wire)
            if self.wires_tree.exists(iid):
                self.wires_tree.item(iid, values=self._wire_row_values(self.current_wire))

    def _delete_wire(self):
        if self.current is None:
            return
        selection = self.wires_tree.selection()
        if not selection:
            return
        wire = self._wire_by_iid.get(selection[0])
        if wire is None:
            return
        self.current.wires.remove(wire)
        self.current_wire = None
        self.wires_tree.delete(selection[0])
        del self._wire_by_iid[selection[0]]
        self._load_wire_into_form(None)


def _pick_symbol_dialog(parent: tk.Widget, pdk_root: Path) -> str | None:
    """A real, minimal modal: pick one real ``.sym`` file (by its own
    real relative path) from the whole downloaded xschem symbol
    library -- used by the Schematics Graphical tab's own Instance
    tool. Returns ``None`` if cancelled."""

    files = sorted(str(p.relative_to(pdk_root)) for p in xschem_mod.find_sym_files(pdk_root))
    dialog = tk.Toplevel(parent)
    dialog.title("Pick a real symbol")
    dialog.geometry("560x420")
    dialog.transient(parent.winfo_toplevel())

    ttk.Label(dialog, text="Real xschem .sym file to instantiate:").pack(anchor="w", padx=8, pady=(8, 4))
    filter_var = tk.StringVar()
    ttk.Entry(dialog, textvariable=filter_var).pack(fill="x", padx=8)

    listbox = tk.Listbox(dialog)
    listbox.pack(fill="both", expand=True, padx=8, pady=8)

    def _populate(*_args):
        listbox.delete(0, "end")
        query = filter_var.get().lower()
        for name in files:
            if query in name.lower():
                listbox.insert("end", name)

    filter_var.trace_add("write", _populate)
    _populate()

    result: list[str | None] = [None]

    def _ok():
        selection = listbox.curselection()
        if selection:
            result[0] = listbox.get(selection[0])
        dialog.destroy()

    def _cancel():
        dialog.destroy()

    listbox.bind("<Double-Button-1>", lambda _e: _ok())
    button_row = ttk.Frame(dialog)
    button_row.pack(fill="x", padx=8, pady=(0, 8))
    ttk.Button(button_row, text="OK", command=_ok).pack(side="right")
    ttk.Button(button_row, text="Cancel", command=_cancel).pack(side="right", padx=(0, 6))

    dialog.grab_set()
    dialog.wait_window()
    return result[0]

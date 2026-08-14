"""Simulation tab: real, parsed Qucs-S data
(``openpdkcreator/ihp/qucs_sym.py``) -- two major sub-tabs, mirroring
``xschem_view.py``'s own Symbols/Schematics split, since this real
directory genuinely holds two different real formats (see
``ihp/qucs_sym.py``'s own docstring):

**Components** (34 real ``.xml`` device definitions): library/
description/models (read-only), real **Parameters** (name/unit/show,
read-only, plus a real default value or equation -- **editable**, via
``ihp/qucs_component_writer.py``'s own surgical text patch, position-
matched to the real file's own ``<Parameter ...>`` tags since a real
Parameter has no other stable identity), and real **Netlists** (the
raw Ngspice/CDL/[Xyce] template strings, read-only).

**Symbols** (22 real ``.sym`` drawn-geometry files): real
``PortSym`` primitives -- **editable** position/type/angle/condition,
via ``ihp/qucs_sym_writer.py``; the real, honestly-partial trailing
``hint`` comment (20 of 66 real lines carry one) stays read-only,
preserved verbatim on an edited line, not itself an editable field --
this format carries no real port *name* at all, unlike xschem's own
``.sym``. New/Delete Port supported (a real, minimal, honest
``0,0``/no-condition starting point for a new port, matching
``ihp/qucs_sym_writer.py``'s own documented default).

Both share the parent ``App``'s own per-file cache
(``App.get_parsed_qucs_symbol``/``get_parsed_qucs_component``), the
same "switching files and back never silently discards an in-progress
edit" discipline every other editable domain here already uses.

Each file picker's own combobox is now editable, not a closed real-
file list: typing a real, existing relative path and its own button
reads **Edit File** (opens ``file_view_dialog.view_file_dialog``);
typing one that doesn't exist yet reads **Create File** (writes a
real, minimal, valid starting file via ``ihp/qucs_sym.py``'s own
``create_new_symbol_geometry_file``/``create_new_component_file``,
then reloads and selects it) -- see ``gui/file_picker_utils.py``'s own
docstring. A newly created Component's own real Description/Models/
Netlists (no structured editor exists for those, only Parameters) can
still be filled in via that same **Edit File** dialog's own raw-text
Edit/Save, once the file exists.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..ihp import qucs_sym as qucs_mod
from .file_picker_utils import handle_action, update_action_button


class QucsView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        outer = ttk.Notebook(self)
        outer.pack(fill="both", expand=True)

        components_frame = ttk.Frame(outer)
        outer.add(components_frame, text="Components")
        self._components = _ComponentsPane(components_frame, app)
        self._components.pack(fill="both", expand=True)

        symbols_frame = ttk.Frame(outer)
        outer.add(symbols_frame, text="Symbols")
        self._symbols = _SymbolsPane(symbols_frame, app)
        self._symbols.pack(fill="both", expand=True)

    def load(self):
        self._components.load()
        self._symbols.load()

    def commit_pending_edits(self):
        self._components.commit_pending_edits()
        self._symbols.commit_pending_edits()


class _ComponentsPane(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pdk_root = app.pdk_root
        self.files: dict[str, Path] = {}
        self.current: qucs_mod.QucsComponent | None = None
        self.current_param: qucs_mod.QucsParameter | None = None
        self._param_by_iid: dict[str, qucs_mod.QucsParameter] = {}
        self._suspend_trace = False

        self._build()
        self.load()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="Qucs-S component .xml file:").pack(side="left")
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

        self.overview_tree = _make_tree(sub, "Overview", ("field", "value"), (160, 680))
        self._build_params_tab(sub)
        self.netlists_tree = _make_tree(sub, "Netlists", ("kind", "template"), (140, 700))

    def _build_params_tab(self, notebook: ttk.Notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Parameters")
        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)

        columns = ("name", "unit", "show", "default_value", "equation", "description")
        self.params_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        for col, width in zip(columns, (100, 60, 60, 120, 200, 220)):
            self.params_tree.heading(col, text=col.replace("_", " ").title())
            self.params_tree.column(col, width=width, anchor="w")
        self.params_tree.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.params_tree.bind("<<TreeviewSelect>>", self._on_param_select)

        right = ttk.Frame(frame)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.columnconfigure(1, weight=1)

        ttk.Label(right, text="Name:").grid(row=0, column=0, sticky="w", pady=2)
        self.param_name_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.param_name_var, state="readonly").grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(right, text="Value kind:").grid(row=1, column=0, sticky="w", pady=2)
        self.param_kind_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.param_kind_var, state="readonly").grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(right, text="Value:").grid(row=2, column=0, sticky="w", pady=2)
        self.param_value_var = tk.StringVar()
        self.param_value_var.trace_add("write", self._on_param_field_changed)
        self.param_value_entry = ttk.Entry(right, textvariable=self.param_value_var)
        self.param_value_entry.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(
            right, text="Name/unit/show/description stay read-only --\nonly a real Parameter's own\n"
            "default_value/equation is editable.",
            foreground="#666", wraplength=260, justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _update_action_button(self):
        update_action_button(self.action_button, self.pdk_root, self.file_var)

    def _on_action(self):
        handle_action(
            self, self.pdk_root, self.file_var,
            create_fn=lambda path: qucs_mod.create_new_component_file(path, path.stem), on_created=self.load,
        )

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
        self._update_action_button()

    def commit_pending_edits(self):
        self._commit_param_form()

    @staticmethod
    def _param_row_values(param: qucs_mod.QucsParameter) -> tuple:
        attrs = param.raw_attrs
        return (
            attrs.get("name", ""), attrs.get("unit", ""), attrs.get("show", ""),
            attrs.get("default_value", ""), attrs.get("equation", ""), param.description,
        )

    def _refresh_all(self):
        self.commit_pending_edits()
        for tree in (self.overview_tree, self.params_tree, self.netlists_tree):
            for row in tree.get_children():
                tree.delete(row)
        self._param_by_iid = {}

        path = self.files.get(self.file_var.get())
        if path is None:
            self.summary_var.set("No Qucs-S component data loaded -- has ihp/fetch.py been run?")
            self.current = None
            self._load_param_into_form(None)
            return

        self.current = self.app.get_parsed_qucs_component(path)
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

        for i, param in enumerate(component.parameters):
            iid = str(i)
            self._param_by_iid[iid] = param
            self.params_tree.insert("", "end", iid=iid, values=self._param_row_values(param))

        for kind, template in component.netlist_templates.items():
            self.netlists_tree.insert("", "end", values=(kind, template))

        self._load_param_into_form(None)
        self.summary_var.set(
            f"{component.description or '(no description)'}  --  {len(component.parameters)} real parameter(s)"
        )

    def _on_param_select(self, _event=None):
        self._commit_param_form()
        selection = self.params_tree.selection()
        param = self._param_by_iid.get(selection[0]) if selection else None
        self._load_param_into_form(param)

    def _load_param_into_form(self, param: qucs_mod.QucsParameter | None):
        self._suspend_trace = True
        self.current_param = param
        if param is None:
            self.param_name_var.set("")
            self.param_kind_var.set("")
            self.param_value_var.set("")
            self.param_value_entry.configure(state="disabled")
        else:
            attrs = param.raw_attrs
            self.param_name_var.set(attrs.get("name", ""))
            if "equation" in attrs:
                self.param_kind_var.set("equation")
                self.param_value_var.set(attrs["equation"])
                self.param_value_entry.configure(state="normal")
            elif "default_value" in attrs:
                self.param_kind_var.set("default_value")
                self.param_value_var.set(attrs["default_value"])
                self.param_value_entry.configure(state="normal")
            else:
                self.param_kind_var.set("(none)")
                self.param_value_var.set("")
                self.param_value_entry.configure(state="disabled")
        self._suspend_trace = False

    def _commit_param_form(self):
        param = self.current_param
        if param is None:
            return
        kind = self.param_kind_var.get()
        if kind in ("equation", "default_value"):
            param.raw_attrs[kind] = self.param_value_var.get()

    def _on_param_field_changed(self, *_args):
        if self._suspend_trace:
            return
        self._commit_param_form()
        if self.current_param is not None:
            for iid, param in self._param_by_iid.items():
                if param is self.current_param:
                    self.params_tree.item(iid, values=self._param_row_values(param))
                    break


class _SymbolsPane(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pdk_root = app.pdk_root
        self.files: dict[str, Path] = {}
        self.current: qucs_mod.QucsSymbolGeometry | None = None
        self.current_port: qucs_mod.QucsPort | None = None
        self._port_by_iid: dict[str, qucs_mod.QucsPort] = {}
        self._suspend_trace = False

        self._build()
        self.load()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="Qucs-S symbol .sym file:").pack(side="left")
        self.file_var = tk.StringVar()
        self.file_combo = ttk.Combobox(top, textvariable=self.file_var, width=50)
        self.file_combo.pack(side="left", padx=(4, 12))
        self.file_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())
        self.file_combo.bind("<KeyRelease>", lambda _event: self._update_action_button())

        self.action_button = ttk.Button(top, text="Edit File", command=self._on_action)
        self.action_button.pack(side="left")

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        button_row = ttk.Frame(body)
        button_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(button_row, text="New Port", command=self._new_port).pack(side="left")
        ttk.Button(button_row, text="Delete Port", command=self._delete_port).pack(side="left", padx=(6, 0))

        columns = ("x", "y", "type", "angle", "condition", "hint")
        self.ports_tree = ttk.Treeview(body, columns=columns, show="headings", selectmode="browse")
        widths = {"x": 60, "y": 60, "type": 60, "angle": 60, "condition": 160, "hint": 100}
        for col in columns:
            self.ports_tree.heading(col, text=col.title())
            self.ports_tree.column(col, width=widths[col], anchor="w")
        self.ports_tree.grid(row=1, column=0, sticky="nsew")
        self.ports_tree.bind("<<TreeviewSelect>>", self._on_port_select)

        right = ttk.Frame(body)
        right.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(8, 0))
        right.columnconfigure(1, weight=1)

        self.port_vars: dict[str, tk.StringVar] = {}
        for row, (field, label) in enumerate((("x", "X"), ("y", "Y"), ("port_type", "Type"), ("angle", "Angle"), ("condition", "Condition"))):
            ttk.Label(right, text=f"{label}:").grid(row=row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_port_field_changed)
            ttk.Entry(right, textvariable=var).grid(row=row, column=1, sticky="ew", pady=2)
            self.port_vars[field] = var

        ttk.Label(right, text="Hint (real, trailing comment):").grid(row=5, column=0, sticky="w", pady=2)
        self.port_hint_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.port_hint_var, state="readonly").grid(row=5, column=1, sticky="ew", pady=2)

    def _update_action_button(self):
        update_action_button(self.action_button, self.pdk_root, self.file_var)

    def _on_action(self):
        handle_action(
            self, self.pdk_root, self.file_var,
            create_fn=qucs_mod.create_new_symbol_geometry_file, on_created=self.load,
        )

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
        self._update_action_button()

    def commit_pending_edits(self):
        self._commit_port_form()

    @staticmethod
    def _port_row_values(port: qucs_mod.QucsPort) -> tuple:
        return (port.x, port.y, port.port_type, port.angle, port.condition, port.hint)

    def _refresh_all(self):
        self.commit_pending_edits()
        for row in self.ports_tree.get_children():
            self.ports_tree.delete(row)
        self._port_by_iid = {}

        path = self.files.get(self.file_var.get())
        if path is None:
            self.summary_var.set("No Qucs-S symbol data loaded -- has ihp/fetch.py been run?")
            self.current = None
            self._load_port_into_form(None)
            return

        self.current = self.app.get_parsed_qucs_symbol(path)
        geometry = self.current

        for i, port in enumerate(geometry.ports):
            iid = str(i)
            self._port_by_iid[iid] = port
            self.ports_tree.insert("", "end", iid=iid, values=self._port_row_values(port))

        self._load_port_into_form(None)
        self.summary_var.set(f"{geometry.primitive_count} real drawing primitive(s), {len(geometry.ports)} real port(s)")

    def _on_port_select(self, _event=None):
        self._commit_port_form()
        selection = self.ports_tree.selection()
        port = self._port_by_iid.get(selection[0]) if selection else None
        self._load_port_into_form(port)

    def _load_port_into_form(self, port: qucs_mod.QucsPort | None):
        self._suspend_trace = True
        self.current_port = port
        if port is None:
            for var in self.port_vars.values():
                var.set("")
            self.port_hint_var.set("")
        else:
            self.port_vars["x"].set(str(port.x))
            self.port_vars["y"].set(str(port.y))
            self.port_vars["port_type"].set(port.port_type)
            self.port_vars["angle"].set(str(port.angle))
            self.port_vars["condition"].set(port.condition)
            self.port_hint_var.set(port.hint)
        self._suspend_trace = False

    def _commit_port_form(self):
        port = self.current_port
        if port is None:
            return
        try:
            port.x = int(self.port_vars["x"].get())
        except ValueError:
            pass
        try:
            port.y = int(self.port_vars["y"].get())
        except ValueError:
            pass
        port.port_type = self.port_vars["port_type"].get()
        try:
            port.angle = int(self.port_vars["angle"].get())
        except ValueError:
            pass
        port.condition = self.port_vars["condition"].get()

    def _on_port_field_changed(self, *_args):
        if self._suspend_trace:
            return
        self._commit_port_form()
        if self.current_port is not None:
            for iid, port in self._port_by_iid.items():
                if port is self.current_port:
                    self.ports_tree.item(iid, values=self._port_row_values(port))
                    break

    def _new_port(self):
        if self.current is None:
            return
        self._commit_port_form()
        port = qucs_mod.QucsPort(x=0, y=0, port_type="1", angle=0)
        self.current.ports.append(port)
        iid = str(len(self._port_by_iid))
        self._port_by_iid[iid] = port
        self.ports_tree.insert("", "end", iid=iid, values=self._port_row_values(port))
        self.ports_tree.selection_set(iid)
        self.ports_tree.see(iid)

    def _delete_port(self):
        if self.current is None:
            return
        selection = self.ports_tree.selection()
        if not selection:
            return
        port = self._port_by_iid.get(selection[0])
        if port is None:
            return
        self.current.ports.remove(port)
        self.current_port = None
        self.ports_tree.delete(selection[0])
        del self._port_by_iid[selection[0]]
        self._load_port_into_form(None)


def _make_tree(notebook: ttk.Notebook, title: str, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
    frame = ttk.Frame(notebook)
    notebook.add(frame, text=title)
    tree = ttk.Treeview(frame, columns=columns, show="headings")
    for col, width in zip(columns, widths):
        tree.heading(col, text=col.replace("_", " ").title())
        tree.column(col, width=width, anchor="w")
    tree.pack(fill="both", expand=True)
    return tree

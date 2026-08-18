"""A reusable netlist/Verilog port-list editor: a port list + New/
Delete Port + a Name/Direction[/Width] form, the same commit-on-switch
pattern every other editable view here uses (``pin_editor.PinEditor``,
``rules_view.RulesView``, ...). Shared across CDL, SPICE, and Verilog
port editing (``gui/cell_hub_view.py``'s own "Edit ... Ports" dialogs)
since all three are structurally the same real thing -- an ordered
list of named ports, each with an optional real direction
(``pdklib/netlist.py``'s ``NetlistPort``/``pdklib/verilog.py``'s
``VerilogPort``) -- via duck typing plus a ``port_factory`` callback
for "New Port" (the two real dataclasses differ: `VerilogPort` also
has a real bus ``width``, `NetlistPort` doesn't, since CDL/SPICE ports
carry no real width concept).

Direction is a free-typable entry, not a closed combobox: SPICE ports
carry no real direction data at all (stays blank, honestly), and even
CDL/Verilog's own real direction vocabularies shouldn't be treated as a
closed set this project invented.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


class PortEditor(ttk.Frame):
    def __init__(self, parent, port_factory: Callable[[str], object], has_width: bool = False, on_change=None):
        super().__init__(parent)
        self.port_factory = port_factory
        self.has_width = has_width
        self.on_change = on_change
        self.ports: list | None = None
        self.current_port = None
        self._suspend_trace = False
        self._port_by_iid: dict[str, object] = {}

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
        ttk.Button(button_row, text="New Port", command=self._new_port).pack(side="left")
        ttk.Button(button_row, text="Delete Port", command=self._delete_port).pack(side="left", padx=(6, 0))

        columns = ("name", "direction", "width") if self.has_width else ("name", "direction")
        self.ports_tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        widths = {"name": 160, "direction": 90, "width": 80}
        for col in columns:
            self.ports_tree.heading(col, text=col.title())
            self.ports_tree.column(col, width=widths[col], anchor="w")
        self.ports_tree.grid(row=1, column=0, sticky="nsew")
        self.ports_tree.bind("<<TreeviewSelect>>", self._on_port_select)

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right.columnconfigure(1, weight=1)

        self.port_vars: dict[str, tk.StringVar] = {}
        form_row = 0

        def add_entry(field, label):
            nonlocal form_row
            ttk.Label(right, text=label).grid(row=form_row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_field_changed)
            ttk.Entry(right, textvariable=var).grid(row=form_row, column=1, sticky="ew", pady=2)
            self.port_vars[field] = var
            form_row += 1

        add_entry("name", "Name")
        add_entry("direction", "Direction")
        if self.has_width:
            add_entry("width", "Width (e.g. [7:0])")

    # -- port switching -------------------------------------------------------

    @staticmethod
    def _port_iid(port) -> str:
        # Identity-based, not name-based: name is an editable field.
        return str(id(port))

    def _port_row_values(self, port) -> tuple:
        if self.has_width:
            return (port.name, port.direction, port.width)
        return (port.name, port.direction)

    def set_ports(self, ports: list | None):
        self._commit_form_to_port()
        self.ports = ports
        for row in self.ports_tree.get_children():
            self.ports_tree.delete(row)
        self._port_by_iid = {}
        if ports is None:
            self._load_port_into_form(None)
            return
        for port in ports:
            iid = self._port_iid(port)
            self._port_by_iid[iid] = port
            self.ports_tree.insert("", "end", iid=iid, values=self._port_row_values(port))
        if ports:
            self.ports_tree.selection_set(self._port_iid(ports[0]))
            self._load_port_into_form(ports[0])
        else:
            self._load_port_into_form(None)

    def _on_port_select(self, _event=None):
        self._commit_form_to_port()
        selection = self.ports_tree.selection()
        port = self._port_by_iid.get(selection[0]) if selection else None
        self._load_port_into_form(port)

    def _load_port_into_form(self, port):
        self._suspend_trace = True
        self.current_port = port
        if port is None:
            for var in self.port_vars.values():
                var.set("")
        else:
            self.port_vars["name"].set(port.name)
            self.port_vars["direction"].set(port.direction)
            if self.has_width:
                self.port_vars["width"].set(port.width)
        self._suspend_trace = False

    def _commit_form_to_port(self):
        port = self.current_port
        if port is None:
            return
        port.name = self.port_vars["name"].get().strip() or port.name
        port.direction = self.port_vars["direction"].get()
        if self.has_width:
            port.width = self.port_vars["width"].get()

    def commit_pending_edits(self):
        self._commit_form_to_port()

    def _on_field_changed(self, *_args):
        if self._suspend_trace:
            return
        self._commit_form_to_port()
        if self.current_port is not None:
            iid = self._port_iid(self.current_port)
            if self.ports_tree.exists(iid):
                self.ports_tree.item(iid, values=self._port_row_values(self.current_port))
        if self.on_change is not None:
            self.on_change()

    def _new_port(self):
        if self.ports is None:
            return
        self._commit_form_to_port()
        port = self.port_factory(f"NEW_PORT_{len(self.ports) + 1}")
        self.ports.append(port)
        iid = self._port_iid(port)
        self._port_by_iid[iid] = port
        self.ports_tree.insert("", "end", iid=iid, values=self._port_row_values(port))
        self.ports_tree.selection_set(iid)
        self.ports_tree.see(iid)
        if self.on_change is not None:
            self.on_change()

    def _delete_port(self):
        if self.ports is None:
            return
        selection = self.ports_tree.selection()
        if not selection:
            return
        port = self._port_by_iid.get(selection[0])
        if port is None:
            return
        self.ports.remove(port)
        self.current_port = None
        self.ports_tree.delete(selection[0])
        del self._port_by_iid[selection[0]]
        remaining = self.ports_tree.get_children()
        if remaining:
            self.ports_tree.selection_set(remaining[0])
            self._load_port_into_form(self._port_by_iid[remaining[0]])
        else:
            self._load_port_into_form(None)
        if self.on_change is not None:
            self.on_change()

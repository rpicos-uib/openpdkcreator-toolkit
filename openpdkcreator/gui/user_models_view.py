"""Simulation tab: user-authored Verilog/Verilog-A models
(``openpdkcreator/ihp/user_models.py``) -- browse every real module
found under ``user_models/verilog/*.v``/``user_models/veriloga/*.va``
and see (or set) which real cell each one is linked to.

A module named the same as a real cell is linked automatically (shown
as ``(auto: NAME)``, not editable here -- rename the module or add an
explicit link below to override); an explicit link is set by selecting
a module's own row and typing a cell name into **Cell name**, then
**Save Link** -- persisted immediately to ``user_models/links.yaml``
(``ihp/user_models.py``'s own ``save_links``), and ``App.reload_user_models``
is called afterward so **By Cell** picks up the change without a
restart. **Clear Link** removes an explicit link, falling back to
whatever the automatic name-match would be (or none, if the module's
own name matches no real cell either).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import export as export_mod
from ..ihp import user_models as user_models_mod


class UserModelsView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_module_key: tuple[str, str] | None = None
        """(file_relpath, module_name) of the currently selected row."""

        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ttk.Label(
            top, text="Real modules under user_models/verilog/ and user_models/veriloga/:",
        ).pack(side="left")
        ttk.Button(top, text="Rescan", command=self.refresh).pack(side="left", padx=(8, 0))

        columns = ("file", "kind", "module", "ports", "linked_cell")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        widths = {"file": 220, "kind": 70, "module": 160, "ports": 320, "linked_cell": 160}
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=8)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        form = ttk.Frame(self)
        form.grid(row=2, column=0, sticky="ew", padx=8, pady=8)
        ttk.Label(form, text="Cell name:").pack(side="left")
        self.cell_name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.cell_name_var, width=30).pack(side="left", padx=(4, 8))
        ttk.Button(form, text="Save Link", command=self._save_link).pack(side="left")
        ttk.Button(form, text="Clear Link", command=self._clear_link).pack(side="left", padx=(4, 0))

        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, foreground="#666").grid(
            row=3, column=0, sticky="w", padx=8, pady=(0, 8)
        )

    def refresh(self):
        self.app.reload_user_models()
        for row in self.tree.get_children():
            self.tree.delete(row)

        link_by_key = {
            (link.file_relpath, link.module_name): link.cell_name for link in self.app.user_model_links
        }
        project_root = self._project_root()
        for model_file in self.app.user_models:
            relpath = user_models_mod.relpath_for(project_root, model_file.path)
            for module in model_file.modules:
                explicit = link_by_key.get((relpath, module.name))
                linked_text = explicit if explicit else f"(auto: {module.name})"
                ports_text = ", ".join(f"{p.name}:{p.direction or '?'}" for p in module.ports)
                iid = f"{relpath}::{module.name}"
                self.tree.insert(
                    "", "end", iid=iid,
                    values=(relpath, model_file.kind, module.name, ports_text, linked_text),
                )

        count = sum(len(mf.modules) for mf in self.app.user_models)
        self.status_var.set(f"{len(self.app.user_models)} real file(s), {count} real module(s).")

    def _project_root(self):
        return export_mod.PROJECT_ROOT

    def _on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            self.current_module_key = None
            self.cell_name_var.set("")
            return
        relpath, module_name = selection[0].split("::", 1)
        self.current_module_key = (relpath, module_name)
        link_by_key = {
            (link.file_relpath, link.module_name): link.cell_name for link in self.app.user_model_links
        }
        self.cell_name_var.set(link_by_key.get((relpath, module_name), ""))

    def _save_link(self):
        if self.current_module_key is None:
            return
        relpath, module_name = self.current_module_key
        cell_name = self.cell_name_var.get().strip()
        if not cell_name:
            self.status_var.set("Type a cell name before Save Link (or use Clear Link to remove one).")
            return
        links = [
            link for link in self.app.user_model_links
            if (link.file_relpath, link.module_name) != (relpath, module_name)
        ]
        links.append(user_models_mod.UserModelLink(module_name=module_name, file_relpath=relpath, cell_name=cell_name))
        path = user_models_mod.save_links(self._project_root(), links)
        self.status_var.set(f"Saved link: {module_name} -> {cell_name} ({path}).")
        self.refresh()

    def _clear_link(self):
        if self.current_module_key is None:
            return
        relpath, module_name = self.current_module_key
        links = [
            link for link in self.app.user_model_links
            if (link.file_relpath, link.module_name) != (relpath, module_name)
        ]
        path = user_models_mod.save_links(self._project_root(), links)
        self.status_var.set(f"Cleared explicit link for {module_name} ({path}).")
        self.refresh()

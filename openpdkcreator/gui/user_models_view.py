"""Simulation tab: user-authored Verilog/Verilog-A models
(``openpdkcreator/pdklib/user_models.py``) -- browse every real module
found under ``user_models/verilog/*.v``/``user_models/veriloga/*.va``
and see (or set) which real cell each one is linked to.

A module named the same as a real cell is linked automatically (shown
as ``(auto: NAME)``, not editable here -- rename the module or add an
explicit link below to override); an explicit link is set by selecting
one or more rows and typing a cell name into **Cell name**, then
**Save Link** -- persisted immediately to ``user_models/links.yaml``
(``pdklib/user_models.py``'s own ``save_links``), and ``App.reload_user_models``
is called afterward so **By Cell** picks up the change without a
restart. Multi-selecting rows (``Ctrl``/``Shift``-click, real Tk
``extended`` select mode) applies the same typed cell name to every
selected module in one save -- useful when consolidating several
model variants onto one real cell. **Clear Link** removes an explicit
link for every selected row, falling back to whatever the automatic
name-match would be. **Link All Auto-Matches** is a separate, whole-
tree batch operation: it freezes *every* row's current implicit
name-match into an explicit, persisted link in one save -- handy
before renaming source files or cells, so an accidental rename can't
silently break a link that used to "just work."

**Edit Ports** opens the same real port editor CDL/SPICE/Verilog
already use (``port_dialog.edit_ports_dialog``), then writes the
edited port list straight back to the real, local ``.v``/``.va``
source file via ``pdklib/verilog_writer.py`` -- unlike the real,
downloaded PDK's own CDL/SPICE/Verilog views, a user model's own
source file *is* the user's live, git-tracked edit surface, so there's
no separate export/write-back step: closing the dialog commits.

**Generate ngspice OSDI Snippet** (Verilog-A modules only) renders
IHP's own real, documented OpenVAF-compile-then-``osdi``-load
recipe (``pdklib/user_models.py``'s own ``osdi_snippet``), pointed at the
selected module -- a real, copy-pasteable two-step wiring recipe, not
executed or written to disk by this tool.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .. import export as export_mod
from ..pdklib import user_models as user_models_mod
from ..pdklib import verilog as verilog_mod
from ..pdklib import verilog_writer as verilog_writer_mod
from .port_dialog import edit_ports_dialog
from .text_dialog import show_text_dialog


class UserModelsView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.row_by_iid: dict[str, tuple[user_models_mod.UserModelFile, verilog_mod.VerilogModule]] = {}

        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ttk.Label(
            top, text="Real modules under user_models/verilog/ and user_models/veriloga/:",
        ).pack(side="left")
        ttk.Button(top, text="Rescan", command=self.refresh).pack(side="left", padx=(8, 0))
        ttk.Button(top, text="Link All Auto-Matches", command=self._link_all_auto).pack(side="left", padx=(8, 0))

        columns = ("file", "kind", "module", "ports", "linked_cell")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="extended")
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
        self.edit_ports_button = ttk.Button(form, text="Edit Ports", command=self._edit_ports, state="disabled")
        self.edit_ports_button.pack(side="left", padx=(12, 0))
        self.osdi_button = ttk.Button(
            form, text="Generate ngspice OSDI Snippet", command=self._generate_osdi, state="disabled",
        )
        self.osdi_button.pack(side="left", padx=(4, 0))

        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, foreground="#666").grid(
            row=3, column=0, sticky="w", padx=8, pady=(0, 8)
        )

    def refresh(self):
        self.app.reload_user_models()
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.row_by_iid.clear()

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
                self.row_by_iid[iid] = (model_file, module)
                self.tree.insert(
                    "", "end", iid=iid,
                    values=(relpath, model_file.kind, module.name, ports_text, linked_text),
                )

        count = sum(len(mf.modules) for mf in self.app.user_models)
        self.status_var.set(f"{len(self.app.user_models)} real file(s), {count} real module(s).")
        self._on_select()

    def _project_root(self):
        return export_mod.PROJECT_ROOT

    def _selected_keys(self) -> list[tuple[str, str]]:
        keys = []
        for iid in self.tree.selection():
            relpath, module_name = iid.split("::", 1)
            keys.append((relpath, module_name))
        return keys

    def _on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            self.cell_name_var.set("")
            self.edit_ports_button.configure(state="disabled")
            self.osdi_button.configure(state="disabled")
            return

        if len(selection) == 1:
            relpath, module_name = selection[0].split("::", 1)
            link_by_key = {
                (link.file_relpath, link.module_name): link.cell_name for link in self.app.user_model_links
            }
            self.cell_name_var.set(link_by_key.get((relpath, module_name), ""))
            self.edit_ports_button.configure(state="normal")
            model_file, _module = self.row_by_iid[selection[0]]
            self.osdi_button.configure(state="normal" if model_file.kind == "veriloga" else "disabled")
        else:
            # Batch mode: don't show one row's own link text as if it
            # applied to all of them; ports/OSDI generation are both
            # inherently single-module actions.
            self.cell_name_var.set("")
            self.edit_ports_button.configure(state="disabled")
            self.osdi_button.configure(state="disabled")

    def _save_link(self):
        keys = self._selected_keys()
        if not keys:
            return
        cell_name = self.cell_name_var.get().strip()
        if not cell_name:
            self.status_var.set("Type a cell name before Save Link (or use Clear Link to remove one).")
            return
        links = [link for link in self.app.user_model_links if (link.file_relpath, link.module_name) not in keys]
        for relpath, module_name in keys:
            links.append(user_models_mod.UserModelLink(module_name=module_name, file_relpath=relpath, cell_name=cell_name))
        path = user_models_mod.save_links(self._project_root(), links)
        plural = "" if len(keys) == 1 else f"s ({len(keys)} modules)"
        self.status_var.set(f"Saved link{plural}: -> {cell_name} ({path}).")
        self.refresh()

    def _clear_link(self):
        keys = self._selected_keys()
        if not keys:
            return
        links = [link for link in self.app.user_model_links if (link.file_relpath, link.module_name) not in keys]
        path = user_models_mod.save_links(self._project_root(), links)
        plural = "" if len(keys) == 1 else f"s ({len(keys)} modules)"
        self.status_var.set(f"Cleared explicit link{plural} ({path}).")
        self.refresh()

    def _link_all_auto(self):
        link_by_key = {
            (link.file_relpath, link.module_name): link.cell_name for link in self.app.user_model_links
        }
        project_root = self._project_root()
        links = list(self.app.user_model_links)
        added = 0
        for model_file in self.app.user_models:
            relpath = user_models_mod.relpath_for(project_root, model_file.path)
            for module in model_file.modules:
                key = (relpath, module.name)
                if key in link_by_key:
                    continue  # already has its own explicit link -- leave it alone.
                links.append(user_models_mod.UserModelLink(module_name=module.name, file_relpath=relpath, cell_name=module.name))
                added += 1
        if added == 0:
            self.status_var.set("Every module already has an explicit link -- nothing to freeze.")
            return
        path = user_models_mod.save_links(project_root, links)
        self.status_var.set(f"Froze {added} auto-match(es) into explicit links ({path}).")
        self.refresh()

    def _edit_ports(self):
        selection = self.tree.selection()
        if len(selection) != 1:
            return
        model_file, module = self.row_by_iid[selection[0]]
        edit_ports_dialog(
            self, f"Verilog Ports -- {module.name} ({model_file.path.name})", module.ports,
            lambda name: verilog_mod.VerilogPort(name=name), has_width=True,
        )
        verilog_writer_mod.export_verilog_file(model_file.modules, model_file.path, model_file.path)
        self.status_var.set(f"Saved port edits to {model_file.path}.")
        self.refresh()

    def _generate_osdi(self):
        selection = self.tree.selection()
        if len(selection) != 1:
            return
        model_file, module = self.row_by_iid[selection[0]]
        if model_file.kind != "veriloga":
            return
        try:
            snippet = user_models_mod.osdi_snippet(self._project_root(), model_file, module)
        except ValueError as exc:
            messagebox.showerror("Cannot generate OSDI snippet", str(exc), parent=self)
            return
        show_text_dialog(self, f"ngspice OSDI snippet -- {module.name}", snippet)

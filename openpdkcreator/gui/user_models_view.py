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

**Edit Source** (or double-clicking a row) opens the selected module's
own real file in a real, in-GUI View -> Edit -> Save editor
(``file_view_dialog.view_file_dialog``, the same one every other real
source-viewing dialog in this project already uses -- not a second,
parallel editor) for the whole real behavioral body, not just the port
list **Edit Ports** covers. Saving triggers a real, immediate
**Rescan** (``on_save=self.refresh``), so the **Compile** column below
reflects the just-saved real edit without a second, separate click.

**Real, automatic compile-check on every refresh** (``pdklib/
user_models.py``'s own ``run_compile_check``) -- the closest real
equivalent this project has to Cadence's own "compile on save"
Verilog/Verilog-A editors, now genuinely close: **Edit Source** ->
**Save** -> **Rescan** (automatic) covers the same real edit-then-
compile loop, just one real step more explicit than a live keystroke-
level check would be. Every real module's own file is actually run
through ``openvaf``/``iverilog`` (not just linted or guessed), and the
**Compile** column shows the real, current verdict; **Compile Log**
shows that real run's full stdout/stderr for the one selected row,
instantly (cached from the last real ``refresh()``, never re-run just
to view it).
"""

from __future__ import annotations

import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

from .. import eda_tools
from .. import export as export_mod
from ..pdklib import user_models as user_models_mod
from ..pdklib import verilog as verilog_mod
from ..pdklib import verilog_writer as verilog_writer_mod
from .file_view_dialog import view_file_dialog
from .port_dialog import edit_ports_dialog
from .text_dialog import show_text_dialog


def _find_tool(tool_id: str) -> eda_tools.Tool | None:
    return next((t for t in eda_tools.TOOL_REGISTRY if t.id == tool_id), None)


class UserModelsView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.row_by_iid: dict[str, tuple[user_models_mod.UserModelFile, verilog_mod.VerilogModule]] = {}
        self.compile_results: dict[str, user_models_mod.CompileCheckResult | None] = {}
        """Real ``run_compile_check`` result per row iid, refreshed
        every real ``refresh()`` -- ``None`` means the matching real
        compiler (``openvaf``/``iverilog``) isn't on ``PATH``, told
        apart from a real pass/fail so **Compile Log** can say which
        one honestly, not guess."""

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

        columns = ("file", "kind", "module", "ports", "linked_cell", "compile")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="extended")
        widths = {"file": 220, "kind": 70, "module": 160, "ports": 280, "linked_cell": 140, "compile": 160}
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=8)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda _e: self._edit_source())
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
        self.edit_source_button = ttk.Button(
            form, text="Edit Source", command=self._edit_source, state="disabled",
        )
        self.edit_source_button.pack(side="left", padx=(4, 0))
        self.osdi_button = ttk.Button(
            form, text="Generate ngspice OSDI Snippet", command=self._generate_osdi, state="disabled",
        )
        self.osdi_button.pack(side="left", padx=(4, 0))
        self.compile_log_button = ttk.Button(
            form, text="Compile Log", command=self._show_compile_log, state="disabled",
        )
        self.compile_log_button.pack(side="left", padx=(4, 0))

        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, foreground="#666").grid(
            row=3, column=0, sticky="w", padx=8, pady=(0, 8)
        )

    def refresh(self):
        self.app.reload_user_models()
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.row_by_iid.clear()
        self.compile_results.clear()

        openvaf_tool = _find_tool("openvaf")
        iverilog_tool = _find_tool("iverilog")
        openvaf_status = eda_tools.check_tool(openvaf_tool) if openvaf_tool is not None else None
        iverilog_status = eda_tools.check_tool(iverilog_tool) if iverilog_tool is not None else None

        link_by_key = {
            (link.file_relpath, link.module_name): link.cell_name for link in self.app.user_model_links
        }
        project_root = self._project_root()
        for model_file in self.app.user_models:
            relpath = user_models_mod.relpath_for(project_root, model_file.path)
            tool_status = openvaf_status if model_file.kind == "veriloga" else iverilog_status
            if tool_status is not None and tool_status.found:
                try:
                    result = user_models_mod.run_compile_check(model_file, tool_status.path)
                except subprocess.TimeoutExpired:
                    result = user_models_mod.CompileCheckResult(ok=False, log="Compiler did not finish within 30s.")
                compile_text = "compiles clean" if result.ok else "compile error -- see Compile Log"
            else:
                result = None
                tool_name = "openvaf" if model_file.kind == "veriloga" else "iverilog"
                compile_text = f"({tool_name} not on PATH)"
            for module in model_file.modules:
                explicit = link_by_key.get((relpath, module.name))
                linked_text = explicit if explicit else f"(auto: {module.name})"
                ports_text = ", ".join(f"{p.name}:{p.direction or '?'}" for p in module.ports)
                iid = f"{relpath}::{module.name}"
                self.row_by_iid[iid] = (model_file, module)
                self.compile_results[iid] = result
                self.tree.insert(
                    "", "end", iid=iid,
                    values=(relpath, model_file.kind, module.name, ports_text, linked_text, compile_text),
                )

        count = sum(len(mf.modules) for mf in self.app.user_models)
        error_count = sum(1 for r in self.compile_results.values() if r is not None and not r.ok)
        suffix = f" -- {error_count} real compile error(s)" if error_count else ""
        self.status_var.set(f"{len(self.app.user_models)} real file(s), {count} real module(s){suffix}.")
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
            self.edit_source_button.configure(state="disabled")
            self.osdi_button.configure(state="disabled")
            self.compile_log_button.configure(state="disabled")
            return

        if len(selection) == 1:
            relpath, module_name = selection[0].split("::", 1)
            link_by_key = {
                (link.file_relpath, link.module_name): link.cell_name for link in self.app.user_model_links
            }
            self.cell_name_var.set(link_by_key.get((relpath, module_name), ""))
            self.edit_ports_button.configure(state="normal")
            self.edit_source_button.configure(state="normal")
            model_file, _module = self.row_by_iid[selection[0]]
            self.osdi_button.configure(state="normal" if model_file.kind == "veriloga" else "disabled")
            self.compile_log_button.configure(
                state="normal" if self.compile_results.get(selection[0]) is not None else "disabled"
            )
        else:
            # Batch mode: don't show one row's own link text as if it
            # applied to all of them; ports/OSDI generation, source
            # editing, and compile log are all inherently single-module
            # actions.
            self.cell_name_var.set("")
            self.edit_ports_button.configure(state="disabled")
            self.edit_source_button.configure(state="disabled")
            self.osdi_button.configure(state="disabled")
            self.compile_log_button.configure(state="disabled")

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

    def _edit_source(self):
        """Real, free-form editing of a user model's own real
        behavioral body -- reuses ``file_view_dialog.view_file_dialog``
        (the same real View -> Edit -> Save mechanism every other real
        source-viewing dialog in this project already uses) rather than
        a second, parallel editor; only ``edit_note`` differs from that
        module's own default, since this is the user's own real,
        git-tracked project content, not this project's own downloaded,
        gitignored PDK data. ``on_save=self.refresh`` is the real,
        immediate follow-up -- the same real **Rescan** action, re-
        running every real module's own compile-check (``pdklib/
        user_models.py``'s own ``run_compile_check``) so the **Compile**
        column reflects a just-saved real edit without a second,
        separate click."""

        selection = self.tree.selection()
        if len(selection) != 1:
            return
        model_file, module = self.row_by_iid[selection[0]]
        view_file_dialog(self, model_file.path, edit_note=user_models_mod.EDIT_NOTE, on_save=self.refresh)

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

    def _show_compile_log(self):
        """Shows the real, already-computed ``run_compile_check``
        result for the one selected row (refreshed every real
        ``refresh()`` -- not re-run here, so this is always instant,
        no matter how slow the real compiler itself is)."""

        selection = self.tree.selection()
        if len(selection) != 1:
            return
        result = self.compile_results.get(selection[0])
        if result is None:
            return
        model_file, module = self.row_by_iid[selection[0]]
        tool_name = "openvaf" if model_file.kind == "veriloga" else "iverilog"
        verdict = "compiles clean" if result.ok else "COMPILE ERROR"
        body = result.log if result.log else "(no output -- a real, clean, silent pass.)"
        show_text_dialog(self, f"Compile Log ({tool_name}) -- {module.name} [{verdict}]", body)

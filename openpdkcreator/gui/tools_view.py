"""Tools sub-tab (under Settings): real, live status of the FOSS EDA
toolchain this project's various real PDK views are authored/verified
with (``openpdkcreator/eda_tools.py``) -- found/missing, real detected
version and path, and a **Launch** button for whatever's already on
PATH. A thin GUI wrapper around functionality ``eda_tools.py``'s own
CLI already had (``eda_tools.py list/check/install/launch``) -- no new
detection/install/launch logic here, so the two stay in lock-step; this
view only calls ``eda_tools.check_all``/``eda_tools.resolve_launch``
directly.

Install guidance is shown as read-only text (docs URL + the real,
exact package-manager/user-local command) -- never auto-run from here.
Matches ``eda_tools.py``'s own "opt-in, never silently privileged"
install philosophy: even its own CLI only ever *runs* an install
command for the safe, non-privileged ``user_local`` case, and only
behind an explicit ``--run`` flag; everything else is shown for the
user to run themselves.

**Launch Selected** used to call ``subprocess.Popen(argv, cwd=cwd)``
directly, with no ``app``/``pdk_root`` reference at all -- a real,
found-not-assumed gap: xschem/Qucs-S/Magic's own real per-project
launch-time fixes (see ``pdklib/tool_env.py``'s own docstring) all
live in ``library_manager_view.py``'s own ``_open_*`` methods, keyed
off a specific cell's own view entry, so this second, separate,
no-file "just start the tool" launch path bypassed every one of them
-- Open in xschem/Qucs-S from here would still have shown IHP's own
container-wide workspace even after those fixes. Now threads
``app.pdk_root`` through (same ``app``-taking constructor convention
``settings_view.py`` already uses) and calls the exact same real
``pdklib/tool_env.py`` functions, not a second, re-derived copy."""

from __future__ import annotations

import os
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

from .. import eda_tools
from ..pdklib import tool_env as tool_env_mod


class ToolsView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.statuses: dict[str, eda_tools.ToolStatus] = {}

        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Button(top, text="Recheck", command=self.refresh).pack(side="left")
        ttk.Button(top, text="Launch Selected", command=self._launch_selected).pack(side="left", padx=(6, 0))
        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True, padx=(12, 0))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        columns = ("id", "category", "required", "status", "version", "path")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        widths = {"id": 90, "category": 100, "required": 70, "status": 70, "version": 150, "path": 220}
        for col in columns:
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        scroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        self.detail_var = tk.StringVar(value="Select a tool.")
        ttk.Label(right, textvariable=self.detail_var, font=("TkDefaultFont", 10, "bold"), wraplength=260).grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        self.install_text = tk.Text(right, height=18, width=34, wrap="word", state="disabled")
        self.install_text.grid(row=1, column=0, sticky="nsew")

    # -- data ---------------------------------------------------------------

    def refresh(self):
        selected_id = self._selected_tool_id()
        for row in self.tree.get_children():
            self.tree.delete(row)

        statuses = eda_tools.check_all()
        self.statuses = {status.tool.id: status for status in statuses}
        found = 0
        missing_required = []
        for status in statuses:
            tool = status.tool
            if status.found:
                found += 1
            elif tool.required:
                missing_required.append(tool.id)
            self.tree.insert(
                "", "end", iid=tool.id,
                values=(
                    tool.id, tool.category, "yes" if tool.required else "no",
                    "found" if status.found else "MISSING", status.version or "", status.path or "",
                ),
            )

        summary = f"{found}/{len(statuses)} tool(s) found"
        if missing_required:
            summary += f" -- {len(missing_required)} required missing: {', '.join(missing_required)}"
        self.summary_var.set(summary)

        if selected_id and self.tree.exists(selected_id):
            self.tree.selection_set(selected_id)
        self._show_detail(selected_id if selected_id and self.tree.exists(selected_id) else None)

    def _selected_tool_id(self) -> str | None:
        selection = self.tree.selection()
        return selection[0] if selection else None

    def _on_select(self, _event=None):
        self._show_detail(self._selected_tool_id())

    def _show_detail(self, tool_id: str | None):
        self.install_text.configure(state="normal")
        self.install_text.delete("1.0", "end")
        if tool_id is None:
            self.detail_var.set("Select a tool.")
            self.install_text.configure(state="disabled")
            return

        status = self.statuses[tool_id]
        tool = status.tool
        self.detail_var.set(f"{tool.name} ({tool.category}) -- {'required' if tool.required else 'optional'}")

        lines = [tool.purpose, "", f"Real PDK view: {tool.view}", ""]
        if status.found:
            lines.append(f"Found: {status.path}")
            lines.append(f"Version: {status.version or 'unknown'}")
        else:
            lines.append("Not found on PATH.")
        lines.append("")

        guidance = tool.install
        package_manager = eda_tools.detect_package_manager()
        packaged = guidance.package_manager.get(package_manager)
        if packaged:
            lines.append(f"Install ({package_manager}, run yourself -- needs privileges):")
            lines.append(f"  {packaged}")
        if guidance.user_local:
            lines.append("Install (user-local, non-privileged):")
            lines.append(f"  {guidance.user_local}")
        if guidance.notes:
            lines.append("")
            lines.append(guidance.notes)
        if guidance.docs_url:
            lines.append("")
            lines.append(f"Docs: {guidance.docs_url}")

        self.install_text.insert("1.0", "\n".join(lines))
        self.install_text.configure(state="disabled")

    def _launch_selected(self):
        tool_id = self._selected_tool_id()
        if tool_id is None:
            return
        status = self.statuses.get(tool_id)
        if status is None or not status.found:
            messagebox.showinfo(
                "Not installed", f"{tool_id} isn't on PATH -- see the install guidance on the right.",
            )
            return

        extra_argv: tuple[str, ...] = ()
        extra_env: dict[str, str] | None = None
        if tool_id == "xschem":
            rcfile = tool_env_mod.xschem_rcfile(self.app.pdk_root)
            if rcfile is not None:
                extra_argv = ("--rcfile", rcfile)
        elif tool_id == "qucs-s":
            extra_env = tool_env_mod.qucs_env(self.app.pdk_root)
        elif tool_id == "magic":
            script = tool_env_mod.magic_tech_load_script(self.app.pdk_root)
            if script is not None:
                extra_argv = (script,)

        argv, cwd = eda_tools.resolve_launch(status.tool, status.path, extra_argv=extra_argv)
        env = {**os.environ, **extra_env} if extra_env else None
        subprocess.Popen(argv, cwd=cwd, env=env)

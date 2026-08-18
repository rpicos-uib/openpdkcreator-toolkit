"""Settings tab: project-level, non-PDK-content settings -- a home for
things that describe *this authoring project* rather than any one
tool's real data (which is why it's a flat, top-level tab, not nested
under Technology/Cells). Two clearly separate, deliberately different
things live here so far, and must stay visually and conceptually
distinct (easy to blur otherwise, since this tool is currently pointed
at exactly one real PDK):

- **This Project** -- the user's own, editable identity for what
  they're building: **Project name** (free text, saved via
  ``project_io.py`` alongside DRC Rules/Magic Types/LEF pins -- so it
  survives a relaunch the same way) and **Project directory** (where
  this tool and its saved state -- ``saves/`` -- actually live on
  disk, read-only). Defaults to a deliberately generic placeholder,
  *not* the real PDK's own name, so the two never look identical
  before the user renames anything.
- **Source PDK** (real, read-only, sourced from the actual downloaded
  data) -- **Original PDK name** (``pdk_root.name`` -- IHP's own real
  directory name, e.g. ``ihp-sg13g2``) and **Original PDK location**
  (the real, absolute local path it was fetched into, plus the real
  upstream URL it came from -- ``pdklib/fetch.py``'s own ``REPO_URL``).
  This is what the project was *built from*; per the "final objective"
  (see README's opening paragraph), a future project here could point
  at an entirely different real PDK, so this pairing is kept separate
  from -- and will eventually outlive -- any one specific source.

More project-level settings (a target PDK family name, export/output
paths, ...) belong here as they're added -- this tab is deliberately
a flat list of labeled sections, not yet organized further, since
there's not enough here yet to need it.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..pdklib import fetch as fetch_mod

DEFAULT_PROJECT_NAME = "Untitled PDK Project"


class SettingsView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._suspend_trace = False

        self._build()
        self.refresh()

    def _build(self):
        self.columnconfigure(1, weight=1)
        row = 0

        def section(title: str):
            nonlocal row
            ttk.Label(self, text=title, font=("TkDefaultFont", 10, "bold")).grid(
                row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(14 if row else 8, 4)
            )
            row += 1

        def field(label: str, readonly: bool) -> tk.StringVar:
            nonlocal row
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=(8, 8), pady=2)
            var = tk.StringVar()
            entry = ttk.Entry(self, textvariable=var, state="readonly" if readonly else "normal")
            entry.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=2)
            row += 1
            return var

        section("This Project")
        self.project_name_var = field("Project name:", readonly=False)
        self.project_name_var.trace_add("write", self._on_project_name_changed)
        self.project_dir_var = field("Project directory:", readonly=True)
        ttk.Label(
            self, text="Where this tool and its saved edits (saves/) live -- not the PDK data itself.",
            foreground="#666",
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 4))
        row += 1

        section("Source PDK (real, downloaded data -- read-only)")
        self.pdk_name_var = field("Original PDK name:", readonly=True)
        self.pdk_location_var = field("Original PDK location:", readonly=True)
        self.pdk_upstream_var = field("Fetched from:", readonly=True)
        ttk.Label(
            self, text="What this project was originally built from -- see pdklib/fetch.py.\n"
            "The current model, not a permanent target: see this project's own README.",
            foreground="#666", justify="left",
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 4))
        row += 1

    def refresh(self):
        self._suspend_trace = True
        self.project_name_var.set(self.app.project_name)
        self._suspend_trace = False

        project_dir = Path(__file__).resolve().parents[2]
        self.project_dir_var.set(str(project_dir))
        self.pdk_name_var.set(self.app.pdk_root.name)
        self.pdk_location_var.set(str(self.app.pdk_root))
        self.pdk_upstream_var.set(fetch_mod.REPO_URL)

    def _on_project_name_changed(self, *_args):
        if self._suspend_trace:
            return
        self.app.set_project_name(self.project_name_var.get())

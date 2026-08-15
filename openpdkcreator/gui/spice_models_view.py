"""Simulation tab: real, parsed ngspice ``.lib`` model cards
(``openpdkcreator/ihp/spice_models.py``) -- a file picker over all 32
real, downloaded ``libs.tech/ngspice/models/*.lib`` files, since
there's no small, fixed set of "the real ones" to enumerate (mirroring
``lef_view.py``'s own file-picker shape for the same reason).

Three sub-tabs per file: **Models** (every real ``.model NAME TYPE
...`` statement, its own real parameter list shown as one raw
``key=value`` text column rather than a parameter-by-parameter
breakdown -- some real PSP MOSFET model cards carry 370+ real
parameters, well past what a tabular column layout could usefully
show), **Subckts** (every real ``.subckt NAME port1 port2 ...``
block's own real port list), and **Corners** (every real ``.LIB NAME
... .ENDL`` PVT-corner block's own real ``.param``/``.include``
content -- confirmed real in all 6 real `corner*.lib` files). Read-only
-- no editor exists for real ``.model``/``.subckt`` content yet,
matching every other real, display-only domain here (Layers, Magic
Tech's other five domains, GDS, LEF's own Vias tab).

The file picker mirrors ``lef_view.py``'s own **Edit File**/**Create
File** toggle (``gui/file_picker_utils.py``): typing a real, existing
relative path opens it (``file_view_dialog.view_file_dialog``); typing
one that doesn't exist yet writes a real, minimal, valid empty ``.lib``
skeleton (``ihp/spice_models.py``'s own ``create_new_lib_file``), then
reloads and selects it.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..ihp import spice_models as spice_models_mod
from .file_picker_utils import handle_action, update_action_button


class SpiceModelsView(ttk.Frame):
    def __init__(self, parent, pdk_root: Path):
        super().__init__(parent)
        self.pdk_root = pdk_root
        self.lib_files: dict[str, Path] = {}
        self.current: spice_models_mod.SpiceLibFile | None = None

        self._build()
        self.load()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="ngspice .lib file:").pack(side="left")
        self.file_var = tk.StringVar()
        self.file_combo = ttk.Combobox(top, textvariable=self.file_var, width=50)
        self.file_combo.pack(side="left", padx=(4, 12))
        self.file_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())
        self.file_combo.bind("<KeyRelease>", lambda _event: self._update_action_button())

        self.action_button = ttk.Button(top, text="Edit File", command=self._on_action)
        self.action_button.pack(side="left")

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True)

        hint = ttk.Frame(self)
        hint.pack(fill="x", padx=8)
        ttk.Label(
            hint, foreground="#616161",
            text="New file: type a path like libs.tech/ngspice/models/<name>.lib, then Create File.",
        ).pack(side="left")

        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.models_tree = self._make_tree(sub, "Models", ("name", "type", "params"), (200, 100, 640))
        self.subckts_tree = self._make_tree(sub, "Subckts", ("name", "ports"), (200, 640))
        self.corners_tree = self._make_tree(sub, "Corners", ("name", "param_count", "includes", "params"), (140, 90, 220, 500))

    def _make_tree(self, notebook: ttk.Notebook, title: str, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col, width in zip(columns, widths):
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        return tree

    def _update_action_button(self):
        update_action_button(self.action_button, self.pdk_root, self.file_var)

    def _on_action(self):
        handle_action(
            self, self.pdk_root, self.file_var,
            create_fn=spice_models_mod.create_new_lib_file, on_created=self.load,
        )

    def load(self):
        self.lib_files = {
            str(path.relative_to(self.pdk_root)): path
            for path in spice_models_mod.find_lib_files(self.pdk_root)
        }
        names = sorted(self.lib_files)
        self.file_combo["values"] = names
        if names and not self.file_var.get():
            self.file_var.set(names[0])
        self._refresh_all()
        self._update_action_button()

    def _refresh_all(self):
        for row in self.models_tree.get_children():
            self.models_tree.delete(row)
        for row in self.subckts_tree.get_children():
            self.subckts_tree.delete(row)
        for row in self.corners_tree.get_children():
            self.corners_tree.delete(row)

        path = self.lib_files.get(self.file_var.get())
        if path is None:
            self.summary_var.set("No ngspice .lib data loaded -- has ihp/fetch.py been run?")
            self.current = None
            return

        self.current = spice_models_mod.parse_lib_file(path)
        lib = self.current

        for model in lib.models:
            params_text = " ".join(f"{key}={value}" for key, value in model.params)
            self.models_tree.insert("", "end", values=(model.name, model.model_type, params_text))
        for subckt in lib.subckts:
            self.subckts_tree.insert("", "end", values=(subckt.name, " ".join(subckt.ports)))
        for corner in lib.corners:
            params_text = " ".join(f"{key}={value}" for key, value in corner.params)
            self.corners_tree.insert(
                "", "end",
                values=(corner.name, len(corner.params), ", ".join(corner.includes), params_text),
            )

        self.summary_var.set(f"models:{len(lib.models)}  subckts:{len(lib.subckts)}  corners:{len(lib.corners)}")

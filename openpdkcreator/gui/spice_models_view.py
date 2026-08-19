"""Simulation tab: real, parsed ngspice ``.lib`` model cards
(``openpdkcreator/pdklib/spice_models.py``) -- a file picker over all 32
real, downloaded ``libs.tech/ngspice/models/*.lib`` files, since
there's no small, fixed set of "the real ones" to enumerate (mirroring
``lef_view.py``'s own file-picker shape for the same reason).

Three sub-tabs per file: **Models** (every real ``.model NAME TYPE
...`` statement, its own real parameter list shown as one raw
``key=value`` text column rather than a parameter-by-parameter
breakdown -- some real PSP MOSFET model cards carry 370+ real
parameters, well past what a tabular column layout could usefully
show), **Subckts** (every real ``.subckt NAME port1 port2 ...``
block's own real port list), both still read-only -- no editor exists
for real ``.model``/``.subckt`` content yet, matching every other
real, display-only domain here (Layers, Magic Tech's other five
domains, GDS, LEF's own Vias tab) -- and **Corners** (every real
``.LIB NAME ... .ENDL`` PVT-corner block's own real ``.param``/
``.include`` content -- confirmed real in all 6 real `corner*.lib`
files), which **is** editable: a real New/Delete Corner pair plus a
per-corner side form (Name, one ``key = value`` real param override
per line, real ``.include`` file list) -- a real, direct need (this
project's own memristor PDK task explicitly calls for real corners,
and there was no way to author one until now). Persists through
``project_io.py`` the same way DRC Rules/Magic Types/LEF pins do, and
writes back to a real ``.lib`` file via ``pdklib/spice_models_writer.py``'s
own diff-first patching (unedited corners, and every real ``.model``/
``.subckt``/comment, stay byte-for-byte untouched).

The file picker mirrors ``lef_view.py``'s own **Edit File**/**Create
File** toggle (``gui/file_picker_utils.py``): typing a real, existing
relative path opens it (``file_view_dialog.view_file_dialog``); typing
one that doesn't exist yet writes a real, minimal, valid empty ``.lib``
skeleton (``pdklib/spice_models.py``'s own ``create_new_lib_file``), then
reloads and selects it.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..pdklib import spice_models as spice_models_mod
from .file_picker_utils import handle_action, update_action_button


class SpiceModelsView(ttk.Frame):
    def __init__(self, parent, pdk_root: Path):
        super().__init__(parent)
        self.pdk_root = pdk_root
        self.lib_files: dict[str, Path] = {}
        self.current: spice_models_mod.SpiceLibFile | None = None
        # A real file, once parsed, stays cached (not re-parsed fresh
        # on every _refresh_all) so a real, in-session corner edit
        # survives switching to a different .lib file and back -- the
        # same real "one shared, live object" discipline
        # gui/app.py's own lef_cache already established.
        self.lib_cache: dict[Path, spice_models_mod.SpiceLibFile] = {}
        self.corner_overrides: dict[str, list[spice_models_mod.SpiceCorner]] = {}
        self.current_corner: spice_models_mod.SpiceCorner | None = None
        self._corner_by_iid: dict[str, spice_models_mod.SpiceCorner] = {}
        self._suspend_corner_trace = False

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
        self.corners_tree = self._build_corners_tab(sub)

    def _make_tree(self, notebook: ttk.Notebook, title: str, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col, width in zip(columns, widths):
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        return tree

    def _build_corners_tab(self, notebook: ttk.Notebook) -> ttk.Treeview:
        """The one editable sub-tab -- a real tree (left) + New/Delete
        buttons + a per-corner side form (right), the same left-list/
        right-form commit-on-switch layout ``gui/pin_editor.py``'s
        own ``PinEditor`` already uses."""

        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Corners")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)

        button_row = ttk.Frame(frame)
        button_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(button_row, text="New Corner", command=self._new_corner).pack(side="left")
        ttk.Button(button_row, text="Delete Corner", command=self._delete_corner).pack(side="left", padx=(6, 0))

        columns = ("name", "param_count", "includes", "params")
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        for col, width in zip(columns, (140, 90, 220, 400)):
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=width, anchor="w")
        tree.grid(row=1, column=0, sticky="nsew", padx=(0, 4))
        tree.bind("<<TreeviewSelect>>", self._on_corner_select)

        right = ttk.Frame(frame)
        right.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(4, 0))
        right.columnconfigure(1, weight=1)
        right.rowconfigure(3, weight=1)

        ttk.Label(right, text="Name").grid(row=0, column=0, sticky="w", pady=2)
        self.corner_name_var = tk.StringVar()
        self.corner_name_var.trace_add("write", self._on_corner_field_changed)
        ttk.Entry(right, textvariable=self.corner_name_var).grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(right, text="Includes (one file per line)").grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.corner_includes_text = tk.Text(right, height=3, font=("Courier", 9))
        self.corner_includes_text.grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)
        self.corner_includes_text.bind("<<Modified>>", self._on_corner_field_changed)

        ttk.Label(right, text="Params (one \"key = value\" per line)").grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.corner_params_text = tk.Text(right, height=10, font=("Courier", 9))
        self.corner_params_text.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=2)
        right.rowconfigure(4, weight=1)
        self.corner_params_text.bind("<<Modified>>", self._on_corner_field_changed)

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
        self._commit_corner_form()
        for row in self.models_tree.get_children():
            self.models_tree.delete(row)
        for row in self.subckts_tree.get_children():
            self.subckts_tree.delete(row)
        for row in self.corners_tree.get_children():
            self.corners_tree.delete(row)
        self._corner_by_iid = {}

        path = self.lib_files.get(self.file_var.get())
        if path is None:
            self.summary_var.set("No ngspice .lib data loaded -- has pdklib/fetch.py been run?")
            self.current = None
            self._load_corner_into_form(None)
            return

        if path not in self.lib_cache:
            parsed = spice_models_mod.parse_lib_file(path)
            self._apply_corner_overrides(str(path.relative_to(self.pdk_root)), parsed)
            self.lib_cache[path] = parsed
        self.current = self.lib_cache[path]
        lib = self.current

        for model in lib.models:
            params_text = " ".join(f"{key}={value}" for key, value in model.params)
            self.models_tree.insert("", "end", values=(model.name, model.model_type, params_text))
        for subckt in lib.subckts:
            self.subckts_tree.insert("", "end", values=(subckt.name, " ".join(subckt.ports)))
        for corner in lib.corners:
            iid = str(id(corner))
            self._corner_by_iid[iid] = corner
            self.corners_tree.insert("", "end", iid=iid, values=self._corner_row_values(corner))

        self.summary_var.set(f"models:{len(lib.models)}  subckts:{len(lib.subckts)}  corners:{len(lib.corners)}")
        if lib.corners:
            first_iid = str(id(lib.corners[0]))
            self.corners_tree.selection_set(first_iid)
            self._load_corner_into_form(lib.corners[0])
        else:
            self._load_corner_into_form(None)

    # -- Corners: editable ----------------------------------------------------

    def _corner_row_values(self, corner: spice_models_mod.SpiceCorner) -> tuple:
        params_text = " ".join(f"{key}={value}" for key, value in corner.params)
        return (corner.name, len(corner.params), ", ".join(corner.includes), params_text)

    def _on_corner_select(self, _event=None):
        self._commit_corner_form()
        selection = self.corners_tree.selection()
        corner = self._corner_by_iid.get(selection[0]) if selection else None
        self._load_corner_into_form(corner)

    def _load_corner_into_form(self, corner: spice_models_mod.SpiceCorner | None):
        self._suspend_corner_trace = True
        self.current_corner = corner
        self.corner_includes_text.delete("1.0", "end")
        self.corner_params_text.delete("1.0", "end")
        if corner is not None:
            self.corner_name_var.set(corner.name)
            self.corner_includes_text.insert("1.0", "\n".join(corner.includes))
            self.corner_params_text.insert("1.0", "\n".join(f"{key} = {value}" for key, value in corner.params))
        else:
            self.corner_name_var.set("")
        self.corner_includes_text.edit_modified(False)
        self.corner_params_text.edit_modified(False)
        self._suspend_corner_trace = False

    def _commit_corner_form(self):
        corner = self.current_corner
        if corner is None:
            return
        corner.name = self.corner_name_var.get().strip() or corner.name
        corner.includes = [
            line.strip() for line in self.corner_includes_text.get("1.0", "end").splitlines() if line.strip()
        ]
        params: list[tuple[str, str]] = []
        for line in self.corner_params_text.get("1.0", "end").splitlines():
            stripped = line.strip()
            if not stripped or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            params.append((key.strip(), value.strip()))
        corner.params = params
        iid = str(id(corner))
        if self.corners_tree.exists(iid):
            self.corners_tree.item(iid, values=self._corner_row_values(corner))

    def commit_pending_edits(self):
        self._commit_corner_form()

    def _on_corner_field_changed(self, *_args):
        if self._suspend_corner_trace:
            return
        self.corner_includes_text.edit_modified(False)
        self.corner_params_text.edit_modified(False)
        self._commit_corner_form()

    def _new_corner(self):
        if self.current is None:
            return
        self._commit_corner_form()
        n = len(self.current.corners) + 1
        corner = spice_models_mod.SpiceCorner(name=f"NEW_CORNER_{n}")
        self.current.corners.append(corner)
        iid = str(id(corner))
        self._corner_by_iid[iid] = corner
        self.corners_tree.insert("", "end", iid=iid, values=self._corner_row_values(corner))
        self.corners_tree.selection_set(iid)
        self.corners_tree.see(iid)
        self.summary_var.set(
            f"models:{len(self.current.models)}  subckts:{len(self.current.subckts)}  corners:{len(self.current.corners)}"
        )

    def _delete_corner(self):
        if self.current is None:
            return
        selection = self.corners_tree.selection()
        if not selection:
            return
        corner = self._corner_by_iid.get(selection[0])
        if corner is None:
            return
        self.current.corners.remove(corner)
        self.current_corner = None
        self.corners_tree.delete(selection[0])
        del self._corner_by_iid[selection[0]]
        remaining = self.corners_tree.get_children()
        if remaining:
            self.corners_tree.selection_set(remaining[0])
            self._load_corner_into_form(self._corner_by_iid[remaining[0]])
        else:
            self._load_corner_into_form(None)
        self.summary_var.set(
            f"models:{len(self.current.models)}  subckts:{len(self.current.subckts)}  corners:{len(self.current.corners)}"
        )

    def _apply_corner_overrides(self, relpath: str, parsed: spice_models_mod.SpiceLibFile):
        override = self.corner_overrides.get(relpath)
        if override is not None:
            parsed.corners = override

    def apply_saved_corner_overrides(self, overrides: dict[str, list[spice_models_mod.SpiceCorner]]):
        self.corner_overrides = overrides
        for path, parsed in self.lib_cache.items():
            self._apply_corner_overrides(str(path.relative_to(self.pdk_root)), parsed)
        self._refresh_all()

    def collect_corners_by_file(self) -> dict[str, list[spice_models_mod.SpiceCorner]]:
        """Every real ``.lib`` file's own current corner list, for
        every real file parsed so far this session (files never
        visited via this tab are still exactly their real, on-disk
        starting state, so there's nothing to save for them) -- the
        same real shape ``gui/app.py``'s own ``collect_lef_pin_overrides``
        already uses."""

        self._commit_corner_form()
        return {
            str(path.relative_to(self.pdk_root)): parsed.corners
            for path, parsed in self.lib_cache.items()
        }

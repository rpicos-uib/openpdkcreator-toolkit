"""Library Manager tab -- a Cadence-style Libraries | Cells | Views
browser over ``ihp/library_index.py``'s own merged real+registered
index (no separate logic here; this view only calls that module and
``eda_tools.py``'s own launch mechanism -- see both modules' own
docstrings for the real design decisions and the real, source-verified
per-tool "open a specific file" research behind the mapping below).

**Open** launches the real, corresponding tool pointed at a view's own
real file, via ``eda_tools.resolve_launch``'s new ``extra_argv``
(never a new, separate launch mechanism):

- Schematic/Symbol -> ``xschem <file>`` (a bare positional arg -- real,
  confirmed by fetching xschem's own real ``src/options.c``; its
  ``--help`` prints nothing in this container).
- Qucs-S Symbol/Component -> ``qucs-s`` -- launched, but **not** pointed
  at the file: confirmed real, from Qucs-S's own fetched
  ``qucs/main.cpp``, there is no CLI way to open a specific file in the
  interactive GUI (``-i`` only applies in batch ``--netlist``/
  ``--print`` mode). Said plainly to the user before launching, not
  glossed over.
- GDS/Layout -> **two** real, verified options: **Open in KLayout**
  (``klayout -l <real .lyp> <real .gds> -rr <script.rb>`` -- KLayout's
  own existing static ``LaunchGuidance`` already supplies ``-l``;
  ``extra_argv`` adds the real, per-cell GDS path plus a real,
  freshly-written one-line Ruby script,
  ``RBA::CellView::active.cell_name = "<cell>"``, run via ``-rr``
  (confirmed real, from KLayout's own local ``-h`` text: ``-r`` "after
  having loaded files" but exits afterward; ``-rm`` runs *before*
  files load, too early for ``CellView::active`` to have anything yet;
  ``-rr`` is "like -r, but does not exit" -- the one that actually
  works here, verified live in noVNC: the window title and canvas both
  correctly jump straight to the requested real cell inside a real,
  combined multi-macro GDS, closing what was a real, previously
  accepted CLI limit) and **Open in Magic** (a real, freshly-written
  2-line Tcl script -- ``gds read <path>`` then ``load <cell>`` --
  passed as ``extra_argv`` on top of Magic's own existing tech-loading
  ``LaunchGuidance``; verified live, for real, in this project's own
  container: ``gds read`` against a real IHP GDS printed every real
  cell name inside it).
- Magic Layout (``.mag``) -> **Open in Magic**, a real, freshly-written
  1-line Tcl script (``cd <dir>; load <cell>``) -- unlike GDS, a
  ``.mag`` file is already Magic's own real, native format, so no
  ``gds read`` two-step is needed.
- LEF/CDL/SPICE/Verilog/Liberty -> ``file_view_dialog`` (in-app text
  view) -- no real external-tool identity for these, matching
  ``cell_hub_view.py``'s own existing precedent.

**Create** only appears for the seven view kinds with real
create-from-scratch support (``ihp/library_index.py``'s own
``CREATABLE_VIEW_KINDS`` -- xschem Symbol/Schematic, Qucs-S
Symbol/Component, Verilog, Verilog-A, Magic Layout); every other kind
still gets a real **Add...** button. A created Magic Layout is
deliberately *not* meant to be edited in this Python GUI -- it writes
a real, minimal, empty ``.mag`` skeleton (``ihp/mag.py``'s own
``create_new_mag_file``, grounded in Magic's own official file-format
manual and verified live against the real installed Magic binary),
then **Open in Magic** is where the real drawing happens; Magic's own
real ``gds write`` is the real path from there to an actual, real GDS. A created xschem/Qucs-S view's real file
defaults to ``<project_root>/libraries/<library>/<cell>.<ext>`` (a
real, tracked, but entirely optional convention -- nothing elsewhere
requires it). A created **Verilog**/**Verilog-A** view instead defaults
into the already-established ``user_models/{verilog,veriloga}/``
convention (``ihp/user_models.py``) -- real, project-authored model
content, giving it free integration with By Cell's own "User Models"
column and OSDI-snippet generation. Either way, if the cell being
created for already has another real/registered view with known real
pins (LEF, then an xschem symbol, then an existing Verilog/Verilog-A
module of the same name -- ``ihp/library_index.py``'s own
``infer_ports_for_cell``), the new module/port declaration is
pre-populated with those real pins instead of an empty template.

**Add...** registers a real, *existing* file for any view kind at all
-- including the six with no real create-from-scratch support -- and
the file can live anywhere on disk, not just under ``libraries/``.
This is the whole reason this tab tracks real file *locations*
(``ihp/library_index.py``) instead of enforcing a fixed directory
convention: a hand-authored LEF, or a file some other tool already
wrote elsewhere, is just as trackable as something this app created
itself.

**Automatic tracking**: every real refresh of the Cells pane also
scans that library's own default ``libraries/<library>/`` directory
for real files this app didn't itself register yet (``ihp/
library_index.py``'s own ``auto_register_new_files``, content-sniffed
to disambiguate xschem vs. Qucs-S ``.sym`` files -- both share the same
real extension) and registers them immediately -- so a file some other
tool wrote there directly (e.g. a real "Save As" in xschem) shows up
here without an explicit **Add...** click.
"""

from __future__ import annotations

import subprocess
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .. import eda_tools
from .. import export as export_mod
from ..ihp import library_index as li_mod
from ..ihp import mag as mag_mod
from ..ihp import magic_tech as magic_tech_mod
from ..ihp import qucs_sym as qucs_sym_mod
from ..ihp import user_models as user_models_mod
from ..ihp import verilog as verilog_mod
from ..ihp import xschem as xschem_mod
from ..ihp import xschem_sch as xschem_sch_mod
from .file_view_dialog import view_file_dialog
from .tooltip import add_help_icon

LIBRARIES_DIRNAME = li_mod.LIBRARIES_DIRNAME

_TOOL_FOR_VIEW_KIND: dict[str, str] = {
    "xschem_symbol": "xschem",
    "xschem_schematic": "xschem",
    "qucs_symbol": "qucs-s",
    "qucs_component": "qucs-s",
}
"""view_kind -> eda_tools Tool id, for the one-button-launch cases.
GDS gets two real buttons (KLayout/Magic), handled separately below --
not in this simple 1:1 map."""

_EXT_FOR_VIEW_KIND: dict[str, str] = {
    "xschem_symbol": ".sym",
    "xschem_schematic": ".sch",
    "qucs_symbol": ".sym",
    "qucs_component": ".xml",
    "lef": ".lef",
    "cdl": ".cdl",
    "spice": ".spice",
    "verilog": ".v",
    "veriloga": ".va",
    "liberty": ".lib",
    "mag": ".mag",
    "gds": ".gds",
}
"""Every real view kind's own extension -- used by **Create** (the
seven ``li_mod.CREATABLE_VIEW_KINDS`` only) and by **Add...**'s own
file-dialog filter (all twelve, so browsing for an existing LEF/GDS/...
file to register starts pre-filtered too)."""

VIEW_KIND_HELP: dict[str, str] = {
    "xschem_schematic": "The real, editable circuit -- device instances and wires, drawn in xschem. "
                         "What you'd hand-draw or simulate from.",
    "xschem_symbol": "The real, editable device icon xschem shows when this cell is instantiated "
                      "inside another schematic -- pins, shape, no internal circuitry.",
    "qucs_symbol": "Qucs-S's own drawn-geometry symbol for this cell (ports only, no port names) -- "
                   "a separate real format from xschem's own .sym, sharing the same .sym extension.",
    "qucs_component": "Qucs-S's own real device/model definition (parameters, netlist templates) for "
                       "this cell -- what Qucs-S actually simulates.",
    "lef": "The real, physical abstract: pin locations/directions and the cell's own footprint, used "
           "for placement and routing -- no internal geometry, just the outside-facing contract.",
    "cdl": "A real SPICE-family netlist (CDL dialect) describing this cell's own transistor-level "
           "circuit -- used for LVS (layout-vs-schematic) comparison.",
    "spice": "A real, plain SPICE netlist for this cell -- similar role to CDL, a different real "
             "dialect/toolchain expects this one instead.",
    "verilog": "A real, plain digital Verilog module for this cell -- structural/behavioral, for "
               "digital simulation or synthesis.",
    "veriloga": "A real Verilog-A compact model for this cell -- analog/mixed-signal behavior, "
                "compiled with OpenVAF then loaded into ngspice via its own real 'osdi' command.",
    "liberty": "Real timing/power data (.lib) for this cell -- what a digital synthesis/STA tool "
               "reads to know delays, setup/hold, and power per real PVT corner.",
    "mag": "The real, editable Magic layout source for this cell -- draw real geometry here in "
           "Magic itself; Magic's own 'gds write' then produces a real, exportable GDS from it.",
    "gds": "The real, final physical layout (polygons on real mask layers) -- what actually gets "
           "fabricated, or the read-only result of exporting a drawn Magic layout.",
}
"""One real sentence per view kind, shown as a hover tooltip next to
its own row label -- what the file *is*, not how to use this tab."""


def _create_view_file(
    view_kind: str, path: Path, cell_name: str, ports: list[tuple[str, str]] | None = None,
    tech_name: str = "",
) -> None:
    """Dispatches to the one real ``create_new_*`` function for
    *view_kind* -- only ever called for a key in
    ``li_mod.CREATABLE_VIEW_KINDS``. *ports* (real ``(name,
    direction)`` pairs, from ``li_mod.infer_ports_for_cell``) only
    matters for Verilog/Verilog-A -- every other real create-from-
    scratch view here has no real per-cell pin data to seed from.
    *tech_name* only matters for ``mag`` -- the real Magic technology
    name written into its own ``tech <name>`` header line."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if view_kind == "xschem_symbol":
        xschem_mod.create_new_sym_file(path)
    elif view_kind == "xschem_schematic":
        xschem_sch_mod.create_new_sch_file(path)
    elif view_kind == "qucs_symbol":
        qucs_sym_mod.create_new_symbol_geometry_file(path)
    elif view_kind == "qucs_component":
        qucs_sym_mod.create_new_component_file(path, cell_name)
    elif view_kind == "verilog":
        verilog_mod.create_new_verilog_file(path, cell_name, ports)
    elif view_kind == "veriloga":
        verilog_mod.create_new_veriloga_file(path, cell_name, ports)
    elif view_kind == "mag":
        mag_mod.create_new_mag_file(path, tech_name)
    else:
        raise ValueError(f"{view_kind!r} has no real create-from-scratch support")


def _find_tool(tool_id: str) -> eda_tools.Tool | None:
    return next((t for t in eda_tools.TOOL_REGISTRY if t.id == tool_id), None)


class LibraryManagerView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.project_root = export_mod.PROJECT_ROOT
        self.current_library: str | None = None
        self.current_cell: str | None = None
        self._entries: dict[tuple[str, str], li_mod.ViewEntry] = {}
        self._build()
        self.refresh_libraries()

    # -- layout -------------------------------------------------------------

    def _build(self):
        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=8)

        lib_frame = ttk.Frame(body)
        body.add(lib_frame, weight=1)
        self._build_libraries_pane(lib_frame)

        cell_frame = ttk.Frame(body)
        body.add(cell_frame, weight=1)
        self._build_cells_pane(cell_frame)

        views_frame = ttk.Frame(body)
        body.add(views_frame, weight=2)
        self._build_views_pane(views_frame)

        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, anchor="w", foreground="#2e7d32").pack(
            fill="x", padx=8, pady=(0, 8)
        )

    def _build_libraries_pane(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", pady=(0, 4))
        ttk.Label(top, text="Libraries", font=("TkDefaultFont", 10, "bold")).pack(side="left")
        ttk.Button(top, text="New Library...", command=self._new_library).pack(side="right")

        self.library_tree = ttk.Treeview(parent, columns=("kind",), show="headings", selectmode="browse")
        self.library_tree.heading("kind", text="Library (real/project)")
        self.library_tree.column("kind", width=220, anchor="w")
        self.library_tree.pack(fill="both", expand=True)
        self.library_tree.bind("<<TreeviewSelect>>", self._on_library_select)

    def _build_cells_pane(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", pady=(0, 4))
        ttk.Label(top, text="Cells", font=("TkDefaultFont", 10, "bold")).pack(side="left")
        ttk.Button(top, text="New Cell...", command=self._new_cell).pack(side="right")

        self.cell_tree = ttk.Treeview(parent, columns=("views",), show="headings", selectmode="browse")
        self.cell_tree.heading("views", text="Cell (real view count)")
        self.cell_tree.column("views", width=220, anchor="w")
        self.cell_tree.pack(fill="both", expand=True)
        self.cell_tree.bind("<<TreeviewSelect>>", self._on_cell_select)

    def _build_views_pane(self, parent):
        ttk.Label(parent, text="Views", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(0, 4))
        self.views_header_var = tk.StringVar(value="Select a library and cell.")
        ttk.Label(parent, textvariable=self.views_header_var, wraplength=420, justify="left").pack(
            anchor="w", pady=(0, 8)
        )

        self.views_rows_frame = ttk.Frame(parent)
        self.views_rows_frame.pack(fill="both", expand=True)

    # -- Libraries ------------------------------------------------------------

    def refresh_libraries(self):
        selected = self.current_library
        for row in self.library_tree.get_children():
            self.library_tree.delete(row)
        libraries = li_mod.merged_libraries(self.app.pdk_root, self.project_root)
        for name, is_real in libraries:
            label = f"{name}  ({'real' if is_real else 'project'})"
            self.library_tree.insert("", "end", iid=name, values=(label,))
        if selected and self.library_tree.exists(selected):
            self.library_tree.selection_set(selected)
        else:
            self.current_library = None
            self.current_cell = None
            self.refresh_cells()

    def _on_library_select(self, _event=None):
        selection = self.library_tree.selection()
        new_library = selection[0] if selection else None
        # Real Tk quirk, not a hypothetical: <<TreeviewSelect>> is a
        # queued virtual event, only actually dispatched on the next
        # real event-loop pass -- not synchronously when selection_set()
        # is called from Python code. A refresh that rebuilds the tree
        # and re-selects the *same* library (e.g. after Create adds a
        # view to the currently-open library/cell) still re-fires this
        # handler once that queued event is processed, so only reset
        # the current cell when the library selection *actually*
        # changed -- otherwise a real, unchanged cell selection would
        # be silently wiped by a refresh that never meant to change it.
        if new_library != self.current_library:
            self.current_cell = None
        self.current_library = new_library
        self.refresh_cells()

    def _new_library(self):
        name = simpledialog.askstring("New Library", "Library name:", parent=self)
        if not name:
            return
        li_mod.register_library(self.project_root, name)
        self.refresh_libraries()
        if self.library_tree.exists(name):
            self.library_tree.selection_set(name)
        self.status_var.set(f"Registered new, empty library {name!r} -- use New Cell... to start adding cells.")

    # -- Cells ------------------------------------------------------------

    def refresh_cells(self):
        selected = self.current_cell
        for row in self.cell_tree.get_children():
            self.cell_tree.delete(row)
        if self.current_library is None:
            self.refresh_views()
            return
        # Real, not-yet-registered files a tool wrote directly into
        # this library's own default directory (e.g. a real "Save As"
        # in xschem) get picked up automatically here, every refresh --
        # not just via an explicit Add... click.
        auto_found = li_mod.auto_register_new_files(self.project_root, self.current_library)
        if auto_found:
            names = ", ".join(f"{e.cell}/{li_mod.VIEW_KIND_LABELS[e.view_kind]}" for e in auto_found)
            self.status_var.set(f"Automatically tracked {len(auto_found)} new real file(s): {names}")
        entries = li_mod.merged_entries(self.app.pdk_root, self.project_root, self.current_library)
        cell_counts: dict[str, int] = {}
        for cell, _view_kind in entries:
            cell_counts[cell] = cell_counts.get(cell, 0) + 1
        for cell in sorted(cell_counts):
            self.cell_tree.insert("", "end", iid=cell, values=(f"{cell}  ({cell_counts[cell]} view(s))",))
        if selected and self.cell_tree.exists(selected):
            self.cell_tree.selection_set(selected)
        else:
            self.current_cell = None
            self.refresh_views()

    def _on_cell_select(self, _event=None):
        selection = self.cell_tree.selection()
        self.current_cell = selection[0] if selection else None
        self.refresh_views()

    def _new_cell(self):
        if self.current_library is None:
            messagebox.showinfo("New Cell", "Select (or create) a library first.", parent=self)
            return
        name = simpledialog.askstring("New Cell", "Cell name:", parent=self)
        if not name:
            return
        view_kind = self._ask_creatable_view_kind(
            "New Cell", f"Create the first view for {name!r} as:",
        )
        if view_kind is None:
            return
        self.current_cell = name
        self._create_view(view_kind)

    def _ask_creatable_view_kind(self, title: str, prompt: str) -> str | None:
        labels = [li_mod.VIEW_KIND_LABELS[k] for k in li_mod.VIEW_KIND_ORDER if k in li_mod.CREATABLE_VIEW_KINDS]
        kinds = [k for k in li_mod.VIEW_KIND_ORDER if k in li_mod.CREATABLE_VIEW_KINDS]
        choice_window = tk.Toplevel(self)
        choice_window.title(title)
        ttk.Label(choice_window, text=prompt).pack(padx=12, pady=(12, 6))
        chosen: list[str] = []

        def pick(kind: str):
            chosen.append(kind)
            choice_window.destroy()

        for kind, label in zip(kinds, labels):
            ttk.Button(choice_window, text=label, command=lambda k=kind: pick(k)).pack(
                fill="x", padx=12, pady=2
            )
        ttk.Button(choice_window, text="Cancel", command=choice_window.destroy).pack(
            fill="x", padx=12, pady=(6, 12)
        )
        choice_window.transient(self)
        choice_window.grab_set()
        self.wait_window(choice_window)
        return chosen[0] if chosen else None

    # -- Views ------------------------------------------------------------

    def refresh_views(self):
        for widget in self.views_rows_frame.winfo_children():
            widget.destroy()

        if self.current_library is None or self.current_cell is None:
            self.views_header_var.set("Select a library and cell.")
            self._entries = {}
            return

        self.views_header_var.set(f"{self.current_library} / {self.current_cell}")
        all_entries = li_mod.merged_entries(self.app.pdk_root, self.project_root, self.current_library)
        self._entries = {
            view_kind: entry for (cell, view_kind), entry in all_entries.items() if cell == self.current_cell
        }

        for row, view_kind in enumerate(li_mod.VIEW_KIND_ORDER):
            self._build_view_row(row, view_kind)

    def _build_view_row(self, row: int, view_kind: str):
        entry = self._entries.get(view_kind)
        label = li_mod.VIEW_KIND_LABELS[view_kind]

        row_frame = ttk.Frame(self.views_rows_frame)
        row_frame.grid(row=row, column=0, sticky="ew", pady=2)
        self.views_rows_frame.columnconfigure(0, weight=1)

        ttk.Label(row_frame, text=label, width=16, anchor="w").pack(side="left")
        help_text = VIEW_KIND_HELP.get(view_kind, "")
        if help_text:
            add_help_icon(row_frame, help_text).pack(side="left", padx=(0, 4))

        if entry is None:
            ttk.Label(row_frame, text="(absent)", foreground="#9e9e9e").pack(side="left", padx=(4, 8))
            if view_kind in li_mod.CREATABLE_VIEW_KINDS:
                ttk.Button(row_frame, text="Create", command=lambda k=view_kind: self._create_view(k)).pack(
                    side="left", padx=(0, 4)
                )
            ttk.Button(row_frame, text="Add...", command=lambda k=view_kind: self._add_view(k)).pack(side="left")
            if view_kind not in li_mod.CREATABLE_VIEW_KINDS:
                ttk.Label(
                    row_frame, text="  no in-GUI create -- Add an existing file instead", foreground="#e65100",
                ).pack(side="left")
            return

        source_tag = "real" if entry.source == "real" else "project"
        ttk.Label(row_frame, text=f"{entry.path} ({source_tag})", foreground="#2e7d32").pack(
            side="left", padx=(4, 8), fill="x", expand=True
        )

        if view_kind in ("xschem_symbol", "xschem_schematic"):
            ttk.Button(row_frame, text="Open in xschem", command=lambda e=entry: self._open_xschem(e)).pack(
                side="left"
            )
        elif view_kind in ("qucs_symbol", "qucs_component"):
            ttk.Button(row_frame, text="Open in Qucs-S", command=lambda e=entry: self._open_qucs_s(e)).pack(
                side="left"
            )
        elif view_kind == "gds":
            ttk.Button(row_frame, text="Open in KLayout", command=lambda e=entry: self._open_klayout(e)).pack(
                side="left", padx=(0, 4)
            )
            ttk.Button(row_frame, text="Open in Magic", command=lambda e=entry: self._open_magic_gds(e)).pack(
                side="left"
            )
        elif view_kind == "mag":
            ttk.Button(row_frame, text="Open in Magic", command=lambda e=entry: self._open_magic_mag(e)).pack(
                side="left"
            )
        else:
            ttk.Button(row_frame, text="View", command=lambda e=entry: view_file_dialog(self, e.path)).pack(
                side="left"
            )

    # -- Create -------------------------------------------------------------

    def _refresh_preserving_selection(self, library: str, cell: str):
        """Rebuilds every pane while keeping the same real
        library/cell selected. Rebuilding the Libraries/Cells trees
        re-fires ``<<TreeviewSelect>>`` on re-selection (Tk treats a
        fresh insert + reselect of the "same" iid as a real selection
        change, not a no-op) -- which would otherwise run
        ``_on_library_select``'s own real "the user picked a different
        library" reset of ``current_cell`` to ``None``. Capturing and
        restoring the real, unchanged identity explicitly here (rather
        than trusting the cascading refresh/reselect side effects)
        keeps this deterministic regardless of when Tk actually
        dispatches those queued events."""

        self.refresh_libraries()
        if self.library_tree.exists(library):
            self.library_tree.selection_set(library)
        self.current_library = library
        self.refresh_cells()
        if self.cell_tree.exists(cell):
            self.cell_tree.selection_set(cell)
        self.current_library, self.current_cell = library, cell
        self.refresh_views()

    def _default_create_path(self, view_kind: str) -> Path:
        ext = _EXT_FOR_VIEW_KIND[view_kind]
        # Verilog/Verilog-A views created here default into the
        # already-established ``user_models/`` convention
        # (``ihp/user_models.py``), not ``libraries/<library>/`` --
        # this is real, project-authored model content, and landing it
        # there gives it free integration with By Cell's own "User
        # Models" column and the OSDI-snippet generation, both of which
        # already auto-match a user model to a cell by name.
        # ``register_entry`` below still tags it with the current
        # library regardless -- registration is just a grouping label,
        # decoupled from physical file location, matching this whole
        # index's own real design (see ``ihp/library_index.py``'s own
        # docstring).
        if view_kind == "verilog":
            root = user_models_mod.user_models_root(self.project_root) / user_models_mod.VERILOG_DIRNAME
        elif view_kind == "veriloga":
            root = user_models_mod.user_models_root(self.project_root) / user_models_mod.VERILOGA_DIRNAME
        else:
            root = self.project_root / LIBRARIES_DIRNAME / self.current_library
        return root / f"{self.current_cell}{ext}"

    def _default_tech_name(self) -> str:
        """The real Magic technology name a newly-created ``.mag``
        file's own ``tech`` line should declare. Real IHP data (found
        empirically: ``libs.tech/magic/*.tech``) has one complete,
        loadable tech file (``ihp-sg13g2.tech``, the one the real
        ``.magicrc``'s own ``tech load`` line references) plus several
        per-domain *fragments* meant to be ``include``d by it
        (``ihp-sg13g2-GDS.tech``, ``-cifin``, ``-cifout``, ``-drc``,
        ``-extract``) -- each fragment's stem is the main file's own
        stem plus a ``-suffix``, so the shortest stem among every real
        ``.tech`` file found is always the main, real, active
        technology's name. Falls back to the pdk_root's own directory
        name if no ``.tech`` file exists yet (a genuinely from-scratch
        project)."""

        tech_files = magic_tech_mod.find_tech_files(self.app.pdk_root)
        if tech_files:
            return min(tech_files, key=lambda p: (len(p.stem), p.stem)).stem
        return self.app.pdk_root.name

    def _create_view(self, view_kind: str):
        if self.current_library is None or self.current_cell is None:
            return
        default_path = self._default_create_path(view_kind)
        if default_path.is_file():
            messagebox.showerror("Create", f"{default_path} already exists.", parent=self)
            return
        ports: list[tuple[str, str]] | None = None
        if view_kind in ("verilog", "veriloga"):
            ports = li_mod.infer_ports_for_cell(
                self.app.pdk_root, self.project_root, self.current_library, self.current_cell,
            )
        tech_name = self._default_tech_name() if view_kind == "mag" else ""
        try:
            _create_view_file(view_kind, default_path, self.current_cell, ports, tech_name)
        except (FileExistsError, OSError, ValueError) as exc:
            messagebox.showerror("Create", str(exc), parent=self)
            return
        library, cell = self.current_library, self.current_cell
        li_mod.register_entry(self.project_root, library, cell, view_kind, default_path)
        self._refresh_preserving_selection(library, cell)
        if ports:
            self.status_var.set(
                f"Created {li_mod.VIEW_KIND_LABELS[view_kind]} at {default_path} "
                f"with {len(ports)} real pin(s) from an existing view."
            )
        else:
            self.status_var.set(f"Created {li_mod.VIEW_KIND_LABELS[view_kind]} at {default_path}.")

    def _add_view(self, view_kind: str):
        """Registers a real, existing file for this view -- unlike
        **Create**, works for *every* view kind (including the six
        with no real create-from-scratch support), and the file can
        live anywhere on disk, not just under ``libraries/``. This is
        the whole point of tracking real file *locations* rather than
        enforcing a fixed directory convention -- see ``ihp/
        library_index.py``'s own docstring."""

        if self.current_library is None or self.current_cell is None:
            return
        ext = _EXT_FOR_VIEW_KIND.get(view_kind, "")
        label = li_mod.VIEW_KIND_LABELS[view_kind]
        filetypes = [(label, f"*{ext}"), ("All files", "*")] if ext else [("All files", "*")]
        path_str = filedialog.askopenfilename(
            title=f"Add {label} for {self.current_cell}", filetypes=filetypes, parent=self,
        )
        if not path_str:
            return
        path = Path(path_str)
        library, cell = self.current_library, self.current_cell
        li_mod.register_entry(self.project_root, library, cell, view_kind, path)
        self._refresh_preserving_selection(library, cell)
        self.status_var.set(f"Added {label}: {path}")

    # -- Open / launch --------------------------------------------------------

    def _launch(self, tool_id: str, extra_argv: tuple[str, ...] = ()) -> bool:
        tool = _find_tool(tool_id)
        if tool is None:
            messagebox.showerror("Open", f"No {tool_id!r} tool registered.", parent=self)
            return False
        status = eda_tools.check_tool(tool)
        if not status.found:
            messagebox.showerror("Open", f"{tool.name} isn't on PATH.", parent=self)
            return False
        argv, cwd = eda_tools.resolve_launch(tool, status.path, extra_argv=extra_argv)
        subprocess.Popen(argv, cwd=cwd)
        self.status_var.set(f"Launched: {' '.join(argv)}")
        return True

    def _open_xschem(self, entry: li_mod.ViewEntry):
        self._launch("xschem", extra_argv=(str(entry.path),))

    def _open_qucs_s(self, entry: li_mod.ViewEntry):
        messagebox.showinfo(
            "Open in Qucs-S",
            "Qucs-S has no real CLI way to open a specific file in its interactive GUI "
            f"(confirmed from its own real source) -- it will launch blank. Use File > Open "
            f"for:\n\n{entry.path}",
            parent=self,
        )
        self._launch("qucs-s")

    def _open_klayout(self, entry: li_mod.ViewEntry):
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".rb", prefix="openpdkcreator_klayout_cell_", delete=False, encoding="utf-8",
        )
        cell_name = self.current_cell.replace('"', '\\"') if self.current_cell else ""
        with handle:
            handle.write(f'RBA::CellView::active.cell_name = "{cell_name}"\n')
        self._launch("klayout", extra_argv=(str(entry.path), "-rr", handle.name))

    def _open_magic_gds(self, entry: li_mod.ViewEntry):
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".tcl", prefix="openpdkcreator_magic_gds_", delete=False, encoding="utf-8",
        )
        with handle:
            handle.write(f"gds read {entry.path}\nload {self.current_cell}\n")
        self._launch("magic", extra_argv=(handle.name,))

    def _open_magic_mag(self, entry: li_mod.ViewEntry):
        """Unlike GDS (which needs the real ``gds read`` + ``load``
        two-step -- see ``_open_magic_gds`` above), a ``.mag`` file is
        already Magic's own real, native format: a real, freshly-
        written 1-line Tcl script (``cd <dir>; load <cell>``, self-
        contained rather than relying on Magic's own cwd) is enough to
        open it directly, ready for real drawing."""

        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".tcl", prefix="openpdkcreator_magic_mag_", delete=False, encoding="utf-8",
        )
        with handle:
            handle.write(f"cd {entry.path.parent}\nload {entry.path.stem}\n")
        self._launch("magic", extra_argv=(handle.name,))

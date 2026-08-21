"""Library Manager tab -- a Cadence-style Libraries | Cells | Views
browser over ``pdklib/library_index.py``'s own merged real+registered
index (no separate logic here; this view only calls that module and
``eda_tools.py``'s own launch mechanism -- see both modules' own
docstrings for the real design decisions and the real, source-verified
per-tool "open a specific file" research behind the mapping below).

**Open** launches the real, corresponding tool pointed at a view's own
real file, via ``eda_tools.resolve_launch``'s new ``extra_argv``
(never a new, separate launch mechanism):

- Schematic/Symbol -> ``xschem --rcfile <path> <file>`` (the file
  itself is a bare positional arg -- real, confirmed by fetching
  xschem's own real ``src/options.c``; its ``--help`` prints nothing
  in this container, but its real, installed man page documents
  ``--rcfile``). ``_xschem_rcfile`` supplies the ``<path>``: this
  project's own real, persistent ``libs.tech/xschem/xschemrc`` if one
  has been created (Xschem RC File row, top of this tab -- Create
  starts from a real template adapted from IHP's own), else a real,
  freshly-generated minimal one (just the real ``XSCHEM_LIBRARY_PATH``
  append) -- either way pointed at this project's own real
  ``libs.tech/xschem``, a real, found-not-assumed bug fix: this dev
  container's own global ``~/.xschem/xschemrc`` unconditionally
  sources IHP's own hardcoded ``$PDK_ROOT/$PDK/libs.tech/xschem``
  otherwise, for *any* project, confirmed live by a real "IHP" menu
  appearing even when opening a non-IHP (memristor) symbol -- gone
  once ``--rcfile`` replaces the default chain. A project's own
  ``libs.tech/xschem/xschem-menu`` (Xschem Custom Menu row, same
  place) is sourced the same real, generic, presence-only way IHP's
  own real ``xschemrc`` sources its own -- real, adopted IHP menu back
  for the real IHP project, nothing extra for one that ships none.
- Qucs-S Symbol/Component -> ``qucs-s`` -- launched, but **not** pointed
  at the file: confirmed real, from Qucs-S's own fetched
  ``qucs/main.cpp``, there is no CLI way to open a specific file in the
  interactive GUI (``-i`` only applies in batch ``--netlist``/
  ``--print`` mode). Said plainly to the user before launching, not
  glossed over. Its own real Projects workspace *is* redirected,
  though (``_qucs_env``): the same real bug class as Magic/xschem --
  this dev container's own global ``~/.config/qucs/qucs_s.conf``
  hardcodes ``QucsHomeDir`` at IHP's own real workspace -- fixed via a
  real, disposable, per-launch ``XDG_CONFIG_HOME`` copy (Qt's own
  standard lookup for ``QSettings("qucs", "qucs_s")``, confirmed from
  Qucs-S's own fetched ``settings.cpp``) rather than mutating that
  real, shared file, since Qucs-S has no CLI flag for this either.
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

**Create** only appears for the ten view kinds with real
create-from-scratch support (``pdklib/library_index.py``'s own
``CREATABLE_VIEW_KINDS`` -- xschem Symbol/Schematic, Qucs-S
Symbol/Component, Verilog, Verilog-A, Magic Layout, CDL, SPICE,
Liberty); every other kind still gets a real **Add...** button. A
created Magic Layout is deliberately *not* meant to be edited in this
Python GUI -- it writes a real, minimal, empty ``.mag`` skeleton
(``pdklib/mag.py``'s own ``create_new_mag_file``, grounded in Magic's
own official file-format manual and verified live against the real
installed Magic binary), then **Open in Magic** is where the real
drawing happens; Magic's own real ``gds write`` is the real path from
there to an actual, real GDS. A created xschem/Qucs-S/CDL/SPICE/
Liberty view's real file defaults to
``<project_root>/libraries/<library>/<cell>.<ext>`` (a real, tracked,
but entirely optional convention -- nothing elsewhere requires it). A
created **Verilog**/**Verilog-A** view instead defaults into the
already-established ``user_models/{verilog,veriloga}/`` convention
(``pdklib/user_models.py``) -- real, project-authored model content,
giving it free integration with By Cell's own "User Models" column and
OSDI-snippet generation. Either way, if the cell being created for
already has another real/registered view with known real pins (LEF,
then an xschem symbol, then an existing Verilog/Verilog-A module of
the same name -- ``pdklib/library_index.py``'s own
``infer_ports_for_cell``), the new file's own port/pin declarations
are pre-populated with those real pins instead of an empty template
(a real ``*.PININFO`` comment too, for a newly created **CDL** view --
see ``pdklib/netlist.py``'s own ``create_new_cdl_file``; **SPICE**
deliberately gets none, matching the real, confirmed convention that
no real, downloaded SPICE file carries one either).

**Add...** registers a real, *existing* file for any view kind at all
-- including the six with no real create-from-scratch support -- and
the file can live anywhere on disk, not just under ``libraries/``.
This is the whole reason this tab tracks real file *locations*
(``pdklib/library_index.py``) instead of enforcing a fixed directory
convention: a hand-authored LEF, or a file some other tool already
wrote elsewhere, is just as trackable as something this app created
itself.

**Automatic tracking**: every real refresh of the Cells pane also
scans that library's own default ``libraries/<library>/`` directory
for real files this app didn't itself register yet (``pdklib/
library_index.py``'s own ``auto_register_new_files``, content-sniffed
to disambiguate xschem vs. Qucs-S ``.sym`` files -- both share the same
real extension) and registers them immediately -- so a file some other
tool wrote there directly (e.g. a real "Save As" in xschem) shows up
here without an explicit **Add...** click.

**Import from LibMan Project.../Export to LibMan Project...**: real,
native, bidirectional support for IHP-GmbH's own real LibMan tool's
own real ``.projects`` file format (``pdklib/libman_project.py`` -- a
real, bounded parser/writer verified against LibMan's own real,
fetched C++ source and a real, committed ground-truth fixture for this
same SG13G2 PDK; see that module's own docstring for the exact
real grammar and which real commit it's pinned to, and the real risk
that an actively-developed, unversioned external file format could
still drift). Export writes one real ``define("library", "path");``
line per real view whose kind LibMan's own real Import feature
actually understands (GDS/Xschem/Qucs); every other real kind here has
no LibMan counterpart and is silently skipped (counted, not hidden, in
the real status-bar summary afterward). Import registers every real
``define()`` whose own real path resolves to a real, existing file on
this machine -- as a normal, openable view kind when this project
already understands the real file's own extension (``pdklib/
library_index.py``'s own ``infer_view_kind``, the same real,
content-sniffed function **Automatic tracking** above already uses),
or as the new, honestly tracked-but-unopenable **LibMan CORE View**
kind otherwise (LibMan's own real, proprietary Cap'n Proto binary
format -- needs LibMan's own converter toolchain, not embedded here).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .. import eda_tools
from .. import export as export_mod
from ..pdklib import liberty as liberty_mod
from ..pdklib import libman_project as libman_mod
from ..pdklib import library_index as li_mod
from ..pdklib import drc as drc_mod
from ..pdklib import extraction as extraction_mod
from ..pdklib import klayout_server as klayout_server_mod
from ..pdklib import mag as mag_mod
from ..pdklib import netlist as netlist_mod
from ..pdklib import qucs_sym as qucs_sym_mod
from ..pdklib import tool_env as tool_env_mod
from ..pdklib import user_models as user_models_mod
from ..pdklib import verilog as verilog_mod
from ..pdklib import xschem as xschem_mod
from ..pdklib import xschem_sch as xschem_sch_mod
from ..pdklib import xschem_view_switch as xschem_view_switch_mod
from .file_view_dialog import view_file_dialog
from .text_dialog import show_text_dialog
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
ten ``li_mod.CREATABLE_VIEW_KINDS`` only) and by **Add...**'s own
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
    "libman_core": "A real view from IHP-GmbH's own LibMan tool, tracked by location only -- its "
                    "'.layout.core'/'.schematic.core' files are LibMan's own proprietary Cap'n Proto "
                    "format and need LibMan's own converter tools to open; this app can't view it.",
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
    matters for Verilog/Verilog-A/CDL/SPICE/Liberty -- every other real
    create-from-scratch view here has no real per-cell pin data to
    seed from. *tech_name* only matters for ``mag`` -- the real Magic technology
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
    elif view_kind == "cdl":
        netlist_mod.create_new_cdl_file(path, cell_name, ports)
    elif view_kind == "spice":
        netlist_mod.create_new_spice_file(path, cell_name, ports)
    elif view_kind == "liberty":
        liberty_mod.create_new_liberty_file(path, cell_name, ports)
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
        libman_row = ttk.Frame(self)
        libman_row.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Label(libman_row, text="IHP LibMan project file:").pack(side="left")
        ttk.Button(
            libman_row, text="Import from LibMan Project...", command=self._import_libman_project,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            libman_row, text="Export to LibMan Project...", command=self._export_libman_project,
        ).pack(side="left", padx=(6, 0))
        add_help_icon(
            libman_row,
            "Real, native support for IHP-GmbH/LibMan's own real '.projects' file format "
            "(define(\"lib\",\"path\"); lines) -- NOT its separate, much heavier Cap'n Proto "
            "'CORE' binary geometry format, which needs LibMan's own converter tools to read. "
            "LibMan is under active development with no version marker in its own file format; "
            "this is pinned to a specific, real, fetched commit -- see pdklib/libman_project.py.",
        ).pack(side="left", padx=(4, 0))

        xschem_menu_row = ttk.Frame(self)
        xschem_menu_row.pack(fill="x", padx=8, pady=(4, 0))
        ttk.Label(xschem_menu_row, text="Xschem Custom Menu:").pack(side="left")
        self.xschem_menu_status_var = tk.StringVar()
        ttk.Label(xschem_menu_row, textvariable=self.xschem_menu_status_var).pack(side="left", padx=(6, 0))
        self.xschem_menu_create_button = ttk.Button(
            xschem_menu_row, text="Create", command=self._create_xschem_menu,
        )
        self.xschem_menu_create_button.pack(side="left", padx=(6, 0))
        self.xschem_menu_edit_button = ttk.Button(
            xschem_menu_row, text="Edit...", command=self._edit_xschem_menu,
        )
        self.xschem_menu_edit_button.pack(side="left", padx=(6, 0))
        self.xschem_menu_remove_button = ttk.Button(
            xschem_menu_row, text="Remove", command=self._remove_xschem_menu,
        )
        self.xschem_menu_remove_button.pack(side="left", padx=(6, 0))
        add_help_icon(
            xschem_menu_row,
            "A real, project-wide xschem Tcl file (libs.tech/xschem/xschem-menu) -- "
            "sourced automatically by every real Open in xschem launch (_xschem_rcfile), "
            "by on-disk presence alone, same convention as IHP's own real PDK: its own "
            "real xschem-menu there is what adds the real \"IHP\" menu (corner-model "
            "shortcuts, FET/BIP parameter annotators) when working with the real IHP "
            "project -- this row lets a from-scratch project add its own equivalent, "
            "hand-written custom menu the same way, no external editor needed.",
        ).pack(side="left", padx=(4, 0))
        self._refresh_xschem_menu_row()

        xschem_rcfile_row = ttk.Frame(self)
        xschem_rcfile_row.pack(fill="x", padx=8, pady=(4, 0))
        ttk.Label(xschem_rcfile_row, text="Xschem RC File:").pack(side="left")
        self.xschem_rcfile_status_var = tk.StringVar()
        ttk.Label(xschem_rcfile_row, textvariable=self.xschem_rcfile_status_var).pack(side="left", padx=(6, 0))
        self.xschem_rcfile_create_button = ttk.Button(
            xschem_rcfile_row, text="Create", command=self._create_xschem_rcfile,
        )
        self.xschem_rcfile_create_button.pack(side="left", padx=(6, 0))
        self.xschem_rcfile_edit_button = ttk.Button(
            xschem_rcfile_row, text="Edit...", command=self._edit_xschem_rcfile,
        )
        self.xschem_rcfile_edit_button.pack(side="left", padx=(6, 0))
        self.xschem_rcfile_remove_button = ttk.Button(
            xschem_rcfile_row, text="Remove", command=self._remove_xschem_rcfile,
        )
        self.xschem_rcfile_remove_button.pack(side="left", padx=(6, 0))
        add_help_icon(
            xschem_rcfile_row,
            "This project's own real, persistent libs.tech/xschem/xschemrc -- the same "
            "real filename/path IHP's own sg13g2 PDK uses for its own full startup file "
            "(library paths, general preferences, its own custom-menu source line). Used "
            "directly, unmodified, as the real --rcfile every Open in xschem launch passes "
            "once it exists (_xschem_rcfile); until then, a minimal one is auto-generated "
            "each launch instead. Create starts from a real template adapted from IHP's "
            "own real file -- edit freely afterward, no external editor needed.",
        ).pack(side="left", padx=(4, 0))
        self._refresh_xschem_rcfile_row()

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
                side="left", padx=(0, 4)
            )
            if view_kind == "xschem_schematic":
                ttk.Button(
                    row_frame, text="Netlist (View Switches)",
                    command=lambda e=entry: self._netlist_view_switches(e),
                ).pack(side="left")
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
                side="left", padx=(0, 4)
            )
            ttk.Button(
                row_frame, text="Extract to SPICE", command=lambda e=entry: self._extract_spice(e),
            ).pack(side="left", padx=(0, 4))
            reference = self._entries.get("cdl") or self._entries.get("spice")
            if reference is not None:
                ttk.Button(
                    row_frame, text="Run LVS", command=lambda e=entry, r=reference: self._run_lvs(e, r),
                ).pack(side="left", padx=(0, 4))
            ttk.Button(row_frame, text="Run DRC", command=lambda e=entry: self._run_drc(e)).pack(side="left")
        elif view_kind == "libman_core":
            # A real, proprietary LibMan Cap'n Proto binary -- offering
            # a "View" button here would open it through the generic
            # text-preview dialog and show garbled binary, actively
            # misleading rather than honestly absent. No button at all.
            ttk.Label(
                row_frame, text="  LibMan's own format -- open in LibMan itself", foreground="#e65100",
            ).pack(side="left")
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
        # (``pdklib/user_models.py``), not ``libraries/<library>/`` --
        # this is real, project-authored model content, and landing it
        # there gives it free integration with By Cell's own "User
        # Models" column and the OSDI-snippet generation, both of which
        # already auto-match a user model to a cell by name.
        # ``register_entry`` below still tags it with the current
        # library regardless -- registration is just a grouping label,
        # decoupled from physical file location, matching this whole
        # index's own real design (see ``pdklib/library_index.py``'s own
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
        file's own ``tech`` line should declare -- the same real
        "shortest stem among every real .tech file wins" convention
        ``extraction.default_tech_file`` already established (real
        IHP data has one complete, loadable tech file plus several
        per-domain *fragments* whose own stem is always the main
        file's stem plus a ``-suffix``); reused here rather than
        re-derived so every real call site agrees on the same real
        file. Falls back to the pdk_root's own directory name if no
        ``.tech`` file exists yet (a genuinely from-scratch project)."""

        tech_file = extraction_mod.default_tech_file(self.app.pdk_root)
        return tech_file.stem if tech_file is not None else self.app.pdk_root.name

    def _create_view(self, view_kind: str):
        if self.current_library is None or self.current_cell is None:
            return
        default_path = self._default_create_path(view_kind)
        if default_path.is_file():
            messagebox.showerror("Create", f"{default_path} already exists.", parent=self)
            return
        ports: list[tuple[str, str]] | None = None
        if view_kind in ("verilog", "veriloga", "cdl", "spice", "liberty"):
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

        if view_kind in ("verilog", "veriloga", "cdl", "spice", "liberty"):
            self._check_and_report_port_consistency(library, cell)
        if view_kind in ("verilog", "veriloga"):
            self._check_and_report_compile(view_kind, default_path)

    def _check_and_report_compile(self, view_kind: str, path: Path):
        """Real, immediate compile-check right after **Create** writes
        a new Verilog/Verilog-A skeleton -- the closest real
        equivalent this project has to Cadence's own compile-on-save,
        run at the one real point a freshly created file's own content
        is guaranteed to have just changed (see ``gui/
        user_models_view.py``'s own docstring for the other real
        trigger point, **Rescan**, covering files edited externally
        afterward). Silent on a real, clean pass; a real
        ``messagebox.showwarning`` on a real compile error, quoting
        the compiler's own real output directly, never summarized."""

        tool_id = "openvaf" if view_kind == "veriloga" else "iverilog"
        tool = _find_tool(tool_id)
        if tool is None:
            return
        status = eda_tools.check_tool(tool)
        if not status.found:
            return
        model_file = user_models_mod.UserModelFile(path=path, kind=view_kind)
        try:
            result = user_models_mod.run_compile_check(model_file, status.path)
        except subprocess.TimeoutExpired:
            return
        if not result.ok:
            messagebox.showwarning(
                "Compile check",
                f"{path.name} does not compile cleanly with real {tool.name}:\n\n{result.log}",
                parent=self,
            )

    def _check_and_report_port_consistency(self, library: str, cell: str):
        """Real cross-check of every real pin-list source *cell* now
        has (``li_mod.check_port_consistency``) -- run right after
        **Create** seeds a new view from an existing one, since that's
        exactly when a real, previously invisible disagreement between
        two *older* real views becomes worth surfacing (the new view
        only ever inherits from one of them; the others might quietly
        disagree). Silent when consistent -- only a real popup, never a
        dialog on the happy path, matching this tab's own established
        no-news-is-good-news convention for a real, successful
        **Create**."""

        problems = li_mod.check_port_consistency(self.app.pdk_root, self.project_root, library, cell)
        if not problems:
            return
        messagebox.showwarning(
            "Pin consistency",
            f"{cell}: real pin-list disagreement between existing views:\n\n"
            + "\n".join(f"- {p}" for p in problems),
            parent=self,
        )

    def _add_view(self, view_kind: str):
        """Registers a real, existing file for this view -- unlike
        **Create**, works for *every* view kind (including the six
        with no real create-from-scratch support), and the file can
        live anywhere on disk, not just under ``libraries/``. This is
        the whole point of tracking real file *locations* rather than
        enforcing a fixed directory convention -- see ``pdklib/
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

    def _launch(
        self, tool_id: str, extra_argv: tuple[str, ...] = (), extra_env: dict[str, str] | None = None,
    ) -> bool:
        """*extra_env*: real environment variables merged on top of a
        copy of this process's own real ``os.environ`` for just this
        one subprocess -- never mutates anything shared/persistent.
        Exists for **Open in Qucs-S** (``_qucs_env``): a real,
        per-launch, non-invasive way to redirect Qt's own real
        ``QSettings("qucs", "qucs_s")`` lookup via ``XDG_CONFIG_HOME``
        (real, standard, confirmed both from Qucs-S's own fetched real
        ``settings.cpp`` -- a plain two-arg ``QSettings`` constructor,
        no explicit format/path -- and live, empirically: the real
        Projects panel correctly showed a redirected project's own
        real subdirectories) -- Qucs-S has no real CLI flag for this
        (confirmed from its own real, fetched ``main.cpp``: a full
        ``QCommandLineParser`` option list with nothing for the home/
        workspace directory), unlike Magic's ``tech load``/xschem's
        ``--rcfile``."""

        tool = _find_tool(tool_id)
        if tool is None:
            messagebox.showerror("Open", f"No {tool_id!r} tool registered.", parent=self)
            return False
        status = eda_tools.check_tool(tool)
        if not status.found:
            messagebox.showerror("Open", f"{tool.name} isn't on PATH.", parent=self)
            return False
        argv, cwd = eda_tools.resolve_launch(tool, status.path, extra_argv=extra_argv)
        env = {**os.environ, **extra_env} if extra_env else None
        subprocess.Popen(argv, cwd=cwd, env=env)
        self.status_var.set(f"Launched: {' '.join(argv)}")
        return True

    def _xschem_menu_path(self) -> Path:
        return tool_env_mod.xschem_menu_path(self.app.pdk_root)

    def _refresh_xschem_menu_row(self):
        path = self._xschem_menu_path()
        exists = path.is_file()
        self.xschem_menu_status_var.set(str(path) if exists else "(absent)")
        self.xschem_menu_create_button.configure(state="disabled" if exists else "normal")
        self.xschem_menu_edit_button.configure(state="normal" if exists else "disabled")
        self.xschem_menu_remove_button.configure(state="normal" if exists else "disabled")

    def _create_xschem_menu(self):
        path = self._xschem_menu_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '##################### Custom xschem menu (project-specific) #####################\n'
            "#\n"
            "# Real, project-specific xschem menu commands -- sourced automatically by\n"
            "# every real Open in xschem launch (see library_manager_view.py's own\n"
            "# _xschem_rcfile()), modeled on IHP's own real xschem-menu convention for\n"
            "# its sg13g2 PDK: define a proc, register it in postinit_commands, and it\n"
            "# runs once xschem's own real GUI has finished initializing.\n"
            "\n"
            "proc project_menu {} {\n"
            "  global has_x\n"
            "  if { [info exists has_x] } {\n"
            "    set topwin [xschem get top_path]\n"
            "\n"
            "    # Adds a new top-level menu, inserted just before the real \"Netlist\" menu.\n"
            '    $topwin.menubar insert Netlist cascade -label "Project" -menu $topwin.menubar.project\n'
            "    menu $topwin.menubar.project -tearoff 0\n"
            "\n"
            "    # One example entry -- replace with this project's own real commands.\n"
            "    $topwin.menubar.project add command -label {Example command} -command {\n"
            "      tk_messageBox -message {Replace this with a real xschem Tcl command.}\n"
            "    }\n"
            "  }\n"
            "}\n"
            "\n"
            'append postinit_commands "project_menu\\n"\n'
            "\n"
            "##################### /Custom xschem menu #####################\n",
            encoding="utf-8",
        )
        self._refresh_xschem_menu_row()
        view_file_dialog(self, path)
        self._refresh_xschem_menu_row()

    def _edit_xschem_menu(self):
        view_file_dialog(self, self._xschem_menu_path())
        self._refresh_xschem_menu_row()

    def _remove_xschem_menu(self):
        path = self._xschem_menu_path()
        if not messagebox.askyesno(
            "Remove xschem custom menu?",
            f"Delete the real, local file\n{path}\n\n"
            f"This only removes this project's own custom xschem menu -- nothing else.",
            parent=self,
        ):
            return
        path.unlink()
        self._refresh_xschem_menu_row()

    def _xschem_project_rcfile_path(self) -> Path:
        return tool_env_mod.xschem_project_rcfile_path(self.app.pdk_root)

    def _default_xschem_rcfile_content(self) -> str:
        return tool_env_mod.default_xschem_rcfile_content(self.app.pdk_root)

    def _refresh_xschem_rcfile_row(self):
        path = self._xschem_project_rcfile_path()
        exists = path.is_file()
        self.xschem_rcfile_status_var.set(str(path) if exists else "(absent -- auto-generated minimal one used)")
        self.xschem_rcfile_create_button.configure(state="disabled" if exists else "normal")
        self.xschem_rcfile_edit_button.configure(state="normal" if exists else "disabled")
        self.xschem_rcfile_remove_button.configure(state="normal" if exists else "disabled")

    def _create_xschem_rcfile(self):
        path = self._xschem_project_rcfile_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._default_xschem_rcfile_content(), encoding="utf-8")
        self._refresh_xschem_rcfile_row()
        view_file_dialog(self, path)
        self._refresh_xschem_rcfile_row()

    def _edit_xschem_rcfile(self):
        view_file_dialog(self, self._xschem_project_rcfile_path())
        self._refresh_xschem_rcfile_row()

    def _remove_xschem_rcfile(self):
        path = self._xschem_project_rcfile_path()
        if not messagebox.askyesno(
            "Remove xschem RC file?",
            f"Delete the real, local file\n{path}\n\n"
            f"Open in xschem will fall back to a minimal, auto-generated rc file "
            f"(just the real symbol library path) until a new one is created here.",
            parent=self,
        ):
            return
        path.unlink()
        self._refresh_xschem_rcfile_row()

    def _xschem_rcfile(self) -> str | None:
        return tool_env_mod.xschem_rcfile(self.app.pdk_root)

    def _open_xschem(self, entry: li_mod.ViewEntry):
        rcfile = self._xschem_rcfile()
        extra_argv = ("--rcfile", rcfile, str(entry.path)) if rcfile is not None else (str(entry.path),)
        self._launch("xschem", extra_argv=extra_argv)

    def _resolve_extracted_for_cell(self, cell_name: str, sch_path: Path) -> Path | None:
        """Real search for *cell_name*'s own real
        ``pdklib/extraction.py``-written ``<cell>_extracted.spice`` --
        first right next to *sch_path* itself (this project's own real
        convention: every view of one cell lives together in one real
        per-library directory, confirmed live for the memristor
        fixture used to build/verify this feature), then the same real
        dual-root fallback ``pdk_wizard_view.py``'s own
        ``_status_extraction`` already established (a from-scratch
        project's own real ``libraries/`` tree may sit under
        ``export_mod.PROJECT_ROOT`` rather than ``app.pdk_root``)."""

        candidate = sch_path.with_name(f"{cell_name}_extracted.spice")
        if candidate.is_file():
            return candidate
        for root in (self.app.pdk_root, self.project_root):
            for match in root.glob(f"**/{cell_name}_extracted.spice"):
                return match
        return None

    def _netlist_view_switches(self, entry: li_mod.ViewEntry):
        """Real, batch-mode xschem netlist (``xschem_view_switch.
        run_netlist`` -- the same real ``-n -s -q`` flags
        ``walkthrough_full.tex`` Step 27 documents) with this
        schematic's own real per-instance ``view=extracted`` switches
        (set via the real **View Switch** menu this app now injects
        into every xschem launch -- ``xschem_view_switch.py``'s own
        module docstring) applied: each such instance's own default
        behavioral call is replaced with a real ``.include`` of its
        own Magic-extracted netlist plus a call into that file's own
        real top-level subcircuit. Confirmed live end-to-end against a
        real memristor fixture, including a real ngspice run of the
        substituted result via ``pre_osdi``.

        Deliberately writes a derived, regenerated-every-click
        ``<cell>_viewswitch.spice`` next to the schematic rather than
        registering a new view -- the same real rule ``_extract_spice``
        above already documents for its own output."""

        tool = _find_tool("xschem")
        if tool is None:
            messagebox.showerror("Netlist (View Switches)", "No 'xschem' tool registered.", parent=self)
            return
        status = eda_tools.check_tool(tool)
        if not status.found:
            messagebox.showerror("Netlist (View Switches)", f"{tool.name} isn't on PATH.", parent=self)
            return
        self.status_var.set("Running xschem batch netlist...")
        self.update_idletasks()
        rcfile = self._xschem_rcfile()
        try:
            netlist_text, log = xschem_view_switch_mod.run_netlist(entry.path, status.path, rcfile)
        except subprocess.TimeoutExpired:
            messagebox.showerror("Netlist (View Switches)", "xschem did not finish within 60s.", parent=self)
            self.status_var.set("Netlist generation timed out.")
            return
        if netlist_text is None:
            show_text_dialog(
                self, f"Netlist (View Switches) -- {entry.path.stem}",
                f"No output file was written -- netlist generation failed.\n\n{log}",
            )
            self.status_var.set("Netlist generation failed.")
            return

        schematic = xschem_sch_mod.parse_sch_file(entry.path)
        new_text, switched = xschem_view_switch_mod.apply_view_switches(
            netlist_text, schematic, lambda cell_name: self._resolve_extracted_for_cell(cell_name, entry.path),
        )
        out_path = entry.path.with_name(entry.path.stem + "_viewswitch.spice")
        out_path.write_text(new_text, encoding="utf-8")
        self.status_var.set(f"Wrote {out_path}.")
        header = (
            f"Real per-instance view switches applied for: {', '.join(switched)}\n\n" if switched else
            "No instance carried a real view=extracted property -- identical to xschem's own plain netlist.\n\n"
        )
        show_text_dialog(
            self, f"Netlist (View Switches) -- {entry.path.stem}", header + f"Wrote {out_path}\n\n" + new_text,
        )

    def _qucs_env(self) -> dict[str, str] | None:
        return tool_env_mod.qucs_env(self.app.pdk_root)

    def _open_qucs_s(self, entry: li_mod.ViewEntry):
        messagebox.showinfo(
            "Open in Qucs-S",
            "Qucs-S has no real CLI way to open a specific file in its interactive GUI "
            f"(confirmed from its own real source) -- it will launch blank. Use File > Open "
            f"for:\n\n{entry.path}",
            parent=self,
        )
        self._launch("qucs-s", extra_env=self._qucs_env())

    def _open_klayout(self, entry: li_mod.ViewEntry):
        """Reuses a real, already-running KLayout instance across
        repeated real clicks instead of spawning a new window every
        time -- see ``pdklib/klayout_server.py``'s own docstring for
        the real mechanism (the same real idea IHP's own LibMan tool
        uses)."""

        tool = _find_tool("klayout")
        if tool is None:
            messagebox.showerror("Open in KLayout", "No 'klayout' tool registered.", parent=self)
            return
        status = eda_tools.check_tool(tool)
        if not status.found:
            messagebox.showerror("Open in KLayout", f"{tool.name} isn't on PATH.", parent=self)
            return
        self.status_var.set("Opening in KLayout...")
        self.update_idletasks()
        reused = klayout_server_mod.open_cell(
            self.app.pdk_root, status.path, entry.path, self.current_cell or "", lyp_path=self.app.lyp_path,
        )
        self.status_var.set(
            f"Sent {self.current_cell!r} to the real, already-running KLayout." if reused
            else f"Launched a new KLayout for {self.current_cell!r}."
        )

    def _tech_load_line(self) -> str:
        return tool_env_mod.magic_tech_load_line(self.app.pdk_root)

    def _open_magic_gds(self, entry: li_mod.ViewEntry):
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".tcl", prefix="openpdkcreator_magic_gds_", delete=False, encoding="utf-8",
        )
        with handle:
            handle.write(f"{self._tech_load_line()}gds read {entry.path}\nload {self.current_cell}\n")
        self._launch("magic", extra_argv=(handle.name,))

    def _open_magic_mag(self, entry: li_mod.ViewEntry):
        """Unlike GDS (which needs the real ``gds read`` + ``load``
        two-step -- see ``_open_magic_gds`` above), a ``.mag`` file is
        already Magic's own real, native format: a real, freshly-
        written Tcl script (``tech load`` + ``cd <dir>; load <cell>``,
        self-contained rather than relying on Magic's own cwd) is
        enough to open it directly, ready for real drawing."""

        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".tcl", prefix="openpdkcreator_magic_mag_", delete=False, encoding="utf-8",
        )
        with handle:
            handle.write(f"{self._tech_load_line()}cd {entry.path.parent}\nload {entry.path.stem}\n")
        self._launch("magic", extra_argv=(handle.name,))

    def _ask_extract_mode(self) -> str | None:
        chosen: list[str | None] = [None]
        window = tk.Toplevel(self)
        window.title("Extract to SPICE")
        ttk.Label(window, text="Extraction mode:").pack(padx=12, pady=(12, 4))

        def pick(mode: str):
            chosen[0] = mode
            window.destroy()

        ttk.Button(
            window, text="Parasitic (for ngspice simulation)", command=lambda: pick("parasitic"),
        ).pack(fill="x", padx=12, pady=2)
        ttk.Button(
            window, text="LVS (fast, connectivity-only)", command=lambda: pick("lvs"),
        ).pack(fill="x", padx=12, pady=2)
        ttk.Button(window, text="Cancel", command=window.destroy).pack(fill="x", padx=12, pady=(6, 12))
        window.transient(self)
        window.grab_set()
        self.wait_window(window)
        return chosen[0]

    def _extract_spice(self, entry: li_mod.ViewEntry):
        """Real, batch-mode Magic extraction -- see ``pdklib/
        extraction.py``'s own docstring. Deliberately does not
        register the resulting ``.spice`` as a new "SPICE" view: it's
        a derived artifact of this specific layout, re-generated on
        every click, not an authored view of the cell."""

        tool = _find_tool("magic")
        if tool is None:
            messagebox.showerror("Extract to SPICE", "No 'magic' tool registered.", parent=self)
            return
        status = eda_tools.check_tool(tool)
        if not status.found:
            messagebox.showerror("Extract to SPICE", f"{tool.name} isn't on PATH.", parent=self)
            return
        tech_file = extraction_mod.default_tech_file(self.app.pdk_root)
        if tech_file is None:
            messagebox.showerror("Extract to SPICE", "No Magic technology (.tech) file found under this PDK.", parent=self)
            return
        mode = self._ask_extract_mode()
        if mode is None:
            return
        self.status_var.set(f"Running Magic extraction ({mode})...")
        self.update_idletasks()
        try:
            result = extraction_mod.run_extract(entry.path, tech_file, status.path, mode=mode)
        except subprocess.TimeoutExpired:
            messagebox.showerror("Extract to SPICE", "Magic did not finish within 120s.", parent=self)
            self.status_var.set("Extraction timed out.")
            return
        self.status_var.set(f"Extracted {result.spice_path}." if result.ok else "Extraction failed -- see log.")
        show_text_dialog(
            self, f"Extract to SPICE ({mode}) -- {entry.path.stem}",
            (f"Wrote {result.spice_path}\n\n" if result.ok else "No output file was written -- extraction failed.\n\n")
            + result.log,
        )

    def _run_lvs(self, entry: li_mod.ViewEntry, reference: li_mod.ViewEntry):
        """Real, batch-mode extraction (LVS-preset, fast/connectivity-
        only) followed by a real Netgen LVS comparing the freshly
        extracted layout netlist against *reference* (the cell's own
        CDL, or SPICE if no CDL view exists -- ``library_index.py``'s
        own existing CDL-before-SPICE precedence, reused here)."""

        magic_tool = _find_tool("magic")
        netgen_tool = _find_tool("netgen")
        if magic_tool is None or netgen_tool is None:
            messagebox.showerror("Run LVS", "'magic' and/or 'netgen' tool not registered.", parent=self)
            return
        magic_status = eda_tools.check_tool(magic_tool)
        netgen_status = eda_tools.check_tool(netgen_tool)
        if not magic_status.found:
            messagebox.showerror("Run LVS", f"{magic_tool.name} isn't on PATH.", parent=self)
            return
        if not netgen_status.found:
            messagebox.showerror("Run LVS", f"{netgen_tool.name} isn't on PATH.", parent=self)
            return
        tech_file = extraction_mod.default_tech_file(self.app.pdk_root)
        if tech_file is None:
            messagebox.showerror("Run LVS", "No Magic technology (.tech) file found under this PDK.", parent=self)
            return

        self.status_var.set("Extracting layout for LVS...")
        self.update_idletasks()
        try:
            extract_result = extraction_mod.run_extract(entry.path, tech_file, magic_status.path, mode="lvs")
        except subprocess.TimeoutExpired:
            messagebox.showerror("Run LVS", "Magic did not finish within 120s.", parent=self)
            self.status_var.set("LVS aborted: extraction timed out.")
            return
        if not extract_result.ok:
            show_text_dialog(
                self, f"Run LVS -- {entry.path.stem}",
                f"Layout extraction failed, LVS was not run.\n\n{extract_result.log}",
            )
            self.status_var.set("LVS aborted: extraction failed.")
            return

        self.status_var.set("Running netgen LVS...")
        self.update_idletasks()
        try:
            lvs_result = extraction_mod.run_lvs(
                extract_result.spice_path, self.current_cell, reference.path, self.current_cell, netgen_status.path,
            )
        except subprocess.TimeoutExpired:
            messagebox.showerror("Run LVS", "netgen did not finish within 120s.", parent=self)
            self.status_var.set("LVS aborted: netgen timed out.")
            return

        verdict = {True: "MATCH", False: "MISMATCH", None: "UNKNOWN -- no report written"}[lvs_result.matched]
        self.status_var.set(f"LVS result: {verdict}.")
        show_text_dialog(
            self, f"Run LVS -- {entry.path.stem} ({verdict})",
            f"{lvs_result.log}\n\n--- {lvs_result.report_path.name} ---\n{lvs_result.report_text}",
        )

    def _run_drc(self, entry: li_mod.ViewEntry):
        """Real, batch-mode GDS export (``extraction.run_gds_export``,
        since a Magic Layout view doesn't necessarily have a separate,
        registered GDS view of its own) followed by a real KLayout DRC
        run (``drc.run_drc``) against this project's own real, exported
        ``custom_rules.drc`` deck."""

        magic_tool = _find_tool("magic")
        klayout_tool = _find_tool("klayout")
        if magic_tool is None or klayout_tool is None:
            messagebox.showerror("Run DRC", "'magic' and/or 'klayout' tool not registered.", parent=self)
            return
        magic_status = eda_tools.check_tool(magic_tool)
        klayout_status = eda_tools.check_tool(klayout_tool)
        if not magic_status.found:
            messagebox.showerror("Run DRC", f"{magic_tool.name} isn't on PATH.", parent=self)
            return
        if not klayout_status.found:
            messagebox.showerror("Run DRC", f"{klayout_tool.name} isn't on PATH.", parent=self)
            return
        tech_file = extraction_mod.default_tech_file(self.app.pdk_root)
        if tech_file is None:
            messagebox.showerror("Run DRC", "No Magic technology (.tech) file found under this PDK.", parent=self)
            return
        drc_root = drc_mod.find_drc_root(self.app.pdk_root)
        if drc_root is None:
            messagebox.showerror("Run DRC", "No DRC deck found under this PDK (Technology -> DRC Rules).", parent=self)
            return
        drc_script = drc_root / drc_mod.CUSTOM_DRC_FILENAME
        if not drc_script.is_file():
            messagebox.showerror("Run DRC", f"{drc_script} doesn't exist.", parent=self)
            return

        self.status_var.set("Exporting GDS for DRC...")
        self.update_idletasks()
        try:
            gds_result = extraction_mod.run_gds_export(entry.path, tech_file, magic_status.path)
        except subprocess.TimeoutExpired:
            messagebox.showerror("Run DRC", "Magic did not finish within 120s.", parent=self)
            self.status_var.set("DRC aborted: GDS export timed out.")
            return
        if not gds_result.ok:
            show_text_dialog(
                self, f"Run DRC -- {entry.path.stem}",
                f"GDS export failed, DRC was not run.\n\n{gds_result.log}",
            )
            self.status_var.set("DRC aborted: GDS export failed.")
            return

        self.status_var.set("Running KLayout DRC...")
        self.update_idletasks()
        try:
            drc_result = drc_mod.run_drc(gds_result.gds_path, drc_script, klayout_status.path)
        except subprocess.TimeoutExpired:
            messagebox.showerror("Run DRC", "KLayout did not finish within 120s.", parent=self)
            self.status_var.set("DRC aborted: KLayout timed out.")
            return

        if drc_result.violation_count is None:
            verdict = "UNKNOWN -- no report written"
        elif drc_result.violation_count == 0:
            verdict = "CLEAN"
        else:
            verdict = f"{drc_result.violation_count} violation(s)"
        self.status_var.set(f"DRC result: {verdict}.")
        report_text = drc_result.report_path.read_text(encoding="utf-8") if drc_result.report_path.is_file() else ""
        show_text_dialog(
            self, f"Run DRC -- {entry.path.stem} ({verdict})",
            f"{drc_result.log}\n\n--- {drc_result.report_path.name} ---\n{report_text}",
        )

    # -- IHP LibMan project-file import/export ---------------------------------

    _LIBMAN_EXPORTABLE_KINDS = ("gds", "xschem_symbol", "xschem_schematic", "qucs_symbol", "qucs_component")
    """Real view kinds LibMan's own real Import doc lists as real,
    convertible source formats (GDS/Xschem/Qucs -- see ``pdklib/
    libman_project.py``'s own docstring for the real, fetched source).
    Every other real kind here (LEF/CDL/SPICE/Verilog/Liberty/Magic
    Layout) has no real LibMan counterpart, so exporting them would
    just be a dead ``define()`` LibMan itself can't do anything with."""

    def _export_libman_project(self):
        path_str = filedialog.asksaveasfilename(
            title="Export to LibMan Project", defaultextension=".projects",
            filetypes=[("LibMan project file", "*.projects"), ("All files", "*")], parent=self,
        )
        if not path_str:
            return
        defines: list[libman_mod.LibManDefine] = []
        skipped = 0
        for library, _is_real in li_mod.merged_libraries(self.app.pdk_root, self.project_root):
            entries = li_mod.merged_entries(self.app.pdk_root, self.project_root, library)
            for (_cell, view_kind), entry in entries.items():
                if view_kind not in self._LIBMAN_EXPORTABLE_KINDS:
                    skipped += 1
                    continue
                defines.append(libman_mod.LibManDefine(name=library, path=str(entry.path)))
        Path(path_str).write_text(libman_mod.render_project_file(defines))
        self.status_var.set(
            f"Exported {len(defines)} real view(s) to {path_str} "
            f"({skipped} real view(s) skipped -- no real LibMan-understood format for them)."
        )

    def _import_libman_project(self):
        path_str = filedialog.askopenfilename(
            title="Import from LibMan Project",
            filetypes=[("LibMan project file", "*.projects *.lib"), ("All files", "*")], parent=self,
        )
        if not path_str:
            return
        try:
            project = libman_mod.parse_project_file(Path(path_str))
        except libman_mod.LibManParseError as exc:
            messagebox.showerror("Import from LibMan Project", str(exc), parent=self)
            return
        registered = 0
        opaque = 0
        skipped = 0
        for define in project.defines:
            resolved = libman_mod.resolve_path(define)
            if not resolved.is_file():
                # A real, honest LibMan gap, not a bug: a define() path
                # can be a bare, non-file reference (its own real
                # "analogLib" self-reference is exactly this), or point
                # at a real file simply not present on this machine.
                skipped += 1
                continue
            view_kind = li_mod.infer_view_kind(resolved)
            if view_kind is None:
                view_kind = "libman_core"
                opaque += 1
            else:
                registered += 1
            cell = libman_mod.infer_library_name(str(resolved))
            li_mod.register_entry(self.project_root, define.name, cell, view_kind, resolved)
        self.refresh_libraries()
        self.status_var.set(
            f"Imported from {path_str}: {registered} real, viewable view(s) + {opaque} real LibMan "
            f"CORE view(s) (tracked, not openable) registered; {skipped} real define(s) skipped "
            f"(no real file found at their own real path)."
        )

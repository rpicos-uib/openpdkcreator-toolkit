"""A guided PDK-authoring map: one new GUI tab laying out every real
domain this project already knows how to read/edit as a flowchart --
starting from the real layout/technology definition (**Layers**) at
the top, then forking into a **Digital** path (Verilog / Liberty /
CDL-SPICE, all surfaced in the By Cell tab) and an **Analog /
Memristor** path (User Models Verilog-A, xschem Symbols/Schematics,
Qucs-S Symbols/Components, ngspice Models), both converging back into
**By Cell**, then **GDS**, then **Export / Package**.

This is a deliberately *different*, simpler widget from
``geometry_canvas.py``: that one edits a real device's own real,
numeric coordinates; this one is a static, hand-laid-out conceptual
diagram of *stages*, not tied to any one PDK's real geometry.

Written explicitly toward this project's own stated end goal: using
this same generic tool to create/maintain a from-scratch **memristor**
PDK, not just to browse the real, downloaded IHP reference deck. Each
node's own "For a memristor PDK" note says plainly what that stage
means for a 2-terminal device with no IHP precedent to copy from.

**A real, honest gap, surfaced once as a legend callout and again per
node**: only xschem Symbols/Schematics and Qucs-S Symbols/Components
support creating a brand-new file from inside this GUI today (their
own "New..." actions -- see ``ihp/xschem.py``'s ``create_new_sym_file``,
``ihp/xschem_sch.py``'s ``create_new_sch_file``, ``ihp/qucs_sym.py``'s
``create_new_symbol_geometry_file``/``create_new_component_file``).
Every other domain (Layers, Magic Tech, DRC Rules, LEF, Verilog,
Liberty, CDL/SPICE, ngspice Models, and User Models' own ``.va``/``.v``
files) requires a real file to already exist on disk -- hand-place one
(copied from a template/reference PDK, or written in an external
editor) under the matching real path, and this tool can load and edit
it from there. This is not glossed over: a from-scratch memristor PDK
genuinely starts smallest at User Models (just write a ``.va`` file and
drop it under ``user_models/veriloga/`` -- no template needed at all)
and the xschem/Qucs-S symbol editors (draw a device symbol from
nothing), and grows outward from there.

Status per node is computed directly from *app.pdk_root* (and, for User
Models, ``export.PROJECT_ROOT``) on every ``refresh()`` -- cheap
directory globs, the same ``find_*``/``discover_families`` helpers
every other tab already uses, never a full parse -- so it reflects
whatever project is actually loaded right now, not a cached guess.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable

from .. import export as export_mod
from ..ihp import cells as cells_mod
from ..ihp import drc as drc_mod
from ..ihp import layers as layers_mod
from ..ihp import lef as lef_mod
from ..ihp import magic_tech as magic_tech_mod
from ..ihp import qucs_sym as qucs_sym_mod
from ..ihp import spice_models as spice_models_mod
from ..ihp import user_models as user_models_mod
from ..ihp import xschem as xschem_mod
from ..ihp import xschem_sch as xschem_sch_mod
from .settings_view import DEFAULT_PROJECT_NAME

_COLOR_DONE = "#2e7d32"
_COLOR_TODO = "#616161"
_COLOR_GAP = "#e65100"
_COLOR_INFO = "#1565c0"
_BOX_W, _BOX_H = 180, 60
_COL_SPACING, _ROW_SPACING = 210, 95
_MARGIN = 30


@dataclass
class WizardStage:
    stage_id: str
    title: str
    col: int
    row: int
    goto_path: tuple[str, ...] | None
    description: str
    memristor_note: str
    status_fn: Callable[[object], tuple[bool, str, str | None]]
    """Returns ``(has_data, detail, gap_note)``. *gap_note* is only set
    when *has_data* is False AND this tool has no in-GUI way to create
    that file from nothing -- it explains the real workaround."""


def _glob_count(app, pattern: str) -> int:
    return len(list(app.pdk_root.glob(pattern)))


def _status_overview(app):
    from ..ihp import inventory as inventory_mod

    count = len(inventory_mod.scan_all(app.pdk_root))
    return True, f"{count} real tool director(y/ies) inventoried under {app.pdk_root.name}/.", None


def _status_project_setup(app):
    started = app.project_name != DEFAULT_PROJECT_NAME
    return started, f"Project name: {app.project_name!r}.", None


def _status_layers(app):
    path = layers_mod.find_lyp(app.pdk_root)
    if path is None:
        return (
            False,
            "No real .lyp file found under libs.tech/.",
            "This tool can't create a brand-new .lyp from scratch yet -- "
            "start from a template or an existing PDK's .lyp (e.g. copy "
            "IHP's own sg13g2.lyp) and edit its layers in the Layers tab "
            "to match your own stack.",
        )
    return True, f"{len(app.project.layers)} real layer(s) loaded from {path.name}.", None


def _status_magic_tech(app):
    files = magic_tech_mod.find_tech_files(app.pdk_root)
    if not files:
        return (
            False,
            "No real Magic .tech file found under libs.tech/.",
            "No in-GUI way to create one from scratch -- start from a "
            "template .tech file and edit its types/planes/DRC/extract "
            "rules in the Magic Tech tab.",
        )
    return True, f"{len(files)} real .tech file(s) found.", None


def _status_drc_rules(app):
    root = drc_mod.find_drc_root(app.pdk_root)
    if root is None:
        return (
            False,
            "No real DRC deck found.",
            "No in-GUI way to create a DRC deck from scratch -- start "
            "from a template KLayout DRC script and edit rule "
            "id/description/value in the DRC Rules tab.",
        )
    return True, f"{len(app.project.design_rules)} real rule(s) extracted from {root.name}.", None


def _status_lef(app):
    files = lef_mod.find_lef_files(app.pdk_root)
    if not files:
        return (
            False,
            "No real .lef file found under libs.ref/.",
            "No in-GUI way to create a .lef from scratch -- start from a "
            "template macro and edit its pins in the LEF tab.",
        )
    return True, f"{len(files)} real .lef file(s) found.", None


def _status_verilog(app):
    n = _glob_count(app, "libs.ref/*/verilog/*.v")
    if n == 0:
        return (
            False,
            "No real digital Verilog module found under libs.ref/.",
            "No in-GUI way to author one from scratch -- either hand-write "
            "a .v file under libs.ref/<family>/verilog/, or (for a "
            "memristor device) skip this and author it as a User Model "
            "instead, which By Cell picks up automatically by name.",
        )
    return True, f"{n} real .v file(s) found across libs.ref/*/verilog/.", None


def _status_liberty(app):
    n = _glob_count(app, "libs.ref/*/lib/*.lib")
    if n == 0:
        return (
            False,
            "No real Liberty (.lib) file found under libs.ref/.",
            "No in-GUI way to author one from scratch -- hand-write a "
            ".lib file (or adapt a template) under libs.ref/<family>/lib/.",
        )
    return True, f"{n} real .lib file(s) found across libs.ref/*/lib/.", None


def _status_cdl_spice(app):
    n = _glob_count(app, "libs.ref/*/cdl/*.cdl") + _glob_count(app, "libs.ref/*/spice/*.spice")
    if n == 0:
        return (
            False,
            "No real CDL/SPICE netlist found under libs.ref/.",
            "No in-GUI way to author one from scratch -- hand-write a "
            ".cdl/.spice file under libs.ref/<family>/{cdl,spice}/.",
        )
    return True, f"{n} real .cdl/.spice file(s) found across libs.ref/*/.", None


def _status_user_models(app):
    files = user_models_mod.find_user_model_files(export_mod.PROJECT_ROOT)
    if not files:
        return (
            False,
            "No user_models/verilog/*.v or user_models/veriloga/*.va file found yet.",
            None,
        )
    n_va = sum(1 for _p, kind in files if kind == "veriloga")
    n_v = len(files) - n_va
    return True, f"{len(files)} user model file(s) found ({n_va} Verilog-A, {n_v} Verilog).", None


def _status_xschem_sym(app):
    files = xschem_mod.find_sym_files(app.pdk_root)
    return bool(files), f"{len(files)} real xschem symbol file(s) found.", None


def _status_xschem_sch(app):
    files = xschem_sch_mod.find_sch_files(app.pdk_root)
    return bool(files), f"{len(files)} real xschem schematic file(s) found.", None


def _status_qucs_sym(app):
    files = qucs_sym_mod.find_symbol_geometry_files(app.pdk_root)
    return bool(files), f"{len(files)} real Qucs-S symbol file(s) found.", None


def _status_qucs_components(app):
    files = qucs_sym_mod.find_component_files(app.pdk_root)
    return bool(files), f"{len(files)} real Qucs-S component file(s) found.", None


def _status_ngspice(app):
    files = spice_models_mod.find_lib_files(app.pdk_root)
    if not files:
        return (
            False,
            "No real ngspice .lib model file found under libs.tech/ngspice/models/.",
            "No in-GUI way to author one from scratch -- write a real "
            ".model/.subckt deck by hand (or adapt an existing one) and "
            "place it under libs.tech/ngspice/models/.",
        )
    return True, f"{len(files)} real .lib model file(s) found.", None


def _status_by_cell(app):
    families = cells_mod.discover_families(app.pdk_root)
    return bool(families), f"{len(families)} real cell family/families found under libs.ref/.", None


def _status_gds(app):
    n = _glob_count(app, "libs.ref/*/gds/*.gds")
    if n == 0:
        return (
            False,
            "No real .gds file found under libs.ref/.",
            "There's no in-GUI GDS editor at all (view-only, via "
            "ihp/gds.py's KLayout API) -- draw the physical layout in "
            "KLayout or Magic directly and place the .gds under "
            "libs.ref/<family>/gds/.",
        )
    return True, f"{n} real .gds file(s) found across libs.ref/*/gds/.", None


def _status_export(app):
    return True, "Available any time via File > Export Edited ... .", None


_STAGES: list[WizardStage] = [
    WizardStage(
        "overview", "Overview", 2, 0, ("Overview",),
        "The real, per-tool file inventory -- see what's actually present "
        "under this project's pdk_root before touching anything.",
        "For a from-scratch memristor PDK, expect this to start almost "
        "empty -- that's the normal starting point, not a bug.",
        _status_overview,
    ),
    WizardStage(
        "project_setup", "Project Setup", 2, 1, ("Settings", "General"),
        "Name this project and confirm where it (and the real source PDK "
        "it's derived from) live on disk.",
        "Give it a name that says what it is, e.g. \"memristor-pdk\", "
        "distinct from the IHP reference deck you may be starting from.",
        _status_project_setup,
    ),
    WizardStage(
        "layers", "Layers (.lyp)", 2, 2, ("Technology", "Layers"),
        "The real KLayout layer stack -- every other real file (LEF, GDS, "
        "DRC) ultimately refers back to these layer/purpose pairs. This "
        "is the layout definition everything else branches from.",
        "Define your own physical stack here: e.g. a bottom electrode "
        "layer, a resistive-switching layer, a top electrode layer, plus "
        "whatever via/cut layers connect a memristor cell to standard "
        "metal routing.",
        _status_layers,
    ),
    WizardStage(
        "magic_tech", "Magic Tech", 1, 3, ("Technology", "Magic Tech"),
        "Magic's own types/planes/contacts/aliases/styles/DRC/extract/CIF "
        "rules -- Magic's native technology-file counterpart to the .lyp.",
        "Only needed if you plan to lay out or verify cells in Magic; "
        "otherwise this can stay empty for a KLayout-only flow.",
        _status_magic_tech,
    ),
    WizardStage(
        "drc_rules", "DRC Rules", 3, 3, ("Technology", "DRC Rules"),
        "Design-rule checks extracted from a real KLayout DRC deck -- "
        "minimum widths/spacings/enclosures that a real layout must obey.",
        "Your memristor stack's own rules: minimum electrode overlap, "
        "switching-layer enclosure, via alignment to the electrodes, etc.",
        _status_drc_rules,
    ),
    WizardStage(
        "lef", "LEF", 2, 4, ("Cells", "LEF"),
        "Abstract place-and-route views: a cell's real footprint, "
        "pin shapes, and routing obstructions, independent of its full "
        "layout.",
        "A 2-terminal memristor cell needs just two real pins (e.g. "
        "TE/BE) -- draw its LEF footprint here once its layers exist.",
        _status_lef,
    ),
    WizardStage(
        "verilog", "Verilog", 0, 5, ("Cells", "By Cell"),
        "Digital behavioral views -- module port lists for standard "
        "cells, surfaced per-cell in the By Cell tab.",
        "Not usually relevant to an analog memristor device -- skip "
        "unless you're also building digital cells around it.",
        _status_verilog,
    ),
    WizardStage(
        "liberty", "Liberty", 0, 6, ("Cells", "By Cell"),
        "Timing/power characterization (.lib) for digital cells, "
        "surfaced per-cell in the By Cell tab.",
        "Not applicable to an analog memristor device on its own.",
        _status_liberty,
    ),
    WizardStage(
        "cdl_spice", "CDL / SPICE", 0, 7, ("Cells", "By Cell"),
        "Flat SPICE-level netlists (.cdl/.spice) for real cells, "
        "surfaced per-cell in the By Cell tab.",
        "A digital-flow counterpart to the analog User Model path on the "
        "right -- most memristor work will use that path instead.",
        _status_cdl_spice,
    ),
    WizardStage(
        "user_models", "User Models (Verilog-A)", 4, 5, ("Simulation", "User Models"),
        "Your own Verilog/Verilog-A behavioral models, tracked as real "
        "project content (not gitignored, not part of the downloaded "
        "PDK) under user_models/{verilog,veriloga}/.",
        "The real starting point for a memristor compact model: write a "
        "module implementing your I-V/state-variable equations in a "
        ".va file, name it (or link it) to a real or new cell name, and "
        "By Cell picks it up automatically.",
        _status_user_models,
    ),
    WizardStage(
        "xschem_sym", "xschem Symbol", 4, 6, ("Simulation", "xschem", "Symbols"),
        "A real xschem device symbol: pins plus drawn geometry (lines, "
        "arcs, text) -- editable in a real graphical canvas, or created "
        "from scratch via New Symbol File.",
        "Draw your memristor's own 2-terminal symbol -- two real pins "
        "(name=/dir=), whatever schematic glyph you want (e.g. the "
        "standard memristor \"pinched hysteresis\" box symbol).",
        _status_xschem_sym,
    ),
    WizardStage(
        "xschem_sch", "xschem Schematic", 4, 7, ("Simulation", "xschem", "Schematics"),
        "A real xschem schematic: instances of other symbols wired "
        "together -- editable in the same graphical canvas, place new "
        "instances by browsing the real symbol library.",
        "Build a testbench schematic here: your new memristor symbol "
        "plus a voltage source and probes, to simulate the compact "
        "model you wrote as a User Model.",
        _status_xschem_sch,
    ),
    WizardStage(
        "qucs_sym", "Qucs-S Symbol", 4, 8, ("Simulation", "Qucs-S", "Symbols"),
        "A real Qucs-S symbol's own drawn geometry (lines/arcs/text) plus "
        "its port positions -- Qucs-S's own graphical counterpart to an "
        "xschem symbol, for users of that simulator instead.",
        "Optional second symbol for the same device, only needed if you "
        "also want to simulate in Qucs-S rather than (or as well as) "
        "ngspice/Xyce via xschem.",
        _status_qucs_sym,
    ),
    WizardStage(
        "qucs_components", "Qucs-S Component", 4, 9, ("Simulation", "Qucs-S", "Components"),
        "A Qucs-S component's own real parameter list and netlist "
        "templates -- what actually gets instantiated in a Qucs-S "
        "netlist, distinct from its symbol's drawn geometry.",
        "Declares your memristor's simulation parameters (e.g. Ron/Roff/ "
        "Rinit/window-function coefficients) for Qucs-S netlisting.",
        _status_qucs_components,
    ),
    WizardStage(
        "ngspice", "ngspice Models", 4, 10, ("Simulation", "ngspice Models"),
        "Real .model/.subckt statements ngspice uses at simulation time "
        "-- read-only here, no editor exists for this domain yet.",
        "If your Verilog-A compact model needs OSDI compilation to run "
        "in ngspice, see the User Models tab's own Generate OSDI Snippet "
        "action; PVT-corner .model decks would live here.",
        _status_ngspice,
    ),
    WizardStage(
        "by_cell", "By Cell", 2, 11, ("Cells", "By Cell"),
        "The cross-tool convergence point: pick one real cell name, see "
        "which of its real views (LEF/CDL/SPICE/Verilog/Liberty/GDS/User "
        "Models) actually exist, side by side.",
        "Your memristor cell's own real name should show up here once "
        "its LEF and/or User Model exist -- even before every other view "
        "does; a cell with only a User Model is a real, valid entry.",
        _status_by_cell,
    ),
    WizardStage(
        "gds", "GDS", 2, 12, ("Cells", "By Cell"),
        "The real physical layout -- view-only here (bounding box, "
        "per-layer shape counts via KLayout's own Python API).",
        "The actual drawn memristor stack cross-section/footprint -- "
        "drawn in KLayout or Magic directly, not in this tool.",
        _status_gds,
    ),
    WizardStage(
        "export", "Export / Package", 2, 13, None,
        "File > Export Edited ... writes every structured-editable "
        "domain's real in-memory edits back into real, valid file "
        "text (never touching the original data/ tree).",
        "Once your memristor PDK's layers/LEF/DRC/symbols/models are in "
        "place, export them, then package the result as a real, "
        "installable open_pdks-format tree (see the Toolchain tab).",
        _status_export,
    ),
]

_EDGES: list[tuple[str, str]] = [
    ("overview", "project_setup"),
    ("project_setup", "layers"),
    ("layers", "magic_tech"),
    ("layers", "drc_rules"),
    ("magic_tech", "lef"),
    ("drc_rules", "lef"),
    ("lef", "verilog"),
    ("lef", "user_models"),
    ("verilog", "liberty"),
    ("liberty", "cdl_spice"),
    ("cdl_spice", "by_cell"),
    ("user_models", "xschem_sym"),
    ("xschem_sym", "xschem_sch"),
    ("xschem_sym", "qucs_sym"),
    ("qucs_sym", "qucs_components"),
    ("xschem_sch", "ngspice"),
    ("qucs_components", "ngspice"),
    ("user_models", "by_cell"),
    ("by_cell", "gds"),
    ("gds", "export"),
]


def _box_center(stage: WizardStage) -> tuple[int, int]:
    x = _MARGIN + stage.col * _COL_SPACING + _BOX_W // 2
    y = _MARGIN + stage.row * _ROW_SPACING + _BOX_H // 2
    return x, y


class PdkWizardView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._stage_by_id = {stage.stage_id: stage for stage in _STAGES}
        self._box_ids: dict[str, int] = {}
        self._label_ids: dict[str, int] = {}
        self._selected: str | None = None
        self._build()

    def _build(self):
        intro = ttk.Frame(self)
        intro.pack(fill="x", padx=10, pady=(10, 4))
        ttk.Label(
            intro,
            text=(
                "Building a PDK from scratch (e.g. a custom memristor PDK): start at the "
                "top and work down, forking into whichever of Digital / Analog-Memristor "
                "you need. Click a box for details; \"Go to Tab\" jumps straight there."
            ),
            wraplength=760,
            justify="left",
        ).pack(anchor="w")
        legend = ttk.Frame(self)
        legend.pack(fill="x", padx=10, pady=(0, 6))
        for color, text in (
            (_COLOR_DONE, "real data present"),
            (_COLOR_TODO, "not started (creatable in this GUI)"),
            (_COLOR_GAP, "not started -- no in-GUI \"create new\" yet"),
            (_COLOR_INFO, "always available"),
        ):
            swatch = tk.Canvas(legend, width=14, height=14, highlightthickness=0)
            swatch.create_rectangle(1, 1, 13, 13, fill=color, outline=color)
            swatch.pack(side="left", padx=(0, 4))
            ttk.Label(legend, text=text).pack(side="left", padx=(0, 14))
        ttk.Button(legend, text="Refresh Status", command=self.refresh).pack(side="right")

        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        canvas_frame = ttk.Frame(body)
        body.add(canvas_frame, weight=3)

        max_col = max(stage.col for stage in _STAGES)
        max_row = max(stage.row for stage in _STAGES)
        width = _MARGIN * 2 + (max_col + 1) * _COL_SPACING
        height = _MARGIN * 2 + (max_row + 1) * _ROW_SPACING

        self.canvas = tk.Canvas(canvas_frame, background="white", highlightthickness=0)
        vbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        hbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set, scrollregion=(0, 0, width, height))
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        detail_frame = ttk.Frame(body)
        body.add(detail_frame, weight=2)

        self.detail_title = ttk.Label(detail_frame, text="Select a stage", font=("TkDefaultFont", 12, "bold"))
        self.detail_title.pack(anchor="w", padx=4, pady=(4, 2))
        self.detail_status = ttk.Label(detail_frame, text="", wraplength=340, justify="left")
        self.detail_status.pack(anchor="w", padx=4, pady=(0, 8))

        ttk.Label(detail_frame, text="What this is", font=("TkDefaultFont", 9, "bold")).pack(anchor="w", padx=4)
        self.detail_description = ttk.Label(detail_frame, text="", wraplength=340, justify="left")
        self.detail_description.pack(anchor="w", padx=4, pady=(0, 8))

        ttk.Label(detail_frame, text="For a memristor PDK", font=("TkDefaultFont", 9, "bold")).pack(anchor="w", padx=4)
        self.detail_memristor = ttk.Label(detail_frame, text="", wraplength=340, justify="left", foreground="#4a148c")
        self.detail_memristor.pack(anchor="w", padx=4, pady=(0, 8))

        self.detail_gap = ttk.Label(detail_frame, text="", wraplength=340, justify="left", foreground=_COLOR_GAP)
        self.detail_gap.pack(anchor="w", padx=4, pady=(0, 8))

        self.goto_button = ttk.Button(detail_frame, text="Go to Tab", command=self._on_goto, state="disabled")
        self.goto_button.pack(anchor="w", padx=4)

        self._draw_static()
        self.refresh()

    def _draw_static(self):
        for from_id, to_id in _EDGES:
            self._draw_edge(self._stage_by_id[from_id], self._stage_by_id[to_id])
        for stage in _STAGES:
            self._draw_box(stage)

    def _draw_edge(self, src: WizardStage, dst: WizardStage):
        x0, y0 = _box_center(src)
        x1, y1 = _box_center(dst)
        if dst.col == src.col:
            y0 += _BOX_H // 2
            y1 -= _BOX_H // 2
        self.canvas.create_line(x0, y0, x1, y1, fill="#9e9e9e", width=2, arrow="last", smooth=True)

    def _draw_box(self, stage: WizardStage):
        cx, cy = _box_center(stage)
        x0, y0 = cx - _BOX_W // 2, cy - _BOX_H // 2
        x1, y1 = cx + _BOX_W // 2, cy + _BOX_H // 2
        box_id = self.canvas.create_rectangle(x0, y0, x1, y1, fill=_COLOR_TODO, outline="#212121", width=1)
        label_id = self.canvas.create_text(cx, cy, text=stage.title, fill="white", width=_BOX_W - 12, justify="center")
        self._box_ids[stage.stage_id] = box_id
        self._label_ids[stage.stage_id] = label_id
        for item_id in (box_id, label_id):
            self.canvas.tag_bind(item_id, "<Button-1>", lambda _e, sid=stage.stage_id: self._select(sid))

    def refresh(self):
        for stage in _STAGES:
            has_data, detail, gap_note = stage.status_fn(self.app)
            if stage.stage_id == "export":
                color = _COLOR_INFO
            elif has_data:
                color = _COLOR_DONE
            elif gap_note:
                color = _COLOR_GAP
            else:
                color = _COLOR_TODO
            self.canvas.itemconfigure(self._box_ids[stage.stage_id], fill=color)
        if self._selected:
            self._select(self._selected)

    def _select(self, stage_id: str):
        self._selected = stage_id
        stage = self._stage_by_id[stage_id]
        has_data, detail, gap_note = stage.status_fn(self.app)
        self.detail_title.configure(text=stage.title)
        self.detail_status.configure(text=detail)
        self.detail_description.configure(text=stage.description)
        self.detail_memristor.configure(text=stage.memristor_note)
        self.detail_gap.configure(text=gap_note or "")
        if stage.goto_path is None:
            self.goto_button.configure(state="disabled")
        else:
            self.goto_button.configure(state="normal")

    def _on_goto(self):
        if self._selected is None:
            return
        stage = self._stage_by_id[self._selected]
        if stage.goto_path is not None:
            self.app.goto(*stage.goto_path)

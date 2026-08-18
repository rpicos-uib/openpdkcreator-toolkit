"""Aggregates a real cell's views across ``libs.ref/<family>/{lef,cdl,
spice,verilog,lib}/`` -- the real, cross-tool "same cell, different
real file, different tool" picture ``gui/cell_hub_view.py`` surfaces.

Real, confirmed structural fact worth handling deliberately (not
assumed): IHP's own families use *two different* real file
organizations for the same view kind. ``sg13g2_io``/``sg13g2_stdcell``
pack every cell for a view into one combined file (one real ``.cdl``
with all 84 real `.SUBCKT` blocks); ``sg13g2_sram`` instead ships one
real file per hard macro (28 real ``.cdl`` files, one `.SUBCKT` each --
confirmed by directly counting real files, not assumed from either
family alone). This module scans *every* real file under a view
directory and lets the per-format parser (``netlist``/``verilog``/
``liberty``/``lef``) find however many cells live inside each one, so
both real organizations work without special-casing either.

GDS views: ``gds_present`` (does a real ``.gds`` exist for this cell)
still works even where KLayout isn't installed; when it is, ``gds_cell``
carries real structural content (bounding box, per-layer shape count)
via ``pdklib/gds.py`` (KLayout's own real Python API, lazily imported) --
``sg13g2_pr`` is GDS-only (confirmed: zero real files under any other
real view directory) -- its cell index is genuinely empty, not a bug.

User models: a cell's own ``user_models`` list holds any user-authored
Verilog/Verilog-A model connected to it (by name match or explicit
link) -- see ``pdklib/user_models.py``'s own docstring. Unlike every real
view above, a user model can introduce a wholly new cell name this
family's own real files never had.

**xschem/Qucs-S views** (``xschem_symbol``/``xschem_schematic``/
``qucs_symbol``/``qucs_component``): matched by real cell **name**
(file stem), not by family/directory name -- confirmed real, not
assumed: ``libs.tech/xschem/`` uses different real subdirectory names
than ``libs.ref/`` does for the very same family (``sg13g2_stdcells``,
plural, vs. ``sg13g2_stdcell``; no ``_io``/``_sram`` xschem directory
at all), and ``libs.tech/qucs-s/symbols/`` has no per-family split
whatsoever, just one real, flat directory. So every real xschem/Qucs-S
file across the *entire* real PDK is name-matched against cells this
*family*'s own real LEF/CDL/SPICE/Verilog/Liberty/GDS views already
established -- unlike those views (and unlike ``user_models``), a
xschem/Qucs-S file with no matching real cell name here never
introduces a brand-new entry; a wholly new, project-authored cell
(symbol/schematic only, no real libs.ref view at all) is
``pdklib/library_index.py``'s own job, not this function's.

**Registered (Library Manager) entries** work the same way as xschem/
Qucs-S -- ``registered_views`` (view kind -> path) only ever enriches a
cell already known from a real view above, matching the same "a
wholly new cell belongs to ``library_index.py``, not here" boundary.
The caller (``gui/cell_hub_view.py``) computes which entries are
registered (via ``pdklib/library_index.py``'s own ``merged_entries``,
``source == "registered"``) and passes them in as a plain
``dict[str, dict[str, Path]]`` -- this module stays decoupled from
``library_index.py``'s own dataclasses, the same reason
``user_models_by_cell`` is pre-computed by its own caller too.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import gds as gds_mod
from . import lef as lef_mod
from . import liberty as liberty_mod
from . import netlist as netlist_mod
from . import qucs_sym as qucs_sym_mod
from . import user_models as user_models_mod
from . import verilog as verilog_mod
from . import xschem as xschem_mod
from . import xschem_sch as xschem_sch_mod


@dataclass
class CellViews:
    name: str
    family: str
    lef_macro: lef_mod.LefMacro | None = None
    lef_source: Path | None = None
    cdl_cell: netlist_mod.NetlistCell | None = None
    cdl_source: Path | None = None
    spice_cell: netlist_mod.NetlistCell | None = None
    spice_source: Path | None = None
    verilog_module: verilog_mod.VerilogModule | None = None
    verilog_source: Path | None = None
    liberty_entries: list[tuple[liberty_mod.LibertyCell, Path]] = field(default_factory=list)
    gds_present: bool = False
    gds_cell: gds_mod.GdsCell | None = None
    gds_source: Path | None = None
    user_models: list[tuple[verilog_mod.VerilogModule, Path, str]] = field(default_factory=list)
    """This real cell's own user-authored Verilog/Verilog-A models
    (module, real source path, "verilog"/"veriloga") -- via a name
    match or an explicit ``UserModelLink``, see ``pdklib/user_models.py``
    own docstring."""
    xschem_symbol_source: Path | None = None
    xschem_schematic_source: Path | None = None
    qucs_symbol_source: Path | None = None
    qucs_component_source: Path | None = None
    registered_views: dict[str, Path] = field(default_factory=dict)
    """This cell's own project-authored (Library Manager-registered,
    ``source == "registered"`` in ``pdklib/library_index.py``) views, view
    kind -> real file path -- e.g. ``{"lef": Path(...)}`` for a
    hand-authored LEF registered via **Add...** with no real
    ``libs.ref/`` counterpart. Only set for a view kind this cell has
    no *real* source for already (real always wins, matching
    ``library_index.py``'s own merge rule) -- see this module's own
    docstring for why a wholly new cell can't be introduced this way."""


def discover_families(pdk_root: Path) -> list[str]:
    libs_ref = pdk_root / "libs.ref"
    if not libs_ref.is_dir():
        return []
    return sorted(p.name for p in libs_ref.iterdir() if p.is_dir())


def build_cell_index(
    pdk_root: Path, family: str,
    get_lef: Callable[[Path], lef_mod.LefFile] | None = None,
    get_netlist_cells: Callable[[Path], list[netlist_mod.NetlistCell]] | None = None,
    get_verilog_modules: Callable[[Path], list[verilog_mod.VerilogModule]] | None = None,
    get_liberty_cells: Callable[[Path], list[liberty_mod.LibertyCell]] | None = None,
    user_models_by_cell: dict[str, list[tuple[verilog_mod.VerilogModule, Path, str]]] | None = None,
    registered_by_cell: dict[str, dict[str, Path]] | None = None,
) -> dict[str, CellViews]:
    """*get_lef*/*get_netlist_cells*/*get_verilog_modules*/
    *get_liberty_cells*: optional parse-with-caching hooks (the GUI
    passes ``App.get_parsed_lef``/``get_parsed_netlist``/
    ``get_parsed_verilog``/``get_parsed_liberty``, so the very same
    ``LefMacro``/``NetlistCell``/``VerilogModule``/``LibertyCell``
    objects -- and any in-memory edits on them -- are shared with the
    LEF tab and across a family switch, rather than re-parsed fresh
    here on every call, which would otherwise silently discard edits
    the moment the user switched families and back -- the exact same
    real bug already found and fixed for LEF pins. The CLI and tests
    leave these ``None`` and get a plain, uncached parse each call.

    *user_models_by_cell*: pre-computed via
    ``pdklib/user_models.py``'s own ``group_by_cell`` (this module stays
    decoupled from link persistence/path-relative bookkeeping). A cell
    name with no real view of its own here (a wholly new, user-defined
    cell not yet in the real PDK) still gets a real ``CellViews``
    entry -- ``get_or_create`` runs for user models the same as every
    real view above.

    *registered_by_cell*: cell name -> view kind -> real path, for this
    family's own ``library_index.yaml`` entries with
    ``source == "registered"`` (pre-computed by the caller -- see this
    module's own docstring). Enriches an already-known cell's
    ``registered_views`` only, the same real "no brand-new cell this
    way" boundary xschem/Qucs-S already has."""

    parse_lef = get_lef or lef_mod.parse_lef_file
    parse_netlist = get_netlist_cells or netlist_mod.find_cells
    parse_verilog = get_verilog_modules or verilog_mod.find_modules
    parse_liberty = get_liberty_cells or liberty_mod.find_cells
    family_dir = pdk_root / "libs.ref" / family
    index: dict[str, CellViews] = {}

    def get_or_create(name: str) -> CellViews:
        if name not in index:
            index[name] = CellViews(name=name, family=family)
        return index[name]

    lef_dir = family_dir / "lef"
    if lef_dir.is_dir():
        for lef_path in sorted(lef_dir.glob("*.lef")):
            for macro in parse_lef(lef_path).macros:
                cv = get_or_create(macro.name)
                cv.lef_macro = macro
                cv.lef_source = lef_path

    cdl_dir = family_dir / "cdl"
    if cdl_dir.is_dir():
        for cdl_path in sorted(cdl_dir.glob("*.cdl")):
            for cell in parse_netlist(cdl_path):
                cv = get_or_create(cell.name)
                cv.cdl_cell = cell
                cv.cdl_source = cdl_path

    spice_dir = family_dir / "spice"
    if spice_dir.is_dir():
        for spice_path in sorted(spice_dir.glob("*.spice")):
            for cell in parse_netlist(spice_path):
                cv = get_or_create(cell.name)
                cv.spice_cell = cell
                cv.spice_source = spice_path

    verilog_dir = family_dir / "verilog"
    if verilog_dir.is_dir():
        for v_path in sorted(verilog_dir.glob("*.v")):
            for module in parse_verilog(v_path):
                cv = get_or_create(module.name)
                cv.verilog_module = module
                cv.verilog_source = v_path

    lib_dir = family_dir / "lib"
    if lib_dir.is_dir():
        for lib_path in sorted(lib_dir.glob("*.lib")):
            for cell in parse_liberty(lib_path):
                cv = get_or_create(cell.name)
                cv.liberty_entries.append((cell, lib_path))

    gds_dir = family_dir / "gds"
    if gds_dir.is_dir():
        gds_paths = sorted(gds_dir.glob("*.gds"))
        gds_names = {p.stem for p in gds_paths}
        if len(gds_names) == 1 and next(iter(gds_names)) not in index:
            # One real combined file (e.g. sg13g2_stdcell.gds): every
            # real cell discovered above has a real GDS inside it,
            # just not split out.
            gds_path = gds_paths[0]
            real_cells = _try_find_gds_cells(gds_path)
            for cv in index.values():
                cv.gds_present = True
                if real_cells is not None and cv.name in real_cells:
                    cv.gds_cell = real_cells[cv.name]
                    cv.gds_source = gds_path
        else:
            # Per-macro convention (e.g. sg13g2_sram): one real file
            # per cell, matched by name.
            for gds_path in gds_paths:
                cv = index.get(gds_path.stem)
                if cv is None:
                    continue
                cv.gds_present = True
                real_cells = _try_find_gds_cells(gds_path)
                if real_cells is not None and cv.name in real_cells:
                    cv.gds_cell = real_cells[cv.name]
                    cv.gds_source = gds_path

    # xschem/Qucs-S: enrich only cells already known from real
    # libs.ref/ views above -- see this module's own docstring for why
    # a real xschem/Qucs-S file with no matching real cell name here
    # never introduces a brand-new entry (that's library_index.py's
    # own job, not this function's).
    if index:
        xschem_syms = {p.stem: p for p in xschem_mod.find_sym_files(pdk_root)}
        xschem_schs = {p.stem: p for p in xschem_sch_mod.find_sch_files(pdk_root)}
        qucs_syms = {p.stem: p for p in qucs_sym_mod.find_symbol_geometry_files(pdk_root)}
        qucs_comps = {p.stem: p for p in qucs_sym_mod.find_component_files(pdk_root)}
        for name, cv in index.items():
            if name in xschem_syms:
                cv.xschem_symbol_source = xschem_syms[name]
            if name in xschem_schs:
                cv.xschem_schematic_source = xschem_schs[name]
            if name in qucs_syms:
                cv.qucs_symbol_source = qucs_syms[name]
            if name in qucs_comps:
                cv.qucs_component_source = qucs_comps[name]

    if user_models_by_cell:
        for cell_name, models in user_models_by_cell.items():
            cv = get_or_create(cell_name)
            cv.user_models.extend(models)

    if registered_by_cell:
        for cell_name, views in registered_by_cell.items():
            cv = index.get(cell_name)
            if cv is None:
                continue  # a wholly new cell: library_index.py's own job, not this one's -- see docstring.
            cv.registered_views.update(views)

    return index


def _try_find_gds_cells(gds_path: Path) -> dict[str, gds_mod.GdsCell] | None:
    """``None`` (not an empty dict) when ``klayout.db`` simply isn't
    importable here -- distinct from a real file with genuinely no
    matching structures, so callers don't mistake 'can't check' for
    'checked, and there's nothing.'"""

    try:
        return gds_mod.find_cells(gds_path)
    except gds_mod.KLayoutUnavailable:
        return None

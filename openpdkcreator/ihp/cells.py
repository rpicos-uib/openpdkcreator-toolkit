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

GDS views are inventoried (a flag: does a real ``.gds`` exist for this
family) but never content-parsed -- no real GDS parser exists yet, see
README's Future Work. ``sg13g2_pr`` is GDS-only (confirmed: zero real
files under any other real view directory) -- its cell index is
genuinely empty, not a bug.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import lef as lef_mod
from . import liberty as liberty_mod
from . import netlist as netlist_mod
from . import verilog as verilog_mod


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


def discover_families(pdk_root: Path) -> list[str]:
    libs_ref = pdk_root / "libs.ref"
    if not libs_ref.is_dir():
        return []
    return sorted(p.name for p in libs_ref.iterdir() if p.is_dir())


def build_cell_index(
    pdk_root: Path, family: str,
    get_lef: Callable[[Path], lef_mod.LefFile] | None = None,
) -> dict[str, CellViews]:
    """*get_lef*: an optional parse-with-caching hook (the GUI passes
    ``App.get_parsed_lef``, so the very same ``LefMacro`` objects --
    and any in-memory pin edits on them -- are shared with the LEF tab
    rather than re-parsed fresh here; the CLI and tests leave this
    ``None`` and get a plain, uncached parse each call)."""

    parse_lef = get_lef or lef_mod.parse_lef_file
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
            for cell in netlist_mod.find_cells(cdl_path):
                cv = get_or_create(cell.name)
                cv.cdl_cell = cell
                cv.cdl_source = cdl_path

    spice_dir = family_dir / "spice"
    if spice_dir.is_dir():
        for spice_path in sorted(spice_dir.glob("*.spice")):
            for cell in netlist_mod.find_cells(spice_path):
                cv = get_or_create(cell.name)
                cv.spice_cell = cell
                cv.spice_source = spice_path

    verilog_dir = family_dir / "verilog"
    if verilog_dir.is_dir():
        for v_path in sorted(verilog_dir.glob("*.v")):
            for module in verilog_mod.find_modules(v_path):
                cv = get_or_create(module.name)
                cv.verilog_module = module
                cv.verilog_source = v_path

    lib_dir = family_dir / "lib"
    if lib_dir.is_dir():
        for lib_path in sorted(lib_dir.glob("*.lib")):
            for cell in liberty_mod.find_cells(lib_path):
                cv = get_or_create(cell.name)
                cv.liberty_entries.append((cell, lib_path))

    gds_dir = family_dir / "gds"
    if gds_dir.is_dir():
        gds_names = {p.stem for p in gds_dir.glob("*.gds")}
        if len(gds_names) == 1 and next(iter(gds_names)) not in index:
            # One real combined file (e.g. sg13g2_stdcell.gds): every
            # real cell discovered above has a real GDS inside it,
            # just not split out.
            for cv in index.values():
                cv.gds_present = True
        else:
            # Per-macro convention (e.g. sg13g2_sram): one real file
            # per cell, matched by name.
            for cv in index.values():
                cv.gds_present = cv.name in gds_names

    return index

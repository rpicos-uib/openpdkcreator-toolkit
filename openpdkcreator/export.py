"""Real, open_pdks-format export -- the first concrete piece of native
write-back serialization (see README's own Future Work): takes this
session's in-memory, possibly-edited real structures and writes real,
valid, patched files to a new ``export/`` tree, mirroring each file's
own real relative path under its ``pdk_root`` -- never touching the
real, downloaded ``data/`` copy.

Covers every currently-editable domain: LEF pins (``ihp/lef_writer.py``'s
own docstring explains exactly how the patching preserves everything
this project's LEF model doesn't capture), DRC Rules
(``ihp/drc_writer.py``'s own docstring explains the real
``.drc``-script-vs-JSON-config split), Magic Types
(``ihp/magic_tech_writer.py``), CDL/SPICE/Verilog ports
(``ihp/netlist_writer.py``/``ihp/verilog_writer.py``), Liberty
pin/timing-arc data (``ihp/liberty_writer.py``'s own docstring explains
the per-field diffing discipline; the real lookup-table sub-groups
stay untouched, unmodeled), and Layers (``ihp/layers_writer.py`` --
only ``name``/``gds_layer``/``gds_datatype``/``frame_color``/
``fill_color`` have any real ``.lyp`` counterpart; every other
editable ``Layer`` field is this project's own metadata, saved via
``project_io.py`` instead). Every other real, non-editable domain
(GDS, Magic Tech's other domains, ...) has no write-back because
there's no editor for it either -- see README's own Future Work.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .ihp import drc as drc_mod
from .ihp import drc_writer
from .ihp import layers as layers_mod
from .ihp import layers_writer
from .ihp import lef as lef_mod
from .ihp import lef_writer
from .ihp import liberty as liberty_mod
from .ihp import liberty_writer
from .ihp import magic_tech as magic_tech_mod
from .ihp import magic_tech_writer
from .ihp import netlist as netlist_mod
from .ihp import netlist_writer
from .ihp import verilog as verilog_mod
from .ihp import verilog_writer
from .models import DesignRule, Layer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = PROJECT_ROOT / "export"


def export_path_for(pdk_root: Path, source_path: Path, dest_root: Path | None = None) -> Path:
    """*dest_root* defaults to this project's own ``EXPORT_ROOT /
    pdk_root.name`` (the GUI/CLI session-export destination); passed
    explicitly by ``export_full_pdk`` to target an arbitrary directory
    instead (e.g. a smoking-gun round-trip test's own scratch dir)."""

    dest_root = dest_root if dest_root is not None else (EXPORT_ROOT / pdk_root.name)
    return dest_root / source_path.relative_to(pdk_root)


def export_lef_files(
    pdk_root: Path, lef_cache: dict[Path, lef_mod.LefFile], dest_root: Path | None = None,
) -> list[Path]:
    """Every real ``.lef`` file in *lef_cache* (the GUI passes only
    files parsed this session; ``export_full_pdk``/``main.py
    export-lef`` pass every real file, freshly parsed). Returns the
    real export paths written."""

    written = []
    for source_path, parsed in lef_cache.items():
        export_path = export_path_for(pdk_root, source_path, dest_root)
        lef_writer.export_lef_file(parsed, export_path)
        written.append(export_path)
    return written


def export_drc_rules(
    pdk_root: Path, drc_root: Path, design_rules: list[DesignRule], dest_root: Path | None = None,
) -> tuple[list[Path], list[str]]:
    """Every real ``.drc`` file with at least one real, resolvable
    rule (grouped by real source file, all real edits in a file
    applied in one pass) plus the one real JSON config file (if any
    rule's value needs patching there). A rule with no real,
    resolvable provenance (hand-authored via New Rule) can't be
    written back -- returned by ``rule_id`` in the second list, not
    silently dropped."""

    by_relpath: dict[str, list[DesignRule]] = {}
    skipped: list[str] = []
    for rule in design_rules:
        parsed = drc_writer.parse_provenance(rule.source_provenance)
        if parsed is None:
            skipped.append(rule.rule_id)
            continue
        relpath, _check_line, _output_line = parsed
        by_relpath.setdefault(relpath, []).append(rule)

    written: list[Path] = []
    all_value_edits: dict[str, float] = {}
    for relpath, rules in by_relpath.items():
        source_path = pdk_root / relpath
        text, value_edits = drc_writer.render_drc_file(source_path, rules)
        all_value_edits.update(value_edits)
        export_path = export_path_for(pdk_root, source_path, dest_root)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(text, encoding="utf-8")
        written.append(export_path)

    json_path = drc_mod.find_json_config_path(drc_root)
    if all_value_edits and json_path is not None:
        json_text = drc_writer.render_json_config(json_path, all_value_edits)
        export_json_path = export_path_for(pdk_root, json_path, dest_root)
        export_json_path.parent.mkdir(parents=True, exist_ok=True)
        export_json_path.write_text(json_text, encoding="utf-8")
        written.append(export_json_path)

    return written, skipped


def export_magic_types(
    pdk_root: Path, technologies: dict[str, magic_tech_mod.MagicTechnology], dest_root: Path | None = None,
) -> list[Path]:
    """Every real technology in *technologies* (the GUI passes every
    technology currently loaded; ``export_full_pdk``/``main.py
    export-magic-types`` pass every real technology, freshly parsed).
    Returns the real export paths written."""

    written = []
    for tech in technologies.values():
        export_path = export_path_for(pdk_root, tech.source_path, dest_root)
        magic_tech_writer.export_tech_file(tech, export_path)
        written.append(export_path)
    return written


def export_netlist_files(
    pdk_root: Path, netlist_cache: dict[Path, list[netlist_mod.NetlistCell]], dest_root: Path | None = None,
) -> list[Path]:
    """Every real ``.cdl``/``.spice`` file in *netlist_cache* (the GUI
    passes only files parsed this session via ``App.get_parsed_netlist``;
    ``export_full_pdk``/``main.py export-netlist`` pass every real
    file, freshly parsed). Returns the real export paths written."""

    written = []
    for source_path, cells in netlist_cache.items():
        export_path = export_path_for(pdk_root, source_path, dest_root)
        netlist_writer.export_netlist_file(cells, source_path, export_path)
        written.append(export_path)
    return written


def export_verilog_files(
    pdk_root: Path, verilog_cache: dict[Path, list[verilog_mod.VerilogModule]], dest_root: Path | None = None,
) -> list[Path]:
    """Every real ``.v`` file in *verilog_cache* (the GUI passes only
    files parsed this session via ``App.get_parsed_verilog``;
    ``export_full_pdk``/``main.py export-verilog`` pass every real
    file, freshly parsed). Returns the real export paths written."""

    written = []
    for source_path, modules in verilog_cache.items():
        export_path = export_path_for(pdk_root, source_path, dest_root)
        verilog_writer.export_verilog_file(modules, source_path, export_path)
        written.append(export_path)
    return written


def export_layers(
    pdk_root: Path, lyp_path: Path, layers: list[Layer], dest_root: Path | None = None,
) -> Path:
    """The one real ``.lyp`` file this project ever has loaded at once
    (unlike every other domain here, Layers has no per-file cache --
    ``App.lyp_path``/``App.project.layers`` are already singular).
    Returns the real export path written."""

    export_path = export_path_for(pdk_root, lyp_path, dest_root)
    layers_writer.export_lyp_file(layers, lyp_path, export_path)
    return export_path


def export_liberty_files(
    pdk_root: Path, liberty_cache: dict[Path, list[liberty_mod.LibertyCell]], dest_root: Path | None = None,
) -> list[Path]:
    """Every real ``.lib`` file in *liberty_cache* (the GUI passes only
    files parsed this session via ``App.get_parsed_liberty``;
    ``export_full_pdk``/``main.py export-liberty`` pass every real
    file, freshly parsed). Returns the real export paths written."""

    written = []
    for source_path, cells in liberty_cache.items():
        export_path = export_path_for(pdk_root, source_path, dest_root)
        liberty_writer.export_lib_file(cells, source_path, export_path)
        written.append(export_path)
    return written


def export_full_pdk(pdk_root: Path, dest_root: Path) -> None:
    """A complete, real, standalone open_pdks-format PDK tree at
    *dest_root* -- every real file under *pdk_root* copied verbatim
    (``shutil.copytree``, so ``dest_root`` starts as an exact, complete
    clone -- Liberty/GDS/docs/qa/every other real file this project has
    no editor for included, not just the small subset the other
    ``export_*`` functions above touch), then every real LEF/DRC/
    Magic-Types/CDL/SPICE/Verilog file is re-rendered on top through
    its own real writer, freshly parsed straight from *pdk_root* with
    no GUI session or edits involved -- a real no-op patch, but one
    that exercises every real writer against every real file in the
    whole PDK, not a hand-picked sample. Refuses to run if *dest_root*
    already exists (never silently overwrites)."""

    if dest_root.exists():
        raise FileExistsError(f"{dest_root} already exists -- remove it first (this never overwrites blindly).")
    # symlinks=True: a real, confirmed bug found via the smoking-gun
    # round-trip test -- shutil.copytree's own default (symlinks=False)
    # *dereferences* a real symlink (IHP's own
    # libs.tech/ngspice/install.py -> ../xschem/install.py) into a
    # plain file copy of its target, silently losing the real symlink
    # structure. A plain content diff (e.g. 'diff -rq' without
    # --no-dereference) doesn't catch this -- it compares resolved
    # content and reports no difference -- so the bug only surfaced via
    # a real, structural comparison (--no-dereference) across the full
    # exported tree.
    shutil.copytree(pdk_root, dest_root, symlinks=True)

    lef_cache = {path: lef_mod.parse_lef_file(path) for path in lef_mod.find_lef_files(pdk_root)}
    export_lef_files(pdk_root, lef_cache, dest_root)

    drc_root = drc_mod.find_drc_root(pdk_root)
    if drc_root is not None:
        rules, _skipped_extraction = drc_mod.extract_design_rules(pdk_root, drc_root)
        export_drc_rules(pdk_root, drc_root, rules, dest_root)

    technologies: dict[str, magic_tech_mod.MagicTechnology] = {}
    for path in magic_tech_mod.find_tech_files(pdk_root):
        tech = magic_tech_mod.parse_tech_file(path)
        if tech.name:
            technologies[tech.name] = tech
    export_magic_types(pdk_root, technologies, dest_root)

    netlist_cache = {
        path: netlist_mod.find_cells(path)
        for pattern in ("libs.ref/*/cdl/*.cdl", "libs.ref/*/spice/*.spice")
        for path in pdk_root.glob(pattern)
    }
    export_netlist_files(pdk_root, netlist_cache, dest_root)

    verilog_cache = {path: verilog_mod.find_modules(path) for path in pdk_root.glob("libs.ref/*/verilog/*.v")}
    export_verilog_files(pdk_root, verilog_cache, dest_root)

    liberty_cache = {path: liberty_mod.find_cells(path) for path in pdk_root.glob("libs.ref/*/lib/*.lib")}
    export_liberty_files(pdk_root, liberty_cache, dest_root)

    lyp_path = layers_mod.find_lyp(pdk_root)
    if lyp_path is not None:
        export_layers(pdk_root, lyp_path, layers_mod.import_layers(pdk_root, lyp_path), dest_root)

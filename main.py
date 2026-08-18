#!/usr/bin/env python3
"""openPDKcreator: read real PDK files (starting with IHP's SG13G2) and
represent the information, organized by tool -- reusing OpenPDKCreator's
own Layers interface for displaying/editing real, parsed layer data.

A real, deliberately-scoped first increment (see README.md's Future
Work): an honest per-tool file inventory, real KLayout .lyp -> Layer
parsing, a real (if partial) Magic .tech parser -- its cleanly tabular
sections (tech/version/planes/types/contact/aliases/styles) in full,
plus the one reliable pattern extractable from the much harder
cifoutput geometry DSL (a real Magic-type-name -> GDS-layer/datatype
mapping), cross-referenced against the KLayout .lyp data above -- and a
real LEF parser (tech-LEF layers plus real macro/cell footprints:
class/size/site/symmetry, PINs with direction/use/port layers+rect
counts, OBS layers), and a real KLayout DRC-deck rule extractor (the
same, already-proven-elsewhere regex pattern, pointed at the full,
real, downloaded deck: a line assigning a real
width()/space()/sep() result -- or a real two-layer .enclosed() result
-- to a variable, cross-referenced against a real JSON values file,
feeding a same-variable .output() call).
Also aggregates one real cell's views across ``libs.ref/<family>/*/``
(LEF/CDL/SPICE/Verilog -- real per-port structure, direction included
(a real CDL ``*.PININFO`` comment or real Verilog ``input``/
``output``/``inout`` declarations), not just a name list; Liberty --
real pin/timing-arc extraction (direction/capacitance/function per
pin, related_pin/timing_type/timing_sense/when per timing arc), the
real lookup-table sub-groups deliberately left unparsed; GDS -- real
bounding box + per-layer shape count via KLayout's own real Python
API, ``klayout.db``, lazily imported so every other command here still
runs without it installed). Magic's own ``compose``/``connect``
sections are fully parsed, and one real pattern each is pulled out of
its harder ``drc`` (``width``/``spacing``/``maxwidth``, 192 real checks),
``extract`` (``resist``/``planeorder``, 44 real entries), and
``cifinput`` (``ignore``/standalone ``calma`` hints, 156 real entries
combined) mini-rule-languages -- see ``pdklib/magic_tech.py``'s own
docstring for exact real coverage and what's still not attempted
(``device``, the rest of ``drc``/``extract``, ``cifinput``'s own real
geometry-boolean recipes). LEF's own real
``VIA``/``ViaRULE`` via-stack geometry is also parsed (real layer/rect
geometry for a fixed via, real enclosure/spacing/resistance for a
generated one -- ``pdklib/lef.py``); no attempt at Liberty's own real
lookup-table content. Real,
open_pdks-format write-back now exists for every currently
structured-editable domain -- LEF pins (``export-lef``/
``pdklib/lef_writer.py``), DRC Rules (``export-drc``/``pdklib/drc_writer.py``
-- a rule's ``rule_id``/``description`` patched into its real ``.drc``
script, its ``value`` into the one real JSON config file it actually
lives in), Magic Types (``export-magic-types``/
``pdklib/magic_tech_writer.py`` -- a type's own real one-line entry in
its real ``.tech`` file), CDL/SPICE/Verilog ports
(``export-netlist``/``export-verilog``/``pdklib/netlist_writer.py``/
``pdklib/verilog_writer.py``), Liberty pin/timing-arc data
(``export-liberty``/``pdklib/liberty_writer.py``), and Layers
(``export-layers``/``pdklib/layers_writer.py``) -- all surgical,
position-targeted patching into a new ``export/`` tree, never touching
``data/``, and independently re-verified faithful across the *entire*
real PDK via ``export-full``'s own smoking-gun round-trip test. The
much larger end goal -- editing/creating/generating arbitrary PDK file
types, not just reading/displaying them -- is explicit, tracked future
work, still only partially attempted here.

    python3 main.py fetch                 # download the real IHP PDK (once)
    python3 main.py inventory             # per-tool file census, printed
    python3 main.py magic-tech            # real Magic .tech parse + KLayout cross-reference
    python3 main.py lef                   # real LEF parse summary (tech layers + macros)
    python3 main.py drc                   # real KLayout DRC-deck rule extraction summary
    python3 main.py cells                 # real per-cell view aggregation, one family at a time
    python3 main.py gds                   # real GDS structural summary (needs klayout.db)
    python3 main.py export-lef            # real LEF write-back verification (no-edit == byte-identical)
    python3 main.py export-drc            # real DRC Rule write-back verification
    python3 main.py export-magic-types    # real Magic Types write-back verification
    python3 main.py export-netlist        # real CDL/SPICE port write-back verification
    python3 main.py export-verilog        # real Verilog port write-back verification
    python3 main.py export-liberty        # real Liberty pin/timing write-back verification
    python3 main.py export-layers         # real .lyp write-back verification
    python3 main.py export-full --dest D  # a complete, standalone PDK tree (round-trip fidelity testing)
    python3 main.py gui                   # Overview, Technology, Cells, Settings tabs
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from openpdkcreator import export as export_mod
from openpdkcreator import project_io
from openpdkcreator.pdklib import cells as cells_mod
from openpdkcreator.pdklib import drc as drc_mod
from openpdkcreator.pdklib import fetch as fetch_mod
from openpdkcreator.pdklib import gds as gds_mod
from openpdkcreator.pdklib import inventory as inventory_mod
from openpdkcreator.pdklib import layers as layers_mod
from openpdkcreator.pdklib import lef as lef_mod
from openpdkcreator.pdklib import liberty as liberty_mod
from openpdkcreator.pdklib import magic_tech as magic_tech_mod
from openpdkcreator.pdklib import netlist as netlist_mod
from openpdkcreator.pdklib import qucs_sym as qucs_mod
from openpdkcreator.pdklib import reconcile as reconcile_mod
from openpdkcreator.pdklib import shell_env as shell_env_mod
from openpdkcreator.pdklib import skeleton as skeleton_mod
from openpdkcreator.pdklib import spice_models as spice_models_mod
from openpdkcreator.pdklib import user_models as user_models_mod
from openpdkcreator.pdklib import verilog as verilog_mod
from openpdkcreator.pdklib import xschem as xschem_mod
from openpdkcreator.pdklib import xschem_sch as xschem_sch_mod

DEFAULT_PDK_ROOT = Path(__file__).resolve().parent / "data" / "ihp-sg13g2" / "ihp-sg13g2"

# Matches gui/environment_view.py's own SHELL_ENV_DIRNAME/SCRIPT_NAME --
# kept as separate literals rather than importing that module, so
# every other CLI command here still runs without pulling in tkinter.
SHELL_ENV_DIRNAME = "shell_env"
SHELL_ENV_SCRIPT_NAME = "pdk_env.sh"


def _slugify_name(name: str) -> str:
    """A plain, real filename stem from a human-typed project name --
    lowercased, any run of non-alphanumeric characters collapsed to one
    underscore -- used only for ``wizard --name``'s own Layers/Magic
    Tech/LEF skeleton file names (``build_new_pdk_skeleton``'s own
    *name* argument). The project name saved via ``project_io.
    save_state`` keeps whatever the user actually typed, unslugified --
    the same real, deliberate distinction ``project_io.py``'s own
    docstring already draws between a PDK's immutable directory name
    and its separate, freely-editable display label."""

    slug = re.sub(r"[^A-Za-z0-9]+", "_", name.strip()).strip("_").lower()
    return slug or "pdk"


def cmd_fetch(dest: Path) -> int:
    fetch_mod.fetch(dest)
    return 0


def cmd_inventory(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2
    inventory_mod.print_inventory(inventory_mod.scan_all(pdk_root))
    return 0


def cmd_magic_tech(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    tech_files = magic_tech_mod.find_tech_files(pdk_root)
    if not tech_files:
        print(f"No .tech files found under {pdk_root}/libs.tech/magic/", file=sys.stderr)
        return 2

    main_tech = None
    for path in tech_files:
        tech = magic_tech_mod.parse_tech_file(path)
        print(f"=== {path.name} ===")
        print(f"  name: {tech.name or '(fragment, no own tech/version header)'}  format: {tech.format}")
        if tech.version:
            print(f"  version {tech.version} -- {tech.description}  (requires {tech.requires})")
        if tech.included_files:
            print(f"  includes: {', '.join(tech.included_files)}")
        print(
            f"  planes:{len(tech.planes)}  types:{len(tech.types)}  "
            f"contacts:{len(tech.contacts)}  aliases:{len(tech.aliases)}  "
            f"styles:{len(tech.styles)}  cif_layers:{len(tech.cif_layers)}  "
            f"compose:{len(tech.compose)}  connect:{len(tech.connect)}"
        )
        if tech.cifinput_ignored_layers or tech.cifinput_layer_hints or tech.cifinput_recipes:
            print(
                f"  cifinput_ignored:{len(tech.cifinput_ignored_layers)}  "
                f"cifinput_layer_hints:{len(tech.cifinput_layer_hints)}  "
                f"cifinput_recipes:{len(tech.cifinput_recipes)}"
            )
        print(
            f"  drc_checks:{len(tech.drc_checks)}  drc_angle_checks:{len(tech.drc_angle_checks)} "
            f"({len(tech.drc_skipped)} real line(s) not matched)  "
            f"extract_resist:{len(tech.extract_resist)}  extract_plane_order:{len(tech.extract_plane_order)}"
        )
        if tech.extract_cap_coefficients or tech.extract_devices or tech.extract_misc:
            print(
                f"  extract_cap_coefficients:{len(tech.extract_cap_coefficients)}  "
                f"extract_devices:{len(tech.extract_devices)}  extract_misc:{len(tech.extract_misc)}"
            )
        for skipped_line in tech.drc_skipped:
            print(f"    not matched: {skipped_line}")
        if tech.unparsed_sections:
            print(f"  not parsed this pass: {', '.join(tech.unparsed_sections)}")
        print()
        if tech.included_files and main_tech is None:
            # The one file that includes others is the real, primary
            # technology -- the only one worth cross-referencing
            # against the .lyp (ihp-sg13g2-GDS.tech is a genuinely
            # separate, second technology -- see magic_tech.py's
            # own docstring).
            main_tech = tech

    if main_tech is None:
        return 0

    lyp_path = layers_mod.find_lyp(pdk_root)
    if lyp_path is None:
        return 0
    lyp_layers = layers_mod.import_layers(pdk_root, lyp_path)
    print(f"--- Cross-reference: {main_tech.source_path.name}'s cifoutput vs. {lyp_path.name} ---")
    report = reconcile_mod.reconcile(lyp_layers, main_tech)
    reconcile_mod.print_report(report)
    return 0


def cmd_lef(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    lef_files = lef_mod.find_lef_files(pdk_root)
    if not lef_files:
        print(f"No .lef files found under {pdk_root}/libs.ref/*/lef/", file=sys.stderr)
        return 2

    total_macros = 0
    total_layers = 0
    for path in lef_files:
        parsed = lef_mod.parse_lef_file(path)
        total_macros += len(parsed.macros)
        total_layers += len(parsed.layers)
        detail = []
        if parsed.layers:
            detail.append(f"{len(parsed.layers)} tech layer(s)")
        if parsed.sites:
            detail.append(f"{len(parsed.sites)} site(s)")
        if parsed.macros:
            pin_total = sum(len(m.pins) for m in parsed.macros)
            detail.append(f"{len(parsed.macros)} macro(s), {pin_total} pin(s) total")
        if parsed.vias:
            rect_total = sum(len(layer.rects) for via in parsed.vias for layer in via.layers)
            detail.append(f"{len(parsed.vias)} via def(s), {rect_total} rect(s) total")
        if parsed.via_rules:
            detail.append(f"{len(parsed.via_rules)} viarule(s)")
        print(f"{path.relative_to(pdk_root)}: {', '.join(detail) if detail else '(nothing recognized)'}")

    print(f"\n{len(lef_files)} real .lef file(s): {total_layers} tech layer(s), {total_macros} macro(s) total.")
    return 0


def cmd_ngspice(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    lib_files = spice_models_mod.find_lib_files(pdk_root)
    if not lib_files:
        print(f"No .lib files found under {pdk_root}/libs.tech/ngspice/models/", file=sys.stderr)
        return 2

    total_models = 0
    total_subckts = 0
    total_corners = 0
    for path in lib_files:
        parsed = spice_models_mod.parse_lib_file(path)
        total_models += len(parsed.models)
        total_subckts += len(parsed.subckts)
        total_corners += len(parsed.corners)
        detail = []
        if parsed.models:
            detail.append(f"{len(parsed.models)} model(s)")
        if parsed.subckts:
            detail.append(f"{len(parsed.subckts)} subckt(s)")
        if parsed.corners:
            detail.append(f"{len(parsed.corners)} corner(s)")
        print(f"{path.relative_to(pdk_root)}: {', '.join(detail) if detail else '(nothing recognized)'}")

    print(
        f"\n{len(lib_files)} real .lib file(s): {total_models} model(s), "
        f"{total_subckts} subckt(s), {total_corners} PVT-corner(s) total."
    )
    return 0


def cmd_xschem(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    sym_files = xschem_mod.find_sym_files(pdk_root)
    if not sym_files:
        print(f"No .sym files found under {pdk_root}/libs.tech/xschem/", file=sys.stderr)
        return 2

    total_pins = 0
    by_type: dict[str, int] = {}
    for path in sym_files:
        sym = xschem_mod.parse_sym_file(path)
        total_pins += len(sym.pins)
        by_type[sym.device_type] = by_type.get(sym.device_type, 0) + 1
        pin_text = ", ".join(f"{p.name}:{p.direction}" for p in sym.pins)
        print(f"{path.relative_to(pdk_root)}: type={sym.device_type or '(none)'}  pins=[{pin_text}]")

    print(f"\n{len(sym_files)} real .sym file(s): {total_pins} real pin(s) total.")
    print("By device type: " + ", ".join(f"{t or '(none)'}:{n}" for t, n in sorted(by_type.items())))
    return 0


def cmd_xschem_sch(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    sch_files = xschem_sch_mod.find_sch_files(pdk_root)
    if not sch_files:
        print(f"No .sch files found under {pdk_root}/libs.tech/xschem/", file=sys.stderr)
        return 2

    xschem_root = pdk_root / "libs.tech" / "xschem"
    total_instances = 0
    total_pins = 0
    total_wires = 0
    unresolved: set[str] = set()
    for path in sch_files:
        schematic = xschem_sch_mod.parse_sch_file(path, xschem_root=xschem_root)
        total_instances += len(schematic.instances)
        total_pins += len(schematic.pin_instances)
        total_wires += len(schematic.wires)
        unresolved.update(inst.symbol_ref for inst in schematic.instances if inst.resolved_path is None)
        pin_text = ", ".join(f"{inst.name}:{inst.pin_label}" for inst in schematic.pin_instances)
        print(
            f"{path.relative_to(pdk_root)}: instances={len(schematic.instances)} "
            f"wires={len(schematic.wires)} pins=[{pin_text}]"
        )

    print(
        f"\n{len(sch_files)} real .sch file(s): {total_instances} real component instance(s), "
        f"{total_pins} real pin instance(s), {total_wires} real wire segment(s)."
    )
    print(f"{len(unresolved)} unique real symbol reference(s) resolve outside the downloaded PDK (external to it):")
    for ref in sorted(unresolved):
        print(f"  {ref}")
    return 0


def cmd_qucs(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    component_files = qucs_mod.find_component_files(pdk_root)
    sym_files = qucs_mod.find_symbol_geometry_files(pdk_root)
    if not component_files and not sym_files:
        print(f"No Qucs-S component/symbol files found under {pdk_root}/libs.tech/qucs-s/symbols/", file=sys.stderr)
        return 2

    total_params = 0
    for path in component_files:
        component = qucs_mod.parse_component_file(path)
        total_params += len(component.parameters)
        resolved = "PDK" if component.resolved_symbol_path is not None else "external"
        print(
            f"{path.relative_to(pdk_root)}: {component.description or '(no description)'}  "
            f"model={component.spice_model}  params={len(component.parameters)}  symbol={component.symbol_file}[{resolved}]"
        )

    print(f"\n{len(component_files)} real .xml component(s): {total_params} real parameter(s) total.")

    total_ports = 0
    total_primitives = 0
    for path in sym_files:
        geometry = qucs_mod.parse_symbol_geometry(path)
        total_ports += len(geometry.ports)
        total_primitives += geometry.primitive_count
        print(f"{path.relative_to(pdk_root)}: {geometry.primitive_count} primitive(s), {len(geometry.ports)} port(s)")

    print(f"\n{len(sym_files)} real .sym symbol(s): {total_primitives} real drawing primitive(s), {total_ports} real port(s).")
    return 0


def cmd_user_models() -> int:
    """Lists every real module under ``user_models/verilog/*.v`` and
    ``user_models/veriloga/*.va``, plus which real (or wholly new,
    user-defined) cell it's linked to -- explicitly via
    ``user_models/links.yaml``, or by the same auto name-match every
    other view already uses. Ignores ``--pdk-root``: user models live
    in this project's own tree, not the downloaded PDK."""

    project_root = export_mod.PROJECT_ROOT
    models = user_models_mod.load_user_models(project_root)
    if not models:
        print(
            f"No user models found under {project_root / 'user_models'}/{{verilog,veriloga}}/ "
            f"-- see user_models/README.md."
        )
        return 0

    links = user_models_mod.load_links(project_root)
    link_by_key = {(link.file_relpath, link.module_name): link.cell_name for link in links}

    total_modules = 0
    for model_file in models:
        relpath = user_models_mod.relpath_for(project_root, model_file.path)
        for module in model_file.modules:
            total_modules += 1
            explicit = link_by_key.get((relpath, module.name))
            linked_text = explicit if explicit else f"(auto: {module.name})"
            ports_text = ", ".join(f"{p.name}:{p.direction or '?'}" for p in module.ports)
            print(f"{relpath} [{model_file.kind}] {module.name} -> {linked_text}  ports=[{ports_text}]")

    print(f"\n{len(models)} real file(s), {total_modules} real module(s), {len(links)} explicit link(s).")
    return 0


def cmd_drc(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    drc_root = drc_mod.find_drc_root(pdk_root)
    if drc_root is None:
        print(f"No DRC deck found under {pdk_root}/libs.tech/klayout/tech/drc/", file=sys.stderr)
        return 2

    rules, skipped = drc_mod.extract_design_rules(pdk_root, drc_root)
    print(f"{len(rules)} real design rule(s) extracted from {drc_root.relative_to(pdk_root)}:")
    for rule in rules:
        value = f"{rule.value} {rule.units}" if rule.value is not None else "(unresolved value)"
        print(f"  {rule.rule_id}: {rule.check_type} = {value}  [{rule.source_provenance}]")

    print(f"\n{len(skipped)} construct(s) not auto-extracted (composite/derived checks -- real, honest gaps):")
    for line in skipped:
        print(f"  {line}")
    return 0


def cmd_cells(pdk_root: Path, family: str | None) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    families = cells_mod.discover_families(pdk_root)
    if not families:
        print(f"No families found under {pdk_root}/libs.ref/", file=sys.stderr)
        return 2
    targets = [family] if family else families
    for fam in targets:
        if fam not in families:
            print(f"Unknown family {fam!r}. Real families: {', '.join(families)}", file=sys.stderr)
            return 2
        index = cells_mod.build_cell_index(pdk_root, fam)
        top_level = sum(1 for cv in index.values() if cv.lef_macro is not None)
        print(f"=== {fam}: {len(index)} real cell(s) found ({top_level} with a real LEF macro) ===")
        for name in sorted(index):
            cv = index[name]
            views = []
            if cv.lef_macro:
                views.append("lef")
            if cv.cdl_cell:
                views.append("cdl")
            if cv.spice_cell:
                views.append("spice")
            if cv.verilog_module:
                views.append("verilog")
            if cv.liberty_entries:
                views.append(f"liberty x{len(cv.liberty_entries)}")
            if cv.gds_cell is not None:
                views.append(f"gds({len(cv.gds_cell.shapes_by_layer)}L,{cv.gds_cell.total_shapes}shapes)")
            elif cv.gds_present:
                views.append("gds(presence only -- klayout unavailable)")
            print(f"  {name}: {', '.join(views) if views else '(no real view recognized)'}")
        print()
    return 0


def cmd_gds(pdk_root: Path, family: str | None) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    try:
        gds_mod.check_available()
    except gds_mod.KLayoutUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 2

    families = cells_mod.discover_families(pdk_root)
    if not families:
        print(f"No families found under {pdk_root}/libs.ref/", file=sys.stderr)
        return 2
    targets = [family] if family else families
    for fam in targets:
        if fam not in families:
            print(f"Unknown family {fam!r}. Real families: {', '.join(families)}", file=sys.stderr)
            return 2
        gds_dir = pdk_root / "libs.ref" / fam / "gds"
        if not gds_dir.is_dir():
            print(f"=== {fam}: no gds/ directory ===\n")
            continue
        total_structures = 0
        total_shapes = 0
        print(f"=== {fam} ===")
        for gds_path in sorted(gds_dir.glob("*.gds")):
            real_cells = gds_mod.find_cells(gds_path)
            shapes = sum(c.total_shapes for c in real_cells.values())
            total_structures += len(real_cells)
            total_shapes += shapes
            print(f"  {gds_path.relative_to(pdk_root)}: {len(real_cells)} real structure(s), {shapes} real shape(s)")
        print(f"  -> {total_structures} real structure(s) total, {total_shapes} real shape(s) total\n")
    return 0


def cmd_export_lef(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    lef_files = lef_mod.find_lef_files(pdk_root)
    if not lef_files:
        print(f"No .lef files found under {pdk_root}/libs.ref/*/lef/", file=sys.stderr)
        return 2

    lef_cache = {path: lef_mod.parse_lef_file(path) for path in lef_files}
    written = export_mod.export_lef_files(pdk_root, lef_cache)

    mismatches = []
    for path in lef_files:
        export_path = export_mod.export_path_for(pdk_root, path)
        original = path.read_text(encoding="utf-8", errors="replace")
        if not original.endswith("\n"):
            original += "\n"
        if export_path.read_text(encoding="utf-8", errors="replace") != original:
            mismatches.append(path)

    print(f"Exported {len(written)} real .lef file(s) to {export_mod.EXPORT_ROOT / pdk_root.name}")
    print(
        f"No real edits were made this run, so every export should be byte-identical "
        f"to its real original -- {len(lef_files) - len(mismatches)}/{len(lef_files)} are."
    )
    if mismatches:
        print("MISMATCHES (a real write-back correctness bug):", file=sys.stderr)
        for path in mismatches:
            print(f"  {path.relative_to(pdk_root)}", file=sys.stderr)
        return 1
    return 0


def cmd_export_xschem_sym(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    sym_files = xschem_mod.find_sym_files(pdk_root)
    if not sym_files:
        print(f"No .sym files found under {pdk_root}/libs.tech/xschem/", file=sys.stderr)
        return 2

    symbol_cache = {path: xschem_mod.parse_sym_file(path) for path in sym_files}
    written = export_mod.export_xschem_symbols(pdk_root, symbol_cache)

    mismatches = []
    for path in sym_files:
        export_path = export_mod.export_path_for(pdk_root, path)
        original = path.read_text(encoding="utf-8", errors="replace")
        if not original.endswith("\n"):
            original += "\n"
        if export_path.read_text(encoding="utf-8", errors="replace") != original:
            mismatches.append(path)

    print(f"Exported {len(written)} real .sym file(s) to {export_mod.EXPORT_ROOT / pdk_root.name}")
    print(
        f"No real edits were made this run, so every export should be byte-identical "
        f"to its real original -- {len(sym_files) - len(mismatches)}/{len(sym_files)} are."
    )
    if mismatches:
        print("MISMATCHES (a real write-back correctness bug):", file=sys.stderr)
        for path in mismatches:
            print(f"  {path.relative_to(pdk_root)}", file=sys.stderr)
        return 1
    return 0


def cmd_export_xschem_sch(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    sch_files = xschem_sch_mod.find_sch_files(pdk_root)
    if not sch_files:
        print(f"No .sch files found under {pdk_root}/libs.tech/xschem/", file=sys.stderr)
        return 2

    xschem_root = pdk_root / "libs.tech" / "xschem"
    schematic_cache = {path: xschem_sch_mod.parse_sch_file(path, xschem_root=xschem_root) for path in sch_files}
    written = export_mod.export_xschem_schematics(pdk_root, schematic_cache)

    mismatches = []
    for path in sch_files:
        export_path = export_mod.export_path_for(pdk_root, path)
        original = path.read_text(encoding="utf-8", errors="replace")
        if not original.endswith("\n"):
            original += "\n"
        if export_path.read_text(encoding="utf-8", errors="replace") != original:
            mismatches.append(path)

    print(f"Exported {len(written)} real .sch file(s) to {export_mod.EXPORT_ROOT / pdk_root.name}")
    print(
        f"No real edits were made this run, so every export should be byte-identical "
        f"to its real original -- {len(sch_files) - len(mismatches)}/{len(sch_files)} are."
    )
    if mismatches:
        print("MISMATCHES (a real write-back correctness bug):", file=sys.stderr)
        for path in mismatches:
            print(f"  {path.relative_to(pdk_root)}", file=sys.stderr)
        return 1
    return 0


def cmd_export_qucs_sym(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    sym_files = qucs_mod.find_symbol_geometry_files(pdk_root)
    if not sym_files:
        print(f"No Qucs-S .sym files found under {pdk_root}/libs.tech/qucs-s/symbols/", file=sys.stderr)
        return 2

    symbol_cache = {path: qucs_mod.parse_symbol_geometry(path) for path in sym_files}
    written = export_mod.export_qucs_symbols(pdk_root, symbol_cache)

    mismatches = []
    for path in sym_files:
        export_path = export_mod.export_path_for(pdk_root, path)
        original = path.read_text(encoding="utf-8", errors="replace")
        if not original.endswith("\n"):
            original += "\n"
        if export_path.read_text(encoding="utf-8", errors="replace") != original:
            mismatches.append(path)

    print(f"Exported {len(written)} real Qucs-S .sym file(s) to {export_mod.EXPORT_ROOT / pdk_root.name}")
    print(
        f"No real edits were made this run, so every export should be byte-identical "
        f"to its real original -- {len(sym_files) - len(mismatches)}/{len(sym_files)} are."
    )
    if mismatches:
        print("MISMATCHES (a real write-back correctness bug):", file=sys.stderr)
        for path in mismatches:
            print(f"  {path.relative_to(pdk_root)}", file=sys.stderr)
        return 1
    return 0


def cmd_export_qucs_component(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    component_files = qucs_mod.find_component_files(pdk_root)
    if not component_files:
        print(f"No Qucs-S component .xml files found under {pdk_root}/libs.tech/qucs-s/symbols/", file=sys.stderr)
        return 2

    component_cache = {path: qucs_mod.parse_component_file(path) for path in component_files}
    written = export_mod.export_qucs_components(pdk_root, component_cache)

    mismatches = []
    for path in component_files:
        export_path = export_mod.export_path_for(pdk_root, path)
        original = path.read_text(encoding="utf-8", errors="replace")
        if not original.endswith("\n"):
            original += "\n"
        if export_path.read_text(encoding="utf-8", errors="replace") != original:
            mismatches.append(path)

    print(f"Exported {len(written)} real Qucs-S component .xml file(s) to {export_mod.EXPORT_ROOT / pdk_root.name}")
    print(
        f"No real edits were made this run, so every export should be byte-identical "
        f"to its real original -- {len(component_files) - len(mismatches)}/{len(component_files)} are."
    )
    if mismatches:
        print("MISMATCHES (a real write-back correctness bug):", file=sys.stderr)
        for path in mismatches:
            print(f"  {path.relative_to(pdk_root)}", file=sys.stderr)
        return 1
    return 0


def cmd_export_drc(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    drc_root = drc_mod.find_drc_root(pdk_root)
    if drc_root is None:
        print(f"No DRC deck found under {pdk_root}/libs.tech/klayout/tech/drc/", file=sys.stderr)
        return 2

    rules, _skipped_extraction = drc_mod.extract_design_rules(pdk_root, drc_root)
    written, skipped_writeback = export_mod.export_drc_rules(pdk_root, drc_root, rules)

    mismatches = []
    for export_path in written:
        relpath = export_path.relative_to(export_mod.EXPORT_ROOT / pdk_root.name)
        original_path = pdk_root / relpath
        if export_path.read_text(encoding="utf-8", errors="replace") != original_path.read_text(encoding="utf-8", errors="replace"):
            mismatches.append(original_path)

    print(f"Exported {len(written)} real file(s) (DRC scripts + JSON config) to {export_mod.EXPORT_ROOT / pdk_root.name}")
    print(
        f"No real edits were made this run, so every export should be byte-identical "
        f"to its real original -- {len(written) - len(mismatches)}/{len(written)} are."
    )
    if skipped_writeback:
        reasons = "; ".join(f"{rule_id} ({reason})" for rule_id, reason in skipped_writeback)
        print(f"{len(skipped_writeback)} rule(s) not written back: {reasons}")
    if mismatches:
        print("MISMATCHES (a real write-back correctness bug):", file=sys.stderr)
        for path in mismatches:
            print(f"  {path.relative_to(pdk_root)}", file=sys.stderr)
        return 1
    return 0


def cmd_export_magic_types(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    technologies = {}
    for path in magic_tech_mod.find_tech_files(pdk_root):
        tech = magic_tech_mod.parse_tech_file(path)
        if tech.name:
            technologies[tech.name] = tech
    if not technologies:
        print(f"No real Magic technologies found under {pdk_root}/libs.tech/magic/", file=sys.stderr)
        return 2

    written = export_mod.export_magic_types(pdk_root, technologies)

    mismatches = []
    for export_path in written:
        relpath = export_path.relative_to(export_mod.EXPORT_ROOT / pdk_root.name)
        original_path = pdk_root / relpath
        if export_path.read_text(encoding="utf-8", errors="replace") != original_path.read_text(encoding="utf-8", errors="replace"):
            mismatches.append(original_path)

    print(f"Exported {len(written)} real .tech file(s) to {export_mod.EXPORT_ROOT / pdk_root.name}")
    print(
        f"No real edits were made this run, so every export should be byte-identical "
        f"to its real original -- {len(written) - len(mismatches)}/{len(written)} are."
    )
    if mismatches:
        print("MISMATCHES (a real write-back correctness bug):", file=sys.stderr)
        for path in mismatches:
            print(f"  {path.relative_to(pdk_root)}", file=sys.stderr)
        return 1
    return 0


def cmd_export_netlist(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    netlist_cache = {
        path: netlist_mod.find_cells(path)
        for pattern in ("libs.ref/*/cdl/*.cdl", "libs.ref/*/spice/*.spice")
        for path in pdk_root.glob(pattern)
    }
    if not netlist_cache:
        print(f"No .cdl/.spice files found under {pdk_root}/libs.ref/", file=sys.stderr)
        return 2

    written = export_mod.export_netlist_files(pdk_root, netlist_cache)

    mismatches = []
    for export_path in written:
        relpath = export_path.relative_to(export_mod.EXPORT_ROOT / pdk_root.name)
        original_path = pdk_root / relpath
        if export_path.read_text(encoding="utf-8", errors="replace") != original_path.read_text(encoding="utf-8", errors="replace"):
            mismatches.append(original_path)

    print(f"Exported {len(written)} real .cdl/.spice file(s) to {export_mod.EXPORT_ROOT / pdk_root.name}")
    print(
        f"No real edits were made this run, so every export should be byte-identical "
        f"to its real original -- {len(written) - len(mismatches)}/{len(written)} are."
    )
    if mismatches:
        print("MISMATCHES (a real write-back correctness bug):", file=sys.stderr)
        for path in mismatches:
            print(f"  {path.relative_to(pdk_root)}", file=sys.stderr)
        return 1
    return 0


def cmd_export_verilog(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    verilog_cache = {path: verilog_mod.find_modules(path) for path in pdk_root.glob("libs.ref/*/verilog/*.v")}
    if not verilog_cache:
        print(f"No .v files found under {pdk_root}/libs.ref/", file=sys.stderr)
        return 2

    written = export_mod.export_verilog_files(pdk_root, verilog_cache)

    mismatches = []
    for export_path in written:
        relpath = export_path.relative_to(export_mod.EXPORT_ROOT / pdk_root.name)
        original_path = pdk_root / relpath
        if export_path.read_text(encoding="utf-8", errors="replace") != original_path.read_text(encoding="utf-8", errors="replace"):
            mismatches.append(original_path)

    print(f"Exported {len(written)} real .v file(s) to {export_mod.EXPORT_ROOT / pdk_root.name}")
    print(
        f"No real edits were made this run, so every export should be byte-identical "
        f"to its real original -- {len(written) - len(mismatches)}/{len(written)} are."
    )
    if mismatches:
        print("MISMATCHES (a real write-back correctness bug):", file=sys.stderr)
        for path in mismatches:
            print(f"  {path.relative_to(pdk_root)}", file=sys.stderr)
        return 1
    return 0


def cmd_export_liberty(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    liberty_cache = {path: liberty_mod.find_cells(path) for path in pdk_root.glob("libs.ref/*/lib/*.lib")}
    if not liberty_cache:
        print(f"No .lib files found under {pdk_root}/libs.ref/", file=sys.stderr)
        return 2

    written = export_mod.export_liberty_files(pdk_root, liberty_cache)

    mismatches = []
    for export_path in written:
        relpath = export_path.relative_to(export_mod.EXPORT_ROOT / pdk_root.name)
        original_path = pdk_root / relpath
        if export_path.read_text(encoding="utf-8", errors="replace") != original_path.read_text(encoding="utf-8", errors="replace"):
            mismatches.append(original_path)

    print(f"Exported {len(written)} real .lib file(s) to {export_mod.EXPORT_ROOT / pdk_root.name}")
    print(
        f"No real edits were made this run, so every export should be byte-identical "
        f"to its real original -- {len(written) - len(mismatches)}/{len(written)} are."
    )
    if mismatches:
        print("MISMATCHES (a real write-back correctness bug):", file=sys.stderr)
        for path in mismatches:
            print(f"  {path.relative_to(pdk_root)}", file=sys.stderr)
        return 1
    return 0


def cmd_export_layers(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2

    lyp_path = layers_mod.find_lyp(pdk_root)
    if lyp_path is None:
        print(f"No .lyp file found under {pdk_root}/libs.tech/", file=sys.stderr)
        return 2

    layers = layers_mod.import_layers(pdk_root, lyp_path)
    export_path = export_mod.export_layers(pdk_root, lyp_path, layers)

    original_text = lyp_path.read_text(encoding="utf-8", errors="replace")
    exported_text = export_path.read_text(encoding="utf-8", errors="replace")
    match = exported_text == original_text

    print(f"Exported {len(layers)} real layer(s) to {export_path}")
    print(
        f"No real edits were made this run, so the export should be byte-identical "
        f"to its real original -- {'yes' if match else 'NO'}."
    )
    if not match:
        print("MISMATCH (a real write-back correctness bug):", file=sys.stderr)
        return 1
    return 0


def cmd_export_full(pdk_root: Path, dest: Path) -> int:
    """A complete, real, standalone PDK tree at *dest* (see
    ``export.export_full_pdk``'s own docstring) -- the "smoking gun"
    round-trip fidelity check: run this twice, chaining the previous
    output back in as the next real input
    (``export-full --pdk-root real_pdk --dest A`` then
    ``export-full --pdk-root A --dest B``), then diff A and B
    (structurally -- ``diff -rq --no-dereference``, not a plain
    content diff, which silently treats a dereferenced symlink as
    unchanged) -- they should be identical. Confirmed for real against
    the full ~744 MB IHP deck (4900 real files/symlinks): identical in
    both directions after fixing a real bug this exact test found
    (``shutil.copytree``'s own default dereferences symlinks into
    plain files -- IHP's own real
    ``libs.tech/ngspice/install.py -> ../xschem/install.py``)."""

    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2
    try:
        export_mod.export_full_pdk(pdk_root, dest)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Exported a complete real PDK tree to {dest}")
    return 0


def cmd_wizard(pdk_root: Path, name: str, blank: bool, force: bool, env: str, open_gui: bool) -> int:
    """The CLI equivalent of the GUI's own **File > Create a New
    PDK.../Create a Blank PDK...** (``gui/app.py``'s ``_create_pdk``)
    -- same real ``pdklib/skeleton.py`` builders, same non-empty-
    directory confirmation (here, ``--force``), no Tk required. Lets a
    new project be started headlessly -- from a script, CI, or a
    terminal with no display -- rather than only through the GUI.

    *env* controls the generated shell-env script
    (``pdklib/shell_env.py``, the same one Settings > Environment
    already exposes): ``"save"`` (default) writes ``shell_env/
    pdk_env.sh`` under the project root and reports its path;
    ``"print"`` prints *only* the raw script text to stdout (every
    other message here moves to stderr instead), so the whole command
    can be sourced directly, e.g. ``source <(python3 main.py
    --pdk-root DIR wizard --name NAME --env print)``; ``"skip"`` does
    neither."""

    out = sys.stderr if env == "print" else sys.stdout

    if pdk_root.is_dir() and any(pdk_root.iterdir()) and not force:
        print(
            f"{pdk_root} already exists and is not empty -- pass --force to create the PDK there "
            "anyway (matches the GUI's own File > Create a New/Blank PDK... confirmation).",
            file=sys.stderr,
        )
        return 2

    try:
        if blank:
            skeleton_mod.build_blank_pdk(pdk_root)
        else:
            skeleton_mod.build_new_pdk_skeleton(pdk_root, _slugify_name(name))
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Created a {'blank' if blank else 'new'} PDK at {pdk_root}", file=out)

    save_path = project_io.save_state(pdk_root, design_rules=[], magic_types={}, lef_pins={}, project_name=name)
    print(f"Project name {name!r} saved to {save_path}", file=out)

    if env != "skip":
        script = shell_env_mod.generate_shell_env_script(pdk_root, SHELL_ENV_SCRIPT_NAME)
        if env == "print":
            sys.stdout.write(script.text)
        else:
            dest_dir = export_mod.PROJECT_ROOT / SHELL_ENV_DIRNAME
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / SHELL_ENV_SCRIPT_NAME
            dest_path.write_text(script.text, encoding="utf-8")
            dest_path.chmod(0o755)
            print(f"Shell-env script saved to {dest_path} -- run: source {dest_path}", file=out)

    if open_gui:
        return cmd_gui(pdk_root)
    return 0


def cmd_gui(pdk_root: Path) -> int:
    if not pdk_root.is_dir():
        print(f"Not a directory: {pdk_root} -- run 'python3 main.py fetch' first.", file=sys.stderr)
        return 2
    import tkinter as tk

    from openpdkcreator.gui.app import App

    root = tk.Tk()
    App(root, pdk_root)
    root.mainloop()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--pdk-root", type=Path, default=DEFAULT_PDK_ROOT,
        help=f"Root of the downloaded ihp-sg13g2/ tree (default: {DEFAULT_PDK_ROOT})",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    fetch_parser = sub.add_parser("fetch", help="Download the real IHP PDK.")
    fetch_parser.add_argument("--dest", type=Path, default=fetch_mod.DEFAULT_DEST)
    sub.add_parser("inventory", help="Print a per-tool file inventory.")
    sub.add_parser("magic-tech", help="Parse real Magic .tech files; cross-reference against the .lyp.")
    sub.add_parser("lef", help="Parse real LEF files: tech layers + macro/cell footprints.")
    sub.add_parser("ngspice", help="Parse real ngspice .lib model cards: .model/.subckt statements.")
    sub.add_parser("xschem", help="Parse real xschem .sym symbols: device type + pin list.")
    sub.add_parser("xschem-sch", help="Parse real xschem .sch schematics: instances/pins/wires.")
    sub.add_parser("qucs", help="Parse real Qucs-S component .xml/symbol .sym files.")
    sub.add_parser("user-models", help="List user_models/ Verilog/Verilog-A modules and their real cell links.")
    sub.add_parser("drc", help="Extract real design rules from the real KLayout DRC deck.")
    cells_parser = sub.add_parser("cells", help="Aggregate one real cell's views across libs.ref/<family>/*/.")
    cells_parser.add_argument("--family", default=None, help="Real family to scope to (default: all).")
    gds_parser = sub.add_parser("gds", help="Real GDS structural summary (bbox/shape counts) via klayout.db.")
    gds_parser.add_argument("--family", default=None, help="Real family to scope to (default: all).")
    sub.add_parser("export-lef", help="Export real, patched .lef files to export/ (byte-identical with no edits).")
    sub.add_parser("export-drc", help="Export real, patched DRC scripts + JSON config to export/ (byte-identical with no edits).")
    sub.add_parser("export-magic-types", help="Export real, patched .tech files to export/ (byte-identical with no edits).")
    sub.add_parser("export-netlist", help="Export real, patched .cdl/.spice files to export/ (byte-identical with no edits).")
    sub.add_parser("export-verilog", help="Export real, patched .v files to export/ (byte-identical with no edits).")
    sub.add_parser("export-liberty", help="Export real, patched .lib files to export/ (byte-identical with no edits).")
    sub.add_parser("export-layers", help="Export the real, patched .lyp file to export/ (byte-identical with no edits).")
    sub.add_parser("export-xschem-sym", help="Export real, patched xschem .sym files to export/ (byte-identical with no edits).")
    sub.add_parser("export-xschem-sch", help="Export real, patched xschem .sch files to export/ (byte-identical with no edits).")
    sub.add_parser("export-qucs-sym", help="Export real, patched Qucs-S .sym files to export/ (byte-identical with no edits).")
    sub.add_parser("export-qucs-component", help="Export real, patched Qucs-S component .xml files to export/ (byte-identical with no edits).")
    export_full_parser = sub.add_parser(
        "export-full", help="Export a complete, standalone PDK tree -- for round-trip fidelity testing.",
    )
    export_full_parser.add_argument("--dest", type=Path, required=True, help="Destination directory (must not exist).")
    wizard_parser = sub.add_parser(
        "wizard",
        help="Create a new PDK project headlessly, no GUI needed -- the CLI equivalent of "
        "File > Create a New/Blank PDK....",
    )
    wizard_parser.add_argument(
        "--name", required=True,
        help="Project name, saved to Settings > Project name; also slugified for the skeleton's "
        "own Layers/Magic Tech/LEF file names (ignored with --blank).",
    )
    wizard_parser.add_argument(
        "--blank", action="store_true",
        help="Create a blank PDK (just libs.tech/libs.ref, no files) instead of the default "
        "minimal, immediately-usable skeleton (Layers/Magic Tech/DRC deck/LEF).",
    )
    wizard_parser.add_argument(
        "--force", action="store_true", help="Proceed even if --pdk-root already exists and is not empty.",
    )
    wizard_parser.add_argument(
        "--env", choices=("save", "print", "skip"), default="save",
        help="What to do with the generated shell-env script: 'save' (default) writes "
        "shell_env/pdk_env.sh under the project root and prints its path; 'print' prints only the "
        "raw script to stdout (everything else here goes to stderr instead), so it can be sourced "
        "directly; 'skip' does neither.",
    )
    wizard_parser.add_argument(
        "--open-gui", action="store_true", help="Launch the GUI on the new project once it's created.",
    )
    sub.add_parser("gui", help="Open the Overview/Technology/Cells GUI.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "fetch":
        return cmd_fetch(args.dest)
    if args.command == "inventory":
        return cmd_inventory(args.pdk_root.resolve())
    if args.command == "magic-tech":
        return cmd_magic_tech(args.pdk_root.resolve())
    if args.command == "lef":
        return cmd_lef(args.pdk_root.resolve())
    if args.command == "ngspice":
        return cmd_ngspice(args.pdk_root.resolve())
    if args.command == "xschem":
        return cmd_xschem(args.pdk_root.resolve())
    if args.command == "xschem-sch":
        return cmd_xschem_sch(args.pdk_root.resolve())
    if args.command == "qucs":
        return cmd_qucs(args.pdk_root.resolve())
    if args.command == "user-models":
        return cmd_user_models()
    if args.command == "drc":
        return cmd_drc(args.pdk_root.resolve())
    if args.command == "cells":
        return cmd_cells(args.pdk_root.resolve(), args.family)
    if args.command == "gds":
        return cmd_gds(args.pdk_root.resolve(), args.family)
    if args.command == "export-lef":
        return cmd_export_lef(args.pdk_root.resolve())
    if args.command == "export-drc":
        return cmd_export_drc(args.pdk_root.resolve())
    if args.command == "export-magic-types":
        return cmd_export_magic_types(args.pdk_root.resolve())
    if args.command == "export-netlist":
        return cmd_export_netlist(args.pdk_root.resolve())
    if args.command == "export-verilog":
        return cmd_export_verilog(args.pdk_root.resolve())
    if args.command == "export-liberty":
        return cmd_export_liberty(args.pdk_root.resolve())
    if args.command == "export-layers":
        return cmd_export_layers(args.pdk_root.resolve())
    if args.command == "export-xschem-sym":
        return cmd_export_xschem_sym(args.pdk_root.resolve())
    if args.command == "export-xschem-sch":
        return cmd_export_xschem_sch(args.pdk_root.resolve())
    if args.command == "export-qucs-sym":
        return cmd_export_qucs_sym(args.pdk_root.resolve())
    if args.command == "export-qucs-component":
        return cmd_export_qucs_component(args.pdk_root.resolve())
    if args.command == "export-full":
        return cmd_export_full(args.pdk_root.resolve(), args.dest.resolve())
    if args.command == "wizard":
        return cmd_wizard(args.pdk_root.resolve(), args.name, args.blank, args.force, args.env, args.open_gui)
    if args.command == "gui":
        return cmd_gui(args.pdk_root.resolve())
    return 1


if __name__ == "__main__":
    sys.exit(main())

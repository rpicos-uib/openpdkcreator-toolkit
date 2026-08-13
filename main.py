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
counts, OBS layers). No attempt at GDS parsing, LEF via-stack geometry,
or Magic's drc/extract/cifinput/connect/compose sections (each its own
real, separate mini rule-language) -- that's real, separate future
work. The much larger end goal -- editing/creating/generating arbitrary
PDK file types, not just reading/displaying them -- is explicit,
tracked future work, not attempted here.

    python3 main.py fetch                 # download the real IHP PDK (once)
    python3 main.py inventory             # per-tool file census, printed
    python3 main.py magic-tech            # real Magic .tech parse + KLayout cross-reference
    python3 main.py lef                   # real LEF parse summary (tech layers + macros)
    python3 main.py gui                   # Overview, Technology, Cells tabs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openpdkcreator.ihp import fetch as fetch_mod
from openpdkcreator.ihp import inventory as inventory_mod
from openpdkcreator.ihp import layers as layers_mod
from openpdkcreator.ihp import lef as lef_mod
from openpdkcreator.ihp import magic_tech as magic_tech_mod
from openpdkcreator.ihp import reconcile as reconcile_mod

DEFAULT_PDK_ROOT = Path(__file__).resolve().parent / "data" / "ihp-sg13g2" / "ihp-sg13g2"


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
            f"styles:{len(tech.styles)}  cif_layers:{len(tech.cif_layers)}"
        )
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
        if parsed.via_names:
            detail.append(f"{len(parsed.via_names)} via def(s) (bodies not parsed)")
        if parsed.via_rule_names:
            detail.append(f"{len(parsed.via_rule_names)} viarule(s) (bodies not parsed)")
        print(f"{path.relative_to(pdk_root)}: {', '.join(detail) if detail else '(nothing recognized)'}")

    print(f"\n{len(lef_files)} real .lef file(s): {total_layers} tech layer(s), {total_macros} macro(s) total.")
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
    if args.command == "gui":
        return cmd_gui(args.pdk_root.resolve())
    return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""openPDKcreator: read real PDK files (starting with IHP's SG13G2) and
represent the information, organized by tool -- reusing OpenPDKCreator's
own Layers interface for displaying/editing real, parsed layer data.

A real, deliberately-scoped first increment (see README.md's Future
Work): an honest per-tool file inventory (no attempt at deep-parsing
Magic/LEF/GDS -- no existing parser for those yet, that's real,
separate future work) plus real KLayout .lyp -> Layer parsing. The
much larger end goal -- editing/creating/generating arbitrary PDK file
types, not just reading/displaying layers -- is explicit, tracked
future work, not attempted here.

    python3 main.py fetch                 # download the real IHP PDK (once)
    python3 main.py inventory             # per-tool file census, printed
    python3 main.py gui                   # Inventory + Layers tabs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openpdkcreator.ihp import fetch as fetch_mod
from openpdkcreator.ihp import inventory as inventory_mod

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
    sub.add_parser("gui", help="Open the Inventory + Layers GUI.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "fetch":
        return cmd_fetch(args.dest)
    if args.command == "inventory":
        return cmd_inventory(args.pdk_root.resolve())
    if args.command == "gui":
        return cmd_gui(args.pdk_root.resolve())
    return 1


if __name__ == "__main__":
    sys.exit(main())

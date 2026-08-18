#!/usr/bin/env python3
"""Fetch the real IHP-Open-PDK (github.com/IHP-GmbH/IHP-Open-PDK,
Apache-2.0) into ``data/ihp-sg13g2/`` -- specifically just
``ihp-sg13g2/{libs.doc,libs.qa,libs.ref,libs.tech}`` (real size,
confirmed via the GitHub API: ~734 MB), deliberately excluding IHP's
own git submodules (separate third-party repos for a digital synthesis
flow and openEMS/palace EM-solver integration, unrelated to PDK
structure -- never initialized here, since this never runs
``git submodule update``).

A depth-1, blobless-then-sparse clone: fetches minimal history, and
only ever materializes blobs for the four directories actually checked
out. This directory is ``.gitignore``d -- never committed to this
project's own git history (see README.md and
docs/ihp_vs_open_pdks.md for why).

    python3 -m openpdkcreator.pdklib.fetch
    python3 -m openpdkcreator.pdklib.fetch --dest /some/other/path
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/IHP-GmbH/IHP-Open-PDK.git"
SPARSE_PATHS = (
    "ihp-sg13g2/libs.doc",
    "ihp-sg13g2/libs.qa",
    "ihp-sg13g2/libs.ref",
    "ihp-sg13g2/libs.tech",
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEST = PROJECT_ROOT / "data" / "ihp-sg13g2"


def _run(argv: list[str], cwd: Path | None = None) -> None:
    print(f"$ {' '.join(argv)}" + (f"  (cwd={cwd})" if cwd else ""))
    subprocess.run(argv, cwd=cwd, check=True)


def fetch(dest: Path) -> None:
    if dest.exists():
        raise SystemExit(
            f"{dest} already exists -- remove it first if you want a fresh fetch "
            f"(this script never overwrites an existing checkout)."
        )
    dest.parent.mkdir(parents=True, exist_ok=True)

    _run([
        "git", "clone",
        "--filter=blob:none", "--no-checkout", "--depth", "1",
        REPO_URL, str(dest),
    ])
    _run(["git", "sparse-checkout", "init", "--cone"], cwd=dest)
    _run(["git", "sparse-checkout", "set", *SPARSE_PATHS], cwd=dest)
    _run(["git", "checkout", "main"], cwd=dest)

    print("\nDone. Real content lands under:")
    for path in SPARSE_PATHS:
        print(f"  {dest / path}")
    print(
        "\nSubmodule directories under libs.tech/ (digital, openems/"
        "openems_ihp_sg13g2, palace, klayout/python/*) exist as empty "
        "placeholders -- never initialized (no 'git submodule update' "
        "was run), by design."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dest", type=Path, default=DEFAULT_DEST,
        help=f"Where to clone into (default: {DEFAULT_DEST})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fetch(args.dest.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())

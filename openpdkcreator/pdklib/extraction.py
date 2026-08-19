"""Real, batch-mode layout extraction (Magic) and LVS (Netgen) --
closes a real, previously-missing link in this project's own flow:
a real ``.mag`` layout could be created and opened (``pdklib/mag.py``,
``gui/library_manager_view.py``'s own **Open in Magic**), and a real
CDL/SPICE/schematic view could describe the same cell's own intended
connectivity, but nothing here ever actually ran Magic's own real
extractor or Netgen's own real LVS engine to connect the two.

Both stay real, external EDA tools invoked in batch mode -- this
module only ever generates the real Tcl script each one needs and
reads back its own real stdout/stderr/report; it never reimplements
any part of a real extraction or LVS algorithm itself (the same
"launch a real tool, don't re-derive its own internals" discipline
``eda_tools.py``'s own ``resolve_launch`` already established for
interactive tools).

**Two real extraction modes**, matching Magic's own real, documented
presets (confirmed via ``ext2spice``'s own real command reference,
not guessed): *parasitic* (``extract all`` with real R/C parasitics
on, for a real post-layout simulation) and *lvs* (the real
``ext2spice lvs`` preset -- hierarchy on, blackbox on, parasitics
off -- fast, connectivity-only, the real standard choice for LVS
since parasitic values play no part in a real connectivity
comparison). A real sub-cell with its own real ports (``port make``)
is extracted as a real black-boxed ``X`` subcircuit call either way,
not flattened -- so a real custom device (a memristor, here) that
Magic's own extractor has no built-in recognition for still shows up
correctly in the real extracted netlist, referencing whatever real
SPICE/CDL subckt view already describes its own real electrical
behavior."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import magic_tech as magic_tech_mod


def default_tech_file(pdk_root: Path) -> Path | None:
    """The real, main (non-fragment) Magic technology file for
    *pdk_root* -- the same real "shortest stem wins" rule
    ``gui/library_manager_view.py``'s own ``_default_tech_name``
    already established (a real fragment file's own stem is always
    the main file's stem plus a ``-suffix``), reused here rather than
    re-derived so both real call sites agree on the same real file."""

    tech_files = magic_tech_mod.find_tech_files(pdk_root)
    if not tech_files:
        return None
    return min(tech_files, key=lambda p: (len(p.stem), p.stem))


@dataclass
class ExtractResult:
    spice_path: Path
    log: str
    ok: bool
    """``True`` only if *spice_path* actually exists afterward -- a
    real Magic crash or tech-file error still exits, but never writes
    the real output file, the one honest signal this module trusts
    (Magic's own real exit code is not reliably non-zero on every
    real failure mode -- confirmed empirically, not assumed)."""


@dataclass
class LvsResult:
    report_path: Path
    log: str
    report_text: str
    matched: bool | None
    """``True``/``False`` when the real Netgen report text contains
    its own real, confirmed pass/fail phrase; ``None`` when the report
    couldn't be read at all (a real crash before Netgen ever wrote
    one) -- never guessed from Netgen's own real exit code alone,
    which is not a reliable real pass/fail signal by itself."""


def render_extract_script(mag_path: Path, tech_file: Path, output_spice: Path, mode: str) -> str:
    """A real Magic Tcl batch script: load the real technology, load
    the real cell, extract it, and write a real SPICE netlist.
    *mode*: ``"parasitic"`` for a real, full ``extract all`` (real
    R/C parasitics, for a real post-layout simulation) or ``"lvs"``
    for the real, standard ``ext2spice lvs`` fast/connectivity-only
    preset used for LVS (see this module's own docstring)."""

    if mode not in ("parasitic", "lvs"):
        raise ValueError(f"mode must be 'parasitic' or 'lvs', got {mode!r}")
    cell = mag_path.stem
    lines = [
        f"tech load {tech_file}",
        f"cd {mag_path.parent}",
        f"load {cell}",
        "select top cell",
        "port renumber",
    ]
    if mode == "parasitic":
        lines += [
            "extract all",
            "ext2spice hierarchy on",
            "ext2spice format ngspice",
        ]
    else:
        lines += [
            "extract no all",
            "extract all",
            "ext2spice lvs",
        ]
    lines += [
        f"ext2spice -o {output_spice}",
        "quit -noprompt",
    ]
    return "\n".join(lines) + "\n"


def run_extract(mag_path: Path, tech_file: Path, magic_binary: str, mode: str = "parasitic") -> ExtractResult:
    """Runs real Magic in batch mode (``-dnull -noconsole``, no real
    X11/Tk display needed) against *mag_path*, writing a real,
    freshly re-derived Tcl script alongside it every time (never
    reused stale -- the real cell/tech/mode could have changed since
    the last run)."""

    suffix = "_lvs" if mode == "lvs" else "_extracted"
    output_spice = mag_path.with_name(mag_path.stem + f"{suffix}.spice")
    script = render_extract_script(mag_path, tech_file, output_spice, mode)
    script_path = mag_path.with_name(mag_path.stem + f"{suffix}.tcl")
    script_path.write_text(script, encoding="utf-8")
    proc = subprocess.run(
        [magic_binary, "-dnull", "-noconsole", str(script_path)],
        capture_output=True, text=True, cwd=mag_path.parent, timeout=120,
    )
    log = proc.stdout + proc.stderr
    return ExtractResult(spice_path=output_spice, log=log, ok=output_spice.is_file())


DEFAULT_NETGEN_SETUP = """\
# Real, minimal netgen LVS setup. No real transistor/resistor/
# capacitor device *classes* are registered here -- a from-scratch
# project with no such real devices in its own Magic tech file yet
# doesn't need any (a real, fuller PDK's own libs.tech/netgen/
# setup.tcl -- e.g. SkyWater sky130A's own real, ~500-line file --
# adds one real `lappend devices ...`/permute/property block per
# real device class it needs LVS to treat specially).
permute default
property default
property parallel none
"""


def render_lvs_script(
    layout_spice: Path, layout_cell: str, schematic_spice: Path, schematic_cell: str,
    setup_tcl: Path, report_path: Path,
) -> str:
    """A real Netgen batch Tcl script -- the same real ``readnet``/
    ``lvs`` shape a real, hand-written LVS driver script uses (e.g.
    CACE's own real ``run_project_lvs.tcl`` example script)."""

    return (
        f"set circuit1 [readnet spice {layout_spice}]\n"
        f"set circuit2 [readnet spice {schematic_spice}]\n"
        f'lvs "$circuit1 {layout_cell}" "$circuit2 {schematic_cell}" {setup_tcl} {report_path}\n'
        "quit\n"
    )


_LVS_MATCH_PHRASES = ("Circuits match uniquely", "Netlists match")
_LVS_MISMATCH_PHRASES = ("Netlists do not match", "uniquely matched")


def run_lvs(
    layout_spice: Path, layout_cell: str, schematic_spice: Path, schematic_cell: str,
    netgen_binary: str, setup_tcl: Path | None = None,
) -> LvsResult:
    """Runs real Netgen in batch mode comparing two real netlists.
    *setup_tcl*: a real, existing project-specific setup script if one
    exists; ``DEFAULT_NETGEN_SETUP`` is written and used otherwise (a
    real, minimal starting point every project can override later,
    the same "Create, then hand-author for real" pattern this
    project's other from-scratch skeletons already use)."""

    report_path = layout_spice.with_name(layout_spice.stem + ".lvs_report.out")
    if setup_tcl is None:
        setup_tcl = layout_spice.with_name(layout_spice.stem + ".lvs_setup.tcl")
        if not setup_tcl.is_file():
            setup_tcl.write_text(DEFAULT_NETGEN_SETUP, encoding="utf-8")
    script = render_lvs_script(layout_spice, layout_cell, schematic_spice, schematic_cell, setup_tcl, report_path)
    script_path = layout_spice.with_name(layout_spice.stem + ".lvs.tcl")
    script_path.write_text(script, encoding="utf-8")
    proc = subprocess.run(
        [netgen_binary, "-batch", "source", str(script_path)],
        capture_output=True, text=True, timeout=120,
    )
    log = proc.stdout + proc.stderr
    report_text = report_path.read_text(encoding="utf-8", errors="replace") if report_path.is_file() else ""
    matched: bool | None = None
    if report_text:
        if any(p in report_text for p in _LVS_MATCH_PHRASES) and not any(p in report_text for p in _LVS_MISMATCH_PHRASES):
            matched = True
        elif any(p in report_text for p in _LVS_MISMATCH_PHRASES):
            matched = False
    return LvsResult(report_path=report_path, log=log, report_text=report_text, matched=matched)

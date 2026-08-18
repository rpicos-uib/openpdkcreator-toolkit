"""Real ``.subckt``/``.ends`` boundary detection for CDL and SPICE
netlists -- both real IHP files use the same real syntax
(``.subckt NAME ports...`` ... ``.ends``), confirmed to differ only in
case between the two real, downloaded files (CDL:
`.SUBCKT`/`.ENDS`, SPICE: `.subckt`/`.ends`) -- matched
case-insensitively throughout, the same lesson learned from
``lef.py``'s own real ``Via``/``ViaRULE`` mixed-case finding.

Real, deliberately bounded scope: cell name + port list (+ real
per-port direction, when a real ``*.PININFO`` comment is present -- see
below) + the real source line range -- not a full SPICE/CDL netlist
parser (device instantiation lines, parameters, subcircuit calls are
not modeled). Good enough to answer "does this cell have a CDL/SPICE
view, what are its real ports, and where is it in the real file" -- the
rest of the real content is shown by scrolling ``file_view_dialog`` to
that real line range, not by re-rendering it.

**A real, easy-to-miss detail, found while extending this parser for
real port editing, not assumed**: a real ``.SUBCKT`` header can wrap
its port list across multiple lines with a leading ``+`` continuation
marker (standard SPICE/CDL convention) -- confirmed real and common in
IHP's own SRAM family (dozens of real internal sub-elements in
``RM_IHPSG13_1P_1024x16_c2_bm_bist.cdl`` alone). The original version
of this parser didn't join continuation lines, silently truncating
those cells' real port lists at the first line break -- a real,
previously-unnoticed bug (the real, top-level hard-macro SUBCKTs
happen to each fit on one real line, so it never affected the By Cell
hub's own top-level-only default view) fixed here by joining ``+``
continuation lines before parsing a header, the same discipline
``pdklib/drc_writer.py``'s own backslash-continuation joining already
established for a different real format.

**Real per-port direction** (``NetlistPort.direction``): CDL files
carry a real ``*.PININFO name:I name:O name:B ...`` comment
immediately following every real ``.SUBCKT`` line (confirmed: 100%
real coverage across ``sg13g2_io``/``sg13g2_stdcell``'s CDL files, 130
of 130 SUBCKTs; confirmed real absence across all of `sg13g2_sram`'s
own CDL files -- 0 of 2338 -- an honest real gap in IHP's own SRAM
netlists, not a parser gap). Real letters map directly:
``I``->``INPUT``, ``O``->``OUTPUT``, ``B``->``INOUT`` (CDL's own
convention for "bidirectional," used for both true bidirectional
signals and power/ground pins alike -- kept as the closest existing
term, matching ``lef.py``'s own ``DIRECTIONS`` vocabulary). SPICE files
carry no such comment in any real IHP file found -- ``direction``
stays blank there, honestly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_SUBCKT_START_RE = re.compile(r"^\.subckt\s+(\S+)", re.IGNORECASE)
_ENDS_RE = re.compile(r"^\.ends\b", re.IGNORECASE)
_PININFO_RE = re.compile(r"^\*\.PININFO\s+(.+)$", re.IGNORECASE)
_PININFO_LETTER_TO_DIRECTION = {"I": "INPUT", "O": "OUTPUT", "B": "INOUT"}


@dataclass
class NetlistPort:
    name: str
    direction: str = ""
    """"INPUT"/"OUTPUT"/"INOUT" from a real CDL ``*.PININFO`` entry,
    or "" when unknown (SPICE, or a real CDL file with no PININFO
    comment -- e.g. every real ``sg13g2_sram`` netlist)."""


@dataclass
class NetlistCell:
    name: str
    ports: list[NetlistPort] = field(default_factory=list)
    start_line: int = 0
    """The real ``.SUBCKT`` line itself (its *first* real line, if the
    header wraps across ``+`` continuations)."""
    end_line: int = 0
    header_end_line: int = 0
    """The real last line of the (possibly ``+``-continued) header --
    equal to ``start_line`` when the header fits on one real line.
    ``pdklib/netlist_writer.py`` replaces exactly this real span on
    write-back."""
    pininfo_line_no: int = 0
    """The real source line of this cell's ``*.PININFO`` comment, ``0``
    if none was found (SPICE, or a real CDL cell with no such
    comment)."""


def find_cells(path: Path) -> list[NetlistCell]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    cells: list[NetlistCell] = []
    current: NetlistCell | None = None
    i = 0
    n = len(lines)

    while i < n:
        stripped = lines[i].strip()

        if current is None:
            start_match = _SUBCKT_START_RE.match(stripped)
            if start_match:
                header_line_no = i + 1
                header_text = stripped
                while i + 1 < n and lines[i + 1].strip().startswith("+"):
                    i += 1
                    header_text += " " + lines[i].strip()[1:].strip()
                port_names = header_text.split()[2:]
                current = NetlistCell(
                    name=start_match.group(1),
                    ports=[NetlistPort(name=name) for name in port_names],
                    start_line=header_line_no,
                    header_end_line=i + 1,
                )
            i += 1
            continue

        if current.pininfo_line_no == 0 and (i + 1) == current.header_end_line + 1:
            pininfo_match = _PININFO_RE.match(stripped)
            if pininfo_match:
                current.pininfo_line_no = i + 1
                direction_by_name = {}
                for token in pininfo_match.group(1).split():
                    name, _, letter = token.partition(":")
                    direction_by_name[name] = _PININFO_LETTER_TO_DIRECTION.get(letter.upper(), "")
                for port in current.ports:
                    port.direction = direction_by_name.get(port.name, "")
                i += 1
                continue

        if _ENDS_RE.match(stripped):
            current.end_line = i + 1
            cells.append(current)
            current = None
        i += 1

    return cells

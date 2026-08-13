"""Real ``.subckt``/``.ends`` boundary detection for CDL and SPICE
netlists -- both real IHP files use the same real syntax
(``.subckt NAME ports...`` ... ``.ends``), confirmed to differ only in
case between the two real, downloaded files (CDL:
`.SUBCKT`/`.ENDS`, SPICE: `.subckt`/`.ends`) -- matched
case-insensitively throughout, the same lesson learned from
``lef.py``'s own real ``Via``/``ViaRULE`` mixed-case finding.

Real, deliberately bounded scope: cell name + port list + the real
source line range -- not a full SPICE/CDL netlist parser (device
instantiation lines, parameters, subcircuit calls are not modeled).
Good enough to answer "does this cell have a CDL/SPICE view, and where
is it in the real file" -- the actual content is shown by scrolling
``file_view_dialog`` to that real line range, not by re-rendering it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_SUBCKT_RE = re.compile(r"^\.subckt\s+(\S+)(.*)$", re.IGNORECASE)
_ENDS_RE = re.compile(r"^\.ends\b", re.IGNORECASE)


@dataclass
class NetlistCell:
    name: str
    ports: list[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0


def find_cells(path: Path) -> list[NetlistCell]:
    if not path.is_file():
        return []
    cells: list[NetlistCell] = []
    current: NetlistCell | None = None
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        stripped = raw_line.strip()
        subckt_match = _SUBCKT_RE.match(stripped)
        if subckt_match:
            current = NetlistCell(
                name=subckt_match.group(1),
                ports=subckt_match.group(2).split(),
                start_line=line_no,
            )
            continue
        if current is not None and _ENDS_RE.match(stripped):
            current.end_line = line_no
            cells.append(current)
            current = None
    return cells

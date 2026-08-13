"""Real ``cell (NAME) { ... }`` boundary detection for Liberty (.lib)
timing views -- unlike CDL/SPICE/Verilog's flat ``.subckt``/``module``
blocks, a real Liberty cell group nests further real groups inside it
(``pin (...)  { ... }``, ``timing () { ... }``, ...), so the real end
of a cell is found by brace-depth counting from its own opening ``{``
back to 0, not a fixed closing keyword.

Real, deliberately bounded scope: cell name + the real source line
range only -- not a full Liberty parser (no pin/timing-arc modeling).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_CELL_RE = re.compile(r"^cell\s*\(\s*(\S+?)\s*\)\s*\{")


@dataclass
class LibertyCell:
    name: str
    start_line: int = 0
    end_line: int = 0


def find_cells(path: Path) -> list[LibertyCell]:
    if not path.is_file():
        return []
    cells: list[LibertyCell] = []
    current: LibertyCell | None = None
    depth = 0
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        stripped = raw_line.strip()
        if current is None:
            match = _CELL_RE.match(stripped)
            if match:
                current = LibertyCell(name=match.group(1), start_line=line_no)
                depth = stripped.count("{") - stripped.count("}")
                if depth <= 0:
                    current.end_line = line_no
                    cells.append(current)
                    current = None
            continue
        depth += stripped.count("{") - stripped.count("}")
        if depth <= 0:
            current.end_line = line_no
            cells.append(current)
            current = None
    return cells

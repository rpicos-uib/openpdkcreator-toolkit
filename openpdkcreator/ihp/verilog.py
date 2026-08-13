"""Real ``module``/``endmodule`` boundary detection for Verilog
behavioral views. Same deliberately bounded scope as ``netlist.py``:
module name + port list + the real source line range, not a full
Verilog parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_MODULE_RE = re.compile(r"^module\s+(\S+)\s*\(([^)]*)\)")
_ENDMODULE_RE = re.compile(r"^endmodule\b")


@dataclass
class VerilogModule:
    name: str
    ports: list[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0


def find_modules(path: Path) -> list[VerilogModule]:
    if not path.is_file():
        return []
    modules: list[VerilogModule] = []
    current: VerilogModule | None = None
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        stripped = raw_line.strip()
        match = _MODULE_RE.match(stripped)
        if match:
            ports = [p.strip() for p in match.group(2).split(",") if p.strip()]
            current = VerilogModule(name=match.group(1), ports=ports, start_line=line_no)
            continue
        if current is not None and _ENDMODULE_RE.match(stripped):
            current.end_line = line_no
            modules.append(current)
            current = None
    return modules

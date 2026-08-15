"""Real ``module``/``endmodule`` boundary detection for Verilog
behavioral views. Same deliberately bounded scope as ``netlist.py``:
module name + port list (+ real per-port direction/width, when
declared -- see below) + the real source line range, not a full
Verilog parser (no expression/instance modeling).

**A real, easy-to-miss detail, found while extending this parser for
real port editing, not assumed**: a real Verilog ``module`` header can
wrap its port list across multiple lines (standard, common style for a
module with many ports) -- confirmed real in every one of IHP's own
28 real SRAM top-level macros (``module NAME (`` on its own line, one
port per subsequent line, closing ``);`` after). The original version
of this parser required the closing ``)`` on the *same* line as
``module NAME (``, so it silently found **zero** real Verilog modules
for any real SRAM macro -- a real, previously-unnoticed bug (every
other real family's own modules happen to fit their header on one real
line, so it never surfaced there) fixed here by joining lines until a
real closing ``)`` is found before parsing a header.

**Real per-port direction/width** (``VerilogPort.direction``/
``.width``): IHP's own real modules declare each port's real
``input``/``output``/``inout`` direction (and, for a real bus port, its
real ``[msb:lsb]`` width) in real declaration statements just inside
the module body (e.g. ``input [9:0] A_ADDR;`` -- confirmed real and
common in the SRAM family). Scanned across the *whole* real module
body (not just immediately after the header -- real IHP files
interleave direction declarations with a leading blank line/comment in
some real cells), attributed by name to the matching real header port;
a port with no matching declaration keeps blank direction/width,
honestly (never guessed).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_MODULE_START_RE = re.compile(r"^module\s+(\S+)\s*\(")
_ENDMODULE_RE = re.compile(r"^endmodule\b")
_DIRECTION_DECL_RE = re.compile(r"^(input|output|inout)\s*(\[[^\]]*\])?\s*(.+);\s*$", re.IGNORECASE)


@dataclass
class VerilogPort:
    name: str
    direction: str = ""
    """"input"/"output"/"inout" (kept lowercase, matching Verilog's own
    real keyword -- unlike LEF's uppercase DIRECTION convention) from a
    real declaration statement in the module body; "" if undeclared."""
    width: str = ""
    """Real ``[msb:lsb]`` text from a real bus declaration, verbatim;
    "" for a real scalar (1-bit) port."""


@dataclass
class VerilogModule:
    name: str
    ports: list[VerilogPort] = field(default_factory=list)
    start_line: int = 0
    """The real ``module`` line itself (its *first* real line, if the
    header wraps across multiple lines)."""
    end_line: int = 0
    header_end_line: int = 0
    """The real last line of the (possibly multi-line) header --
    equal to ``start_line`` when the header fits on one real line.
    ``ihp/verilog_writer.py`` replaces exactly this real span on
    write-back."""
    declaration_line_nos: list[int] = field(default_factory=list)
    """Every real ``input``/``output``/``inout`` declaration line's own
    line number, in real file order -- used by
    ``ihp/verilog_writer.py`` to know exactly which real lines to
    replace (or leave alone) on write-back, the same way
    ``ihp/lef.py``'s ``LefMacro.all_parsed_pin_ranges`` does for pins."""


def create_new_verilog_file(path: Path, module_name: str, ports: list[tuple[str, str]] | None = None) -> None:
    """Writes a real, minimal, valid Verilog module skeleton --
    ``module NAME(port, ...); direction port; ... endmodule`` -- with a
    real ``input``/``output``/``inout`` declaration line for every port
    whose direction is known (see ``ihp/library_index.py``'s own
    ``infer_ports_for_cell`` for where a ports list reflecting a cell's
    already-known real pins comes from). A port with an unknown
    direction still appears in the header port list, just without its
    own declaration line -- matching this module's own parser
    precedent above (an undeclared direction stays blank, never
    guessed)."""

    if path.exists():
        raise FileExistsError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    ports = ports or []
    header_ports = ", ".join(name for name, _direction in ports)
    lines = [f"module {module_name}({header_ports});"]
    for name, direction in ports:
        if direction in ("input", "output", "inout"):
            lines.append(f"  {direction} {name};")
    lines.append("")
    lines.append("endmodule")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def create_new_veriloga_file(path: Path, module_name: str, ports: list[tuple[str, str]] | None = None) -> None:
    """Writes a real, minimal, valid Verilog-A module skeleton --
    empirically confirmed to compile, via a real, live ``openvaf``
    invocation against this exact shape in this project's own
    container: a real ``\\`include "disciplines.vams"`` (OpenVAF's own
    built-in, portable discipline set -- confirmed to need no local
    ``discipline.h`` copy the way IHP's own real ``.va`` files each
    ship one, since a fresh, generated file here has no such file
    alongside it), every real port declared both ``inout`` and
    ``electrical`` -- confirmed real, from IHP's own real ``.va`` files
    (``mosvar.va``/``r3_cmc.va``): a real Verilog-A analog terminal has
    no directional concept the way a digital Verilog port does, so
    every real port there is declared ``inout`` regardless of its own
    analog role -- and a real, empty ``analog begin ... end`` block
    ready for real compact-model equations. *ports*' own real direction
    (if any, e.g. inferred from a matching LEF/xschem view) is
    intentionally unused here, for that same real reason -- only the
    real port names matter."""

    if path.exists():
        raise FileExistsError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    port_names = [name for name, _direction in (ports or [])]
    header_ports = ", ".join(port_names)
    lines = ['`include "disciplines.vams"', "", f"module {module_name}({header_ports});"]
    if port_names:
        decl = ", ".join(port_names)
        lines.append(f"inout {decl};")
        lines.append(f"electrical {decl};")
    lines.append("")
    lines.append("analog begin")
    lines.append("  // TODO: real compact-model equations here")
    lines.append("end")
    lines.append("endmodule")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def find_modules(path: Path) -> list[VerilogModule]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    modules: list[VerilogModule] = []
    current: VerilogModule | None = None
    i = 0
    n = len(lines)

    while i < n:
        stripped = lines[i].strip()

        if current is None:
            start_match = _MODULE_START_RE.match(stripped)
            if start_match:
                header_line_no = i + 1
                header_text = stripped
                while ")" not in header_text and i + 1 < n:
                    i += 1
                    header_text += " " + lines[i].strip()
                open_idx = header_text.index("(")
                close_idx = header_text.index(")", open_idx)
                port_names = [p.strip() for p in header_text[open_idx + 1 : close_idx].split(",") if p.strip()]
                current = VerilogModule(
                    name=start_match.group(1),
                    ports=[VerilogPort(name=name) for name in port_names],
                    start_line=header_line_no,
                    header_end_line=i + 1,
                )
            i += 1
            continue

        decl_match = _DIRECTION_DECL_RE.match(stripped)
        if decl_match:
            direction, width, names_part = decl_match.groups()
            width = (width or "").strip()
            ports_by_name = {port.name: port for port in current.ports}
            matched_any = False
            for raw_name in names_part.split(","):
                port = ports_by_name.get(raw_name.strip())
                if port is not None:
                    port.direction = direction.lower()
                    port.width = width
                    matched_any = True
            if matched_any:
                current.declaration_line_nos.append(i + 1)
            i += 1
            continue

        if _ENDMODULE_RE.match(stripped):
            current.end_line = i + 1
            modules.append(current)
            current = None
        i += 1

    return modules

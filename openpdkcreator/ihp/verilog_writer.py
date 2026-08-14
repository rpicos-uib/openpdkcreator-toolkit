"""Real Verilog port write-back -- same overall strategy as
``ihp/netlist_writer.py``: compares each module's *current* port list
(name + real direction + real width) against a **fresh re-parse** of
the same real original file. Unchanged -- the real original header and
every real declaration line are kept byte-for-byte, wherever they sit
in the module body (interleaved with comments/``wire`` declarations/
logic, as real IHP files do). Changed -- the header is regenerated as
one clean real line, and *every* real declaration line
(``VerilogModule.declaration_line_nos``, tracked at parse time) is
removed and replaced with one freshly-generated line per port at the
position of the first original declaration (right after the header if
there was none) -- real device/logic lines and comments in between are
never touched, only the declaration lines themselves move.

A module added this session (no real source position) can't be
written back, matching ``ihp/netlist_writer.py``'s own precedent --
only ports *within* an existing real module are structured-editable.
"""

from __future__ import annotations

from pathlib import Path

from . import text_utils
from . import verilog as verilog_mod


def _render_declaration(port: verilog_mod.VerilogPort) -> str:
    width_part = f"{port.width} " if port.width else ""
    return f"{port.direction} {width_part}{port.name};"


def _module_unchanged(module: verilog_mod.VerilogModule, fresh: verilog_mod.VerilogModule | None) -> bool:
    if fresh is None:
        return False
    current = [(port.name, port.direction, port.width) for port in module.ports]
    original = [(port.name, port.direction, port.width) for port in fresh.ports]
    return current == original


def render_verilog_file(original_path: Path, modules: list[verilog_mod.VerilogModule]) -> str:
    original_text = original_path.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines()
    fresh_by_start_line = {module.start_line: module for module in verilog_mod.find_modules(original_path)}

    output: list[str] = []
    cursor = 0

    for module in modules:
        if module.start_line == 0:
            continue  # a module added this session -- no real position to patch into, not attempted.

        header_start_idx = module.start_line - 1
        header_end_idx = module.header_end_line - 1
        end_idx = module.end_line - 1  # the real 'endmodule' line
        output.extend(original_lines[cursor:header_start_idx])

        fresh = fresh_by_start_line.get(module.start_line)
        unchanged = _module_unchanged(module, fresh)

        if unchanged:
            output.extend(original_lines[header_start_idx : header_end_idx + 1])
            output.extend(original_lines[header_end_idx + 1 : end_idx])
        else:
            port_names = ", ".join(port.name for port in module.ports)
            output.append(f"module {module.name} ({port_names});")

            decl_indices = sorted(line_no - 1 for line_no in module.declaration_line_nos)
            fresh_block = [_render_declaration(port) for port in module.ports if port.direction]
            pos = header_end_idx + 1
            inserted = False
            for idx in decl_indices:
                output.extend(original_lines[pos:idx])
                if not inserted:
                    output.extend(fresh_block)
                    inserted = True
                pos = idx + 1
            if not inserted:
                output.extend(fresh_block)
            output.extend(original_lines[pos:end_idx])

        output.append(original_lines[end_idx])  # the real 'endmodule' line
        cursor = end_idx + 1

    output.extend(original_lines[cursor:])
    return text_utils.join_preserving_trailing_newline(original_text, output)


def export_verilog_file(modules: list[verilog_mod.VerilogModule], original_path: Path, export_path: Path) -> None:
    text = render_verilog_file(original_path, modules)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

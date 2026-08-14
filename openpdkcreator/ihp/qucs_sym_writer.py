"""Real Qucs-S ``.sym`` (drawn-geometry) write-back for the in-memory
``QucsSymbolGeometry.ports`` this project's Symbols editor edits --
``x``/``y``/``type``/``angle``/``condition``, the same real fields
``ihp/qucs_sym.py`` itself parses; every other real drawing primitive
(``Line``/``Arc``/``Text``) is left completely untouched.

Same surgical, position-targeted discipline as every other writer
here: re-reads the *original* file fresh from disk and, using each
port's real source line number (``QucsPort.line_no``, tracked at
parse time), keeps every real non-port line verbatim, regenerating
only an edited port's own single real line -- preserving its own real
leading indentation and, when present, its real trailing hint comment
(``<!--D-->``, see ``ihp/qucs_sym.py``'s own docstring) exactly, since
that's real, useful annotation content, not this project's own
metadata to silently drop. A port deleted this session (present in
``QucsSymbolGeometry.all_parsed_port_line_nos`` but not in ``ports``)
has its original line omitted entirely; a port added this session
(``line_no == 0``) is appended as a new, real, valid, self-closing
``<PortSym .../>`` line at the very end of the file -- a real,
minimal, honest starting point (position ``0,0``, no condition), not a
claim of correct real placement (this project has no drawn-geometry
editor to place one sensibly, the same "structure, not graphics"
precedent as everywhere else).
"""

from __future__ import annotations

import re
from pathlib import Path

from . import qucs_sym as qucs_sym_mod
from . import text_utils

_LINE_RE = re.compile(r"^(\s*)<PortSym\b[^>]*?(\s*)/>(\s*(?:<!--\s*(.*?)\s*-->)?\s*)$")


def _port_unchanged(port: qucs_sym_mod.QucsPort, fresh: qucs_sym_mod.QucsPort | None) -> bool:
    if fresh is None:
        return False
    return (
        port.x == fresh.x and port.y == fresh.y and port.port_type == fresh.port_type
        and port.angle == fresh.angle and port.condition == fresh.condition
    )


def _render_port_line(port: qucs_sym_mod.QucsPort, original_line: str | None) -> str:
    """Only called for a genuinely *edited* (or brand-new) port --
    an unchanged real port keeps its own original line completely
    verbatim instead (see ``render_symbol_file``), so a real, per-
    attribute column-alignment convention some real files use (e.g.
    extra spaces before ``y=`` to line up with a sibling port's own
    ``x=``, confirmed real in ``Varicap.sym``) is never silently
    collapsed for a port nobody touched -- the very first correctness
    check (no-edit export must be byte-identical) caught this
    immediately against real data. An edited port's own regenerated
    line still preserves real indentation, the real, per-line-
    inconsistent choice of a space before the self-closing ``/>``, and
    any real trailing hint comment/whitespace, all confirmed real."""

    match = _LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else ""
    close_space = match.group(2) if match else ""
    trailer = match.group(3) if match else (f" <!--{port.hint}-->" if port.hint else "")

    attrs = f'x="{port.x}" y="{port.y}" type="{port.port_type}" angle="{port.angle}"'
    if port.condition:
        attrs += f' condition="{port.condition}"'
    return f"{indent}<PortSym {attrs}{close_space}/>{trailer}"


def render_symbol_file(original_path: Path, geometry: qucs_sym_mod.QucsSymbolGeometry) -> str:
    """Real, patched Qucs-S ``.sym`` text for *geometry*. With no
    edits at all, this is byte-identical to the real original file."""

    original_text = original_path.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines()
    fresh_by_line = {p.line_no: p for p in qucs_sym_mod.parse_symbol_geometry(original_path).ports}

    current_by_line = {port.line_no: port for port in geometry.ports if port.line_no}
    output: list[str] = []
    cursor = 0
    for orig_line_no in geometry.all_parsed_port_line_nos:
        line_idx = orig_line_no - 1
        output.extend(original_lines[cursor:line_idx])  # verbatim gap (Line/Arc/Text/comments)
        port = current_by_line.get(orig_line_no)
        if port is not None:
            fresh = fresh_by_line.get(orig_line_no)
            if _port_unchanged(port, fresh):
                output.append(original_lines[line_idx])  # untouched -- keep the real original line exactly.
            else:
                output.append(_render_port_line(port, original_lines[line_idx]))
        # else: this real port was deleted this session -- omit its original line entirely.
        cursor = line_idx + 1

    output.extend(original_lines[cursor:])

    for port in geometry.ports:
        if port.line_no == 0:
            output.append(_render_port_line(port, None))  # a port added this session

    text = text_utils.join_preserving_trailing_newline(original_text, output)
    return text_utils.restore_crlf_if_needed(original_path, text)


def export_symbol_file(geometry: qucs_sym_mod.QucsSymbolGeometry, export_path: Path) -> None:
    text = render_symbol_file(geometry.source_path, geometry)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

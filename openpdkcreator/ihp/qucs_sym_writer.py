"""Real Qucs-S ``.sym`` (drawn-geometry) write-back for the in-memory
``QucsSymbolGeometry`` this project's Symbols editor (table-based, and
the real graphical canvas, ``gui/geometry_canvas.py``) edits -- real
``PortSym`` ``x``/``y``/``type``/``angle``/``condition``, and now every
real drawing primitive too (``Line``/``Arc``/``Text``, each with its
own real fields); every real primitive kind's own line is otherwise
left completely untouched.

Same surgical, position-targeted discipline as every other writer
here: re-reads the *original* file fresh from disk and, using each
real primitive's own real source line number (tracked at parse time),
keeps every real *unedited* primitive's own line completely verbatim
-- only a genuinely edited (or brand-new) primitive's own line is
regenerated, preserving its own real leading indentation and the
real, per-line-inconsistent choice of a space before the self-closing
``/>`` (both confirmed real, coexisting across the actual downloaded
deck -- a naive always-regenerate approach silently collapsed a real,
confirmed column-alignment convention, e.g. ``Varicap.sym``'s own real
ports, caught by this project's own byte-identical check). A real,
trailing hint comment (``<!--D-->``) is preserved verbatim on an
edited ``PortSym`` line; confirmed real, no other real primitive kind
ever carries one. A primitive deleted this session has its original
line omitted entirely; one added this session (``line_no == 0``) is
appended as a new, real, valid, self-closing line at the very end of
the file.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import qucs_sym as qucs_sym_mod
from . import text_utils

_LINE_RE = re.compile(r"^(\s*)<PortSym\b[^>]*?(\s*)/>(\s*(?:<!--\s*(.*?)\s*-->)?\s*)$")
_TAG_LINE_RE = re.compile(r"^(\s*)<(Line|Arc|Text)\b[^>]*?(\s*)/>(\s*)$")


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


def _line_unchanged(line: qucs_sym_mod.QucsLine, fresh: qucs_sym_mod.QucsLine | None) -> bool:
    if fresh is None:
        return False
    return (
        line.x1 == fresh.x1 and line.y1 == fresh.y1 and line.x2 == fresh.x2 and line.y2 == fresh.y2
        and line.color == fresh.color and line.width == fresh.width and line.style == fresh.style
        and line.condition == fresh.condition
    )


def _render_line_tag(line: qucs_sym_mod.QucsLine, original_line: str | None) -> str:
    match = _TAG_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else ""
    close_space = match.group(3) if match else ""
    trailer = match.group(4) if match else ""

    attrs = f'x1="{line.x1}" y1="{line.y1}" x2="{line.x2}" y2="{line.y2}" color="{line.color}" width="{line.width}" style="{line.style}"'
    if line.condition:
        attrs += f' condition="{line.condition}"'
    return f"{indent}<Line {attrs}{close_space}/>{trailer}"


def _arc_unchanged(arc: qucs_sym_mod.QucsArc, fresh: qucs_sym_mod.QucsArc | None) -> bool:
    if fresh is None:
        return False
    return (
        arc.x == fresh.x and arc.y == fresh.y and arc.arc_width == fresh.arc_width and arc.height == fresh.height
        and arc.angle == fresh.angle and arc.sweep_len == fresh.sweep_len and arc.color == fresh.color
        and arc.width == fresh.width and arc.style == fresh.style and arc.condition == fresh.condition
    )


def _render_arc_tag(arc: qucs_sym_mod.QucsArc, original_line: str | None) -> str:
    match = _TAG_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else ""
    close_space = match.group(3) if match else ""
    trailer = match.group(4) if match else ""

    attrs = (
        f'x="{arc.x}" y="{arc.y}" arcWidth="{arc.arc_width}" height="{arc.height}" '
        f'angle="{arc.angle}" len="{arc.sweep_len}" color="{arc.color}" width="{arc.width}" style="{arc.style}"'
    )
    if arc.condition:
        attrs += f' condition="{arc.condition}"'
    return f"{indent}<Arc {attrs}{close_space}/>{trailer}"


def _text_unchanged(text_obj: qucs_sym_mod.QucsText, fresh: qucs_sym_mod.QucsText | None) -> bool:
    if fresh is None:
        return False
    return (
        text_obj.x == fresh.x and text_obj.y == fresh.y and text_obj.size == fresh.size
        and text_obj.color == fresh.color and text_obj.text == fresh.text and text_obj.condition == fresh.condition
    )


def _render_text_tag(text_obj: qucs_sym_mod.QucsText, original_line: str | None) -> str:
    match = _TAG_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else ""
    close_space = match.group(3) if match else ""
    trailer = match.group(4) if match else ""

    attrs = f'x="{text_obj.x}" y="{text_obj.y}" size="{text_obj.size}" color="{text_obj.color}" text="{text_obj.text}"'
    if text_obj.condition:
        attrs += f' condition="{text_obj.condition}"'
    return f"{indent}<Text {attrs}{close_space}/>{trailer}"


def render_symbol_file(original_path: Path, geometry: qucs_sym_mod.QucsSymbolGeometry) -> str:
    """Real, patched Qucs-S ``.sym`` text for *geometry*. With no
    edits at all, this is byte-identical to the real original file."""

    original_text = original_path.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines()
    fresh = qucs_sym_mod.parse_symbol_geometry(original_path)

    patches: list[tuple[int, str]] = []

    for entries, all_line_nos, fresh_entries, unchanged_fn, render_fn in (
        (geometry.ports, geometry.all_parsed_port_line_nos, fresh.ports, _port_unchanged, _render_port_line),
        (geometry.lines, geometry.all_parsed_line_line_nos, fresh.lines, _line_unchanged, _render_line_tag),
        (geometry.arcs, geometry.all_parsed_arc_line_nos, fresh.arcs, _arc_unchanged, _render_arc_tag),
        (geometry.texts, geometry.all_parsed_text_line_nos, fresh.texts, _text_unchanged, _render_text_tag),
    ):
        current_by_line = {e.line_no: e for e in entries if e.line_no}
        fresh_by_line = {e.line_no: e for e in fresh_entries}
        for orig_line_no in all_line_nos:
            entry = current_by_line.get(orig_line_no)
            if entry is None:
                continue  # deleted this session -- omit its original line entirely (handled via absence below).
            line_idx = orig_line_no - 1
            if unchanged_fn(entry, fresh_by_line.get(orig_line_no)):
                patches.append((orig_line_no, original_lines[line_idx]))
            else:
                patches.append((orig_line_no, render_fn(entry, original_lines[line_idx])))

    patched_by_line = dict(patches)
    all_real_line_nos = set(
        geometry.all_parsed_port_line_nos + geometry.all_parsed_line_line_nos
        + geometry.all_parsed_arc_line_nos + geometry.all_parsed_text_line_nos
    )

    output: list[str] = []
    for line_no, line in enumerate(original_lines, start=1):
        if line_no in all_real_line_nos:
            if line_no in patched_by_line:
                output.append(patched_by_line[line_no])
            # else: this real primitive was deleted this session -- omit its original line.
        else:
            output.append(line)

    for entries, render_fn in (
        (geometry.ports, _render_port_line), (geometry.lines, _render_line_tag),
        (geometry.arcs, _render_arc_tag), (geometry.texts, _render_text_tag),
    ):
        for entry in entries:
            if entry.line_no == 0:
                output.append(render_fn(entry, None))  # added this session

    text = text_utils.join_preserving_trailing_newline(original_text, output)
    return text_utils.restore_crlf_if_needed(original_path, text)


def export_symbol_file(geometry: qucs_sym_mod.QucsSymbolGeometry, export_path: Path) -> None:
    text = render_symbol_file(geometry.source_path, geometry)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

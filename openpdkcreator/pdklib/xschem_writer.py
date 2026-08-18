"""Real xschem ``.sym`` write-back for the in-memory ``XschemSymbol``
this project's Symbols editor (table-based Pins list, and the real
graphical canvas, ``gui/geometry_canvas.py``) edits -- pin name/
direction/**position**, and now every real drawing primitive's own
position too (``L``ines, ``A``rcs, ``T``ext, non-pin ``B``oxes).

**Surgical patching, not full regeneration**, the same discipline
``pdklib/lef_writer.py``'s own PIN/END patching established: re-reads the
*original* source file fresh from disk and, using each primitive's
real source line range (tracked at parse time), keeps every real,
*unedited* primitive's own line completely verbatim -- only a
genuinely edited (or brand-new) primitive's own line is regenerated,
the same "unchanged -> keep the real original line verbatim" real,
column-alignment-preserving discipline ``pdklib/qucs_sym_writer.py``
already established (a naive always-regenerate approach would
otherwise silently reformat real, untouched lines the moment *any*
other primitive changed).

Real ``B``/``T`` primitives can carry real properties beyond what this
project models as structured fields (a pin's own real ``goto=``/
``propag=``; a real, non-pin box's own real ``sim_pinnumber=``; a real
text's own real ``layer=``, confirmed in real data) -- these are
preserved character-for-character via the same real, quote-aware
key=value substitution ``_replace_kv`` already uses for pin name/
direction, applied here to the *position* fields' own header tokens
too, never touching the trailing props text except where a real,
modeled key (``name=``/``dir=``) is being patched. Real ``L``/``A``
primitives never carry any real props (confirmed real: every one across
the whole downloaded deck has an empty ``{}``), so their own header is
regenerated wholesale on a real edit with no props to preserve.

A primitive deleted this session (present in the matching
``all_parsed_*_ranges`` but not in the matching current list) has its
original text span omitted entirely; one added this session
(``start_line == 0``) is appended at the very end of the file.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import text_utils
from . import xschem as xschem_mod

_KV_RE = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')


def _fmt_num(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return repr(float(value))


def _kv_repr(value: str) -> str:
    if not value or any(ch.isspace() for ch in value) or '"' in value:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _replace_kv(text: str, key: str, new_value: str) -> str:
    pattern = re.compile(rf'\b{re.escape(key)}=("(?:[^"\\]|\\.)*"|\S+)')
    match = pattern.search(text)
    new_repr = _kv_repr(new_value)
    if match:
        return text[: match.start(1)] + new_repr + text[match.end(1) :]
    separator = " " if text.strip() else ""
    return f"{text}{separator}{key}={new_repr}"


def _split_simple_block(block_text: str, head_re: re.Pattern) -> tuple[str, int] | None:
    """For ``B``/``L``/``A`` (a single regex match ending in the
    props' own opening ``{``). Returns (props_interior, close_pos) or
    ``None`` if the real shape doesn't match (never observed)."""

    match = head_re.match(block_text)
    if not match:
        return None
    brace_pos = match.end() - 1
    return xschem_mod._scan_braced(block_text, brace_pos)


def _split_text_block(block_text: str) -> tuple[str, int] | None:
    head_match = xschem_mod._T_HEAD_RE.match(block_text)
    if not head_match:
        return None
    _text_content, after_text = xschem_mod._scan_braced(block_text, head_match.end() - 1)
    tail_match = xschem_mod._T_TAIL_RE.match(block_text, after_text)
    if not tail_match:
        return None
    return xschem_mod._scan_braced(block_text, tail_match.end() - 1)


def _render_pin_block(pin: xschem_mod.XschemPin, original_lines: list[str], fresh: xschem_mod.XschemPin | None) -> list[str]:
    header = f"B {pin.layer} {_fmt_num(pin.x1)} {_fmt_num(pin.y1)} {_fmt_num(pin.x2)} {_fmt_num(pin.y2)} {{"
    if not original_lines:
        return [f"{header}name={pin.name} dir={pin.direction}}}"]

    unchanged = fresh is not None and (
        pin.layer == fresh.layer and pin.x1 == fresh.x1 and pin.y1 == fresh.y1
        and pin.x2 == fresh.x2 and pin.y2 == fresh.y2 and pin.name == fresh.name and pin.direction == fresh.direction
    )
    if unchanged:
        return original_lines

    block_text = "\n".join(original_lines)
    split = _split_simple_block(block_text, xschem_mod._B_RE)
    if split is None:
        return original_lines
    interior, close_pos = split
    new_interior = _replace_kv(interior, "name", pin.name)
    new_interior = _replace_kv(new_interior, "dir", pin.direction)
    new_block = header + new_interior + block_text[close_pos - 1 :]
    return new_block.split("\n")


def _render_box_block(box: xschem_mod.XschemBox, original_lines: list[str], fresh: xschem_mod.XschemBox | None) -> list[str]:
    header = f"B {box.layer} {_fmt_num(box.x1)} {_fmt_num(box.y1)} {_fmt_num(box.x2)} {_fmt_num(box.y2)} {{"
    if not original_lines:
        return [f"{header}}}"]

    unchanged = fresh is not None and (
        box.layer == fresh.layer and box.x1 == fresh.x1 and box.y1 == fresh.y1
        and box.x2 == fresh.x2 and box.y2 == fresh.y2
    )
    if unchanged:
        return original_lines

    block_text = "\n".join(original_lines)
    split = _split_simple_block(block_text, xschem_mod._B_RE)
    if split is None:
        return original_lines
    _interior, close_pos = split  # real box props (e.g. sim_pinnumber=) preserved verbatim, untouched.
    new_block = header + block_text[close_pos - 1 :]
    return new_block.split("\n")


def _render_line_block(line: xschem_mod.XschemLine, original_lines: list[str], fresh: xschem_mod.XschemLine | None) -> list[str]:
    unchanged = fresh is not None and (
        line.layer == fresh.layer and line.x1 == fresh.x1 and line.y1 == fresh.y1
        and line.x2 == fresh.x2 and line.y2 == fresh.y2
    )
    if unchanged and original_lines:
        return original_lines
    return [f"L {line.layer} {_fmt_num(line.x1)} {_fmt_num(line.y1)} {_fmt_num(line.x2)} {_fmt_num(line.y2)} {{}}"]


def _render_arc_block(arc: xschem_mod.XschemArc, original_lines: list[str], fresh: xschem_mod.XschemArc | None) -> list[str]:
    unchanged = fresh is not None and (
        arc.layer == fresh.layer and arc.cx == fresh.cx and arc.cy == fresh.cy and arc.radius == fresh.radius
        and arc.start_angle == fresh.start_angle and arc.sweep_angle == fresh.sweep_angle
    )
    if unchanged and original_lines:
        return original_lines
    return [
        f"A {arc.layer} {_fmt_num(arc.cx)} {_fmt_num(arc.cy)} {_fmt_num(arc.radius)} "
        f"{_fmt_num(arc.start_angle)} {_fmt_num(arc.sweep_angle)} {{}}"
    ]


def _render_text_block(text_obj: xschem_mod.XschemText, original_lines: list[str], fresh: xschem_mod.XschemText | None) -> list[str]:
    header = (
        f"T {{{text_obj.text}}} {_fmt_num(text_obj.x)} {_fmt_num(text_obj.y)} "
        f"{text_obj.rot} {text_obj.flip} {_fmt_num(text_obj.hsize)} {_fmt_num(text_obj.vsize)} {{"
    )
    if not original_lines:
        return [f"{header}}}"]

    unchanged = fresh is not None and (
        text_obj.text == fresh.text and text_obj.x == fresh.x and text_obj.y == fresh.y
        and text_obj.rot == fresh.rot and text_obj.flip == fresh.flip
        and text_obj.hsize == fresh.hsize and text_obj.vsize == fresh.vsize
    )
    if unchanged:
        return original_lines

    block_text = "\n".join(original_lines)
    split = _split_text_block(block_text)
    if split is None:
        return original_lines
    _interior, close_pos = split  # real text props (e.g. layer=) preserved verbatim, untouched.
    new_block = header + block_text[close_pos - 1 :]
    return new_block.split("\n")


def render_sym_file(original_path: Path, symbol: xschem_mod.XschemSymbol) -> str:
    """Real, patched xschem ``.sym`` text for *symbol*. With no edits
    at all, this is byte-identical to the real original file."""

    original_text = original_path.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines()
    fresh = xschem_mod.parse_sym_file(original_path)

    patches: list[tuple[int, int, list[str] | None]] = []

    for entries, all_ranges, fresh_entries, render_fn in (
        (symbol.pins, symbol.all_parsed_pin_ranges, fresh.pins, _render_pin_block),
        (symbol.boxes, symbol.all_parsed_box_ranges, fresh.boxes, _render_box_block),
        (symbol.lines, symbol.all_parsed_line_ranges, fresh.lines, _render_line_block),
        (symbol.arcs, symbol.all_parsed_arc_ranges, fresh.arcs, _render_arc_block),
        (symbol.texts, symbol.all_parsed_text_ranges, fresh.texts, _render_text_block),
    ):
        current_by_start = {e.start_line: e for e in entries if e.start_line}
        fresh_by_start = {e.start_line: e for e in fresh_entries}
        for orig_start, orig_end in all_ranges:
            start_idx, end_idx = orig_start - 1, orig_end - 1
            obj = current_by_start.get(orig_start)
            if obj is not None:
                block = render_fn(obj, original_lines[start_idx : end_idx + 1], fresh_by_start.get(orig_start))
                patches.append((orig_start, orig_end, block))
            else:
                patches.append((orig_start, orig_end, None))  # deleted this session

    patches.sort(key=lambda p: p[0])

    output: list[str] = []
    cursor = 0
    for start_line, end_line, block in patches:
        start_idx, end_idx = start_line - 1, end_line - 1
        output.extend(original_lines[cursor:start_idx])  # verbatim gap
        if block is not None:
            output.extend(block)
        cursor = end_idx + 1

    output.extend(original_lines[cursor:])  # rest of the real file, verbatim

    for entries, render_fn in (
        (symbol.pins, _render_pin_block), (symbol.boxes, _render_box_block),
        (symbol.lines, _render_line_block), (symbol.arcs, _render_arc_block),
        (symbol.texts, _render_text_block),
    ):
        for entry in entries:
            if entry.start_line == 0:
                output.extend(render_fn(entry, [], None))  # added this session

    return text_utils.join_preserving_trailing_newline(original_text, output)


def export_sym_file(symbol: xschem_mod.XschemSymbol, export_path: Path) -> None:
    text = render_sym_file(symbol.source_path, symbol)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

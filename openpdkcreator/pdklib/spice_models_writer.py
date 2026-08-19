"""Writes real, valid ngspice ``.lib`` text back to disk for the
in-memory ``SpiceLibFile`` structure ``gui/spice_models_view.py``'s
Corners sub-tab edits -- scoped deliberately to ``.LIB ... .ENDL``
corner blocks only (the one editable domain there; real ``.model``/
``.subckt`` content stays completely untouched, matching every other
``pdklib/*_writer.py`` module's own "surgical patching, not full
regeneration" discipline in this project).

**Never overwrites the real, downloaded source file** -- the caller
(``openpdkcreator/export.py``) always writes the result to a separate
export tree, never back into ``data/``, the same real discipline every
other writer here follows.

**Surgical patching**: ``render_lib_file`` re-reads the *original*
source file fresh from disk and, using each corner's own real source
line range (tracked at parse time in ``pdklib/spice_models.py``),
keeps every real interior line of an unedited corner verbatim --
regenerating a fresh ``.LIB ... .ENDL`` block only for a corner whose
current, live ``name``/``params``/``includes`` no longer match what
its own captured original lines represent (``_reparse_corner_block``
re-derives that real, semantic content the same way ``parse_lib_file``
itself would, and the comparison ignores ``start_line``/``end_line``
themselves -- those describe *where* the corner sits, not what it
*is*). Everything else in the file -- real ``.model``/``.subckt``
content, comments, blank lines -- stays completely untouched, copied
verbatim. A corner deleted this session (present in
``SpiceLibFile.all_parsed_corner_ranges`` but not in
``SpiceLibFile.corners``) has its original text span omitted entirely;
a corner added this session (``start_line == 0``) gets a freshly-
generated block appended at the end of the file."""

from __future__ import annotations

from pathlib import Path

from . import spice_models as spice_mod
from . import text_utils


def _reparse_corner_block(lines: list[str]) -> tuple[str, list[tuple[str, str]], list[str]]:
    """The real ``(name, params, includes)`` a captured, real sequence
    of ``.LIB ... .ENDL`` block lines represents -- mirrors
    ``parse_lib_file``'s own corner-body logic exactly, just scoped to
    one already-isolated block instead of a whole file."""

    name = ""
    params: list[tuple[str, str]] = []
    includes: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        lib_match = spice_mod._LIB_RE.match(stripped)
        if lib_match:
            name = lib_match.group(1)
            continue
        if spice_mod._ENDL_RE.match(stripped):
            continue
        param_match = spice_mod._DOT_PARAM_RE.match(stripped)
        if param_match:
            parsed = spice_mod._parse_params(param_match.group(1))
            if parsed:
                params.append(parsed[0])
            continue
        include_match = spice_mod._INCLUDE_RE.match(stripped)
        if include_match:
            includes.append(include_match.group(1))
    return name, params, includes


def _render_param_value(value: str) -> str:
    """``parse_lib_file``'s own ``_parse_params`` strips a real
    param's surrounding quotes when reading it in (so a plain, bare
    numeric value and an intentionally-quoted one are stored the same,
    unquoted way -- see that function's own docstring) -- re-quoted
    here on the way back out whenever the bare value would otherwise
    no longer parse as the same single ngspice token, confirmed real
    and necessary: real corner params carry quoted formula
    expressions containing spaces (e.g.
    ``cap_carea_mm='agauss(1, 0.01, (mm_ok != 1 ? 0 : 1))'``,
    ``libs.tech/ngspice/models/capacitors_mod_mismatch.lib``) that
    would silently become a broken, multi-token statement without
    this."""

    if any(ch.isspace() for ch in value) and not (len(value) >= 2 and value[0] == value[-1] and value[0] in "'\""):
        return f"'{value}'"
    return value


def _render_corner_block(corner: spice_mod.SpiceCorner) -> list[str]:
    """A fresh, real ``.LIB ... .ENDL`` block for *corner*."""

    lines = [f".LIB {corner.name}"]
    for key, value in corner.params:
        lines.append(f".param {key} = {_render_param_value(value)}")
    for include in corner.includes:
        lines.append(f".include {include}")
    lines.append(f".ENDL {corner.name}")
    return lines


def render_lib_file(original_path: Path, parsed: spice_mod.SpiceLibFile) -> str:
    """Real, patched ``.lib`` text for *parsed* (the current, possibly
    corner-edited in-memory structure originally parsed from
    *original_path*). With no edits at all, this is byte-identical to
    the real original file."""

    original_text = original_path.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines()
    output: list[str] = []
    cursor = 0  # next un-emitted original line index (0-based)

    current_corners_by_start = {c.start_line: c for c in parsed.corners if c.start_line != 0}
    for orig_start, orig_end in parsed.all_parsed_corner_ranges:
        start_idx, end_idx = orig_start - 1, orig_end - 1
        output.extend(original_lines[cursor:start_idx])  # verbatim gap (comments/models/subckts/blank lines)
        corner = current_corners_by_start.get(orig_start)
        if corner is not None:
            original_block = original_lines[start_idx:end_idx + 1]
            if _reparse_corner_block(original_block) == (corner.name, corner.params, corner.includes):
                output.extend(original_block)
            else:
                output.extend(_render_corner_block(corner))
        # else: this real corner was deleted this session -- omit its original text entirely.
        cursor = end_idx + 1

    output.extend(original_lines[cursor:])  # everything after the last real corner, verbatim

    new_blocks: list[str] = []
    for corner in parsed.corners:
        if corner.start_line == 0:
            if new_blocks:
                new_blocks.append("")
            new_blocks.extend(_render_corner_block(corner))
    if new_blocks:
        if output and output[-1].strip():
            output.append("")
        output.extend(new_blocks)

    return text_utils.join_preserving_trailing_newline(original_text, output)


def export_lib_file(parsed: spice_mod.SpiceLibFile, export_path: Path) -> None:
    text = render_lib_file(parsed.source_path, parsed)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

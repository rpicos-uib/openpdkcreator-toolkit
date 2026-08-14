"""Writes real, valid LEF text back to disk for the in-memory
``LefFile``/``LefMacro``/``LefPin`` structures this project's LEF tab/
By Cell tab edit -- the first concrete piece of "native write-back
serialization" (see README's own Future Work), scoped deliberately to
LEF pins only (name/direction/use -- the only structured-editable LEF
content; port geometry stays untouched, see ``gui/pin_editor.py``).

**Never overwrites the real, downloaded source file** -- the caller
(``openpdkcreator/export.py``) always writes the result to a separate
export tree, never back into ``data/``, matching this whole project's
"never silently corrupt or overwrite a real, third-party foundry file"
discipline (the same reason ``file_view_dialog``'s raw-text Save asks
for confirmation, and DRC Rules/Magic Types/LEF pins persist through
``project_io.py``'s own separate ``saves/`` format rather than into the
real ``.drc``/``.tech`` files).

**Surgical patching, not full regeneration**: this project's own LEF
model doesn't capture every real LEF construct (PROPERTY declarations,
port RECT *coordinates* -- only a rect *count* is tracked, not real
geometry -- FOREIGN, SHAPE, and, confirmed by a real, direct
byte-identical-export test failing against IHP's own real data,
``ANTENNAMODEL``, which sits between a pin's header and its ``PORT``
block on plenty of real pins). Regenerating a whole pin from only the
fields this parser *does* model would have silently dropped that real
content -- so instead, ``render_lef_file`` re-reads the *original*
source file fresh from disk (always still pristine, since this module
never writes there) and, using each pin's real source line range
(tracked at parse time in ``ihp/lef.py``), keeps **every** real
interior line of an existing pin verbatim -- ``ANTENNAMODEL``, ``PORT``
sub-blocks, anything else -- substituting only the specific
``DIRECTION``/``USE`` lines (the two fields this project actually
edits), and only the pin's own name in its ``PIN``/``END`` header and
trailer. Everything else in the file -- tech ``LAYER`` blocks, ``SITE``
defs, ``VIA``/``ViaRULE`` bodies, other macros, comments, blank lines,
an ``OBS`` block -- stays completely untouched, copied verbatim. A pin
deleted this session (present in ``LefMacro.all_parsed_pin_ranges`` but
not in ``LefMacro.pins``) has its original text span omitted entirely;
a pin added this session (``start_line == 0``) gets a freshly-generated
block (no real interior to preserve -- there was never a real pin
there) inserted just before the macro's own real ``END`` line.
"""

from __future__ import annotations

from pathlib import Path

from . import lef as lef_mod


def _leading_whitespace(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _render_pin_block(pin: lef_mod.LefPin, indent: str, original_pin_lines: list[str]) -> list[str]:
    """*original_pin_lines*: the pin's own real, original line range
    (``PIN name`` through ``END name``, inclusive) from the freshly
    re-read source file -- empty for a brand-new pin with no real
    source position (nothing to preserve).

    For an existing pin, every real interior line (``PORT`` sub-blocks,
    ``ANTENNAMODEL``, anything else this parser doesn't model) is kept
    verbatim; only ``DIRECTION``/``USE`` lines are substituted (or
    inserted, if the current value is set but no such line existed --
    or dropped, if the field was cleared to empty), and only the pin's
    own name changes in the header/trailer, matching a real rename."""

    if not original_pin_lines:
        lines = [f"{indent}PIN {pin.name}"]
        if pin.direction:
            lines.append(f"{indent}  DIRECTION {pin.direction} ;")
        if pin.use:
            lines.append(f"{indent}  USE {pin.use} ;")
        lines.append(f"{indent}END {pin.name}")
        return lines

    header_indent = _leading_whitespace(original_pin_lines[0])
    trailer_indent = _leading_whitespace(original_pin_lines[-1])
    interior = original_pin_lines[1:-1]

    new_interior: list[str] = []
    direction_written = use_written = False
    for line in interior:
        content = line.split("#", 1)[0].strip()
        body = content[:-1].strip() if content.endswith(";") else content
        keyword = body.split()[0].upper() if body.split() else ""
        if keyword == "DIRECTION":
            if pin.direction:
                new_interior.append(f"{_leading_whitespace(line)}DIRECTION {pin.direction} ;")
                direction_written = True
            continue
        if keyword == "USE":
            if pin.use:
                new_interior.append(f"{_leading_whitespace(line)}USE {pin.use} ;")
                use_written = True
            continue
        new_interior.append(line)

    prefix: list[str] = []
    if pin.direction and not direction_written:
        prefix.append(f"{header_indent}  DIRECTION {pin.direction} ;")
    if pin.use and not use_written:
        prefix.append(f"{header_indent}  USE {pin.use} ;")

    return (
        [f"{header_indent}PIN {pin.name}"] + prefix + new_interior
        + [f"{trailer_indent}END {pin.name}"]
    )


def render_lef_file(original_path: Path, parsed: lef_mod.LefFile) -> str:
    """Real, patched LEF text for *parsed* (the current, possibly
    pin-edited in-memory structure originally parsed from
    *original_path*). With no edits at all, this is byte-identical to
    the real original file -- a real, direct correctness check (see
    ``main.py export-lef``'s own verification)."""

    original_lines = original_path.read_text(encoding="utf-8", errors="replace").splitlines()
    output: list[str] = []
    cursor = 0  # next un-emitted original line index (0-based)

    for macro in parsed.macros:
        if macro.start_line == 0:
            # A macro added this session (no real source position) --
            # whole-macro editing isn't attempted this pass, only pins
            # within an existing macro; skip defensively rather than
            # guess where a new macro's real text should go.
            continue

        macro_start_idx = macro.start_line - 1
        macro_end_idx = macro.end_line - 1  # the macro's own 'END name' line

        output.extend(original_lines[cursor:macro_start_idx])  # verbatim, up to this macro
        output.append(original_lines[macro_start_idx])  # 'MACRO name' line, verbatim

        current_pins_by_start = {pin.start_line: pin for pin in macro.pins if pin.start_line != 0}
        pin_cursor = macro_start_idx + 1
        for orig_start, orig_end in macro.all_parsed_pin_ranges:
            start_idx, end_idx = orig_start - 1, orig_end - 1
            output.extend(original_lines[pin_cursor:start_idx])  # verbatim gap (comments/OBS/blank lines)
            pin = current_pins_by_start.get(orig_start)
            if pin is not None:
                indent = _leading_whitespace(original_lines[start_idx])
                output.extend(_render_pin_block(pin, indent, original_lines[start_idx:end_idx + 1]))
            # else: this real pin was deleted this session -- omit its original text entirely.
            pin_cursor = end_idx + 1

        output.extend(original_lines[pin_cursor:macro_end_idx])  # rest of the macro body, verbatim

        for pin in macro.pins:
            if pin.start_line == 0:
                # A pin added this session -- no real PORT to preserve.
                output.extend(_render_pin_block(pin, "  ", []))

        output.append(original_lines[macro_end_idx])  # macro's own 'END name' line, verbatim
        cursor = macro_end_idx + 1

    output.extend(original_lines[cursor:])  # everything after the last macro, verbatim
    return "\n".join(output) + "\n"


def export_lef_file(parsed: lef_mod.LefFile, export_path: Path) -> None:
    text = render_lef_file(parsed.source_path, parsed)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

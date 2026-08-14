"""Real Magic Types write-back -- the third and final piece of native
write-back serialization (after ``ihp/lef_writer.py`` and
``ihp/drc_writer.py``), same surgical, position-targeted discipline:
re-reads the real *original* ``.tech`` file fresh from disk (always
pristine, since export never writes to ``data/``) and patches only the
real lines belonging to the currently-editable domain -- **Types**, a
list + form pane, the only Magic Tech domain with a real form at all
(see ``gui/magic_tech_view.py``'s own docstring). Every other real
section (planes/contacts/aliases/styles/compose/connect/cifoutput/
everything ``magic_tech.py`` doesn't parse) is copied verbatim,
untouched -- there's no editor for them, so nothing to write back.

Each real type occupies exactly one real line (``[-]plane
name,alias1,alias2``, no block structure to navigate, unlike LEF's
``PIN``/``MACRO`` or DRC's multi-line ``.output()`` calls) --
``ihp/magic_tech.py``'s own ``TypeEntry.line_no``/
``MagicTechnology.all_parsed_type_line_nos`` (tracked at parse time,
only when safely mappable back to real file line numbers -- see
``_safe_prefix_line_count``'s own docstring) are used exactly the way
``ihp/lef.py``'s ``LefPin.start_line``/``LefMacro.
all_parsed_pin_ranges`` are: a deleted type's original line is omitted
entirely; a brand-new type (``line_no == 0``) is appended just before
the real ``types`` section's own closing ``end`` line; an existing
type's line is regenerated fresh from its current in-memory fields
(name/aliases/obsolete/plane), preserving only its original
indentation -- there's no unmodeled per-type content to lose here
(unlike a LEF pin's real ``PORT``/``ANTENNAMODEL`` data), since a real
type line's entire real content is exactly the fields this project
already models.

If ``MagicTechnology.types_section_start_line`` is ``0`` (no real,
safely-mappable ``types`` section was found in this exact file), the
file is returned completely unmodified -- refusing to guess is safer
than patching the wrong real position.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import magic_tech as magic_tech_mod

_TYPE_LINE_RE = re.compile(r"^(\s*)(-)?(\S+)(\s+)(\S.*)$")


def _render_type_line(entry: magic_tech_mod.TypeEntry, original_line: str | None) -> str:
    """Preserves the real, original indentation and plane/names
    separator whitespace exactly -- a real, confirmed case (IHP's own
    GDS technology) column-aligns 102 real type lines with more than
    one space there, which a fixed single-space reconstruction would
    have silently collapsed even when nothing was actually edited (the
    very first correctness check -- no-edit export must be
    byte-identical -- caught this immediately against real data, the
    same way the LEF/DRC writers' own formatting bugs were caught).
    ``original_line`` is ``None`` for a brand-new type (New Type, no
    real original line to preserve anything from)."""

    match = _TYPE_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else ""
    separator = match.group(4) if match else " "
    prefix = "-" if entry.obsolete else ""
    names = ",".join([entry.canonical_name, *entry.aliases])
    return f"{indent}{prefix}{entry.plane}{separator}{names}"


def render_tech_file(original_path: Path, tech: magic_tech_mod.MagicTechnology) -> str:
    original_lines = original_path.read_text(encoding="utf-8", errors="replace").splitlines()

    if tech.types_section_start_line == 0 or tech.types_section_end_line == 0:
        return "\n".join(original_lines) + "\n"

    start_idx = tech.types_section_start_line - 1  # the 'types' keyword line itself
    end_idx = tech.types_section_end_line - 1  # the section's own 'end' line

    current_by_line = {entry.line_no: entry for entry in tech.types if entry.line_no}

    output = original_lines[: start_idx + 1]  # everything up to and including 'types', verbatim
    cursor = start_idx + 1
    for orig_line_no in tech.all_parsed_type_line_nos:
        line_idx = orig_line_no - 1
        output.extend(original_lines[cursor:line_idx])  # verbatim gap (comments/blank lines)
        entry = current_by_line.get(orig_line_no)
        if entry is not None:
            output.append(_render_type_line(entry, original_lines[line_idx]))
        # else: this real type was deleted this session -- omit its original line entirely.
        cursor = line_idx + 1

    output.extend(original_lines[cursor:end_idx])  # rest of the section body, verbatim

    for entry in tech.types:
        if entry.line_no == 0:
            output.append(_render_type_line(entry, None))  # a type added this session

    output.append(original_lines[end_idx])  # the section's own 'end' line, verbatim
    output.extend(original_lines[end_idx + 1 :])  # everything after, verbatim
    return "\n".join(output) + "\n"


def export_tech_file(tech: magic_tech_mod.MagicTechnology, export_path: Path) -> None:
    text = render_tech_file(tech.source_path, tech)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

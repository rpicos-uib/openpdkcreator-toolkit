"""Real Magic write-back -- the third and final piece of native
write-back serialization (after ``pdklib/lef_writer.py`` and
``pdklib/drc_writer.py``), same surgical, position-targeted discipline:
re-reads the real *original* ``.tech`` file fresh from disk (always
pristine, since export never writes to ``data/``) and patches only the
real lines belonging to a currently-editable domain -- **Types**,
**Planes**, **Contacts**, **Aliases**, **Styles**, **Compose**, and
**Connect**, the seven Magic Tech domains with a real form (see
``gui/magic_tech_view.py``'s own docstring). Every other real section
(cifoutput/cifinput/drc/extract/everything ``magic_tech.py`` doesn't
parse) is copied verbatim, untouched -- there's no editor for them, so
nothing to write back; deliberately bounded, not attempted for all
nine remaining real sub-tabs at once (see README's own Future Work
note on the remaining gap).

Each real entry in all seven editable domains occupies exactly one
real line (``[-]plane name,alias1,alias2`` for a type; ``NAME, SHORT``
for a plane; ``TYPE LAYER1 LAYER2`` for a contact; ``NAME MEMBERS`` for
an alias; ``TYPE_NAME STYLE1 STYLE2 ...`` for a style; ``VERB ARG1 ARG2
ARG3`` for a compose statement; ``TYPES_A TYPES_B`` for a connect rule
-- no block structure to navigate, unlike LEF's ``PIN``/``MACRO`` or
DRC's multi-line ``.output()`` calls), so all seven share one generic
patch routine, ``_render_section_patch``, parameterized by a per-domain
line-render function -- rather than seven near-duplicated copies of
the same real positional-patch logic.
``pdklib/magic_tech.py``'s own ``TypeEntry.line_no``/``PlaneEntry.
line_no``/``ContactEntry.line_no``/``AliasEntry.line_no``/
``StyleEntry.line_no``/``ComposeStatement.line_no``/``ConnectRule.
line_no`` (tracked at parse time, only when safely mappable back to
real file line numbers -- see ``_safe_prefix_line_count``'s own
docstring) are used exactly the way ``pdklib/lef.py``'s ``LefPin.
start_line``/``LefMacro.all_parsed_pin_ranges`` are: a deleted entry's
original line is omitted entirely; a brand-new entry (``line_no ==
0``) is appended just before its own real section's closing ``end``
line; an existing entry's line is regenerated fresh from its current
in-memory fields, preserving only its original indentation/separator
whitespace -- there's no unmodeled per-entry content to lose in any of
the seven (unlike a LEF pin's real ``PORT``/``ANTENNAMODEL`` data),
since a real entry line's entire real content is exactly the fields
this project already models. Styles' own real section additionally
carries one, real non-entry ``styletype NAME`` header line right after
its opening keyword -- ``_render_section_patch``'s existing "copy any
untracked line verbatim" gap logic already handles it for free, since
``pdklib/magic_tech.py``'s own ``_parse_style_line`` never adds it to
``all_line_nos`` in the first place. Compose/Connect need no such
special case -- both are genuinely flat, no non-entry header line of
their own.

All seven real sections (confirmed real, not assumed: ``planes``
83-98, ``types`` 104-260, ``contact`` 266-298, ``aliases`` 304-382,
``styles`` 388-529, ``compose`` 535-591, ``connect`` 597-621 in IHP's
own real ``ihp-sg13g2.tech``) sit well before the file's own first
real ``include`` line, so all seven share the exact same real
``safe_through`` boundary already established for Types alone. If a
given domain's own section start/end line is ``0`` (not found at a
safely-mappable position), that one domain's real lines are simply
left untouched -- refusing to guess is safer than patching the wrong
real position -- while the other six still patch normally.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import magic_tech as magic_tech_mod
from . import text_utils

_TYPE_LINE_RE = re.compile(r"^(\s*)(-)?(\S+)(\s+)(\S.*)$")
_PLANE_LINE_RE = re.compile(r"^(\s*)(\S+)(\s*,\s*)(\S.*)$")
_CONTACT_LINE_RE = re.compile(r"^(\s*)(\S+)(\s+)(\S+)(\s+)(\S+)\s*$")
_ALIAS_LINE_RE = re.compile(r"^(\s*)(\S+)(\s+)(\S.*)$")
_STYLE_LINE_RE = re.compile(r"^(\s*)(\S+)(\s+)(\S.*)$")
_COMPOSE_LINE_RE = re.compile(r"^(\s*)(\S+)(\s+)(\S+)(\s+)(\S+)(\s+)(\S+)\s*$")
_CONNECT_LINE_RE = re.compile(r"^(\s*)(\S+)(\s+)(\S.*)$")


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


def _render_plane_line(entry: magic_tech_mod.PlaneEntry, original_line: str | None) -> str:
    match = _PLANE_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else ""
    separator = match.group(3) if match else ", "
    return f"{indent}{entry.name}{separator}{entry.short_code}"


def _render_contact_line(entry: magic_tech_mod.ContactEntry, original_line: str | None) -> str:
    match = _CONTACT_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else ""
    sep1 = match.group(3) if match else " "
    sep2 = match.group(5) if match else " "
    return f"{indent}{entry.contact_type}{sep1}{entry.layer1}{sep2}{entry.layer2}"


def _render_alias_line(entry: magic_tech_mod.AliasEntry, original_line: str | None) -> str:
    match = _ALIAS_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else ""
    separator = match.group(3) if match else " "
    return f"{indent}{entry.name}{separator}{entry.members_raw}"


def _render_style_line(entry: magic_tech_mod.StyleEntry, original_line: str | None) -> str:
    """Unlike the other four (fixed token count, or a single free-text
    ``members_raw``/rest field), a real style line's own style-name
    list is variable-length *and* real files genuinely column-align
    it with more than one space between names (confirmed real: IHP's
    own ``nfet ntransistor    ntransistor_stripes``) -- the same real
    class of formatting this project's own no-edit-is-byte-identical
    guarantee already exists to protect (see ``_render_type_line``'s
    own docstring for the first real case this bit). So: if the style
    list itself is genuinely unchanged from the original line, its
    real original inter-name whitespace is preserved exactly, not
    collapsed to one space; only a real, deliberate change to the list
    gets freshly, normally spaced -- the same "diff first, only
    reformat what actually changed" discipline ``pdklib/
    liberty_writer.py`` already established for its own per-field
    writes."""

    match = _STYLE_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else ""
    separator = match.group(3) if match else " "
    rest_original = match.group(4) if match else None
    if rest_original is not None and rest_original.split() == entry.style_names:
        style_names_text = rest_original
    else:
        style_names_text = " ".join(entry.style_names)
    return f"{indent}{entry.type_name}{separator}{style_names_text}"


def _render_compose_line(entry: magic_tech_mod.ComposeStatement, original_line: str | None) -> str:
    """A real compose-section line always has exactly four tokens
    (verb + 3 args), so -- unlike Styles' own variable-length list --
    the real per-token separators can just be captured and always
    reused verbatim, the same real approach ``_render_contact_line``
    already uses for its own fixed 3-token shape; no diff-first
    handling needed, since there's no variable-length blob for extra
    real spacing to hide inside."""

    match = _COMPOSE_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else ""
    sep1 = match.group(3) if match else " "
    sep2 = match.group(5) if match else " "
    sep3 = match.group(7) if match else " "
    return f"{indent}{entry.verb}{sep1}{entry.arg1}{sep2}{entry.arg2}{sep3}{entry.arg3}"


def _render_connect_line(entry: magic_tech_mod.ConnectRule, original_line: str | None) -> str:
    match = _CONNECT_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else ""
    separator = match.group(3) if match else " "
    return f"{indent}{entry.types_a}{separator}{entry.types_b}"


def _render_section_patch(
    original_lines: list[str], start_line: int, end_line: int,
    entries: list, all_line_nos: list[int], render_fn,
) -> list[str]:
    """One real section's own patched lines, from its own real keyword
    line through its own real closing ``end`` (both inclusive,
    verbatim) -- shared by all four editable domains, see this
    module's own docstring."""

    start_idx = start_line - 1
    end_idx = end_line - 1
    current_by_line = {entry.line_no: entry for entry in entries if entry.line_no}

    output = [original_lines[start_idx]]  # the section's own keyword line, verbatim
    cursor = start_idx + 1
    for orig_line_no in all_line_nos:
        line_idx = orig_line_no - 1
        output.extend(original_lines[cursor:line_idx])  # verbatim gap (comments/blank lines)
        entry = current_by_line.get(orig_line_no)
        if entry is not None:
            output.append(render_fn(entry, original_lines[line_idx]))
        # else: this real entry was deleted this session -- omit its original line entirely.
        cursor = line_idx + 1
    output.extend(original_lines[cursor:end_idx])

    for entry in entries:
        if entry.line_no == 0:
            output.append(render_fn(entry, None))  # an entry added this session

    output.append(original_lines[end_idx])  # the section's own 'end' line, verbatim
    return output


def render_tech_file(original_path: Path, tech: magic_tech_mod.MagicTechnology) -> str:
    original_text = original_path.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines()

    candidate_sections = [
        (tech.planes_section_start_line, tech.planes_section_end_line, tech.planes, tech.all_parsed_plane_line_nos, _render_plane_line),
        (tech.types_section_start_line, tech.types_section_end_line, tech.types, tech.all_parsed_type_line_nos, _render_type_line),
        (tech.contacts_section_start_line, tech.contacts_section_end_line, tech.contacts, tech.all_parsed_contact_line_nos, _render_contact_line),
        (tech.aliases_section_start_line, tech.aliases_section_end_line, tech.aliases, tech.all_parsed_alias_line_nos, _render_alias_line),
        (tech.styles_section_start_line, tech.styles_section_end_line, tech.styles, tech.all_parsed_style_line_nos, _render_style_line),
        (tech.compose_section_start_line, tech.compose_section_end_line, tech.compose, tech.all_parsed_compose_line_nos, _render_compose_line),
        (tech.connect_section_start_line, tech.connect_section_end_line, tech.connect, tech.all_parsed_connect_line_nos, _render_connect_line),
    ]
    active_sections = sorted(
        (s for s in candidate_sections if s[0] and s[1]), key=lambda s: s[0],
    )

    if not active_sections:
        return text_utils.join_preserving_trailing_newline(original_text, original_lines)

    output: list[str] = []
    cursor = 0
    for start_line, end_line, entries, all_line_nos, render_fn in active_sections:
        start_idx = start_line - 1
        output.extend(original_lines[cursor:start_idx])  # verbatim gap before this section
        output.extend(_render_section_patch(original_lines, start_line, end_line, entries, all_line_nos, render_fn))
        cursor = end_line  # end_line - 1 is the 0-indexed 'end' line, already appended; next gap starts right after.

    output.extend(original_lines[cursor:])  # everything after the last patched section, verbatim
    return text_utils.join_preserving_trailing_newline(original_text, output)


def export_tech_file(tech: magic_tech_mod.MagicTechnology, export_path: Path) -> None:
    text = render_tech_file(tech.source_path, tech)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

"""Real Magic write-back -- the third and final piece of native
write-back serialization (after ``pdklib/lef_writer.py`` and
``pdklib/drc_writer.py``), same surgical, position-targeted discipline:
re-reads the real *original* ``.tech`` file fresh from disk (always
pristine, since export never writes to ``data/``) and patches only the
real lines belonging to a currently-editable domain -- **Types**,
**Planes**, **Contacts**, **Aliases**, **Styles**, **Compose**,
**Connect**, **cifinput**'s own two flat sub-structures (ignored
layers, layer hints), **cifoutput**'s own flat, editable-in-place
``calma`` lines, and **extract**'s own four flat sub-structures,
``ExtractMiscStatement`` (``contact``/``devresist``/``antenna``/
``disconnect``/``substrate``), ``ExtractPlaneOrder`` (``planeorder``),
``ExtractResist`` (``resist``), and ``ExtractCapCoefficient`` (the four
``default*`` directives), the Magic Tech domains with a real form (see
``gui/magic_tech_view.py``'s own docstring). Every other real section
(cifinput's own recipe blocks/drc/``device``/everything else
``magic_tech.py`` doesn't parse) is copied verbatim, untouched --
there's no editor for them, so nothing to write back; deliberately
bounded, not attempted for every remaining real sub-tab at once (see
README's own Future Work note on the remaining gap).

Each real entry in every flat editable domain occupies exactly one
real line (``[-]plane name,alias1,alias2`` for a type; ``NAME, SHORT``
for a plane; ``TYPE LAYER1 LAYER2`` for a contact; ``NAME MEMBERS`` for
an alias; ``TYPE_NAME STYLE1 STYLE2 ...`` for a style; ``VERB ARG1 ARG2
ARG3`` for a compose statement; ``TYPES_A TYPES_B`` for a connect rule;
``ignore NAME``/``calma NAME LAYER DATATYPE`` for cifinput's own two;
``calma LAYER DATATYPE`` for cifoutput; ``DIRECTIVE ARG1 ARG2 ...`` for
an extract-section misc statement -- no block structure to navigate,
unlike LEF's ``PIN``/``MACRO`` or DRC's multi-line ``.output()``
calls), so all of them share one generic patch routine,
``_render_section_patch``, parameterized by a per-domain line-render
function -- rather than near-duplicated copies of the same real
positional-patch logic.
``pdklib/magic_tech.py``'s own ``TypeEntry.line_no``/``PlaneEntry.
line_no``/``ContactEntry.line_no``/``AliasEntry.line_no``/
``StyleEntry.line_no``/``ComposeStatement.line_no``/``ConnectRule.
line_no``/``CifInputIgnoredLayer.line_no``/``CifInputLayerHint.
line_no``/``CifOutputLayerMapping.line_no``/``ExtractMiscStatement.
line_no``/``ExtractPlaneOrder.line_no``/``ExtractResist.line_no``/
``ExtractCapCoefficient.line_no`` (tracked at parse time, only when
safely mappable back to
real file line numbers -- see ``_safe_prefix_line_count``'s own
docstring) are used exactly the way
``pdklib/lef.py``'s ``LefPin.start_line``/``LefMacro.
all_parsed_pin_ranges`` are: a deleted entry's original line is
omitted entirely; a brand-new entry (``line_no == 0``) is appended
just before its own real section's closing ``end`` line; an existing
entry's line is regenerated fresh from its current in-memory fields,
preserving only its original indentation/separator whitespace --
there's no unmodeled per-entry content to lose in any domain here
(unlike a LEF pin's real ``PORT``/``ANTENNAMODEL`` data), since a real
entry line's entire real content is exactly the fields this project
already models. Styles' own real section additionally carries one,
real non-entry ``styletype NAME`` header line right after its opening
keyword -- ``_render_section_patch``'s existing "copy any untracked
line verbatim" gap logic already handles it for free, since
``pdklib/magic_tech.py``'s own ``_parse_style_line`` never adds it to
``all_line_nos`` in the first place. Compose/Connect need no such
special case -- both are genuinely flat, no non-entry header line of
their own. cifoutput's own section carries plenty of real non-entry
content too (``style``/``scalefactor``/``options``/``gridlimit``,
every real ``layer``/``templayer`` NAME line, and every real geometry
op -- ``shrink``/``or``/``bloat-all``/...) -- all handled the same
generic way, since ``_parse_cifoutput_layers_with_lines`` (see that
module's own docstring) only ever recognizes a real ``calma`` line as
an entry, everything else falls through as a verbatim gap for free,
no special-casing needed there either. **cifoutput's own real entries
are also, deliberately, never created or deleted** -- see
``CifOutputLayerMapping``'s own docstring for why (a real ``calma``
line means nothing without the real geometry recipe leading up to it,
which this project doesn't author) -- so ``render_fn(entry, None)``
(the "brand-new entry" branch) is real, defensive code here, never
actually exercised in practice.

**cifinput's own ignored-layers and layer-hints tables share one real
``cifinput``...``end`` section with each other** (and with every real
``layer``/``templayer`` recipe block, still read-only) -- unlike every
other editable domain above, which each own their own exclusive
section. Patching them independently, one full section-rewrite per
sub-structure, would silently discard whichever one ran second (it
would restart from the real *original* lines and not see the first
one's own edits). So ``_render_section_patch`` takes a real list of
*groups* -- ``(entries, all_line_nos, render_fn)`` tuples -- and merges
every group's own real line numbers into one combined pass over the
shared section, each dispatched to its own real render function;
every other, single-group domain above just wraps its one real tuple
in a one-element list, unchanged in every other respect.

**cifinput and cifoutput are also, structurally, a genuinely different
case from every other domain here**: neither one's real content lives
in ``ihp-sg13g2.tech`` at all -- both are spliced in from their own
separate real files, ``ihp-sg13g2-cifin.tech``/``ihp-sg13g2-cifout.
tech``, via ``include``. When parsed as part of ``ihp-sg13g2.tech``'s
own combined view, both domains' real lines sit well past that file's
own ``safe_through`` boundary (the first real ``include`` line), so
every ``line_no``/section bound here correctly comes back ``0`` --
refusing to guess, not a bug -- and this write-back correctly leaves
both untouched there. Each fragment file is also independently
parseable as its own real file (``find_tech_files`` globs both, same
as every other real ``.tech`` file, confirmed to have no real
``include`` line of its own), so *that* parse's own content **is**
safely, fully mappable, and write-back for *that* real
``tech.source_path`` patches it correctly, using this exact same
machinery -- no new "write to a different file than the one being
viewed" mechanism needed, since each real file is always parsed (and
written back to) independently already. The only real gap this closed
was visibility: neither fragment file has a real ``tech``/``version``
header of its own, so both used to be silently filtered out of the
Technology picker entirely (see ``gui/magic_tech_view.py``'s own
docstring for the real fallback-naming fix).

**extract's own four flat sub-structures, ``ExtractMiscStatement``,
``ExtractPlaneOrder``, ``ExtractResist``, and ``ExtractCapCoefficient``,
are, structurally, the same "spliced in from a separate real file"
case as cifinput/cifoutput above** -- real content lives in
``ihp-sg13g2-extract.tech``, included into ``ihp-sg13g2.tech`` --
**and share one real ``extract``...``end`` section with each other and
with the one remaining, still-read-only extract content** (``device``
lines, real ``variants (...)`` corner-scoping lines, comments), the
same "one section, more than one independently-tracked group" shape
cifinput's own ignored-layers/layer-hints tables already established:
all of that untouched content simply never matches
``_parse_extract_misc_line``/``_parse_plane_order_line``/
``_parse_resist_line``/``_parse_cap_coefficient_line``, so it falls
through ``_render_section_patch``'s existing "copy any untracked line
verbatim" gap logic for free. **A real ``contact``, ``resist``, or
cap-coefficient line can also repeat across more than one real
``variants`` corner block with a different real value each time**
(confirmed real for all three) -- handled the same way
``CifOutputLayerMapping``'s own repeated ``DNWELL`` rows already are:
each real occurrence is its own real line, independently patched by
its own real ``line_no``, with no attempt to resolve which corner a
given row belongs to. ``planeorder`` has no such wrinkle -- confirmed
real to sit entirely before the section's own first real
``variants (...)`` line, so every real name is unique, one row each.
**A real formatting wrinkle unique to cap-coefficients**: unlike
``resist``/``planeorder``'s own fixed two-token shape,
``ExtractCapCoefficient``'s own trailing ``args``/``values`` is a
variable-length blob (per-directive token count), so its own render
function uses the same diff-first "reuse the original text verbatim if
genuinely unchanged" approach ``_render_style_line``/
``_render_extract_misc_line`` already established, rather than the
always-reuse-captured-separators approach the two fixed-token domains
use.

All real sections (confirmed real, not assumed: ``planes`` 83-98,
``types`` 104-260, ``contact`` 266-298, ``aliases`` 304-382, ``styles``
388-529, ``compose`` 535-591, ``connect`` 597-621 in IHP's own real
``ihp-sg13g2.tech``; ``cifinput`` 20-1519 in the separate, real
``ihp-sg13g2-cifin.tech``; ``cifoutput`` 25-1875 in the separate, real
``ihp-sg13g2-cifout.tech``; ``extract`` 23-1282 in the separate, real
``ihp-sg13g2-extract.tech`` -- all three fragment files, when parsed as
that own real file directly) sit well before their own real file's own
first real ``include`` line (none, in any of the three fragment files'
own case), so all of them share the exact same real ``safe_through``
boundary already established for Types alone. If a given domain's own
section start/end line is ``0`` (not found at a safely-mappable
position), that one domain's real lines are simply left untouched --
refusing to guess is safer than patching the wrong real position --
while every other domain still patches normally.
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
_CIFINPUT_IGNORE_LINE_RE = re.compile(r"^(\s*)ignore(\s+)(\S+)(\s*)$")
_CIFINPUT_HINT_LINE_RE = re.compile(r"^(\s*)calma(\s+)(\S+)(\s+)(\S+)(\s+)(\S+)(\s*)$")
_CIFOUTPUT_CALMA_LINE_RE = re.compile(r"^(\s*)calma(\s+)(\S+)(\s+)(\S+)(\s*)$")
_EXTRACT_MISC_LINE_RE = re.compile(r"^(\s*)(\S+)(\s+)(\S.*)$")
_PLANEORDER_LINE_RE = re.compile(r"^(\s*)planeorder(\s+)(\S+)(\s+)(\d+)\s*$")
_RESIST_LINE_RE = re.compile(r"^(\s*)resist(\s+)(\S+)(\s+)(-?\d+)\s*$")
_EXTRACT_CAP_COEFF_LINE_RE = re.compile(r"^(\s*)(\S+)(\s+)(\S.*)$")


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


def _render_cifinput_ignore_line(entry: magic_tech_mod.CifInputIgnoredLayer, original_line: str | None) -> str:
    match = _CIFINPUT_IGNORE_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else " "
    separator = match.group(2) if match else " "
    trailing = match.group(4) if match else ""
    return f"{indent}ignore{separator}{entry.name}{trailing}"


def _render_cifinput_hint_line(entry: magic_tech_mod.CifInputLayerHint, original_line: str | None) -> str:
    """Fixed three-token shape after the real ``calma`` keyword (name,
    layer, datatype), same real always-reuse-original-separators
    approach as ``_render_contact_line``/``_render_compose_line`` --
    safe here too, no variable-length blob to hide extra real spacing
    inside. A real trailing-whitespace case was found and fixed the
    same way (some real ``calma`` lines in ``ihp-sg13g2-cifin.tech``
    end with a real trailing space, e.g. ``calma DIFFFILL 1 22 `` --
    confirmed real, caught by this project's own no-edit-is-
    byte-identical check, not assumed correct)."""

    match = _CIFINPUT_HINT_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else " "
    sep0 = match.group(2) if match else " "
    sep1 = match.group(4) if match else " "
    sep2 = match.group(6) if match else " "
    trailing = match.group(8) if match else ""
    datatype_text = "*" if entry.gds_datatype is None else str(entry.gds_datatype)
    return f"{indent}calma{sep0}{entry.name}{sep1}{entry.gds_layer}{sep2}{datatype_text}{trailing}"


def _render_cifoutput_calma_line(entry: magic_tech_mod.CifOutputLayerMapping, original_line: str | None) -> str:
    """Fixed two-token shape after the real ``calma`` keyword (layer,
    datatype) -- ``entry.name`` is deliberately never written here (it
    lives on a real, different, preceding ``layer``/``templayer`` line
    this domain doesn't edit -- see ``CifOutputLayerMapping``'s own
    docstring for why: editable in place only, no New/Delete).
    ``original_line`` is never actually ``None`` in real, driven use
    here (this domain has no way to create a brand-new entry, so
    every real ``line_no`` is always non-zero) -- the fallback still
    exists for the same defensive-coding reason every other render
    function here has one, not because it's reachable. Real trailing
    whitespace preserved explicitly, same real, confirmed case as
    ``_render_cifinput_hint_line`` (some real ``calma`` lines in
    ``ihp-sg13g2-cifout.tech`` end with one too)."""

    match = _CIFOUTPUT_CALMA_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else "\t"
    sep0 = match.group(2) if match else " "
    sep1 = match.group(4) if match else " "
    trailing = match.group(6) if match else ""
    return f"{indent}calma{sep0}{entry.gds_layer}{sep1}{entry.gds_datatype}{trailing}"


def _render_extract_misc_line(entry: magic_tech_mod.ExtractMiscStatement, original_line: str | None) -> str:
    """A real extract-misc line's own argument list is sometimes
    column-aligned with more than one space (confirmed real: IHP's own
    ``contact alldiffcont   17000``) -- the same real formatting
    ``_render_style_line`` already guards for a variable-length list.
    If the args are genuinely unchanged from the original line, its
    real original whitespace is preserved verbatim; only a real,
    deliberate edit gets freshly, normally single-spaced."""

    match = _EXTRACT_MISC_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else " "
    separator = match.group(3) if match else " "
    rest_original = match.group(4) if match else None
    if rest_original is not None and tuple(rest_original.split()) == entry.args:
        rest = rest_original
    else:
        rest = " ".join(entry.args)
    return f"{indent}{entry.directive}{separator}{rest}"


def _render_plane_order_line(entry: magic_tech_mod.ExtractPlaneOrder, original_line: str | None) -> str:
    """Fixed two-token shape after the real ``planeorder`` keyword
    (name, order) -- confirmed real to never carry the multi-space
    column alignment `contact`'s own lines sometimes do, so the same
    always-reuse-original-separators approach `_render_contact_line`/
    `_render_compose_line` use is safe here too, no diff-first handling
    needed."""

    match = _PLANEORDER_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else " "
    sep0 = match.group(2) if match else " "
    sep1 = match.group(4) if match else " "
    return f"{indent}planeorder{sep0}{entry.name}{sep1}{entry.order}"


def _render_resist_line(entry: magic_tech_mod.ExtractResist, original_line: str | None) -> str:
    """Fixed two-token shape after the real ``resist`` keyword
    (layer_spec, value) -- unlike ``planeorder``, real ``resist`` lines
    do carry multi-space/tab column alignment (confirmed real: IHP's
    own ``resist (allm5)/metal5    \t  88``), but the same
    always-reuse-original-separators approach still works here: the
    separator is captured per-line from that exact original line, so
    any real alignment survives even when unedited, the same way
    ``_render_contact_line`` already handles a fixed-token-count line
    with no diff-first logic needed."""

    match = _RESIST_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else " "
    sep0 = match.group(2) if match else " "
    sep1 = match.group(4) if match else " "
    return f"{indent}resist{sep0}{entry.layer_spec}{sep1}{entry.milliohms_per_square}"


def _render_cap_coefficient_line(entry: magic_tech_mod.ExtractCapCoefficient, original_line: str | None) -> str:
    """A real cap-coefficient line's own trailing ``args``/``values``
    tokens are also sometimes column-aligned with more than one space
    (confirmed real: IHP's own
    ``defaultoverlap     allpoly active pwell well  87.433``) -- the
    same diff-first approach ``_render_style_line``/
    ``_render_extract_misc_line`` already use for a variable-length
    blob: if the real, parsed ``args``/``values`` are genuinely
    unchanged from the original line, its real original whitespace is
    preserved verbatim; only a real, deliberate edit gets freshly,
    normally single-spaced (values via plain ``str()``, since there's
    no real original formatting worth preserving for a value that
    actually changed)."""

    match = _EXTRACT_CAP_COEFF_LINE_RE.match(original_line) if original_line is not None else None
    indent = match.group(1) if match else " "
    separator = match.group(3) if match else " "
    rest_original = match.group(4) if match else None
    unchanged = False
    if rest_original is not None:
        parts = rest_original.split()
        arg_count = len(entry.args)
        orig_args = tuple(parts[:arg_count])
        try:
            orig_values = tuple(float(token) for token in parts[arg_count:])
        except ValueError:
            orig_values = None
        unchanged = orig_args == entry.args and orig_values == entry.values
    if unchanged:
        rest = rest_original
    else:
        tokens = list(entry.args) + [str(v) for v in entry.values]
        rest = " ".join(tokens)
    return f"{indent}{entry.directive}{separator}{rest}"


def _render_section_patch(
    original_lines: list[str], start_line: int, end_line: int, groups: list[tuple[list, list[int], object]],
) -> list[str]:
    """One real section's own patched lines, from its own real keyword
    line through its own real closing ``end`` (both inclusive,
    verbatim) -- shared by every editable domain, see this module's
    own docstring. *groups*: one ``(entries, all_line_nos, render_fn)``
    tuple per real, independently-tracked sub-structure sharing this
    section (almost always exactly one; cifinput's own ignored-layers
    and layer-hints tables share two) -- merged into one real, combined
    pass over the shared real lines rather than patched independently,
    which would silently discard whichever group ran second."""

    start_idx = start_line - 1
    end_idx = end_line - 1
    current_by_line = {}
    for entries, _group_line_nos, render_fn in groups:
        for entry in entries:
            if entry.line_no:
                current_by_line[entry.line_no] = (entry, render_fn)
    all_line_nos = sorted({
        line_no for _entries, group_line_nos, _render_fn in groups for line_no in group_line_nos
    })

    output = [original_lines[start_idx]]  # the section's own keyword line, verbatim
    cursor = start_idx + 1
    for orig_line_no in all_line_nos:
        line_idx = orig_line_no - 1
        output.extend(original_lines[cursor:line_idx])  # verbatim gap (comments/blank lines/other groups)
        hit = current_by_line.get(orig_line_no)
        if hit is not None:
            entry, render_fn = hit
            output.append(render_fn(entry, original_lines[line_idx]))
        # else: this real entry was deleted this session -- omit its original line entirely.
        cursor = line_idx + 1
    output.extend(original_lines[cursor:end_idx])

    for entries, _group_line_nos, render_fn in groups:
        for entry in entries:
            if entry.line_no == 0:
                output.append(render_fn(entry, None))  # an entry added this session

    output.append(original_lines[end_idx])  # the section's own 'end' line, verbatim
    return output


def render_tech_file(original_path: Path, tech: magic_tech_mod.MagicTechnology) -> str:
    original_text = original_path.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines()

    candidate_sections = [
        (tech.planes_section_start_line, tech.planes_section_end_line, [(tech.planes, tech.all_parsed_plane_line_nos, _render_plane_line)]),
        (tech.types_section_start_line, tech.types_section_end_line, [(tech.types, tech.all_parsed_type_line_nos, _render_type_line)]),
        (tech.contacts_section_start_line, tech.contacts_section_end_line, [(tech.contacts, tech.all_parsed_contact_line_nos, _render_contact_line)]),
        (tech.aliases_section_start_line, tech.aliases_section_end_line, [(tech.aliases, tech.all_parsed_alias_line_nos, _render_alias_line)]),
        (tech.styles_section_start_line, tech.styles_section_end_line, [(tech.styles, tech.all_parsed_style_line_nos, _render_style_line)]),
        (tech.compose_section_start_line, tech.compose_section_end_line, [(tech.compose, tech.all_parsed_compose_line_nos, _render_compose_line)]),
        (tech.connect_section_start_line, tech.connect_section_end_line, [(tech.connect, tech.all_parsed_connect_line_nos, _render_connect_line)]),
        (
            tech.cifinput_section_start_line, tech.cifinput_section_end_line,
            [
                (tech.cifinput_ignored_layers, tech.all_parsed_cifinput_ignore_line_nos, _render_cifinput_ignore_line),
                (tech.cifinput_layer_hints, tech.all_parsed_cifinput_hint_line_nos, _render_cifinput_hint_line),
            ],
        ),
        (
            tech.cifoutput_section_start_line, tech.cifoutput_section_end_line,
            [(tech.cif_layers, tech.all_parsed_cif_layer_line_nos, _render_cifoutput_calma_line)],
        ),
        (
            tech.extract_section_start_line, tech.extract_section_end_line,
            [
                (tech.extract_misc, tech.all_parsed_extract_misc_line_nos, _render_extract_misc_line),
                (tech.extract_plane_order, tech.all_parsed_extract_plane_order_line_nos, _render_plane_order_line),
                (tech.extract_resist, tech.all_parsed_extract_resist_line_nos, _render_resist_line),
                (
                    tech.extract_cap_coefficients, tech.all_parsed_extract_cap_coefficient_line_nos,
                    _render_cap_coefficient_line,
                ),
            ],
        ),
    ]
    active_sections = sorted(
        (s for s in candidate_sections if s[0] and s[1]), key=lambda s: s[0],
    )

    if not active_sections:
        return text_utils.join_preserving_trailing_newline(original_text, original_lines)

    output: list[str] = []
    cursor = 0
    for start_line, end_line, groups in active_sections:
        start_idx = start_line - 1
        output.extend(original_lines[cursor:start_idx])  # verbatim gap before this section
        output.extend(_render_section_patch(original_lines, start_line, end_line, groups))
        cursor = end_line  # end_line - 1 is the 0-indexed 'end' line, already appended; next gap starts right after.

    output.extend(original_lines[cursor:])  # everything after the last patched section, verbatim
    return text_utils.join_preserving_trailing_newline(original_text, output)


def export_tech_file(tech: magic_tech_mod.MagicTechnology, export_path: Path) -> None:
    text = render_tech_file(tech.source_path, tech)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

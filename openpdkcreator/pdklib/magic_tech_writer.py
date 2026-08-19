"""Real Magic write-back -- the third and final piece of native
write-back serialization (after ``pdklib/lef_writer.py`` and
``pdklib/drc_writer.py``), same surgical, position-targeted discipline:
re-reads the real *original* ``.tech`` file fresh from disk (always
pristine, since export never writes to ``data/``) and patches only the
real lines belonging to a currently-editable domain -- **Types**,
**Planes**, **Contacts**, **Aliases**, **Styles**, **Compose**,
**Connect**, **cifinput**'s own three sub-structures (ignored layers,
layer hints, and recipe blocks' own header fields --
``CifInputRecipeBlock``, the one real *ranged* one, its own real op
content still read-only), **cifoutput**'s own flat, editable-in-place
``calma`` lines, **extract**'s own five sub-structures --
``ExtractMiscStatement`` (``contact``/``devresist``/``antenna``/
``disconnect``/``substrate``), ``ExtractPlaneOrder`` (``planeorder``),
``ExtractResist`` (``resist``), ``ExtractCapCoefficient`` (the four
``default*`` directives, all four flat/single-line), and
``ExtractDevice`` (``device``, ranged) -- and **drc**'s own
``MagicAngleCheck`` (``angles``, ranged), ``MagicDrcCheck``
(``width``/``spacing``/``maxwidth``, ranged), and
``MagicDrcMiscStatement`` (``surround``/``edge4way``/``widespacing``/
``cifmaxwidth``/``cifwidth``/``cifspacing``/``area``/
``exact_overlap``/``overhang``/``extend``/``rect_only``/``cifarea``/
``no_overlap``, ranged -- see that dataclass's own docstring, in
``pdklib/magic_tech.py``, for exactly why one shared, raw/positional
shape covers all thirteen), the Magic Tech domains with a real form
(see ``gui/magic_tech_view.py``'s own docstring).
Every other real section (cifinput's own recipe blocks' own real op
content/everything else ``magic_tech.py`` doesn't parse) is copied
verbatim, untouched -- there's no editor for them, so nothing to write
back; deliberately bounded, not attempted for every remaining real
sub-tab at once (see README's own Future Work note on the remaining
gap).

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
``cifinput``...``end`` section with each other, and now with recipe
blocks' own header fields too** -- unlike every other editable domain
above, which each own their own exclusive section. Patching them
independently, one full section-rewrite per sub-structure, would
silently discard whichever one ran second (it would restart from the
real *original* lines and not see the first one's own edits). So
``_render_section_patch`` takes a real list of *groups* --
``(entries, all_line_nos, render_fn)`` tuples for a flat, single-line
sub-structure, plus a separate real list of *range_groups* --
``(entries, all_ranges, render_fn)`` tuples for a ranged one like
``CifInputRecipeBlock`` -- and merges every group's own real lines
(and every range group's own real spans) into one combined pass over
the shared section, each dispatched to its own real render function;
every other, single-group domain above just wraps its one real tuple
in a one-element list, unchanged in every other respect. A recipe
block's own real op content stays completely untouched either way --
``_parse_cifinput_recipes_with_lines`` never claims those lines as
part of any group's own tracked line numbers, so they fall through as
an ordinary, verbatim gap the same as any other real, unrecognized
content sharing this section.

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

**extract's own five sub-structures -- ``ExtractMiscStatement``,
``ExtractPlaneOrder``, ``ExtractResist``, ``ExtractCapCoefficient``,
and ``ExtractDevice`` -- are, structurally, the same "spliced in from
a separate real file" case as cifinput/cifoutput above** -- real
content lives in ``ihp-sg13g2-extract.tech``, included into
``ihp-sg13g2.tech`` -- **and all five share one real
``extract``...``end`` section**, the same "one section, more than one
independently-tracked group" shape cifinput's own ignored-layers/
layer-hints tables already established: every real line that isn't
one of these five constructs (cap-coefficient directives aside, the
only real extract-section content left over is comments and real
``variants (...)`` corner-scoping lines -- see this module's own
docstring for exactly what's parsed) simply never matches any of
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
use. **``ExtractDevice`` is a real, genuinely different shape from the
other four**: its own real entries can span more than one real
physical line (a trailing ``\\`` continuation, confirmed real for 5 of
the real 50 entries) -- tracked by a real ``(start_line, end_line)``
range instead of a single ``line_no``, and merged into the same
combined pass via ``_render_section_patch``'s own *range_groups*
parameter (see that function's own docstring for exactly how a
ranged group is merged alongside flat, single-line ones).
``drc``'s own ``MagicAngleCheck`` (``angles``) is the same real ranged
shape (one of the real 17 entries, ``allm7``, also wraps this way),
sharing ``ihp-sg13g2-drc.tech``'s own real ``drc``...``end`` section
with the still-read-only ``width``/``spacing``/``maxwidth``
statements -- see ``MagicAngleCheck``'s own docstring
(``pdklib/magic_tech.py``) for why those three aren't editable yet.

All real sections (confirmed real, not assumed: ``planes`` 83-98,
``types`` 104-260, ``contact`` 266-298, ``aliases`` 304-382, ``styles``
388-529, ``compose`` 535-591, ``connect`` 597-621 in IHP's own real
``ihp-sg13g2.tech``; ``cifinput`` 20-1519 in the separate, real
``ihp-sg13g2-cifin.tech``; ``cifoutput`` 25-1875 in the separate, real
``ihp-sg13g2-cifout.tech``; ``extract`` 23-1282 in the separate, real
``ihp-sg13g2-extract.tech``; ``drc`` 23-970 in the separate, real
``ihp-sg13g2-drc.tech`` -- all four fragment files, when parsed as
that own real file directly) sit well before their own real file's own
first real ``include`` line (none, in any of the four fragment files'
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
from . import numeric
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


_CIFINPUT_RECIPE_HEADER_RE = re.compile(r"^(\s*)(layer|templayer)(\s+)(\S+)(\s+)(\S+)\s*$")


def _render_cifinput_recipe_range(entry: magic_tech_mod.CifInputRecipeBlock, original_lines: list[str] | None) -> list[str]:
    """cifinput's own recipe blocks -- a real *ranged* domain, but one
    where the range's own trailing content (every real op line) is
    never edited here (see ``CifInputRecipeBlock``'s own docstring for
    why), only the real header line (``name``/``kind_text``/
    ``base_layer``) is. This makes the real "preserve verbatim if
    unchanged" comparison simpler than every other ranged domain's own:
    it only ever needs to check the header line itself, never the
    trailing op lines -- if the header is genuinely unchanged, the
    *entire* real range (header plus every real op line, verbatim,
    including whatever real trailing blank/comment padding sits before
    the next real boundary) is returned untouched; if the header
    changed, only that first real line is regenerated, and every real
    op line after it is still carried through completely verbatim
    (they're never touched either way, so there's nothing to lose)."""

    if original_lines is not None:
        header_match = _CIFINPUT_RECIPE_HEADER_RE.match(original_lines[0])
        if header_match is not None:
            indent, kind, sep1, name, sep2, base = header_match.groups()
            if (kind == entry.kind_text) and (name == entry.name) and (base == entry.base_layer):
                return list(original_lines)
            new_header = f"{indent}{entry.kind_text}{sep1}{entry.name}{sep2}{entry.base_layer}"
            return [new_header, *original_lines[1:]]
    return [f" {entry.kind_text} {entry.name} {entry.base_layer}"]


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
        parsed_orig_values = [numeric.parse_number(token) for token in parts[arg_count:]]
        orig_values = None if any(v is None for v in parsed_orig_values) else tuple(parsed_orig_values)
        unchanged = orig_args == entry.args and orig_values == entry.values
    if unchanged:
        rest = rest_original
    else:
        tokens = list(entry.args) + [str(v) for v in entry.values]
        rest = " ".join(tokens)
    return f"{indent}{entry.directive}{separator}{rest}"


def _join_ranged_lines(lines: list[str]) -> str:
    """Real backslash-continuation joining for any real, ranged
    (possibly multi-line) entry's own real line span -- the same real
    "strip trailing '\\', join with a single space" shape
    ``pdklib/magic_tech.py``'s own ``_join_backslash_continuations``
    uses, reimplemented locally rather than reaching into that
    module's own private helper across files. Shared by every real
    ranged domain (``ExtractDevice``, ``MagicAngleCheck``'s own
    ``allm7`` wrap) rather than one copy each, since the real
    continuation shape itself is identical across all of them."""

    pieces = []
    for line in lines:
        stripped = line.strip()
        pieces.append(stripped[:-1].rstrip() if stripped.endswith("\\") else stripped)
    return " ".join(pieces)


def _render_device_range(entry: magic_tech_mod.ExtractDevice, original_lines: list[str] | None) -> list[str]:
    """The one real extract-section domain whose own real entries can
    span more than one real physical line (a trailing ``\\``
    continuation, confirmed real for 5 of the real 50 entries -- every
    real ``msubcircuit`` MOSFET). If the real, parsed
    ``devclass``/``model``/``type_name``/``rest`` are genuinely
    unchanged from the original range, that range's own real lines
    (wrapping, tab indentation, and all) are preserved completely
    verbatim; a real, deliberate edit collapses to one freshly
    formatted line -- no attempt is made to re-wrap edited content back
    across multiple real lines the way the original author chose to,
    the same "don't guess further" real formatting discipline every
    other regenerated (not preserved) line in this module already
    follows."""

    if original_lines is not None:
        parts = _join_ranged_lines(original_lines).split()
        if len(parts) >= 4 and parts[0] == "device":
            orig = (parts[1], parts[2], parts[3], tuple(parts[4:]))
            if orig == (entry.devclass, entry.model, entry.type_name, entry.rest):
                return list(original_lines)
    tokens = [entry.devclass, entry.model, entry.type_name, *entry.rest]
    return [" device " + " ".join(tokens)]


_ANGLES_LINE_RE = re.compile(r'^\s*angles\s+(\S+)\s+(\d+)\s+(?:\S+\s+)*"([^"]*)"\s*$')


def _render_angle_range(entry: magic_tech_mod.MagicAngleCheck, original_lines: list[str] | None) -> list[str]:
    """The first real drc-section domain made editable (see
    ``MagicAngleCheck``'s own docstring for why it was safe before
    ``width``/``spacing``/``maxwidth``) -- and, like ``ExtractDevice``,
    a real *ranged* domain: one of the real 17 ``angles`` lines
    (``allm7``) wraps across two real physical lines via a trailing
    ``\\`` continuation. Same real "preserve verbatim if genuinely
    unchanged, else collapse to one fresh line" approach
    ``_render_device_range`` already established."""

    if original_lines is not None:
        joined = _join_ranged_lines(original_lines)
        match = _ANGLES_LINE_RE.match(joined)
        if match is not None:
            layer, degrees, message = match.groups()
            if (layer, int(degrees), message) == (entry.layer, entry.degrees, entry.message):
                return list(original_lines)
    return [f' angles {entry.layer} {entry.degrees} "{entry.message}"']


# Same real, empirically-confirmed file-unit-to-micron factor
# pdklib/magic_tech.py's own _DRC_VALUE_TO_MICRONS uses -- duplicated
# locally rather than reaching into that module's own private constant
# across files, same reasoning _join_ranged_lines already documents.
_DRC_VALUE_TO_MICRONS = 1000.0
_WIDTH_LINE_RE = re.compile(r'^\s*width\s+(\S+)\s+(-?\d+)\s+((?:\S+\s+)*)"([^"]*)"\s*$')
_SPACING_LINE_RE = re.compile(r'^\s*spacing\s+(\S+)\s+(\S+)\s+(-?\d+)\s+((?:\S+\s+)*)"([^"]*)"\s*$')
_MAXWIDTH_LINE_RE = re.compile(r'^\s*maxwidth\s+(\S+)\s+(-?\d+)\s+((?:\S+\s+)*)"([^"]*)"\s*$')


def _reparse_drc_check_range(joined: str):
    """Real, local re-parse of a joined drc-check range's own text,
    for diff-first comparison only -- mirrors
    ``pdklib/magic_tech.py``'s own ``_parse_drc_check_text``,
    reimplemented locally rather than reaching into that module's own
    private helper across files. Returns
    ``(check_type, layer_args, value_int, filler, message)`` or
    ``None``."""

    if joined.startswith("width "):
        match = _WIDTH_LINE_RE.match(joined)
        if match is None:
            return None
        layers_raw, value, filler, message = match.groups()
        return "width", [layers_raw.split(",")], int(value), filler.strip(), message
    if joined.startswith("spacing "):
        match = _SPACING_LINE_RE.match(joined)
        if match is None:
            return None
        layer1, layer2, value, filler, message = match.groups()
        return "spacing", [layer1.split(","), layer2.split(",")], int(value), filler.strip(), message
    if joined.startswith("maxwidth "):
        match = _MAXWIDTH_LINE_RE.match(joined)
        if match is None:
            return None
        layers_raw, value, filler, message = match.groups()
        return "maxwidth", [layers_raw.split(",")], int(value), filler.strip(), message
    return None


def _render_drc_check_range(entry: magic_tech_mod.MagicDrcCheck, original_lines: list[str] | None) -> list[str]:
    """``width``/``spacing``/``maxwidth`` -- the drc section's second
    real ranged domain, and a real, genuinely messier shape than
    ``angles``/``ExtractDevice``: a real backslash continuation here
    can split anywhere (mid layer-list, before the real ``mode``/
    exception-list filler, or right before the quoted message), not
    always right before the same fixed trailing content, so every
    entry is range-tracked regardless of whether it happens to wrap
    (see ``MagicDrcCheck.start_line``'s own docstring). Same real
    "preserve verbatim if genuinely unchanged, else collapse to one
    fresh line" approach every other ranged domain here uses -- the
    real, empirically-confirmed ``/1000`` value scaling is reversed
    here (multiply back to the real raw file integer), the one real
    place in this module that conversion runs in reverse."""

    if original_lines is not None:
        joined = _join_ranged_lines(original_lines)
        parsed = _reparse_drc_check_range(joined)
        if parsed is not None:
            current_value_int = round(entry.value_um * _DRC_VALUE_TO_MICRONS)
            if parsed == (entry.check_type, entry.layer_args, current_value_int, entry.filler_raw, entry.message):
                return list(original_lines)
    value_int = round(entry.value_um * _DRC_VALUE_TO_MICRONS)
    layers_part = " ".join(",".join(group) for group in entry.layer_args)
    filler_part = f" {entry.filler_raw}" if entry.filler_raw else ""
    return [f' {entry.check_type} {layers_part} {value_int}{filler_part} "{entry.message}"']


def _render_drc_misc_range(entry: magic_tech_mod.MagicDrcMiscStatement, original_lines: list[str] | None) -> list[str]:
    """The drc section's third real ranged domain -- every real
    keyword besides ``width``/``spacing``/``maxwidth``/``angles`` (see
    ``MagicDrcMiscStatement``'s own docstring). Kept fully raw and
    positional, so comparison is a plain whitespace-split token match
    rather than a per-directive regex the way
    ``_reparse_drc_check_range`` needs -- one shared shape for all
    thirteen real keywords, same reason the dataclass itself is one
    shared shape. Same real "preserve verbatim if genuinely unchanged,
    else collapse to one fresh line" approach every other ranged
    domain here uses."""

    if original_lines is not None:
        joined = _join_ranged_lines(original_lines)
        parts = joined.split()
        if parts and parts[0] == entry.directive and tuple(parts[1:]) == entry.args:
            return list(original_lines)
    return [" " + " ".join([entry.directive, *entry.args])]


def _render_section_patch(
    original_lines: list[str], start_line: int, end_line: int, groups: list[tuple[list, list[int], object]],
    range_groups: list[tuple[list, list[tuple[int, int]], object]] = (),
) -> list[str]:
    """One real section's own patched lines, from its own real keyword
    line through its own real closing ``end`` (both inclusive,
    verbatim) -- shared by every editable domain, see this module's
    own docstring. *groups*: one ``(entries, all_line_nos, render_fn)``
    tuple per real, independently-tracked, single-physical-line
    sub-structure sharing this section (almost always exactly one;
    cifinput's own ignored-layers and layer-hints tables share two) --
    merged into one real, combined pass over the shared real lines
    rather than patched independently, which would silently discard
    whichever group ran second. *range_groups*: the same real idea,
    generalized for a sub-structure whose own real entries can span
    more than one real physical line (``ExtractDevice``'s own real
    backslash-continued lines) -- one ``(entries, all_ranges,
    render_fn)`` tuple per such group, *all_ranges* a list of real
    ``(start_line, end_line)`` tuples (both inclusive) rather than
    single line numbers; *render_fn* here takes ``(entry,
    original_lines_slice_or_None)`` and returns a real list of lines,
    not a single line, since an unchanged multi-line real entry's own
    original wrapping/indentation is preserved verbatim across however
    many real lines it spans."""

    start_idx = start_line - 1
    end_idx = end_line - 1
    current_by_line = {}
    for entries, _group_line_nos, render_fn in groups:
        for entry in entries:
            if entry.line_no:
                current_by_line[entry.line_no] = (entry, render_fn)
    current_by_start: dict[int, tuple] = {}
    original_end_by_start: dict[int, int] = {}
    for entries, group_ranges, render_fn in range_groups:
        for entry in entries:
            if entry.start_line:
                current_by_start[entry.start_line] = (entry, render_fn)
        for start, end in group_ranges:
            original_end_by_start[start] = end

    # One real, merged, sorted list of (start, end, is_range) blocks --
    # a flat group's own single line is just a (line, line) block, so
    # both kinds sort and gap-fill together in one combined pass.
    blocks = sorted(
        [(line_no, line_no, False) for _entries, group_line_nos, _render_fn in groups for line_no in group_line_nos]
        + [(start, end, True) for start, end in original_end_by_start.items()]
    )

    output = [original_lines[start_idx]]  # the section's own keyword line, verbatim
    cursor = start_idx + 1
    for block_start, block_end, is_range in blocks:
        start_i, end_i = block_start - 1, block_end - 1
        output.extend(original_lines[cursor:start_i])  # verbatim gap (comments/blank lines/other groups)
        if is_range:
            hit = current_by_start.get(block_start)
            if hit is not None:
                entry, render_fn = hit
                output.extend(render_fn(entry, original_lines[start_i : end_i + 1]))
            # else: this real entry was deleted this session -- omit its original range entirely.
        else:
            hit = current_by_line.get(block_start)
            if hit is not None:
                entry, render_fn = hit
                output.append(render_fn(entry, original_lines[start_i]))
            # else: this real entry was deleted this session -- omit its original line entirely.
        cursor = end_i + 1
    output.extend(original_lines[cursor:end_idx])

    for entries, _group_line_nos, render_fn in groups:
        for entry in entries:
            if entry.line_no == 0:
                output.append(render_fn(entry, None))  # an entry added this session
    for entries, _group_ranges, render_fn in range_groups:
        for entry in entries:
            if entry.start_line == 0:
                output.extend(render_fn(entry, None))  # an entry added this session

    output.append(original_lines[end_idx])  # the section's own 'end' line, verbatim
    return output


def render_tech_file(original_path: Path, tech: magic_tech_mod.MagicTechnology) -> str:
    original_text = original_path.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines()

    candidate_sections = [
        (tech.planes_section_start_line, tech.planes_section_end_line, [(tech.planes, tech.all_parsed_plane_line_nos, _render_plane_line)], []),
        (tech.types_section_start_line, tech.types_section_end_line, [(tech.types, tech.all_parsed_type_line_nos, _render_type_line)], []),
        (tech.contacts_section_start_line, tech.contacts_section_end_line, [(tech.contacts, tech.all_parsed_contact_line_nos, _render_contact_line)], []),
        (tech.aliases_section_start_line, tech.aliases_section_end_line, [(tech.aliases, tech.all_parsed_alias_line_nos, _render_alias_line)], []),
        (tech.styles_section_start_line, tech.styles_section_end_line, [(tech.styles, tech.all_parsed_style_line_nos, _render_style_line)], []),
        (tech.compose_section_start_line, tech.compose_section_end_line, [(tech.compose, tech.all_parsed_compose_line_nos, _render_compose_line)], []),
        (tech.connect_section_start_line, tech.connect_section_end_line, [(tech.connect, tech.all_parsed_connect_line_nos, _render_connect_line)], []),
        (
            tech.cifinput_section_start_line, tech.cifinput_section_end_line,
            [
                (tech.cifinput_ignored_layers, tech.all_parsed_cifinput_ignore_line_nos, _render_cifinput_ignore_line),
                (tech.cifinput_layer_hints, tech.all_parsed_cifinput_hint_line_nos, _render_cifinput_hint_line),
            ],
            [(tech.cifinput_recipes, tech.all_parsed_cifinput_recipe_ranges, _render_cifinput_recipe_range)],
        ),
        (
            tech.cifoutput_section_start_line, tech.cifoutput_section_end_line,
            [(tech.cif_layers, tech.all_parsed_cif_layer_line_nos, _render_cifoutput_calma_line)],
            [],
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
            [(tech.extract_devices, tech.all_parsed_extract_device_ranges, _render_device_range)],
        ),
        (
            tech.drc_section_start_line, tech.drc_section_end_line,
            [],
            [
                (tech.drc_angle_checks, tech.all_parsed_drc_angle_ranges, _render_angle_range),
                (tech.drc_checks, tech.all_parsed_drc_check_ranges, _render_drc_check_range),
                (tech.drc_misc, tech.all_parsed_drc_misc_ranges, _render_drc_misc_range),
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
    for start_line, end_line, groups, range_groups in active_sections:
        start_idx = start_line - 1
        output.extend(original_lines[cursor:start_idx])  # verbatim gap before this section
        output.extend(_render_section_patch(original_lines, start_line, end_line, groups, range_groups))
        cursor = end_line  # end_line - 1 is the 0-indexed 'end' line, already appended; next gap starts right after.

    output.extend(original_lines[cursor:])  # everything after the last patched section, verbatim
    return text_utils.join_preserving_trailing_newline(original_text, output)


def export_tech_file(tech: magic_tech_mod.MagicTechnology, export_path: Path) -> None:
    text = render_tech_file(tech.source_path, tech)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

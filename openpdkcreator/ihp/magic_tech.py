"""Real Magic ``.tech`` technology-file parsing.

Magic's tech-file format has ~15 distinct sections (``tech``,
``version``, ``planes``, ``types``, ``contact``, ``aliases``,
``styles``, ``compose``, ``connect``, ``cifoutput``, ``cifinput``,
``drc``, ``extract``, ``lef``, ``mzrouter``, ``wiring``, ``router``,
``plowing``, ``plot``), each simply ``<keyword> ... end`` -- confirmed
by hand-reading IHP's own real, downloaded
``libs.tech/magic/ihp-sg13g2.tech`` (761 lines) and the four files it
``include``s (``ihp-sg13g2-{cifout,cifin,drc,extract}.tech``, spliced
in textually at the ``include`` line -- confirmed real: those four are
*fragments* of one logical technology, not standalone ones; only
``ihp-sg13g2-GDS.tech`` is a genuinely separate, second technology,
confirmed by its own distinct ``tech``/``version`` header).

Scoped like ``import_open_pdks.py``'s own DRC-rule extraction: parse
what's reliably tabular and structured in full (``tech``, ``version``,
``planes``, ``types``, ``contact``, ``aliases``, ``styles``,
``compose``, ``connect``), and pull one real, valuable pattern out of
each harder, mini-rule-language section rather than a full interpreter:

- ``cifoutput``: real "recipes" ending in a ``calma <layer> <datatype>``
  statement -- the Magic-type-name to real-GDS-layer/datatype mapping,
  cross-referenceable against ``ihp/layers.py``'s own KLayout ``.lyp``
  layer list (``ihp/reconcile.py``).
- ``drc``: the three dominant, cleanly tabular real statement kinds --
  ``width <layers> <value> "message"``,
  ``spacing <layer1> <layer2> <value> ... "message"``, and
  ``maxwidth <layer> <value> <mode> [exceptions] "message"`` (192 of
  the real section's statements combined, confirmed against the real
  file: 65/65 ``width``, 101/102 ``spacing``, and 26/26 ``maxwidth``
  lines match -- the one real ``spacing`` exception is a genuine
  defect in IHP's own file, a message string missing its closing
  quote, confirmed by direct inspection, not a parser bug). All three
  share the exact same real message-quoting shape, so ``maxwidth``
  reuses ``width``'s own regex structure exactly (skip any filler
  tokens -- ``mode``, an optional real exception-list like
  ``glass,pillar,solder`` -- up to the quoted message, same as
  ``width``/``spacing`` already do, rather than asserting what each
  filler token means). ``value`` is raw file units; empirically
  confirmed for ``width``/``spacing`` (cross-referenced against three
  independent, already-extracted real KLayout DRC rules sharing the
  same real rule ID -- Act.a, Gat.a, NW.b) that dividing by 1000 gives
  the real micron value Magic itself reports -- not from Magic's own
  documented unit spec, which this pass had no authoritative local
  source to confirm against, but a real, repeatable, cross-checked
  empirical fact; the same factor is applied to ``maxwidth`` too, on
  the reasonable inference that one real file's one real section
  shares one real internal unit scale, not a fresh independent
  confirmation of that specific check kind.

  A fourth real, cleanly tabular kind is extracted separately, into its
  own ``MagicAngleCheck``, not folded into the above: real
  ``angles <layer> <degrees> "message"`` statements (17/17 real lines
  match, including one real line needing the section's own backslash-
  continuation join). Same real message-quoting shape as
  ``width``/``maxwidth``, so it reuses that same regex structure -- but
  a real angle is a plain degree count (45/90), not a length, so the
  real, empirically-confirmed ``/1000`` micron conversion is
  deliberately *not* applied here; forcing it into ``MagicDrcCheck``'s
  own ``value_um`` field would have been a real, silent unit lie.

  ``surround``/``edge4way``/``variants``/``widespacing``/``cifwidth``/
  ``cifspacing``/``cifmaxwidth``/... remain real, separate future work
  -- their own real shapes are less uniform (variable argument counts,
  nested real layer-boolean expressions like
  ``~(alldiffhv,allpoly,*pdiff,*nsd,*ntap)/a``, or, for ``variants``, a
  real conditional-scoping directive rather than a check at all), so
  extending the ``width``-style pattern to them isn't a safe reuse.
- ``extract``: real per-layer sheet-resistance values
  (``resist <layer-spec> <value>``, milliohms/square per the file's own
  comment -- 30 of 33 real lines; the other 3 are real non-numeric
  config entries, ``blocktypes``/``obstypes``/``comment None``, not a
  parsing gap) and real plane ordering (``planeorder <name> <int>``,
  14/14). Also the real parasitic-capacitance-coefficient lines --
  ``defaultoverlap``/``defaultsideoverlap``/``defaultareacap``/
  ``defaultperimeter``/``defaultsidewall`` (506 real lines combined,
  every real line for a given directive sharing the exact same real
  token count -- confirmed directly, not assumed -- so leading args
  and trailing numeric value(s) split at a fixed, real, per-directive
  position; argument *semantics* deliberately not asserted, same
  "don't guess" discipline ``ComposeStatement`` already uses) -- and
  every real ``device <class> <model> <type> ...`` statement (50 real
  entries, some wrapped across lines with a trailing '\\' and joined
  via ``_join_backslash_continuations`` first, the same helper the
  ``drc`` section's own wrapped statements use; class/model/type kept
  as real, confirmed-positional fields, everything after kept raw).
  ``devresist``/``contact``/``antenna``/``disconnect``/``substrate``
  remain real, separate future work.

- ``cifinput``: two real, cleanly tabular facts pulled out of the
  section, its own real geometry-boolean recipe blocks (``layer``/
  ``templayer`` ... ``and``/``and-not``/``grow``/``shrink``/``labels``/
  ``copyup``) still deliberately NOT interpreted -- their *first* line
  alone (unlike ``cifoutput``'s *final* ``calma`` line) isn't a
  complete, honest fact about the resulting Magic type, so fully
  modeling them remains real, separate future work. The two real facts
  that *are* extracted, in full: every real ``ignore LAYERNAME``
  statement (23 real entries, a simple, unambiguous "this GDS/CIF
  layer is ignored on read" fact), and a real, standalone
  ``calma NAME L D`` table (133 real entries, confirmed by reading the
  real file to sit together in one flat block, *not* nested inside any
  preceding boolean recipe -- unlike ``cifoutput``'s own per-recipe
  ``calma L D`` lines, which omit the name and inherit it from the
  enclosing ``layer``/``templayer`` block, `cifinput`'s own real
  ``calma`` lines carry their own name token directly, a genuinely
  different real shape requiring its own regex, not a reuse of
  ``cifoutput``'s). Two of those 133 real entries use a literal ``*``
  as their datatype (``calma BOUND 189 *``) -- a real wildcard,
  confirmed by reading the file, kept as ``None`` rather than silently
  dropped or coerced to a fake integer.

``lef``/``mzrouter``/``wiring``/``router``/``plowing``/``plot`` are
still deliberately NOT parsed this pass. Every section name found
(directly or via include) that this pass doesn't fully parse is
reported in ``MagicTechnology.unparsed_sections``, never silently
dropped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_TABULAR_SECTIONS = ("tech", "version", "planes", "types", "contact", "aliases", "styles")
_ALL_KNOWN_SECTIONS = _TABULAR_SECTIONS + (
    "compose", "connect", "cifoutput", "cifinput", "drc", "extract",
    "lef", "mzrouter", "wiring", "router", "plowing", "plot",
)

_SECTION_START_RE = re.compile(r"^(" + "|".join(_ALL_KNOWN_SECTIONS) + r")\s*$")
_INCLUDE_RE = re.compile(r"^include\s+(\S+)\s*$")
_LAYER_BLOCK_START_RE = re.compile(r"^\s*(?:layer|templayer)\s+(\S+)")
_CALMA_RE = re.compile(r"^\s*calma\s+(\d+)\s+(\d+)")
_CIFINPUT_IGNORE_RE = re.compile(r"^\s*ignore\s+(\S+)")
_CIFINPUT_CALMA_RE = re.compile(r"^\s*calma\s+(\S+)\s+(\d+)\s+(\d+|\*)")
_COMPOSE_VERBS = ("compose", "decompose", "paint")
_WIDTH_RE = re.compile(r'^width\s+(\S+)\s+(-?\d+)\s+(?:\S+\s+)*"([^"]*)"\s*$')
_SPACING_RE = re.compile(r'^spacing\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(?:\S+\s+)*"([^"]*)"\s*$')
_MAXWIDTH_RE = re.compile(r'^maxwidth\s+(\S+)\s+(-?\d+)\s+(?:\S+\s+)*"([^"]*)"\s*$')
_ANGLES_RE = re.compile(r'^angles\s+(\S+)\s+(\d+)\s+(?:\S+\s+)*"([^"]*)"\s*$')
_TRAILING_PARENS_RE = re.compile(r"\(([^()]+)\)\s*$")
_RESIST_RE = re.compile(r"^resist\s+(\S+)\s+(-?\d+)\s*$")
_PLANEORDER_RE = re.compile(r"^planeorder\s+(\S+)\s+(\d+)\s*$")
_EXTRACT_CAP_DIRECTIVES = {
    # directive -> real, confirmed real leading-arg count (every real
    # line for that directive has the exact same real token count --
    # checked directly, not assumed; anything past the leading args is
    # the line's own trailing numeric value(s)).
    "defaultareacap": 2,
    "defaultperimeter": 2,
    "defaultsidewall": 2,
    "defaultoverlap": 4,
    "defaultsideoverlap": 4,
}
# Magic's own real value -> micron conversion for the drc section's
# width/spacing statements -- empirically confirmed (not from a local
# spec), see this module's own docstring.
_DRC_VALUE_TO_MICRONS = 1000.0


@dataclass
class PlaneEntry:
    name: str
    short_code: str


@dataclass
class TypeEntry:
    plane: str
    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    obsolete: bool = False
    """The leading '-' flag Magic uses for internal/no-longer-directly-
    painted types (e.g. '-active hvnmosesd,...')."""
    line_no: int = 0
    """This type's own real, 1-indexed source line number in
    ``MagicTechnology.source_path`` -- ``0`` for a type created this
    session (New Type, no real source position) *or* one whose real
    ``types`` section this parser can't safely map back to
    ``source_path``'s own line numbers (see
    ``_safe_prefix_line_count``'s own docstring). Used by
    ``ihp/magic_tech_writer.py`` to patch just this type's own real
    line in place on export."""


@dataclass
class ContactEntry:
    contact_type: str
    layer1: str
    layer2: str


@dataclass
class AliasEntry:
    name: str
    members_raw: str
    """Real, unresolved member-list text (comma-separated, may contain
    '*name' wildcard-prefixed entries and references to other aliases)
    -- resolving wildcard/alias-of-alias semantics is real, separate
    future work; kept verbatim so nothing is silently lost."""


@dataclass
class StyleEntry:
    type_name: str
    style_names: list[str] = field(default_factory=list)


@dataclass
class CifLayer:
    """One real 'layer NAME ... calma L D' recipe from a cifoutput
    section -- a real Magic-type-name to GDS-layer/datatype mapping.
    A name can have more than one real (layer, datatype) pair (e.g.
    drawing + a second output for the same logical layer)."""

    name: str
    gds_pairs: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class CifInputLayerHint:
    """One real 'calma NAME L D' statement from the cifinput section --
    unlike cifoutput's own per-recipe CifLayer, this real statement's
    own NAME token is self-contained, not inherited from an enclosing
    'layer'/'templayer' recipe block (confirmed real: all 133 real
    entries sit together in one flat, standalone table, immediately
    after the last real recipe block, not nested inside any of them).
    A real Magic-type-name to real GDS-layer/datatype hint used for
    CIF/GDS-read layer recognition -- the reverse direction of
    cifoutput's own real mapping."""

    name: str
    gds_layer: int
    gds_datatype: int | None
    """``None`` for a real wildcard datatype (the file's own literal
    ``*``, confirmed real -- e.g. ``calma BOUND 189 *`` -- meaning "any
    datatype", not a parsing gap)."""


@dataclass
class ComposeStatement:
    """One real 'compose|decompose|paint <arg1> <arg2> <arg3>'
    statement from the compose section. Argument *semantics* (which
    slot means e.g. "result" vs. "under"/"over") are deliberately not
    asserted -- no authoritative real source for Magic's own
    compose-section argument order was available to confirm against
    this pass; kept raw and positional, the same 'don't guess'
    discipline ``AliasEntry.members_raw`` already uses."""

    verb: str
    args: tuple[str, str, str]


@dataclass
class ConnectRule:
    """One real connectivity-equivalence line from the connect
    section: two real, raw comma-separated Magic type-lists (wildcard
    prefixes kept verbatim, not resolved) that this technology's
    connectivity model treats as electrically connectable."""

    types_a: str
    types_b: str


@dataclass
class MagicDrcCheck:
    """One real 'width'/'spacing' statement from the drc section --
    see this module's own docstring for the real, empirically-confirmed
    value -> micron conversion and real match-rate numbers."""

    check_type: str
    """"width" or "spacing"."""
    layer_args: list[list[str]]
    """One raw, comma-split real Magic type-list for "width"; two for
    "spacing" (layer1, layer2)."""
    value_um: float
    message: str
    rule_ids_raw: str | None
    """Raw text of a trailing '(...)' in the message, when present
    (e.g. "NW.b", or a real compound case like "Sal.c + Sal.d") --
    kept as one raw string, not split, since a compound case doesn't
    cleanly separate into independent rule IDs without guessing."""


@dataclass
class MagicAngleCheck:
    """One real 'angles <layer> <degrees> "message"' statement from
    the drc section -- a real permitted-angle constraint. Deliberately
    a separate dataclass from ``MagicDrcCheck``, not folded into its
    own ``value_um`` field: a real angle is a plain degree count
    (45/90), not a length, so the real, empirically-confirmed
    ``/1000`` micron conversion ``width``/``spacing``/``maxwidth`` use
    would be a real, silent unit lie if applied here."""

    layer: str
    degrees: int
    message: str


@dataclass
class ExtractResist:
    """One real per-layer sheet-resistance value from the extract
    section (milliohms/square, per the real file's own comment). Real
    layers can repeat across different real PVT-corner ``variants``
    blocks (confirmed: IHP's own hvndiffres/active appears three times
    with three different real values) -- kept as a flat list, not a
    name-keyed dict, so no real corner value is silently dropped."""

    layer_spec: str
    """Raw, e.g. "(allm1)/metal1" -- not decomposed further."""
    milliohms_per_square: int


@dataclass
class ExtractCapCoefficient:
    """One real 'defaultoverlap'/'defaultsideoverlap'/'defaultareacap'/
    'defaultperimeter'/'defaultsidewall' line from the extract
    section -- a real parasitic-capacitance coefficient. Argument
    *semantics* (which token means e.g. "over" vs "under", or which
    physical quantity a trailing number is) are deliberately not
    asserted -- no authoritative real source was available this pass
    to cross-check against (unlike the ``drc`` section's own
    empirically-confirmed ``/1000`` unit factor) -- kept raw and
    positional, same 'don't guess further' discipline
    ``ComposeStatement``/``AliasEntry`` already use. Every real line
    for a given ``directive`` has the exact same real token count
    (confirmed by direct inspection, not assumed), so ``args``/
    ``values`` split at a fixed, real, per-directive position -- see
    ``_EXTRACT_CAP_DIRECTIVES``."""

    directive: str
    args: tuple[str, ...]
    values: tuple[float, ...]


@dataclass
class ExtractDevice:
    """One real 'device <class> <model> <type> ...' statement from the
    extract section's own real transistor/resistor/capacitor-model
    mini-language. ``devclass``/``model``/``type_name`` are real,
    confirmed-positional fields (always tokens 2/3/4 across all 50 real
    entries); everything after is kept raw and positional (a mix of
    real terminal-layer references and 'key=value' parameter mappings)
    -- same 'don't guess further semantics' discipline as
    ``ExtractCapCoefficient``. Real lines can wrap across multiple
    physical lines with a trailing '\\' -- joined first via
    ``_join_backslash_continuations``, the same helper the ``drc``
    section's own real wrapped statements already use."""

    devclass: str
    model: str
    type_name: str
    rest: tuple[str, ...]


@dataclass
class MagicTechnology:
    source_path: Path
    included_files: list[str] = field(default_factory=list)
    name: str = ""
    format: int | None = None
    version: str = ""
    description: str = ""
    requires: str = ""
    planes: list[PlaneEntry] = field(default_factory=list)
    types: list[TypeEntry] = field(default_factory=list)
    contacts: list[ContactEntry] = field(default_factory=list)
    aliases: list[AliasEntry] = field(default_factory=list)
    styles: list[StyleEntry] = field(default_factory=list)
    cif_layers: list[CifLayer] = field(default_factory=list)
    cifinput_ignored_layers: list[str] = field(default_factory=list)
    """Real 'ignore LAYERNAME' statements from the cifinput section."""
    cifinput_layer_hints: list[CifInputLayerHint] = field(default_factory=list)
    """Real, standalone 'calma NAME L D' statements from the cifinput
    section -- see ``CifInputLayerHint``'s own docstring."""
    compose: list[ComposeStatement] = field(default_factory=list)
    connect: list[ConnectRule] = field(default_factory=list)
    drc_checks: list[MagicDrcCheck] = field(default_factory=list)
    drc_angle_checks: list[MagicAngleCheck] = field(default_factory=list)
    """Real 'angles' statements -- see ``MagicAngleCheck``'s own
    docstring for why these are a separate list, not folded into
    ``drc_checks``."""
    drc_skipped: list[str] = field(default_factory=list)
    """Real 'width'/'spacing'/'maxwidth'/'angles' lines found but not
    matched -- e.g. the one real, confirmed defect in IHP's own file
    (a message string missing its closing quote). Every *other* real
    drc-section construct (surround/edge4way/variants/...) was never
    attempted and isn't listed here -- see this module's own
    docstring."""
    extract_resist: list[ExtractResist] = field(default_factory=list)
    extract_plane_order: list[tuple[str, int]] = field(default_factory=list)
    extract_cap_coefficients: list[ExtractCapCoefficient] = field(default_factory=list)
    """Real defaultoverlap/defaultsideoverlap/defaultareacap/
    defaultperimeter/defaultsidewall lines -- see
    ``ExtractCapCoefficient``'s own docstring."""
    extract_devices: list[ExtractDevice] = field(default_factory=list)
    """Real 'device ...' statements -- see ``ExtractDevice``'s own
    docstring."""
    unparsed_sections: list[str] = field(default_factory=list)
    """Real section names found (directly or via include) that this
    pass deliberately does not parse -- see this module's own
    docstring for why."""
    all_parsed_type_line_nos: list[int] = field(default_factory=list)
    """Every real type's own line number as originally parsed, in real
    file order -- unlike ``types``, never mutated by editing (New/
    Delete Type); mirrors ``ihp/lef.py``'s ``LefMacro.
    all_parsed_pin_ranges``, used by ``ihp/magic_tech_writer.py`` to
    tell a real deleted type apart from a comment/blank-line gap.
    Excludes any real type line this parser couldn't safely map back
    to ``source_path``'s own line numbers (see
    ``_safe_prefix_line_count``)."""
    types_section_start_line: int = 0
    """The real, 1-indexed line number of the ``types`` keyword
    itself, in ``source_path`` -- ``0`` if the real ``types`` section
    wasn't found at a safely-mappable position (see
    ``_safe_prefix_line_count``'s own docstring); write-back leaves the
    whole file untouched in that case rather than guess."""
    types_section_end_line: int = 0
    """The real, 1-indexed line number of the ``types`` section's own
    closing ``end``, in ``source_path``."""


def find_tech_files(pdk_root: Path) -> list[Path]:
    return sorted((pdk_root / "libs.tech" / "magic").glob("*.tech"))


def _load_lines_with_includes(path: Path, included: list[str], _seen: set[Path] | None = None) -> list[str]:
    """Real textual splicing: an 'include NAME' line's content is
    replaced by NAME.tech's own real lines, read from the same
    directory Magic itself resolves against -- so section parsing
    below sees one combined, logically-complete technology, matching
    what Magic itself actually loads."""

    _seen = _seen or set()
    if path in _seen:
        return []
    _seen.add(path)

    lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _INCLUDE_RE.match(raw_line.strip())
        if match:
            include_name = match.group(1)
            included.append(include_name)
            include_path = path.parent / f"{include_name}.tech"
            if include_path.is_file():
                lines.extend(_load_lines_with_includes(include_path, included, _seen))
            else:
                lines.append(f"# [unresolved include: {include_name}.tech not found]")
            continue
        lines.append(raw_line)
    return lines


def _safe_prefix_line_count(path: Path) -> int:
    """How many of *path*'s own real leading lines are guaranteed to
    appear at the exact same real line number in
    ``_load_lines_with_includes``'s combined, spliced view -- every
    line before *path*'s own first real ``include`` statement (all of
    it, if there's none). Confirmed true for IHP's own real
    ``ihp-sg13g2.tech``: its real ``types`` section (and everything
    ``ihp/magic_tech_writer.py`` needs to write back) sits well before
    its first real ``include`` line. Not assumed true in general --
    write-back for a real ``types`` line past this boundary is
    deliberately refused (``TypeEntry.line_no`` stays ``0``) rather
    than risk patching the wrong real position in the wrong real
    file."""

    text = path.read_text(encoding="utf-8", errors="replace")
    line_no = 0
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        if _INCLUDE_RE.match(raw_line.strip()):
            return line_no - 1
    return line_no


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    """{section_name: [body lines]} -- everything between a bare
    section-keyword line and the next bare 'end' line. A technology
    can (and does, for cifoutput's real recipes) repeat some
    structure across many 'layer NAME ...' sub-blocks inside one
    section; those are handled by the section-specific parser, not
    here."""

    sections: dict[str, list[str]] = {}
    current: str | None = None
    body: list[str] = []
    for line in lines:
        stripped = line.strip()
        if current is None:
            match = _SECTION_START_RE.match(stripped)
            if match:
                current = match.group(1)
                body = []
            continue
        if stripped == "end":
            sections.setdefault(current, []).extend(body)
            current = None
            continue
        body.append(line)
    return sections


def _parse_planes(lines: list[str]) -> list[PlaneEntry]:
    entries = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "," not in stripped:
            continue
        name, _, short = stripped.partition(",")
        entries.append(PlaneEntry(name=name.strip(), short_code=short.strip()))
    return entries


def _parse_types_with_lines(
    lines: list[str], safe_through: int,
) -> tuple[list[TypeEntry], list[int], int, int]:
    """Unlike every other ``_parse_*`` function here, this one scans
    the full, combined (include-spliced) ``lines`` list itself, not a
    pre-sectioned body -- it needs each real type's own combined-space
    line number to decide whether write-back can safely map it back to
    *source_path*'s own real line numbers (``line_no <= safe_through``,
    see ``_safe_prefix_line_count``). Returns (entries,
    all_parsed_type_line_nos, section_start_line, section_end_line);
    the last two are ``0`` if no safely-mappable real ``types`` section
    was found at all."""

    entries: list[TypeEntry] = []
    all_line_nos: list[int] = []
    section_start = section_end = 0
    in_types = False

    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not in_types:
            if stripped == "types":
                in_types = True
                if section_start == 0 and line_no <= safe_through:
                    section_start = line_no
            continue
        if stripped == "end":
            in_types = False
            if section_start and section_end == 0 and line_no <= safe_through:
                section_end = line_no
            continue
        if not stripped or stripped.startswith("#"):
            continue
        obsolete = stripped.startswith("-")
        body = stripped[1:] if obsolete else stripped
        parts = body.split(None, 1)
        if len(parts) != 2:
            continue
        plane, names_raw = parts
        names = [n.strip() for n in names_raw.split(",") if n.strip()]
        if not names:
            continue
        safe_line_no = line_no if section_start and line_no <= safe_through else 0
        if safe_line_no:
            all_line_nos.append(safe_line_no)
        entries.append(TypeEntry(
            plane=plane, canonical_name=names[0], aliases=names[1:], obsolete=obsolete,
            line_no=safe_line_no,
        ))

    return entries, all_line_nos, section_start, section_end


def _parse_contacts(lines: list[str]) -> list[ContactEntry]:
    entries = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "stackable":
            continue
        parts = stripped.split()
        if len(parts) != 3:
            continue
        entries.append(ContactEntry(contact_type=parts[0], layer1=parts[1], layer2=parts[2]))
    return entries


def _parse_aliases(lines: list[str]) -> list[AliasEntry]:
    entries = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 1)
        if len(parts) != 2:
            continue
        entries.append(AliasEntry(name=parts[0], members_raw=parts[1].strip()))
    return entries


def _parse_styles(lines: list[str]) -> list[StyleEntry]:
    entries = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("styletype"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        entries.append(StyleEntry(type_name=parts[0], style_names=parts[1:]))
    return entries


def _parse_cifoutput_layers(lines: list[str]) -> list[CifLayer]:
    """Every real 'layer NAME ... calma L D' recipe -- a block starts
    at a 'layer'/'templayer' line and runs until the next such line
    (or the section end); every calma statement found inside it is
    attributed to that block's NAME. Multiple blocks can share the
    same NAME (real, confirmed: IHP's own DNWELL is built across two
    separate 'layer DNWELL ...' blocks) -- their calma pairs are
    merged under one CifLayer."""

    by_name: dict[str, CifLayer] = {}
    current_name: str | None = None
    for line in lines:
        start_match = _LAYER_BLOCK_START_RE.match(line)
        if start_match:
            current_name = start_match.group(1)
            by_name.setdefault(current_name, CifLayer(name=current_name))
            continue
        if current_name is None:
            continue
        calma_match = _CALMA_RE.match(line)
        if calma_match:
            pair = (int(calma_match.group(1)), int(calma_match.group(2)))
            by_name[current_name].gds_pairs.append(pair)
    return list(by_name.values())


def _parse_cifinput_ignored_layers(lines: list[str]) -> list[str]:
    names = []
    for line in lines:
        match = _CIFINPUT_IGNORE_RE.match(line)
        if match:
            names.append(match.group(1))
    return names


def _parse_cifinput_layer_hints(lines: list[str]) -> list[CifInputLayerHint]:
    hints = []
    for line in lines:
        match = _CIFINPUT_CALMA_RE.match(line)
        if match:
            datatype_raw = match.group(3)
            hints.append(
                CifInputLayerHint(
                    name=match.group(1), gds_layer=int(match.group(2)),
                    gds_datatype=None if datatype_raw == "*" else int(datatype_raw),
                )
            )
    return hints


def _parse_compose(lines: list[str]) -> list[ComposeStatement]:
    entries = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) != 4 or parts[0] not in _COMPOSE_VERBS:
            continue
        entries.append(ComposeStatement(verb=parts[0], args=(parts[1], parts[2], parts[3])))
    return entries


def _parse_connect(lines: list[str]) -> list[ConnectRule]:
    entries = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) != 2:
            continue
        entries.append(ConnectRule(types_a=parts[0], types_b=parts[1]))
    return entries


def _join_backslash_continuations(lines: list[str]) -> list[str]:
    """Magic's real drc/extract sections wrap long statements across
    lines with a trailing '\\' -- collapse those before line-by-line
    parsing so a wrapped statement isn't silently mis-tokenized as two
    separate, incomplete lines."""

    joined: list[str] = []
    pending = ""
    for line in lines:
        if pending:
            line = pending + " " + line.strip()
            pending = ""
        if line.rstrip().endswith("\\"):
            pending = line.rstrip()[:-1].rstrip()
            continue
        joined.append(line)
    return joined


def _parse_drc_checks(lines: list[str]) -> tuple[list[MagicDrcCheck], list[MagicAngleCheck], list[str]]:
    checks: list[MagicDrcCheck] = []
    angle_checks: list[MagicAngleCheck] = []
    skipped: list[str] = []
    for line in _join_backslash_continuations(lines):
        stripped = line.strip()
        if stripped.startswith("width "):
            match = _WIDTH_RE.match(stripped)
            if match is None:
                skipped.append(stripped)
                continue
            layers_raw, value, message = match.groups()
            id_match = _TRAILING_PARENS_RE.search(message)
            checks.append(MagicDrcCheck(
                check_type="width", layer_args=[layers_raw.split(",")],
                value_um=int(value) / _DRC_VALUE_TO_MICRONS, message=message,
                rule_ids_raw=id_match.group(1) if id_match else None,
            ))
        elif stripped.startswith("spacing "):
            match = _SPACING_RE.match(stripped)
            if match is None:
                skipped.append(stripped)
                continue
            layer1, layer2, value, message = match.groups()
            id_match = _TRAILING_PARENS_RE.search(message)
            checks.append(MagicDrcCheck(
                check_type="spacing", layer_args=[layer1.split(","), layer2.split(",")],
                value_um=int(value) / _DRC_VALUE_TO_MICRONS, message=message,
                rule_ids_raw=id_match.group(1) if id_match else None,
            ))
        elif stripped.startswith("maxwidth "):
            match = _MAXWIDTH_RE.match(stripped)
            if match is None:
                skipped.append(stripped)
                continue
            layers_raw, value, message = match.groups()
            id_match = _TRAILING_PARENS_RE.search(message)
            checks.append(MagicDrcCheck(
                check_type="maxwidth", layer_args=[layers_raw.split(",")],
                value_um=int(value) / _DRC_VALUE_TO_MICRONS, message=message,
                rule_ids_raw=id_match.group(1) if id_match else None,
            ))
        elif stripped.startswith("angles "):
            match = _ANGLES_RE.match(stripped)
            if match is None:
                skipped.append(stripped)
                continue
            layer, degrees, message = match.groups()
            angle_checks.append(MagicAngleCheck(layer=layer, degrees=int(degrees), message=message))
    return checks, angle_checks, skipped


def _parse_extract_resist(lines: list[str]) -> list[ExtractResist]:
    entries = []
    for line in lines:
        match = _RESIST_RE.match(line.strip())
        if match is None:
            continue
        entries.append(ExtractResist(layer_spec=match.group(1), milliohms_per_square=int(match.group(2))))
    return entries


def _parse_extract_plane_order(lines: list[str]) -> list[tuple[str, int]]:
    entries = []
    for line in lines:
        match = _PLANEORDER_RE.match(line.strip())
        if match is None:
            continue
        entries.append((match.group(1), int(match.group(2))))
    return entries


def _parse_extract_cap_coefficients(lines: list[str]) -> list[ExtractCapCoefficient]:
    entries = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        arg_count = _EXTRACT_CAP_DIRECTIVES.get(parts[0])
        if arg_count is None or len(parts) <= arg_count:
            continue
        args = tuple(parts[1 : 1 + arg_count])
        value_tokens = parts[1 + arg_count :]
        try:
            values = tuple(float(token) for token in value_tokens)
        except ValueError:
            continue
        entries.append(ExtractCapCoefficient(directive=parts[0], args=args, values=values))
    return entries


def _parse_extract_devices(lines: list[str]) -> list[ExtractDevice]:
    entries = []
    for line in _join_backslash_continuations(lines):
        stripped = line.strip()
        if not stripped.startswith("device "):
            continue
        parts = stripped.split()
        if len(parts) < 4:
            continue
        entries.append(
            ExtractDevice(devclass=parts[1], model=parts[2], type_name=parts[3], rest=tuple(parts[4:]))
        )
    return entries


def parse_tech_file(path: Path) -> MagicTechnology:
    included: list[str] = []
    lines = _load_lines_with_includes(path, included)
    sections = _split_sections(lines)

    tech = MagicTechnology(source_path=path, included_files=included)

    for line in sections.get("tech", []):
        stripped = line.strip()
        if stripped.startswith("format"):
            parts = stripped.split()
            if len(parts) == 2 and parts[1].isdigit():
                tech.format = int(parts[1])
        elif stripped and not stripped.startswith("#"):
            tech.name = stripped

    for line in sections.get("version", []):
        stripped = line.strip()
        if stripped.startswith("version"):
            tech.version = stripped.split(None, 1)[1].strip() if " " in stripped else ""
        elif stripped.startswith("description"):
            tech.description = stripped.split(None, 1)[1].strip().strip('"')
        elif stripped.startswith("requires"):
            tech.requires = stripped.split(None, 1)[1].strip()

    safe_through = _safe_prefix_line_count(path)
    tech.types, tech.all_parsed_type_line_nos, tech.types_section_start_line, tech.types_section_end_line = (
        _parse_types_with_lines(lines, safe_through)
    )

    tech.planes = _parse_planes(sections.get("planes", []))
    tech.contacts = _parse_contacts(sections.get("contact", []))
    tech.aliases = _parse_aliases(sections.get("aliases", []))
    tech.styles = _parse_styles(sections.get("styles", []))
    tech.cif_layers = _parse_cifoutput_layers(sections.get("cifoutput", []))
    tech.cifinput_ignored_layers = _parse_cifinput_ignored_layers(sections.get("cifinput", []))
    tech.cifinput_layer_hints = _parse_cifinput_layer_hints(sections.get("cifinput", []))
    tech.compose = _parse_compose(sections.get("compose", []))
    tech.connect = _parse_connect(sections.get("connect", []))
    tech.drc_checks, tech.drc_angle_checks, tech.drc_skipped = _parse_drc_checks(sections.get("drc", []))
    tech.extract_resist = _parse_extract_resist(sections.get("extract", []))
    tech.extract_plane_order = _parse_extract_plane_order(sections.get("extract", []))
    tech.extract_cap_coefficients = _parse_extract_cap_coefficients(sections.get("extract", []))
    tech.extract_devices = _parse_extract_devices(sections.get("extract", []))

    parsed = set(_TABULAR_SECTIONS) | {"cifoutput", "cifinput", "compose", "connect", "drc", "extract"}
    tech.unparsed_sections = sorted(set(sections) - parsed)

    return tech

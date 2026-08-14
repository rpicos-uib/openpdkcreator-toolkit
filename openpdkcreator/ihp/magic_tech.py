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
- ``drc``: the two dominant, cleanly tabular real statement kinds --
  ``width <layers> <value> "message"`` and
  ``spacing <layer1> <layer2> <value> ... "message"`` (167 of the real
  section's statements combined, confirmed against the real file: 65/65
  ``width`` and 101/102 ``spacing`` lines match -- the one real
  exception is a genuine defect in IHP's own file, a message string
  missing its closing quote, confirmed by direct inspection, not a
  parser bug). ``value`` is raw file units; empirically confirmed
  (cross-referenced against three independent, already-extracted real
  KLayout DRC rules sharing the same real rule ID -- Act.a, Gat.a,
  NW.b) that dividing by 1000 gives the real micron value Magic itself
  reports -- not from Magic's own documented unit spec, which this
  pass had no authoritative local source to confirm against, but a
  real, repeatable, cross-checked empirical fact.
- ``extract``: real per-layer sheet-resistance values
  (``resist <layer-spec> <value>``, milliohms/square per the file's own
  comment -- 30 of 33 real lines; the other 3 are real non-numeric
  config entries, ``blocktypes``/``obstypes``/``comment None``, not a
  parsing gap) and real plane ordering (``planeorder <name> <int>``,
  14/14). The much larger real remainder of this section --
  ``defaultoverlap``/``defaultsideoverlap``/``defaultareacap``/
  ``defaultperimeter``/``defaultsidewall`` (505 real parasitic-
  capacitance-coefficient lines combined) and ``device``/``devresist``/
  ``contact``/``antenna``/``disconnect``/``substrate`` -- is real,
  separate future work; ``device`` in particular is its own real
  transistor-model mini-language.

``cifinput``/``lef``/``mzrouter``/``wiring``/``router``/``plowing``/
``plot`` are still deliberately NOT parsed this pass -- ``cifinput``'s
own real recipes are geometry-boolean chains (``and``/``and-not``/
``grow``/``shrink``) whose *first* line alone (unlike ``cifoutput``'s
*final* ``calma`` line) isn't a complete, honest fact about the
resulting Magic type, so it needs its own, separate real design pass,
not a quick reuse of the ``cifoutput`` pattern. These are reported, by
name, in ``MagicTechnology.unparsed_sections``, never silently dropped.
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
_COMPOSE_VERBS = ("compose", "decompose", "paint")
_WIDTH_RE = re.compile(r'^width\s+(\S+)\s+(-?\d+)\s+(?:\S+\s+)*"([^"]*)"\s*$')
_SPACING_RE = re.compile(r'^spacing\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(?:\S+\s+)*"([^"]*)"\s*$')
_TRAILING_PARENS_RE = re.compile(r"\(([^()]+)\)\s*$")
_RESIST_RE = re.compile(r"^resist\s+(\S+)\s+(-?\d+)\s*$")
_PLANEORDER_RE = re.compile(r"^planeorder\s+(\S+)\s+(\d+)\s*$")
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
    compose: list[ComposeStatement] = field(default_factory=list)
    connect: list[ConnectRule] = field(default_factory=list)
    drc_checks: list[MagicDrcCheck] = field(default_factory=list)
    drc_skipped: list[str] = field(default_factory=list)
    """Real 'width'/'spacing' lines found but not matched -- e.g. the
    one real, confirmed defect in IHP's own file (a message string
    missing its closing quote). Every *other* real drc-section
    construct (surround/edge4way/maxwidth/variants/...) was never
    attempted and isn't listed here -- see this module's own
    docstring."""
    extract_resist: list[ExtractResist] = field(default_factory=list)
    extract_plane_order: list[tuple[str, int]] = field(default_factory=list)
    unparsed_sections: list[str] = field(default_factory=list)
    """Real section names found (directly or via include) that this
    pass deliberately does not parse -- see this module's own
    docstring for why."""


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


def _parse_types(lines: list[str]) -> list[TypeEntry]:
    entries = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        obsolete = stripped.startswith("-")
        if obsolete:
            stripped = stripped[1:]
        parts = stripped.split(None, 1)
        if len(parts) != 2:
            continue
        plane, names_raw = parts
        names = [n.strip() for n in names_raw.split(",") if n.strip()]
        if not names:
            continue
        entries.append(TypeEntry(plane=plane, canonical_name=names[0], aliases=names[1:], obsolete=obsolete))
    return entries


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


def _parse_drc_checks(lines: list[str]) -> tuple[list[MagicDrcCheck], list[str]]:
    checks: list[MagicDrcCheck] = []
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
    return checks, skipped


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

    tech.planes = _parse_planes(sections.get("planes", []))
    tech.types = _parse_types(sections.get("types", []))
    tech.contacts = _parse_contacts(sections.get("contact", []))
    tech.aliases = _parse_aliases(sections.get("aliases", []))
    tech.styles = _parse_styles(sections.get("styles", []))
    tech.cif_layers = _parse_cifoutput_layers(sections.get("cifoutput", []))
    tech.compose = _parse_compose(sections.get("compose", []))
    tech.connect = _parse_connect(sections.get("connect", []))
    tech.drc_checks, tech.drc_skipped = _parse_drc_checks(sections.get("drc", []))
    tech.extract_resist = _parse_extract_resist(sections.get("extract", []))
    tech.extract_plane_order = _parse_extract_plane_order(sections.get("extract", []))

    parsed = set(_TABULAR_SECTIONS) | {"cifoutput", "compose", "connect", "drc", "extract"}
    tech.unparsed_sections = sorted(set(sections) - parsed)

    return tech

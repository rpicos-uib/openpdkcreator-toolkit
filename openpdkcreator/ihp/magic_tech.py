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
``planes``, ``types``, ``contact``, ``aliases``, ``styles``), and pull
one real, valuable pattern out of the much harder ``cifoutput``
geometry-DSL section (real, boolean-operation "recipes" ending in a
``calma <layer> <datatype>`` statement) -- the actual Magic-type-name
to real-GDS-layer/datatype mapping, directly cross-referenceable
against ``ihp/layers.py``'s own KLayout ``.lyp``-derived layer list.
``compose``/``connect``/``cifinput``/``drc``/``extract``/``lef``/
``mzrouter``/``wiring``/``router``/``plowing``/``plot`` are
deliberately NOT parsed this pass -- each is real, separate work (DRC
and extract in particular are their own mini rule-languages, the Magic
equivalent of KLayout's DRC Ruby DSL) -- and are reported, by name, in
``MagicTechnology.unparsed_sections``, never silently dropped.
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

    parsed = set(_TABULAR_SECTIONS) | {"cifoutput"}
    tech.unparsed_sections = sorted(set(sections) - parsed)

    return tech

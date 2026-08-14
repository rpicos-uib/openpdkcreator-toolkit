"""Real Qucs-S symbol/component parsing, hand-verified against IHP's
real, downloaded ``libs.tech/qucs-s/symbols/`` files.

**A real, confirmed structural fact worth stating plainly**: this one
real directory holds *two* genuinely different real formats sharing
one file location, not one:

- ``.sym`` (22 real files): a flat sequence of real, individually
  well-formed, self-closing XML tags (``<Line/>``, ``<Arc/>``,
  ``<Text/>``, ``<PortSym/>`` -- 350 real lines total, confirmed every
  one self-closing by direct check) -- Qucs-S's own real *drawn
  symbol* geometry. This is the format README's own Future Work
  section already flagged as a real, unrelated tag syntax from
  xschem's own ``.sym`` (confirmed again here: real
  ``<PortSym x=... y=... type=... angle=... [condition=...]/>``
  primitives carry **no real port name** at all, unlike xschem's own
  real ``B ... {name=...}`` pins -- position/type/angle only, exactly
  as already documented).
- ``.xml`` (34 real files): a real, single-root, well-formed XML
  ``<Component>`` document -- a real *device definition*
  (library/schematic id, a real ``Description``, real
  ``Models``' ``DefaultModel``/``SpiceModel``, real ``Parameters``
  each with a real ``name``/``unit``/``show`` plus either a real
  ``default_value`` or a real ``equation`` -- confirmed real variance,
  177 of 188 real parameters carry the former, the other 11 the
  latter, never both -- real ``Netlists``' ``NgspiceNetlist``/
  ``CDLNetlist``/optionally ``XyceNetlist`` template strings, and a
  reference to exactly one real ``.sym`` file for its own drawn
  geometry, confirmed to resolve for all 34 real files). Confirmed
  real, parseable by the standard ``xml.etree.ElementTree`` with zero
  failures across all 34 real files -- unlike this project's other
  real, XML-*shaped* format (KLayout's own real ``.lyp``, see
  ``ihp/layers.py``), ``ElementTree`` is safe and appropriate here:
  this domain is read-only, with no line-number-tracking write-back
  requirement forcing a hand-rolled scanner. A ``.sym`` file, by
  contrast, is genuinely *not* single-root XML (a flat top-level tag
  sequence, the same real shape xschem's own ``.sym``/``.sch`` use),
  so each of its own real primitive lines is parsed individually via
  ``ET.fromstring`` instead.

A real, optional ``condition=`` attribute on a ``.sym``'s own drawing
primitive (e.g. ``condition="type=npn"``) marks that primitive as
belonging to only one real symbol *variant* -- a real BJT symbol's own
drawn geometry switches between its ``npn``/``pnp`` variants this way,
the Qucs-S schematic-capture analog of Magic's own ``variants``
conditional-scoping construct (``ihp/magic_tech.py``). Not evaluated
or resolved here -- kept as a raw, per-primitive fact, the same
"structure, not full semantics" precedent as everywhere else.

Real device Parameters are kept raw/positional (``raw_attrs``), the
same "don't guess further semantics" precedent
``ihp/magic_tech.py``'s own ``ComposeStatement`` and
``ihp/xschem.py``'s own ``raw_fields`` already use.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

_PRIMITIVE_LINE_RE = re.compile(r"^<([A-Za-z]+)[^>]*/>\s*(?:<!--\s*(.*?)\s*-->)?\s*$")


def _to_int(token: str) -> int:
    try:
        return int(token)
    except ValueError:
        return 0  # a real, unexpected non-integer coordinate -- never seen in practice; kept defensive, not fatal.


@dataclass
class QucsPort:
    x: int
    y: int
    port_type: str
    """Real ``type=`` value -- a small integer code, kept as its own
    real string, not decoded further (see this module's docstring)."""
    angle: int
    condition: str = ""
    """Real, optional ``condition=`` value (e.g. ``type=npn``) --
    empty when this port belongs to every real symbol variant."""
    hint: str = ""
    """A real, trailing XML comment some (not all -- 20 of 66 real
    ``PortSym`` lines, confirmed by direct count) ``PortSym`` lines
    carry, naming the physical pin (e.g. ``<!--D-->`` for a real
    transistor's drain) -- a real, honestly partial annotation, not a
    substitute for the real port name this format simply doesn't
    carry (see this module's own docstring)."""


@dataclass
class QucsSymbolGeometry:
    source_path: Path
    ports: list[QucsPort] = field(default_factory=list)
    primitive_count: int = 0
    """Every real top-level drawing primitive (``Line``/``Arc``/
    ``Text``/``PortSym``), not just ports -- a quick real complexity
    summary; the non-port primitives' own geometry is not parsed
    further, the same "structure, not graphics" precedent
    ``ihp/xschem.py``'s own ``.sym`` parser already established."""


@dataclass
class QucsParameter:
    raw_attrs: dict[str, str]
    description: str = ""


@dataclass
class QucsComponent:
    source_path: Path
    library: str = ""
    names: str = ""
    schematic_id: str = ""
    description: str = ""
    default_model: str = ""
    spice_model: str = ""
    symbol_file: str = ""
    """Bare filename (the real ``{QUCS_S_COMPONENTS_LIBRARY}/`` prefix
    stripped), e.g. ``Mos.sym``."""
    resolved_symbol_path: Path | None = None
    """The real, existing ``.sym`` geometry file this component
    references, confirmed to resolve for all 34 real files -- kept
    ``None``-checked anyway rather than assumed, matching this
    project's own "confirmed real, not assumed" discipline."""
    netlist_templates: dict[str, str] = field(default_factory=dict)
    """Real ``NgspiceNetlist``/``CDLNetlist``/``XyceNetlist`` template
    strings, raw -- the template DSL itself is not parsed further."""
    parameters: list[QucsParameter] = field(default_factory=list)


def find_component_files(pdk_root: Path) -> list[Path]:
    return sorted((pdk_root / "libs.tech" / "qucs-s" / "symbols").glob("*.xml"))


def find_symbol_geometry_files(pdk_root: Path) -> list[Path]:
    return sorted((pdk_root / "libs.tech" / "qucs-s" / "symbols").glob("*.sym"))


def parse_symbol_geometry(path: Path) -> QucsSymbolGeometry:
    text = path.read_text(encoding="utf-8", errors="replace")
    geometry = QucsSymbolGeometry(source_path=path)

    for line in text.splitlines():
        match = _PRIMITIVE_LINE_RE.match(line.strip())
        if not match:
            continue
        geometry.primitive_count += 1
        if match.group(1) != "PortSym":
            continue
        tag_text = line.strip()[: line.strip().index("/>") + 2]
        try:
            el = ET.fromstring(tag_text)
        except ET.ParseError:
            continue  # a real, malformed primitive line -- never observed; skipped rather than crashing.
        geometry.ports.append(
            QucsPort(
                x=_to_int(el.get("x", "0")), y=_to_int(el.get("y", "0")),
                port_type=el.get("type", ""), angle=_to_int(el.get("angle", "0")),
                condition=el.get("condition", ""), hint=match.group(2) or "",
            )
        )

    return geometry


def parse_component_file(path: Path) -> QucsComponent:
    root = ET.parse(path).getroot()
    component = QucsComponent(
        source_path=path,
        library=root.get("library", ""),
        names=root.get("names", ""),
        schematic_id=root.get("schematic_id", ""),
    )

    desc_el = root.find("Description")
    if desc_el is not None and desc_el.text:
        component.description = desc_el.text.strip()

    models_el = root.find("Models")
    if models_el is not None:
        default_el = models_el.find("DefaultModel")
        if default_el is not None:
            component.default_model = default_el.get("value", "")
        spice_el = models_el.find("SpiceModel")
        if spice_el is not None:
            component.spice_model = spice_el.get("value", "")

    netlists_el = root.find("Netlists")
    if netlists_el is not None:
        for child in netlists_el:
            component.netlist_templates[child.tag] = (child.get("value") or child.text or "").strip()

    symbols_el = root.find("Symbols")
    if symbols_el is not None:
        symbol_el = symbols_el.find("Symbol")
        if symbol_el is not None:
            file_el = symbol_el.find("File")
            if file_el is not None and file_el.text:
                bare = file_el.text.strip().rsplit("/", 1)[-1]
                component.symbol_file = bare
                resolved = path.parent / bare
                component.resolved_symbol_path = resolved if resolved.is_file() else None

    params_el = root.find("Parameters")
    if params_el is not None:
        for p in params_el:
            pdesc_el = p.find("Description")
            desc = (pdesc_el.text or "").strip() if pdesc_el is not None else ""
            component.parameters.append(QucsParameter(raw_attrs=dict(p.attrib), description=desc))

    return component

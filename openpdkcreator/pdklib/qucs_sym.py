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
  ``pdklib/layers.py``), ``ElementTree`` is safe and appropriate here:
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
conditional-scoping construct (``pdklib/magic_tech.py``). Not evaluated
or resolved here -- kept as a raw, per-primitive fact, the same
"structure, not full semantics" precedent as everywhere else.

Real device Parameters are kept raw/positional (``raw_attrs``), the
same "don't guess further semantics" precedent
``pdklib/magic_tech.py``'s own ``ComposeStatement`` and
``pdklib/xschem.py``'s own ``raw_fields`` already use.
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
    line_no: int = 0
    """This port's own real, 1-indexed source line number -- ``0`` for
    a port added this session. Used by ``pdklib/qucs_sym_writer.py`` for
    write-back."""


@dataclass
class QucsLine:
    x1: int
    y1: int
    x2: int
    y2: int
    color: str = "#000080"
    width: int = 2
    style: int = 1
    condition: str = ""
    line_no: int = 0


@dataclass
class QucsArc:
    """Real, bounding-box-based arc (``x``/``y`` = the ellipse's own
    real top-left corner, ``arcWidth``/``height`` = its own real full
    bounding-box size) -- confirmed real, not a center/radius shape
    the way xschem's own arc is. Real ``angle``/``len`` are in real
    1/16-degree units (confirmed: real full-circle sweeps use
    ``len="5760"`` = 360 * 16)."""

    x: int
    y: int
    arc_width: int
    height: int
    angle: int
    """Real start angle, in 1/16-degree units."""
    sweep_len: int
    """Real sweep length, in 1/16-degree units."""
    color: str = "#000080"
    width: int = 2
    style: int = 1
    condition: str = ""
    line_no: int = 0


@dataclass
class QucsText:
    x: int
    y: int
    size: int
    color: str
    text: str
    condition: str = ""
    line_no: int = 0


@dataclass
class QucsSymbolGeometry:
    source_path: Path
    ports: list[QucsPort] = field(default_factory=list)
    lines: list[QucsLine] = field(default_factory=list)
    arcs: list[QucsArc] = field(default_factory=list)
    texts: list[QucsText] = field(default_factory=list)
    primitive_count: int = 0
    """Every real top-level drawing primitive (``Line``/``Arc``/
    ``Text``/``PortSym``) -- a quick real complexity summary; now that
    the real graphical editor (``gui/geometry_canvas.py``) exists,
    ``lines``/``arcs``/``texts`` above hold every one of these
    individually, not just a count."""
    all_parsed_port_line_nos: list[int] = field(default_factory=list)
    all_parsed_line_line_nos: list[int] = field(default_factory=list)
    all_parsed_arc_line_nos: list[int] = field(default_factory=list)
    all_parsed_text_line_nos: list[int] = field(default_factory=list)
    """Every real primitive's own line number as originally parsed, in
    real file order, one list per real shape kind -- unlike ``ports``/
    ``lines``/``arcs``/``texts``, never mutated by editing (New/
    Delete); used by ``pdklib/qucs_sym_writer.py`` to tell a real deleted
    primitive apart from a non-matching-kind/comment gap."""


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


def create_new_symbol_geometry_file(path: Path) -> None:
    """Writes a real, minimal, valid (empty) Qucs-S ``.sym`` file at
    *path* -- no real drawing primitives yet (added afterward via the
    GUI's own New Port action; every other real primitive kind --
    ``Line``/``Arc``/``Text`` -- has no editor here either). Refuses
    to overwrite an existing real file."""

    if path.exists():
        raise FileExistsError(f"{path} already exists -- refusing to overwrite it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def create_new_component_file(path: Path, name: str) -> None:
    """Writes a real, minimal, valid Qucs-S component ``.xml`` at
    *path* -- the same real ``<Component>`` structure every real file
    uses (library/schematic_id, Description, Models, Netlists,
    Symbols referencing a same-named real ``.sym`` file, an empty real
    Parameters list -- adding one isn't supported here, see
    ``pdklib/qucs_component_writer.py``'s own docstring). Every real
    field this project has no structured editor for (Description,
    Models, Netlists) is left as an honest placeholder for real,
    raw-text editing via the GUI's own View File -> Edit -> Save.
    Refuses to overwrite an existing real file."""

    if path.exists():
        raise FileExistsError(f"{path} already exists -- refusing to overwrite it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<?xml version="1.0"?>\n'
        f'<Component\n'
        f'  xsi:noNamespaceSchemaLocation="Component.xsd"\n'
        f'  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
        f'  library="IHP SG13G2 devices" names="{name}" schematic_id="X">\n'
        f'    <Description>\n'
        f'        TODO: describe this device\n'
        f'    </Description>\n'
        f'    <Models>\n'
        f'        <DefaultModel value="{name}">\n'
        f'        </DefaultModel>\n'
        f'        <SpiceModel value="{name}">\n'
        f'        </SpiceModel>\n'
        f'    </Models>\n'
        f'    <Netlists>\n'
        f'        <NgspiceNetlist value=""> </NgspiceNetlist>\n'
        f'        <CDLNetlist value="{{NgspiceNetlist}}"> </CDLNetlist>\n'
        f'    </Netlists>\n'
        f'    <Symbols>\n'
        f'        <Symbol id="Standard">\n'
        f'           <File>{{QUCS_S_COMPONENTS_LIBRARY}}/{name}.sym</File>\n'
        f'        </Symbol>\n'
        f'    </Symbols>\n'
        f'    <Parameters>\n'
        f'    </Parameters>\n'
        f'</Component>\n',
        encoding="utf-8",
    )


def parse_symbol_geometry(path: Path) -> QucsSymbolGeometry:
    text = path.read_text(encoding="utf-8", errors="replace")
    geometry = QucsSymbolGeometry(source_path=path)

    for line_no, line in enumerate(text.splitlines(), start=1):
        match = _PRIMITIVE_LINE_RE.match(line.strip())
        if not match:
            continue
        geometry.primitive_count += 1
        kind = match.group(1)
        if kind not in ("PortSym", "Line", "Arc", "Text"):
            continue
        tag_text = line.strip()[: line.strip().index("/>") + 2]
        try:
            el = ET.fromstring(tag_text)
        except ET.ParseError:
            continue  # a real, malformed primitive line -- never observed; skipped rather than crashing.

        if kind == "PortSym":
            geometry.ports.append(
                QucsPort(
                    x=_to_int(el.get("x", "0")), y=_to_int(el.get("y", "0")),
                    port_type=el.get("type", ""), angle=_to_int(el.get("angle", "0")),
                    condition=el.get("condition", ""), hint=match.group(2) or "",
                    line_no=line_no,
                )
            )
            geometry.all_parsed_port_line_nos.append(line_no)
        elif kind == "Line":
            geometry.lines.append(
                QucsLine(
                    x1=_to_int(el.get("x1", "0")), y1=_to_int(el.get("y1", "0")),
                    x2=_to_int(el.get("x2", "0")), y2=_to_int(el.get("y2", "0")),
                    color=el.get("color", "#000080"), width=_to_int(el.get("width", "2")),
                    style=_to_int(el.get("style", "1")), condition=el.get("condition", ""),
                    line_no=line_no,
                )
            )
            geometry.all_parsed_line_line_nos.append(line_no)
        elif kind == "Arc":
            geometry.arcs.append(
                QucsArc(
                    x=_to_int(el.get("x", "0")), y=_to_int(el.get("y", "0")),
                    arc_width=_to_int(el.get("arcWidth", "0")), height=_to_int(el.get("height", "0")),
                    angle=_to_int(el.get("angle", "0")), sweep_len=_to_int(el.get("len", "0")),
                    color=el.get("color", "#000080"), width=_to_int(el.get("width", "2")),
                    style=_to_int(el.get("style", "1")), condition=el.get("condition", ""),
                    line_no=line_no,
                )
            )
            geometry.all_parsed_arc_line_nos.append(line_no)
        elif kind == "Text":
            geometry.texts.append(
                QucsText(
                    x=_to_int(el.get("x", "0")), y=_to_int(el.get("y", "0")),
                    size=_to_int(el.get("size", "12")), color=el.get("color", "#800000"),
                    text=el.get("text", ""), condition=el.get("condition", ""),
                    line_no=line_no,
                )
            )
            geometry.all_parsed_text_line_nos.append(line_no)

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

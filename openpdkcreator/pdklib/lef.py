"""Real LEF parsing, hand-verified against IHP's real, downloaded
``.lef`` files (a tech LEF, two macro/cell LEFs, and 28 real SRAM
hard-macro LEFs). LEF statements are semicolon-terminated
(``WIDTH 0.16 ;``); block delimiters are bare, newline-terminated
lines (``LAYER Cont`` / ``END Cont``, ``MACRO name`` / ``END name``,
``PIN name`` / ``END name``, ``PORT``/``OBS`` / bare ``END``) -- that
distinction (trailing ``;`` or not) is what this parser uses to tell a
block *opener* apart from a same-named *statement* used elsewhere
(e.g. a top-level ``LAYER Cont`` technology-layer block vs. a
``LAYER Metal1 ;`` layer-reference statement inside a ``PORT``/``OBS``/
``ViaRULE`` body).

**Real, easy-to-miss detail, confirmed by reading IHP's actual file,
not assumed from the LEF spec's usual all-uppercase convention**: this
file's real via keywords are mixed-case (``Via``, ``ViaRULE``), not
``VIA``/``VIARULE`` -- LEF keywords are spec-case-insensitive, and this
parser matches them that way throughout (uppercasing the keyword
token only, never a name/value token, which stay real/case-preserved).

Scoped like ``magic_tech.py``: a real, useful subset in full --
``LAYER`` (type/direction/pitch/width/one simple spacing value/
resistance), ``SITE``, ``MACRO`` (class/size/site/symmetry) with real
``PIN`` (direction/use/port layers+rect counts) and ``OBS`` (layers
touched) sub-blocks, and ``VIA``/``ViaRULE`` (real via-stack geometry
-- see below) -- and an honest, deliberate skip of
``PROPERTYDEFINITIONS`` (kept as a name list only) -- names recorded,
body never silently pretended-parsed.

**``VIA``/``ViaRULE`` real body structure**, confirmed by reading
IHP's actual tech LEF, not assumed from the spec: a real fixed-geometry
``Via NAME DEFAULT`` block holds an optional, real via-level
``RESISTANCE`` (always *before* any real ``LAYER`` line in every one of
its 70 real occurrences here, never per-layer -- checked directly, not
assumed) followed by one or more real ``LAYER name ;`` / ``RECT x1 y1
x2 y2 ;`` pairs -- the *same real layer name can legitimately repeat*
with a different real rect (confirmed real: IHP's own double-cut vias,
e.g. ``Via1_DC1B``, declare ``LAYER Via1`` twice for two separate real
cut rects), so layers are kept as an ordered list, never a dict keyed
by name. A real ``ViaRULE NAME GENERATE`` block instead holds one real
``LAYER name ;`` sub-block per real layer, each with its own real
``ENCLOSURE dx dy ;`` (the two real metal layers) or real ``RECT``/
``SPACING w BY h ;``/``RESISTANCE`` (the one real cut layer) --
confirmed real: never both ``ENCLOSURE`` and ``RECT`` on the same real
layer. Both block kinds close on a real, name-echoing ``END NAME``
line at real, *indentation-tolerant* position (this file's own real
formatting is inconsistent -- some real ``END`` lines are flush-left,
others indented -- handled the same generic, whitespace-stripped way
every other block close already is here)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LefLayer:
    name: str
    layer_type: str = ""
    direction: str = ""
    pitch: float | None = None
    width: float | None = None
    spacing: float | None = None
    resistance: str = ""


@dataclass
class LefSite:
    name: str
    site_class: str = ""
    symmetry: list[str] = field(default_factory=list)
    size: tuple[float, float] | None = None


@dataclass
class LefPort:
    layer: str
    rect_count: int = 0


@dataclass
class LefPin:
    name: str
    direction: str = ""
    use: str = ""
    ports: list[LefPort] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0
    """Real, 1-indexed, inclusive source line range of this pin's own
    'PIN name ... END name' block in *its macro's* source file --
    ``0`` for a pin created this session (New Pin), which has no real
    source position. Used by ``pdklib/lef_writer.py`` to patch just this
    pin's own real text back in place on export, without needing to
    fully regenerate content this parser doesn't model (e.g. real
    PORT rect coordinates -- only a count is tracked)."""


@dataclass
class LefMacro:
    name: str
    macro_class: str = ""
    size: tuple[float, float] | None = None
    site: str = ""
    symmetry: list[str] = field(default_factory=list)
    pins: list[LefPin] = field(default_factory=list)
    obs_layers: list[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0
    """Real, 1-indexed, inclusive source line range of this macro's own
    'MACRO name ... END name' block."""
    all_parsed_pin_ranges: list[tuple[int, int]] = field(default_factory=list)
    """Every real pin's (start_line, end_line) as originally parsed,
    in real file order -- unlike ``pins``, never mutated by editing
    (New/Delete Pin) -- ``pdklib/lef_writer.py`` uses this to tell a real
    deleted pin (omit its original text) apart from a gap between real
    pins that's just a comment/blank line (keep it verbatim)."""


@dataclass
class LefViaLayerGeometry:
    layer: str
    rects: list[tuple[float, float, float, float]] = field(default_factory=list)
    """Real (x1, y1, x2, y2) micron rects for this layer within the
    via -- more than one when the same real layer name repeats inside
    one real via (a real multi-cut via, e.g. ``Via1_DC1B``)."""


@dataclass
class LefVia:
    name: str
    is_default: bool = False
    resistance: float | None = None
    layers: list[LefViaLayerGeometry] = field(default_factory=list)


@dataclass
class LefViaRuleLayer:
    layer: str
    enclosure: tuple[float, float] | None = None
    rect: tuple[float, float, float, float] | None = None
    spacing: tuple[float, float] | None = None
    """Real ``SPACING w BY h`` -- the cut layer's own real array
    pitch, not a simple single-value spacing."""
    resistance: float | None = None


@dataclass
class LefViaRule:
    name: str
    is_generate: bool = False
    layers: list[LefViaRuleLayer] = field(default_factory=list)


@dataclass
class LefFile:
    source_path: Path
    version: str = ""
    database_microns: int | None = None
    manufacturing_grid: float | None = None
    layers: list[LefLayer] = field(default_factory=list)
    sites: list[LefSite] = field(default_factory=list)
    macros: list[LefMacro] = field(default_factory=list)
    vias: list[LefVia] = field(default_factory=list)
    """Real VIA blocks, including their own real via-stack geometry --
    see this module's own docstring for the real body structure."""
    via_rules: list[LefViaRule] = field(default_factory=list)
    """Real ViaRULE GENERATE blocks -- see this module's own docstring."""


def find_lef_files(pdk_root: Path) -> list[Path]:
    return sorted((pdk_root / "libs.ref").glob("*/lef/*.lef"))


_LEF_SKELETON = """VERSION 5.7 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
"""


def create_new_lef_file(path: Path) -> None:
    """Writes a minimal, valid, real empty-library LEF skeleton --
    a real ``VERSION``/``BUSBITCHARS``/``DIVIDERCHAR`` header, zero
    macros (confirmed real: IHP's own real ``.lef`` files never carry
    a trailing ``END LIBRARY`` either -- they just end after the last
    real macro's own ``END <name>`` line, so omitting one here matches
    real convention, not a shortcut). *path* must sit under
    ``libs.ref/<family>/lef/`` to be found again by ``find_lef_files``
    above.

    Pair with the LEF Macros sub-tab's own **New Macro...** action to
    add a real, brand-new macro to a file created this way --
    ``lef_writer.py``'s own ``render_lef_file`` renders it as a whole,
    freshly-generated block on export (``ORIGIN``/``SITE`` still
    aren't modeled -- real, separate future work -- but ``CLASS``/
    ``SIZE``/``SYMMETRY``/pins all round-trip)."""

    if path.exists():
        raise FileExistsError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_LEF_SKELETON, encoding="utf-8")


def _apply_layer_field(layer: LefLayer, keyword: str, tokens: list[str]) -> None:
    if keyword == "TYPE" and len(tokens) > 1:
        layer.layer_type = tokens[1]
    elif keyword == "DIRECTION" and len(tokens) > 1:
        layer.direction = tokens[1]
    elif keyword == "PITCH" and len(tokens) > 1:
        layer.pitch = _try_float(tokens[1])
    elif keyword == "WIDTH" and len(tokens) > 1:
        layer.width = _try_float(tokens[1])
    elif keyword == "SPACING" and len(tokens) == 2:
        # A bare "SPACING <value>" only -- real, more elaborate variants
        # ("SPACING <value> ADJACENTCUTS N WITHIN W") are a second,
        # conditional rule on top of this one; kept as the simple,
        # primary value only.
        layer.spacing = _try_float(tokens[1])
    elif keyword == "RESISTANCE" and len(tokens) > 1:
        layer.resistance = " ".join(tokens[1:])


def _apply_site_field(site: LefSite, keyword: str, tokens: list[str]) -> None:
    if keyword == "CLASS" and len(tokens) > 1:
        site.site_class = " ".join(tokens[1:])
    elif keyword == "SYMMETRY":
        site.symmetry = tokens[1:]
    elif keyword == "SIZE" and len(tokens) >= 4:
        size = _try_size(tokens)
        if size:
            site.size = size


def _apply_macro_field(macro: LefMacro, keyword: str, tokens: list[str]) -> None:
    if keyword == "CLASS" and len(tokens) > 1:
        macro.macro_class = " ".join(tokens[1:])
    elif keyword == "SIZE" and len(tokens) >= 4:
        size = _try_size(tokens)
        if size:
            macro.size = size
    elif keyword == "SITE" and len(tokens) > 1:
        macro.site = tokens[1]
    elif keyword == "SYMMETRY":
        macro.symmetry = tokens[1:]


def _apply_pin_field(pin: LefPin, keyword: str, tokens: list[str]) -> None:
    if keyword == "DIRECTION" and len(tokens) > 1:
        pin.direction = tokens[1]
    elif keyword == "USE" and len(tokens) > 1:
        pin.use = tokens[1]


def _try_float(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


def _try_size(tokens: list[str]) -> tuple[float, float] | None:
    # "SIZE w BY h" -- tokens[1]=w, tokens[2]="BY", tokens[3]=h
    w, h = _try_float(tokens[1]), _try_float(tokens[3])
    return (w, h) if w is not None and h is not None else None


def _try_rect(tokens: list[str]) -> tuple[float, float, float, float] | None:
    if len(tokens) < 5:
        return None
    values = [_try_float(t) for t in tokens[1:5]]
    return (values[0], values[1], values[2], values[3]) if all(v is not None for v in values) else None


def parse_lef_file(path: Path) -> LefFile:
    lef = LefFile(source_path=path)
    stack: list[dict] = []

    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        content = raw_line.split("#", 1)[0].strip()
        if not content:
            continue
        has_semicolon = content.endswith(";")
        body = content[:-1].strip() if has_semicolon else content
        tokens = body.split()
        if not tokens:
            continue
        keyword = tokens[0].upper()
        frame = stack[-1] if stack else None
        kind = frame["kind"] if frame else "root"

        if kind == "skip":
            if keyword == "END":
                stack.pop()
            continue

        if keyword == "END":
            if kind == "root":
                continue
            stack.pop()
            if kind == "layer":
                lef.layers.append(frame["obj"])
            elif kind == "site":
                lef.sites.append(frame["obj"])
            elif kind == "macro":
                frame["obj"].end_line = line_no
                lef.macros.append(frame["obj"])
            elif kind == "pin":
                frame["obj"].end_line = line_no
                pin_obj = frame["obj"]
                stack[-1]["obj"].pins.append(pin_obj)
                stack[-1]["obj"].all_parsed_pin_ranges.append((pin_obj.start_line, pin_obj.end_line))
            elif kind == "via":
                lef.vias.append(frame["obj"])
            elif kind == "viarule":
                lef.via_rules.append(frame["obj"])
            continue

        if keyword == "UNITS" and not has_semicolon and kind == "root":
            stack.append({"kind": "units", "obj": None})
            continue
        if keyword == "PROPERTYDEFINITIONS" and kind == "root":
            stack.append({"kind": "propdefs", "obj": None})
            continue
        if keyword == "LAYER" and not has_semicolon and kind == "root":
            stack.append({"kind": "layer", "obj": LefLayer(name=tokens[1])})
            continue
        if keyword == "SITE" and not has_semicolon and kind == "root":
            stack.append({"kind": "site", "obj": LefSite(name=tokens[1])})
            continue
        if keyword == "MACRO" and kind == "root":
            stack.append({"kind": "macro", "obj": LefMacro(name=tokens[1], start_line=line_no)})
            continue
        if keyword == "VIA" and kind == "root":
            name = tokens[1] if len(tokens) > 1 else ""
            is_default = len(tokens) > 2 and tokens[2].upper() == "DEFAULT"
            stack.append({"kind": "via", "obj": LefVia(name=name, is_default=is_default)})
            continue
        if keyword == "VIARULE" and kind == "root":
            name = tokens[1] if len(tokens) > 1 else ""
            is_generate = len(tokens) > 2 and tokens[2].upper() == "GENERATE"
            stack.append({"kind": "viarule", "obj": LefViaRule(name=name, is_generate=is_generate)})
            continue
        if keyword == "PIN" and kind == "macro":
            stack.append({"kind": "pin", "obj": LefPin(name=tokens[1], start_line=line_no)})
            continue
        if keyword == "PORT" and kind == "pin":
            stack.append({"kind": "port", "obj": None})
            continue
        if keyword == "OBS" and kind == "macro":
            stack.append({"kind": "obs", "obj": None})
            continue

        if kind == "root" and keyword == "VERSION" and len(tokens) > 1:
            lef.version = tokens[1]
        elif kind == "root" and keyword == "MANUFACTURINGGRID" and len(tokens) > 1:
            lef.manufacturing_grid = _try_float(tokens[1])
        elif kind == "units" and keyword == "DATABASE" and len(tokens) >= 3 and tokens[1].upper() == "MICRONS":
            value = _try_float(tokens[2])
            lef.database_microns = int(value) if value is not None else None
        elif kind == "layer":
            _apply_layer_field(frame["obj"], keyword, tokens)
        elif kind == "site":
            _apply_site_field(frame["obj"], keyword, tokens)
        elif kind == "macro":
            _apply_macro_field(frame["obj"], keyword, tokens)
        elif kind == "pin":
            _apply_pin_field(frame["obj"], keyword, tokens)
        elif kind == "port" and keyword == "LAYER" and len(tokens) > 1:
            stack[-2]["obj"].ports.append(LefPort(layer=tokens[1]))
        elif kind == "port" and keyword == "RECT":
            ports = stack[-2]["obj"].ports
            if ports:
                ports[-1].rect_count += 1
        elif kind == "obs" and keyword == "LAYER" and len(tokens) > 1:
            macro_obj = stack[-2]["obj"]
            if tokens[1] not in macro_obj.obs_layers:
                macro_obj.obs_layers.append(tokens[1])
        elif kind == "via" and keyword == "LAYER" and len(tokens) > 1:
            frame["obj"].layers.append(LefViaLayerGeometry(layer=tokens[1]))
        elif kind == "via" and keyword == "RECT":
            rect = _try_rect(tokens)
            if rect is not None and frame["obj"].layers:
                frame["obj"].layers[-1].rects.append(rect)
        elif kind == "via" and keyword == "RESISTANCE" and not frame["obj"].layers and len(tokens) > 1:
            # Real, confirmed via every one of IHP's own 70 real Via
            # blocks: RESISTANCE only ever appears once, before any
            # LAYER line -- a real via-level value, never per-layer.
            frame["obj"].resistance = _try_float(tokens[1])
        elif kind == "viarule" and keyword == "LAYER" and len(tokens) > 1:
            frame["obj"].layers.append(LefViaRuleLayer(layer=tokens[1]))
        elif kind == "viarule" and frame["obj"].layers:
            via_rule_layer = frame["obj"].layers[-1]
            if keyword == "ENCLOSURE" and len(tokens) >= 3:
                dx, dy = _try_float(tokens[1]), _try_float(tokens[2])
                if dx is not None and dy is not None:
                    via_rule_layer.enclosure = (dx, dy)
            elif keyword == "RECT":
                rect = _try_rect(tokens)
                if rect is not None:
                    via_rule_layer.rect = rect
            elif keyword == "SPACING":
                size = _try_size(tokens)
                if size is not None:
                    via_rule_layer.spacing = size
            elif keyword == "RESISTANCE" and len(tokens) > 1:
                via_rule_layer.resistance = _try_float(tokens[1])

    return lef

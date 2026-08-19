"""Real xschem ``.sym`` symbol parsing, hand-verified against IHP's
real, downloaded ``libs.tech/xschem/*/*.sym`` files (202 real symbols
across `sg13g2_pr`/`sg13g2_stdcells`/`sg13g2_tests`/
`sg13g2_tests_xyce`) -- the first concrete real parser for the
project's own stated **Simulation** GUI group's schematic-capture
side (see README's Future Work): a real symbol's own device-attribute
(``K { ... }``) block, its own real pin list (``B ... { name=...
dir=... }`` primitives), and, for the real graphical editor (see
``gui/geometry_canvas.py``), its own real drawing geometry too --
``L`` (line), ``A`` (arc), ``T`` (text), and any non-pin ``B`` (a real
decorative box, confirmed real in `sg13_hv_nmos.sym`/
`sg13_hv_pmos.sym`/... -- has no `name=`/`dir=` at all) primitives,
each with its own real coordinates.

**Real format, confirmed by reading actual files, not assumed**: an
xschem ``.sym`` file is a flat sequence of top-level, column-0
``TAG {content}`` primitives (``v``/``G``/``K``/``V``/``S``/``F``/
``E``/``L``/``B``/``A``/``T``); ``content`` can itself be multi-line
and can contain a real, embedded, *escaped* brace inside a real quoted
Tcl expression (e.g. real ``ptap1.sym``'s own
``format="tcleval(... [ev \\{ ... \\} ] ...)"``) -- so finding a real
block's own matching closing ``}`` requires a real, quote-aware,
brace-depth-aware scan (``_scan_braced``), not a naive first-``}``
search (which a first draft used, and which broke on this exact real
file). A real ``B`` primitive's own property block can itself span
multiple physical lines (confirmed real: `inductor.sym`'s own real
``sim_pinnumber``/``name``/``dir`` properties are split across three
real lines) -- the same scanner handles this uniformly. Not every real
``B`` primitive is a real pin (some are plain decorative boxes with no
``name=``/``dir=`` properties at all, confirmed real in
`sg13_hv_nmos.sym`/`sg13_hv_pmos.sym`/`sg13_hv_rf_nmos.sym`/
`sg13_hv_rf_pmos.sym`) -- these are correctly skipped as pins, but
still captured as real, plain boxes now that graphics are modeled.
Real geometry shapes, confirmed by direct reading: ``L <layer> <x1>
<y1> <x2> <y2> {props}`` (a line segment); ``A <layer> <cx> <cy>
<radius> <start_angle> <sweep_angle> {props}`` (an arc, real angles in
real degrees, not always integers -- confirmed real,
non-integer sweep angles in `sg13g2_a21o_1.sym`); ``T {text} <x> <y>
<rotation> <flip> <hsize> <vsize> {props}`` (a text label, real
``@name``/``@symname``/... placeholder tokens included verbatim, not
resolved). Real coordinates are floats throughout (confirmed real,
non-integer values), unlike Qucs-S's own real integer-only geometry.

The real ``K`` block's own ``type=`` field (e.g. ``capacitor``/
``primitive``/``nmos``/``subcircuit``/``res``/``diode``) is exposed as
its own field; its own real ``template="name=X model=Y w=... l=..."``
sub-value (a real, embedded, space-separated key=value default-
parameter list -- confirmed real and consistently shaped across every
device symbol that has one) is parsed one level deeper into
``template_params``. Every other real ``K``-block field
(``format``/``lvs_format``/``function3``/``extra``/``highlight``/
``drc``/...) varies field-by-field per device kind (confirmed real:
`cap_cmim.sym` and `sg13g2_a21o_1.sym` share almost no field names) --
kept raw and positional in ``raw_fields``, the same "don't guess
further semantics" discipline ``pdklib/magic_tech.py``'s own
``ComposeStatement``/``ExtractCapCoefficient`` already use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import numeric

_K_BLOCK_RE = re.compile(r"(?m)^K\s*\{")
_B_RE = re.compile(r"(?m)^B\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*\{")
_L_RE = re.compile(r"(?m)^L\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*\{")
_A_RE = re.compile(r"(?m)^A\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*\{")
_T_HEAD_RE = re.compile(r"(?m)^T\s*\{")
_T_TAIL_RE = re.compile(r"\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*\{")
_KV_RE = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')


def _to_float(token: str) -> float:
    parsed = numeric.parse_number(token)
    return 0.0 if parsed is None else parsed  # a real, unexpected non-numeric coordinate -- never seen in practice; kept defensive, not fatal.


def _unquote(text: str) -> str:
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1].replace('\\"', '"').replace("\\{", "{").replace("\\}", "}")
    return text


def _scan_braced(text: str, brace_pos: int) -> tuple[str, int]:
    """*text[brace_pos]* == ``'{'``. Returns (interior_text,
    index_just_after_the_matching_close) -- quote-aware: a real,
    escaped brace inside a real double-quoted value (a real Tcl
    ``ev \\{...\\}`` expression) never affects depth."""

    depth = 1
    i = brace_pos + 1
    in_quotes = False
    start = i
    n = len(text)
    while i < n:
        ch = text[i]
        if in_quotes:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_quotes = False
        else:
            if ch == '"':
                in_quotes = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i], i + 1
        i += 1
    return text[start:], n  # real, unterminated block -- shouldn't happen; return what's there.


def _line_no_at(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _parse_kv_block(text: str) -> dict[str, str]:
    return {key: _unquote(value) for key, value in _KV_RE.findall(text)}


@dataclass
class XschemPin:
    name: str
    direction: str
    """Real ``dir=`` value -- ``in``/``out``/``inout``, confirmed the
    only three real values across all 202 real symbols."""
    layer: str = "5"
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    """Real pin geometry (a real ``B`` primitive's own rectangle) --
    used by the real graphical editor (``gui/geometry_canvas.py``) to
    draw and drag the pin; not previously modeled when only the
    structured Pins list editor existed."""
    start_line: int = 0
    end_line: int = 0


@dataclass
class XschemLine:
    layer: str
    x1: float
    y1: float
    x2: float
    y2: float
    start_line: int = 0
    end_line: int = 0


@dataclass
class XschemArc:
    layer: str
    cx: float
    cy: float
    radius: float
    start_angle: float
    sweep_angle: float
    start_line: int = 0
    end_line: int = 0


@dataclass
class XschemText:
    text: str
    x: float
    y: float
    rot: int
    flip: int
    hsize: float
    vsize: float
    start_line: int = 0
    end_line: int = 0


@dataclass
class XschemBox:
    """A real, non-pin ``B`` primitive -- a plain decorative box (see
    this module's own docstring)."""

    layer: str
    x1: float
    y1: float
    x2: float
    y2: float
    start_line: int = 0
    end_line: int = 0


@dataclass
class XschemSymbol:
    source_path: Path
    device_type: str = ""
    """Real ``K`` block's own ``type=`` field, e.g. ``capacitor``/
    ``primitive``/``nmos``/``subcircuit``."""
    template_params: dict[str, str] = field(default_factory=dict)
    """Real, parsed ``template="key=value key=value ..."`` sub-value --
    a device instance's own real default parameters."""
    raw_fields: dict[str, str] = field(default_factory=dict)
    """Every other real `K`-block field, kept raw -- see this module's
    own docstring for why."""
    pins: list[XschemPin] = field(default_factory=list)
    all_parsed_pin_ranges: list[tuple[int, int]] = field(default_factory=list)
    """Every real pin's own (start_line, end_line) as originally
    parsed, in real file order -- unlike ``pins``, never mutated by
    editing (New/Delete Pin); mirrors ``pdklib/lef.py``'s ``LefMacro.
    all_parsed_pin_ranges``, used by ``pdklib/xschem_writer.py`` to tell a
    real deleted pin apart from a decorative-box/comment gap."""
    lines: list[XschemLine] = field(default_factory=list)
    all_parsed_line_ranges: list[tuple[int, int]] = field(default_factory=list)
    arcs: list[XschemArc] = field(default_factory=list)
    all_parsed_arc_ranges: list[tuple[int, int]] = field(default_factory=list)
    texts: list[XschemText] = field(default_factory=list)
    all_parsed_text_ranges: list[tuple[int, int]] = field(default_factory=list)
    boxes: list[XschemBox] = field(default_factory=list)
    all_parsed_box_ranges: list[tuple[int, int]] = field(default_factory=list)
    """Real drawing geometry -- one list plus one real, parse-time-only
    range list per real shape kind, the same real "line_no ==
    ``0`` -> added this session" / "``all_parsed_*`` tracks deletions"
    discipline ``pins``/``all_parsed_pin_ranges`` already use, so
    ``gui/geometry_canvas.py``'s own graphical editor and
    ``pdklib/xschem_writer.py``'s own write-back can add/move/delete any
    of them."""


def find_sym_files(pdk_root: Path) -> list[Path]:
    return sorted((pdk_root / "libs.tech" / "xschem").glob("*/*.sym"))


def create_new_sym_file(path: Path) -> None:
    """Writes a real, minimal, valid xschem ``.sym`` skeleton at
    *path* -- the same real header primitives (``v``/``G``/``K``/
    ``V``/``S``/``E``) every real symbol opens with, a real
    ``type=subcircuit`` (a real, generic, unopinionated real device
    type -- confirmed real and used across the actual downloaded
    deck), and no pins yet (added afterward via the GUI's own New Pin
    action). Refuses to overwrite an existing real file."""

    if path.exists():
        raise FileExistsError(f"{path} already exists -- refusing to overwrite it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "v {xschem version=3.4.6 file_version=1.2}\nG {}\nK {type=subcircuit}\nV {}\nS {}\nE {}\n",
        encoding="utf-8",
    )


def parse_sym_file(path: Path) -> XschemSymbol:
    text = path.read_text(encoding="utf-8", errors="replace")
    symbol = XschemSymbol(source_path=path)

    k_match = _K_BLOCK_RE.search(text)
    if k_match:
        k_content, _ = _scan_braced(text, k_match.end() - 1)
        k_fields = _parse_kv_block(k_content)
        symbol.device_type = k_fields.pop("type", "")
        template_raw = k_fields.pop("template", None)
        if template_raw is not None:
            symbol.template_params = _parse_kv_block(template_raw)
        symbol.raw_fields = k_fields

    for match in _B_RE.finditer(text):
        layer, x1, y1, x2, y2 = match.groups()
        brace_pos = match.end() - 1
        content, end_pos = _scan_braced(text, brace_pos)
        props = _parse_kv_block(content)
        start_line = _line_no_at(text, match.start())
        end_line = _line_no_at(text, end_pos - 1)
        name = props.get("name")
        direction = props.get("dir")
        if name and direction:
            symbol.pins.append(
                XschemPin(
                    name=name, direction=direction, layer=layer,
                    x1=_to_float(x1), y1=_to_float(y1), x2=_to_float(x2), y2=_to_float(y2),
                    start_line=start_line, end_line=end_line,
                )
            )
            symbol.all_parsed_pin_ranges.append((start_line, end_line))
        else:
            # a real, non-pin decorative box -- not an extraction gap, see this module's docstring.
            symbol.boxes.append(
                XschemBox(
                    layer=layer, x1=_to_float(x1), y1=_to_float(y1), x2=_to_float(x2), y2=_to_float(y2),
                    start_line=start_line, end_line=end_line,
                )
            )
            symbol.all_parsed_box_ranges.append((start_line, end_line))

    for match in _L_RE.finditer(text):
        layer, x1, y1, x2, y2 = match.groups()
        _content, end_pos = _scan_braced(text, match.end() - 1)
        start_line = _line_no_at(text, match.start())
        end_line = _line_no_at(text, end_pos - 1)
        symbol.lines.append(
            XschemLine(
                layer=layer, x1=_to_float(x1), y1=_to_float(y1), x2=_to_float(x2), y2=_to_float(y2),
                start_line=start_line, end_line=end_line,
            )
        )
        symbol.all_parsed_line_ranges.append((start_line, end_line))

    for match in _A_RE.finditer(text):
        layer, cx, cy, radius, start_angle, sweep_angle = match.groups()
        _content, end_pos = _scan_braced(text, match.end() - 1)
        start_line = _line_no_at(text, match.start())
        end_line = _line_no_at(text, end_pos - 1)
        symbol.arcs.append(
            XschemArc(
                layer=layer, cx=_to_float(cx), cy=_to_float(cy), radius=_to_float(radius),
                start_angle=_to_float(start_angle), sweep_angle=_to_float(sweep_angle),
                start_line=start_line, end_line=end_line,
            )
        )
        symbol.all_parsed_arc_ranges.append((start_line, end_line))

    for match in _T_HEAD_RE.finditer(text):
        text_content, after_text = _scan_braced(text, match.end() - 1)
        tail_match = _T_TAIL_RE.match(text, after_text)
        if not tail_match:
            continue  # a real, malformed/truncated T line -- never observed; skipped rather than crashing.
        x, y, rot, flip, hsize, vsize = tail_match.groups()
        _props, end_pos = _scan_braced(text, tail_match.end() - 1)
        start_line = _line_no_at(text, match.start())
        end_line = _line_no_at(text, end_pos - 1)
        symbol.texts.append(
            XschemText(
                text=text_content, x=_to_float(x), y=_to_float(y),
                rot=int(_to_float(rot)), flip=int(_to_float(flip)),
                hsize=_to_float(hsize), vsize=_to_float(vsize),
                start_line=start_line, end_line=end_line,
            )
        )
        symbol.all_parsed_text_ranges.append((start_line, end_line))

    return symbol

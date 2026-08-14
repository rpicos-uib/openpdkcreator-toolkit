"""Real xschem ``.sym`` symbol parsing, hand-verified against IHP's
real, downloaded ``libs.tech/xschem/*/*.sym`` files (202 real symbols
across `sg13g2_pr`/`sg13g2_stdcells`/`sg13g2_tests`/
`sg13g2_tests_xyce`) -- the first concrete real parser for the
project's own stated **Simulation** GUI group's schematic-capture
side (see README's Future Work), matching this project's established
"one honest, bounded pattern per real format" discipline: a real
symbol's own device-attribute (``K { ... }``) block and its own real
pin list (``B ... { name=... dir=... }`` primitives) are extracted in
full; the symbol's own real drawing geometry (``L``/``A``/``T``
lines -- line segments, arcs, text labels) is deliberately NOT parsed
or rendered, the same "structure yes, graphics no" precedent
``ihp/lef.py``'s own PORT rect-count-only scope and ``ihp/gds.py``'s
own bbox-only scope already established.

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
`sg13_hv_rf_pmos.sym`) -- these are correctly skipped, not an
extraction gap.

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
further semantics" discipline ``ihp/magic_tech.py``'s own
``ComposeStatement``/``ExtractCapCoefficient`` already use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_K_BLOCK_RE = re.compile(r"(?m)^K\s*\{")
_B_BLOCK_RE = re.compile(r"(?m)^B\s+(?:\S+\s+){5}\{")
_KV_RE = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')


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
    editing (New/Delete Pin); mirrors ``ihp/lef.py``'s ``LefMacro.
    all_parsed_pin_ranges``, used by ``ihp/xschem_writer.py`` to tell a
    real deleted pin apart from a decorative-box/comment gap."""


def find_sym_files(pdk_root: Path) -> list[Path]:
    return sorted((pdk_root / "libs.tech" / "xschem").glob("*/*.sym"))


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

    for match in _B_BLOCK_RE.finditer(text):
        brace_pos = match.end() - 1
        content, end_pos = _scan_braced(text, brace_pos)
        props = _parse_kv_block(content)
        name = props.get("name")
        direction = props.get("dir")
        if not name or not direction:
            continue  # a real, non-pin decorative box -- not an extraction gap, see this module's docstring.
        start_line = _line_no_at(text, match.start())
        end_line = _line_no_at(text, end_pos - 1)
        symbol.pins.append(XschemPin(name=name, direction=direction, start_line=start_line, end_line=end_line))
        symbol.all_parsed_pin_ranges.append((start_line, end_line))

    return symbol

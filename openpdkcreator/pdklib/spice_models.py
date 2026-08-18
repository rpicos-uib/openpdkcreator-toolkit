"""Real ngspice ``.lib`` model-card parsing, hand-verified against
IHP's real, downloaded ``libs.tech/ngspice/models/*.lib`` files (32
real files, ~7600 lines combined) -- the first concrete piece of the
project's own stated **Simulation** GUI group (see README's Future
Work), matching this project's established "one honest, bounded
pattern per real format" discipline rather than a full SPICE parser.

Two real, cleanly recognizable statement kinds are extracted in full:

- ``.model NAME TYPE (key=value ...)`` / ``.model NAME TYPE key=value
  ...`` -- both real, confirmed parenthesized and bare forms exist
  (e.g. ``.MODEL darea D (tnom=27 is=... )`` vs. ``.model dinner_mod d
  tnom=27 level=1``); real keyword case varies file to file
  (``.MODEL``/``.model``), matched case-insensitively like every other
  keyword-driven parser here (``pdklib/lef.py``). Real parameter values
  are kept as raw strings, not converted to float -- some real BSIM/PSP
  model cards use a quoted formula expression as a value (e.g.
  ``vfbo = '-0.94312*sg13g2_lv_nmos_vfbo'``), not a plain number, so
  asserting numeric type would be a real, silent data-loss risk, not a
  parsing convenience. Real statements that wrap across multiple
  physical lines via a leading ``+`` continuation marker (SPICE's own
  convention, distinct from Magic's trailing ``\\``) are joined first.
- ``.subckt NAME port1 port2 ... / .ends NAME`` -- a real port list,
  the same bounded shape ``pdklib/netlist.py``'s own CDL/SPICE
  ``.SUBCKT`` extraction already uses. A real ``.model`` can sit
  *inside* a real ``.subckt`` body (a locally-scoped model, confirmed
  real -- e.g. ``resistors_mod.lib``'s own ``rsil`` subckt defines its
  own ``rmod_rsil`` model) -- found via a real per-file count mismatch
  (26 parsed vs. 61 real ``grep`` hits) during verification, not
  assumed; every real ``.model`` is captured regardless of subckt
  nesting.

A third real, cleanly recognizable statement kind, also extracted in
full: ``.LIB NAME ... .ENDL NAME`` PVT-corner blocks (confirmed real
in all 6 real ``corner*.lib`` files -- 47 real blocks combined, every
real ``.LIB``/``.ENDL`` pair balanced). Each real corner's own real
``.param KEY = VALUE`` overrides (kept as raw strings, same "don't
assert numeric type" reasoning as ``.model``'s own params -- some real
values are quoted formula expressions, e.g. real
``cap_carea_mm='agauss(1, 0.01, (mm_ok != 1 ? 0 : 1))'``) and real
``.include FILE`` statements (confirmed real inside these same 6
files' own corner blocks -- which real model file a given corner
actually pulls in) are both captured. Each real model's own full
parameter *count* (some real PSP MOSFET cards carry 100+ real
parameters) is browsable here, not semantically interpreted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_MODEL_RE = re.compile(r"^\.model\s+(\S+)\s+(\S+)\s*(.*)$", re.IGNORECASE)
_SUBCKT_RE = re.compile(r"^\.subckt\s+(\S+)\s*(.*)$", re.IGNORECASE)
_ENDS_RE = re.compile(r"^\.ends\b", re.IGNORECASE)
_PARAM_RE = re.compile(r"(\S+)\s*=\s*('[^']*'|\"[^\"]*\"|\S+)")
_LIB_RE = re.compile(r"^\.lib\s+(\S+)", re.IGNORECASE)
_ENDL_RE = re.compile(r"^\.endl\b", re.IGNORECASE)
_DOT_PARAM_RE = re.compile(r"^\.param\s+(.*)$", re.IGNORECASE)
_INCLUDE_RE = re.compile(r"^\.include\s+(\S+)", re.IGNORECASE)


@dataclass
class SpiceModel:
    """One real ``.model NAME TYPE ...`` statement -- ``params`` is
    every real ``key=value`` pair found, in real file order, kept as
    raw strings (see this module's own docstring for why)."""

    name: str
    model_type: str
    params: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class SpiceSubckt:
    """One real ``.subckt NAME port1 port2 ... / .ends`` block."""

    name: str
    ports: list[str] = field(default_factory=list)


@dataclass
class SpiceCorner:
    """One real ``.LIB NAME ... .ENDL NAME`` PVT-corner block --
    ``params`` is every real ``.param KEY = VALUE`` override found
    inside it, in real file order, kept as raw strings (see this
    module's own docstring for why); ``includes`` is every real
    ``.include FILE`` statement found inside it."""

    name: str
    params: list[tuple[str, str]] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)


@dataclass
class SpiceLibFile:
    source_path: Path
    models: list[SpiceModel] = field(default_factory=list)
    subckts: list[SpiceSubckt] = field(default_factory=list)
    corners: list[SpiceCorner] = field(default_factory=list)


def find_lib_files(pdk_root: Path) -> list[Path]:
    return sorted((pdk_root / "libs.tech" / "ngspice" / "models").glob("*.lib"))


def create_new_lib_file(path: Path) -> None:
    """Writes a minimal, valid, real empty ngspice ``.lib`` skeleton --
    a real, bare comment line, no ``.model``/``.subckt``/``.LIB``
    statements. Genuinely usable immediately afterward, not just a
    stub: ngspice's own real ``.lib``/``.include`` grammar has no
    mandatory header (unlike LEF's ``VERSION``/Magic's ``tech``
    section) -- a real file with nothing but a comment parses cleanly
    to zero real models/subckts/corners here, the same honest "empty,
    not broken" result ``parse_lib_file`` already gives a real file
    with genuinely nothing in it. *path* must sit under
    ``libs.tech/ngspice/models/`` to be found again by
    ``find_lib_files`` above. No editor exists for adding real
    ``.model``/``.subckt`` content from inside this GUI yet -- a real,
    separate future work, matching every other read-only-content
    domain here (see README's own gap note)."""

    if path.exists():
        raise FileExistsError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("* New, empty ngspice model library.\n", encoding="utf-8")


def _join_plus_continuations(lines: list[str]) -> list[str]:
    """Real ngspice ``.lib`` statements wrap across lines with a
    *leading* ``+`` marker on the continuation line -- SPICE's own,
    different convention from Magic's trailing ``\\`` (see
    ``pdklib/magic_tech.py``'s own ``_join_backslash_continuations``)."""

    joined: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("+") and joined:
            joined[-1] = joined[-1] + " " + stripped[1:].strip()
        else:
            joined.append(line)
    return joined


def _parse_params(text: str) -> list[tuple[str, str]]:
    text = text.strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    params = []
    for match in _PARAM_RE.finditer(text):
        key, value = match.groups()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        params.append((key, value))
    return params


def parse_lib_file(path: Path) -> SpiceLibFile:
    lib = SpiceLibFile(source_path=path)
    # Real comment lines start with a bare '*' -- drop them before
    # joining continuations so a commented-out '+' line never gets
    # spliced into a real, active statement.
    content_lines = [
        line for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if not line.strip().startswith("*")
    ]
    joined = _join_plus_continuations(content_lines)

    current_subckt: SpiceSubckt | None = None
    current_corner: SpiceCorner | None = None
    for line in joined:
        stripped = line.strip()
        if not stripped:
            continue
        # A real '.model' can sit *inside* a real '.subckt'/'.ends'
        # body (a locally-scoped model, confirmed real -- e.g.
        # resistors_mod.lib's own 'rsil' subckt defines its own
        # 'rmod_rsil' model) -- checked on every line regardless of
        # subckt nesting, not just at top level.
        model_match = _MODEL_RE.match(stripped)
        if model_match:
            name, model_type, rest = model_match.groups()
            lib.models.append(SpiceModel(name=name, model_type=model_type, params=_parse_params(rest)))
            continue
        if current_corner is not None:
            if _ENDL_RE.match(stripped):
                lib.corners.append(current_corner)
                current_corner = None
                continue
            param_match = _DOT_PARAM_RE.match(stripped)
            if param_match:
                parsed = _parse_params(param_match.group(1))
                if parsed:
                    current_corner.params.append(parsed[0])
                continue
            include_match = _INCLUDE_RE.match(stripped)
            if include_match:
                current_corner.includes.append(include_match.group(1))
            continue
        if current_subckt is not None:
            if _ENDS_RE.match(stripped):
                lib.subckts.append(current_subckt)
                current_subckt = None
            continue
        subckt_match = _SUBCKT_RE.match(stripped)
        if subckt_match:
            name, rest = subckt_match.groups()
            current_subckt = SpiceSubckt(name=name, ports=rest.split())
            continue
        lib_match = _LIB_RE.match(stripped)
        if lib_match:
            current_corner = SpiceCorner(name=lib_match.group(1))
            continue

    return lib

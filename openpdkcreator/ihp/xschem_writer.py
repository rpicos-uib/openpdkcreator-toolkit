"""Real xschem ``.sym`` write-back for the in-memory ``XschemSymbol.pins``
this project's Symbols editor edits -- name/direction only, the same
scope ``ihp/xschem.py`` itself parses (see that module's own docstring
for why: a real ``B`` primitive's own geometry, and every real
property besides ``name=``/``dir=`` -- e.g. real ``goto=``/``propag=``
-- is left completely untouched).

**Surgical patching, not full regeneration**, the same discipline
``ihp/lef_writer.py``'s own PIN/END patching already established: this
module re-reads the *original* source file fresh from disk and, using
each pin's real source line range (``XschemPin.start_line``/
``end_line``, tracked at parse time), keeps every real line of an
existing pin's own ``B ... {...}`` block verbatim, substituting only
the ``name=``/``dir=`` key-value spans *inside* the props text via a
real, quote-aware key=value regex (the same shape
``ihp/xschem.py``'s own ``_KV_RE`` already parses with) -- any other
real property in that block (``goto=``, ``propag=``, ``sim_pinnumber=``,
...) is preserved character-for-character, not reconstructed from a
fields dict this project doesn't fully model. A pin deleted this
session (present in ``XschemSymbol.all_parsed_pin_ranges`` but not in
``XschemSymbol.pins``) has its original text span omitted entirely; a
pin added this session (``start_line == 0``) gets a freshly-generated,
single-line ``B 5 0 0 0 0 {name=... dir=...}`` block appended at the
very end of the file -- real layer ``5`` (374 of 378 real pins across
the downloaded deck use it, confirmed by direct count; the other 4 are
non-pin decorative boxes) and a placeholder 0,0/0,0 position, since
this project has no real pin-geometry editor -- a real, honest starting
point to reposition inside xschem itself, not a claim of correct
placement.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import text_utils
from . import xschem as xschem_mod

_KV_RE = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')


def _kv_repr(value: str) -> str:
    if not value or any(ch.isspace() for ch in value) or '"' in value:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _replace_kv(text: str, key: str, new_value: str) -> str:
    pattern = re.compile(rf'\b{re.escape(key)}=("(?:[^"\\]|\\.)*"|\S+)')
    match = pattern.search(text)
    new_repr = _kv_repr(new_value)
    if match:
        return text[: match.start(1)] + new_repr + text[match.end(1) :]
    # A real pin (both name/dir required by the parser's own filter)
    # always has both keys already -- this only guards a degenerate,
    # never-observed case rather than crashing.
    separator = " " if text.strip() else ""
    return f"{text}{separator}{key}={new_repr}"


def _render_pin_block(pin: xschem_mod.XschemPin, original_block_lines: list[str]) -> list[str]:
    if not original_block_lines:
        return [f"B 5 0 0 0 0 {{name={pin.name} dir={pin.direction}}}"]

    block_text = "\n".join(original_block_lines)
    brace_pos = block_text.index("{")
    interior, close_pos = xschem_mod._scan_braced(block_text, brace_pos)
    new_interior = _replace_kv(interior, "name", pin.name)
    new_interior = _replace_kv(new_interior, "dir", pin.direction)
    new_block = block_text[: brace_pos + 1] + new_interior + block_text[close_pos - 1 :]
    return new_block.split("\n")


def render_sym_file(original_path: Path, symbol: xschem_mod.XschemSymbol) -> str:
    """Real, patched xschem ``.sym`` text for *symbol* (the current,
    possibly pin-edited in-memory structure originally parsed from
    *original_path*). With no edits at all, this is byte-identical to
    the real original file."""

    original_text = original_path.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines()

    current_by_start = {pin.start_line: pin for pin in symbol.pins if pin.start_line != 0}
    output: list[str] = []
    cursor = 0

    for orig_start, orig_end in symbol.all_parsed_pin_ranges:
        start_idx, end_idx = orig_start - 1, orig_end - 1
        output.extend(original_lines[cursor:start_idx])  # verbatim gap (other primitives/comments)
        pin = current_by_start.get(orig_start)
        if pin is not None:
            output.extend(_render_pin_block(pin, original_lines[start_idx : end_idx + 1]))
        # else: this real pin was deleted this session -- omit its original text entirely.
        cursor = end_idx + 1

    output.extend(original_lines[cursor:])  # rest of the real file, verbatim

    for pin in symbol.pins:
        if pin.start_line == 0:
            output.extend(_render_pin_block(pin, []))  # a pin added this session

    return text_utils.join_preserving_trailing_newline(original_text, output)


def export_sym_file(symbol: xschem_mod.XschemSymbol, export_path: Path) -> None:
    text = render_sym_file(symbol.source_path, symbol)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

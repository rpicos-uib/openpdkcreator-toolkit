"""Real xschem ``.sch`` write-back for the in-memory ``XschemSchematic``
this project's Schematics editor edits -- deliberately narrow, matching
what's safely editable without a real geometry editor (this project has
none, the same "structure, not graphics" precedent
``ihp/xschem.py``/``ihp/xschem_sch.py`` themselves already established):

- An instance's real ``name=`` property, and, for a real pin instance
  (``ipin``/``opin``/``iopin``), its real ``lab=`` net-label property
  -- both patched via the same real, quote-aware key=value
  substitution ``ihp/xschem_writer.py`` already uses for symbol pins,
  preserving every other real instance property (device parameters
  like ``l=``/``w=``/``model=``, ...) and the instance's own real
  position/rotation/flip untouched.
- A wire's real ``lab=`` property, same substitution.
- **Delete only** for both -- no "add a new instance/wire" here: a
  real component instance needs a real symbol reference and a real
  drawn position to mean anything, and this project has no schematic
  geometry editor to place one sensibly; synthesizing a fake default
  would misrepresent a real schematic rather than honestly extend it.
  Deleting an existing real instance/wire (a genuinely safe, real
  removal) is supported; every other structural change is left to
  xschem itself.

Same surgical, position-targeted discipline as every other writer
here: re-reads the *original* file fresh from disk, keeps every real
line of an unedited (or non-deletable) block verbatim via
``XschemSchematic.all_parsed_instance_ranges``/
``all_parsed_wire_ranges`` (tracked at parse time), and omits a
deleted entry's original text span entirely.
"""

from __future__ import annotations

from pathlib import Path

from . import text_utils
from . import xschem_sch as xschem_sch_mod
from .xschem_writer import _replace_kv

_SCAN = xschem_sch_mod._scan_braced
_C_HEAD_RE = xschem_sch_mod._C_HEAD_RE
_C_TAIL_RE = xschem_sch_mod._C_TAIL_RE
_N_HEAD_RE = xschem_sch_mod._N_HEAD_RE


def _has_unbalanced_quotes(block_text: str) -> bool:
    """A real, general, computable safety signal: an unescaped
    ``"`` count that isn't even means at least one real quoted region
    in this block never found its own real closing quote during
    parsing -- a reliable sign the block's own line range was mis-
    scanned (see this module's own docstring) and is not safe to
    surgically patch. A correctly-scanned real block's own quotes
    always pair up. Confirmed real, not a guess: every one of the
    3{,}899 real instances/wires across the whole downloaded deck with
    an odd count is exactly one of the 27 real, known-affected files'
    own single malformed entry -- zero false positives found."""

    count = 0
    i = 0
    n = len(block_text)
    while i < n:
        if block_text[i] == "\\":
            i += 2
            continue
        if block_text[i] == '"':
            count += 1
        i += 1
    return count % 2 != 0


def _render_instance_block(inst: xschem_sch_mod.XschemInstance, original_lines: list[str]) -> list[str]:
    """Locates the props block's own real opening brace the exact same
    way ``xschem_sch.parse_sch_file`` itself does -- via ``_C_HEAD_RE``/
    ``_C_TAIL_RE``, not a naive raw-character brace scan -- because a
    real instance's own props text can contain a real, escaped brace
    inside a quoted Tcl expression (confirmed real: some
    ``sg13g2_tests_xyce`` instances embed real Tcl scripts with
    ``\\{...\\}``), which a naive scan would misidentify as a
    structural brace and corrupt the file -- caught by this project's
    own real, driven byte-identical-export check before it ever
    shipped. Returns *original_lines* verbatim, ignoring any pending
    edit, when ``_has_unbalanced_quotes`` flags this specific block as
    unsafe to patch (see this module's own docstring) -- a real,
    narrow, per-entry refusal, not a whole-file one."""

    block_text = "\n".join(original_lines)
    if _has_unbalanced_quotes(block_text):
        return original_lines
    head_match = _C_HEAD_RE.match(block_text)
    if not head_match:
        return original_lines  # a real, unexpected shape -- never observed; leave untouched rather than corrupt it.
    _symbol_ref, after_symbol = _SCAN(block_text, head_match.end() - 1)
    tail_match = _C_TAIL_RE.match(block_text, after_symbol)
    if not tail_match:
        return original_lines

    interior, close_pos = _SCAN(block_text, tail_match.end() - 1)
    new_interior = _replace_kv(interior, "name", inst.name)
    if inst.is_pin:
        new_interior = _replace_kv(new_interior, "lab", inst.pin_label)
    new_block = block_text[: tail_match.end()] + new_interior + block_text[close_pos - 1 :]
    return new_block.split("\n")


def _render_wire_block(wire: xschem_sch_mod.XschemWire, original_lines: list[str]) -> list[str]:
    block_text = "\n".join(original_lines)
    if _has_unbalanced_quotes(block_text):
        return original_lines
    head_match = _N_HEAD_RE.match(block_text)
    if not head_match:
        return original_lines
    interior, close_pos = _SCAN(block_text, head_match.end() - 1)
    new_interior = _replace_kv(interior, "lab", wire.label) if wire.label else interior
    new_block = block_text[: head_match.end()] + new_interior + block_text[close_pos - 1 :]
    return new_block.split("\n")


def _has_overlapping_ranges(ranges: list[tuple[int, int]]) -> bool:
    ordered = sorted(ranges)
    return any(ordered[i][1] >= ordered[i + 1][0] for i in range(len(ordered) - 1))


def render_sch_file(original_path: Path, schematic: xschem_sch_mod.XschemSchematic) -> str:
    """Real, patched xschem ``.sch`` text for *schematic*. With no
    edits at all, this is byte-identical to the real original file --
    **including a real, confirmed, narrow class of entries this
    refuses to touch rather than risk corrupting**: 27 real files
    (26 under ``sg13g2_tests_xyce/`` plus ``start_page.sch``) embed a
    real, deliberate ``simulator_commands_shown.sym`` instance whose
    own multi-line ``value="..."``/``tclcommand="..."`` property text
    ends with a real, doubled quote-then-close-brace idiom
    (``"\\n"}``, confirmed present verbatim via direct search) that
    this project's quote-aware brace scanner (``ihp/xschem.py``'s own
    ``_scan_braced``, shared with the ``.sym`` domain, where this
    exact idiom has never been observed) cannot safely disambiguate
    from a second, nested quoted region -- without real xschem's own
    source to confirm the intended real grammar, guessing risks
    silently corrupting a real file. Two real, computable safety
    signals catch every real occurrence found (confirmed zero false
    positives across the whole downloaded deck): a whole-file check
    (two parsed entries' own line ranges overlapping, the case for 26
    of the 27, where the mis-scan swallows a real sibling instance
    whole -- the entire file is left untouched, any pending edits
    included, rather than a partial, uneven patch) and a per-entry
    check (``_has_unbalanced_quotes``, the case for the 27th --
    ``dc_esd_diodes.sch``'s own affected instance is the real file's
    own *last* entry, so its mis-scan runs off the end of the file
    instead of overlapping a sibling -- only that one real entry is
    left untouched, every other real entry in that same file still
    patches normally)."""

    original_text = original_path.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines()

    whole_file_unsafe = _has_overlapping_ranges(schematic.all_parsed_instance_ranges) or _has_overlapping_ranges(
        schematic.all_parsed_wire_ranges
    )
    if whole_file_unsafe:
        return text_utils.join_preserving_trailing_newline(original_text, original_lines)

    # Merge both real entry kinds (instances, wires) into one, real
    # file-order patch pass -- their own real line ranges never
    # overlap (confirmed: each is its own real, separate top-level
    # primitive), so a single sorted merge is safe.
    patches: list[tuple[int, int, list[str] | None]] = []

    current_instances_by_start = {inst.start_line: inst for inst in schematic.instances if inst.start_line}
    for orig_start, orig_end in schematic.all_parsed_instance_ranges:
        inst = current_instances_by_start.get(orig_start)
        if inst is None:
            patches.append((orig_start, orig_end, None))  # deleted this session
        else:
            block = _render_instance_block(inst, original_lines[orig_start - 1 : orig_end])
            patches.append((orig_start, orig_end, block))

    current_wires_by_start = {wire.start_line: wire for wire in schematic.wires if wire.start_line}
    for orig_start, orig_end in schematic.all_parsed_wire_ranges:
        wire = current_wires_by_start.get(orig_start)
        if wire is None:
            patches.append((orig_start, orig_end, None))
        else:
            block = _render_wire_block(wire, original_lines[orig_start - 1 : orig_end])
            patches.append((orig_start, orig_end, block))

    patches.sort(key=lambda p: p[0])

    output: list[str] = []
    cursor = 0
    for start_line, end_line, block in patches:
        start_idx, end_idx = start_line - 1, end_line - 1
        output.extend(original_lines[cursor:start_idx])  # verbatim gap
        if block is not None:
            output.extend(block)
        cursor = end_idx + 1

    output.extend(original_lines[cursor:])
    return text_utils.join_preserving_trailing_newline(original_text, output)


def export_sch_file(schematic: xschem_sch_mod.XschemSchematic, export_path: Path) -> None:
    text = render_sch_file(schematic.source_path, schematic)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

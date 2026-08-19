"""Real DRC Rule write-back -- patches the two real files a KLayout
DRC-deck rule's editable fields actually live in, mirroring
``pdklib/lef_writer.py``'s own surgical, non-destructive discipline:

- ``rule_id``/``description`` live inside the real ``.drc`` Ruby
  script's own ``result_var.output("ID", "description")`` call.
- ``value`` lives in the real JSON config file's ``drc_rules['KEY']``
  entry (``pdklib/drc.py``'s own extraction already established this
  split: the ``.drc`` script never contains a literal numeric
  threshold, only a variable traced back to a JSON lookup via
  ``.um``).

**Surgical, character-offset-based patching, not full regeneration**:
every function here re-reads the *original* file fresh from disk
(always still pristine, since export never writes to ``data/``) and
replaces only the exact substrings a rule's editable fields occupy --
everything else (surrounding Ruby code, other rules' own ``.output()``
calls, comments, formatting, every other real JSON entry) stays
byte-for-byte untouched. ``_locate`` re-derives which real JSON key (if
any) backs a rule's value, and the exact real ``.output()`` regex
match, by re-running ``pdklib/drc.py``'s own extraction regexes
directly against the target line -- not a second, independently-
drifting implementation of the same fact. This includes a real,
boolean-composed rule's own value too (``pdklib/drc.py``'s own
``_trace_composite_provenance``, reused here rather than re-derived) --
a composite rule's ``value`` edit patches the real JSON correctly, the
same as a direct rule's does.

**A real, common wrinkle handled deliberately, not glossed over**: 61
of IHP's own real ``.output()`` calls have a real ``"<section> : ...
"`` prefix before the description ``pdklib/drc.py`` actually keeps as
``DesignRule.description`` (it splits on the real, first ``" : "`` and
keeps only the suffix). A rule with such a prefix has to have it
preserved verbatim on write-back -- reconstructing the description from
``rule.description`` alone would silently discard that real prefix
text for over a third of IHP's own real rules.

Rules with real, resolvable provenance (extracted by ``pdklib/drc.py``)
patch back into their own real, original file this way. A
hand-authored **New Rule** has no such position to patch -- it instead
gets *generated*, not patched, into a separate, entirely tool-owned
file (``custom_rules.drc``, see ``render_new_rule_block``/
``render_custom_drc_file`` below), for the six ``check_type``s with a
real, single-method KLayout DRC shape this project knows how to emit
(``min_width``/``min_spacing``/``min_enclosure``, plus, added later,
``min_area``/``min_overlap``/``max_length`` -- see
``render_new_rule_block``'s own docstring for the real, local ground
truth each one was checked against before writing any generation code)
-- everything else about a rule (``classification``/``condition``/
``process_revision``/``owner``/``why``/``status``/...) is this
project's own metadata with no real counterpart in the KLayout deck at
all, and stays ``project_io.py``-only, same as before.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import drc as drc_mod
from ..models import DesignRule, Layer
from ..schema import CHECK_TYPES

_PROVENANCE_RE = re.compile(r"^([^:]+):(\d+) \(\.output at :(\d+)\)$")


def parse_provenance(source_provenance: str) -> tuple[str, int, int] | None:
    """(relpath, check_line, output_line), or ``None`` for a rule with
    no real, resolvable source position (hand-authored, or a real
    provenance string this pattern doesn't recognize)."""

    match = _PROVENANCE_RE.match(source_provenance or "")
    if match is None:
        return None
    relpath, check_line, output_line = match.groups()
    return relpath, int(check_line), int(output_line)


def _locate(text: str, check_line: int, output_line: int) -> tuple[str | None, re.Match | None]:
    """Re-derives the real JSON key (if any) backing this check's
    value, and the real ``.output()`` regex ``Match``, from *text*
    alone (the same real ``.drc`` file's fresh content) -- mirroring
    ``pdklib/drc.py``'s own extraction logic exactly (its own compiled
    regexes, imported not duplicated).

    ``check_line`` isn't always a direct ``width()``/``space()``/
    ``sep()``/``enclosed()``/``with_area()``/``with_length()`` line --
    for a real rule ``pdklib/drc.py`` traced through a real boolean
    composition (``.join()``/``.and()``/...), it's the line where the
    *composite* result variable was itself assigned. The same real
    ``_trace_composite_provenance`` used for extraction is reused here
    too (not a second, independently-drifting notion of what a
    composite resolves to) so a composite rule's own real ``value``
    edit patches the real JSON key correctly, the same as a direct
    rule's does -- not silently dropped just because its own real
    ``source_provenance`` doesn't point at one of the two direct
    patterns."""

    value_var_to_key: dict[str, str] = {}
    for match in drc_mod._VALUE_ASSIGN_RE.finditer(text):
        value_var_to_key[match.group(1)] = match.group(2)

    value_var = None
    seed_provenance: dict[str, frozenset] = {}
    for match in drc_mod._CHECK_CALL_RE.finditer(text):
        line_no = text.count("\n", 0, match.start()) + 1
        result_var, _layer_expr, method, args = match.groups()
        value_match = drc_mod._VALUE_VAR_IN_ARGS_RE.search(args)
        this_value_var = value_match.group(1) if value_match else None
        seed_provenance[result_var] = frozenset({(drc_mod.DRC_METHOD_TO_CHECK_TYPE[method], this_value_var)})
        if line_no == check_line:
            value_var = this_value_var
    if value_var is None:
        # Not a width()/space()/sep()/with_area()/with_length() result --
        # check the other real, direct pattern pdklib/drc.py extracts
        # from, .enclosed(outer, value.um, ...).
        for match in drc_mod._ENCLOSURE_CALL_RE.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            result_var, _inner_expr, _outer_expr, args = match.groups()
            value_match = drc_mod._VALUE_VAR_IN_ARGS_RE.search(args)
            this_value_var = value_match.group(1) if value_match else None
            seed_provenance[result_var] = frozenset({("min_enclosure", this_value_var)})
            if line_no == check_line:
                value_var = this_value_var
    if value_var is None:
        # Not a direct check line either -- try the real, composite
        # case: is check_line a real, traceable boolean-composed
        # assignment instead?
        composite_var = None
        for line_no, raw_line in enumerate(text.split("\n"), start=1):
            match = drc_mod._ANY_ASSIGN_RE.match(raw_line.strip())
            if match and line_no == check_line:
                composite_var = match.group(1)
        if composite_var is not None:
            provenance = drc_mod._trace_composite_provenance(text, value_var_to_key, seed_provenance)
            resolved = provenance.get(composite_var)
            if resolved is not None and composite_var not in seed_provenance:
                (_check_type, value_var), = resolved
    json_key = value_var_to_key.get(value_var) if value_var else None

    output_match = None
    for match in drc_mod._OUTPUT_CALL_RE.finditer(text):
        line_no = text.count("\n", 0, match.start()) + 1
        if line_no == output_line:
            output_match = match
            break

    return json_key, output_match


def _apply_spans(text: str, spans: list[tuple[int, int, str]]) -> str:
    spans = sorted(spans, key=lambda span: span[0])
    pieces = []
    cursor = 0
    for start, end, replacement in spans:
        pieces.append(text[cursor:start])
        pieces.append(replacement)
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def render_drc_file(original_path: Path, rules: list[DesignRule]) -> tuple[str, dict[str, float]]:
    """*rules*: every real ``DesignRule`` whose provenance points into
    *original_path* (the caller groups by relpath before calling this).
    Returns the patched real ``.drc`` text, plus ``{json_key:
    rule.value}`` for every rule here whose value traces back to a
    real JSON key -- the caller merges these across every real file
    before patching the JSON config once."""

    text = original_path.read_text(encoding="utf-8", errors="replace")
    spans: list[tuple[int, int, str]] = []
    value_edits: dict[str, float] = {}

    for rule in rules:
        parsed = parse_provenance(rule.source_provenance)
        if parsed is None:
            continue
        _relpath, check_line, output_line = parsed
        json_key, output_match = _locate(text, check_line, output_line)

        if output_match is not None:
            spans.append((output_match.start(2), output_match.end(2), rule.rule_id))
            raw_full_description = output_match.group(3)
            if " : " in raw_full_description:
                prefix = raw_full_description.split(" : ", 1)[0]
                new_description = f"{prefix} : {rule.description}"
            else:
                new_description = rule.description
            spans.append((output_match.start(3), output_match.end(3), new_description))

        if json_key and rule.value is not None:
            value_edits[json_key] = rule.value

    return _apply_spans(text, spans), value_edits


_JSON_NUMBER_RE_TEMPLATE = r'("{key}"\s*:\s*)([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)'


def patch_json_value(json_text: str, key: str, new_value: float) -> str:
    """Replaces *key*'s real value with *new_value* -- but only if it
    actually differs (by real numeric value, not text) from what's
    already there. Skipping a no-op patch matters: a real, confirmed
    case (``"Padb_b": 70.00``) has trailing zeros Python's own
    ``repr(float(...))`` would silently normalize away
    (``"70.0"``) even when nothing was actually edited, which would
    have broken the no-edit-is-byte-identical guarantee -- caught by
    that very check failing against real data, the same way the LEF
    writer's ``ANTENNAMODEL`` bug was caught."""

    pattern = re.compile(_JSON_NUMBER_RE_TEMPLATE.format(key=re.escape(key)))
    match = pattern.search(json_text)
    if match is None:
        raise ValueError(f"real JSON key {key!r} not found in the real config file -- can't patch it")
    if float(match.group(2)) == float(new_value):
        return json_text
    formatted = repr(float(new_value))
    return json_text[: match.start(2)] + formatted + json_text[match.end(2):]


def render_json_config(original_path: Path, value_edits: dict[str, float]) -> str:
    text = original_path.read_text(encoding="utf-8", errors="replace")
    for key, value in value_edits.items():
        text = patch_json_value(text, key, value)
    return text


# -- custom_rules.drc: real write-back for hand-authored (New Rule) rules ---
#
# A genuinely different discipline from every function above, not the
# same "surgical patch" pattern loosely applied: custom_rules.drc is
# entirely owned/generated by this tool (born from New Rule, never a
# real, downloaded foundry file the way every other .drc/.tech/.lef/
# .lyp this project writes back to is), so there's no third-party
# formatting to preserve. Full regeneration on every export is
# correct here, not a shortcut -- it sidesteps needing to track each
# hand-authored rule's own position across sessions the way a real
# rule's source_provenance does.

_GENERATABLE_CHECK_TYPES = {
    "min_width", "min_spacing", "min_enclosure", "min_area", "min_overlap", "max_length", "density_window",
}
_IDENT_RE = re.compile(r"[^0-9A-Za-z_]+")


def _sanitize_ruby_identifier(text: str) -> str:
    ident = _IDENT_RE.sub("_", text).strip("_").lower() or "rule"
    if ident[0].isdigit():
        ident = f"r_{ident}"
    return ident


_FIXED_LAYER_COUNTS = {"min_area": 1, "min_overlap": 2}
"""``min_area``/``min_overlap`` both have a real ``max_layers=None`` in
``CHECK_TYPES`` (a real rule *can* reference more, for shapes this
project doesn't attempt to generate), but the one real, single-method
KLayout DRC idiom each maps to (``with_area(0, v)``/``overlap(other,
v)``, see ``render_new_rule_block`` below) only has a real meaning for
exactly this many layers -- more than that is refused with an honest
reason rather than guessing which real, wider Boolean combination the
rule author actually meant."""

_DENSITY_DIRECTIONS = {"min", "max"}


def _render_density_window_lines(rule: DesignRule, ident: str, layer_vars: list[str]) -> list[str]:
    """Real, runnable KLayout DRC Ruby for a ``density_window`` rule --
    a genuinely different generation shape from every check_type
    above: not a single geometric method + ``.output()``, but a real
    scalar ratio compared against ``rule.value`` (a percent), reported
    via an explicit ``if`` block. Two real, confirmed patterns, chosen
    by whether ``rule.window_size_um`` is set:

    - **Global** (``window_size_um`` is ``None``): one real ratio over
      the whole chip -- ``material.area / extent.area``. Confirmed
      real via an independent cross-check: it's the *only* pattern
      GlobalFoundries' own real, downloaded gf180mcu deck uses for its
      own density rules (``chip_area = extent.sized(0.0).area; ratio =
      (comp + comp_dummy).area / chip_area * 100``, real
      ``DCF.1b``/``DCF.1d`` rules); IHP's own real deck implements this
      same mode too, alongside its own windowed one (its own real
      ``output_global_density_violation`` helper).
    - **Windowed/tiled** (``window_size_um`` set): KLayout's own real,
      officially documented ``layer.with_density(range, tile_size(...),
      [tile_step(...)])`` method -- confirmed by fetching and reading
      KLayout's own official DRC Reference ("Layer Object") directly,
      not guessed: ``min_value``/``max_value`` are real fractions in
      ``0..1`` (not percent), and ``tile_size``/``tile_step`` are real,
      separate top-level helper calls (``tile_step`` optional,
      defaulting to ``tile_size`` when omitted). IHP's own real deck
      uses this exact same core method too (``density.drc``'s own real
      ``with_density_backup`` wrapper), wrapped in real, elaborate
      chip-edge backup-window logic this project deliberately does
      **not** replicate here -- a real, higher-risk, chip-boundary-
      specific optimization, not required for a correct (if slightly
      more conservative right at the chip edge) check -- a real,
      honest, documented scope limit, not a silent simplification.

    Either way, ``rule.condition`` -- already confirmed to be exactly
    ``"min"`` or ``"max"`` by ``render_new_rule_block``'s own
    pre-check -- decides which side of ``rule.value`` is violated:
    density *below* the bound for ``"min"``, *above* it for ``"max"``,
    the same real convention both gf180mcu's own paired rules
    (``DCF.1b``/``DCF.1d``) and IHP's own paired rules (its own real
    ``AFil.g2``/``AFil.g3``) already use."""

    direction = rule.condition.strip().lower()
    material_var = f"{ident}_material"
    lines = [f"{material_var} = " + " + ".join(layer_vars)]
    result_var = f"r_{ident}"
    description = (rule.description or "").replace('"', "'")

    if rule.window_size_um is None:
        chip_var = f"{ident}_chip_area"
        ratio_var = f"{ident}_ratio"
        lines.append(f"{chip_var} = extent.sized(0.0).area")
        lines.append(f"{ratio_var} = {material_var}.area / {chip_var} * 100")
        comparison = f"{ratio_var} < {rule.value}" if direction == "min" else f"{ratio_var} > {rule.value}"
        lines.append(f"if {comparison}")
        lines.append(f'  extent.output("{rule.rule_id}", "{description}")')
        lines.append("end")
        return lines

    fraction = rule.value / 100.0
    density_range = f"0.0 .. {fraction}" if direction == "min" else f"{fraction} .. 1.0"
    tile_args = f"tile_size({rule.window_size_um}.um)"
    if rule.window_step_um is not None:
        tile_args += f", tile_step({rule.window_step_um}.um)"
    lines.append(f"{material_var} = {material_var}.merged")
    lines.append(f"{result_var} = {material_var}.with_density({density_range}, {tile_args})")
    lines.append(f'{result_var}.output("{rule.rule_id}", "{description}")')
    return lines


def render_new_rule_block(rule: DesignRule, layers_by_name: dict[str, Layer]) -> tuple[list[str], str | None]:
    """Real, runnable KLayout DRC Ruby for one hand-authored rule --
    each real layer it references is defined right there, inline, via
    KLayout's own real ``input(gds_layer, gds_datatype)`` (there's no
    real, pre-existing Ruby variable for it to reuse the way a real,
    downloaded deck's own included common file would provide -- a
    from-scratch deck has no such file yet). Returns ``(lines, None)``
    on success, or ``([], reason)`` when this rule genuinely can't be
    generated -- an unsupported *check_type*, a missing *value*, a
    *layers* entry with no matching real, resolvable ``Layer`` (real
    ``gds_layer``/``gds_datatype``), or (``min_area``/``min_overlap``
    only) the wrong real layer count -- reported back to the caller,
    never silently dropped.

    Seven real ``check_type``s map to a real KLayout DRC shape this
    project knows how to emit: ``min_width``/``min_spacing``/
    ``min_enclosure`` (the original three, also the three ``pdklib/
    drc.py``'s own extractor already recognizes coming the other way)
    plus ``min_area``/``min_overlap``/``max_length``, added later --
    grounded in real, local ground truth, not external documentation
    alone: ``layer.with_area(0, v)``, ``layer.overlap(other, v)``, and
    ``layer.edges.with_length(v, nil)`` were each confirmed as real,
    already-used idioms by grepping this project's own real, downloaded
    IHP deck (``antenna.drc``'s own real
    ``dantenna_connected.with_area(0, ant_g_min_area)``;
    ``sg13g2_maximal.drc``'s own real ``self.overlap(other, value)``;
    ``5_16_metal1.drc``'s own real
    ``m1_g_l1.with_length(m1_g_length.um + 0.001.um, nil)``) before
    writing a single line of generation code, the same discipline as
    everywhere else in this project. ``pdklib/drc.py``'s own extractor
    was later extended to recognize ``with_area``/``with_length`` too
    (real, direct ``.output()``-feeding call sites do exist for both --
    ``LBE.b1``/``Seal.k`` -- see that module's own docstring), so a
    ``min_area``/``max_length`` rule generated here now round-trips
    back through re-extraction the same way the original three do.
    ``min_overlap`` alone still doesn't: real, direct ``.overlap()``
    call sites genuinely don't exist anywhere in this deck (its only
    two real occurrences sit inside one generic, parameterized Ruby
    method definition, not a concrete real rule) -- extending the
    extractor for it would have nothing real to extract, so this
    remains a real, honest, one-directional gap for ``min_overlap``
    specifically, not silently closed.

    ``density_window`` (the seventh, added later still) is a real,
    architecturally different shape from the other six -- see
    ``_render_density_window_lines``'s own docstring for the full real
    reasoning (two real generation patterns, global vs. windowed/tiled;
    a real ``rule.condition`` requirement to resolve the min/max
    ambiguity ``schema.CHECK_TYPES['density_window']`` itself doesn't
    encode). It doesn't round-trip back through re-extraction either --
    ``pdklib/drc.py``'s own extractor has no real, direct ground truth
    for either pattern's own shape to verify against (the real IHP deck
    never feeds a density check straight into ``.output()`` the simple
    way ``width()``/``space()``/etc. do -- its own real density checks
    go through hand-written helper functions first), a real, honest gap
    left open the same way ``min_overlap``'s already is."""

    if rule.check_type not in _GENERATABLE_CHECK_TYPES:
        return [], f"check_type {rule.check_type!r} has no real Ruby-generation pattern yet"
    if rule.value is None:
        return [], "no value set"
    spec = CHECK_TYPES[rule.check_type]
    if len(rule.layers) < spec.min_layers:
        return [], f"needs at least {spec.min_layers} real layer(s), has {len(rule.layers)}"
    fixed_count = _FIXED_LAYER_COUNTS.get(rule.check_type)
    if fixed_count is not None and len(rule.layers) != fixed_count:
        return [], f"{rule.check_type} needs exactly {fixed_count} real layer(s), has {len(rule.layers)}"
    if rule.check_type == "density_window" and rule.condition.strip().lower() not in _DENSITY_DIRECTIONS:
        return [], "density_window needs Condition set to exactly 'min' or 'max' to know which bound this value represents"

    needed = rule.layers[: spec.max_layers] if spec.max_layers else rule.layers
    ident = _sanitize_ruby_identifier(rule.rule_id)
    layer_vars: list[str] = []
    lines = [f"# --- {rule.rule_id} ---"]
    for i, layer_name in enumerate(needed):
        layer = layers_by_name.get(layer_name)
        if layer is None or layer.gds_layer is None or layer.gds_datatype is None:
            return [], f"layer {layer_name!r} isn't a real, resolvable Layer with a real GDS layer/datatype"
        var = f"{ident}_l{i}"
        lines.append(f"{var} = input({layer.gds_layer}, {layer.gds_datatype})  # {layer_name}")
        layer_vars.append(var)

    if rule.check_type == "density_window":
        lines.extend(_render_density_window_lines(rule, ident, layer_vars))
        return lines, None

    result_var = f"r_{ident}"
    if rule.check_type == "min_width":
        lines.append(f"{result_var} = {layer_vars[0]}.width({rule.value}.um)")
    elif rule.check_type == "min_spacing":
        lines.append(f"{result_var} = {layer_vars[0]}.space({rule.value}.um)")
    elif rule.check_type == "min_enclosure":
        lines.append(f"{result_var} = {layer_vars[0]}.enclosed({layer_vars[1]}, {rule.value}.um)")
    elif rule.check_type == "min_area":
        lines.append(f"{result_var} = {layer_vars[0]}.with_area(0, {rule.value}.um2)")
    elif rule.check_type == "min_overlap":
        lines.append(f"{result_var} = {layer_vars[0]}.overlap({layer_vars[1]}, {rule.value}.um)")
    else:  # max_length
        lines.append(f"{result_var} = {layer_vars[0]}.edges.with_length({rule.value}.um, nil)")
    description = (rule.description or "").replace('"', "'")
    lines.append(f'{result_var}.output("{rule.rule_id}", "{description}")')
    return lines, None


def render_custom_drc_file(new_rules: list[DesignRule], layers: list[Layer]) -> tuple[str, list[tuple[str, str]]]:
    """*new_rules*: every real ``DesignRule`` with no resolvable
    ``source_provenance`` (hand-authored via New Rule). Returns the
    real, full text for ``custom_rules.drc`` plus ``[(rule_id,
    reason)]`` for every rule that couldn't be generated -- see
    ``render_new_rule_block``'s own docstring for why."""

    layers_by_name = {layer.name: layer for layer in layers}
    lines = [drc_mod.DRC_DECK_SKELETON_HEADER.rstrip("\n")]
    failures: list[tuple[str, str]] = []
    for rule in new_rules:
        block, error = render_new_rule_block(rule, layers_by_name)
        if error is not None:
            failures.append((rule.rule_id, error))
            continue
        lines.append("")
        lines.extend(block)
    lines.append("")
    return "\n".join(lines), failures

"""Bridges Magic Tech's own DRC statements (``pdklib/magic_tech.py``'s
``MagicDrcCheck`` -- Magic-*type* width/spacing rules embedded in a
real ``.tech`` file's ``drc`` section) to DRC Rules' own real,
independent ``DesignRule`` model (``pdklib/drc.py``/``schema.py`` --
a real KLayout DRC deck's own, unrelated rule dialect, referencing
this project's own named ``Layer`` records instead of Magic types).

The two are genuinely different rule engines, not two views of the
same data -- confirmed real, structural mismatches, not just a naming
difference: Magic's own ``width``/``spacing`` statements can union
several real Magic types on one side (a real, unrepresented-here
boolean OR), Magic's own ``spacing`` supports a real, *different*-
layer separation check (``spacing LAYER1 | LAYER2``) that DRC Rules'
own ``min_spacing`` (``layer.space()``, same-layer only) has no way to
express, Magic's own ``maxwidth``/``angles``/misc drc-section keywords
have no matching real ``check_type`` in ``schema.CHECK_TYPES`` at all,
and Magic's own real mode/exception filler (``touching_ok``/...) has
no KLayout equivalent either. ``copy_magic_drc_check_to_rule`` only
ever copies the real, clean-overlap subset (a single-Magic-type real
``width``, or a real ``spacing`` check where both sides name the same
single type -- true self-spacing) and reports every real mismatch it
finds along the way, blocking or advisory, rather than guessing past
one."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import DesignRule, Layer
from ..schema import CHECK_TYPES
from .magic_tech import CifOutputLayerMapping, MagicDrcCheck

_CHECK_TYPE_MAP = {"width": "min_width", "spacing": "min_spacing"}
_ABBREVIATION = {"width": "W", "spacing": "S"}


@dataclass
class DrcCopyResult:
    rule: DesignRule | None
    """The real ``DesignRule`` to append, or ``None`` when nothing
    should be written -- either genuinely ineligible, or a matching
    rule already exists (see ``messages`` for which)."""

    messages: list[str]
    """Every real coherence note found. When ``rule is None`` these
    are the real, blocking reason(s) nothing was written. When
    ``rule`` is set, these are advisory-only (e.g. a real Magic
    mode/exception filler with no KLayout equivalent) -- the copy
    still happened, this is just what got silently narrowed along the
    way."""


def _resolve_single_type(layer_args: list[list[str]], check_type: str) -> tuple[str | None, list[str]]:
    """The one real Magic type name both a ``width`` and a real,
    true-self ``spacing`` check need -- or ``None`` plus the real,
    blocking reason why no single type could be resolved."""

    if check_type == "width":
        if len(layer_args) != 1 or len(layer_args[0]) != 1:
            union_size = len(layer_args[0]) if layer_args else 0
            return None, [
                f"'width' check unions {union_size} real Magic type(s) on its one side -- "
                "no single KLayout layer expression to map to."
            ]
        return layer_args[0][0], []

    # spacing: two real, ' | '-separated groups.
    if len(layer_args) != 2 or len(layer_args[0]) != 1 or len(layer_args[1]) != 1:
        return None, [
            "'spacing' check unions multiple real Magic types on one side -- "
            "no single KLayout layer expression to map to."
        ]
    type_a, type_b = layer_args[0][0], layer_args[1][0]
    if type_a != type_b:
        return None, [
            f"'spacing' checks two different real Magic types ({type_a!r} vs {type_b!r}) -- "
            "DRC Rules' own min_spacing only checks one real layer against itself "
            "(KLayout's .space()), not a real separation between two different layers."
        ]
    return type_a, []


def copy_magic_drc_check_to_rule(
    check: MagicDrcCheck,
    cif_layers: list[CifOutputLayerMapping],
    project_layers: list[Layer],
    existing_rules: list[DesignRule],
) -> DrcCopyResult:
    """Real coherence check, then (only if it passes) a real
    ``DesignRule`` to append -- never both guessed and written in one
    step. Only ``width``/true-self ``spacing`` checks are ever
    eligible (see this module's own docstring); resolution is Magic
    type name -> a real, bare ``layer NAME TYPE ... calma L D``
    cifoutput pass-through naming that same type on its own
    layer/templayer line (``CifOutputLayerMapping.recipe_types``,
    ``()`` whenever a real geometry recipe sits in between instead --
    see that field's own docstring) -> real GDS layer/datatype -> the
    one real, registered project ``Layer`` sharing that same pair.
    Every real point this can't resolve unambiguously (no real
    pass-through mapping, more than one real GDS pair for the same
    type, no matching registered Layer,
    more than one Layer sharing the same real GDS pair) is reported
    and blocks the copy, rather than picking one and guessing. A
    real, exact-duplicate rule (same check_type/layer/value) already
    present blocks too, so re-running this never creates real
    duplicates."""

    if check.check_type not in _CHECK_TYPE_MAP:
        return DrcCopyResult(None, [
            f"'{check.check_type}' has no real DRC Rules equivalent -- only 'width'/'spacing' can be "
            "copied ('maxwidth' and every other drc-section keyword have no matching check_type in "
            "this project's own schema)."
        ])

    type_name, blocking = _resolve_single_type(check.layer_args, check.check_type)
    if type_name is None:
        return DrcCopyResult(None, blocking)

    matching_cif = [c for c in cif_layers if type_name in c.recipe_types]
    if not matching_cif:
        return DrcCopyResult(None, [
            f"Magic type {type_name!r} has no real, bare 'layer NAME {type_name} ... calma L D' pass-through "
            "in cifoutput -- either it's genuinely absent there, or it only reaches a real calma line through "
            "a real geometry recipe (shrink/or/and-not/...) this project deliberately doesn't model; can't "
            "resolve it to a real GDS layer/datatype either way."
        ])
    pairs = sorted({(c.gds_layer, c.gds_datatype) for c in matching_cif})
    if len(pairs) > 1:
        return DrcCopyResult(None, [
            f"Magic type {type_name!r} maps to {len(pairs)} different real GDS layer/datatype pairs in "
            f"cifoutput ({pairs}) -- ambiguous, not picking one."
        ])
    gds_layer, gds_datatype = pairs[0]

    matching_layers = [
        layer for layer in project_layers
        if layer.gds_layer == gds_layer and layer.gds_datatype == gds_datatype
    ]
    if not matching_layers:
        return DrcCopyResult(None, [
            f"No real Layer registered in Technology > Layers for GDS {gds_layer}/{gds_datatype} "
            f"(resolved from Magic type {type_name!r}) -- add it there first."
        ])
    if len(matching_layers) > 1:
        names = ", ".join(layer.name for layer in matching_layers)
        return DrcCopyResult(None, [
            f"{len(matching_layers)} real Layers share GDS {gds_layer}/{gds_datatype} ({names}) -- "
            "ambiguous, not picking one."
        ])
    layer = matching_layers[0]

    check_type = _CHECK_TYPE_MAP[check.check_type]
    existing = next(
        (
            rule for rule in existing_rules
            if rule.check_type == check_type and rule.layers == [layer.name] and rule.value == check.value_um
        ),
        None,
    )
    if existing is not None:
        return DrcCopyResult(None, [
            f"A matching rule already exists ({existing.rule_id!r}) -- not creating a duplicate."
        ])

    messages: list[str] = []
    if check.filler_raw.strip():
        messages.append(
            f"Magic's own real mode/exception filler ({check.filler_raw!r}) has no KLayout equivalent -- "
            "dropped; the copied rule is a plain min_width/min_spacing check only."
        )

    abbreviation = _ABBREVIATION[check.check_type]
    n = 1 + sum(
        1 for rule in existing_rules if rule.check_type == check_type and rule.layers == [layer.name]
    )
    rule = DesignRule(
        rule_id=f"{layer.name}.{abbreviation}.{n}",
        description=check.message or f"Copied from Magic Tech DRC ({check.check_type}).",
        check_type=check_type,
        layers=[layer.name],
        value=check.value_um,
        units=CHECK_TYPES[check_type].default_units,
        source_provenance=f"Magic Tech DRC ({check.check_type}): type {type_name!r}",
    )
    return DrcCopyResult(rule, messages)

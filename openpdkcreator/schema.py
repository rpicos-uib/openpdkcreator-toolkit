"""Declarative registry for design-rule check types, originally copied
verbatim from OpenPDKCreator's own ``scripts/pdk_wizard/schema.py``
(github.com/rpicos-uib/OpenPDKCreator) -- confirmed fully
technology-agnostic during ADR 0018 research (no field, enum, or
default here is memristor-specific; every entry is a generic DRC
concept -- minimum width/spacing/area/overlap/enclosure, maximum
length/current-density/array-dimension, density-window bound). One
real, deliberate divergence since: ``density_window``'s own
``layer_roles``/``min_layers`` were widened from the original ``()``/
``0`` (which left it with literally no way to attach a real layer to
the rule at all -- see this project's own ``pdklib/drc_writer.py`` for
the real, confirmed reason a density check always needs at least one),
per the "Copy-vs-share, revisited" changelog entry's own conclusion --
keep copying, but diverge when *this* project's own real needs
warrant it, and re-check if the shared data models themselves start to
diverge (see README's own Future Work).

Every place that needs to know "what does a min_enclosure rule mean"
reads it from ``CHECK_TYPES`` here instead of hard-coding it, so
``gui/rules_view.py``/``gui/rule_canvas.py`` never need to change when
a new check type shows up in a real DRC deck (they'd need a new
registry *entry*, not new list/form/diagram code).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckTypeSpec:
    key: str
    label: str
    layer_roles: tuple[str, ...]  # names shown next to each layer picker
    min_layers: int
    max_layers: int | None  # None means unbounded
    default_units: str
    renderer: str  # key into rule_canvas.RENDERERS
    abbreviation: str  # short token used by RulesView's rule_id auto-namer, e.g. "W" for min_width

    def applies_to_text(self, layers: list[str], override: str | None) -> str:
        if override:
            return override
        if not layers:
            return ""
        if self.key == "min_enclosure" and len(layers) >= 2:
            return f"{layers[0]} by {layers[1]}"
        return "+".join(layers)


CHECK_TYPES: dict[str, CheckTypeSpec] = {
    spec.key: spec
    for spec in (
        CheckTypeSpec(
            key="min_width", label="Minimum width", layer_roles=("Layer",),
            min_layers=1, max_layers=1, default_units="um", renderer="width", abbreviation="W",
        ),
        CheckTypeSpec(
            key="min_spacing", label="Minimum spacing", layer_roles=("Layer",),
            min_layers=1, max_layers=1, default_units="um", renderer="spacing", abbreviation="S",
        ),
        CheckTypeSpec(
            key="min_area", label="Minimum area", layer_roles=("Layer", "Layer", "Layer"),
            min_layers=1, max_layers=None, default_units="um2", renderer="area", abbreviation="A",
        ),
        CheckTypeSpec(
            key="min_overlap", label="Minimum overlap", layer_roles=("Layer", "Layer", "Layer"),
            min_layers=2, max_layers=None, default_units="um", renderer="overlap", abbreviation="OV",
        ),
        CheckTypeSpec(
            key="min_enclosure", label="Minimum enclosure", layer_roles=("Inner layer", "Outer layer"),
            min_layers=2, max_layers=2, default_units="um", renderer="enclosure", abbreviation="ENC",
        ),
        CheckTypeSpec(
            key="max_length", label="Maximum unsegmented length", layer_roles=("Layer",),
            min_layers=1, max_layers=1, default_units="um", renderer="max_length", abbreviation="MAX",
        ),
        CheckTypeSpec(
            key="max_current_density", label="Maximum current density", layer_roles=("Layer",),
            min_layers=1, max_layers=1, default_units="A_per_cm2", renderer="current_density", abbreviation="CD",
        ),
        CheckTypeSpec(
            key="max_dimension", label="Maximum array dimension", layer_roles=(),
            min_layers=0, max_layers=None, default_units="count", renderer="max_dimension", abbreviation="DIM",
        ),
        CheckTypeSpec(
            # layer_roles/min_layers widened from the original, upstream
            # copy's (), 0 -- confirmed real, from two independent real
            # PDKs' own density rule decks (IHP SG13G2's own
            # density.drc, GlobalFoundries gf180mcu's own density.rb),
            # a real density check always measures at least one real
            # material layer's own coverage (e.g. gf180mcu's own real
            # `comp + comp_dummy`, summing two). Three "Layer" slots
            # mirrors min_area/min_overlap's own real precedent for
            # "up to a few, summed" rather than a fixed pair/single.
            key="density_window", label="Density window bound", layer_roles=("Layer", "Layer", "Layer"),
            min_layers=1, max_layers=None, default_units="percent", renderer="density_window", abbreviation="DENS",
        ),
    )
}

CHECK_TYPE_ORDER: tuple[str, ...] = tuple(CHECK_TYPES.keys())

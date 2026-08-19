"""Data model for real PDK layer and design-rule information.

``Layer``/``DesignRule`` are copied from OpenPDKCreator's own
``scripts/pdk_wizard/models.py`` (github.com/rpicos-uib/OpenPDKCreator)
-- ``Layer`` is the reliable subset every real KLayout ``.lyp`` entry
has (name, GDS layer/datatype, frame/fill color), plus a few fields
(``purpose``, ``plane``, ``stack_order``, ``streamout_allowed``,
``notes``, ``status``) a human fills in once a layer is more than just
"found in a real .lyp." ``DesignRule`` is unchanged from the sibling
project's own copy -- its schema (rule_id/check_type/layers/value/...)
was already fully technology-agnostic there (confirmed during ADR 0018
research this session: no field or default is memristor-specific).
Copied rather than shared -- see the project README for why -- so this
project is free to extend either as real, non-memristor PDK complexity
demands, without touching the other project's own, ADR-gated schema.

``Layer.start_line``/``end_line`` are this project's own addition (not
present upstream), added for ``pdklib/layers_writer.py``'s own real
write-back -- the same "track a real source position on the dataclass
itself" pattern every other editable domain here already uses (e.g.
``pdklib/lef.py``'s ``LefPin``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

STATUS_PLACEHOLDER = "placeholder"
STATUS_CONFIRMED = "confirmed"
STATUSES = (STATUS_PLACEHOLDER, STATUS_CONFIRMED)


@dataclass
class Layer:
    """A single technology layer."""

    name: str
    gds_layer: int | None = None
    gds_datatype: int | None = None
    purpose: str = "drawing"
    plane: str = "routing"
    stack_order: int = 0
    frame_color: str = "#7f7f7f"
    fill_color: str = "#d9d9d9"
    streamout_allowed: bool | None = None
    notes: str = ""
    status: str = STATUS_PLACEHOLDER
    start_line: int = 0
    """Real, 1-indexed source line of this layer's own real
    ``<properties>`` block in a real ``.lyp`` file (``pdklib/layers.py``'s
    own ``import_layers``) -- ``0`` for a layer with no real source
    position (created this session, or not from a ``.lyp`` at all).
    Used by ``pdklib/layers_writer.py`` to patch just this layer's own
    real text back in place on export."""
    end_line: int = 0
    """Real, 1-indexed, inclusive closing line of the same block."""

    def is_placeholder(self) -> bool:
        return (
            self.status == STATUS_PLACEHOLDER
            or self.gds_layer is None
            or self.gds_datatype is None
            or self.streamout_allowed is None
        )


@dataclass
class DesignRule:
    """A single design rule.

    ``layers`` holds the layer names the rule references, in an order
    whose meaning depends on ``check_type`` (see
    ``schema.CHECK_TYPES[check_type].layer_roles``) -- for example
    ``min_enclosure`` reads ``layers`` as ``[inner, outer]``.

    ``applies_to_override`` lets a rule target something that is not a
    layer at all; when set it is used verbatim in place of a
    layers-derived "applies to" string.

    ``window_size_um``/``window_step_um`` are only meaningful for a
    ``density_window`` rule requesting real, windowed/tiled Ruby
    generation -- see ``pdklib/drc_writer.py``'s own
    ``render_new_rule_block`` docstring for the real, confirmed
    KLayout ``with_density``/``tile_size``/``tile_step`` shapes these
    map to, and why they needed a real, dedicated home here rather
    than being crammed into an existing field. Every other check_type
    leaves both ``None``.
    """

    rule_id: str
    description: str
    check_type: str
    layers: list[str] = field(default_factory=list)
    applies_to_override: str | None = None
    value: float | None = None
    units: str = ""
    net_qualifier: str = "not_applicable"
    classification: str = ""
    condition: str = ""
    process_revision: str = ""
    owner: str = ""
    source_provenance: str = ""
    why: str = ""
    status: str = STATUS_PLACEHOLDER
    window_size_um: float | None = None
    window_step_um: float | None = None

    def is_placeholder(self) -> bool:
        return self.status == STATUS_PLACEHOLDER or self.value is None

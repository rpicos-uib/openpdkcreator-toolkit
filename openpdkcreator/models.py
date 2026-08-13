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

    def is_placeholder(self) -> bool:
        return self.status == STATUS_PLACEHOLDER or self.value is None

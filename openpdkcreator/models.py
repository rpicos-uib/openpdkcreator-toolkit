"""Data model for real PDK layer information.

``Layer`` is copied from OpenPDKCreator's own
``scripts/pdk_wizard/models.py`` (github.com/rpicos-uib/OpenPDKCreator)
-- the reliable subset every real KLayout ``.lyp`` entry has (name,
GDS layer/datatype, frame/fill color), plus a few fields (``purpose``,
``plane``, ``stack_order``, ``streamout_allowed``, ``notes``,
``status``) a human fills in once a layer is more than just "found in
a real .lyp." Copied rather than shared -- see the project README for
why -- so this project is free to extend it as real, non-memristor PDK
complexity demands, without touching the other project's own,
ADR-gated schema.
"""

from __future__ import annotations

from dataclasses import dataclass

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

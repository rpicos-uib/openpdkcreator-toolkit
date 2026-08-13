"""Real KLayout ``.lyp`` layer-properties parsing, adapted from
OpenPDKCreator's own ``scripts/import_open_pdks.py``
(``import_layers()``/``find_lyp()``/``_parse_source()``), which already
proved this logic against real, fetched open_pdks-format `.lyp` files
(including this exact IHP SG13G2 one) -- see
docs/ADR/0017-multi-project-support-and-open-pdks-import.md in that
project.

Deliberately a flat ``<properties>`` scan, not a recursive one: real
KLayout `.lyp` files *can* nest layers inside `<group-members>` blocks
(common for grouped metal stacks), which a flat scan would silently
miss. Checked by hand against IHP's real, downloaded
``libs.tech/klayout/tech/sg13g2.lyp``: zero ``<group-members>``
occurrences, all 377 real ``<properties>`` entries at the top level --
confirmed safe for this file specifically. ``find_group_members`` below
still reports if a *different* `.lyp` ever has any, rather than
silently trusting the flat scan is always correct.
"""

from __future__ import annotations

import datetime
import xml.etree.ElementTree as ET
from pathlib import Path

from ..models import Layer


def find_lyp(pdk_root: Path) -> Path | None:
    candidates = sorted((pdk_root / "libs.tech").glob("**/*.lyp"))
    return candidates[0] if candidates else None


def find_group_members(lyp_path: Path) -> int:
    """Count of <group-members> blocks in *lyp_path* -- 0 for IHP's real
    sg13g2.lyp, confirmed by hand. A non-zero count here means
    import_layers() below is silently missing nested entries; check
    before trusting the returned layer count in that case."""

    tree = ET.parse(lyp_path)
    return len(tree.getroot().findall(".//group-members"))


def _parse_source(source: str) -> tuple[int | None, int | None]:
    """"40/0" or "40/0@1" -> (40, 0). Real open_pdks .lyp files use
    both forms."""

    at_index = source.find("@")
    if at_index != -1:
        source = source[:at_index]
    parts = source.split("/")
    if len(parts) != 2:
        return None, None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None, None


def import_layers(pdk_root: Path, lyp_path: Path) -> list[Layer]:
    """Every real top-level `<properties>` block's name/source/
    frame-color/fill-color -- the reliable subset every real entry has.
    Deliberately does NOT try to split `<name>` into a "layer name" +
    "purpose": a real foundry .lyp's own `<name>` values (e.g.
    "Substrate.drawing") are already KLayout's own unique identifiers,
    with far more distinct trailing segments than a small, fixed
    "purpose" enum could ever enumerate."""

    tree = ET.parse(lyp_path)
    layers: list[Layer] = []
    today = datetime.date.today().isoformat()
    rel = lyp_path.relative_to(pdk_root) if pdk_root in lyp_path.parents else lyp_path
    for props in tree.getroot().findall("properties"):
        name_el = props.find("name")
        source_el = props.find("source")
        if name_el is None or source_el is None or not (name_el.text or "").strip():
            continue
        if not (source_el.text or "").strip():
            continue
        gds_layer, gds_datatype = _parse_source(source_el.text.strip())
        frame_el = props.find("frame-color")
        fill_el = props.find("fill-color")
        layers.append(
            Layer(
                name=name_el.text.strip(),
                gds_layer=gds_layer,
                gds_datatype=gds_datatype,
                purpose="drawing",
                frame_color=(frame_el.text or "#7f7f7f").strip() if frame_el is not None and frame_el.text else "#7f7f7f",
                fill_color=(fill_el.text or "#d9d9d9").strip() if fill_el is not None and fill_el.text else "#d9d9d9",
                status="placeholder",
                notes=f"Imported from {rel} on {today}. Real GDS layer/datatype/color; "
                      f"plane/stack_order/streamout_allowed not derivable from a .lyp "
                      f"and still need a human decision.",
            )
        )
    return layers

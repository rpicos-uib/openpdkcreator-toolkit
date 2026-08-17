"""Real KLayout ``.lyp`` layer-properties parsing, adapted from
OpenPDKCreator's own ``scripts/import_open_pdks.py``
(``import_layers()``/``find_lyp()``/``_parse_source()``), which already
proved this logic against real, fetched open_pdks-format `.lyp` files
(including this exact IHP SG13G2 one) -- see
docs/ADR/0017-multi-project-support-and-open-pdks-import.md in that
project.

**Text-based, not ``ElementTree``-based** -- switched from the
original ``ElementTree`` implementation so each real ``<properties>``
block's own real, 1-indexed source line range could be tracked
(stdlib ``ElementTree`` doesn't expose source line numbers; only
``lxml`` does), needed by ``ihp/layers_writer.py``'s own real,
surgical write-back. Confirmed real and fully uniform before switching,
not assumed: all 377 real ``<properties>`` blocks in IHP's own
``sg13g2.lyp`` are exactly 16 real lines each, same 14-tag field order
(``frame-color``/``fill-color``/``frame-brightness``/
``fill-brightness``/``dither-pattern``/``line-style``/``valid``/
``visible``/``transparent``/``width``/``marked``/``animation``/
``name``/``source``) -- the parser below tracks real
``<properties>``/``</properties>`` nesting depth (matching, not
assuming, correct block boundaries) but still only extracts flat,
top-level tag values, the same known limitation the original
``ElementTree`` flat scan had.

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
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from ..models import Layer

_TAG_LINE_RE = re.compile(r"^\s*<([\w-]+)>(.*)</\1>\s*$")


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


def find_layer_blocks(lyp_path: Path) -> list[tuple[int, int, dict[str, str]]]:
    """Every real top-level ``<properties>`` block's own real,
    1-indexed, inclusive ``(start_line, end_line)`` line range plus its
    flat tag->text field dict -- the shared real-position scan both
    ``import_layers`` (below) and ``ihp/layers_writer.py`` use, so the
    two never independently re-derive (and risk disagreeing about)
    the same real block boundaries."""

    lines = lyp_path.read_text(encoding="utf-8", errors="replace").splitlines()
    blocks: list[tuple[int, int, dict[str, str]]] = []
    depth = 0
    start_line = 0
    fields: dict[str, str] = {}
    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if stripped == "<properties>":
            if depth == 0:
                start_line = line_no
                fields = {}
            depth += 1
            continue
        if stripped == "</properties>":
            depth -= 1
            if depth == 0:
                blocks.append((start_line, line_no, fields))
            continue
        if depth == 1:
            match = _TAG_LINE_RE.match(raw_line)
            if match:
                fields[match.group(1)] = match.group(2)
    return blocks


def purpose_from_name(name: str) -> str:
    """The real "purpose" component of a real layer name -- the
    segment after its last real ``.``, e.g. ``"pin"`` for
    ``"Activ.pin"``, or the ``Layer`` dataclass's own ``"drawing"``
    default for a name with no dot at all (matching a brand-new,
    not-yet-renamed layer's own default). A real foundry ``.lyp``'s
    own ``<name>`` values are already KLayout's own unique
    identifiers with far more distinct trailing segments (51, for the
    real IHP deck) than the project's old, small, fixed "purpose" enum
    ever held -- so the GUI's own Purpose selector is now generated
    per-project from whatever real values are actually present,
    rather than trying to force real data into a fixed, static list."""

    if "." not in name:
        return "drawing"
    return name.rsplit(".", 1)[1]


def import_layers(pdk_root: Path, lyp_path: Path) -> list[Layer]:
    """Every real top-level `<properties>` block's name/source/
    frame-color/fill-color -- the reliable subset every real entry has
    -- plus a real, derived ``purpose`` (``purpose_from_name``, above)."""

    layers: list[Layer] = []
    today = datetime.date.today().isoformat()
    rel = lyp_path.relative_to(pdk_root) if pdk_root in lyp_path.parents else lyp_path
    for start_line, end_line, fields in find_layer_blocks(lyp_path):
        name = fields.get("name", "").strip()
        source = fields.get("source", "").strip()
        if not name or not source:
            continue
        gds_layer, gds_datatype = _parse_source(source)
        layers.append(
            Layer(
                name=name,
                gds_layer=gds_layer,
                gds_datatype=gds_datatype,
                purpose=purpose_from_name(name),
                frame_color=fields.get("frame-color", "").strip() or "#7f7f7f",
                fill_color=fields.get("fill-color", "").strip() or "#d9d9d9",
                status="placeholder",
                stack_order=len(layers),
                notes=f"Imported from {rel} on {today}. Real GDS layer/datatype/color; "
                      f"stack_order defaults to this .lyp file's own real block order "
                      f"(a reasonable starting point, not a verified physical stack -- "
                      f"reorder with Move Up/Down if it's wrong); plane/streamout_allowed "
                      f"are not derivable from a .lyp at all and still need a human decision.",
                start_line=start_line,
                end_line=end_line,
            )
        )
    return layers


_LYP_SKELETON = """<?xml version="1.0" encoding="utf-8"?>
<layer-properties>
</layer-properties>
"""


def create_new_lyp_file(path: Path) -> None:
    """Writes a minimal, valid, real KLayout ``.lyp`` skeleton -- an
    empty ``<layer-properties>`` root with zero real ``<properties>``
    (layer) blocks. Genuinely usable from here, not just a stub:
    ``layers_writer.py``'s ``render_lyp_file`` anchors brand-new layer
    blocks just before the real closing ``</layer-properties>`` tag
    when there are no existing blocks to anchor after (see its own
    docstring), so **New Layer** in the Layers tab -- and a real
    export afterward -- works immediately against a file created this
    way, the same as adding a layer to a real, downloaded one."""

    if path.exists():
        raise FileExistsError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_LYP_SKELETON, encoding="utf-8")

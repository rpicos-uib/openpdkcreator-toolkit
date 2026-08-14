"""Real, bounded GDS structural extraction -- via KLayout's own real
Python API (``klayout.db``), not a hand-rolled binary GDSII parser.
Lazily imported (``_import_klayout_db``): this project's other CLI
commands (``inventory``/``lef``/``drc``/``cells``) have no external
dependency and must keep working even where ``klayout`` isn't
installed (e.g. this project's own host, outside the IIC-OSIC-TOOLS
container that bundles it for real) -- a missing import here raises a
real, honest ``KLayoutUnavailable``, not a silent empty result, since
"there's no GDS data because klayout isn't installed" is a genuinely
different fact than "there's no GDS data because the file has none."

Scope, deliberately bounded the same way every other parser here is:
for each real top-level GDS structure (matched by name against the
same real cell names LEF/CDL/SPICE/Verilog/Liberty already use), its
own real bounding box (microns, via the file's own real database
unit) and a real per-(layer, datatype) shape count. ``Cell.bbox()``
is KLayout's own real, hierarchical bounding box (includes child cell
instances) -- not this module reimplementing geometry math. Shape
counts are direct (shapes drawn on that structure itself), **not**
flattened through instances -- real, honest scope, not full geometry
(polygon vertices, hierarchy expansion, layout rendering); that's
real, separate, much bigger future work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class KLayoutUnavailable(RuntimeError):
    """``klayout.db`` isn't importable in this environment."""


def _import_klayout_db():
    try:
        import klayout.db as db
    except ImportError as exc:
        raise KLayoutUnavailable(
            "klayout.db is not importable -- real GDS parsing needs the real "
            "KLayout Python bindings (present inside the IIC-OSIC-TOOLS "
            "container this project's own start_eda_container.sh launches; "
            "not required for any other command here)."
        ) from exc
    return db


def check_available() -> None:
    """Raises ``KLayoutUnavailable`` with a clear message if
    ``klayout.db`` can't be imported -- lets a caller fail fast with
    one clear message instead of mid-loop."""

    _import_klayout_db()


@dataclass
class GdsCell:
    name: str
    bbox_microns: tuple[float, float, float, float] | None  # (left, bottom, right, top); None if empty
    shapes_by_layer: dict[tuple[int, int], int] = field(default_factory=dict)  # (layer, datatype) -> shape count

    @property
    def total_shapes(self) -> int:
        return sum(self.shapes_by_layer.values())


def find_cells(path: Path) -> dict[str, GdsCell]:
    """Every real top-level GDS structure in *path*, keyed by name.
    Raises ``KLayoutUnavailable`` if ``klayout.db`` isn't importable."""

    db = _import_klayout_db()
    layout = db.Layout()
    layout.read(str(path))
    dbu = layout.dbu
    layer_indexes = list(layout.layer_indexes())

    result: dict[str, GdsCell] = {}
    for cell in layout.each_cell():
        bbox = cell.bbox()
        bbox_microns = (
            None if bbox.empty()
            else (bbox.left * dbu, bbox.bottom * dbu, bbox.right * dbu, bbox.top * dbu)
        )
        shapes_by_layer: dict[tuple[int, int], int] = {}
        for layer_index in layer_indexes:
            count = cell.shapes(layer_index).size()
            if count:
                info = layout.get_info(layer_index)
                shapes_by_layer[(info.layer, info.datatype)] = count
        result[cell.name] = GdsCell(name=cell.name, bbox_microns=bbox_microns, shapes_by_layer=shapes_by_layer)
    return result

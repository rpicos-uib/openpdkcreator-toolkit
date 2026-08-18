"""Cross-reference the two independently-parsed, real (GDS layer, GDS
datatype) mappings this project has: KLayout's own ``.lyp`` (``pdklib/
layers.py``, keyed by display name) and Magic's ``cifoutput`` section
(``pdklib/magic_tech.py``, keyed by Magic CIF layer name). Both describe
the *same* real fabricated GDS stream, from two different tools'
independent points of view -- reconciling them is a real, concrete
answer to "is anything in one tool's view missing from the other's."
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .magic_tech import MagicTechnology
from ..models import Layer

GdsKey = tuple[int, int]


@dataclass
class ReconcileEntry:
    gds_key: GdsKey
    lyp_names: list[str] = field(default_factory=list)
    magic_names: list[str] = field(default_factory=list)


@dataclass
class ReconcileReport:
    matched: list[ReconcileEntry] = field(default_factory=list)
    lyp_only: list[ReconcileEntry] = field(default_factory=list)
    magic_only: list[ReconcileEntry] = field(default_factory=list)


def _lyp_index(layers: list[Layer]) -> dict[GdsKey, list[str]]:
    index: dict[GdsKey, list[str]] = {}
    for layer in layers:
        if layer.gds_layer is None or layer.gds_datatype is None:
            continue
        index.setdefault((layer.gds_layer, layer.gds_datatype), []).append(layer.name)
    return index


def _magic_index(tech: MagicTechnology) -> dict[GdsKey, list[str]]:
    index: dict[GdsKey, list[str]] = {}
    for cif_layer in tech.cif_layers:
        for pair in cif_layer.gds_pairs:
            names = index.setdefault(pair, [])
            if cif_layer.name not in names:
                names.append(cif_layer.name)
    return index


def reconcile(lyp_layers: list[Layer], tech: MagicTechnology) -> ReconcileReport:
    lyp_idx = _lyp_index(lyp_layers)
    magic_idx = _magic_index(tech)

    report = ReconcileReport()
    for gds_key in sorted(set(lyp_idx) | set(magic_idx)):
        lyp_names = lyp_idx.get(gds_key, [])
        magic_names = magic_idx.get(gds_key, [])
        entry = ReconcileEntry(gds_key=gds_key, lyp_names=lyp_names, magic_names=magic_names)
        if lyp_names and magic_names:
            report.matched.append(entry)
        elif lyp_names:
            report.lyp_only.append(entry)
        else:
            report.magic_only.append(entry)
    return report


def print_report(report: ReconcileReport) -> None:
    total = len(report.matched) + len(report.lyp_only) + len(report.magic_only)
    print(
        f"{len(report.matched)}/{total} real (GDS layer, datatype) pairs recognized by "
        f"both KLayout's .lyp and Magic's cifoutput section."
    )
    if report.lyp_only:
        print(f"\n{len(report.lyp_only)} pair(s) only in the .lyp (no matching Magic cifoutput calma):")
        for entry in report.lyp_only:
            print(f"  {entry.gds_key[0]}/{entry.gds_key[1]}: {', '.join(entry.lyp_names)}")
    if report.magic_only:
        print(f"\n{len(report.magic_only)} pair(s) only in Magic's cifoutput (no matching .lyp entry):")
        for entry in report.magic_only:
            print(f"  {entry.gds_key[0]}/{entry.gds_key[1]}: {', '.join(entry.magic_names)}")

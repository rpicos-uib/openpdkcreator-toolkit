"""Real, open_pdks-format export -- the first concrete piece of native
write-back serialization (see README's own Future Work): takes this
session's in-memory, possibly-edited real structures and writes real,
valid, patched files to a new ``export/`` tree, mirroring each file's
own real relative path under its ``pdk_root`` -- never touching the
real, downloaded ``data/`` copy.

Covers LEF pins (``ihp/lef_writer.py``'s own docstring explains
exactly how the patching preserves everything this project's LEF model
doesn't capture) and DRC Rules (``ihp/drc_writer.py``'s own docstring
explains the real ``.drc``-script-vs-JSON-config split). Magic Types
are still genuinely structured-editable and persist via
``project_io.py``, but don't yet write back into the real, native
``.tech`` format -- real, separate future work, tracked in README's
Future Work, not attempted here.
"""

from __future__ import annotations

from pathlib import Path

from .ihp import drc as drc_mod
from .ihp import drc_writer
from .ihp import lef as lef_mod
from .ihp import lef_writer
from .models import DesignRule

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = PROJECT_ROOT / "export"


def export_path_for(pdk_root: Path, source_path: Path) -> Path:
    return EXPORT_ROOT / pdk_root.name / source_path.relative_to(pdk_root)


def export_lef_files(pdk_root: Path, lef_cache: dict[Path, lef_mod.LefFile]) -> list[Path]:
    """Every real ``.lef`` file parsed so far this session (files never
    visited have nothing to export -- they're still exactly their real,
    on-disk starting state, unchanged, and copying them unedited would
    just be noise). Returns the real export paths written."""

    written = []
    for source_path, parsed in lef_cache.items():
        export_path = export_path_for(pdk_root, source_path)
        lef_writer.export_lef_file(parsed, export_path)
        written.append(export_path)
    return written


def export_drc_rules(
    pdk_root: Path, drc_root: Path, design_rules: list[DesignRule],
) -> tuple[list[Path], list[str]]:
    """Every real ``.drc`` file with at least one real, resolvable
    rule (grouped by real source file, all real edits in a file
    applied in one pass) plus the one real JSON config file (if any
    rule's value needs patching there). A rule with no real,
    resolvable provenance (hand-authored via New Rule) can't be
    written back -- returned by ``rule_id`` in the second list, not
    silently dropped."""

    by_relpath: dict[str, list[DesignRule]] = {}
    skipped: list[str] = []
    for rule in design_rules:
        parsed = drc_writer.parse_provenance(rule.source_provenance)
        if parsed is None:
            skipped.append(rule.rule_id)
            continue
        relpath, _check_line, _output_line = parsed
        by_relpath.setdefault(relpath, []).append(rule)

    written: list[Path] = []
    all_value_edits: dict[str, float] = {}
    for relpath, rules in by_relpath.items():
        source_path = pdk_root / relpath
        text, value_edits = drc_writer.render_drc_file(source_path, rules)
        all_value_edits.update(value_edits)
        export_path = export_path_for(pdk_root, source_path)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(text, encoding="utf-8")
        written.append(export_path)

    json_path = drc_mod.find_json_config_path(drc_root)
    if all_value_edits and json_path is not None:
        json_text = drc_writer.render_json_config(json_path, all_value_edits)
        export_json_path = export_path_for(pdk_root, json_path)
        export_json_path.parent.mkdir(parents=True, exist_ok=True)
        export_json_path.write_text(json_text, encoding="utf-8")
        written.append(export_json_path)

    return written, skipped

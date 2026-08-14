"""Real, open_pdks-format export -- the first concrete piece of native
write-back serialization (see README's own Future Work): takes this
session's in-memory, possibly-edited real structures and writes real,
valid, patched files to a new ``export/`` tree, mirroring each file's
own real relative path under its ``pdk_root`` -- never touching the
real, downloaded ``data/`` copy.

Currently covers LEF pins only (``ihp/lef_writer.py``'s own docstring
explains exactly how the patching preserves everything this project's
LEF model doesn't capture). DRC Rules and Magic Types are genuinely
structured-editable and persist via ``project_io.py``, but don't yet
write back into their real, native ``.drc``/``.tech`` formats -- that's
real, separate future work, tracked in README's Future Work, not
attempted here.
"""

from __future__ import annotations

from pathlib import Path

from .ihp import lef as lef_mod
from .ihp import lef_writer

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

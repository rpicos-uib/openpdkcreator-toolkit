"""Program-format persistence for this session's edits (DRC rules,
Magic Types, LEF pins) -- a save/load layer completely separate from
the real, downloaded PDK files under ``data/``, the same "program
format is the single source of truth, real tool files are a separate
concern" philosophy `OpenPDKCreator`'s own `rules_db/` has used from
the start (ADR 0002 in that project).

**Why this exists**: without it, every edit made through DRC Rules/
LEF pins/Magic Types vanishes the moment the GUI is closed -- an
editor whose edits don't survive a relaunch isn't really an editor
yet, and the whole point of this project is eventually authoring a
real PDK, not just browsing one. See README's own Future Work note.

Once a save exists for a given ``pdk_root``, it becomes authoritative
for these three domains on the next launch -- real re-extraction from
``data/`` is still available (``gui/app.py``'s "Re-extract from Real
Files" menu action) but not automatic, the same way a saved file in
any real editor takes precedence over silently re-reading a changed
source until you explicitly discard it.

Saved under a new top-level ``saves/`` directory, not inside ``data/``
(which `ihp/fetch.py` can delete/re-create wholesale -- these are the
user's own authored edits, kept independent of that) -- gitignored for
the same reason `data/` is: derived from a real, third-party PDK's own
real starting values, not this project's own original code.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import yaml

from .ihp.lef import LefPin, LefPort
from .ihp.magic_tech import TypeEntry
from .models import DesignRule

SAVE_DIR = Path(__file__).resolve().parents[1] / "saves"


def save_path_for(pdk_root: Path) -> Path:
    return SAVE_DIR / f"{pdk_root.name}.yaml"


def save_state(
    pdk_root: Path,
    design_rules: list[DesignRule],
    magic_types: dict[str, list[TypeEntry]],
    lef_pins: dict[str, dict[str, list[LefPin]]],
) -> Path:
    """*magic_types*: technology name -> its current Types list.
    *lef_pins*: real .lef path (relative to pdk_root, as a string,
    matching ``LefView.lef_files``'s own keys) -> macro name -> its
    current Pins list."""

    path = save_path_for(pdk_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "drc_rules": [dataclasses.asdict(rule) for rule in design_rules],
        "magic_types": {
            tech_name: [dataclasses.asdict(t) for t in types]
            for tech_name, types in magic_types.items()
        },
        "lef_pins": {
            lef_path: {
                macro_name: [dataclasses.asdict(pin) for pin in pins]
                for macro_name, pins in macros.items()
            }
            for lef_path, macros in lef_pins.items()
        },
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


@dataclasses.dataclass
class LoadedState:
    design_rules: list[DesignRule]
    magic_types: dict[str, list[TypeEntry]]
    lef_pins: dict[str, dict[str, list[LefPin]]]


def _load_lef_pin(raw: dict) -> LefPin:
    ports = [LefPort(**p) for p in raw.get("ports", [])]
    return LefPin(name=raw["name"], direction=raw.get("direction", ""), use=raw.get("use", ""), ports=ports)


def load_state(pdk_root: Path) -> LoadedState | None:
    path = save_path_for(pdk_root)
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    design_rules = [DesignRule(**r) for r in data.get("drc_rules", [])]
    magic_types = {
        tech_name: [TypeEntry(**t) for t in types]
        for tech_name, types in data.get("magic_types", {}).items()
    }
    lef_pins = {
        lef_path: {
            macro_name: [_load_lef_pin(p) for p in pins]
            for macro_name, pins in macros.items()
        }
        for lef_path, macros in data.get("lef_pins", {}).items()
    }
    return LoadedState(design_rules=design_rules, magic_types=magic_types, lef_pins=lef_pins)


def has_saved_state(pdk_root: Path) -> bool:
    return save_path_for(pdk_root).is_file()

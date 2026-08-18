"""Program-format persistence for this session's edits (DRC rules,
Magic Types, LEF pins, Layers) -- a save/load layer completely separate
from the real, downloaded PDK files under ``data/``, the same "program
format is the single source of truth, real tool files are a separate
concern" philosophy `OpenPDKCreator`'s own `rules_db/` has used from
the start (ADR 0002 in that project).

**Why this exists**: without it, every edit made through DRC Rules/
LEF pins/Magic Types/Layers vanishes the moment the GUI is closed -- an
editor whose edits don't survive a relaunch isn't really an editor
yet, and the whole point of this project is eventually authoring a
real PDK, not just browsing one. See README's own Future Work note.
Layers was a real, found gap here for a while: the other three domains
persisted through this module from early on, but Layers edits lived
only in ``app.project.layers`` (in-memory) plus whatever a real
**Export Edited Layers** happened to write to ``export/`` -- a GUI
restart silently lost anything not yet exported. Fixed by adding it
here too, the same shape as the rest.

Once a save exists for a given ``pdk_root``, it becomes authoritative
for these three domains on the next launch -- real re-extraction from
``data/`` is still available (``gui/app.py``'s "Re-extract from Real
Files" menu action) but not automatic, the same way a saved file in
any real editor takes precedence over silently re-reading a changed
source until you explicitly discard it.

Saved under a new top-level ``saves/`` directory, not inside ``data/``
(which `pdklib/fetch.py` can delete/re-create wholesale -- these are the
user's own authored edits, kept independent of that) -- gitignored for
the same reason `data/` is: derived from a real, third-party PDK's own
real starting values, not this project's own original code.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import yaml

from .pdklib.lef import LefPin, LefPort
from .pdklib.magic_tech import (
    AliasEntry, CifInputIgnoredLayer, CifInputLayerHint, CifOutputLayerMapping, ComposeStatement, ConnectRule,
    ContactEntry, ExtractCapCoefficient, ExtractDevice, ExtractMiscStatement, ExtractPlaneOrder, ExtractResist,
    MagicAngleCheck, MagicDrcCheck, PlaneEntry, StyleEntry, TypeEntry,
)
from .models import DesignRule, Layer

SAVE_DIR = Path(__file__).resolve().parents[1] / "saves"


def save_path_for(pdk_root: Path) -> Path:
    return SAVE_DIR / f"{pdk_root.name}.yaml"


def save_state(
    pdk_root: Path,
    design_rules: list[DesignRule],
    magic_types: dict[str, list[TypeEntry]],
    lef_pins: dict[str, dict[str, list[LefPin]]],
    project_name: str = "",
    magic_planes: dict[str, list[PlaneEntry]] | None = None,
    magic_contacts: dict[str, list[ContactEntry]] | None = None,
    magic_aliases: dict[str, list[AliasEntry]] | None = None,
    magic_styles: dict[str, list[StyleEntry]] | None = None,
    magic_compose: dict[str, list[ComposeStatement]] | None = None,
    magic_connect: dict[str, list[ConnectRule]] | None = None,
    magic_cifinput_ignored_layers: dict[str, list[CifInputIgnoredLayer]] | None = None,
    magic_cifinput_layer_hints: dict[str, list[CifInputLayerHint]] | None = None,
    magic_cif_layers: dict[str, list[CifOutputLayerMapping]] | None = None,
    magic_extract_misc: dict[str, list[ExtractMiscStatement]] | None = None,
    magic_extract_plane_order: dict[str, list[ExtractPlaneOrder]] | None = None,
    magic_extract_resist: dict[str, list[ExtractResist]] | None = None,
    magic_extract_cap_coefficients: dict[str, list[ExtractCapCoefficient]] | None = None,
    magic_extract_devices: dict[str, list[ExtractDevice]] | None = None,
    magic_drc_angle_checks: dict[str, list[MagicAngleCheck]] | None = None,
    magic_drc_checks: dict[str, list[MagicDrcCheck]] | None = None,
    layers: dict[str, list[Layer]] | None = None,
) -> Path:
    """*magic_types*: technology name -> its current Types list.
    *magic_planes*/*magic_contacts*/*magic_aliases*/*magic_styles*/
    *magic_compose*/*magic_connect*/*magic_cifinput_ignored_layers*/
    *magic_cifinput_layer_hints*/*magic_cif_layers*/
    *magic_extract_misc*/*magic_extract_plane_order*/
    *magic_extract_resist*/*magic_extract_cap_coefficients*/
    *magic_extract_devices*/*magic_drc_angle_checks*/
    *magic_drc_checks*: the
    same real shape, one dict per newly-editable Magic Tech domain (see
    ``pdklib/magic_tech_writer.py``'s own docstring) -- optional and
    default to empty so existing callers/save files stay valid.
    *lef_pins*: real .lef path (relative to pdk_root, as a string,
    matching ``LefView.lef_files``'s own keys) -> macro name -> its
    current Pins list. *layers*: real ``.lyp`` path (relative to
    pdk_root, as a string -- there can be more than one, same real
    "New .lyp File..." precedent multiple Magic technologies already
    have) -> its current Layer list. Without this, a Layers edit was
    the one domain among DRC Rules/Magic Types/LEF pins/Layers that
    silently vanished on relaunch -- a real, found inconsistency (see
    ``gui/layers_view.py``'s own docstring for how it was found).
    *project_name*: the user's own editable label for this project
    (Settings tab) -- deliberately separate from ``pdk_root.name``,
    the real, immutable source PDK's own name (see
    ``gui/settings_view.py``'s own docstring for why the two are kept
    visibly distinct)."""

    path = save_path_for(pdk_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "project_name": project_name,
        "drc_rules": [dataclasses.asdict(rule) for rule in design_rules],
        "magic_types": {
            tech_name: [dataclasses.asdict(t) for t in types]
            for tech_name, types in magic_types.items()
        },
        "magic_planes": {
            tech_name: [dataclasses.asdict(p) for p in planes]
            for tech_name, planes in (magic_planes or {}).items()
        },
        "magic_contacts": {
            tech_name: [dataclasses.asdict(c) for c in contacts]
            for tech_name, contacts in (magic_contacts or {}).items()
        },
        "magic_aliases": {
            tech_name: [dataclasses.asdict(a) for a in aliases]
            for tech_name, aliases in (magic_aliases or {}).items()
        },
        "magic_styles": {
            tech_name: [dataclasses.asdict(s) for s in styles]
            for tech_name, styles in (magic_styles or {}).items()
        },
        "magic_compose": {
            # args is a real, fixed 3-tuple -- yaml.safe_dump has no
            # default representer for a plain tuple (only list/dict/
            # scalars), so it's cast to a list here, same real reason
            # ComposeStatement.arg1/arg2/arg3 exist as properties for
            # the GUI editor rather than editing the tuple in place.
            tech_name: [{**dataclasses.asdict(c), "args": list(c.args)} for c in statements]
            for tech_name, statements in (magic_compose or {}).items()
        },
        "magic_connect": {
            tech_name: [dataclasses.asdict(r) for r in rules]
            for tech_name, rules in (magic_connect or {}).items()
        },
        "magic_cifinput_ignored_layers": {
            tech_name: [dataclasses.asdict(layer) for layer in layers_list]
            for tech_name, layers_list in (magic_cifinput_ignored_layers or {}).items()
        },
        "magic_cifinput_layer_hints": {
            tech_name: [dataclasses.asdict(hint) for hint in hints]
            for tech_name, hints in (magic_cifinput_layer_hints or {}).items()
        },
        "magic_cif_layers": {
            tech_name: [dataclasses.asdict(mapping) for mapping in mappings]
            for tech_name, mappings in (magic_cif_layers or {}).items()
        },
        "magic_extract_misc": {
            # args is a real, variable-length tuple -- same real reason
            # magic_compose casts its own fixed 3-tuple to a list here
            # (yaml.safe_dump has no default representer for a plain
            # tuple).
            tech_name: [{**dataclasses.asdict(m), "args": list(m.args)} for m in statements]
            for tech_name, statements in (magic_extract_misc or {}).items()
        },
        "magic_extract_plane_order": {
            tech_name: [dataclasses.asdict(o) for o in orders]
            for tech_name, orders in (magic_extract_plane_order or {}).items()
        },
        "magic_extract_resist": {
            tech_name: [dataclasses.asdict(r) for r in entries]
            for tech_name, entries in (magic_extract_resist or {}).items()
        },
        "magic_extract_cap_coefficients": {
            # args/values are both real tuples -- same real reason
            # magic_compose/magic_extract_misc cast their own tuples to
            # lists here.
            tech_name: [
                {**dataclasses.asdict(c), "args": list(c.args), "values": list(c.values)} for c in coefficients
            ]
            for tech_name, coefficients in (magic_extract_cap_coefficients or {}).items()
        },
        "magic_extract_devices": {
            # rest is a real, variable-length tuple -- same real reason
            # magic_extract_misc casts its own tuple to a list here.
            tech_name: [{**dataclasses.asdict(d), "rest": list(d.rest)} for d in devices]
            for tech_name, devices in (magic_extract_devices or {}).items()
        },
        "magic_drc_angle_checks": {
            tech_name: [dataclasses.asdict(a) for a in checks]
            for tech_name, checks in (magic_drc_angle_checks or {}).items()
        },
        "magic_drc_checks": {
            # layer_args is a real, plain list[list[str]] already --
            # unlike every tuple-typed field elsewhere in this module,
            # yaml.safe_dump handles it natively, no casting needed.
            tech_name: [dataclasses.asdict(c) for c in checks]
            for tech_name, checks in (magic_drc_checks or {}).items()
        },
        "lef_pins": {
            lef_path: {
                macro_name: [dataclasses.asdict(pin) for pin in pins]
                for macro_name, pins in macros.items()
            }
            for lef_path, macros in lef_pins.items()
        },
        "layers": {
            lyp_path: [dataclasses.asdict(layer) for layer in layer_list]
            for lyp_path, layer_list in (layers or {}).items()
        },
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


@dataclasses.dataclass
class LoadedState:
    design_rules: list[DesignRule]
    magic_types: dict[str, list[TypeEntry]]
    lef_pins: dict[str, dict[str, list[LefPin]]]
    project_name: str = ""
    magic_planes: dict[str, list[PlaneEntry]] = dataclasses.field(default_factory=dict)
    magic_contacts: dict[str, list[ContactEntry]] = dataclasses.field(default_factory=dict)
    magic_aliases: dict[str, list[AliasEntry]] = dataclasses.field(default_factory=dict)
    magic_styles: dict[str, list[StyleEntry]] = dataclasses.field(default_factory=dict)
    magic_compose: dict[str, list[ComposeStatement]] = dataclasses.field(default_factory=dict)
    magic_connect: dict[str, list[ConnectRule]] = dataclasses.field(default_factory=dict)
    magic_cifinput_ignored_layers: dict[str, list[CifInputIgnoredLayer]] = dataclasses.field(default_factory=dict)
    magic_cifinput_layer_hints: dict[str, list[CifInputLayerHint]] = dataclasses.field(default_factory=dict)
    magic_cif_layers: dict[str, list[CifOutputLayerMapping]] = dataclasses.field(default_factory=dict)
    magic_extract_misc: dict[str, list[ExtractMiscStatement]] = dataclasses.field(default_factory=dict)
    magic_extract_plane_order: dict[str, list[ExtractPlaneOrder]] = dataclasses.field(default_factory=dict)
    magic_extract_resist: dict[str, list[ExtractResist]] = dataclasses.field(default_factory=dict)
    magic_extract_cap_coefficients: dict[str, list[ExtractCapCoefficient]] = dataclasses.field(default_factory=dict)
    magic_extract_devices: dict[str, list[ExtractDevice]] = dataclasses.field(default_factory=dict)
    magic_drc_angle_checks: dict[str, list[MagicAngleCheck]] = dataclasses.field(default_factory=dict)
    magic_drc_checks: dict[str, list[MagicDrcCheck]] = dataclasses.field(default_factory=dict)
    layers: dict[str, list[Layer]] = dataclasses.field(default_factory=dict)


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
    magic_planes = {
        tech_name: [PlaneEntry(**p) for p in planes]
        for tech_name, planes in data.get("magic_planes", {}).items()
    }
    magic_contacts = {
        tech_name: [ContactEntry(**c) for c in contacts]
        for tech_name, contacts in data.get("magic_contacts", {}).items()
    }
    magic_aliases = {
        tech_name: [AliasEntry(**a) for a in aliases]
        for tech_name, aliases in data.get("magic_aliases", {}).items()
    }
    magic_styles = {
        tech_name: [StyleEntry(**s) for s in styles]
        for tech_name, styles in data.get("magic_styles", {}).items()
    }
    magic_compose = {
        tech_name: [ComposeStatement(**{**c, "args": tuple(c["args"])}) for c in statements]
        for tech_name, statements in data.get("magic_compose", {}).items()
    }
    magic_connect = {
        tech_name: [ConnectRule(**r) for r in rules]
        for tech_name, rules in data.get("magic_connect", {}).items()
    }
    magic_cifinput_ignored_layers = {
        tech_name: [CifInputIgnoredLayer(**layer) for layer in layers_list]
        for tech_name, layers_list in data.get("magic_cifinput_ignored_layers", {}).items()
    }
    magic_cifinput_layer_hints = {
        tech_name: [CifInputLayerHint(**hint) for hint in hints]
        for tech_name, hints in data.get("magic_cifinput_layer_hints", {}).items()
    }
    magic_cif_layers = {
        tech_name: [CifOutputLayerMapping(**mapping) for mapping in mappings]
        for tech_name, mappings in data.get("magic_cif_layers", {}).items()
    }
    magic_extract_misc = {
        tech_name: [ExtractMiscStatement(**{**m, "args": tuple(m["args"])}) for m in statements]
        for tech_name, statements in data.get("magic_extract_misc", {}).items()
    }
    magic_extract_plane_order = {
        tech_name: [ExtractPlaneOrder(**o) for o in orders]
        for tech_name, orders in data.get("magic_extract_plane_order", {}).items()
    }
    magic_extract_resist = {
        tech_name: [ExtractResist(**r) for r in entries]
        for tech_name, entries in data.get("magic_extract_resist", {}).items()
    }
    magic_extract_cap_coefficients = {
        tech_name: [
            ExtractCapCoefficient(**{**c, "args": tuple(c["args"]), "values": tuple(c["values"])})
            for c in coefficients
        ]
        for tech_name, coefficients in data.get("magic_extract_cap_coefficients", {}).items()
    }
    magic_extract_devices = {
        tech_name: [ExtractDevice(**{**d, "rest": tuple(d["rest"])}) for d in devices]
        for tech_name, devices in data.get("magic_extract_devices", {}).items()
    }
    magic_drc_angle_checks = {
        tech_name: [MagicAngleCheck(**a) for a in checks]
        for tech_name, checks in data.get("magic_drc_angle_checks", {}).items()
    }
    magic_drc_checks = {
        tech_name: [MagicDrcCheck(**c) for c in checks]
        for tech_name, checks in data.get("magic_drc_checks", {}).items()
    }
    lef_pins = {
        lef_path: {
            macro_name: [_load_lef_pin(p) for p in pins]
            for macro_name, pins in macros.items()
        }
        for lef_path, macros in data.get("lef_pins", {}).items()
    }
    layers = {
        lyp_path: [Layer(**layer) for layer in layer_list]
        for lyp_path, layer_list in data.get("layers", {}).items()
    }
    return LoadedState(
        design_rules=design_rules, magic_types=magic_types, lef_pins=lef_pins,
        project_name=data.get("project_name", ""),
        magic_planes=magic_planes, magic_contacts=magic_contacts, magic_aliases=magic_aliases,
        magic_styles=magic_styles, magic_compose=magic_compose, magic_connect=magic_connect,
        magic_cifinput_ignored_layers=magic_cifinput_ignored_layers,
        magic_cifinput_layer_hints=magic_cifinput_layer_hints,
        magic_cif_layers=magic_cif_layers,
        magic_extract_misc=magic_extract_misc,
        magic_extract_plane_order=magic_extract_plane_order,
        magic_extract_resist=magic_extract_resist,
        magic_extract_cap_coefficients=magic_extract_cap_coefficients,
        magic_extract_devices=magic_extract_devices,
        magic_drc_angle_checks=magic_drc_angle_checks,
        magic_drc_checks=magic_drc_checks,
        layers=layers,
    )


def has_saved_state(pdk_root: Path) -> bool:
    return save_path_for(pdk_root).is_file()

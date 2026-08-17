"""A real-file-location index for the Library Manager tab -- tracks
*where* each cell's own real view actually lives, real and
project-authored alike, rather than requiring project content to
mirror any fixed directory convention.

**Why an index, not a new directory convention** (a real, explicit
design decision, not a default): real library/family naming is
already inconsistent across this PDK's own real tool domains --
``libs.ref/`` uses ``sg13g2_stdcell`` (singular); ``libs.tech/xschem/``
uses ``sg13g2_stdcells`` (plural, and has no ``_io``/``_sram`` dir at
all); ``libs.tech/qucs-s/symbols/`` is flat, no per-family split
whatsoever (see ``ihp/cells.py``'s own docstring for exactly how
``build_cell_index`` already works around this by matching real
xschem/Qucs-S files to a cell by *name*, not by directory). Forcing
new, project-authored content into a directory layout modeled on
``libs.ref/<family>/<view>/`` would buy nothing real -- it wouldn't
even match this PDK's *own* real conventions consistently. Tracking
wherever a file actually is, in a small, real, tracked index instead,
sidesteps the inconsistency entirely.

**Two kinds of ``ViewEntry``, merged, never silently shadowing each
other the wrong way**:

- ``source="real"`` -- auto-discovered fresh every call from
  *pdk_root* itself (never persisted -- it's just a live reflection of
  the real, downloaded PDK's own current state, same "cheap glob,
  recomputed live" discipline as everywhere else in this project).
  Built by flattening ``ihp/cells.py``'s own ``build_cell_index``
  output -- reused, not duplicated; this module owns no parsing logic
  of its own.
- ``source="registered"`` -- user-added via the Library Manager's own
  **New Library**/**New Cell**/**Create** actions, persisted in a
  small, real, tracked (not gitignored) YAML file at the project root,
  ``library_index.yaml`` -- the same tracked-project-content precedent
  ``user_models/links.yaml`` already established. A file registered
  this way can live anywhere on disk; nothing here requires or assumes
  a particular location.

When both exist for the same ``(library, cell, view_kind)``, **real
wins** -- a registered entry never silently shadows a real, downloaded
PDK file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import cells as cells_mod
from . import lef as lef_mod
from . import mag as mag_mod
from . import verilog as verilog_mod
from . import xschem as xschem_mod

REGISTRY_FILENAME = "library_index.yaml"
LIBRARIES_DIRNAME = "libraries"
"""Default home for a newly-**Create**d view's own real file
(``<project_root>/libraries/<library>/<cell>.<ext>``) -- a real,
tracked, but entirely optional convention. Nothing elsewhere requires
it: ``register_entry``/**Add...** accept a real file anywhere on disk;
this is also the one real directory ``scan_for_unregistered_files``
(below) actually looks in for files this app didn't itself create --
see that function's own docstring for why a wider, unbounded real-
filesystem scan isn't attempted."""

VIEW_KIND_LABELS: dict[str, str] = {
    "xschem_schematic": "Schematic",
    "xschem_symbol": "Symbol",
    "qucs_symbol": "Qucs-S Symbol",
    "qucs_component": "Qucs-S Component",
    "lef": "LEF",
    "cdl": "CDL",
    "spice": "SPICE",
    "verilog": "Verilog",
    "veriloga": "Verilog-A",
    "liberty": "Liberty",
    "mag": "Magic Layout",
    "gds": "GDS/Layout",
}
VIEW_KIND_ORDER: tuple[str, ...] = tuple(VIEW_KIND_LABELS.keys())
"""Real create-from-scratch support exists (this session, verified)
only for these seven -- ``ihp/cells.py``'s own docstring/every other
writer's own real ``start_line == 0`` skip explains why the rest
don't yet. Verilog/Verilog-A were added later than the original four
xschem/Qucs-S ones -- see ``create_new_verilog_file``/
``create_new_veriloga_file`` in ``ihp/verilog.py`` and
``infer_ports_for_cell`` below for how a newly-created one gets a
real cell's own already-known pins pre-populated, not an empty
template. ``mag`` (Magic Layout) was added later still -- see
``ihp/mag.py``'s own ``create_new_mag_file``; unlike every other real
view here, a newly-created one is *not* meant to be edited in this
Python GUI at all, only opened in real Magic to actually draw real
geometry (the same "Create an empty skeleton, do the real work in the
real external tool" pattern xschem/Qucs-S Symbol/Schematic already
established)."""
CREATABLE_VIEW_KINDS: frozenset[str] = frozenset(
    {"xschem_symbol", "xschem_schematic", "qucs_symbol", "qucs_component", "verilog", "veriloga", "mag"}
)


@dataclass
class ViewEntry:
    library: str
    cell: str
    view_kind: str
    path: Path
    source: str = "registered"
    """``"real"`` (auto-discovered, never persisted) or
    ``"registered"`` (user-added, persisted in ``library_index.yaml``)."""


def discover_real_entries_for_family(pdk_root: Path, family: str) -> list[ViewEntry]:
    """Every real view for *family* alone (``ihp/cells.py``'s own
    ``build_cell_index``, reused not duplicated) -- deliberately
    scoped to one real family at a time, not the whole deck, matching
    ``gui/cell_hub_view.py``'s own lazy, per-family loading
    (``sg13g2_sram`` alone has 2342 real cells; building every real
    family's own index just to list one library's views would be
    wasteful). Real, parsed content (``lef_macro``, ``gds_cell``, ...)
    is discarded here -- this index only ever tracks *where* a view's
    real file is, never its own parsed content; the existing tabs
    (LEF/By Cell/xschem/Qucs-S) already own that."""

    entries: list[ViewEntry] = []
    index = cells_mod.build_cell_index(pdk_root, family)
    for cell_name, cv in index.items():
        if cv.xschem_schematic_source:
            entries.append(ViewEntry(family, cell_name, "xschem_schematic", cv.xschem_schematic_source, "real"))
        if cv.xschem_symbol_source:
            entries.append(ViewEntry(family, cell_name, "xschem_symbol", cv.xschem_symbol_source, "real"))
        if cv.qucs_symbol_source:
            entries.append(ViewEntry(family, cell_name, "qucs_symbol", cv.qucs_symbol_source, "real"))
        if cv.qucs_component_source:
            entries.append(ViewEntry(family, cell_name, "qucs_component", cv.qucs_component_source, "real"))
        if cv.lef_source:
            entries.append(ViewEntry(family, cell_name, "lef", cv.lef_source, "real"))
        if cv.cdl_source:
            entries.append(ViewEntry(family, cell_name, "cdl", cv.cdl_source, "real"))
        if cv.spice_source:
            entries.append(ViewEntry(family, cell_name, "spice", cv.spice_source, "real"))
        if cv.verilog_source:
            entries.append(ViewEntry(family, cell_name, "verilog", cv.verilog_source, "real"))
        if cv.liberty_entries:
            # Multiple real corner files can exist; this index tracks
            # presence/one real path to open, not every corner -- the
            # Liberty tab itself is the real place to browse all of them.
            entries.append(ViewEntry(family, cell_name, "liberty", cv.liberty_entries[0][1], "real"))
        if cv.gds_source:
            entries.append(ViewEntry(family, cell_name, "gds", cv.gds_source, "real"))
        # cv.gds_present without cv.gds_source (a real, combined
        # multi-cell GDS with no confirmed per-cell membership -- see
        # ihp/cells.py's own docstring) is deliberately not indexed:
        # pointing every cell at the same shared file would mislead.

    # Magic .mag layouts: matched by real cell name (file stem), same
    # "enrich an already-known cell, never introduce a new one" real
    # boundary xschem/Qucs-S already have -- ihp/cells.py's own
    # CellViews has no mag_source field (this is a Library-Manager-
    # only view kind), so this can't reuse build_cell_index's own
    # output the way every other real view kind above does.
    for mag_path in mag_mod.find_mag_files(pdk_root):
        if mag_path.parent.parent.name == family and mag_path.stem in index:
            entries.append(ViewEntry(family, mag_path.stem, "mag", mag_path, "real"))

    return entries


# -- registered (project-authored) entries, persisted -----------------------


@dataclass
class LibraryRegistry:
    libraries: list[str] = field(default_factory=list)
    """Every registered library name, including one with zero
    registered entries yet -- so a brand-new, still-empty library
    (**New Library**) is real and selectable before any cell/view
    exists in it."""
    entries: list[ViewEntry] = field(default_factory=list)


def registry_path(project_root: Path) -> Path:
    return project_root / REGISTRY_FILENAME


def load_registry(project_root: Path) -> LibraryRegistry:
    path = registry_path(project_root)
    if not path.is_file():
        return LibraryRegistry()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    libraries = list(data.get("libraries") or [])
    entries = [
        ViewEntry(
            library=e["library"], cell=e["cell"], view_kind=e["view_kind"],
            path=Path(e["path"]), source="registered",
        )
        for e in (data.get("entries") or [])
    ]
    return LibraryRegistry(libraries=libraries, entries=entries)


def save_registry(project_root: Path, registry: LibraryRegistry) -> Path:
    path = registry_path(project_root)
    data = {
        "libraries": registry.libraries,
        "entries": [
            {"library": e.library, "cell": e.cell, "view_kind": e.view_kind, "path": str(e.path)}
            for e in registry.entries
        ],
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def register_library(project_root: Path, name: str) -> LibraryRegistry:
    registry = load_registry(project_root)
    if name not in registry.libraries:
        registry.libraries.append(name)
        save_registry(project_root, registry)
    return registry


def register_entry(project_root: Path, library: str, cell: str, view_kind: str, path: Path) -> LibraryRegistry:
    """Adds (or replaces, if one already exists for the same real
    ``(library, cell, view_kind)`` key) a registered entry, and
    registers *library* itself too if it wasn't already."""

    registry = load_registry(project_root)
    if library not in registry.libraries:
        registry.libraries.append(library)
    registry.entries = [
        e for e in registry.entries
        if not (e.library == library and e.cell == cell and e.view_kind == view_kind)
    ]
    registry.entries.append(ViewEntry(library, cell, view_kind, path, "registered"))
    save_registry(project_root, registry)
    return registry


def unregister_entry(project_root: Path, library: str, cell: str, view_kind: str) -> LibraryRegistry:
    registry = load_registry(project_root)
    registry.entries = [
        e for e in registry.entries
        if not (e.library == library and e.cell == cell and e.view_kind == view_kind)
    ]
    save_registry(project_root, registry)
    return registry


# -- merged view (what the GUI actually shows) -------------------------------


def merged_libraries(pdk_root: Path, project_root: Path) -> list[tuple[str, bool]]:
    """Every real family plus every registered library, sorted, as
    ``(name, is_real)`` -- ``is_real`` distinguishes a real,
    downloaded-PDK library from a project-authored one in the GUI."""

    real = set(cells_mod.discover_families(pdk_root))
    registry = load_registry(project_root)
    all_names = real | set(registry.libraries)
    return sorted((name, name in real) for name in all_names)


def merged_entries(pdk_root: Path, project_root: Path, library: str) -> dict[tuple[str, str], ViewEntry]:
    """Every real (if *library* is a real family) plus every
    registered ``ViewEntry`` for *library*, keyed by ``(cell,
    view_kind)`` -- real wins if both exist for the same key (see this
    module's own docstring)."""

    result: dict[tuple[str, str], ViewEntry] = {}
    registry = load_registry(project_root)
    for entry in registry.entries:
        if entry.library == library:
            result[(entry.cell, entry.view_kind)] = entry
    if library in cells_mod.discover_families(pdk_root):
        for entry in discover_real_entries_for_family(pdk_root, library):
            result[(entry.cell, entry.view_kind)] = entry
    return result


def cells_in_library(pdk_root: Path, project_root: Path, library: str) -> list[str]:
    return sorted({cell for cell, _view_kind in merged_entries(pdk_root, project_root, library)})


_DIRECTION_TO_VERILOG: dict[str, str] = {
    "input": "input", "in": "input",
    "output": "output", "out": "output",
    "inout": "inout",
}
"""Normalizes the two real, confirmed pin-direction vocabularies this
project actually has -- LEF's own real ``DIRECTION`` values
(``INPUT``/``OUTPUT``/``INOUT``, uppercase, confirmed via
``grep -h DIRECTION .../sg13g2_stdcell/lef/*.lef`` -- note LEF also has
an unrelated, same-keyworded ``DIRECTION HORIZONTAL``/``VERTICAL`` at
the *layer* level, never reached here since this only ever reads
``LefPin.direction``, not layer text) and xschem's own real ``dir=``
values (``in``/``out``/``inout``, lowercase, confirmed via
``grep -oh dir=... .../sg13g2_stdcells/*.sym``) -- down to Verilog's own
real ``input``/``output``/``inout`` keywords. Matched case-insensitively
so either vocabulary works through the same table. An unrecognized
value normalizes to ``""`` (honestly undeclared), never guessed."""


def _normalize_direction(raw: str) -> str:
    return _DIRECTION_TO_VERILOG.get((raw or "").strip().lower(), "")


def infer_ports_for_cell(pdk_root: Path, project_root: Path, library: str, cell: str) -> list[tuple[str, str]]:
    """Best-effort real port list (``[(name, direction), ...]``,
    direction one of ``"input"``/``"output"``/``"inout"``/``""``) for
    *cell*, used to pre-populate a newly **Create**d Verilog/Verilog-A
    view with that cell's own already-known real pins instead of an
    empty template -- see ``ihp/verilog.py``'s own
    ``create_new_verilog_file``/``create_new_veriloga_file``.

    Tries each of this cell's own already-known real/registered views,
    in priority order, stopping at the first one with a real, non-empty
    port list -- never inventing a name that isn't in one of them:

    1. **LEF** -- the most authoritative real *physical* pin list for
       an actual, placeable cell.
    2. **xschem symbol** -- the schematic-level pin list, for a cell
       with no LEF yet (e.g. a still-schematic-only project cell).
    3. **An existing Verilog module of the same name** -- covers the
       real case of creating a Verilog-A view for a cell that already
       has a plain digital Verilog one, or vice versa.

    Returns ``[]`` (an honestly empty template) for a wholly new cell
    with no other real view yet."""

    entries = merged_entries(pdk_root, project_root, library)

    lef_entry = entries.get((cell, "lef"))
    if lef_entry is not None and lef_entry.path.is_file():
        lef_file = lef_mod.parse_lef_file(lef_entry.path)
        macro = next((m for m in lef_file.macros if m.name == cell), None)
        if macro is not None and macro.pins:
            return [(pin.name, _normalize_direction(pin.direction)) for pin in macro.pins]

    xschem_entry = entries.get((cell, "xschem_symbol"))
    if xschem_entry is not None and xschem_entry.path.is_file():
        symbol = xschem_mod.parse_sym_file(xschem_entry.path)
        if symbol.pins:
            return [(pin.name, _normalize_direction(pin.direction)) for pin in symbol.pins]

    for view_kind in ("verilog", "veriloga"):
        verilog_entry = entries.get((cell, view_kind))
        if verilog_entry is not None and verilog_entry.path.is_file():
            module = next((m for m in verilog_mod.find_modules(verilog_entry.path) if m.name == cell), None)
            if module is not None and module.ports:
                return [(p.name, p.direction) for p in module.ports]

    return []


# -- auto-tracking: pick up a real file this app didn't itself create -------

_EXT_TO_UNAMBIGUOUS_VIEW_KIND: dict[str, str] = {
    ".sch": "xschem_schematic",
    ".xml": "qucs_component",
    ".lef": "lef",
    ".cdl": "cdl",
    ".spice": "spice",
    ".v": "verilog",
    ".lib": "liberty",
    ".mag": "mag",
    ".gds": "gds",
}


def infer_view_kind(path: Path) -> str | None:
    """Real, content-sniffed disambiguation for the one genuine
    ambiguity among real file extensions here: both xschem and Qucs-S
    use a real ``.sym`` extension. Confirmed real, not assumed (read
    directly off real files in this project's own downloaded PDK): a
    real xschem ``.sym`` always starts with ``v {xschem``; a real
    Qucs-S ``.sym`` starts with a bare drawing tag (``<Line``/``<Arc``/
    ``<PortSym``/...), no XML declaration at all. Every other real
    extension already maps to exactly one view kind. Returns ``None``
    for anything unrecognized -- never guessed."""

    if path.suffix in _EXT_TO_UNAMBIGUOUS_VIEW_KIND:
        return _EXT_TO_UNAMBIGUOUS_VIEW_KIND[path.suffix]
    if path.suffix == ".sym":
        try:
            head = path.read_text(encoding="utf-8", errors="replace")[:32].lstrip()
        except OSError:
            return None
        if head.startswith("v {xschem"):
            return "xschem_symbol"
        if head.startswith("<"):
            return "qucs_symbol"
    return None


def scan_for_unregistered_files(project_root: Path, library: str) -> list[ViewEntry]:
    """Real, not-yet-registered files under *library*'s own default
    ``libraries/<library>/`` directory (see ``LIBRARIES_DIRNAME``'s own
    docstring for why only this one, real, tool-written-to directory
    is scanned, not an unbounded real-filesystem search) -- for
    picking up a file some *other* tool wrote there directly (e.g. a
    real "Save As" in xschem into this library's own default
    directory) that this app's own **Create**/**Add...** actions never
    registered. Cell name is the real file's own stem; view kind via
    ``infer_view_kind`` -- a file this can't identify is skipped, not
    guessed."""

    lib_dir = project_root / LIBRARIES_DIRNAME / library
    if not lib_dir.is_dir():
        return []
    registry = load_registry(project_root)
    known_paths = {e.path for e in registry.entries if e.library == library}
    found: list[ViewEntry] = []
    for path in sorted(lib_dir.iterdir()):
        if not path.is_file() or path in known_paths:
            continue
        view_kind = infer_view_kind(path)
        if view_kind is None:
            continue
        found.append(ViewEntry(library, path.stem, view_kind, path, "registered"))
    return found


def auto_register_new_files(project_root: Path, library: str) -> list[ViewEntry]:
    """Runs ``scan_for_unregistered_files`` and registers whatever it
    finds immediately -- called on every real refresh (see
    ``gui/library_manager_view.py``'s own ``refresh_cells``), not just
    behind an explicit user action, so a file created by some other
    tool is picked up automatically the next time this library is
    viewed. Returns the newly-registered entries (empty if none)."""

    found = scan_for_unregistered_files(project_root, library)
    if not found:
        return []
    registry = load_registry(project_root)
    for entry in found:
        registry.entries = [
            e for e in registry.entries
            if not (e.library == entry.library and e.cell == entry.cell and e.view_kind == entry.view_kind)
        ]
        registry.entries.append(entry)
    save_registry(project_root, registry)
    return found

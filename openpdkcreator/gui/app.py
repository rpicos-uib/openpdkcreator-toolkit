"""Minimal Tk shell over a real, downloaded IHP-style PDK tree, tabs
grouped by what they actually represent rather than left flat:

- **Overview** -- the real, per-tool file inventory, spanning every
  tool/domain (including ones with no dedicated view yet, e.g.
  libs.ref/'s cell libraries, libs.doc/).
- **Technology** -- process/technology-definition data specifically,
  one sub-tab per tool that defines it: **Layers** (KLayout's real
  ``.lyp``), **Magic Tech** (Magic's real ``.tech`` files), and
  **DRC Rules** (a real KLayout DRC deck, best-effort extracted --
  ``ihp/drc.py``) -- reusing OpenPDKCreator's own Design Rules tab
  (``RulesView``/``rule_canvas.py``), the same "reuse the existing
  interface" pattern ``LayersView`` already established, just against
  a real, pre-extracted starting set instead of an empty one.
- **Cells** -- real cell/macro data, two sub-tabs: **LEF** (tech-layer
  routing rules plus real macro/cell footprints with editable pins) and
  **By Cell** (``CellHubView``/``ihp/cells.py``) -- a hierarchical,
  cell-centric picture: pick one real cell, see which of its real views
  (LEF/CDL/SPICE/Verilog/Liberty/GDS) actually exist across
  ``libs.ref/<family>/*/``, jump straight to that cell's own real block
  inside each one, and edit its real LEF pins directly -- the exact
  same in-memory macro the LEF tab itself edits (see
  ``App.get_parsed_lef`` below).
- **Settings** -- project-level settings, not any one tool's PDK
  content (``gui/settings_view.py``): this project's own editable name
  and where it lives on disk, versus the real source PDK's own
  (read-only) name and location -- see that module's own docstring for
  why those two pairs are kept deliberately distinct.

Deliberately no "Simulation" top-level group yet -- there's no real
parser behind ngspice/xschem/Qucs-S model/schematic data yet (still
inventory-only, see the Overview tab) -- adding an empty tab for a
domain nothing here actually reads yet would show fake completeness.
**Technology**/**Cells** are the pattern to repeat once one exists.

Every real file-backed tab (Layers, Magic Tech, Cells) has a
**View File** button opening the real, underlying file directly via
``file_view_dialog.view_file_dialog`` -- read-only until its own
**Edit** button is clicked, since these are real, downloaded
third-party PDK files, not this project's own code.

``ProjectState`` is the smallest possible object ``LayersView`` (copied
verbatim from OpenPDKCreator) needs -- just ``layers``/
``sorted_layers()`` -- so that tab works completely unmodified.

**Persistence** (``project_io.py``): DRC Rules/Magic Types/LEF pins/the
Settings tab's project name are edited purely in memory by default --
closing the GUI would silently lose them. A **File** menu offers
**Save Edits** (writes the current state of all four to
``saves/<pdk name>.yaml``, outside ``data/``, gitignored) and
**Reload from Real Files** (discards in-memory edits and any saved
file, re-extracting fresh from the real downloaded PDK -- for when you
want to start over). On startup, a save file for this ``pdk_root``, if
one exists, takes precedence over the real just-extracted starting
values for those domains only -- Layers/Overview/the other four Magic
Tech domains/cell-view discovery stay real-extraction-only, since
nothing here edits them yet.

**Shared LEF parsing** (``get_parsed_lef``/``lef_cache``/
``lef_pin_overrides``): both the LEF tab and the By Cell tab's Pins
pane parse and edit real ``.lef`` macros, and must see the exact same,
single in-memory object for a given real macro -- not two independent
parses silently drifting apart the moment one tab edits a pin. Owned
here, at the ``App`` level, rather than inside either tab, for exactly
that reason (``ihp/cells.py``'s own ``build_cell_index`` takes an
injectable ``get_lef`` hook so ``CellHubView`` can route through this
same cache too).
"""

from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .. import project_io
from ..ihp import drc as drc_mod
from ..ihp import inventory as inventory_mod
from ..ihp import layers as layers_mod
from ..ihp import lef as lef_mod
from ..models import DesignRule, Layer
from .cell_hub_view import CellHubView
from .file_view_dialog import view_file_dialog
from .layers_view import LayersView
from .lef_view import LefView
from .magic_tech_view import MagicTechView
from .rules_view import RulesView
from .settings_view import DEFAULT_PROJECT_NAME, SettingsView

_PROVENANCE_PATH_RE = re.compile(r"^([^:]+):\d+")


class ProjectState:
    """The subset of OpenPDKCreator's own ``Project`` that
    ``LayersView``/``RulesView`` actually touch."""

    def __init__(self, layers: list[Layer] | None = None, design_rules: list[DesignRule] | None = None):
        self.layers: list[Layer] = layers or []
        self.design_rules: list[DesignRule] = design_rules or []

    def sorted_layers(self) -> list[Layer]:
        return sorted(self.layers, key=lambda layer: layer.stack_order)


class App(ttk.Frame):
    def __init__(self, root: tk.Tk, pdk_root: Path):
        super().__init__(root)
        self.root = root
        self.pdk_root = pdk_root
        self.project = ProjectState()
        self.lyp_path: Path | None = None
        self.project_name = DEFAULT_PROJECT_NAME

        # Shared real-LEF-parse cache + saved-pin-override state, owned
        # here (not inside LefView) so the LEF tab and By Cell tab's
        # Pins pane both edit the exact same in-memory LefMacro objects
        # -- see this module's own docstring.
        self.lef_cache: dict[Path, lef_mod.LefFile] = {}
        self.lef_pin_overrides: dict[str, dict[str, list[lef_mod.LefPin]]] = {}

        self._update_title()
        root.geometry("1100x650")
        self.pack(fill="both", expand=True)

        self._build_menu()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self._build_overview_tab()
        self._build_technology_group()
        self._build_cells_group()
        self._build_settings_tab()

        self.status = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", side="bottom")

        self.load()

    def _update_title(self):
        self.root.title(f"openPDKcreator -- {self.project_name} ({self.pdk_root})")

    def set_project_name(self, name: str):
        self.project_name = name or DEFAULT_PROJECT_NAME
        self._update_title()

    # -- shared LEF parsing (LefView + CellHubView) --------------------------

    def get_parsed_lef(self, path: Path) -> lef_mod.LefFile:
        if path not in self.lef_cache:
            parsed = lef_mod.parse_lef_file(path)
            self._apply_lef_overrides(str(path.relative_to(self.pdk_root)), parsed)
            self.lef_cache[path] = parsed
        return self.lef_cache[path]

    def _apply_lef_overrides(self, relpath: str, parsed: lef_mod.LefFile):
        macro_overrides = self.lef_pin_overrides.get(relpath)
        if not macro_overrides:
            return
        macros_by_name = {macro.name: macro for macro in parsed.macros}
        for macro_name, pins in macro_overrides.items():
            macro = macros_by_name.get(macro_name)
            if macro is not None:
                macro.pins = pins

    def apply_saved_lef_pin_overrides(self, overrides: dict[str, dict[str, list[lef_mod.LefPin]]]):
        self.lef_pin_overrides = overrides
        for path, parsed in self.lef_cache.items():
            self._apply_lef_overrides(str(path.relative_to(self.pdk_root)), parsed)

    def collect_lef_pin_overrides(self) -> dict[str, dict[str, list[lef_mod.LefPin]]]:
        """Every macro's current pin list, for every real ``.lef`` file
        parsed so far this session (files never visited via either the
        LEF tab or By Cell tab are still exactly their real, on-disk
        starting state, so there's nothing to save for them)."""

        return {
            str(path.relative_to(self.pdk_root)): {macro.name: macro.pins for macro in parsed.macros}
            for path, parsed in self.lef_cache.items()
        }

    # -- menu / persistence -------------------------------------------------

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Save Edits", command=self._save_project, accelerator="Ctrl+S")
        file_menu.add_command(label="Reload from Real Files", command=self._reload_from_real_files)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)
        self.root.bind_all("<Control-s>", lambda _event: self._save_project())

    def _save_project(self):
        """Commits whatever's mid-edit in each editable tab's form,
        then writes DRC Rules/Magic Types/LEF pins/the project name out
        via ``project_io.save_state`` -- see this module's own
        docstring for why these specific domains."""

        self.rules_view.commit_pending_edits()
        self.magic_tech_view.commit_pending_edits()
        self.lef_view.commit_pending_edits()
        self.cell_hub_view.commit_pending_edits()
        path = project_io.save_state(
            self.pdk_root,
            self.project.design_rules,
            self.magic_tech_view.collect_types_by_tech(),
            self.collect_lef_pin_overrides(),
            self.project_name,
        )
        self.status.set(f"Saved edits to {path}")

    def _reload_from_real_files(self):
        """Discards in-memory edits and any saved file for this
        ``pdk_root``, then re-extracts fresh from the real, downloaded
        PDK -- the explicit "start over" action, since a saved file
        otherwise always takes precedence on the next ``load()``."""

        save_path = project_io.save_path_for(self.pdk_root)
        if save_path.is_file():
            save_path.unlink()
        self.lef_cache.clear()
        self.lef_pin_overrides = {}
        self.set_project_name(DEFAULT_PROJECT_NAME)
        self.settings_view.refresh()
        self.lef_view.load()
        self.cell_hub_view.load()
        self.magic_tech_view.load()
        self.load()

    # -- Overview tab -----------------------------------------------------

    def _build_overview_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Overview")

        columns = ("domain", "files", "size_mb", "top_extensions")
        self.inventory_tree = ttk.Treeview(frame, columns=columns, show="headings")
        widths = {"domain": 260, "files": 70, "size_mb": 90, "top_extensions": 400}
        for col in columns:
            self.inventory_tree.heading(col, text=col.replace("_", " ").title())
            self.inventory_tree.column(col, width=widths[col], anchor="w")
        self.inventory_tree.pack(fill="both", expand=True, padx=8, pady=8)

    def _refresh_inventory(self):
        for row in self.inventory_tree.get_children():
            self.inventory_tree.delete(row)
        for inv in inventory_mod.scan_all(self.pdk_root):
            size_mb = inv.total_bytes / (1024 * 1024)
            top_ext = ", ".join(f"{ext}:{count}" for ext, count in inv.extensions.most_common(4))
            self.inventory_tree.insert(
                "", "end", values=(inv.tool, inv.file_count, f"{size_mb:.1f}", top_ext)
            )

    # -- Technology group (Layers, Magic Tech, DRC Rules) --------------------

    def _build_technology_group(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Technology")

        self.technology_notebook = ttk.Notebook(frame)
        self.technology_notebook.pack(fill="both", expand=True)

        layers_frame = ttk.Frame(self.technology_notebook)
        self.technology_notebook.add(layers_frame, text="Layers")
        layers_toolbar = ttk.Frame(layers_frame)
        layers_toolbar.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Button(layers_toolbar, text="View File", command=self._view_lyp_file).pack(side="left")
        self.layers_view = LayersView(layers_frame, self)
        self.layers_view.pack(fill="both", expand=True)

        magic_tech_frame = ttk.Frame(self.technology_notebook)
        self.technology_notebook.add(magic_tech_frame, text="Magic Tech")
        self.magic_tech_view = MagicTechView(magic_tech_frame, self.pdk_root)
        self.magic_tech_view.pack(fill="both", expand=True)

        rules_frame = ttk.Frame(self.technology_notebook)
        self.technology_notebook.add(rules_frame, text="DRC Rules")
        self.rules_view = RulesView(rules_frame, self)
        self.rules_view.pack(fill="both", expand=True)

    def _view_lyp_file(self):
        if self.lyp_path is not None:
            view_file_dialog(self, self.lyp_path)

    def layer_colors(self) -> dict[str, tuple[str, str]]:
        return {layer.name: (layer.frame_color, layer.fill_color) for layer in self.project.layers}

    def _view_rule_source(self, rule: DesignRule):
        match = _PROVENANCE_PATH_RE.match(rule.source_provenance or "")
        if match is None:
            return
        path = self.pdk_root / match.group(1)
        if path.is_file():
            view_file_dialog(self, path)

    # -- Cells group (LEF, By Cell) ------------------------------------------

    def _build_cells_group(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Cells")

        self.cells_notebook = ttk.Notebook(frame)
        self.cells_notebook.pack(fill="both", expand=True)

        lef_frame = ttk.Frame(self.cells_notebook)
        self.cells_notebook.add(lef_frame, text="LEF")
        self.lef_view = LefView(lef_frame, self)
        self.lef_view.pack(fill="both", expand=True)

        cell_hub_frame = ttk.Frame(self.cells_notebook)
        self.cells_notebook.add(cell_hub_frame, text="By Cell")
        self.cell_hub_view = CellHubView(cell_hub_frame, self)
        self.cell_hub_view.pack(fill="both", expand=True)

    # -- Settings tab -----------------------------------------------------

    def _build_settings_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Settings")
        self.settings_view = SettingsView(frame, self)
        self.settings_view.pack(fill="both", expand=True)

    # -- data loading ---------------------------------------------------------

    def load(self):
        self._refresh_inventory()

        lyp_path = layers_mod.find_lyp(self.pdk_root)
        if lyp_path is None:
            self.status.set(f"No .lyp found under {self.pdk_root}/libs.tech/ -- has ihp/fetch.py been run?")
            return
        self.lyp_path = lyp_path

        group_members = layers_mod.find_group_members(lyp_path)
        parsed = layers_mod.import_layers(self.pdk_root, lyp_path)
        self.project.layers = parsed
        self.layers_view.refresh()

        drc_root = drc_mod.find_drc_root(self.pdk_root)
        rules, skipped = drc_mod.extract_design_rules(self.pdk_root, drc_root)
        self.project.design_rules = rules
        self.drc_skipped_count = len(skipped)
        self.rules_view.refresh()

        warning = f" (WARNING: {group_members} <group-members> block(s) found -- some layers may be missing)" if group_members else ""
        status = (
            f"Loaded {len(parsed)} layers from {lyp_path.name}{warning}; "
            f"extracted {len(rules)} DRC rules ({len(skipped)} construct(s) not auto-extracted, see ihp/drc.py)"
        )

        saved = project_io.load_state(self.pdk_root)
        if saved is not None:
            self.project.design_rules = saved.design_rules
            self.rules_view.refresh()
            for tech_name, types in saved.magic_types.items():
                tech = self.magic_tech_view.technologies.get(tech_name)
                if tech is not None:
                    tech.types = types
            self.magic_tech_view._refresh_all()
            self.apply_saved_lef_pin_overrides(saved.lef_pins)
            self.lef_view._refresh_all()
            self.cell_hub_view._refresh_cells()
            if saved.project_name:
                self.set_project_name(saved.project_name)
                self.settings_view.refresh()
            status += f"; restored saved edits from {project_io.save_path_for(self.pdk_root)}"

        self.status.set(status)

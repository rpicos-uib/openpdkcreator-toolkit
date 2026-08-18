"""Minimal Tk shell over a real, downloaded IHP-style PDK tree, tabs
grouped by what they actually represent rather than left flat:

- **PDK Wizard** (``gui/pdk_wizard_view.py``) -- the first tab shown,
  a guided flowchart of every real domain below, starting from the
  real layout definition (Layers) and forking into Digital vs.
  Analog/Memristor paths, written toward this project's own stated end
  goal of authoring a from-scratch memristor PDK with this same
  generic tool -- see that module's own docstring for the full design
  and its honestly-surfaced "can't create this from scratch yet" gaps.
  ``App.goto(*path)`` (below) is the shared navigation helper its
  "Go to Tab" button uses; it also drives the rest of this docstring's
  own tab structure below.
- **Overview** -- the real, per-tool file inventory, spanning every
  tool/domain (including ones with no dedicated view yet, e.g.
  libs.ref/'s cell libraries, libs.doc/).
- **Technology** -- process/technology-definition data specifically,
  one sub-tab per tool that defines it: **Layers** (KLayout's real
  ``.lyp``), **Magic Tech** (Magic's real ``.tech`` files), and
  **DRC Rules** (a real KLayout DRC deck, best-effort extracted --
  ``pdklib/drc.py``) -- reusing OpenPDKCreator's own Design Rules tab
  (``RulesView``/``rule_canvas.py``), the same "reuse the existing
  interface" pattern ``LayersView`` already established, just against
  a real, pre-extracted starting set instead of an empty one.
- **Cells** -- real cell/macro data, two sub-tabs: **LEF** (tech-layer
  routing rules plus real macro/cell footprints with editable pins) and
  **By Cell** (``CellHubView``/``pdklib/cells.py``) -- a hierarchical,
  cell-centric picture: pick one real cell, see which of its real views
  (LEF/CDL/SPICE/Verilog/Liberty/GDS) actually exist across
  ``libs.ref/<family>/*/``, jump straight to that cell's own real block
  inside each one, and edit its real LEF pins directly -- the exact
  same in-memory macro the LEF tab itself edits (see
  ``App.get_parsed_lef`` below).
- **Simulation** -- **ngspice Models** (real ``.model``/``.subckt``
  statements -- ``pdklib/spice_models.py``) and **xschem Symbols** (a
  real symbol's own device-attribute block and real pin list --
  ``pdklib/xschem.py``), both matching the **Technology**/**Cells**
  groups' own file-picker/Treeview shape; read-only, no editor exists
  for simulation model or symbol data. Qucs-S schematic data stays
  inventory-only (see the Overview tab) -- no real parser exists yet,
  so no sub-tab pretends otherwise.
- **Settings** -- project-level settings, not any one tool's PDK
  content, two sub-tabs: **General** (``gui/settings_view.py``): this
  project's own editable name and where it lives on disk, versus the
  real source PDK's own (read-only) name and location -- see that
  module's own docstring for why those two pairs are kept deliberately
  distinct; and **Tools** (``gui/tools_view.py``): real, live status of
  the FOSS EDA toolchain (``eda_tools.py``) -- found/missing, version,
  path, and a **Launch** button, a thin GUI wrapper around
  ``eda_tools.py``'s own existing check/launch logic, no new detection
  code of its own.

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
that reason (``pdklib/cells.py``'s own ``build_cell_index`` takes an
injectable ``get_lef`` hook so ``CellHubView`` can route through this
same cache too).

**Native write-back** (``export.py``, **File > Export Edited LEF
Files** / **DRC Rules** / **Magic Types** / **CDL/SPICE Ports** /
**Verilog Ports** / **Liberty Files** / **Layers**): unlike
``project_io.py``'s own program-format ``saves/``, this writes real,
valid text back into the real file formats -- ``.lef`` (pin edits,
``pdklib/lef_writer.py``), DRC Rules (a rule's ``rule_id``/``description``
patched into its real ``.drc`` script's own ``.output()`` call, its
``value`` into the one real JSON config file it actually lives in --
``pdklib/drc_writer.py``), Magic Types (a type's own real one-line entry
in its real ``.tech`` file -- ``pdklib/magic_tech_writer.py``),
CDL/SPICE/Verilog port lists (a real ``.SUBCKT``/``*.PININFO`` pair or
real ``module``/``input``/``output``/``inout`` declarations --
``pdklib/netlist_writer.py``/``pdklib/verilog_writer.py``), Liberty
pin/timing-arc data (a pin's own real ``direction``/``capacitance``/
``function`` attribute lines, a timing arc's own real
``related_pin``/``timing_type``/``timing_sense``/``when`` attribute
lines -- ``pdklib/liberty_writer.py``), and Layers (a real ``<name>``/
``<source>``/``<frame-color>``/``<fill-color>`` tag, the only four
real ``.lyp`` fields a ``Layer`` has -- ``pdklib/layers_writer.py``) --
all via surgical, position-targeted text splicing, everything else
preserved byte-for-byte, to a new ``export/`` tree mirroring each
file's own real relative path under ``pdk_root``. Never touches
``data/``. This covers every currently structured-editable domain --
see README's Future Work for what's still read-only (and so has no
write-back either).
"""

from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .. import export as export_mod
from .. import project_io
from ..pdklib import drc as drc_mod
from ..pdklib import inventory as inventory_mod
from ..pdklib import layers as layers_mod
from ..pdklib import lef as lef_mod
from ..pdklib import liberty as liberty_mod
from ..pdklib import netlist as netlist_mod
from ..pdklib import qucs_sym as qucs_sym_mod
from ..pdklib import skeleton as skeleton_mod
from ..pdklib import user_models as user_models_mod
from ..pdklib import verilog as verilog_mod
from ..pdklib import xschem as xschem_mod
from ..pdklib import xschem_sch as xschem_sch_mod
from ..models import DesignRule, Layer
from .cell_hub_view import CellHubView
from .environment_view import EnvironmentView
from .file_view_dialog import view_file_dialog
from .layers_view import LayersView
from .lef_view import LefView
from .library_manager_view import LibraryManagerView
from .magic_tech_view import MagicTechView
from .pdk_wizard_view import PdkWizardView
from .rules_view import RulesView
from .settings_view import DEFAULT_PROJECT_NAME, SettingsView
from .spice_models_view import SpiceModelsView
from .text_dialog import show_text_dialog
from .tools_view import ToolsView
from .qucs_view import QucsView
from .user_models_view import UserModelsView
from .xschem_view import XschemView

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
        self.drc_root: Path | None = None
        self.project_name = DEFAULT_PROJECT_NAME

        # Shared real-LEF-parse cache + saved-pin-override state, owned
        # here (not inside LefView) so the LEF tab and By Cell tab's
        # Pins pane both edit the exact same in-memory LefMacro objects
        # -- see this module's own docstring.
        self.lef_cache: dict[Path, lef_mod.LefFile] = {}
        self.lef_pin_overrides: dict[str, dict[str, list[lef_mod.LefPin]]] = {}
        # Same real reason, same fix, for CDL/SPICE/Verilog port edits
        # via the By Cell tab's own "Edit ... Ports" dialogs -- without
        # this, switching families and back would silently discard any
        # in-memory port edit (cells.py re-parses fresh on every call).
        self.netlist_cache: dict[Path, list[netlist_mod.NetlistCell]] = {}
        self.verilog_cache: dict[Path, list[verilog_mod.VerilogModule]] = {}
        self.liberty_cache: dict[Path, list[liberty_mod.LibertyCell]] = {}
        # Same real reason, same fix, for xschem .sym pin edits -- without
        # this, switching files and back in the Symbols sub-tab would
        # silently discard any in-memory pin edit.
        self.xschem_symbol_cache: dict[Path, xschem_mod.XschemSymbol] = {}
        self.xschem_schematic_cache: dict[Path, xschem_sch_mod.XschemSchematic] = {}
        self.qucs_symbol_cache: dict[Path, qucs_sym_mod.QucsSymbolGeometry] = {}
        self.qucs_component_cache: dict[Path, qucs_sym_mod.QucsComponent] = {}
        self.user_models: list[user_models_mod.UserModelFile] = []
        self.user_model_links: list[user_models_mod.UserModelLink] = []

        self._update_title()
        root.geometry("1100x650")
        self.pack(fill="both", expand=True)

        self._build_menu()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self._build_wizard_tab()
        self._build_pdk_tab()
        self._build_overview_tab()
        self._build_technology_group()
        self._build_cells_group()
        self._build_library_manager_tab()
        self._build_simulation_group()
        self._build_settings_tab()

        self.status = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", side="bottom")

        self.load()
        self.wizard_view.refresh()
        self.pdk_notebook.select(0)
        self.notebook.select(0)

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

    # -- shared netlist/Verilog parsing (CellHubView's own Ports dialogs) ---

    def get_parsed_netlist(self, path: Path) -> list[netlist_mod.NetlistCell]:
        if path not in self.netlist_cache:
            self.netlist_cache[path] = netlist_mod.find_cells(path)
        return self.netlist_cache[path]

    def get_parsed_verilog(self, path: Path) -> list[verilog_mod.VerilogModule]:
        if path not in self.verilog_cache:
            self.verilog_cache[path] = verilog_mod.find_modules(path)
        return self.verilog_cache[path]

    def get_parsed_liberty(self, path: Path) -> list[liberty_mod.LibertyCell]:
        if path not in self.liberty_cache:
            self.liberty_cache[path] = liberty_mod.find_cells(path)
        return self.liberty_cache[path]

    def get_parsed_xschem_symbol(self, path: Path) -> xschem_mod.XschemSymbol:
        if path not in self.xschem_symbol_cache:
            self.xschem_symbol_cache[path] = xschem_mod.parse_sym_file(path)
        return self.xschem_symbol_cache[path]

    def get_parsed_xschem_schematic(self, path: Path) -> xschem_sch_mod.XschemSchematic:
        if path not in self.xschem_schematic_cache:
            xschem_root = self.pdk_root / "libs.tech" / "xschem"
            self.xschem_schematic_cache[path] = xschem_sch_mod.parse_sch_file(path, xschem_root=xschem_root)
        return self.xschem_schematic_cache[path]

    def get_parsed_qucs_symbol(self, path: Path) -> qucs_sym_mod.QucsSymbolGeometry:
        if path not in self.qucs_symbol_cache:
            self.qucs_symbol_cache[path] = qucs_sym_mod.parse_symbol_geometry(path)
        return self.qucs_symbol_cache[path]

    def get_parsed_qucs_component(self, path: Path) -> qucs_sym_mod.QucsComponent:
        if path not in self.qucs_component_cache:
            self.qucs_component_cache[path] = qucs_sym_mod.parse_component_file(path)
        return self.qucs_component_cache[path]

    def collect_lef_pin_overrides(self) -> dict[str, dict[str, list[lef_mod.LefPin]]]:
        """Every macro's current pin list, for every real ``.lef`` file
        parsed so far this session (files never visited via either the
        LEF tab or By Cell tab are still exactly their real, on-disk
        starting state, so there's nothing to save for them)."""

        return {
            str(path.relative_to(self.pdk_root)): {macro.name: macro.pins for macro in parsed.macros}
            for path, parsed in self.lef_cache.items()
        }

    def _layers_by_lyp_path(self) -> dict[str, list[Layer]]:
        """The current layer list, keyed by the real ``.lyp`` path it
        belongs to -- only ``self.lyp_path`` (whichever one is
        actually loaded) has anything to save; empty if none is."""

        if self.lyp_path is None:
            return {}
        return {str(self.lyp_path.relative_to(self.pdk_root)): self.project.layers}

    # -- menu / persistence -------------------------------------------------

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        # File: project-level actions only -- save/reload this
        # project's own edits, plus the two real, project-wide LibMan
        # .projects import/export actions (ihp/libman_project.py) --
        # moved here from being Library-Manager-tab-only, since they
        # act across every real library at once, the same project-wide
        # scope as Save Edits/Reload. Every individual, per-domain
        # "Export Edited X (open_pdks format)" action now lives in its
        # own **Export** menu instead (see below) -- this menu used to
        # hold all of those too, which buried the two, real project-
        # level actions among ten domain-specific ones.
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Create a New PDK...", command=self._create_new_pdk)
        file_menu.add_command(label="Create a Blank PDK...", command=self._create_blank_pdk)
        file_menu.add_separator()
        file_menu.add_command(label="Save Edits", command=self._save_project, accelerator="Ctrl+S")
        file_menu.add_command(label="Reload from Real Files", command=self._reload_from_real_files)
        file_menu.add_separator()
        file_menu.add_command(label="Import from LibMan Project...", command=self._import_libman_project)
        file_menu.add_command(label="Export to LibMan Project...", command=self._export_libman_project)
        menubar.add_cascade(label="File", menu=file_menu)

        # Export: every real, individual, per-domain open_pdks-format
        # write-back action -- previously crowded into File alongside
        # genuinely project-level actions; split out into its own menu
        # now that File also carries the two LibMan project actions above.
        export_menu = tk.Menu(menubar, tearoff=False)
        export_menu.add_command(label="Export Edited LEF Files (open_pdks format)", command=self._export_lef_files)
        export_menu.add_command(label="Export Edited DRC Rules (open_pdks format)", command=self._export_drc_rules)
        export_menu.add_command(
            label="Export Edited Magic Types (open_pdks format)", command=self._export_magic_types
        )
        export_menu.add_command(
            label="Export Edited CDL/SPICE Ports (open_pdks format)", command=self._export_netlist_files
        )
        export_menu.add_command(
            label="Export Edited Verilog Ports (open_pdks format)", command=self._export_verilog_files
        )
        export_menu.add_command(
            label="Export Edited Liberty Files (open_pdks format)", command=self._export_liberty_files
        )
        export_menu.add_command(label="Export Edited Layers (open_pdks format)", command=self._export_layers)
        export_menu.add_command(
            label="Export Edited xschem Symbols (open_pdks format)", command=self._export_xschem_symbols
        )
        export_menu.add_command(
            label="Export Edited xschem Schematics (open_pdks format)", command=self._export_xschem_schematics
        )
        export_menu.add_command(
            label="Export Edited Qucs-S Symbols (open_pdks format)", command=self._export_qucs_symbols
        )
        export_menu.add_command(
            label="Export Edited Qucs-S Components (open_pdks format)", command=self._export_qucs_components
        )
        menubar.add_cascade(label="Export", menu=export_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Help", command=self._show_help)
        help_menu.add_command(label="About openPDKcreator", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)
        self.root.bind_all("<Control-s>", lambda _event: self._save_project())

    def _create_new_pdk(self):
        self._create_pdk(blank=False)

    def _create_blank_pdk(self):
        self._create_pdk(blank=True)

    def _create_pdk(self, *, blank: bool):
        """File > Create a New PDK.../Create a Blank PDK... -- points
        this whole app at a genuinely new ``pdk_root``, either bare
        (just ``libs.tech``/``libs.ref``, the same empty-project shape
        ``pdklib/skeleton.py``'s own ``build_blank_pdk`` builds) or
        seeded with one real, immediately-usable file per
        create-from-scratch domain (Layers/Magic Tech/DRC Rules/LEF,
        via that module's ``build_new_pdk_skeleton``).

        ``self.pdk_root`` is cached directly at construction time in
        nine separate view classes (unlike ``project_root``, which
        ``change_project_directory`` above reassigns live everywhere)
        -- so switching it can't reuse that live-reassignment approach;
        instead this tears down and rebuilds the whole App fresh
        against the new root, via ``_restart_with_pdk_root``."""

        new_dir_str = filedialog.askdirectory(
            title="Choose a Blank PDK Directory" if blank else "Choose a New PDK Directory", parent=self,
        )
        if not new_dir_str:
            return
        new_pdk_root = Path(new_dir_str).resolve()

        name = None
        if not blank:
            name = simpledialog.askstring(
                "Create a New PDK",
                "Technology/library name (used for the .lyp/.tech/.lef skeleton files):",
                parent=self,
            )
            if not name:
                return

        if new_pdk_root.is_dir() and any(new_pdk_root.iterdir()):
            if not messagebox.askyesno(
                "Create a PDK", f"{new_pdk_root} is not empty. Continue anyway?", parent=self,
            ):
                return

        try:
            if blank:
                skeleton_mod.build_blank_pdk(new_pdk_root)
            else:
                skeleton_mod.build_new_pdk_skeleton(new_pdk_root, name)
        except FileExistsError as exc:
            messagebox.showerror("Create a PDK", str(exc), parent=self)
            return

        self._restart_with_pdk_root(new_pdk_root)

    def _restart_with_pdk_root(self, new_pdk_root: Path):
        """Tears down this whole App and rebuilds it fresh against
        ``new_pdk_root`` -- see ``_create_pdk``'s own docstring for why
        a full rebuild, not a live reassignment, is used here."""

        root = self.root
        self.destroy()
        App(root, new_pdk_root)

    def _import_libman_project(self):
        self.goto("Library Manager")
        self.library_manager_view._import_libman_project()

    def _export_libman_project(self):
        self.goto("Library Manager")
        self.library_manager_view._export_libman_project()

    def _show_about(self):
        show_text_dialog(
            self,
            "About openPDKcreator",
            "openPDKcreator\n"
            "==============\n\n"
            "A general PDK-authoring toolkit -- create/edit real PDK content (Layers, Magic "
            "Tech, DRC Rules, LEF, GDS structural info, Liberty, CDL/SPICE, Verilog/Verilog-A, "
            "xschem and Qucs-S symbols/schematics) through one GUI.\n\n"
            "Final objective: a wizard to edit and create an open PDK, generally -- not "
            "specific to any one process. IHP's real SG13G2 PDK "
            "(github.com/IHP-GmbH/IHP-Open-PDK) is the current model this is being built and "
            "verified against, not the permanent target.\n\n"
            "Natively reads/writes IHP-GmbH's own LibMan project file format:\n"
            "  github.com/IHP-GmbH/LibMan\n\n"
            "Repository:\n"
            "  github.com/rpicos-uib/openpdkcreator-toolkit\n\n"
            "License: Apache-2.0",
        )

    def _show_help(self):
        show_text_dialog(
            self,
            "Help",
            "Getting started\n"
            "---------------\n"
            "Wizard -- a guided flowchart of every domain this tool knows how to read/edit. "
            "Click a box for details; \"Go to Tab\" jumps straight there. Start here if you're "
            "building a PDK from scratch.\n\n"
            "PDK > Overview -- a real, per-tool file inventory of whichever PDK is loaded.\n"
            "PDK > Technology -- Layers / Magic Tech / DRC Rules.\n"
            "PDK > Cells -- LEF and By Cell (one real cell's views across every domain).\n"
            "PDK > Library Manager -- a Cadence-style Libraries | Cells | Views browser "
            "spanning real and project-authored content; also where LibMan .projects "
            "import/export lives (see the File menu).\n"
            "PDK > Simulation -- ngspice Models, xschem, Qucs-S, and your own User Models "
            "(Verilog/Verilog-A).\n"
            "Settings -- project name/directory, tool install status, generated shell-env "
            "script.\n\n"
            "Menus\n"
            "-----\n"
            "File -- create a new PDK (minimal skeleton files) or a blank one (no files), "
            "save/reload your edits, import/export a LibMan .projects file.\n"
            "Export -- write real, edited content back out in open_pdks format, one command "
            "per domain.\n"
            "Help -- this dialog, and About.\n\n"
            "Command line\n"
            "------------\n"
            "python3 main.py wizard --name \"My PDK\" --pdk-root DIR -- creates a new PDK "
            "project (or --blank for no files) without opening this GUI, saves the project "
            "name, and writes a ready-to-source shell-env script (shell_env/pdk_env.sh); add "
            "--open-gui to open it here right after. Every other real, read/export command "
            "this tool has -- fetch/inventory/lef/drc/export-.../gui/... -- is listed by "
            "python3 main.py --help, and each one's own options by e.g. "
            "python3 main.py wizard --help.\n\n"
            "Full documentation lives in this project's own README.md:\n"
            "  github.com/rpicos-uib/openpdkcreator-toolkit",
        )

    def _export_lef_files(self):
        """Writes real, patched .lef text for every real file parsed
        this session (LEF tab or By Cell tab) to ``export/<pdk
        name>/...`` -- see ``export.py``'s/``pdklib/lef_writer.py``'s own
        docstrings for exactly what's patched and what's preserved
        verbatim. Never touches the real, downloaded ``data/`` copy."""

        self.lef_view.commit_pending_edits()
        self.cell_hub_view.commit_pending_edits()
        written = export_mod.export_lef_files(self.pdk_root, self.lef_cache)
        if not written:
            self.status.set("No LEF files parsed this session -- nothing to export (visit the LEF or By Cell tab first).")
            return
        self.status.set(f"Exported {len(written)} real .lef file(s) to {export_mod.EXPORT_ROOT / self.pdk_root.name}")

    def _export_drc_rules(self):
        """Writes real, patched DRC-deck text (the .drc scripts a
        rule_id/description live in, plus the one real JSON config
        file a rule's value lives in) for every rule with real,
        resolvable provenance, and real, *generated* KLayout DRC Ruby
        (``custom_rules.drc``) for every hand-authored rule (New Rule)
        whose check_type/value/layers this project knows how to
        generate -- see ``export.py``'s/``pdklib/drc_writer.py``'s own
        docstrings. A rule that still can't be written back either way
        is reported in the status line, not silently dropped."""

        self.rules_view.commit_pending_edits()
        if self.drc_root is None:
            self.status.set("No DRC deck found -- nothing to export.")
            return
        written, failures = export_mod.export_drc_rules(
            self.pdk_root, self.drc_root, self.project.design_rules, self.project.layers,
        )
        if not written:
            self.status.set("No real DRC rules to export.")
            return
        status = f"Exported {len(written)} real file(s) (DRC scripts + JSON config) to {export_mod.EXPORT_ROOT / self.pdk_root.name}"
        if failures:
            reasons = "; ".join(f"{rule_id} ({reason})" for rule_id, reason in failures)
            status += f"; {len(failures)} rule(s) not written back: {reasons}"
        self.status.set(status)

    def _new_drc_deck(self):
        """A real, minimal, valid, empty DRC deck
        (``pdklib/drc.py``'s own ``create_new_drc_deck``) -- genuinely
        usable immediately afterward: **New Rule** in the DRC Rules
        tab, and a real export, both work against it (see that
        function's own docstring)."""

        if self.drc_root is not None:
            if not messagebox.askyesno(
                "New DRC Deck",
                f"A DRC deck is already loaded ({self.drc_root}). Create a new one anyway?",
                parent=self,
            ):
                return
        try:
            new_drc_root = drc_mod.create_new_drc_deck(self.pdk_root)
        except FileExistsError as exc:
            messagebox.showerror("New DRC Deck", str(exc), parent=self)
            return
        self.load()
        # ``load()`` early-returns before reaching DRC-root discovery
        # when there's no real .lyp yet (see its own body) -- a
        # from-scratch project may well create its DRC deck before its
        # Layers, so set this directly rather than relying on load()
        # to have reached that point.
        self.drc_root = new_drc_root
        rules, _skipped = drc_mod.extract_design_rules(self.pdk_root, self.drc_root)
        self.project.design_rules = rules
        self.rules_view.refresh()
        self.status.set(
            f"Created a new, empty DRC deck at {self.drc_root.relative_to(self.pdk_root)} -- "
            "use New Rule in the DRC Rules tab to start adding rules."
        )

    def _export_magic_types(self):
        """Writes real, patched .tech text for every real technology
        currently loaded, with any in-memory Types edits patched in --
        see ``export.py``'s/``pdklib/magic_tech_writer.py``'s own
        docstrings."""

        self.magic_tech_view.commit_pending_edits()
        written = export_mod.export_magic_types(self.pdk_root, self.magic_tech_view.technologies)
        if not written:
            self.status.set("No Magic technologies loaded -- nothing to export.")
            return
        self.status.set(f"Exported {len(written)} real .tech file(s) to {export_mod.EXPORT_ROOT / self.pdk_root.name}")

    def _export_netlist_files(self):
        """Writes real, patched CDL/SPICE text for every real
        ``.cdl``/``.spice`` file parsed this session (By Cell tab's own
        Edit CDL/SPICE Ports dialogs) -- see ``export.py``'s/
        ``pdklib/netlist_writer.py``'s own docstrings."""

        written = export_mod.export_netlist_files(self.pdk_root, self.netlist_cache)
        if not written:
            self.status.set("No CDL/SPICE files parsed this session -- nothing to export (visit By Cell first).")
            return
        self.status.set(f"Exported {len(written)} real CDL/SPICE file(s) to {export_mod.EXPORT_ROOT / self.pdk_root.name}")

    def _export_verilog_files(self):
        """Writes real, patched Verilog text for every real ``.v`` file
        parsed this session (By Cell tab's own Edit Verilog Ports
        dialog) -- see ``export.py``'s/``pdklib/verilog_writer.py``'s own
        docstrings."""

        written = export_mod.export_verilog_files(self.pdk_root, self.verilog_cache)
        if not written:
            self.status.set("No Verilog files parsed this session -- nothing to export (visit By Cell first).")
            return
        self.status.set(f"Exported {len(written)} real .v file(s) to {export_mod.EXPORT_ROOT / self.pdk_root.name}")

    def _export_liberty_files(self):
        """Writes real, patched Liberty pin/timing-arc text for every
        real ``.lib`` file parsed this session (By Cell tab's own Edit
        Pins/Timing dialog) -- see ``export.py``'s/
        ``pdklib/liberty_writer.py``'s own docstrings."""

        written = export_mod.export_liberty_files(self.pdk_root, self.liberty_cache)
        if not written:
            self.status.set("No Liberty files parsed this session -- nothing to export (visit By Cell first).")
            return
        self.status.set(f"Exported {len(written)} real .lib file(s) to {export_mod.EXPORT_ROOT / self.pdk_root.name}")

    def _export_layers(self):
        """Writes real, patched ``.lyp`` text reflecting whatever's
        currently in ``self.project.layers`` -- see ``export.py``'s/
        ``pdklib/layers_writer.py``'s own docstrings. Unlike every other
        domain here, Layers has no per-file cache to check first: the
        Layers tab commits every field live (no pending-edit state),
        and there's only ever one real ``.lyp`` loaded per session."""

        if self.lyp_path is None:
            self.status.set("No .lyp file loaded -- nothing to export.")
            return
        export_path = export_mod.export_layers(self.pdk_root, self.lyp_path, self.project.layers)
        self.status.set(f"Exported {len(self.project.layers)} real layer(s) to {export_path}")

    def _export_xschem_symbols(self):
        """Writes real, patched xschem ``.sym`` text (pin name/direction
        only) for every real file parsed this session to ``export/<pdk
        name>/...`` -- see ``export.py``'s/``pdklib/xschem_writer.py``'s
        own docstrings. Never touches the real, downloaded ``data/``
        copy."""

        self.xschem_view.commit_pending_edits()
        written = export_mod.export_xschem_symbols(self.pdk_root, self.xschem_symbol_cache)
        if not written:
            self.status.set("No xschem .sym files parsed this session -- nothing to export (visit the xschem tab first).")
            return
        self.status.set(f"Exported {len(written)} real .sym file(s) to {export_mod.EXPORT_ROOT / self.pdk_root.name}")

    def _export_xschem_schematics(self):
        """Writes real, patched xschem ``.sch`` text (instance name/
        net-label, wire label, and deletion only) for every real file
        parsed this session to ``export/<pdk name>/...`` -- see
        ``export.py``'s/``pdklib/xschem_sch_writer.py``'s own docstrings,
        including the real, narrow class of entries/files that writer
        safely refuses to touch. Never touches the real, downloaded
        ``data/`` copy."""

        self.xschem_view.commit_pending_edits()
        written = export_mod.export_xschem_schematics(self.pdk_root, self.xschem_schematic_cache)
        if not written:
            self.status.set("No xschem .sch files parsed this session -- nothing to export (visit the xschem tab first).")
            return
        self.status.set(f"Exported {len(written)} real .sch file(s) to {export_mod.EXPORT_ROOT / self.pdk_root.name}")

    def _export_qucs_symbols(self):
        """Writes real, patched Qucs-S ``.sym`` text (real ``PortSym``
        x/y/type/angle/condition only) for every real file parsed this
        session to ``export/<pdk name>/...`` -- see ``export.py``'s/
        ``pdklib/qucs_sym_writer.py``'s own docstrings. Never touches the
        real, downloaded ``data/`` copy."""

        self.qucs_view.commit_pending_edits()
        written = export_mod.export_qucs_symbols(self.pdk_root, self.qucs_symbol_cache)
        if not written:
            self.status.set("No Qucs-S .sym files parsed this session -- nothing to export (visit the Qucs-S tab first).")
            return
        self.status.set(f"Exported {len(written)} real .sym file(s) to {export_mod.EXPORT_ROOT / self.pdk_root.name}")

    def _export_qucs_components(self):
        """Writes real, patched Qucs-S component ``.xml`` text (real
        Parameter default_value/equation only) for every real file
        parsed this session to ``export/<pdk name>/...`` -- see
        ``export.py``'s/``pdklib/qucs_component_writer.py``'s own
        docstrings. Never touches the real, downloaded ``data/`` copy."""

        self.qucs_view.commit_pending_edits()
        written = export_mod.export_qucs_components(self.pdk_root, self.qucs_component_cache)
        if not written:
            self.status.set("No Qucs-S .xml files parsed this session -- nothing to export (visit the Qucs-S tab first).")
            return
        self.status.set(f"Exported {len(written)} real .xml file(s) to {export_mod.EXPORT_ROOT / self.pdk_root.name}")

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
            magic_planes=self.magic_tech_view.collect_planes_by_tech(),
            magic_contacts=self.magic_tech_view.collect_contacts_by_tech(),
            magic_aliases=self.magic_tech_view.collect_aliases_by_tech(),
            magic_styles=self.magic_tech_view.collect_styles_by_tech(),
            magic_compose=self.magic_tech_view.collect_compose_by_tech(),
            magic_connect=self.magic_tech_view.collect_connect_by_tech(),
            magic_cifinput_ignored_layers=self.magic_tech_view.collect_cifinput_ignored_layers_by_tech(),
            magic_cifinput_layer_hints=self.magic_tech_view.collect_cifinput_layer_hints_by_tech(),
            layers=self._layers_by_lyp_path(),
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
        self.netlist_cache.clear()
        self.verilog_cache.clear()
        self.liberty_cache.clear()
        self.xschem_symbol_cache.clear()
        self.xschem_schematic_cache.clear()
        self.qucs_symbol_cache.clear()
        self.qucs_component_cache.clear()
        self.set_project_name(DEFAULT_PROJECT_NAME)
        self.settings_view.refresh()
        self.lef_view.load()
        self.cell_hub_view.load()
        self.magic_tech_view.load()
        self.xschem_view.load()
        self.qucs_view.load()
        self.load()

    def change_project_directory(self, new_dir: Path):
        """Switches this session's own project-level state -- not the
        real PDK data (``self.pdk_root`` is untouched) -- to a
        different real directory: ``saves/``, ``library_index.yaml``,
        ``libraries/``, ``user_models/`` all move with it.

        Real, not cosmetic: reassigns the actual, shared module-level
        constants every consumer already reads dynamically
        (``export.PROJECT_ROOT``/``EXPORT_ROOT``, ``project_io.
        SAVE_DIR``) rather than introducing a second, parallel notion of
        "current project root" -- confirmed, before writing this, that
        every real consumer accesses these as ``export_mod.PROJECT_ROOT``
        (module-qualified, re-read on every call) rather than a name
        frozen at import time, so reassigning here is enough almost
        everywhere. The one real exception:
        ``LibraryManagerView.__init__`` caches it once into
        ``self.project_root`` at construction time, so that has to be
        re-synced explicitly here too, or it would keep silently
        pointing at the old directory.

        A genuinely new, empty directory starts a fresh, empty project
        there (created if it doesn't exist yet); an existing one
        restores its own real saved state -- the same real, full
        reload sequence ``_reload_from_real_files`` already uses for
        "start over," since the new directory's own saved Magic Types/
        LEF pin overrides must apply on top of a real, freshly
        re-parsed baseline, not whatever the *previous* project's own
        edits left in memory."""

        new_dir = new_dir.resolve()
        new_dir.mkdir(parents=True, exist_ok=True)
        export_mod.PROJECT_ROOT = new_dir
        export_mod.EXPORT_ROOT = new_dir / "export"
        project_io.SAVE_DIR = new_dir / "saves"
        self.library_manager_view.project_root = export_mod.PROJECT_ROOT

        self.lef_cache.clear()
        self.lef_pin_overrides = {}
        self.netlist_cache.clear()
        self.verilog_cache.clear()
        self.liberty_cache.clear()
        self.xschem_symbol_cache.clear()
        self.xschem_schematic_cache.clear()
        self.qucs_symbol_cache.clear()
        self.qucs_component_cache.clear()
        self.set_project_name(DEFAULT_PROJECT_NAME)

        self.lef_view.load()
        self.cell_hub_view.load()
        self.magic_tech_view.load()
        self.xschem_view.load()
        self.qucs_view.load()
        self.load()
        self.library_manager_view.refresh_libraries()
        self.settings_view.refresh()
        self.status.set(f"Switched project directory to {new_dir}")

    # -- PDK tab (wraps everything actually about the PDK's own content;
    # Settings -- project naming/tool config -- stays a separate,
    # top-level tab, deliberately outside this one) --------------------

    def _build_pdk_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="PDK")
        self.pdk_notebook = ttk.Notebook(frame)
        self.pdk_notebook.pack(fill="both", expand=True)

    # -- PDK Wizard tab -----------------------------------------------------

    def _build_wizard_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Wizard")
        self.wizard_view = PdkWizardView(frame, self)
        self.wizard_view.pack(fill="both", expand=True)

    # -- Overview tab -----------------------------------------------------

    def _build_overview_tab(self):
        frame = ttk.Frame(self.pdk_notebook)
        self.pdk_notebook.add(frame, text="Overview")

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
        frame = ttk.Frame(self.pdk_notebook)
        self.pdk_notebook.add(frame, text="Technology")

        self.technology_notebook = ttk.Notebook(frame)
        self.technology_notebook.pack(fill="both", expand=True)

        layers_frame = ttk.Frame(self.technology_notebook)
        self.technology_notebook.add(layers_frame, text="Layers")
        layers_toolbar = ttk.Frame(layers_frame)
        layers_toolbar.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Button(layers_toolbar, text="View File", command=self._view_lyp_file).pack(side="left")
        ttk.Button(layers_toolbar, text="New .lyp File...", command=self._new_lyp_file).pack(side="left", padx=(6, 0))
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

    def _new_lyp_file(self):
        """A real, minimal, valid, empty KLayout ``.lyp`` skeleton
        (``pdklib/layers.py``'s own ``create_new_lyp_file``) --
        genuinely usable immediately afterward: **New Layer** in the
        Layers tab, and a real export, both work against it the same
        as against a real, downloaded file (see that function's own
        docstring). Reloads via ``self.load()`` (not just a layers-only
        re-parse) since a from-scratch project has no ``.lyp`` at all
        until now -- ``load()`` early-returns before DRC/saved-state
        restoration when ``lyp_path`` is ``None`` (see its own body)."""

        if self.lyp_path is not None:
            if not messagebox.askyesno(
                "New .lyp File",
                f"A .lyp file is already loaded ({self.lyp_path.name}). "
                "Create a different, new one and switch to it?",
                parent=self,
            ):
                return
        name = simpledialog.askstring(
            "New .lyp File", "Layer-properties file name (without .lyp):", parent=self,
        )
        if not name:
            return
        path = self.pdk_root / "libs.tech" / "klayout" / "tech" / f"{name}.lyp"
        if path.exists():
            messagebox.showerror("New .lyp File", f"{path} already exists.", parent=self)
            return
        layers_mod.create_new_lyp_file(path)
        self.load()
        self.status.set(
            f"Created a new, empty .lyp file at {path.relative_to(self.pdk_root)} -- "
            "use New Layer in the Layers tab to start adding layers."
        )

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
        frame = ttk.Frame(self.pdk_notebook)
        self.pdk_notebook.add(frame, text="Cells")

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

    # -- Library Manager tab -----------------------------------------------

    def _build_library_manager_tab(self):
        frame = ttk.Frame(self.pdk_notebook)
        self.pdk_notebook.add(frame, text="Library Manager")
        self.library_manager_view = LibraryManagerView(frame, self)
        self.library_manager_view.pack(fill="both", expand=True)

    # -- Simulation group (ngspice) -------------------------------------------

    def _build_simulation_group(self):
        frame = ttk.Frame(self.pdk_notebook)
        self.pdk_notebook.add(frame, text="Simulation")

        self.simulation_notebook = ttk.Notebook(frame)
        self.simulation_notebook.pack(fill="both", expand=True)

        ngspice_frame = ttk.Frame(self.simulation_notebook)
        self.simulation_notebook.add(ngspice_frame, text="ngspice Models")
        self.spice_models_view = SpiceModelsView(ngspice_frame, self.pdk_root)
        self.spice_models_view.pack(fill="both", expand=True)

        xschem_frame = ttk.Frame(self.simulation_notebook)
        self.simulation_notebook.add(xschem_frame, text="xschem")
        self.xschem_view = XschemView(xschem_frame, self)
        self.xschem_view.pack(fill="both", expand=True)

        qucs_frame = ttk.Frame(self.simulation_notebook)
        self.simulation_notebook.add(qucs_frame, text="Qucs-S")
        self.qucs_view = QucsView(qucs_frame, self)
        self.qucs_view.pack(fill="both", expand=True)

        user_models_frame = ttk.Frame(self.simulation_notebook)
        self.simulation_notebook.add(user_models_frame, text="User Models")
        self.user_models_view = UserModelsView(user_models_frame, self)
        self.user_models_view.pack(fill="both", expand=True)

    # -- Settings tab -----------------------------------------------------

    def _build_settings_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Settings")

        self.settings_notebook = ttk.Notebook(frame)
        self.settings_notebook.pack(fill="both", expand=True)

        general_frame = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(general_frame, text="General")
        self.settings_view = SettingsView(general_frame, self)
        self.settings_view.pack(fill="both", expand=True)

        tools_frame = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(tools_frame, text="Tools")
        self.tools_view = ToolsView(tools_frame)
        self.tools_view.pack(fill="both", expand=True)

        environment_frame = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(environment_frame, text="Environment")
        self.environment_view = EnvironmentView(environment_frame, self)
        self.environment_view.pack(fill="both", expand=True)

    # -- tab navigation (used by the PDK Wizard tab) -----------------------

    def goto(self, *path: str):
        """Selects the real notebook tab(s) named by *path*, e.g.
        ``goto("Simulation", "xschem", "Symbols")`` -- walks down as
        many nested ``ttk.Notebook`` levels as *path* has segments,
        stopping early (silently) if a segment isn't found, so a
        caller can pass a short path (just the top-level tab) too.

        Every real path except ``("Settings", ...)`` now lives one
        level deeper than *path* itself says, nested under the
        top-level "PDK" tab (``self.pdk_notebook``) -- this method
        inserts that real hop itself, so callers (the PDK Wizard's own
        stage table) never needed to change when that wrapping tab was
        added."""

        if not path:
            return
        if path[0] == "Settings":
            top_notebook = self.notebook
        else:
            self._select_tab_by_text(self.notebook, "PDK")
            top_notebook = self.pdk_notebook
        self._select_tab_by_text(top_notebook, path[0])
        notebook = self._sub_notebook_for(path[:1])
        for depth in range(1, len(path)):
            if notebook is None:
                return
            self._select_tab_by_text(notebook, path[depth])
            notebook = self._sub_notebook_for(path[: depth + 1])

    def _sub_notebook_for(self, path: tuple[str, ...]) -> ttk.Notebook | None:
        registry: dict[tuple[str, ...], ttk.Notebook] = {
            ("Technology",): self.technology_notebook,
            ("Cells",): self.cells_notebook,
            ("Simulation",): self.simulation_notebook,
            ("Settings",): self.settings_notebook,
            ("Simulation", "xschem"): self.xschem_view.outer,
            ("Simulation", "Qucs-S"): self.qucs_view.outer,
        }
        return registry.get(path)

    @staticmethod
    def _select_tab_by_text(notebook: ttk.Notebook, text: str):
        for tab_id in notebook.tabs():
            if notebook.tab(tab_id, "text") == text:
                notebook.select(tab_id)
                return

    # -- data loading ---------------------------------------------------------

    def reload_user_models(self):
        """Re-scans ``user_models/`` and reloads ``links.yaml`` --
        called at startup and after the User Models tab saves a link,
        so ``CellHubView``'s own By Cell aggregation sees the change
        without a full app relaunch."""

        self.user_models = user_models_mod.load_user_models(export_mod.PROJECT_ROOT)
        self.user_model_links = user_models_mod.load_links(export_mod.PROJECT_ROOT)

    def user_models_by_cell(self) -> dict[str, list[tuple[verilog_mod.VerilogModule, Path, str]]]:
        return user_models_mod.group_by_cell(export_mod.PROJECT_ROOT, self.user_models, self.user_model_links)

    def load(self):
        self.reload_user_models()
        self._refresh_inventory()

        lyp_path = layers_mod.find_lyp(self.pdk_root)
        if lyp_path is None:
            self.status.set(f"No .lyp found under {self.pdk_root}/libs.tech/ -- has pdklib/fetch.py been run?")
            return
        self.lyp_path = lyp_path

        group_members = layers_mod.find_group_members(lyp_path)
        parsed = layers_mod.import_layers(self.pdk_root, lyp_path)
        self.project.layers = parsed
        self.layers_view.refresh()

        self.drc_root = drc_mod.find_drc_root(self.pdk_root)
        rules, skipped = drc_mod.extract_design_rules(self.pdk_root, self.drc_root)
        self.project.design_rules = rules
        self.drc_skipped_count = len(skipped)
        self.rules_view.refresh()

        warning = f" (WARNING: {group_members} <group-members> block(s) found -- some layers may be missing)" if group_members else ""
        status = (
            f"Loaded {len(parsed)} layers from {lyp_path.name}{warning}; "
            f"extracted {len(rules)} DRC rules ({len(skipped)} construct(s) not auto-extracted, see pdklib/drc.py)"
        )

        saved = project_io.load_state(self.pdk_root)
        if saved is not None:
            saved_layers = saved.layers.get(str(lyp_path.relative_to(self.pdk_root)))
            if saved_layers is not None:
                self.project.layers = saved_layers
                self.layers_view.refresh()
            self.project.design_rules = saved.design_rules
            self.rules_view.refresh()
            for tech_name, types in saved.magic_types.items():
                tech = self.magic_tech_view.technologies.get(tech_name)
                if tech is not None:
                    tech.types = types
            for tech_name, planes in saved.magic_planes.items():
                tech = self.magic_tech_view.technologies.get(tech_name)
                if tech is not None:
                    tech.planes = planes
            for tech_name, contacts in saved.magic_contacts.items():
                tech = self.magic_tech_view.technologies.get(tech_name)
                if tech is not None:
                    tech.contacts = contacts
            for tech_name, aliases in saved.magic_aliases.items():
                tech = self.magic_tech_view.technologies.get(tech_name)
                if tech is not None:
                    tech.aliases = aliases
            for tech_name, styles in saved.magic_styles.items():
                tech = self.magic_tech_view.technologies.get(tech_name)
                if tech is not None:
                    tech.styles = styles
            for tech_name, statements in saved.magic_compose.items():
                tech = self.magic_tech_view.technologies.get(tech_name)
                if tech is not None:
                    tech.compose = statements
            for tech_name, rules in saved.magic_connect.items():
                tech = self.magic_tech_view.technologies.get(tech_name)
                if tech is not None:
                    tech.connect = rules
            for tech_name, ignored_layers in saved.magic_cifinput_ignored_layers.items():
                tech = self.magic_tech_view.technologies.get(tech_name)
                if tech is not None:
                    tech.cifinput_ignored_layers = ignored_layers
            for tech_name, hints in saved.magic_cifinput_layer_hints.items():
                tech = self.magic_tech_view.technologies.get(tech_name)
                if tech is not None:
                    tech.cifinput_layer_hints = hints
            self.magic_tech_view._refresh_all()
            self.apply_saved_lef_pin_overrides(saved.lef_pins)
            self.lef_view._refresh_all()
            self.cell_hub_view._refresh_cells()
            if saved.project_name:
                self.set_project_name(saved.project_name)
                self.settings_view.refresh()
            status += f"; restored saved edits from {project_io.save_path_for(self.pdk_root)}"

        self.status.set(status)

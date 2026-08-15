"""Cells tab: real, parsed LEF data (``openpdkcreator/ihp/lef.py``) --
tech-layer routing rules and real macro/cell footprints (class/size/
site/symmetry, pins with direction/use/port geometry, obstruction
layers). A file picker over all real, downloaded ``.lef`` files (a
tech LEF, two stdcell/io macro LEFs, 28 real SRAM hard-macro LEFs),
since -- unlike Magic's two real technologies -- there's no small,
fixed set of "the real ones" to enumerate; every real ``.lef`` under
``libs.ref/`` is shown.

Three sub-tabs per file: **LEF Layers** (tech-LEF routing/cut layers --
empty for a macro-only LEF, real and correct, not a bug), **LEF
Macros** (a macro list; selecting one shows its real pins on the
right via the shared ``pin_editor.PinEditor`` widget -- the same one
``cell_hub_view.py``'s **By Cell** tab embeds, so a pin edited from
either tab is the exact same in-memory object, visible and consistent
in both), and **Vias** (real ``VIA``/``ViaRULE`` via-stack geometry --
each real layer's own rect count for a fixed ``VIA``, or its own real
enclosure/spacing/resistance for a ``ViaRULE GENERATE`` -- read-only,
no editor exists for via geometry, matching every other real,
display-only domain here; see ``ihp/lef.py``'s own docstring for the
exact real body structure).

The file picker's own combobox is editable, not a closed real-file
list, the same **Edit File**/**Create File** toggle xschem/Qucs-S's own
file pickers already use (``gui/file_picker_utils.py``): typing a real,
existing relative path (``libs.ref/<family>/lef/<name>.lef``) reads
**Edit File** (opens ``file_view_dialog.view_file_dialog``); typing one
that doesn't exist yet reads **Create File** (writes a real, minimal,
valid empty-library ``.lef`` skeleton via ``ihp/lef.py``'s own
``create_new_lef_file``, then reloads and selects it) -- see that
function's own docstring for a real, honestly-surfaced limit: it
unblocks *loading* a brand-new family's LEF, not authoring a whole new
**MACRO** from inside this GUI (only pins within an already-existing
macro are write-back-editable; there's no **New Macro** action).

Real parsing + persistence live one level up, on ``App`` itself
(``app.get_parsed_lef``/``app.lef_cache``/``app.lef_pin_overrides``),
not here -- ``cell_hub_view.py``'s own cell aggregation
(``ihp/cells.py``) parses the very same ``.lef`` files independently,
so caching and saved-pin-override application had to move somewhere
both tabs share, rather than living inside this one tab as before (a
real bug, found and fixed here originally, would otherwise re-parse a
file fresh on every combo switch, discarding in-memory pin edits --
the shared cache is what prevents that, now for both tabs at once).
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..ihp import lef as lef_mod
from .file_picker_utils import handle_action, update_action_button
from .list_filter import build_filter_row, matches
from .pin_editor import PinEditor


def _format_via_layers(layers: list[lef_mod.LefViaLayerGeometry]) -> str:
    return " | ".join(f"{layer.layer}({len(layer.rects)} rect(s))" for layer in layers)


def _format_via_rule_layers(layers: list[lef_mod.LefViaRuleLayer]) -> str:
    parts = []
    for layer in layers:
        bits = []
        if layer.enclosure is not None:
            bits.append(f"enc {layer.enclosure[0]}x{layer.enclosure[1]}")
        if layer.rect is not None:
            bits.append("rect")
        if layer.spacing is not None:
            bits.append(f"sp {layer.spacing[0]}x{layer.spacing[1]}")
        if layer.resistance is not None:
            bits.append(f"r{layer.resistance}")
        parts.append(f"{layer.layer}({', '.join(bits)})" if bits else layer.layer)
    return " | ".join(parts)


class LefView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pdk_root = app.pdk_root
        self.lef_files: dict[str, Path] = {}
        self.current: lef_mod.LefFile | None = None
        self.current_macro: lef_mod.LefMacro | None = None
        self._macro_filter_query = ""

        self._build()
        self.load()

    # -- layout -----------------------------------------------------------

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="LEF file:").pack(side="left")
        self.file_var = tk.StringVar()
        self.file_combo = ttk.Combobox(top, textvariable=self.file_var, width=50)
        self.file_combo.pack(side="left", padx=(4, 12))
        self.file_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())
        self.file_combo.bind("<KeyRelease>", lambda _event: self._update_action_button())

        self.action_button = ttk.Button(top, text="Edit File", command=self._on_action)
        self.action_button.pack(side="left")

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True)

        hint = ttk.Frame(self)
        hint.pack(fill="x", padx=8)
        ttk.Label(
            hint, foreground="#616161",
            text="New file: type a path like libs.ref/<family>/lef/<name>.lef, then Create File.",
        ).pack(side="left")

        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.layers_tree = self._make_tree(
            sub, "LEF Layers",
            ("name", "type", "direction", "pitch", "width", "spacing", "resistance"),
            (140, 90, 90, 70, 70, 70, 140),
        )
        self._build_macros_tab(sub)
        self.vias_tree = self._make_tree(
            sub, "Vias",
            ("kind", "name", "default_generate", "resistance", "layers"),
            (80, 140, 100, 90, 420),
        )

    def _make_tree(self, notebook: ttk.Notebook, title: str, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col, width in zip(columns, widths):
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        return tree

    def _build_macros_tab(self, notebook: ttk.Notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="LEF Macros")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=2)
        frame.rowconfigure(0, weight=1)

        left = ttk.Frame(frame)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        filter_row = ttk.Frame(left)
        filter_row.grid(row=0, column=0, sticky="w", pady=(0, 4))
        build_filter_row(filter_row, self._on_macro_filter_changed, label="Filter macros:")
        macro_columns = ("name", "class", "size", "site", "pins", "obs_layers")
        self.macros_tree = ttk.Treeview(left, columns=macro_columns, show="headings")
        for col, width in zip(macro_columns, (220, 110, 100, 90, 50, 120)):
            self.macros_tree.heading(col, text=col.replace("_", " ").title())
            self.macros_tree.column(col, width=width, anchor="w")
        self.macros_tree.grid(row=1, column=0, sticky="nsew")
        self.macros_tree.bind("<<TreeviewSelect>>", self._on_macro_select)

        self.pin_editor = PinEditor(frame, on_change=self._on_pin_editor_change)
        self.pin_editor.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

    def _update_action_button(self):
        update_action_button(self.action_button, self.pdk_root, self.file_var)

    def _on_action(self):
        handle_action(
            self, self.pdk_root, self.file_var,
            create_fn=lef_mod.create_new_lef_file, on_created=self.load,
        )

    # -- persistence hooks (project_io.py) -----------------------------------

    def commit_pending_edits(self):
        """Flushes whatever's mid-edit in the pin form into its
        ``LefPin`` before the caller reads/saves state."""

        self.pin_editor.commit_pending_edits()

    # -- data ---------------------------------------------------------------

    def load(self):
        self.lef_files = {
            str(path.relative_to(self.pdk_root)): path
            for path in lef_mod.find_lef_files(self.pdk_root)
        }
        names = sorted(self.lef_files)
        self.file_combo["values"] = names
        if names and not self.file_var.get():
            self.file_var.set(names[0])
        self._refresh_all()
        self._update_action_button()

    def _refresh_all(self):
        for row in self.layers_tree.get_children():
            self.layers_tree.delete(row)
        for row in self.macros_tree.get_children():
            self.macros_tree.delete(row)
        for row in self.vias_tree.get_children():
            self.vias_tree.delete(row)

        path = self.lef_files.get(self.file_var.get())
        if path is None:
            self.summary_var.set("No LEF data loaded -- has ihp/fetch.py been run?")
            self.current = None
            self._show_macro(None)
            return

        self.current = self.app.get_parsed_lef(path)
        tech = self.current

        for layer in tech.layers:
            self.layers_tree.insert(
                "", "end",
                values=(
                    layer.name, layer.layer_type, layer.direction,
                    layer.pitch if layer.pitch is not None else "",
                    layer.width if layer.width is not None else "",
                    layer.spacing if layer.spacing is not None else "",
                    layer.resistance,
                ),
            )
        shown_macros = [m for m in tech.macros if self._macro_matches_filter(m)]
        for macro in shown_macros:
            size = f"{macro.size[0]} x {macro.size[1]}" if macro.size else ""
            self.macros_tree.insert(
                "", "end", iid=macro.name,
                values=(macro.name, macro.macro_class, size, macro.site, len(macro.pins), ", ".join(macro.obs_layers)),
            )
        for via in tech.vias:
            self.vias_tree.insert(
                "", "end",
                values=(
                    "VIA", via.name, "DEFAULT" if via.is_default else "",
                    via.resistance if via.resistance is not None else "",
                    _format_via_layers(via.layers),
                ),
            )
        for via_rule in tech.via_rules:
            self.vias_tree.insert(
                "", "end",
                values=(
                    "VIARULE", via_rule.name, "GENERATE" if via_rule.is_generate else "",
                    "", _format_via_rule_layers(via_rule.layers),
                ),
            )

        summary = (
            f"version {tech.version} | db_microns:{tech.database_microns} | "
            f"mfg_grid:{tech.manufacturing_grid} | layers:{len(tech.layers)} sites:{len(tech.sites)} "
            f"macros:{len(shown_macros)}/{len(tech.macros)} vias:{len(tech.vias)} "
            f"viarules:{len(tech.via_rules)}"
        )
        self.summary_var.set(summary)

        if shown_macros:
            self.macros_tree.selection_set(shown_macros[0].name)
            self._show_macro(shown_macros[0])
        else:
            self._show_macro(None)

    def _macro_matches_filter(self, macro: lef_mod.LefMacro) -> bool:
        return matches(self._macro_filter_query, macro.name, macro.macro_class, macro.site)

    def _on_macro_filter_changed(self, query: str):
        self._macro_filter_query = query
        self._refresh_all()

    def _on_macro_select(self, _event=None):
        if self.current is None:
            return
        selection = self.macros_tree.selection()
        if not selection:
            self._show_macro(None)
            return
        macro = next((m for m in self.current.macros if m.name == selection[0]), None)
        self._show_macro(macro)

    def _show_macro(self, macro: lef_mod.LefMacro | None):
        self.current_macro = macro
        self.pin_editor.set_macro(macro)

    def _on_pin_editor_change(self, macro: lef_mod.LefMacro | None):
        if macro is not None and self.macros_tree.exists(macro.name):
            self.macros_tree.set(macro.name, "pins", len(macro.pins))

"""Magic Tech tab: real, parsed Magic ``.tech`` data
(``openpdkcreator/ihp/magic_tech.py``), one real technology at a time
(``ihp-sg13g2`` and ``ihp-sg13g2-GDS`` for IHP -- the two genuinely
separate technologies; the fragment files ``include``d into
``ihp-sg13g2.tech`` have no own header/name and are skipped in the
picker since they were never meant to be viewed standalone).

A sub-`Notebook` per real, tabular data domain -- planes/types/
contacts/aliases/styles/CIF layers, plus **Compose**/**Connect**/
**DRC (Magic)**/**Extract** (real ``compose``/``connect``/``drc``/
``extract`` section content -- see ``ihp/magic_tech.py``'s own
docstring for exactly what's extracted from each and why). **Types**
is editable (a list + form pane, New/Delete Type, the same
commit-on-switch pattern ``LayersView``/``RulesView``/``LefView``
already use) -- every other domain stays read-only for now (each would
need its own form; Types was the one asked for). Editing is in-memory,
same as DRC Rules/LEF pins, with native write-back into the real
``.tech`` file via ``ihp/magic_tech_writer.py`` (``File > Export
Edited Magic Types``/``main.py export-magic-types``). "View File"
opens the real, underlying ``.tech`` file directly
(``file_view_dialog.view_file_dialog``), which *can* be edited, as raw
text.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..ihp import magic_tech as magic_tech_mod
from .file_view_dialog import view_file_dialog
from .list_filter import build_filter_row, matches

OBSOLETE_VALUES = ("", "yes")


class MagicTechView(ttk.Frame):
    def __init__(self, parent, pdk_root: Path):
        super().__init__(parent)
        self.pdk_root = pdk_root
        self.technologies: dict[str, magic_tech_mod.MagicTechnology] = {}
        self.current_type: magic_tech_mod.TypeEntry | None = None
        self._suspend_trace = False
        self._type_filter_query = ""

        self._build()
        self.load()

    # -- layout -----------------------------------------------------------

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="Technology:").pack(side="left")
        self.tech_var = tk.StringVar()
        self.tech_combo = ttk.Combobox(top, textvariable=self.tech_var, state="readonly", width=24)
        self.tech_combo.pack(side="left", padx=(4, 12))
        self.tech_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())

        ttk.Button(top, text="View File", command=self._view_file).pack(side="left")

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True)

        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.planes_tree = self._make_tab(sub, "Planes", ("name", "short_code"), (200, 100))
        self._build_types_tab(sub)
        self.contacts_tree = self._make_tab(sub, "Contacts", ("contact_type", "layer1", "layer2"), (140, 160, 160))
        self.aliases_tree = self._make_tab(sub, "Aliases", ("name", "members"), (200, 560))
        self.styles_tree = self._make_tab(sub, "Styles", ("type_name", "style_names"), (160, 560))
        self.cif_tree = self._make_tab(sub, "CIF Layers", ("name", "gds_pairs"), (200, 400))
        self.compose_tree = self._make_tab(sub, "Compose", ("verb", "arg1", "arg2", "arg3"), (100, 140, 140, 140))
        self.connect_tree = self._make_tab(sub, "Connect", ("types_a", "types_b"), (330, 330))
        self.drc_tree = self._make_tab(
            sub, "DRC (Magic)", ("check_type", "layers", "value_um", "rule_ids", "message"),
            (80, 220, 80, 100, 300),
        )
        self._build_extract_tab(sub)

    def _build_extract_tab(self, notebook: ttk.Notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Extract")
        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="Sheet resistance (real per-layer, milliohms/square):").grid(
            row=0, column=0, sticky="w", padx=(0, 4)
        )
        resist_columns = ("layer_spec", "milliohms_per_square")
        self.extract_resist_tree = ttk.Treeview(frame, columns=resist_columns, show="headings")
        for col, width in zip(resist_columns, (260, 180)):
            self.extract_resist_tree.heading(col, text=col.replace("_", " ").title())
            self.extract_resist_tree.column(col, width=width, anchor="w")
        self.extract_resist_tree.grid(row=1, column=0, sticky="nsew", padx=(0, 4))

        ttk.Label(frame, text="Plane order:").grid(row=0, column=1, sticky="w")
        order_columns = ("name", "order")
        self.extract_plane_order_tree = ttk.Treeview(frame, columns=order_columns, show="headings")
        for col, width in zip(order_columns, (160, 60)):
            self.extract_plane_order_tree.heading(col, text=col.title())
            self.extract_plane_order_tree.column(col, width=width, anchor="w")
        self.extract_plane_order_tree.grid(row=1, column=1, sticky="nsew")

    def _make_tab(self, notebook: ttk.Notebook, title: str, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col, width in zip(columns, widths):
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        return tree

    def _build_types_tab(self, notebook: ttk.Notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Types")
        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)

        button_row = ttk.Frame(frame)
        button_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(button_row, text="New Type", command=self._new_type).pack(side="left")
        ttk.Button(button_row, text="Delete Type", command=self._delete_type).pack(side="left", padx=(6, 0))
        self.type_filter_var = build_filter_row(button_row, self._on_type_filter_changed)

        columns = ("plane", "name", "aliases", "obsolete")
        self.types_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        for col, width in zip(columns, (120, 160, 300, 80)):
            self.types_tree.heading(col, text=col.replace("_", " ").title())
            self.types_tree.column(col, width=width, anchor="w")
        self.types_tree.grid(row=1, column=0, sticky="nsew")
        self.types_tree.bind("<<TreeviewSelect>>", self._on_type_select)

        right = ttk.Frame(frame)
        right.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(8, 0))
        right.columnconfigure(1, weight=1)

        self.type_vars: dict[str, tk.StringVar] = {}
        form_row = 0

        def add_entry(field, label):
            nonlocal form_row
            ttk.Label(right, text=label).grid(row=form_row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_type_field_changed)
            ttk.Entry(right, textvariable=var).grid(row=form_row, column=1, sticky="ew", pady=2)
            self.type_vars[field] = var
            form_row += 1

        def add_combo(field, label, values, readonly=False):
            nonlocal form_row
            ttk.Label(right, text=label).grid(row=form_row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_type_field_changed)
            combo = ttk.Combobox(
                right, textvariable=var, values=values,
                state="readonly" if readonly else "normal",
            )
            combo.grid(row=form_row, column=1, sticky="ew", pady=2)
            self.type_vars[field] = var
            form_row += 1
            return combo

        # Not readonly: a new type can reference a plane not yet
        # created elsewhere (this project has no real Planes editor
        # yet -- see README's Future Work).
        self.type_plane_combo = add_combo("plane", "Plane", ())
        add_entry("name", "Name (canonical)")
        add_entry("aliases", "Aliases (comma-separated)")
        add_combo("obsolete", "Obsolete ('-' prefix)", OBSOLETE_VALUES, readonly=True)

        ttk.Label(
            right, text="Real Magic .tech type: 'plane name,alias1,alias2' --\n"
            "a leading '-' marks it obsolete/internal.",
            foreground="#666", wraplength=260, justify="left",
        ).grid(row=form_row, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _view_file(self):
        tech = self.technologies.get(self.tech_var.get())
        if tech is not None:
            view_file_dialog(self, tech.source_path)

    # -- persistence hooks (project_io.py) -----------------------------------

    def commit_pending_edits(self):
        """Flushes whatever's mid-edit in the Types form into its
        ``TypeEntry`` before the caller reads/saves state -- otherwise
        a field typed but not yet committed (no selection change since)
        would be silently dropped from a save."""

        self._commit_form_to_type()

    def collect_types_by_tech(self) -> dict[str, list[magic_tech_mod.TypeEntry]]:
        return {name: tech.types for name, tech in self.technologies.items()}

    # -- data ---------------------------------------------------------------

    def load(self):
        self.technologies = {}
        for path in magic_tech_mod.find_tech_files(self.pdk_root):
            tech = magic_tech_mod.parse_tech_file(path)
            if tech.name:
                self.technologies[tech.name] = tech

        names = sorted(self.technologies)
        self.tech_combo["values"] = names
        if names and not self.tech_var.get():
            self.tech_var.set(names[0])
        self._refresh_all()

    def _current_tech(self) -> magic_tech_mod.MagicTechnology | None:
        return self.technologies.get(self.tech_var.get())

    def _refresh_all(self):
        self._commit_form_to_type()
        for tree in (
            self.planes_tree, self.contacts_tree,
            self.aliases_tree, self.styles_tree, self.cif_tree,
            self.compose_tree, self.connect_tree, self.drc_tree,
            self.extract_resist_tree, self.extract_plane_order_tree,
        ):
            for row in tree.get_children():
                tree.delete(row)

        tech = self._current_tech()
        if tech is None:
            self.summary_var.set("No Magic .tech data loaded -- has ihp/fetch.py been run?")
            self._refresh_types()
            return

        for plane in tech.planes:
            self.planes_tree.insert("", "end", values=(plane.name, plane.short_code))
        self.type_plane_combo["values"] = [plane.name for plane in tech.planes]
        self._refresh_types()
        for contact in tech.contacts:
            self.contacts_tree.insert("", "end", values=(contact.contact_type, contact.layer1, contact.layer2))
        for alias in tech.aliases:
            self.aliases_tree.insert("", "end", values=(alias.name, alias.members_raw))
        for style in tech.styles:
            self.styles_tree.insert("", "end", values=(style.type_name, ", ".join(style.style_names)))
        for cif_layer in tech.cif_layers:
            pairs = ", ".join(f"{layer}/{datatype}" for layer, datatype in cif_layer.gds_pairs)
            self.cif_tree.insert("", "end", values=(cif_layer.name, pairs))
        for statement in tech.compose:
            self.compose_tree.insert("", "end", values=(statement.verb, *statement.args))
        for rule in tech.connect:
            self.connect_tree.insert("", "end", values=(rule.types_a, rule.types_b))
        for check in tech.drc_checks:
            layers_text = " | ".join(",".join(group) for group in check.layer_args)
            self.drc_tree.insert(
                "", "end",
                values=(check.check_type, layers_text, f"{check.value_um:g}", check.rule_ids_raw or "", check.message),
            )
        for resist in tech.extract_resist:
            self.extract_resist_tree.insert("", "end", values=(resist.layer_spec, resist.milliohms_per_square))
        for name, order in tech.extract_plane_order:
            self.extract_plane_order_tree.insert("", "end", values=(name, order))

        summary = (
            f"format {tech.format} | v{tech.version} -- {tech.description} | "
            f"planes:{len(tech.planes)} types:{len(tech.types)} contacts:{len(tech.contacts)} "
            f"aliases:{len(tech.aliases)} styles:{len(tech.styles)} cif_layers:{len(tech.cif_layers)} "
            f"compose:{len(tech.compose)} connect:{len(tech.connect)} "
            f"drc_checks:{len(tech.drc_checks)}({len(tech.drc_skipped)} skipped) "
            f"extract_resist:{len(tech.extract_resist)}"
        )
        if tech.included_files:
            summary += f" | includes: {', '.join(tech.included_files)}"
        if tech.unparsed_sections:
            summary += f" | not parsed: {', '.join(tech.unparsed_sections)}"
        self.summary_var.set(summary)

    # -- types (editable) -----------------------------------------------------

    @staticmethod
    def _type_iid(type_entry: magic_tech_mod.TypeEntry) -> str:
        # Identity-based, not name-based: canonical_name is an editable field.
        return str(id(type_entry))

    def _type_row_values(self, type_entry: magic_tech_mod.TypeEntry) -> tuple:
        return (
            type_entry.plane, type_entry.canonical_name,
            ", ".join(type_entry.aliases), "yes" if type_entry.obsolete else "",
        )

    def _type_matches_filter(self, type_entry: magic_tech_mod.TypeEntry) -> bool:
        return matches(
            self._type_filter_query, type_entry.canonical_name, type_entry.plane, *type_entry.aliases,
        )

    def _on_type_filter_changed(self, query: str):
        self._type_filter_query = query
        self._refresh_types()

    def _refresh_types(self):
        for row in self.types_tree.get_children():
            self.types_tree.delete(row)
        self._type_by_iid = {}
        tech = self._current_tech()
        if tech is None:
            self._load_type_into_form(None)
            return
        shown = [t for t in tech.types if self._type_matches_filter(t)]
        for type_entry in shown:
            iid = self._type_iid(type_entry)
            self._type_by_iid[iid] = type_entry
            self.types_tree.insert("", "end", iid=iid, values=self._type_row_values(type_entry))
        if shown:
            self.types_tree.selection_set(self._type_iid(shown[0]))
            self._load_type_into_form(shown[0])
        else:
            self._load_type_into_form(None)

    def _on_type_select(self, _event=None):
        self._commit_form_to_type()
        selection = self.types_tree.selection()
        type_entry = self._type_by_iid.get(selection[0]) if selection else None
        self._load_type_into_form(type_entry)

    def _load_type_into_form(self, type_entry: magic_tech_mod.TypeEntry | None):
        self._suspend_trace = True
        self.current_type = type_entry
        if type_entry is None:
            for var in self.type_vars.values():
                var.set("")
        else:
            self.type_vars["plane"].set(type_entry.plane)
            self.type_vars["name"].set(type_entry.canonical_name)
            self.type_vars["aliases"].set(", ".join(type_entry.aliases))
            self.type_vars["obsolete"].set("yes" if type_entry.obsolete else "")
        self._suspend_trace = False

    def _commit_form_to_type(self):
        type_entry = self.current_type
        if type_entry is None:
            return
        type_entry.plane = self.type_vars["plane"].get().strip() or type_entry.plane
        type_entry.canonical_name = self.type_vars["name"].get().strip() or type_entry.canonical_name
        raw_aliases = self.type_vars["aliases"].get()
        type_entry.aliases = [a.strip() for a in raw_aliases.split(",") if a.strip()]
        type_entry.obsolete = self.type_vars["obsolete"].get() == "yes"

    def _on_type_field_changed(self, *_args):
        if self._suspend_trace:
            return
        self._commit_form_to_type()
        if self.current_type is not None:
            iid = self._type_iid(self.current_type)
            if self.types_tree.exists(iid):
                self.types_tree.item(iid, values=self._type_row_values(self.current_type))

    def _new_type(self):
        tech = self._current_tech()
        if tech is None:
            return
        self._commit_form_to_type()
        self.type_filter_var.set("")  # a freshly-created type must always be visible, even mid-search
        default_plane = tech.planes[0].name if tech.planes else ""
        type_entry = magic_tech_mod.TypeEntry(
            plane=default_plane, canonical_name=f"newtype{len(tech.types) + 1}",
        )
        tech.types.append(type_entry)
        iid = self._type_iid(type_entry)
        self._type_by_iid[iid] = type_entry
        self.types_tree.insert("", "end", iid=iid, values=self._type_row_values(type_entry))
        self.types_tree.selection_set(iid)
        self.types_tree.see(iid)

    def _delete_type(self):
        tech = self._current_tech()
        if tech is None:
            return
        selection = self.types_tree.selection()
        if not selection:
            return
        type_entry = self._type_by_iid.get(selection[0])
        if type_entry is None:
            return
        tech.types.remove(type_entry)
        self.current_type = None
        self.types_tree.delete(selection[0])
        del self._type_by_iid[selection[0]]
        remaining = self.types_tree.get_children()
        if remaining:
            self.types_tree.selection_set(remaining[0])
            self._load_type_into_form(self._type_by_iid[remaining[0]])
        else:
            self._load_type_into_form(None)

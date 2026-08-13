"""Magic Tech tab: real, parsed Magic ``.tech`` data
(``openpdkcreator/ihp/magic_tech.py``), one real technology at a time
(``ihp-sg13g2`` and ``ihp-sg13g2-GDS`` for IHP -- the two genuinely
separate technologies; the fragment files ``include``d into
``ihp-sg13g2.tech`` have no own header/name and are skipped in the
picker since they were never meant to be viewed standalone).

A sub-`Notebook` per real, tabular data domain (planes/types/contacts/
aliases/styles/CIF layers) -- matching the six things
``MagicTechnology`` actually parses. Read-only: unlike the Layers tab,
nothing here is meant to be hand-edited yet (see this project's own
README Future Work).
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..ihp import magic_tech as magic_tech_mod


class MagicTechView(ttk.Frame):
    def __init__(self, parent, pdk_root: Path):
        super().__init__(parent)
        self.pdk_root = pdk_root
        self.technologies: dict[str, magic_tech_mod.MagicTechnology] = {}

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

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True)

        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.planes_tree = self._make_tab(sub, "Planes", ("name", "short_code"), (200, 100))
        self.types_tree = self._make_tab(sub, "Types", ("plane", "name", "aliases", "obsolete"), (120, 160, 340, 80))
        self.contacts_tree = self._make_tab(sub, "Contacts", ("contact_type", "layer1", "layer2"), (140, 160, 160))
        self.aliases_tree = self._make_tab(sub, "Aliases", ("name", "members"), (200, 560))
        self.styles_tree = self._make_tab(sub, "Styles", ("type_name", "style_names"), (160, 560))
        self.cif_tree = self._make_tab(sub, "CIF Layers", ("name", "gds_pairs"), (200, 400))

    def _make_tab(self, notebook: ttk.Notebook, title: str, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col, width in zip(columns, widths):
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        return tree

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

    def _refresh_all(self):
        for tree in (
            self.planes_tree, self.types_tree, self.contacts_tree,
            self.aliases_tree, self.styles_tree, self.cif_tree,
        ):
            for row in tree.get_children():
                tree.delete(row)

        tech = self.technologies.get(self.tech_var.get())
        if tech is None:
            self.summary_var.set("No Magic .tech data loaded -- has ihp/fetch.py been run?")
            return

        for plane in tech.planes:
            self.planes_tree.insert("", "end", values=(plane.name, plane.short_code))
        for type_entry in tech.types:
            self.types_tree.insert(
                "", "end",
                values=(
                    type_entry.plane, type_entry.canonical_name,
                    ", ".join(type_entry.aliases), "yes" if type_entry.obsolete else "",
                ),
            )
        for contact in tech.contacts:
            self.contacts_tree.insert("", "end", values=(contact.contact_type, contact.layer1, contact.layer2))
        for alias in tech.aliases:
            self.aliases_tree.insert("", "end", values=(alias.name, alias.members_raw))
        for style in tech.styles:
            self.styles_tree.insert("", "end", values=(style.type_name, ", ".join(style.style_names)))
        for cif_layer in tech.cif_layers:
            pairs = ", ".join(f"{layer}/{datatype}" for layer, datatype in cif_layer.gds_pairs)
            self.cif_tree.insert("", "end", values=(cif_layer.name, pairs))

        summary = (
            f"format {tech.format} | v{tech.version} -- {tech.description} | "
            f"planes:{len(tech.planes)} types:{len(tech.types)} contacts:{len(tech.contacts)} "
            f"aliases:{len(tech.aliases)} styles:{len(tech.styles)} cif_layers:{len(tech.cif_layers)}"
        )
        if tech.included_files:
            summary += f" | includes: {', '.join(tech.included_files)}"
        if tech.unparsed_sections:
            summary += f" | not parsed: {', '.join(tech.unparsed_sections)}"
        self.summary_var.set(summary)

"""Minimal Tk shell: a two-tab window (Inventory, Layers) over a real,
downloaded IHP-style PDK tree.

``ProjectState`` is the smallest possible object ``LayersView`` (copied
verbatim from OpenPDKCreator) needs -- just ``layers``/
``sorted_layers()`` -- so that tab works completely unmodified.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..ihp import inventory as inventory_mod
from ..ihp import layers as layers_mod
from ..models import Layer
from .layers_view import LayersView


class ProjectState:
    """The subset of OpenPDKCreator's own ``Project`` that
    ``LayersView`` actually touches."""

    def __init__(self, layers: list[Layer] | None = None):
        self.layers: list[Layer] = layers or []

    def sorted_layers(self) -> list[Layer]:
        return sorted(self.layers, key=lambda layer: layer.stack_order)


class App(ttk.Frame):
    def __init__(self, root: tk.Tk, pdk_root: Path):
        super().__init__(root)
        self.root = root
        self.pdk_root = pdk_root
        self.project = ProjectState()

        root.title(f"openPDKcreator -- {pdk_root}")
        root.geometry("1100x650")
        self.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self._build_inventory_tab()
        self._build_layers_tab()

        self.status = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", side="bottom")

        self.load()

    # -- Inventory tab ----------------------------------------------------

    def _build_inventory_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Inventory")

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

    # -- Layers tab ---------------------------------------------------------

    def _build_layers_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Layers")
        self.layers_view = LayersView(frame, self)
        self.layers_view.pack(fill="both", expand=True)

    # -- data loading ---------------------------------------------------------

    def load(self):
        self._refresh_inventory()

        lyp_path = layers_mod.find_lyp(self.pdk_root)
        if lyp_path is None:
            self.status.set(f"No .lyp found under {self.pdk_root}/libs.tech/ -- has ihp/fetch.py been run?")
            return

        group_members = layers_mod.find_group_members(lyp_path)
        parsed = layers_mod.import_layers(self.pdk_root, lyp_path)
        self.project.layers = parsed
        self.layers_view.refresh()

        warning = f" (WARNING: {group_members} <group-members> block(s) found -- some layers may be missing)" if group_members else ""
        self.status.set(f"Loaded {len(parsed)} layers from {lyp_path.name}{warning}")

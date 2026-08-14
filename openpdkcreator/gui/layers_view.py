"""Layers tab: layer list with a reposition helper, a form, and a live
cross-section preview.

Copied verbatim from OpenPDKCreator's own
``scripts/pdk_wizard/gui/layers_view.py`` -- it only ever touches
``app.project.layers``/``app.project.sorted_layers()`` and
``..models.Layer``, so it works unmodified against this project's own
minimal ``ProjectState`` (``openpdkcreator/gui/app.py``).

The reposition helper (Move Up / Move Down) is what lets a contributor
fix stack ordering without hand-editing ``stack_order`` integers in YAML;
it swaps the selected layer's ``stack_order`` with its neighbor's and
redraws both the list and the cross-section canvas immediately.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, ttk

from ..models import Layer
from .list_filter import build_filter_row, matches

PURPOSES = ("drawing", "pin", "label", "marker", "fill", "exclude")
PLANES = ("routing", "annotation")
STATUSES = ("placeholder", "confirmed")
TRISTATE = ("", "yes", "no")

STACK_CANVAS_W = 260
STACK_CANVAS_H = 260
BAND_MARGIN = 20


class LayersView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_layer: Layer | None = None
        self._suspend_trace = False
        self._filter_query = ""

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)

        self._build_list_pane()
        self._build_stack_pane()
        self._build_form_pane()
        self.refresh()

    # -- list + reposition helper ---------------------------------------

    def _build_list_pane(self):
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        button_row = ttk.Frame(left)
        button_row.grid(row=0, column=0, sticky="ew")
        ttk.Button(button_row, text="New Layer", command=self._new_layer).pack(side="left")
        ttk.Button(button_row, text="Delete", command=self._delete_layer).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(button_row, text="▲ Move Up", command=lambda: self._move(-1)).pack(
            side="left", padx=(12, 0)
        )
        ttk.Button(button_row, text="▼ Move Down", command=lambda: self._move(1)).pack(
            side="left", padx=(6, 0)
        )
        self.filter_var = build_filter_row(button_row, self._on_filter_changed)

        columns = ("stack_order", "name", "gds", "purpose", "status")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        for col, width in zip(columns, (60, 90, 80, 90, 90)):
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=width, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    # -- stack cross-section preview -------------------------------------

    def _build_stack_pane(self):
        mid = ttk.Frame(self)
        mid.grid(row=0, column=1, sticky="n", padx=4, pady=8)
        ttk.Label(mid, text="Stack cross-section (bottom → top)").pack()
        self.stack_canvas = tk.Canvas(
            mid, width=STACK_CANVAS_W, height=STACK_CANVAS_H,
            background="white", highlightthickness=1, highlightbackground="#c0c0c0",
        )
        self.stack_canvas.pack(pady=(4, 0))

    def _redraw_stack(self):
        self.stack_canvas.delete("all")
        layers = self.app.project.sorted_layers()
        if not layers:
            return
        band_h = (STACK_CANVAS_H - 2 * BAND_MARGIN) / max(len(layers), 1)
        for i, layer in enumerate(layers):
            y1 = STACK_CANVAS_H - BAND_MARGIN - i * band_h
            y0 = y1 - band_h + 2
            is_selected = layer is self.current_layer
            outline = "#000000" if is_selected else layer.frame_color
            width = 3 if is_selected else 1
            self.stack_canvas.create_rectangle(
                40, y0, STACK_CANVAS_W - 20, y1, outline=outline, fill=layer.fill_color, width=width
            )
            self.stack_canvas.create_text(
                (40 + STACK_CANVAS_W - 20) / 2, (y0 + y1) / 2, text=layer.name,
                font=("TkDefaultFont", 9, "bold"),
            )

    # -- form pane -----------------------------------------------------

    def _build_form_pane(self):
        right = ttk.Frame(self)
        right.grid(row=0, column=2, sticky="nsew", padx=(4, 8), pady=8)
        right.columnconfigure(1, weight=1)

        self.vars: dict[str, tk.StringVar] = {}
        row = 0

        def add_entry(field, label):
            nonlocal row
            ttk.Label(right, text=label).grid(row=row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_field_changed)
            ttk.Entry(right, textvariable=var).grid(row=row, column=1, sticky="ew", pady=2)
            self.vars[field] = var
            row += 1

        def add_combo(field, label, values):
            nonlocal row
            ttk.Label(right, text=label).grid(row=row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            combo = ttk.Combobox(right, textvariable=var, values=values, state="readonly")
            combo.grid(row=row, column=1, sticky="ew", pady=2)
            combo.bind("<<ComboboxSelected>>", self._on_field_changed)
            self.vars[field] = var
            row += 1

        add_entry("name", "Name")
        add_entry("gds_layer", "GDS layer #")
        add_entry("gds_datatype", "GDS datatype #")
        add_combo("purpose", "Purpose", PURPOSES)
        add_combo("plane", "Plane (Magic)", PLANES)
        add_combo("streamout_allowed", "Streamout allowed", TRISTATE)

        for field, label in (("frame_color", "Frame color"), ("fill_color", "Fill color")):
            ttk.Label(right, text=label).grid(row=row, column=0, sticky="w", pady=2)
            swatch_row = ttk.Frame(right)
            swatch_row.grid(row=row, column=1, sticky="ew", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_field_changed)
            self.vars[field] = var
            entry = ttk.Entry(swatch_row, textvariable=var, width=10)
            entry.pack(side="left")
            swatch = tk.Label(swatch_row, width=3, relief="solid", borderwidth=1)
            swatch.pack(side="left", padx=(6, 0))
            self._bind_swatch(field, var, swatch)
            ttk.Button(
                swatch_row, text="Pick…", command=lambda f=field: self._pick_color(f)
            ).pack(side="left", padx=(6, 0))
            row += 1

        add_entry("notes", "Notes")
        add_combo("status", "Status", STATUSES)

    def _bind_swatch(self, field, var, swatch_widget):
        def update(*_args):
            color = var.get() or "#ffffff"
            try:
                swatch_widget.configure(background=color)
            except tk.TclError:
                pass

        var.trace_add("write", update)
        self._swatches = getattr(self, "_swatches", {})
        self._swatches[field] = swatch_widget

    def _pick_color(self, field):
        _, hex_color = colorchooser.askcolor(color=self.vars[field].get() or "#ffffff")
        if hex_color:
            self.vars[field].set(hex_color)

    # -- data plumbing ---------------------------------------------------

    @staticmethod
    def _iid(layer: Layer) -> str:
        # Identity-based, not name-based: the Name field is editable, and a
        # mutable field must never double as a Treeview row identifier or
        # renaming a layer would knock the selection loose mid-edit.
        return str(id(layer))

    def refresh(self):
        selected = self.tree.selection()
        selected_iid = selected[0] if selected else None
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._layer_by_iid = {}
        for layer in self.app.project.sorted_layers():
            if not matches(self._filter_query, layer.name, layer.purpose, layer.status):
                continue
            gds = "" if layer.gds_layer is None else f"{layer.gds_layer}/{layer.gds_datatype}"
            iid = self._iid(layer)
            self._layer_by_iid[iid] = layer
            self.tree.insert(
                "", "end", iid=iid,
                values=(layer.stack_order, layer.name, gds, layer.purpose, layer.status),
            )
        if selected_iid and self.tree.exists(selected_iid):
            self.tree.selection_set(selected_iid)
        elif self._layer_by_iid:
            self.tree.selection_set(next(iter(self._layer_by_iid)))
        else:
            self._load_layer_into_form(None)
        # The stack cross-section always shows the real, complete
        # physical stack -- filtering the list is for finding a layer,
        # not for hiding the rest of the real stack from the diagram.
        self._redraw_stack()

    def _on_filter_changed(self, query: str):
        self._filter_query = query
        self.refresh()

    def _on_select(self, _event=None):
        self._commit_form_to_layer()
        selection = self.tree.selection()
        layer = self._layer_by_iid.get(selection[0]) if selection else None
        self._load_layer_into_form(layer)

    def _load_layer_into_form(self, layer: Layer | None):
        self._suspend_trace = True
        self.current_layer = layer
        if layer is None:
            for var in self.vars.values():
                var.set("")
        else:
            self.vars["name"].set(layer.name)
            self.vars["gds_layer"].set("" if layer.gds_layer is None else str(layer.gds_layer))
            self.vars["gds_datatype"].set(
                "" if layer.gds_datatype is None else str(layer.gds_datatype)
            )
            self.vars["purpose"].set(layer.purpose)
            self.vars["plane"].set(layer.plane)
            self.vars["streamout_allowed"].set(
                {True: "yes", False: "no", None: ""}[layer.streamout_allowed]
            )
            self.vars["frame_color"].set(layer.frame_color)
            self.vars["fill_color"].set(layer.fill_color)
            self.vars["notes"].set(layer.notes)
            self.vars["status"].set(layer.status)
        self._suspend_trace = False
        self._redraw_stack()

    def _commit_form_to_layer(self):
        layer = self.current_layer
        if layer is None:
            return
        layer.name = self.vars["name"].get().strip() or layer.name
        for field in ("gds_layer", "gds_datatype"):
            raw = self.vars[field].get().strip()
            try:
                setattr(layer, field, int(raw) if raw else None)
            except ValueError:
                pass
        layer.purpose = self.vars["purpose"].get() or layer.purpose
        layer.plane = self.vars["plane"].get() or layer.plane
        layer.streamout_allowed = {"yes": True, "no": False, "": None}[
            self.vars["streamout_allowed"].get()
        ]
        layer.frame_color = self.vars["frame_color"].get() or layer.frame_color
        layer.fill_color = self.vars["fill_color"].get() or layer.fill_color
        layer.notes = self.vars["notes"].get()
        layer.status = self.vars["status"].get() or layer.status

    def _on_field_changed(self, *_args):
        if self._suspend_trace:
            return
        if self.current_layer is not None:
            self._commit_form_to_layer()
            self.refresh()

    # -- add/remove/reorder ------------------------------------------

    def _new_layer(self):
        self._commit_form_to_layer()
        self.filter_var.set("")  # a freshly-created layer must always be visible, even mid-search
        next_order = max((l.stack_order for l in self.app.project.layers), default=-1) + 1
        layer = Layer(name=f"NEWLAYER{next_order}", stack_order=next_order)
        self.app.project.layers.append(layer)
        self.refresh()
        self.tree.selection_set(self._iid(layer))

    def _delete_layer(self):
        selection = self.tree.selection()
        layer = self._layer_by_iid.get(selection[0]) if selection else None
        if layer is None:
            return
        self.app.project.layers.remove(layer)
        self.current_layer = None
        self.refresh()

    def _move(self, direction: int):
        selection = self.tree.selection()
        layer = self._layer_by_iid.get(selection[0]) if selection else None
        if layer is None:
            return
        ordered = self.app.project.sorted_layers()
        index = ordered.index(layer)
        target = index + direction
        if target < 0 or target >= len(ordered):
            return
        ordered[index].stack_order, ordered[target].stack_order = (
            ordered[target].stack_order,
            ordered[index].stack_order,
        )
        self.refresh()
        self.tree.selection_set(self._iid(layer))

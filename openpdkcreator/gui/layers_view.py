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

The layer list is filtered by two, independent, combined criteria: a
**Name** search box (plain substring, case-insensitive) and a **Type**
multi-select listbox -- real layer-name "types" (the segment after a
real layer's last ``.``, e.g. ``"pin"`` for ``"Activ.pin"``; see
``_layer_type``), generated fresh from whatever the currently loaded
project's own layers actually contain, never a static list (the real
IHP deck alone has 51 distinct real types). Deliberately *not* the
project's own ``purpose`` field, which every real, imported layer gets
set to a fixed ``"drawing"`` regardless of its real name -- filtering
on that would be close to a no-op.

The cross-section canvas's own real, laid-out *viewport* genuinely
grows with the window (gridded ``sticky="nsew"`` with real weight, band
width redrawn on every real ``<Configure>`` event from the canvas's own
current, real ``winfo_width()``, never a fixed constant), but each real
layer's band is always drawn at one fixed, always-readable pixel height
(``FIXED_BAND_H``) -- a real vertical ``ttk.Scrollbar`` (also mouse-wheel
bound) scrolls through whatever doesn't fit, exactly like the layer
list beside it, rather than squeezing every band to fit the viewport (a
real PDK's full stack -- 377 real layers for IHP -- would otherwise
still need each band under a pixel tall to avoid scrolling at all). A
"Zoom" control beside the drawing -- two editable Min/Max ``stack_order``
bounds (blank means "no bound") -- filters which real layers are drawn
in the first place, independent of the scrollbar.
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

_NO_TYPE_LABEL = "(no dot)"
"""Real IHP layer names are always ``<layer>.<type>`` (e.g.
``Activ.pin``) -- but a brand-new layer added via **New Layer** starts
as a plain ``NEWLAYERn`` with no dot at all until renamed. Grouped
under this one, honest pseudo-type in the Type selector rather than
silently dropped or crashing ``_layer_type``."""


def _layer_type(name: str) -> str:
    """The real "type" component of a real layer name -- the segment
    after its last real ``.``, e.g. ``"pin"`` for ``"Activ.pin"``. This
    is deliberately *not* the project's own ``purpose`` field (which
    ``ihp/layers.py``'s own ``import_layers`` sets to a fixed
    ``"drawing"`` for every real, imported layer regardless of its
    real name -- not a real, per-layer classification at all) -- this
    reads the real name itself, so it's genuinely per-project and
    reflects whatever real types actually appear in the loaded file."""

    if "." not in name:
        return _NO_TYPE_LABEL
    return name.rsplit(".", 1)[1]

STACK_CANVAS_W = 260
"""Initial size hint for the canvas widget, and the minimum fallback
used before its first real ``<Configure>`` event has fired -- every
actual redraw uses the canvas's own live ``winfo_width()`` instead, so
band width genuinely tracks the real window size, not this constant."""
STACK_CANVAS_H = 260
BAND_MARGIN = 20
FIXED_BAND_H = 26
"""Every real layer's band is always drawn at exactly this pixel
height, regardless of viewport size or how many real layers are in the
current zoomed range -- real content taller than the real viewport
scrolls (see the vertical ``ttk.Scrollbar`` in ``_build_stack_pane``)
rather than shrinking bands until a real layer name no longer fits."""
_SPIN_BOUND = 1_000_000
"""A wide, static Zoom Spinbox range -- real clamping to the current
stack's own real min/max happens in Python (``_current_zoom_bounds``),
never via these widgets' own ``from_``/``to`` (see ``_build_stack_pane``'s
own comment for why reconfiguring those is actively unsafe)."""


class LayersView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_layer: Layer | None = None
        self._suspend_trace = False
        self._filter_query = ""
        self._known_types: list[str] = []
        """The real, distinct layer-name types (see ``_layer_type``)
        the Type selector was last populated with -- rebuilt only when
        this actually changes (a real layer added/deleted/renamed),
        not on every ``refresh()``, so an in-progress selection/scroll
        in that listbox survives an unrelated edit elsewhere."""

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
        button_row.grid(row=0, column=0, columnspan=3, sticky="ew")
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
        self.filter_var = build_filter_row(button_row, self._on_filter_changed, label="Name:")

        columns = ("stack_order", "name", "gds", "purpose", "status")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        for col, width in zip(columns, (60, 90, 80, 90, 90)):
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=width, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree_scrollbar = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree_scrollbar.grid(row=1, column=1, sticky="ns", pady=(6, 0))
        self.tree.configure(yscrollcommand=self.tree_scrollbar.set)

        # Type selector: a real, multi-select "selection box" listing
        # whatever real layer-name types (see _layer_type) are actually
        # present in the currently loaded project -- generated fresh
        # from the real data every time it changes, never a static,
        # hardcoded list (the real IHP deck alone has 51 distinct real
        # types: drawing/pin/label/net/boundary/text/... down to
        # one-off via names like "m2tm1"). Everything selected by
        # default, so an untouched filter never hides real data.
        type_frame = ttk.Frame(left)
        type_frame.grid(row=1, column=2, sticky="ns", padx=(6, 0), pady=(6, 0))
        type_frame.rowconfigure(1, weight=1)
        ttk.Label(type_frame, text="Type").grid(row=0, column=0, columnspan=2, sticky="w")
        self.type_listbox = tk.Listbox(
            type_frame, selectmode="extended", exportselection=False, width=12, activestyle="none",
        )
        self.type_listbox.grid(row=1, column=0, sticky="ns")
        type_scrollbar = ttk.Scrollbar(type_frame, orient="vertical", command=self.type_listbox.yview)
        type_scrollbar.grid(row=1, column=1, sticky="ns")
        self.type_listbox.configure(yscrollcommand=type_scrollbar.set)
        self.type_listbox.bind("<<ListboxSelect>>", lambda _e: self.refresh())

    # -- stack cross-section preview -------------------------------------

    def _build_stack_pane(self):
        mid = ttk.Frame(self)
        mid.grid(row=0, column=1, sticky="nsew", padx=4, pady=8)
        mid.rowconfigure(1, weight=1)
        mid.columnconfigure(1, weight=1)

        ttk.Label(mid, text="Stack cross-section (bottom → top)").grid(
            row=0, column=0, columnspan=2, pady=(0, 4)
        )

        # A "lateral scale": two editable stack_order bounds, positioned
        # beside the drawing rather than a real draggable-handle range
        # slider -- with 377 real layers on one screen, each band is
        # under a pixel tall and unreadable; typing a real Min/Max here
        # zooms the drawing to just that sub-range instead.
        zoom_frame = ttk.Frame(mid)
        zoom_frame.grid(row=1, column=0, sticky="ns", padx=(0, 6))
        ttk.Label(zoom_frame, text="Zoom", font=("TkDefaultFont", 8, "bold")).pack(pady=(0, 4))
        ttk.Label(zoom_frame, text="Max").pack()
        self.zoom_max_var = tk.StringVar()
        self.zoom_max_spin = tk.Spinbox(
            zoom_frame, from_=_SPIN_BOUND, to=_SPIN_BOUND, textvariable=self.zoom_max_var,
            width=6, justify="center",
        )
        self.zoom_max_spin.pack(pady=(0, 10))
        ttk.Label(zoom_frame, text="Min").pack()
        self.zoom_min_var = tk.StringVar()
        self.zoom_min_spin = tk.Spinbox(
            zoom_frame, from_=-_SPIN_BOUND, to=_SPIN_BOUND, textvariable=self.zoom_min_var,
            width=6, justify="center",
        )
        self.zoom_min_spin.pack()
        # Real Min/Max clamping to the current, real stack_order range
        # happens in Python (_current_zoom_bounds) on every redraw, not
        # via these widgets' own from_/to -- Tk's own Spinbox silently
        # overwrites its bound textvariable to the new "from_" value
        # every time .configure(from_=..., to=...) is called (confirmed
        # empirically), which would otherwise stomp a real, just-typed
        # Min/Max on the very next redraw. So from_/to are set once,
        # here, to a wide static range, and never reconfigured again.
        self.zoom_min_var.set("")
        self.zoom_max_var.set("")
        ttk.Button(zoom_frame, text="Reset", command=self._reset_zoom).pack(pady=(10, 0))
        # A blank Min/Max means "no bound" -- covers direct typing, the
        # spinbox arrows, and Reset, all through the one code path.
        self.zoom_min_var.trace_add("write", self._on_zoom_changed)
        self.zoom_max_var.trace_add("write", self._on_zoom_changed)

        self.stack_canvas = tk.Canvas(
            mid, width=STACK_CANVAS_W, height=STACK_CANVAS_H,
            background="white", highlightthickness=1, highlightbackground="#c0c0c0",
        )
        self.stack_canvas.grid(row=1, column=1, sticky="nsew", pady=(4, 0))
        self.stack_scrollbar = ttk.Scrollbar(mid, orient="vertical", command=self.stack_canvas.yview)
        self.stack_scrollbar.grid(row=1, column=2, sticky="ns", pady=(4, 0))
        self.stack_canvas.configure(yscrollcommand=self.stack_scrollbar.set)
        # The canvas's own real, laid-out width (not a fixed constant)
        # drives every redraw's band width, so it genuinely tracks the
        # window -- height, though, is a real, fixed-per-band, scrollable
        # region now (see FIXED_BAND_H), not stretched to fit the
        # viewport, so a real layer name is always readable regardless
        # of how many real layers are in the current zoomed range.
        self.stack_canvas.bind("<Configure>", lambda _e: self._redraw_stack())
        self.stack_canvas.bind("<Button-4>", lambda _e: self.stack_canvas.yview_scroll(-3, "units"))
        self.stack_canvas.bind("<Button-5>", lambda _e: self.stack_canvas.yview_scroll(3, "units"))
        self.stack_canvas.bind(
            "<MouseWheel>", lambda e: self.stack_canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")
        )
        # The very first draw (and every real Zoom-bound change) starts
        # scrolled to the *bottom* of the scrollable content -- the
        # real, physical bottom of the stack (e.g. Substrate), matching
        # this pane's own "(bottom -> top)" label -- rather than
        # wherever Tk's own default top-of-scrollregion happens to be.
        # An ordinary redraw (a form-field edit, a window resize)
        # leaves the user's own current scroll position alone.
        self._pending_scroll_reset = True

    def _reset_zoom(self):
        self.zoom_min_var.set("")
        self.zoom_max_var.set("")

    def _on_zoom_changed(self, *_args):
        self._pending_scroll_reset = True
        self._redraw_stack()

    @staticmethod
    def _parse_zoom_bound(raw: str, default: int) -> int:
        raw = raw.strip()
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    def _current_zoom_bounds(self, full_min: int, full_max: int) -> tuple[int, int]:
        zmin = self._parse_zoom_bound(self.zoom_min_var.get(), full_min)
        zmax = self._parse_zoom_bound(self.zoom_max_var.get(), full_max)
        zmin = max(full_min, min(zmin, full_max))
        zmax = max(full_min, min(zmax, full_max))
        if zmin > zmax:
            zmin, zmax = zmax, zmin
        return zmin, zmax

    def _redraw_stack(self):
        self.stack_canvas.delete("all")
        layers_all = self.app.project.sorted_layers()
        if not layers_all:
            self.stack_canvas.configure(scrollregion=(0, 0, 0, 0))
            return

        full_min = layers_all[0].stack_order
        full_max = layers_all[-1].stack_order
        zmin, zmax = self._current_zoom_bounds(full_min, full_max)
        layers = [l for l in layers_all if zmin <= l.stack_order <= zmax]
        if not layers:
            self.stack_canvas.configure(scrollregion=(0, 0, 0, 0))
            return

        canvas_w = max(self.stack_canvas.winfo_width(), STACK_CANVAS_W)
        content_h = 2 * BAND_MARGIN + len(layers) * FIXED_BAND_H
        left, right = 40, canvas_w - 20
        for i, layer in enumerate(layers):
            # Real layer 0 (the lowest real stack_order) sits at the
            # *bottom* of the real, scrollable content -- "Stack
            # cross-section (bottom -> top)" -- so higher real index
            # means smaller y, same as before, just against the real
            # scrollable content height rather than the viewport's own.
            y1 = content_h - BAND_MARGIN - i * FIXED_BAND_H
            y0 = y1 - FIXED_BAND_H + 2
            is_selected = layer is self.current_layer
            outline = "#000000" if is_selected else layer.frame_color
            width = 3 if is_selected else 1
            self.stack_canvas.create_rectangle(
                left, y0, right, y1, outline=outline, fill=layer.fill_color, width=width
            )
            self.stack_canvas.create_text(
                (left + right) / 2, (y0 + y1) / 2, text=layer.name,
                font=("TkDefaultFont", 9, "bold"),
            )

        self.stack_canvas.configure(scrollregion=(0, 0, canvas_w, content_h))
        if self._pending_scroll_reset:
            self.stack_canvas.yview_moveto(1.0)
            self._pending_scroll_reset = False

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

    def _selected_types(self) -> set[str]:
        return {self.type_listbox.get(i) for i in self.type_listbox.curselection()}

    def _refresh_type_listbox(self, types_present: list[str]):
        if types_present == self._known_types:
            return
        old_types = set(self._known_types)
        previously_selected = self._selected_types()
        self._known_types = types_present
        self.type_listbox.delete(0, tk.END)
        for t in types_present:
            self.type_listbox.insert(tk.END, t)
        for i, t in enumerate(types_present):
            # A real type carries over its own previous checked state;
            # a brand-new one (never seen before -- e.g. a layer just
            # got renamed to a new real suffix) starts selected, so an
            # untouched Type selector never hides real, new data.
            if t not in old_types or t in previously_selected:
                self.type_listbox.select_set(i)

    def refresh(self):
        selected = self.tree.selection()
        selected_iid = selected[0] if selected else None

        # The Type selector is generated from *every* real, current
        # layer -- not just the ones the Name filter currently shows --
        # so a type stays selectable/visible even while it's the only
        # thing being searched for.
        types_present = sorted({_layer_type(l.name) for l in self.app.project.layers})
        self._refresh_type_listbox(types_present)
        selected_types = self._selected_types()

        for row in self.tree.get_children():
            self.tree.delete(row)
        self._layer_by_iid = {}
        for layer in self.app.project.sorted_layers():
            if not matches(self._filter_query, layer.name):
                continue
            if _layer_type(layer.name) not in selected_types:
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

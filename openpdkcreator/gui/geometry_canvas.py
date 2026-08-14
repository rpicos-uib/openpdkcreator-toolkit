"""A real, shared, interactive Tkinter ``Canvas`` widget for editing
real drawn geometry -- reused across xschem Symbols, xschem
Schematics, and Qucs-S Symbols (the three real domains with actual
drawn geometry; Qucs-S Components has none of its own, see
``gui/qucs_view.py``'s own docstring), rather than three separate
canvas implementations.

**One shared shape model, ``GeometryItem``**, decoupled from any one
real file format: each domain's own real objects (``ihp/xschem.py``'s
``XschemLine``/``XschemArc``/``XschemText``/``XschemBox``/
``XschemPin``, ``ihp/xschem_sch.py``'s additional
``XschemInstance``/``XschemWire``, ``ihp/qucs_sym.py``'s
``QucsLine``/``QucsArc``/``QucsText``/``QucsPort``) are wrapped by a
small per-domain adapter (``gui/geometry_adapters.py``) into a
``GeometryItem`` -- real coordinates only, no file-format knowledge in
this module at all. Edits made on the canvas (drag = move, Delete key
= remove) call straight back into the real, live domain object via
each item's own ``on_move``/``on_delete`` callback, so the exact same
writers already verified elsewhere (``ihp/xschem_writer.py``/
``ihp/xschem_sch_writer.py``/``ihp/qucs_sym_writer.py``) serialize
whatever the canvas produced -- this module never writes a real file
itself.

**Coordinate system**: real files use an arbitrary, symbol-centered
real coordinate space (origin at the symbol's own real reference
point, Y increasing *downward* -- confirmed by real xschem
convention: a real symbol's own pin `T` labels sit at a real,
*more negative* Y than the pin itself when the label is meant to
appear visually *above* the pin in real xschem, matching a real,
direct on-screen rendering with no flip needed). This canvas maps real
coordinates to pixels via one real, live ``PIXELS_PER_UNIT`` scale
factor and a real, auto-fit origin offset (computed once per real
scene load from its own real bounding box), no per-domain special-
casing.

**Tools** (a real toolbar, one row): **Select** (click to select/drag
to move an existing real shape; ``Delete``/``BackSpace`` removes the
current selection), **Line**/**Arc**/**Text** (click, or click-drag
for Line/Arc, to place a real new shape of that kind -- Arc's own real
start/sweep angle default to a full real circle, ``0``/``360``,
adjustable afterward via the selection's own side form), and, only
when the owning pane supplies them, **Instance** (schematics only --
pick a real ``.sym`` from the existing real symbol library, then click
a position) and **Wire** (schematics only -- click two points).
"""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import simpledialog, ttk
from typing import Callable

_SELECT_COLOR = "#0078d7"
_HANDLE_RADIUS = 4


@dataclass
class GeometryItem:
    """One real, canvas-facing shape -- see this module's own
    docstring for the real domain objects each ``shape`` kind wraps."""

    obj: object
    """The real, live underlying domain object -- mutated in place by
    ``on_move``, matching every other in-memory editor in this
    project (commit-on-switch, not a copy-then-replace)."""
    shape: str
    """One of ``line``/``arc``/``text``/``rect``/``port``/``instance``."""
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    """Real coordinates: for ``line``/``rect``/``port`` these are the
    two real endpoints/corners; for ``arc`` they're the real bounding
    box (matching Tkinter's own ``create_arc`` convention, not
    xschem's center+radius one -- ``gui/geometry_adapters.py`` does
    that real conversion); for ``text``/``instance`` only ``x1``/``y1``
    (the real anchor/reference point) are used."""
    start_angle: float = 0.0
    sweep_angle: float = 360.0
    label: str = ""
    """Real, displayed text -- a text primitive's own real content, a
    port's own real name (if any), or an instance's own real name."""
    color: str = "#000080"
    on_move: Callable[[float, float], None] | None = None
    """Called with a real ``(dx, dy)`` delta in real coordinates after
    a real drag -- mutates the real, live ``obj`` in place."""
    on_delete: Callable[[], None] | None = None
    """Called when the user deletes this real item -- removes ``obj``
    from its real, owning domain list."""
    movable: bool = True
    deletable: bool = True


@dataclass
class Scene:
    items: list[GeometryItem] = field(default_factory=list)


class GeometryCanvas(ttk.Frame):
    def __init__(
        self, parent,
        on_new_line: Callable[[float, float, float, float], None] | None = None,
        on_new_arc: Callable[[float, float, float, float], None] | None = None,
        on_new_text: Callable[[float, float, str], None] | None = None,
        on_new_instance: Callable[[float, float, str], None] | None = None,
        on_new_wire: Callable[[float, float, float, float], None] | None = None,
        on_selection_changed: Callable[[GeometryItem | None], None] | None = None,
        on_scene_changed: Callable[[], None] | None = None,
        pick_symbol: Callable[[], str | None] | None = None,
    ):
        """Every real ``on_new_*``/``pick_symbol`` callback left
        ``None`` simply hides that tool -- e.g. a Symbols pane (no
        real instances/wires of its own) never shows Instance/Wire
        tools at all, rather than showing a real tool that can't
        actually do anything."""

        super().__init__(parent)
        self.scene = Scene()
        self.on_new_line = on_new_line
        self.on_new_arc = on_new_arc
        self.on_new_text = on_new_text
        self.on_new_instance = on_new_instance
        self.on_new_wire = on_new_wire
        self.on_selection_changed = on_selection_changed
        self.on_scene_changed = on_scene_changed
        self.pick_symbol = pick_symbol

        self.tool = tk.StringVar(value="select")
        self.selected: GeometryItem | None = None
        self.scale = 4.0
        self.origin_x = 0.0
        self.origin_y = 0.0
        self._drag_start_canvas: tuple[float, float] | None = None
        self._drag_last_canvas: tuple[float, float] | None = None
        self._draw_start_real: tuple[float, float] | None = None
        self._rubber_band_id: int | None = None
        self._item_by_canvas_id: dict[int, GeometryItem] = {}

        self._build()

    # -- layout ---------------------------------------------------------------

    def _build(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 4))

        ttk.Radiobutton(toolbar, text="Select", variable=self.tool, value="select").pack(side="left")
        ttk.Radiobutton(toolbar, text="Line", variable=self.tool, value="line").pack(side="left")
        ttk.Radiobutton(toolbar, text="Arc", variable=self.tool, value="arc").pack(side="left")
        ttk.Radiobutton(toolbar, text="Text", variable=self.tool, value="text").pack(side="left")
        if self.on_new_instance is not None:
            ttk.Radiobutton(toolbar, text="Instance", variable=self.tool, value="instance").pack(side="left")
        if self.on_new_wire is not None:
            ttk.Radiobutton(toolbar, text="Wire", variable=self.tool, value="wire").pack(side="left")

        ttk.Button(toolbar, text="Delete", command=self._delete_selected).pack(side="left", padx=(12, 0))
        ttk.Button(toolbar, text="Zoom to Fit", command=self.zoom_to_fit).pack(side="left", padx=(6, 0))

        self.status_var = tk.StringVar(value="")
        ttk.Label(toolbar, textvariable=self.status_var, foreground="#666").pack(side="left", padx=(12, 0))

        self.canvas = tk.Canvas(self, background="white", highlightthickness=1, highlightbackground="#ccc")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Delete>", lambda _e: self._delete_selected())
        self.canvas.bind("<BackSpace>", lambda _e: self._delete_selected())
        self.canvas.bind("<Configure>", lambda _e: self.redraw())
        self.canvas.focus_set()
        self.canvas.bind("<Enter>", lambda _e: self.canvas.focus_set())

    # -- coordinate transform ---------------------------------------------

    def _to_canvas(self, x: float, y: float) -> tuple[float, float]:
        return (x - self.origin_x) * self.scale + 20, (y - self.origin_y) * self.scale + 20

    def _to_real(self, cx: float, cy: float) -> tuple[float, float]:
        return (cx - 20) / self.scale + self.origin_x, (cy - 20) / self.scale + self.origin_y

    def zoom_to_fit(self):
        xs, ys = [], []
        for item in self.scene.items:
            xs.extend([item.x1, item.x2])
            ys.extend([item.y1, item.y2])
        if not xs:
            self.scale = 4.0
            self.origin_x = self.origin_y = 0.0
            self.redraw()
            return
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        width = max(max_x - min_x, 1.0)
        height = max(max_y - min_y, 1.0)
        canvas_w = max(self.canvas.winfo_width(), 200)
        canvas_h = max(self.canvas.winfo_height(), 200)
        self.scale = max(min((canvas_w - 40) / width, (canvas_h - 40) / height), 0.1)
        self.origin_x = min_x
        self.origin_y = min_y
        self.redraw()

    # -- scene / rendering --------------------------------------------------

    def set_scene(self, scene: Scene, auto_fit: bool = True):
        self.scene = scene
        self.selected = None
        if self.on_selection_changed is not None:
            self.on_selection_changed(None)
        if auto_fit:
            self.zoom_to_fit()
        else:
            self.redraw()

    def redraw(self):
        self.canvas.delete("all")
        self._item_by_canvas_id = {}
        for item in self.scene.items:
            self._draw_item(item)
        if self.selected is not None and self.selected in self.scene.items:
            self._draw_selection_handles(self.selected)

    def _draw_item(self, item: GeometryItem):
        color = _SELECT_COLOR if item is self.selected else item.color
        x1, y1 = self._to_canvas(item.x1, item.y1)
        x2, y2 = self._to_canvas(item.x2, item.y2)
        if item.shape == "line":
            cid = self.canvas.create_line(x1, y1, x2, y2, fill=color, width=2)
        elif item.shape == "rect":
            cid = self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2)
        elif item.shape == "port":
            cid = self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2, fill="#ffe28a")
            if item.label:
                self.canvas.create_text((x1 + x2) / 2, y1 - 8, text=item.label, fill=color, font=("TkDefaultFont", 8))
        elif item.shape == "arc":
            # Tkinter's own create_arc wants y increasing upward for a
            # visually-correct sweep direction; this project's real
            # coordinate space increases Y downward (see this module's
            # own docstring), so the bbox's own y-ordering is swapped
            # here, not the real, stored data.
            cid = self.canvas.create_arc(
                x1, y2, x2, y1, start=item.start_angle, extent=item.sweep_angle,
                outline=color, width=2, style="arc",
            )
        elif item.shape == "text":
            cid = self.canvas.create_text(x1, y1, text=item.label, fill=color, anchor="w", font=("TkDefaultFont", 9))
        elif item.shape == "instance":
            cid = self.canvas.create_rectangle(x1 - 20, y1 - 20, x1 + 20, y1 + 20, outline=color, width=2, dash=(3, 2))
            self.canvas.create_text(x1, y1, text=item.label, fill=color, font=("TkDefaultFont", 8))
        else:
            return
        self._item_by_canvas_id[cid] = item
        self.canvas.tag_bind(cid, "<ButtonPress-1>", lambda e, it=item: self._select_and_start_drag(it, e))

    def _draw_selection_handles(self, item: GeometryItem):
        for rx, ry in ((item.x1, item.y1), (item.x2, item.y2)):
            cx, cy = self._to_canvas(rx, ry)
            self.canvas.create_oval(
                cx - _HANDLE_RADIUS, cy - _HANDLE_RADIUS, cx + _HANDLE_RADIUS, cy + _HANDLE_RADIUS,
                outline=_SELECT_COLOR, fill="white",
            )

    # -- selection / drag (Select tool) --------------------------------------

    def _select_and_start_drag(self, item: GeometryItem, event):
        if self.tool.get() != "select":
            return
        self.selected = item
        if self.on_selection_changed is not None:
            self.on_selection_changed(item)
        self._drag_start_canvas = (event.x, event.y)
        self._drag_last_canvas = (event.x, event.y)
        self.redraw()

    def select_item(self, item: GeometryItem | None):
        self.selected = item
        if self.on_selection_changed is not None:
            self.on_selection_changed(item)
        self.redraw()

    def _delete_selected(self):
        if self.selected is None or not self.selected.deletable:
            return
        if self.selected.on_delete is not None:
            self.selected.on_delete()
        if self.selected in self.scene.items:
            self.scene.items.remove(self.selected)
        self.selected = None
        if self.on_selection_changed is not None:
            self.on_selection_changed(None)
        if self.on_scene_changed is not None:
            self.on_scene_changed()
        self.redraw()

    # -- mouse handling -------------------------------------------------------

    def _on_press(self, event):
        self.canvas.focus_set()
        tool = self.tool.get()
        if tool == "select":
            # A blank-canvas click (not caught by an item's own
            # tag-bound handler) clears the current selection.
            if self._drag_start_canvas is None:
                self.select_item(None)
            return
        real_x, real_y = self._to_real(event.x, event.y)
        self._draw_start_real = (real_x, real_y)
        if tool == "text":
            self._start_text(real_x, real_y)
            self._draw_start_real = None
        elif tool == "instance":
            self._start_instance(real_x, real_y)
            self._draw_start_real = None

    def _on_drag(self, event):
        tool = self.tool.get()
        if tool == "select" and self.selected is not None and self._drag_start_canvas is not None:
            last_x, last_y = self._drag_last_canvas
            dx_canvas, dy_canvas = event.x - last_x, event.y - last_y
            dx_real, dy_real = dx_canvas / self.scale, dy_canvas / self.scale
            if self.selected.on_move is not None:
                self.selected.on_move(dx_real, dy_real)
            self.selected.x1 += dx_real
            self.selected.y1 += dy_real
            self.selected.x2 += dx_real
            self.selected.y2 += dy_real
            self._drag_last_canvas = (event.x, event.y)
            self.redraw()
        elif tool in ("line", "arc", "wire") and self._draw_start_real is not None:
            if self._rubber_band_id is not None:
                self.canvas.delete(self._rubber_band_id)
            sx, sy = self._to_canvas(*self._draw_start_real)
            self._rubber_band_id = self.canvas.create_line(sx, sy, event.x, event.y, dash=(3, 2), fill="#999")

    def _on_release(self, event):
        tool = self.tool.get()
        if self._rubber_band_id is not None:
            self.canvas.delete(self._rubber_band_id)
            self._rubber_band_id = None

        if tool == "select":
            self._drag_start_canvas = None
            self._drag_last_canvas = None
            if self.on_scene_changed is not None:
                self.on_scene_changed()
            return

        if self._draw_start_real is None:
            return
        real_x1, real_y1 = self._draw_start_real
        real_x2, real_y2 = self._to_real(event.x, event.y)
        self._draw_start_real = None

        if tool == "line" and self.on_new_line is not None:
            self.on_new_line(real_x1, real_y1, real_x2, real_y2)
        elif tool == "arc" and self.on_new_arc is not None:
            self.on_new_arc(real_x1, real_y1, real_x2, real_y2)
        elif tool == "wire" and self.on_new_wire is not None:
            self.on_new_wire(real_x1, real_y1, real_x2, real_y2)
        if self.on_scene_changed is not None:
            self.on_scene_changed()

    def _start_text(self, x: float, y: float):
        if self.on_new_text is None:
            return
        content = simpledialog.askstring("New Text", "Real text content:", parent=self)
        if content:
            self.on_new_text(x, y, content)
            if self.on_scene_changed is not None:
                self.on_scene_changed()

    def _start_instance(self, x: float, y: float):
        if self.on_new_instance is None or self.pick_symbol is None:
            return
        symbol_ref = self.pick_symbol()
        if symbol_ref:
            self.on_new_instance(x, y, symbol_ref)
            if self.on_scene_changed is not None:
                self.on_scene_changed()

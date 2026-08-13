"""Draws the visual diagram for the design rule currently being edited.

Copied verbatim from OpenPDKCreator's own
``scripts/pdk_wizard/gui/rule_canvas.py`` -- pure Tk Canvas drawing
keyed only on layer names/colors/values, no technology-specific
coupling at all.

One function per ``check_type`` renderer key (see ``schema.CHECK_TYPES``).
Each renderer takes the rule's layers, value/units, and a lookup of layer
display colors, and draws directly onto a supplied ``tk.Canvas``. Keeping
this keyed by string (rather than, say, dispatch on the ``DesignRule``
class) is what lets a future extraction-rule check_type register its own
renderer here without touching ``rules_view.py``.
"""

from __future__ import annotations

import tkinter as tk

CANVAS_W = 480
CANVAS_H = 220
DEFAULT_FRAME = "#7f7f7f"
DEFAULT_FILL = "#d9d9d9"


def _color(layer_colors: dict[str, tuple[str, str]], name: str) -> tuple[str, str]:
    return layer_colors.get(name, (DEFAULT_FRAME, DEFAULT_FILL))


def _value_label(value, units: str) -> str:
    if value is None:
        return f"? {units}".strip()
    if isinstance(value, float) and value == int(value):
        value = int(value)
    return f"{value} {units}".strip()


def _dimension(canvas: tk.Canvas, x0: float, x1: float, y: float, label: str) -> None:
    canvas.create_line(x0, y, x1, y, arrow=tk.BOTH, fill="#333333")
    canvas.create_line(x0, y - 6, x0, y + 6, fill="#333333")
    canvas.create_line(x1, y - 6, x1, y + 6, fill="#333333")
    canvas.create_text((x0 + x1) / 2, y - 12, text=label, fill="#333333", font=("TkDefaultFont", 9))


def _vdimension(canvas: tk.Canvas, y0: float, y1: float, x: float, label: str) -> None:
    canvas.create_line(x, y0, x, y1, arrow=tk.BOTH, fill="#333333")
    canvas.create_line(x - 6, y0, x + 6, y0, fill="#333333")
    canvas.create_line(x - 6, y1, x + 6, y1, fill="#333333")
    canvas.create_text(x + 34, (y0 + y1) / 2, text=label, fill="#333333", font=("TkDefaultFont", 9))


def draw_width(canvas, layers, layer_colors, value, units):
    name = layers[0] if layers else "?"
    frame, fill = _color(layer_colors, name)
    x0, x1, y0, y1 = 160, 320, 70, 150
    canvas.create_rectangle(x0, y0, x1, y1, outline=frame, fill=fill, width=2)
    canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=name, font=("TkDefaultFont", 10, "bold"))
    _dimension(canvas, x0, x1, y0 - 24, f"width ≥ {_value_label(value, units)}")


def draw_spacing(canvas, layers, layer_colors, value, units):
    name = layers[0] if layers else "?"
    frame, fill = _color(layer_colors, name)
    y0, y1 = 70, 150
    canvas.create_rectangle(110, y0, 210, y1, outline=frame, fill=fill, width=2)
    canvas.create_rectangle(270, y0, 370, y1, outline=frame, fill=fill, width=2)
    canvas.create_text(160, 110, text=name)
    canvas.create_text(320, 110, text=name)
    _dimension(canvas, 210, 270, 40, f"spacing ≥ {_value_label(value, units)}")


def draw_area(canvas, layers, layer_colors, value, units):
    if len(layers) <= 1:
        name = layers[0] if layers else "?"
        frame, fill = _color(layer_colors, name)
        canvas.create_rectangle(180, 60, 300, 160, outline=frame, fill=fill, width=2)
        canvas.create_text(240, 110, text=name)
    else:
        _stacked_rects(canvas, layers, layer_colors)
    canvas.create_text(
        240, 190, text=f"area ≥ {_value_label(value, units)}", font=("TkDefaultFont", 9)
    )


def _stacked_rects(canvas, layers, layer_colors, x0=170, y0=60, x1=310, y1=160):
    offset = 16
    for i, name in enumerate(layers):
        frame, fill = _color(layer_colors, name)
        canvas.create_rectangle(
            x0 + i * offset, y0 + i * offset, x1 - i * offset, y1 - i * offset,
            outline=frame, fill=fill, stipple="gray50", width=2,
        )
    for i, name in enumerate(layers):
        canvas.create_text(x0 + i * offset + 24, y0 + i * offset + 14, text=name, anchor="w")


def draw_overlap(canvas, layers, layer_colors, value, units):
    _stacked_rects(canvas, layers, layer_colors)
    _dimension(canvas, 202, 278, 190, f"overlap ≥ {_value_label(value, units)}")


def draw_enclosure(canvas, layers, layer_colors, value, units):
    inner = layers[0] if len(layers) > 0 else "?"
    outer = layers[1] if len(layers) > 1 else "?"
    outer_frame, outer_fill = _color(layer_colors, outer)
    inner_frame, inner_fill = _color(layer_colors, inner)
    canvas.create_rectangle(130, 50, 350, 170, outline=outer_frame, fill=outer_fill, width=2)
    canvas.create_text(340, 60, text=outer, anchor="ne", font=("TkDefaultFont", 9))
    canvas.create_rectangle(180, 85, 300, 135, outline=inner_frame, fill=inner_fill, width=2)
    canvas.create_text(240, 110, text=inner)
    _dimension(canvas, 130, 180, 148, f"enc ≥ {_value_label(value, units)}")


def draw_max_length(canvas, layers, layer_colors, value, units):
    name = layers[0] if layers else "?"
    frame, fill = _color(layer_colors, name)
    canvas.create_rectangle(70, 95, 410, 125, outline=frame, fill=fill, width=2)
    canvas.create_text(240, 110, text=name)
    _dimension(canvas, 70, 410, 70, f"length ≤ {_value_label(value, units)}")


def draw_current_density(canvas, layers, layer_colors, value, units):
    name = layers[0] if layers else "?"
    frame, fill = _color(layer_colors, name)
    canvas.create_rectangle(160, 70, 320, 150, outline=frame, fill=fill, width=2)
    canvas.create_text(240, 95, text=name)
    for x in (200, 240, 280):
        canvas.create_line(x, 150, x, 175, arrow=tk.LAST, fill="#b03030", width=2)
    canvas.create_text(
        240, 195, text=f"J ≤ {_value_label(value, units)}", fill="#b03030",
        font=("TkDefaultFont", 9, "bold"),
    )


def draw_max_dimension(canvas, layers, layer_colors, value, units):
    rows = cols = 5
    x0, y0, cell = 150, 55, 24
    for r in range(rows):
        for c in range(cols):
            canvas.create_rectangle(
                x0 + c * cell, y0 + r * cell, x0 + (c + 1) * cell, y0 + (r + 1) * cell,
                outline="#9467bd", fill="#d4b9da",
            )
    canvas.create_text(
        240, y0 + rows * cell + 20,
        text=f"array bound ≤ {_value_label(value, units)}", font=("TkDefaultFont", 9),
    )


def draw_density_window(canvas, layers, layer_colors, value, units):
    canvas.create_rectangle(140, 50, 340, 170, outline="#333333", dash=(4, 2))
    canvas.create_text(240, 40, text="density window", font=("TkDefaultFont", 9))
    for i in range(6):
        canvas.create_rectangle(
            150 + (i % 3) * 60, 60 + (i // 3) * 55, 195 + (i % 3) * 60, 100 + (i // 3) * 55,
            outline="#2ca02c", fill="#a1d99b",
        )
    canvas.create_text(
        240, 190, text=f"density bound: {_value_label(value, units)}", font=("TkDefaultFont", 9)
    )


RENDERERS = {
    "width": draw_width,
    "spacing": draw_spacing,
    "area": draw_area,
    "overlap": draw_overlap,
    "enclosure": draw_enclosure,
    "max_length": draw_max_length,
    "current_density": draw_current_density,
    "max_dimension": draw_max_dimension,
    "density_window": draw_density_window,
}


def render(canvas: tk.Canvas, renderer_key: str, layers, layer_colors, value, units) -> None:
    canvas.delete("all")
    fn = RENDERERS.get(renderer_key)
    if fn is None:
        canvas.create_text(
            CANVAS_W / 2, CANVAS_H / 2, text="No diagram available for this check type"
        )
        return
    fn(canvas, layers, layer_colors, value, units)

"""Per-domain adapters converting real domain objects
(``pdklib/xschem.py``/``pdklib/xschem_sch.py``/``pdklib/qucs_sym.py``) into
``geometry_canvas.GeometryItem``s -- the only place any of these three
real formats' own field names/shapes are known to the graphical
editor; ``geometry_canvas.py`` itself stays completely format-
agnostic (see its own docstring).

Each adapter function takes the real, live in-memory structure (the
same object the App's own per-file cache holds, and the same object
``pdklib/*_writer.py`` serializes) and returns a real
``geometry_canvas.Scene`` whose items' own ``on_move``/``on_delete``
closures mutate that *exact* structure in place -- a drag or delete on
the canvas is immediately visible to (and exportable by) every other
tab, the same "one shared, live object" discipline every other
editable domain in this project already uses.
"""

from __future__ import annotations

from ..pdklib import lef as lef_mod
from ..pdklib import qucs_sym as qucs_mod
from ..pdklib import xschem as xschem_mod
from ..pdklib import xschem_sch as xschem_sch_mod
from .geometry_canvas import GeometryItem, Scene

_PIN_STEMS = {"ipin", "opin", "iopin"}


def _remove(items: list, obj: object) -> None:
    if obj in items:
        items.remove(obj)


def xschem_symbol_scene(symbol: xschem_mod.XschemSymbol) -> Scene:
    items: list[GeometryItem] = []

    for pin in symbol.pins:
        def move(dx, dy, p=pin):
            p.x1 += dx; p.y1 += dy; p.x2 += dx; p.y2 += dy
        items.append(GeometryItem(
            obj=pin, shape="port", x1=pin.x1, y1=pin.y1, x2=pin.x2, y2=pin.y2, label=f"{pin.name} ({pin.direction})",
            color="#8b4513", on_move=move, on_delete=lambda p=pin: _remove(symbol.pins, p),
        ))

    for box in symbol.boxes:
        def move(dx, dy, b=box):
            b.x1 += dx; b.y1 += dy; b.x2 += dx; b.y2 += dy
        items.append(GeometryItem(
            obj=box, shape="rect", x1=box.x1, y1=box.y1, x2=box.x2, y2=box.y2,
            color="#666666", on_move=move, on_delete=lambda b=box: _remove(symbol.boxes, b),
        ))

    for line in symbol.lines:
        def move(dx, dy, l=line):
            l.x1 += dx; l.y1 += dy; l.x2 += dx; l.y2 += dy
        items.append(GeometryItem(
            obj=line, shape="line", x1=line.x1, y1=line.y1, x2=line.x2, y2=line.y2,
            on_move=move, on_delete=lambda l=line: _remove(symbol.lines, l),
        ))

    for arc in symbol.arcs:
        def move(dx, dy, a=arc):
            a.cx += dx; a.cy += dy
        items.append(GeometryItem(
            obj=arc, shape="arc",
            x1=arc.cx - arc.radius, y1=arc.cy - arc.radius, x2=arc.cx + arc.radius, y2=arc.cy + arc.radius,
            start_angle=arc.start_angle, sweep_angle=arc.sweep_angle,
            on_move=move, on_delete=lambda a=arc: _remove(symbol.arcs, a),
        ))

    for text in symbol.texts:
        def move(dx, dy, t=text):
            t.x += dx; t.y += dy
        items.append(GeometryItem(
            obj=text, shape="text", x1=text.x, y1=text.y, x2=text.x, y2=text.y, label=text.text,
            color="#800000", on_move=move, on_delete=lambda t=text: _remove(symbol.texts, t),
        ))

    return Scene(items=items)


def new_xschem_line(symbol: xschem_mod.XschemSymbol, x1: float, y1: float, x2: float, y2: float) -> None:
    symbol.lines.append(xschem_mod.XschemLine(layer="4", x1=round(x1, 2), y1=round(y1, 2), x2=round(x2, 2), y2=round(y2, 2)))


def new_xschem_arc(symbol: xschem_mod.XschemSymbol, x1: float, y1: float, x2: float, y2: float) -> None:
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    radius = max(abs(x2 - x1), abs(y2 - y1)) / 2 or 5.0
    symbol.arcs.append(xschem_mod.XschemArc(layer="4", cx=round(cx, 2), cy=round(cy, 2), radius=round(radius, 2), start_angle=0.0, sweep_angle=360.0))


def new_xschem_text(symbol: xschem_mod.XschemSymbol, x: float, y: float, content: str) -> None:
    symbol.texts.append(xschem_mod.XschemText(text=content, x=round(x, 2), y=round(y, 2), rot=0, flip=0, hsize=0.2, vsize=0.2))


def xschem_schematic_scene(schematic: xschem_sch_mod.XschemSchematic) -> Scene:
    items: list[GeometryItem] = []

    for inst in schematic.instances:
        def move(dx, dy, i=inst):
            i.x += dx; i.y += dy
        items.append(GeometryItem(
            obj=inst, shape="instance", x1=inst.x, y1=inst.y, x2=inst.x, y2=inst.y,
            label=inst.name, color="#0a5f38" if inst.is_pin else "#333333",
            on_move=move, on_delete=lambda i=inst: _remove(schematic.instances, i),
        ))

    for wire in schematic.wires:
        def move(dx, dy, w=wire):
            w.x1 += dx; w.y1 += dy; w.x2 += dx; w.y2 += dy
        items.append(GeometryItem(
            obj=wire, shape="line", x1=wire.x1, y1=wire.y1, x2=wire.x2, y2=wire.y2, label=wire.label,
            color="#c00000", on_move=move, on_delete=lambda w=wire: _remove(schematic.wires, w),
        ))

    for box in schematic.boxes:
        def move(dx, dy, b=box):
            b.x1 += dx; b.y1 += dy; b.x2 += dx; b.y2 += dy
        items.append(GeometryItem(
            obj=box, shape="rect", x1=box.x1, y1=box.y1, x2=box.x2, y2=box.y2,
            color="#666666", on_move=move, on_delete=lambda b=box: _remove(schematic.boxes, b),
        ))

    for line in schematic.lines:
        def move(dx, dy, l=line):
            l.x1 += dx; l.y1 += dy; l.x2 += dx; l.y2 += dy
        items.append(GeometryItem(
            obj=line, shape="line", x1=line.x1, y1=line.y1, x2=line.x2, y2=line.y2,
            on_move=move, on_delete=lambda l=line: _remove(schematic.lines, l),
        ))

    for arc in schematic.arcs:
        def move(dx, dy, a=arc):
            a.cx += dx; a.cy += dy
        items.append(GeometryItem(
            obj=arc, shape="arc",
            x1=arc.cx - arc.radius, y1=arc.cy - arc.radius, x2=arc.cx + arc.radius, y2=arc.cy + arc.radius,
            start_angle=arc.start_angle, sweep_angle=arc.sweep_angle,
            on_move=move, on_delete=lambda a=arc: _remove(schematic.arcs, a),
        ))

    for text in schematic.texts:
        def move(dx, dy, t=text):
            t.x += dx; t.y += dy
        items.append(GeometryItem(
            obj=text, shape="text", x1=text.x, y1=text.y, x2=text.x, y2=text.y, label=text.text,
            color="#800000", on_move=move, on_delete=lambda t=text: _remove(schematic.texts, t),
        ))

    return Scene(items=items)


def new_xschem_sch_wire(schematic: xschem_sch_mod.XschemSchematic, x1: float, y1: float, x2: float, y2: float) -> None:
    schematic.wires.append(xschem_sch_mod.XschemWire(x1=round(x1), y1=round(y1), x2=round(x2), y2=round(y2)))


def new_xschem_sch_instance(schematic: xschem_sch_mod.XschemSchematic, x: float, y: float, symbol_ref: str) -> None:
    from pathlib import Path

    default_name = f"X{len(schematic.instances) + 1}"
    schematic.instances.append(
        xschem_sch_mod.XschemInstance(
            symbol_ref=symbol_ref, x=round(x), y=round(y), rot=0, flip=0, name=default_name,
            resolved_path=None,
        )
    )


def qucs_symbol_scene(geometry: qucs_mod.QucsSymbolGeometry) -> Scene:
    items: list[GeometryItem] = []

    for port in geometry.ports:
        def move(dx, dy, p=port):
            p.x += round(dx); p.y += round(dy)
        items.append(GeometryItem(
            obj=port, shape="port", x1=port.x - 3, y1=port.y - 3, x2=port.x + 3, y2=port.y + 3,
            label=port.hint or f"P({port.port_type})", color="#8b4513",
            on_move=move, on_delete=lambda p=port: _remove(geometry.ports, p),
        ))

    for line in geometry.lines:
        def move(dx, dy, l=line):
            l.x1 += round(dx); l.y1 += round(dy); l.x2 += round(dx); l.y2 += round(dy)
        items.append(GeometryItem(
            obj=line, shape="line", x1=line.x1, y1=line.y1, x2=line.x2, y2=line.y2, color=line.color,
            on_move=move, on_delete=lambda l=line: _remove(geometry.lines, l),
        ))

    for arc in geometry.arcs:
        def move(dx, dy, a=arc):
            a.x += round(dx); a.y += round(dy)
        items.append(GeometryItem(
            obj=arc, shape="arc", x1=arc.x, y1=arc.y, x2=arc.x + arc.arc_width, y2=arc.y + arc.height,
            start_angle=arc.angle / 16.0, sweep_angle=arc.sweep_len / 16.0, color=arc.color,
            on_move=move, on_delete=lambda a=arc: _remove(geometry.arcs, a),
        ))

    for text in geometry.texts:
        def move(dx, dy, t=text):
            t.x += round(dx); t.y += round(dy)
        items.append(GeometryItem(
            obj=text, shape="text", x1=text.x, y1=text.y, x2=text.x, y2=text.y, label=text.text, color=text.color,
            on_move=move, on_delete=lambda t=text: _remove(geometry.texts, t),
        ))

    return Scene(items=items)


def new_qucs_line(geometry: qucs_mod.QucsSymbolGeometry, x1: float, y1: float, x2: float, y2: float) -> None:
    geometry.lines.append(qucs_mod.QucsLine(x1=round(x1), y1=round(y1), x2=round(x2), y2=round(y2)))


def new_qucs_arc(geometry: qucs_mod.QucsSymbolGeometry, x1: float, y1: float, x2: float, y2: float) -> None:
    x, y = min(x1, x2), min(y1, y2)
    width, height = max(abs(x2 - x1), 1), max(abs(y2 - y1), 1)
    geometry.arcs.append(qucs_mod.QucsArc(x=round(x), y=round(y), arc_width=round(width), height=round(height), angle=0, sweep_len=5760))


def new_qucs_text(geometry: qucs_mod.QucsSymbolGeometry, x: float, y: float, content: str) -> None:
    geometry.texts.append(qucs_mod.QucsText(x=round(x), y=round(y), size=12, color="#800000", text=content))


def lef_pin_scene(pin: lef_mod.LefPin) -> Scene:
    """One real ``GeometryItem`` per real rect (not per ``LefPort`` --
    a real port can hold more than one rect on the same real layer,
    see ``LefPort.rects``' own docstring), the first real, non-symbol/
    schematic domain to reuse this shared canvas. Uses the same real
    ``"port"`` shape xschem/Qucs-S pins already use (a filled,
    labeled rectangle) -- the closest real visual match, since this
    *is* the real port geometry itself, labeled with its own real
    layer name (several real rects can legitimately overlap across
    different real layers on one real pin)."""

    items: list[GeometryItem] = []
    for port in pin.ports:
        for idx, rect in enumerate(port.rects):
            # A rect is a real, immutable tuple -- captured by *index*,
            # not by value, so repeated incremental on_move calls
            # during one real drag (geometry_canvas.py calls back with
            # a small per-step delta each mouse-move, not one final
            # total) keep updating the *same* real list slot rather
            # than failing to re-find a tuple that's already changed.
            def move(dx, dy, p=port, i=idx):
                r = p.rects[i]
                p.rects[i] = (r[0] + dx, r[1] + dy, r[2] + dx, r[3] + dy)

            def delete(p=port, i=idx):
                del p.rects[i]
                if not p.rects and p in pin.ports:
                    pin.ports.remove(p)

            items.append(GeometryItem(
                obj=rect, shape="port", x1=rect[0], y1=rect[1], x2=rect[2], y2=rect[3],
                label=port.layer, color="#8b4513", on_move=move, on_delete=delete,
            ))
    return Scene(items=items)


def new_lef_port_rect(pin: lef_mod.LefPin, layer: str, x1: float, y1: float, x2: float, y2: float) -> None:
    """A real new rect on *layer* -- appended to the pin's own real,
    existing ``LefPort`` for that layer when one is already selected
    (matching real ``LAYER`` occurrences legitimately repeating with a
    different real rect, e.g. a real multi-cut via's own layer), or a
    real, brand-new ``LefPort`` otherwise. Real coordinates are
    rounded to 3 decimal places (real LEF is in real microns; this
    project's own real, confirmed manufacturing grids are all
    coarser than 0.001um -- matches the precision every other real
    micron-valued field in this project already rounds display/edit
    values to)."""

    rect = (round(min(x1, x2), 3), round(min(y1, y2), 3), round(max(x1, x2), 3), round(max(y1, y2), 3))
    for port in pin.ports:
        if port.layer == layer:
            port.rects.append(rect)
            return
    pin.ports.append(lef_mod.LefPort(layer=layer, rects=[rect]))

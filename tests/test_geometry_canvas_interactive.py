import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

xv = app.xschem_view
sym_pane = xv._symbols
sym_pane.file_var.set("libs.tech/xschem/sg13g2_stdcells/sg13g2_inv_1.sym")
sym_pane._refresh_all()
root.update()

canvas_view = sym_pane.canvas_view
canvas_view.tool.set("select")

# --- Select + drag an existing pin ---
pin_item = next(it for it in canvas_view.scene.items if it.shape == "port" and "A" in it.label)
pin_obj = pin_item.obj
before_x1 = pin_obj.x1
canvas_view._select_and_start_drag(pin_item, SimpleNamespace(x=100, y=100))
canvas_view._on_drag(SimpleNamespace(x=120, y=100))  # 20 canvas px right
root.update()
after_x1 = pin_obj.x1
print("pin x1 before/after drag:", before_x1, after_x1)
assert after_x1 != before_x1
canvas_view._on_release(SimpleNamespace(x=120, y=100))
print("PASS: dragging a pin on the canvas moves the real, underlying XschemPin object.")

# --- Draw tools: Line via click-drag ---
canvas_view.tool.set("line")
sx, sy = canvas_view._to_canvas(0, 0)
ex, ey = canvas_view._to_canvas(50, 50)
canvas_view._on_press(SimpleNamespace(x=sx, y=sy))
canvas_view._on_drag(SimpleNamespace(x=ex, y=ey))
before_line_count = len(sym_pane.current.lines)
canvas_view._on_release(SimpleNamespace(x=ex, y=ey))
root.update()
print("lines before/after draw:", before_line_count, len(sym_pane.current.lines))
assert len(sym_pane.current.lines) == before_line_count + 1
print("PASS: drawing a new Line via the canvas adds a real XschemLine.")

# --- Draw tool: Arc ---
canvas_view.tool.set("arc")
before_arc_count = len(sym_pane.current.arcs)
canvas_view._on_press(SimpleNamespace(x=sx, y=sy))
canvas_view._on_release(SimpleNamespace(x=ex, y=ey))
root.update()
assert len(sym_pane.current.arcs) == before_arc_count + 1
print("PASS: drawing a new Arc via the canvas adds a real XschemArc.")

# --- Delete selected pin ---
canvas_view.tool.set("select")
canvas_view.select_item(pin_item)
before_pin_count = len(sym_pane.current.pins)
canvas_view._delete_selected()
root.update()
print("pins before/after delete:", before_pin_count, len(sym_pane.current.pins))
assert len(sym_pane.current.pins) == before_pin_count - 1
assert len(sym_pane.pins_editor.ports) == before_pin_count - 1  # Pins table stayed in sync
print("PASS: deleting a selected item on the canvas removes it, and the Pins table stays in sync.")

# --- Real write-back reflects all canvas edits ---
import tempfile
from openpdkcreator import export as export_mod

xv.commit_pending_edits()
with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    written = export_mod.export_xschem_symbols(PDK_ROOT, app.xschem_symbol_cache, dest_root=export_dir)
    sym_path = [p for p in written if p.name == "sg13g2_inv_1.sym"][0]
    text = sym_path.read_text()
    reparsed_lines = text.count("\nL ")
    reparsed_arcs = text.count("\nA ")
    print("exported file line/arc counts:", reparsed_lines, reparsed_arcs)
    assert reparsed_lines == before_line_count + 1
    assert reparsed_arcs == before_arc_count + 1
    assert "name=A" not in text  # deleted pin gone
    print("PASS: real write-back reflects every canvas edit (drag/draw/delete).")

root.destroy()
print("ALL INTERACTIVE CANVAS TESTS PASS")

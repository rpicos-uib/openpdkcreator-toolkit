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
sch_pane = xv._schematics
sch_pane.file_var.set("libs.tech/xschem/sg13g2_stdcells/sg13g2_inv_1.sch")
sch_pane._refresh_all()
root.update()

canvas_view = sch_pane.canvas_view

# --- Draw a new wire via click-drag ---
canvas_view.tool.set("wire")
sx, sy = canvas_view._to_canvas(-100, -100)
ex, ey = canvas_view._to_canvas(-50, -50)
before_wires = len(sch_pane.current.wires)
canvas_view._on_press(SimpleNamespace(x=sx, y=sy))
canvas_view._on_release(SimpleNamespace(x=ex, y=ey))
root.update()
print("wires before/after:", before_wires, len(sch_pane.current.wires))
assert len(sch_pane.current.wires) == before_wires + 1
assert len(sch_pane.wires_tree.get_children()) == before_wires + 1  # tree stayed in sync
print("PASS: drawing a new wire adds a real XschemWire and syncs the Wires table.")

# --- Place a new instance (mock the symbol-picker dialog) ---
import openpdkcreator.gui.xschem_view as xschem_view_mod
original_picker = xschem_view_mod._pick_symbol_dialog
xschem_view_mod._pick_symbol_dialog = lambda parent, pdk_root: "sg13g2_pr/sg13_lv_nmos.sym"

canvas_view.tool.set("instance")
px, py = canvas_view._to_canvas(300, 300)
before_instances = len(sch_pane.current.instances)
try:
    canvas_view._on_press(SimpleNamespace(x=px, y=py))
finally:
    xschem_view_mod._pick_symbol_dialog = original_picker
root.update()
print("instances before/after:", before_instances, len(sch_pane.current.instances))
assert len(sch_pane.current.instances) == before_instances + 1
assert len(sch_pane.instances_tree.get_children()) == before_instances + 1
new_inst = sch_pane.current.instances[-1]
print("new instance:", new_inst.symbol_ref, new_inst.x, new_inst.y, new_inst.name)
assert new_inst.symbol_ref == "sg13g2_pr/sg13_lv_nmos.sym"
print("PASS: placing a new instance via the canvas adds a real XschemInstance and syncs the Instances table.")

# --- Qucs-S Symbols: drag a port, draw a new line ---
qv = app.qucs_view
qsym_pane = qv._symbols
qsym_pane.file_var.set("libs.tech/qucs-s/symbols/Mos.sym")
qsym_pane._refresh_all()
root.update()

qcanvas = qsym_pane.canvas_view
qcanvas.tool.set("select")
port_item = next(it for it in qcanvas.scene.items if it.shape == "port")
port_obj = port_item.obj
before_x = port_obj.x
qcanvas._select_and_start_drag(port_item, SimpleNamespace(x=100, y=100))
qcanvas._on_drag(SimpleNamespace(x=140, y=100))
qcanvas._on_release(SimpleNamespace(x=140, y=100))
root.update()
print("qucs port x before/after:", before_x, port_obj.x)
assert port_obj.x != before_x
print("PASS: dragging a Qucs-S port on the canvas moves the real QucsPort object.")

qcanvas.tool.set("line")
sx2, sy2 = qcanvas._to_canvas(0, 0)
ex2, ey2 = qcanvas._to_canvas(10, 10)
before_qlines = len(qsym_pane.current.lines)
qcanvas._on_press(SimpleNamespace(x=sx2, y=sy2))
qcanvas._on_release(SimpleNamespace(x=ex2, y=ey2))
root.update()
assert len(qsym_pane.current.lines) == before_qlines + 1
print("PASS: drawing a new Line on the Qucs-S canvas adds a real QucsLine.")

# --- Real write-back reflects the new schematic instance/wire ---
import tempfile
from openpdkcreator import export as export_mod

xv.commit_pending_edits()
with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    written = export_mod.export_xschem_schematics(PDK_ROOT, app.xschem_schematic_cache, dest_root=export_dir)
    sch_path = [p for p in written if p.name == "sg13g2_inv_1.sch"][0]
    text = sch_path.read_text()
    assert "sg13g2_pr/sg13_lv_nmos.sym" in text
    assert text.count("\nN ") >= before_wires + 1 or text.count("N ") >= before_wires + 1
    print("PASS: real .sch write-back contains the new instance and wire.")

root.destroy()
print("ALL SCHEMATIC/QUCS CANVAS TESTS PASS")

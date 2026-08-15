import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

xv = app.xschem_view
qv = app.qucs_view

# --- xschem Symbols canvas ---
sym_pane = xv._symbols
sym_pane.file_var.set("libs.tech/xschem/sg13g2_stdcells/sg13g2_inv_1.sym")
sym_pane._refresh_all()
root.update()
scene = sym_pane.canvas_view.scene
print("xschem sym scene items:", len(scene.items))
kinds = {}
for item in scene.items:
    kinds[item.shape] = kinds.get(item.shape, 0) + 1
print("kinds:", kinds)
assert kinds.get("port") == 2
assert kinds.get("line") == 5
assert kinds.get("arc") == 1
assert kinds.get("text") == 4
print("PASS: xschem Symbols canvas scene matches real inverter geometry.")

# --- xschem Schematics canvas ---
sch_pane = xv._schematics
sch_pane.file_var.set("libs.tech/xschem/sg13g2_stdcells/sg13g2_inv_1.sch")
sch_pane._refresh_all()
root.update()
scene2 = sch_pane.canvas_view.scene
kinds2 = {}
for item in scene2.items:
    kinds2[item.shape] = kinds2.get(item.shape, 0) + 1
print("xschem sch scene kinds:", kinds2)
assert kinds2.get("instance") == 6  # 2 transistors + 4 pins
assert kinds2.get("line") == 16  # wires
print("PASS: xschem Schematics canvas scene matches real inverter schematic.")

# --- Qucs-S Symbols canvas ---
qsym_pane = qv._symbols
qsym_pane.file_var.set("libs.tech/qucs-s/symbols/Mos.sym")
qsym_pane._refresh_all()
root.update()
scene3 = qsym_pane.canvas_view.scene
kinds3 = {}
for item in scene3.items:
    kinds3[item.shape] = kinds3.get(item.shape, 0) + 1
print("qucs sym scene kinds:", kinds3)
assert kinds3.get("port") == 8
print("PASS: Qucs-S Symbols canvas scene populated correctly.")

root.destroy()
print("ALL SMOKE TESTS PASS")

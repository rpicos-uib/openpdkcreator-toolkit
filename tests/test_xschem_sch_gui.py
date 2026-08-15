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
sch_pane = xv._schematics
print("real .sch files loaded:", len(sch_pane.sch_files))
assert len(sch_pane.sch_files) == 100, len(sch_pane.sch_files)

target = "libs.tech/xschem/sg13g2_stdcells/sg13g2_inv_1.sch"
assert target in sch_pane.sch_files
sch_pane.file_var.set(target)
sch_pane._refresh_all()
root.update()

instances = sch_pane.instances_tree.get_children()
pins = sch_pane.pins_tree.get_children()
wires = sch_pane.wires_tree.get_children()
print("instances:", len(instances), "pins:", len(pins), "wires:", len(wires))
assert len(instances) == 6, len(instances)  # 2 transistors + 4 pin instances
assert len(pins) == 4, len(pins)
assert len(wires) == 16, len(wires)

pin_values = sorted(sch_pane.pins_tree.item(iid)["values"] for iid in pins)
print("pin rows:", pin_values)
names = {row[0] for row in pin_values}
assert names == {"p1", "p2", "p3", "p4"}

# Confirm the "resolved" column correctly distinguishes real PDK symbols
# from xschem's own external/bundled ones.
resolved_flags = {sch_pane.instances_tree.item(iid)["values"][1]: sch_pane.instances_tree.item(iid)["values"][6] for iid in instances}
print("resolved flags:", resolved_flags)
assert resolved_flags["sg13g2_pr/sg13_lv_nmos.sym"] == "PDK"
assert resolved_flags["opin.sym"] == "external"

print("summary:", sch_pane.summary_var.get())

# Switch to start_page.sch (the real top-level exception file) and
# confirm it loads without error.
sch_pane.file_var.set("libs.tech/xschem/start_page.sch")
sch_pane._refresh_all()
root.update()
print("start_page.sch summary:", sch_pane.summary_var.get())
assert len(sch_pane.instances_tree.get_children()) == 15

root.destroy()
print("ALL PASS")

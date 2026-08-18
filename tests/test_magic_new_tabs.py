import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("ihp-sg13g2")
mtv._refresh_all()
root.update()

assert len(mtv.compose_editor.tree.get_children()) == 39, len(mtv.compose_editor.tree.get_children())
assert len(mtv.connect_editor.tree.get_children()) == 20, len(mtv.connect_editor.tree.get_children())
assert len(mtv.drc_tree.get_children()) == 209, len(mtv.drc_tree.get_children())  # 192 width/spacing/maxwidth + 17 angles
assert len(mtv.extract_resist_editor.tree.get_children()) == 30, len(mtv.extract_resist_editor.tree.get_children())
assert len(mtv.extract_plane_order_editor.tree.get_children()) == 14, len(mtv.extract_plane_order_editor.tree.get_children())
print("PASS: all 5 new tabs populated with the expected real counts.")

# spot-check one real row's rendered values
row = mtv.compose_editor.tree.item(mtv.compose_editor.tree.get_children()[0])["values"]
print("compose row 0:", row)
assert row[0] == "compose"

drc_row = None
for iid in mtv.drc_tree.get_children():
    values = mtv.drc_tree.item(iid)["values"]
    if "Act.a" in str(values[3]):
        drc_row = values
        break
print("drc Act.a row:", drc_row)
assert drc_row is not None
assert drc_row[0] == "width"
assert abs(float(drc_row[2]) - 0.15) < 1e-9

print("Summary:", mtv.summary_var.get())
root.destroy()
print("ALL PASS")

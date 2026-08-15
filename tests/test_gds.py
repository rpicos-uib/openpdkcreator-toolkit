import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

app.cell_hub_view.family_var.set("sg13g2_stdcell")
app.cell_hub_view._refresh_cells()
root.update()

target = "sg13g2_a21o_1"
assert target in app.cell_hub_view.cells_tree.get_children()
app.cell_hub_view.cells_tree.selection_set(target)
app.cell_hub_view._on_cell_select()
root.update()

gds_text = app.cell_hub_view.gds_var.get()
print(f"GDS info shown: {gds_text!r}")
assert "shape" in gds_text and "layer" in gds_text, "expected real GDS structural info, got a generic message"
assert "µm" in gds_text

cv = app.cell_hub_view.current_cell
assert cv.gds_cell is not None
assert cv.gds_cell.total_shapes == 72
print("PASS: By Cell tab shows real GDS structural info for a real cell.")

root.destroy()
print("ALL PASS")

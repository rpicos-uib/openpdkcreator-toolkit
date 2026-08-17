import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

lv = app.layers_view
layers = app.project.layers
assert len(layers) == 377, len(layers)


def tree_names():
    return [lv.tree.set(iid, "name") for iid in lv.tree.get_children()]


# --- Default display order is real stack_order (unsorted click state) ---
assert lv._sort_column is None
assert tree_names()[:3] == ["Substrate.drawing", "Substrate.text", "Activ.drawing"]
print("PASS: with no header clicked, the list shows real stack_order order.")

# --- Clicking "Name" sorts the displayed list alphabetically ---
lv._sort_by("name")
root.update()
names = tree_names()
assert names == sorted(names, key=str.lower), names[:5]
assert lv._sort_column == "name" and lv._sort_reverse is False
assert lv.tree.heading("name", "text") == "Name ▲"
print("PASS: clicking the Name header sorts the real, displayed list alphabetically.")

# --- Clicking the same header again reverses the sort ---
lv._sort_by("name")
root.update()
names_desc = tree_names()
assert names_desc == sorted(names, key=str.lower, reverse=True)
assert lv._sort_reverse is True
assert lv.tree.heading("name", "text") == "Name ▼"
print("PASS: clicking the same header again reverses to descending order.")

# --- Clicking a different header switches the sort column and resets
# to ascending ---
lv._sort_by("purpose")
root.update()
purposes = [lv.tree.set(iid, "purpose") for iid in lv.tree.get_children()]
assert purposes == sorted(purposes, key=str.lower)
assert lv._sort_column == "purpose" and lv._sort_reverse is False
assert lv.tree.heading("purpose", "text") == "Purpose ▲"
assert lv.tree.heading("name", "text") == "Name"  # the old marker is cleared
print("PASS: clicking a different header switches columns and resets to ascending.")

# --- Sorting is display-only: Move Up/Down still operates on real
# stack_order, unaffected by the current display sort ---
lv._sort_by("purpose")  # leave the list sorted by something other than stack_order
root.update()
by_stack_order = app.project.sorted_layers()
first_real, second_real = by_stack_order[0], by_stack_order[1]
lv.tree.selection_set(lv._iid(first_real))
root.update()
lv._move(1)
root.update()
assert first_real.stack_order == 1 and second_real.stack_order == 0
print("PASS: Move Up/Down still swaps real stack_order correctly regardless of the current display sort.")
# swap back
lv._move(-1)
root.update()
assert first_real.stack_order == 0 and second_real.stack_order == 1

# --- Sort survives a Name/Purpose filter change (still real, still
# applied to whatever's currently shown) ---
lv._sort_by("name")
root.update()
lv.filter_var.set("Activ")
root.update()
filtered_names = tree_names()
assert len(filtered_names) > 0
assert filtered_names == sorted(filtered_names, key=str.lower)
lv.filter_var.set("")
root.update()
print("PASS: the active sort still applies after the Name filter narrows the list.")

# --- GDS column sorts numerically (by real layer/datatype), not as text ---
lv._sort_by("gds")
root.update()
gds_layers = [lv._layer_by_iid[iid].gds_layer for iid in lv.tree.get_children()]
real_gds_layers = [g for g in gds_layers if g is not None]
assert real_gds_layers == sorted(real_gds_layers)
print("PASS: the GDS column sorts numerically by real layer/datatype.")

# --- Show All: after narrowing the Purpose selection, Show All
# restores every real purpose in one click ---
lv._sort_by("stack_order")
lv.purpose_listbox.selection_clear(0, tk.END)
lv.purpose_listbox.selection_set(0)
lv.refresh()
root.update()
assert len(lv.tree.get_children()) < 377
lv._select_all_purposes()
root.update()
assert len(lv.tree.get_children()) == 377
assert len(lv.purpose_listbox.curselection()) == lv.purpose_listbox.size()
print("PASS: Show All restores every real purpose and the full 377-layer view in one click.")

root.destroy()
print("ALL LAYERS SORT + SHOW ALL TESTS PASS")

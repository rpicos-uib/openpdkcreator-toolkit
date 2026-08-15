import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

chv = app.cell_hub_view
chv.family_var.set("sg13g2_stdcell")
chv._refresh_cells()
root.update()
chv.cells_tree.selection_set("sg13g2_a21o_1")
chv._on_cell_select()
root.update()
cv = chv.current_cell
assert cv.liberty_entries, "expected real liberty entries"
print(f"Liberty entries for sg13g2_a21o_1: {len(cv.liberty_entries)}")

cell_entry, path = cv.liberty_entries[0]
print(f"First corner: {path.name}, pins: {[(p.name, p.direction, p.capacitance) for p in cell_entry.pins]}")

from openpdkcreator.gui.liberty_editor import LibertyPinEditor
editor = LibertyPinEditor(root)
editor.set_cell(cell_entry)
root.update()

pin = cell_entry.pins[0]
original_direction = pin.direction
new_direction = "inout" if original_direction != "inout" else "input"
editor.pin_vars["direction"].set(new_direction)
root.update()
assert pin.direction == new_direction, pin.direction
print(f"PASS: edited pin {pin.name} direction {original_direction} -> {pin.direction}")

if pin.timing_arcs:
    arc = pin.timing_arcs[0]
    original_related = arc.related_pin
    new_related = "ZZ_TEST"
    editor._load_arc_into_form(arc)
    root.update()
    editor.arc_vars["related_pin"].set(new_related)
    root.update()
    assert arc.related_pin == new_related, arc.related_pin
    print(f"PASS: edited timing arc related_pin {original_related} -> {arc.related_pin}")
else:
    print("(pin has no timing arcs to test directly, trying X)")
    xpin = next(p for p in cell_entry.pins if p.name == "X")
    assert xpin.timing_arcs
    editor._load_pin_into_form(xpin)
    root.update()
    arc = xpin.timing_arcs[0]
    editor._load_arc_into_form(arc)
    root.update()
    editor.arc_vars["timing_type"].set("edited_type")
    root.update()
    assert arc.timing_type == "edited_type"
    print("PASS: edited timing arc timing_type on X pin")

# New/Delete pin
editor._new_pin()
root.update()
assert len(cell_entry.pins) == 5
print(f"PASS: New Pin works, count now {len(cell_entry.pins)}")

editor.pins_tree.selection_set(editor._pin_iid(cell_entry.pins[0]))
editor._delete_pin()
root.update()
assert len(cell_entry.pins) == 4
print(f"PASS: Delete Pin works, count now {len(cell_entry.pins)}")

# --- Persistence across family switch ---
chv.family_var.set("sg13g2_io")
chv._refresh_cells()
root.update()
chv.family_var.set("sg13g2_stdcell")
chv._refresh_cells()
root.update()
chv.cells_tree.selection_set("sg13g2_a21o_1")
chv._on_cell_select()
root.update()
re_cv = chv.current_cell
re_cell_entry, re_path = re_cv.liberty_entries[0]
assert re_path == path
assert re_cell_entry is cell_entry, "family switch re-parsed instead of reusing the cached, edited LibertyCell"
print("PASS: switching families and back reuses the same cached LibertyCell object (no silent data loss).")

root.destroy()
print("ALL PASS")

import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator.gui.layers_view import _layer_type, _NO_TYPE_LABEL

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

lv = app.layers_view
layers = app.project.layers
assert len(layers) == 377, len(layers)

# --- _layer_type: the real segment after a real layer's last "." ---
assert _layer_type("Activ.pin") == "pin"
assert _layer_type("Substrate.drawing") == "drawing"
assert _layer_type("Cont.m2tm1") == "m2tm1"
assert _layer_type("NEWLAYER0") == _NO_TYPE_LABEL
print("PASS: _layer_type reads the real segment after a layer's last '.', with an honest fallback for none.")

# --- The Type selector is generated from the real, loaded project's
# own real layer names -- not a static, hardcoded list ---
real_types = sorted({_layer_type(l.name) for l in layers})
assert len(real_types) > 40, len(real_types)  # the real IHP deck has 51 distinct real types
listbox_items = list(lv.type_listbox.get(0, tk.END))
assert listbox_items == real_types, (listbox_items, real_types)
print(f"PASS: the Type selector lists exactly the {len(real_types)} real, distinct types found in this real project.")

# --- Every real type starts selected, so an untouched Type filter
# never hides real data (matches total tree row count) ---
assert lv._selected_types() == set(real_types)
assert len(lv.tree.get_children()) == 377
print("PASS: every real type starts selected -- the untouched Type filter shows all 377 real layers.")

# --- Deselecting all but one real type filters the tree down to
# exactly the real layers of that type ---
lv.type_listbox.selection_clear(0, tk.END)
pin_index = real_types.index("pin")
lv.type_listbox.selection_set(pin_index)
lv.refresh()
root.update()
real_pin_count = sum(1 for l in layers if _layer_type(l.name) == "pin")
assert real_pin_count == 24, real_pin_count  # confirmed against the real deck
assert len(lv.tree.get_children()) == real_pin_count, len(lv.tree.get_children())
assert all(lv.tree.set(iid, "name").endswith(".pin") for iid in lv.tree.get_children())
print(f"PASS: selecting only 'pin' filters the real tree down to exactly the {real_pin_count} real .pin layers.")

# --- Name search and Type selection combine (AND), not override each
# other ---
lv.filter_var.set("Activ")
root.update()
real_activ_pin_count = sum(1 for l in layers if _layer_type(l.name) == "pin" and "activ" in l.name.lower())
assert len(lv.tree.get_children()) == real_activ_pin_count, len(lv.tree.get_children())
assert real_activ_pin_count > 0
print(f"PASS: Name search ('Activ') and Type selection ('pin') combine, not override each other ({real_activ_pin_count} rows).")

# --- Deselecting every real type shows zero rows -- an honest, real
# empty result, not a silent fallback to "show everything" ---
lv.filter_var.set("")
lv.type_listbox.selection_clear(0, tk.END)
lv.refresh()
root.update()
assert len(lv.tree.get_children()) == 0
assert lv.current_layer is None
print("PASS: deselecting every real type honestly shows zero rows, not a silent fallback.")

# --- Re-selecting "Reset" (select everything again) restores the full,
# real, unfiltered view ---
for i in range(len(real_types)):
    lv.type_listbox.selection_set(i)
lv.refresh()
root.update()
assert len(lv.tree.get_children()) == 377
print("PASS: re-selecting every real type restores the full, real 377-layer view.")

# --- The Name field's own free-text filter no longer false-matches on
# 'purpose'/'status' (e.g. every real layer's purpose defaults to
# "drawing", which used to make searching "drawing" match everything,
# not just layers with "drawing" in their real name) ---
lv.type_listbox.selection_clear(0, tk.END)
for i in range(len(real_types)):
    lv.type_listbox.selection_set(i)
lv.filter_var.set("placeholder")  # every real layer's status, not part of any real name
lv.refresh()
root.update()
assert len(lv.tree.get_children()) == 0, len(lv.tree.get_children())
lv.filter_var.set("")
root.update()
print("PASS: the Name filter searches real layer names only, not the project-only purpose/status fields.")

# --- A brand-new layer's own real type (no dot yet) is a new, real
# entry in the Type selector, and starts selected/visible ---
lv._new_layer()
root.update()
assert _NO_TYPE_LABEL in list(lv.type_listbox.get(0, tk.END))
assert _NO_TYPE_LABEL in lv._selected_types()
assert lv.current_layer is not None and lv.current_layer.name.startswith("NEWLAYER")
print(f"PASS: a brand-new, dot-less layer adds a new, real '{_NO_TYPE_LABEL}' Type entry, selected by default.")

root.destroy()
print("ALL LAYERS TYPE FILTER TESTS PASS")

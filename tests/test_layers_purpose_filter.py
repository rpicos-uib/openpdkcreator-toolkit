import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator.pdklib import layers as layers_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

# --- purpose_from_name: the real segment after a real layer's last "." ---
assert layers_mod.purpose_from_name("Activ.pin") == "pin"
assert layers_mod.purpose_from_name("Substrate.drawing") == "drawing"
assert layers_mod.purpose_from_name("Cont.m2tm1") == "m2tm1"
assert layers_mod.purpose_from_name("NEWLAYER0") == "drawing"  # honest fallback, matches the Layer dataclass default
print("PASS: purpose_from_name reads the real segment after a layer's last '.', with an honest fallback for none.")

# --- import_layers now sets a real, derived purpose per layer -- not
# a fixed "drawing" for every one of them ---
lyp_path = layers_mod.find_lyp(PDK_ROOT)
imported = layers_mod.import_layers(PDK_ROOT, lyp_path)
assert len(imported) == 377, len(imported)
real_purposes = {l.purpose for l in imported}
assert len(real_purposes) > 40, len(real_purposes)  # the real IHP deck has 51 distinct real values
substrate_drawing = next(l for l in imported if l.name == "Substrate.drawing")
assert substrate_drawing.purpose == "drawing"
activ_pin = next(l for l in imported if l.name == "Activ.pin")
assert activ_pin.purpose == "pin"
print(f"PASS: import_layers derives {len(real_purposes)} distinct, real purpose values from real layer names.")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

lv = app.layers_view
layers = app.project.layers
assert len(layers) == 377, len(layers)

# --- The Purpose selector is generated from the real, loaded
# project's own real layer purposes -- not a static, hardcoded list ---
real_purposes_sorted = sorted({l.purpose for l in layers})
listbox_items = list(lv.purpose_listbox.get(0, tk.END))
assert listbox_items == real_purposes_sorted, (listbox_items, real_purposes_sorted)
print(f"PASS: the Purpose selector lists exactly the {len(real_purposes_sorted)} real, distinct purposes in this real project.")

# --- The Purpose combobox in the edit form is real, per-project, and
# freely editable (not a closed, static 6-value enum anymore) ---
assert str(lv.purpose_combo.cget("state")) == "normal"
assert set(lv.purpose_combo.cget("values")) == set(real_purposes_sorted)
print("PASS: the Purpose combobox in the edit form is editable and suggests the real, current per-project values.")

# --- Every real purpose starts selected, so an untouched Purpose
# filter never hides real data (matches total tree row count) ---
assert lv._selected_purposes() == set(real_purposes_sorted)
assert len(lv.tree.get_children()) == 377
print("PASS: every real purpose starts selected -- the untouched Purpose filter shows all 377 real layers.")

# --- Deselecting all but one real purpose filters the tree down to
# exactly the real layers of that purpose ---
lv.purpose_listbox.selection_clear(0, tk.END)
pin_index = real_purposes_sorted.index("pin")
lv.purpose_listbox.selection_set(pin_index)
lv.refresh()
root.update()
real_pin_count = sum(1 for l in layers if l.purpose == "pin")
assert real_pin_count == 24, real_pin_count  # confirmed against the real deck
assert len(lv.tree.get_children()) == real_pin_count, len(lv.tree.get_children())
assert all(lv.tree.set(iid, "name").endswith(".pin") for iid in lv.tree.get_children())
print(f"PASS: selecting only 'pin' filters the real tree down to exactly the {real_pin_count} real .pin layers.")

# --- Name search and Purpose selection combine (AND), not override
# each other ---
lv.filter_var.set("Activ")
root.update()
real_activ_pin_count = sum(1 for l in layers if l.purpose == "pin" and "activ" in l.name.lower())
assert len(lv.tree.get_children()) == real_activ_pin_count, len(lv.tree.get_children())
assert real_activ_pin_count > 0
print(f"PASS: Name search ('Activ') and Purpose selection ('pin') combine, not override each other ({real_activ_pin_count} rows).")

# --- Deselecting every real purpose shows zero rows -- an honest, real
# empty result, not a silent fallback to "show everything" ---
lv.filter_var.set("")
lv.purpose_listbox.selection_clear(0, tk.END)
lv.refresh()
root.update()
assert len(lv.tree.get_children()) == 0
assert lv.current_layer is None
print("PASS: deselecting every real purpose honestly shows zero rows, not a silent fallback.")

# --- Re-selecting everything restores the full, real, unfiltered view ---
for i in range(len(real_purposes_sorted)):
    lv.purpose_listbox.selection_set(i)
lv.refresh()
root.update()
assert len(lv.tree.get_children()) == 377
print("PASS: re-selecting every real purpose restores the full, real 377-layer view.")

# --- Editing a real layer's Purpose in the form (free-typed, not
# picked from a closed dropdown) live-commits and the Purpose selector
# picks up the new, real value ---
activ_pin_gui = next(l for l in layers if l.name == "Activ.pin")
lv.tree.selection_set(lv._iid(activ_pin_gui))
root.update()
lv.vars["purpose"].set("my_custom_purpose")
root.update()
assert activ_pin_gui.purpose == "my_custom_purpose"
assert "my_custom_purpose" in list(lv.purpose_listbox.get(0, tk.END))
assert "my_custom_purpose" in lv._selected_purposes()
print("PASS: free-typing a new Purpose in the edit form live-commits and adds/selects it in the Purpose selector.")
activ_pin_gui.purpose = "pin"  # restore for the assertions below
lv.refresh()
root.update()

# --- The Name field's own free-text filter still searches layer names
# only, not the project-only status field ---
lv.purpose_listbox.selection_clear(0, tk.END)
for i in range(lv.purpose_listbox.size()):
    lv.purpose_listbox.selection_set(i)
lv.filter_var.set("placeholder")  # every real layer's status, not part of any real name
lv.refresh()
root.update()
assert len(lv.tree.get_children()) == 0, len(lv.tree.get_children())
lv.filter_var.set("")
root.update()
print("PASS: the Name filter searches real layer names only, not the project-only status field.")

# --- A brand-new layer's own real purpose (no dot yet, dataclass
# default "drawing") is already a known, selected entry -- no new,
# surprising pseudo-value needed ---
lv._new_layer()
root.update()
assert lv.current_layer is not None and lv.current_layer.name.startswith("NEWLAYER")
assert lv.current_layer.purpose == "drawing"
assert "drawing" in lv._selected_purposes()
print("PASS: a brand-new, dot-less layer defaults to the real 'drawing' purpose, already selected.")

root.destroy()
print("ALL LAYERS PURPOSE FILTER TESTS PASS")

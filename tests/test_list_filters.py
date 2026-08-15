import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

# --- Layers ---
lv = app.layers_view
total_layers = len(lv.tree.get_children())
assert total_layers > 0
sample_name = lv.app.project.sorted_layers()[0].name
lv.filter_var.set(sample_name[:3])
root.update()
filtered = len(lv.tree.get_children())
assert 0 < filtered <= total_layers, (filtered, total_layers)
assert all(sample_name[:3].lower() in lv.tree.set(iid, "name").lower() for iid in lv.tree.get_children())
lv.filter_var.set("ZZZ_NO_SUCH_LAYER_XYZ")
root.update()
assert len(lv.tree.get_children()) == 0
assert lv.current_layer is None
lv.filter_var.set("")
root.update()
assert len(lv.tree.get_children()) == total_layers
print(f"PASS: Layers filter ({total_layers} total, {filtered} matched '{sample_name[:3]}')")

# New Layer while filtered must still show up (filter auto-clears)
lv.filter_var.set("ZZZ_NO_SUCH_LAYER_XYZ")
root.update()
lv._new_layer()
root.update()
assert lv.filter_var.get() == ""
assert lv.current_layer is not None and lv.current_layer.name.startswith("NEWLAYER")
print("PASS: New Layer clears an active filter so the new layer is visible")
lv.app.project.layers.remove(lv.current_layer)
lv.refresh()

# --- DRC Rules ---
rv = app.rules_view
total_rules = len(rv.tree.get_children())
assert total_rules > 0
sample_rule = rv.app.project.design_rules[0]
rv.filter_var.set(sample_rule.rule_id[:4])
root.update()
filtered_rules = len(rv.tree.get_children())
assert 0 < filtered_rules <= total_rules
rv.filter_var.set("ZZZ_NO_SUCH_RULE_XYZ")
root.update()
assert len(rv.tree.get_children()) == 0
assert rv.current_rule is None
rv.filter_var.set("")
root.update()
assert len(rv.tree.get_children()) == total_rules
print(f"PASS: DRC Rules filter ({total_rules} total, {filtered_rules} matched '{sample_rule.rule_id[:4]}')")

rv.filter_var.set("ZZZ_NO_SUCH_RULE_XYZ")
root.update()
rv._new_rule()
root.update()
assert rv.filter_var.get() == ""
assert rv.current_rule is not None and rv.current_rule.rule_id.startswith("NEW.RULE.")
print("PASS: New Rule clears an active filter so the new rule is visible")
rv.app.project.design_rules.remove(rv.current_rule)
rv.refresh()

# --- Magic Types ---
mtv = app.magic_tech_view
total_types = len(mtv.types_tree.get_children())
assert total_types > 0
sample_type = mtv._current_tech().types[0]
mtv.type_filter_var.set(sample_type.canonical_name[:3])
root.update()
filtered_types = len(mtv.types_tree.get_children())
assert 0 < filtered_types <= total_types
mtv.type_filter_var.set("ZZZ_NO_SUCH_TYPE_XYZ")
root.update()
assert len(mtv.types_tree.get_children()) == 0
assert mtv.current_type is None
mtv.type_filter_var.set("")
root.update()
assert len(mtv.types_tree.get_children()) == total_types
print(f"PASS: Magic Types filter ({total_types} total, {filtered_types} matched '{sample_type.canonical_name[:3]}')")

mtv.type_filter_var.set("ZZZ_NO_SUCH_TYPE_XYZ")
root.update()
mtv._new_type()
root.update()
assert mtv.type_filter_var.get() == ""
assert mtv.current_type is not None and mtv.current_type.canonical_name.startswith("newtype")
print("PASS: New Type clears an active filter so the new type is visible")
mtv._current_tech().types.remove(mtv.current_type)
mtv._refresh_types()

# --- LEF Macros ---
lefv = app.lef_view
lefv.file_var.set("libs.ref/sg13g2_stdcell/lef/sg13g2_stdcell.lef")
lefv._refresh_all()
root.update()
total_macros = len(lefv.macros_tree.get_children())
assert total_macros > 0
sample_macro = lefv.current.macros[0].name
lefv._macro_filter_query = sample_macro[:4].lower()
lefv._refresh_all()
root.update()
filtered_macros = len(lefv.macros_tree.get_children())
assert 0 < filtered_macros <= total_macros
lefv._macro_filter_query = "zzz_no_such_macro_xyz"
lefv._refresh_all()
root.update()
assert len(lefv.macros_tree.get_children()) == 0
assert lefv.current_macro is None
lefv._macro_filter_query = ""
lefv._refresh_all()
root.update()
assert len(lefv.macros_tree.get_children()) == total_macros
print(f"PASS: LEF Macros filter ({total_macros} total, {filtered_macros} matched '{sample_macro[:4]}')")

# --- By Cell ---
chv = app.cell_hub_view
chv.family_var.set("sg13g2_stdcell")
chv._refresh_cells()
root.update()
total_cells = len(chv.cells_tree.get_children())
assert total_cells > 0
sample_cell = chv.cells_tree.get_children()[0]
chv._filter_query = sample_cell[:6].lower()
chv._refresh_cells()
root.update()
filtered_cells = len(chv.cells_tree.get_children())
assert 0 < filtered_cells <= total_cells
chv._filter_query = "zzz_no_such_cell_xyz"
chv._refresh_cells()
root.update()
assert len(chv.cells_tree.get_children()) == 0
assert chv.current_cell is None
chv._filter_query = ""
chv._refresh_cells()
root.update()
assert len(chv.cells_tree.get_children()) == total_cells
print(f"PASS: By Cell filter ({total_cells} total, {filtered_cells} matched '{sample_cell[:6]}')")

root.destroy()
print("ALL LIST-FILTER TESTS PASSED")

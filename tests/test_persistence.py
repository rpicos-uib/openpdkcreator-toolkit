import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator import project_io
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

save_path = project_io.save_path_for(PDK_ROOT)
if save_path.is_file():
    save_path.unlink()
    print("Cleared pre-existing save file.")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

# --- Edit 1: a DRC rule's description (via the real form, like the
# LEF pin edit below, so commit-on-switch is genuinely exercised) ---
rule = app.project.design_rules[0]
rule_id = rule.rule_id
app.rules_view.tree.selection_set(app.rules_view._iid(rule))
app.rules_view._on_select()
root.update()
original_desc = app.rules_view.vars["description"].get()
app.rules_view.vars["description"].set("EDITED-BY-TEST")
root.update()
print(f"Edited rule {rule_id!r}: {original_desc!r} -> {rule.description!r}")
assert rule.description == "EDITED-BY-TEST", "trace commit did not fire for DRC rule"

# --- Edit 2: a Magic Type's canonical_name (via the real form) ---
tech_name = sorted(app.magic_tech_view.technologies)[0]
app.magic_tech_view.tech_var.set(tech_name)
app.magic_tech_view._refresh_all()
root.update()
tech = app.magic_tech_view.technologies[tech_name]
type_entry = tech.types[0]
app.magic_tech_view.types_tree.selection_set(app.magic_tech_view._type_iid(type_entry))
app.magic_tech_view._on_type_select()
root.update()
original_type_name = app.magic_tech_view.type_vars["name"].get()
app.magic_tech_view.type_vars["name"].set("edited_type_name")
root.update()
print(f"Edited type in {tech_name!r}: {original_type_name!r} -> {type_entry.canonical_name!r}")
assert type_entry.canonical_name == "edited_type_name", "trace commit did not fire for Magic Type"

# --- Edit 3: a LEF pin's direction (via the actual form, driven, to
# exercise the real trace-commit path, not just direct attribute
# mutation) ---
app.lef_view.file_var.set(sorted(app.lef_view.lef_files)[0])
app.lef_view._refresh_all()
root.update()
lef_relpath = app.lef_view.file_var.get()
macro = app.lef_view.current.macros[0]
app.lef_view.macros_tree.selection_set(macro.name)
app.lef_view._on_macro_select()
root.update()
pin = app.lef_view.pin_editor.current_pin
assert pin is not None, "no pin loaded into form"
original_direction = pin.direction
new_direction = "OUTPUT" if original_direction != "OUTPUT" else "INPUT"
app.lef_view.pin_editor.pin_vars["direction"].set(new_direction)
root.update()
print(f"Edited pin {pin.name!r} in {macro.name!r} ({lef_relpath}): {original_direction!r} -> {pin.direction!r}")
assert pin.direction == new_direction, "trace commit did not fire"

# --- Save ---
app._save_project()
root.update()
print(f"Save status: {app.status.get()}")
assert save_path.is_file(), "save file was not created"
print(f"Save file size: {save_path.stat().st_size} bytes")

root.destroy()

# --- Simulate a relaunch: fresh App instance, same pdk_root ---
root2 = tk.Tk()
app2 = App(root2, PDK_ROOT)
root2.update()
print(f"Reload status: {app2.status.get()}")

rule2 = next(r for r in app2.project.design_rules if r.rule_id == rule_id)
assert rule2.description == "EDITED-BY-TEST", f"DRC rule edit lost: {rule2.description!r}"
print("PASS: DRC rule edit survived relaunch.")

tech2 = app2.magic_tech_view.technologies[tech_name]
names2 = [t.canonical_name for t in tech2.types]
assert "edited_type_name" in names2, f"Magic Type edit lost: {names2[:5]}..."
print("PASS: Magic Type edit survived relaunch.")

app2.lef_view.file_var.set(lef_relpath)
app2.lef_view._refresh_all()
root2.update()
macro2 = next(m for m in app2.lef_view.current.macros if m.name == macro.name)
pin2 = next(p for p in macro2.pins if p.name == pin.name)
assert pin2.direction == new_direction, f"LEF pin edit lost: {pin2.direction!r}"
print("PASS: LEF pin edit survived relaunch.")

root2.destroy()
print("ALL PASS")

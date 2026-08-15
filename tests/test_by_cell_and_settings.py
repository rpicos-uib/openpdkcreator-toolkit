import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator import project_io
from openpdkcreator.gui.app import App
from openpdkcreator.gui.settings_view import DEFAULT_PROJECT_NAME

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
save_path = project_io.save_path_for(PDK_ROOT)
if save_path.is_file():
    save_path.unlink()
    print("Cleared pre-existing save file.")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

# --- Settings tab: defaults ---
assert app.project_name == DEFAULT_PROJECT_NAME
assert app.settings_view.project_name_var.get() == DEFAULT_PROJECT_NAME
assert app.settings_view.pdk_name_var.get() == PDK_ROOT.name
assert app.settings_view.pdk_location_var.get() == str(PDK_ROOT)
project_dir = app.settings_view.project_dir_var.get()
assert project_dir != str(PDK_ROOT), "Project directory must differ from the PDK's own location"
print(f"Settings defaults OK. project dir={project_dir!r} pdk location={str(PDK_ROOT)!r} (different: {project_dir != str(PDK_ROOT)})")
print(f"Upstream: {app.settings_view.pdk_upstream_var.get()}")

# --- Edit project name via the real Settings form ---
app.settings_view.project_name_var.set("My Custom SG13G2 Fork")
root.update()
assert app.project_name == "My Custom SG13G2 Fork"
assert "My Custom SG13G2 Fork" in root.title()
print(f"Title after rename: {root.title()!r}")

# --- By Cell tab: select a family/cell with a real LEF macro, edit a pin ---
app.cell_hub_view.family_var.set("sg13g2_stdcell")
app.cell_hub_view._refresh_cells()
root.update()
cell_names = list(app.cell_hub_view.cells_tree.get_children())
assert cell_names, "no cells listed for sg13g2_stdcell"
target_name = "sg13g2_a21o_1" if "sg13g2_a21o_1" in cell_names else cell_names[0]
app.cell_hub_view.cells_tree.selection_set(target_name)
app.cell_hub_view._on_cell_select()
root.update()
cv = app.cell_hub_view.current_cell
assert cv is not None and cv.lef_macro is not None, "selected cell has no LEF macro"
pin_editor = app.cell_hub_view.pin_editor
assert pin_editor.macro is cv.lef_macro
pin = pin_editor.current_pin
assert pin is not None
original_use = pin.use
new_use = "POWER" if original_use != "POWER" else "GROUND"
pin_editor.pin_vars["use"].set(new_use)
root.update()
assert pin.use == new_use, "trace commit did not fire in By Cell's pin editor"
print(f"Edited {target_name}'s pin {pin.name!r} via By Cell tab: {original_use!r} -> {pin.use!r}")

# --- Cross-tab identity check: same edit visible on the LEF tab, same object ---
lef_relpath = str(cv.lef_source.relative_to(PDK_ROOT))
app.lef_view.file_var.set(lef_relpath)
app.lef_view._refresh_all()
root.update()
app.lef_view.macros_tree.selection_set(target_name)
app.lef_view._on_macro_select()
root.update()
lef_tab_pin = app.lef_view.pin_editor.current_pin
assert lef_tab_pin is pin, "By Cell tab and LEF tab parsed two different LefPin objects for the same macro!"
assert lef_tab_pin.use == new_use
print("PASS: By Cell tab and LEF tab share the exact same in-memory LefMacro/LefPin object.")

# --- Save everything, then simulate a relaunch ---
app._save_project()
root.update()
print(f"Save status: {app.status.get()}")
assert save_path.is_file()

root.destroy()

root2 = tk.Tk()
app2 = App(root2, PDK_ROOT)
root2.update()
print(f"Reload status: {app2.status.get()}")

assert app2.project_name == "My Custom SG13G2 Fork", f"project name lost: {app2.project_name!r}"
assert "My Custom SG13G2 Fork" in root2.title()
print("PASS: project name survived relaunch, title updated.")

app2.cell_hub_view.family_var.set("sg13g2_stdcell")
app2.cell_hub_view._refresh_cells()
root2.update()
app2.cell_hub_view.cells_tree.selection_set(target_name)
app2.cell_hub_view._on_cell_select()
root2.update()
cv2 = app2.cell_hub_view.current_cell
pin2 = next(p for p in cv2.lef_macro.pins if p.name == pin.name)
assert pin2.use == new_use, f"By Cell pin edit lost: {pin2.use!r}"
print("PASS: pin edit made via By Cell tab survived relaunch.")

root2.destroy()
print("ALL PASS")

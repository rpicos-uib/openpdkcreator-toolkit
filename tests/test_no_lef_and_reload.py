import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator import project_io
from openpdkcreator.gui.app import App
from openpdkcreator.gui.settings_view import DEFAULT_PROJECT_NAME

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

# A macro-less internal sub-cell: turn on "show all" for sg13g2_sram,
# pick a cell without a real LEF macro, confirm the placeholder shows
# instead of the pin editor (and doesn't crash).
app.cell_hub_view.family_var.set("sg13g2_sram")
app.cell_hub_view.show_all_var.set(True)
app.cell_hub_view._refresh_cells()
root.update()
no_lef_cell = next(
    (name for name in app.cell_hub_view.cells_tree.get_children()
     if app.cell_hub_view.cell_index[name].lef_macro is None),
    None,
)
assert no_lef_cell is not None, "expected at least one macro-less internal sub-cell in sg13g2_sram"
app.cell_hub_view.cells_tree.selection_set(no_lef_cell)
app.cell_hub_view._on_cell_select()
root.update()
assert app.cell_hub_view.pin_editor.macro is None
# The tab isn't the actively-selected Notebook page during this driven
# test, so winfo_ismapped() would be False for everything in it
# regardless -- check via grid_info() (was grid() actually called)
# instead, which is unaffected by notebook tab visibility.
assert not app.cell_hub_view.pin_editor.grid_info(), "pin editor should be un-gridded for a macro-less cell"
assert app.cell_hub_view.no_lef_label.grid_info(), "placeholder label should be gridded instead"
print(f"PASS: macro-less cell {no_lef_cell!r} shows the placeholder, not a broken pin editor.")

# Now edit something, then explicitly reload from real files, and
# confirm project name/edits/save file are all discarded together.
app.settings_view.project_name_var.set("Temp Name")
root.update()
app.rules_view.vars["description"].set("WILL BE DISCARDED")
root.update()
app._save_project()
root.update()
save_path = project_io.save_path_for(PDK_ROOT)
assert save_path.is_file()

app._reload_from_real_files()
root.update()
assert not save_path.is_file(), "save file should be gone after Reload from Real Files"
assert app.project_name == DEFAULT_PROJECT_NAME, f"project name not reset: {app.project_name!r}"
assert app.settings_view.project_name_var.get() == DEFAULT_PROJECT_NAME
assert "WILL BE DISCARDED" not in [r.description for r in app.project.design_rules]
print("PASS: Reload from Real Files reset project name, DRC edits, and deleted the save file.")

root.destroy()
print("ALL PASS")

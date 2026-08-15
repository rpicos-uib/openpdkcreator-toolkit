import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
PROJECT_ROOT = Path("/foss/designs")

# --- Self-contained fixture: this test needs exactly one real user
# model ("my_custom_inverter") in user_models/, not gitignored real
# project content -- write it fresh here rather than depending on
# whatever a previous, unrelated session may have left behind.
fixture_path = PROJECT_ROOT / "user_models" / "veriloga" / "my_custom_inverter.va"
fixture_path.parent.mkdir(parents=True, exist_ok=True)
fixture_path.write_text(
    "module my_custom_inverter(A, Y, VDD, VSS);\n"
    "input A;\n"
    "output Y;\n"
    "inout VDD;\n"
    "inout VSS;\n"
    "endmodule\n"
)
links_path = PROJECT_ROOT / "user_models" / "links.yaml"
if links_path.is_file():
    links_path.unlink()

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

umv = app.user_models_view
umv.refresh()
root.update()
rows = umv.tree.get_children()
print("user models tree rows:", rows)
assert len(rows) == 1, rows
iid = rows[0]
values = umv.tree.item(iid)["values"]
print("row values:", values)
assert values[2] == "my_custom_inverter"
assert values[4] == "(auto: my_custom_inverter)"

# Select the row, save an explicit link, verify persistence + refresh.
umv.tree.selection_set(iid)
umv._on_select()
umv.cell_name_var.set("sg13g2_inv_1")
umv._save_link()
root.update()

links_path = Path("/foss/designs/user_models/links.yaml")
assert links_path.is_file(), "links.yaml not written"
print("links.yaml:", links_path.read_text())

rows2 = umv.tree.get_children()
new_iid = rows2[0]
values2 = umv.tree.item(new_iid)["values"]
print("row values after save:", values2)
assert values2[4] == "sg13g2_inv_1", values2

# Now check By Cell tab reflects it: my_custom_inverter no longer its own cell,
# sg13g2_inv_1 (a real cell) now shows the user model.
chv = app.cell_hub_view
chv.family_var.set("sg13g2_stdcell")
chv._refresh_cells()
root.update()
cell_names = {chv.cells_tree.item(iid)["values"][0] for iid in chv.cells_tree.get_children()}
assert "my_custom_inverter" not in cell_names
assert "sg13g2_inv_1" in cell_names
print("PASS: my_custom_inverter absorbed into real cell sg13g2_inv_1 in By Cell tree.")

# Select sg13g2_inv_1 and verify the User Models listbox populates, and the
# "user" column shows a count.
for iid in chv.cells_tree.get_children():
    if chv.cells_tree.item(iid)["values"][0] == "sg13g2_inv_1":
        row_values = chv.cells_tree.item(iid)["values"]
        print("sg13g2_inv_1 row:", row_values)
        chv.cells_tree.selection_set(iid)
        chv._on_cell_select()
        break
root.update()
listbox_items = chv.user_models_list.get(0, "end")
print("user_models_list contents:", listbox_items)
assert len(listbox_items) == 1
assert "my_custom_inverter" in listbox_items[0]

# Exercise the double-click view handler (was the missing method) -- the
# dialog is modal (wait_window), so schedule its own close asynchronously
# before invoking the handler that opens it.
chv.user_models_list.selection_set(0)


def _close_toplevels():
    stack = list(root.winfo_children())
    while stack:
        w = stack.pop()
        if isinstance(w, tk.Toplevel):
            w.destroy()
        else:
            stack.extend(w.winfo_children())


root.after(200, _close_toplevels)
chv._view_selected_user_model()
root.update()
print("PASS: _view_selected_user_model ran without error.")

# Clear the link, verify it falls back to no auto-match (wholly-new cell again).
umv.refresh()
root.update()
rows3 = umv.tree.get_children()
umv.tree.selection_set(rows3[0])
umv._on_select()
umv._clear_link()
root.update()
assert not links_path.is_file() or links_path.read_text().strip() in ("[]", ""), links_path.read_text()
print("PASS: Clear Link removed the explicit link.")

root.destroy()
fixture_path.unlink(missing_ok=True)
if links_path.is_file():
    links_path.unlink()
print("ALL PASS")

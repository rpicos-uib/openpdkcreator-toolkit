import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path
from unittest import mock

from openpdkcreator.gui.app import App
from openpdkcreator.pdklib import lef as lef_mod

PDK_ROOT = Path("/tmp/empty_pdk2")
import shutil
shutil.rmtree(PDK_ROOT, ignore_errors=True)
(PDK_ROOT / "libs.tech").mkdir(parents=True)
(PDK_ROOT / "libs.ref").mkdir(parents=True)

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

# --- Layers: click "New .lyp File..." for real, via App._new_lyp_file ---
with mock.patch("openpdkcreator.gui.app.simpledialog.askstring", return_value="mem"):
    app._new_lyp_file()
root.update()
assert app.lyp_path == PDK_ROOT / "libs.tech" / "klayout" / "tech" / "mem.lyp"
assert app.lyp_path.is_file()
print("PASS: New .lyp File... button creates + loads a real .lyp.")

# --- Magic Tech: click "New .tech File..." for real ---
with mock.patch("openpdkcreator.gui.magic_tech_view.simpledialog.askstring", return_value="mem"):
    app.magic_tech_view._new_tech_file()
root.update()
assert "mem" in app.magic_tech_view.technologies
assert app.magic_tech_view.tech_var.get() == "mem"
print("PASS: New .tech File... button creates + loads + selects a real technology.")

# --- LEF: type a path into the (now editable) combobox, click Create File ---
app.lef_view.file_var.set("libs.ref/mem_cells/lef/mem.lef")
app.lef_view._update_action_button()
assert str(app.lef_view.action_button.cget("text")) == "Create File"
app.lef_view._on_action()
root.update()
lef_path = PDK_ROOT / "libs.ref" / "mem_cells" / "lef" / "mem.lef"
assert lef_path.is_file()
assert str(lef_path.relative_to(PDK_ROOT)) in app.lef_view.lef_files
print("PASS: LEF tab's editable combobox + Create File action creates + loads a real .lef.")

# Now the action button should read "Edit File" for the same, now-existing path
app.lef_view._update_action_button()
assert str(app.lef_view.action_button.cget("text")) == "Edit File"
print("PASS: action button flips to Edit File once the typed path exists.")

# --- Duplicate creation raises FileExistsError, surfaced (not crashed) via messagebox ---
with mock.patch("openpdkcreator.gui.file_picker_utils.messagebox.showerror") as mock_err:
    app.lef_view.file_var.set("libs.ref/mem_cells/lef/mem.lef")
    app.lef_view._update_action_button()
    # existing file -> action button is Edit File, opens view_file_dialog instead; test the raw create_fn guard directly
    try:
        lef_mod.create_new_lef_file(lef_path)
        raised = False
    except FileExistsError:
        raised = True
    assert raised
print("PASS: create_new_lef_file refuses to overwrite an existing file.")

root.destroy()
print("ALL SKELETON BUTTON TESTS PASS")

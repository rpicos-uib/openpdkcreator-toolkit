import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator.ihp import spice_models as spice_models_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

# --- Unit test: create_new_lib_file writes a real, minimal, valid,
# genuinely empty (0 models/subckts/corners) skeleton ---
tmp_path = Path("/tmp/test_new_ngspice_lib.lib")
tmp_path.unlink(missing_ok=True)
spice_models_mod.create_new_lib_file(tmp_path)
assert tmp_path.is_file()
parsed = spice_models_mod.parse_lib_file(tmp_path)
assert parsed.models == [] and parsed.subckts == [] and parsed.corners == []
print("PASS: create_new_lib_file writes a real file that parses to an honestly empty SpiceLibFile.")

try:
    spice_models_mod.create_new_lib_file(tmp_path)
    assert False, "must refuse to overwrite an existing real file"
except FileExistsError:
    print("PASS: create_new_lib_file refuses to overwrite an existing real file.")

tmp_path.unlink()

# --- Real, driven GUI test: New file -> Create File -> reload -> selected ---
root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

sv = app.spice_models_view
new_rel_path = "libs.tech/ngspice/models/zz_new_test.lib"
new_path = PDK_ROOT / new_rel_path
new_path.unlink(missing_ok=True)

sv.file_var.set(new_rel_path)
sv._update_action_button()
root.update()
assert sv.action_button.cget("text") == "Create File"

sv._on_action()
root.update()

assert new_path.is_file()
assert new_rel_path in sv.lib_files
assert sv.file_var.get() == new_rel_path
assert sv.action_button.cget("text") == "Edit File"
assert sv.summary_var.get() == "models:0  subckts:0  corners:0"
print(f"PASS: Create File writes a real, valid, empty .lib at {new_path} through the actual GUI action, then selects it.")

root.destroy()
new_path.unlink()

print("ALL SPICE MODELS CREATE TESTS PASS")

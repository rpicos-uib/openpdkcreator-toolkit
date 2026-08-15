import sys
sys.path.insert(0, "/foss/designs")
import shutil
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator import project_io

# A genuinely empty, throwaway pdk_root (same precedent as
# test_skeletons.py/test_pdk_wizard_empty.py) -- real Layers
# persistence needs to survive exactly this from-scratch scenario,
# not just an already-real, downloaded deck.
PDK_ROOT = Path("/tmp/test_layers_persistence_pdk")
shutil.rmtree(PDK_ROOT, ignore_errors=True)
PDK_ROOT.mkdir(parents=True)
save_path = project_io.save_path_for(PDK_ROOT)
save_path.unlink(missing_ok=True)

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

# --- Create a real .lyp, add real layers, matching the openMemristorPDK
# session that first found this gap ---
lv = app.layers_view
from openpdkcreator.ihp import layers as layers_mod
lyp_path = PDK_ROOT / "libs.tech" / "klayout" / "tech" / "test.lyp"
layers_mod.create_new_lyp_file(lyp_path)
app.load()
root.update()
assert app.lyp_path == lyp_path

lv._new_layer()
root.update()
# Real fields go through the same StringVars a real Entry widget edits
# (not a direct dataclass mutation) -- these live-commit on every
# keystroke via _on_field_changed, the real behavior this test needs
# to exercise, not bypass.
lv.vars["name"].set("BE")
lv.vars["gds_layer"].set("30")
lv.vars["gds_datatype"].set("0")
root.update()
assert [l.name for l in app.project.layers] == ["BE"], app.project.layers

# --- Save Edits, confirm layers actually landed in saves/*.yaml ---
app._save_project()
root.update()
saved = project_io.load_state(PDK_ROOT)
assert saved is not None
key = str(lyp_path.relative_to(PDK_ROOT))
assert key in saved.layers, saved.layers
assert [l.name for l in saved.layers[key]] == ["BE"]
assert saved.layers[key][0].gds_layer == 30
print("PASS: Save Edits persists the real, in-progress layer list to saves/*.yaml.")

# --- Fresh app instance (simulates a real relaunch) -- restored, not lost ---
root.destroy()
root2 = tk.Tk()
app2 = App(root2, PDK_ROOT)
root2.update()
assert [l.name for l in app2.project.layers] == ["BE"], app2.project.layers
assert app2.project.layers[0].gds_layer == 30
print("PASS: a fresh App() instance (simulating a real GUI relaunch) restores the real, saved layer list -- it no longer silently reverts to the empty real .lyp on disk.")

root2.destroy()

# --- cleanup ---
save_path.unlink(missing_ok=True)
shutil.rmtree(PDK_ROOT, ignore_errors=True)

print("ALL LAYERS PERSISTENCE TESTS PASS")

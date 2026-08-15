import sys
sys.path.insert(0, "/foss/designs")
import shutil
import tkinter as tk
from pathlib import Path

from openpdkcreator import export as export_mod
from openpdkcreator import project_io
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

if export_mod.EXPORT_ROOT.is_dir():
    shutil.rmtree(export_mod.EXPORT_ROOT)
save_path = project_io.save_path_for(PDK_ROOT)
if save_path.is_file():
    save_path.unlink()

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

rule = next(r for r in app.project.design_rules if r.rule_id == "Act.a")
app.rules_view.tree.selection_set(app.rules_view._iid(rule))
app.rules_view._on_select()
root.update()
app.rules_view.vars["value"].set("0.25")
root.update()
assert rule.value == 0.25, rule.value

app._export_drc_rules()
root.update()
print("Export status:", app.status.get())

import json
json_export = export_mod.export_path_for(PDK_ROOT, export_mod.drc_mod.find_json_config_path(app.drc_root))
exported = json.loads(json_export.read_text())
assert exported["drc_rules"]["Act_a"] == 0.25, exported["drc_rules"]["Act_a"]
print("PASS: editing a DRC rule's value via the real form and exporting patches the real JSON correctly.")

root.destroy()
print("ALL PASS")

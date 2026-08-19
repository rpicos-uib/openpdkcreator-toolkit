import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator import project_io
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
save_path = project_io.save_path_for(PDK_ROOT)
assert save_path.is_file(), "expected a save file from the previous test run"

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()
assert "restored saved edits" in app.status.get(), app.status.get()

# test_persistence.py always edits design_rules[0] -- currently real
# 'Ant.g' (pdklib/drc.py's own composite-check tracing resolves it as
# the first real rule in file-sort order, ahead of 'M1.a', once
# extraction was extended to trace real boolean-composed constructs
# too; was 'M1.a' before that).
rule = next(r for r in app.project.design_rules if r.rule_id == "Ant.g")
assert rule.description == "EDITED-BY-TEST"

app._reload_from_real_files()
root.update()
print("Reload status:", app.status.get())
assert not save_path.is_file(), "save file should have been deleted"
assert "restored saved edits" not in app.status.get()

rule2 = next(r for r in app.project.design_rules if r.rule_id == "Ant.g")
assert rule2.description != "EDITED-BY-TEST", f"edit survived a discard: {rule2.description!r}"
print("PASS: Reload from Real Files discarded the edit and the save file.")

root.destroy()
print("ALL PASS")

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

mtv = app.magic_tech_view
mtv.tech_var.set("ihp-sg13g2")
mtv._refresh_all()
root.update()

type_entry = next(t for t in mtv.technologies["ihp-sg13g2"].types if t.canonical_name == "nwell")
mtv.types_tree.selection_set(mtv._type_iid(type_entry))
mtv._on_type_select()
root.update()
mtv.type_vars["name"].set("nwell_renamed")
root.update()
assert type_entry.canonical_name == "nwell_renamed"

app._export_magic_types()
root.update()
print("Export status:", app.status.get())

from openpdkcreator.pdklib import magic_tech as mt
export_path = export_mod.export_path_for(PDK_ROOT, type_entry_source := mtv.technologies["ihp-sg13g2"].source_path)
reexported = mt.parse_tech_file(export_path)
assert any(t.canonical_name == "nwell_renamed" for t in reexported.types)
print("PASS: editing a Magic Type via the real form and exporting patches the real .tech file correctly.")

root.destroy()
print("ALL PASS")

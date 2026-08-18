import sys
sys.path.insert(0, "/foss/designs")
import tempfile
import tkinter as tk
from tkinter import ttk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator import export as export_mod
from openpdkcreator.pdklib import magic_tech as magic_tech_mod
from openpdkcreator.pdklib import reconcile as reconcile_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
CIFOUT_PATH = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2-cifout.tech"

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

mtv = app.magic_tech_view
assert "ihp-sg13g2-cifout" in mtv.technologies
assert mtv.technologies["ihp-sg13g2-cifout"].source_path == CIFOUT_PATH

mtv.tech_var.set("ihp-sg13g2-cifout")
mtv._refresh_all()
root.update()

print("cif layer rows:", len(mtv.cif_layers_editor.tree.get_children()))
assert len(mtv.cif_layers_editor.tree.get_children()) == 138

# --- Deliberately no New/Delete for this domain -- the buttons don't
# exist at all (allow_new_delete=False), not just disabled. ---
button_texts = [
    w.cget("text") for w in mtv.cif_layers_editor.winfo_children() if isinstance(w, ttk.Frame)
    for w in w.winfo_children() if isinstance(w, ttk.Button)
]
print("cif_layers_editor buttons:", button_texts)
assert not any("New" in t or "Delete" in t for t in button_texts)
print("PASS: CIF Layers has no New/Delete buttons -- edit-in-place only, by design.")

# --- A real name can appear on more than one row (DNWELL, built
# across two separate real 'layer DNWELL ...' blocks) -- confirms the
# flattened, one-row-per-real-calma-line design, not merged by name. ---
dnwell_entries = [e for e in mtv.cif_layers_editor.entries if e.name == "DNWELL"]
print("DNWELL rows:", dnwell_entries)
assert len(dnwell_entries) == 2
assert all(e.gds_layer == 32 and e.gds_datatype == 0 for e in dnwell_entries)

# --- Edit an existing mapping's own layer/datatype -- both real ints,
# via the gds_layer_text/gds_datatype_text properties. ---
mtv.cif_layers_editor.tree.selection_set(mtv.cif_layers_editor.tree.get_children()[0])
mtv.cif_layers_editor._on_select()
mtv.cif_layers_editor.field_vars["gds_layer_text"].set("555")
mtv.cif_layers_editor.field_vars["gds_datatype_text"].set("7")
root.update()
edited = mtv.cif_layers_editor.current_entry
assert edited.gds_layer == 555 and isinstance(edited.gds_layer, int)
assert edited.gds_datatype == 7 and isinstance(edited.gds_datatype, int)
row_values = mtv.cif_layers_editor.tree.item(mtv.cif_layers_editor.tree.get_children()[0])["values"]
# Tkinter's own Tcl-list round-trip returns a numeric-looking string as
# a real int, not the original string -- compared loosely here, real
# correctness already confirmed above via entry.gds_layer/gds_datatype
# themselves (real Python ints, not strings).
assert str(row_values[1]) == "555" and str(row_values[2]) == "7"
print("PASS: in-GUI edit of an existing CIF Layer mapping's own real layer/datatype.")

# -- Save Edits / relaunch persistence, keyed by 'ihp-sg13g2-cifout' --
app._save_project()
root.update()
edited_name = mtv.cif_layers_editor.entries[0].name

root.destroy()
root2 = tk.Tk()
app2 = App(root2, PDK_ROOT)
root2.update()
mtv2 = app2.magic_tech_view
mtv2.tech_var.set("ihp-sg13g2-cifout")
mtv2._refresh_all()
root2.update()

reloaded = mtv2.cif_layers_editor.entries[0]
assert reloaded.name == edited_name
assert reloaded.gds_layer == 555
assert reloaded.gds_datatype == 7
print("PASS: cifoutput edits survive Save Edits + a simulated relaunch.")

# -- Real write-back export: lands in ihp-sg13g2-cifout.tech, NOT
# ihp-sg13g2.tech -- same real "different file" pattern as cifinput. --
with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    written = export_mod.export_magic_types(PDK_ROOT, mtv2.technologies, dest_root=export_dir)
    cifout_export = [p for p in written if p.name == "ihp-sg13g2-cifout.tech"][0]
    cifout_text = cifout_export.read_text()
    import re as _re
    assert _re.search(r"calma\s+555\s+7\s*$", cifout_text, _re.MULTILINE)
    print("PASS: real write-back for cifoutput lands in ihp-sg13g2-cifout.tech.")

    main_export = [p for p in written if p.name == "ihp-sg13g2.tech"][0]
    assert main_export.read_text() == (PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2.tech").read_text()
    print("PASS: ihp-sg13g2.tech's own export is completely unaffected.")

# -- reconcile.py's own _magic_index still works against the new,
# flattened CifOutputLayerMapping shape (not the old, grouped-by-name
# CifLayer.gds_pairs list). --
report = reconcile_mod.reconcile([], mtv2.technologies["ihp-sg13g2-cifout"])
assert len(report.magic_only) > 0
print(f"PASS: reconcile.py's own _magic_index still works against the new flattened shape "
      f"({len(report.magic_only)} real (layer,datatype) pairs indexed).")

root2.destroy()
print("ALL MAGIC CIFOUTPUT TESTS PASS")

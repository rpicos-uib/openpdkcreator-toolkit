import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.pdklib import magic_tech as mt
from openpdkcreator.pdklib import magic_tech_writer as mtw
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
EXTRACT_PATH = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2-extract.tech"

# --- Real, direct parse of the fragment file: extract_resist is now
# line-tracked, sharing the same section bounds as extract_misc/
# extract_plane_order ---
tech = mt.parse_tech_file(EXTRACT_PATH)
print("extract_resist entries:", len(tech.extract_resist))
assert len(tech.extract_resist) == 30
assert all(r.line_no > 0 for r in tech.extract_resist)
print("PASS: real resist lines are line-tracked when the fragment file is parsed directly.")

# A real 'resist' layer repeats across variants(...) corner blocks --
# confirm more than one real row shares the same layer_spec, each with
# its own distinct line_no and distinct value (not merged/deduped).
hvndiffres_rows = [r for r in tech.extract_resist if r.layer_spec == "hvndiffres/active"]
print("real 'resist hvndiffres/active' rows across corners:", len(hvndiffres_rows))
assert len(hvndiffres_rows) == 3
assert len({r.line_no for r in hvndiffres_rows}) == 3
assert len({r.milliohms_per_square for r in hvndiffres_rows}) == 3
print("PASS: a real 'resist' layer repeated across variants(...) corners is kept as independent, distinct rows.")

# --- No-edit export of the real fragment file is still byte-identical
# now that extract_resist is a third group sharing the section ---
rendered = mtw.render_tech_file(EXTRACT_PATH, tech)
original = EXTRACT_PATH.read_text(encoding="utf-8", errors="replace")
if not original.endswith("\n"):
    original += "\n"
assert rendered == original
print("PASS: no-edit export of ihp-sg13g2-extract.tech is still byte-identical with three groups sharing the section.")

combined_path = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2.tech"
combined_tech = mt.parse_tech_file(combined_path)
combined_rendered = mtw.render_tech_file(combined_path, combined_tech)
combined_original = combined_path.read_text(encoding="utf-8", errors="replace")
if not combined_original.endswith("\n"):
    combined_original += "\n"
assert combined_rendered == combined_original
print("PASS: ihp-sg13g2.tech's own export is still byte-identical.")

# --- GUI: SimpleListEditor-backed Sheet resistance sub-pane ---
root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("ihp-sg13g2-extract")
mtv._refresh_all()
root.update()

print("Sheet resistance rows:", len(mtv.extract_resist_editor.tree.get_children()))
assert len(mtv.extract_resist_editor.tree.get_children()) == 30

mtv.extract_resist_editor.tree.selection_set(mtv.extract_resist_editor.tree.get_children()[0])
mtv.extract_resist_editor._on_select()
root.update()
mtv.extract_resist_editor.field_vars["milliohms_text"].set("99999")
root.update()
assert mtv.extract_resist_editor.current_entry.milliohms_per_square == 99999
row_values = mtv.extract_resist_editor.tree.item(mtv.extract_resist_editor.tree.get_children()[0])["values"]
assert str(row_values[1]) == "99999"
print("PASS: editing milliohms_text round-trips into the real int field.")

before_count = len(mtv.extract_resist_editor.tree.get_children())
mtv.extract_resist_editor.new_entry()
root.update()
assert len(mtv.extract_resist_editor.tree.get_children()) == before_count + 1
new_entry = mtv.extract_resist_editor.current_entry
assert new_entry.line_no == 0
mtv.extract_resist_editor.delete_entry()
root.update()
assert len(mtv.extract_resist_editor.tree.get_children()) == before_count
print("PASS: New/Delete Resist Entry work in the GUI.")

# -- Save Edits / relaunch persistence -------------------------------
edited_line_no = mtv.extract_resist_editor.entries[0].line_no
app._save_project()
root.update()

root.destroy()
root2 = tk.Tk()
app2 = App(root2, PDK_ROOT)
root2.update()
mtv2 = app2.magic_tech_view
mtv2.tech_var.set("ihp-sg13g2-extract")
mtv2._refresh_all()
root2.update()

reloaded = next(r for r in mtv2.extract_resist_editor.entries if r.line_no == edited_line_no)
print("reloaded milliohms_per_square:", reloaded.milliohms_per_square)
assert reloaded.milliohms_per_square == 99999
print("PASS: Sheet resistance edit survives Save Edits + a simulated relaunch.")

# --- Real write-back export ---
import tempfile
from openpdkcreator import export as export_mod

with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    written = export_mod.export_magic_types(PDK_ROOT, mtv2.technologies, dest_root=export_dir)
    exported_path = [p for p in written if p.name == "ihp-sg13g2-extract.tech"][0]
    text = exported_path.read_text()
    assert "99999" in text
    print("PASS: real ihp-sg13g2-extract.tech write-back contains the edited resistance.")

    exported_combined = [p for p in written if p.name == "ihp-sg13g2.tech"][0]
    assert exported_combined.read_text() == combined_original
    print("PASS: ihp-sg13g2.tech's own export via the same App/technologies dict is still byte-identical.")

root2.destroy()
print("ALL MAGIC EXTRACT RESIST TESTS PASS")

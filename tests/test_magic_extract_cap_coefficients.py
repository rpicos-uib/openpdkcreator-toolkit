import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.pdklib import magic_tech as mt
from openpdkcreator.pdklib import magic_tech_writer as mtw
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
EXTRACT_PATH = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2-extract.tech"

# --- Real, direct parse of the fragment file: extract_cap_coefficients
# is now line-tracked, the fourth group sharing extract_section bounds ---
tech = mt.parse_tech_file(EXTRACT_PATH)
print("extract_cap_coefficients entries:", len(tech.extract_cap_coefficients))
assert len(tech.extract_cap_coefficients) == 506
assert all(c.line_no > 0 for c in tech.extract_cap_coefficients)
print("PASS: real cap-coefficient lines are line-tracked when the fragment file is parsed directly.")

# A real 'defaultsidewall allpoly active' entry repeats across
# variants(...) corner blocks -- confirm distinct rows/line_nos/values.
sidewall_rows = [
    c for c in tech.extract_cap_coefficients
    if c.directive == "defaultsidewall" and c.args == ("allpoly", "active")
]
print("real 'defaultsidewall allpoly active' rows across corners:", len(sidewall_rows))
assert len(sidewall_rows) == 3
assert len({c.line_no for c in sidewall_rows}) == 3
assert len({c.values for c in sidewall_rows}) == 3
print("PASS: a real cap-coefficient entry repeated across variants(...) corners is kept as independent, distinct rows.")

# args_text/values_text round-trip
entry = tech.extract_cap_coefficients[0]
assert tuple(entry.args_text.split()) == entry.args
assert entry.values_text == ", ".join(f"{v:g}" for v in entry.values)
print("PASS: args_text/values_text render correctly from the real, parsed fields.")

# --- No-edit export of the real fragment file is still byte-identical
# now that extract_cap_coefficients is a fourth group sharing the section ---
rendered = mtw.render_tech_file(EXTRACT_PATH, tech)
original = EXTRACT_PATH.read_text(encoding="utf-8", errors="replace")
if not original.endswith("\n"):
    original += "\n"
assert rendered == original
print("PASS: no-edit export of ihp-sg13g2-extract.tech is still byte-identical with four groups sharing the section.")

combined_path = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2.tech"
combined_tech = mt.parse_tech_file(combined_path)
combined_rendered = mtw.render_tech_file(combined_path, combined_tech)
combined_original = combined_path.read_text(encoding="utf-8", errors="replace")
if not combined_original.endswith("\n"):
    combined_original += "\n"
assert combined_rendered == combined_original
print("PASS: ihp-sg13g2.tech's own export is still byte-identical.")

# --- GUI: SimpleListEditor-backed Extract Coefficients tab ---
root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("ihp-sg13g2-extract")
mtv._refresh_all()
root.update()

print("Extract Coefficients rows:", len(mtv.extract_coeff_editor.tree.get_children()))
assert len(mtv.extract_coeff_editor.tree.get_children()) == 506

mtv.extract_coeff_editor.tree.selection_set(mtv.extract_coeff_editor.tree.get_children()[0])
mtv.extract_coeff_editor._on_select()
root.update()
mtv.extract_coeff_editor.field_vars["values_text"].set("1.5, -2.5")
root.update()
assert mtv.extract_coeff_editor.current_entry.values == (1.5, -2.5)
row_values = mtv.extract_coeff_editor.tree.item(mtv.extract_coeff_editor.tree.get_children()[0])["values"]
assert row_values[2] == "1.5, -2.5"
print("PASS: editing values_text round-trips into the real values float tuple.")

mtv.extract_coeff_editor.field_vars["args_text"].set("editedarg1 editedarg2")
root.update()
assert mtv.extract_coeff_editor.current_entry.args == ("editedarg1", "editedarg2")
print("PASS: editing args_text round-trips into the real args tuple.")

before_count = len(mtv.extract_coeff_editor.tree.get_children())
mtv.extract_coeff_editor.new_entry()
root.update()
assert len(mtv.extract_coeff_editor.tree.get_children()) == before_count + 1
new_entry = mtv.extract_coeff_editor.current_entry
assert new_entry.line_no == 0
mtv.extract_coeff_editor.delete_entry()
root.update()
assert len(mtv.extract_coeff_editor.tree.get_children()) == before_count
print("PASS: New/Delete Cap Coefficient work in the GUI.")

# -- Save Edits / relaunch persistence -------------------------------
edited_line_no = mtv.extract_coeff_editor.entries[0].line_no
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

reloaded = next(c for c in mtv2.extract_coeff_editor.entries if c.line_no == edited_line_no)
print("reloaded args/values:", reloaded.args, reloaded.values)
assert reloaded.args == ("editedarg1", "editedarg2")
assert reloaded.values == (1.5, -2.5)
print("PASS: Cap Coefficient edit survives Save Edits + a simulated relaunch.")

# --- Real write-back export ---
import tempfile
from openpdkcreator import export as export_mod

with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    written = export_mod.export_magic_types(PDK_ROOT, mtv2.technologies, dest_root=export_dir)
    exported_path = [p for p in written if p.name == "ihp-sg13g2-extract.tech"][0]
    text = exported_path.read_text()
    assert "editedarg1 editedarg2 1.5 -2.5" in text
    print("PASS: real ihp-sg13g2-extract.tech write-back contains the edited args/values.")

    exported_combined = [p for p in written if p.name == "ihp-sg13g2.tech"][0]
    assert exported_combined.read_text() == combined_original
    print("PASS: ihp-sg13g2.tech's own export via the same App/technologies dict is still byte-identical.")

root2.destroy()
print("ALL MAGIC EXTRACT CAP COEFFICIENTS TESTS PASS")

import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.pdklib import magic_tech as mt
from openpdkcreator.pdklib import magic_tech_writer as mtw
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
EXTRACT_PATH = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2-extract.tech"

# --- Real, direct parse of the fragment file: extract_plane_order is
# now line-tracked, sharing the same section bounds as extract_misc ---
tech = mt.parse_tech_file(EXTRACT_PATH)
print("extract_plane_order entries:", len(tech.extract_plane_order))
assert len(tech.extract_plane_order) == 14
assert all(o.line_no > 0 for o in tech.extract_plane_order)
assert len({o.name for o in tech.extract_plane_order}) == 14, "planeorder sits before 'variants', no real repeats"
assert tech.extract_section_start_line > 0
assert tech.extract_section_end_line > tech.extract_section_start_line
print("PASS: real planeorder lines are line-tracked, all 14 unique, sharing the extract section's own bounds.")

dwell = next(o for o in tech.extract_plane_order if o.name == "dwell")
assert dwell.order == 0
print("PASS: a real planeorder entry's name/order parse correctly (dwell -> 0).")

# When parsed as part of ihp-sg13g2.tech's own combined view, extract's
# real lines still sit past that file's own safe_through boundary.
combined_path = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2.tech"
combined_tech = mt.parse_tech_file(combined_path)
assert combined_tech.extract_section_start_line == 0
assert combined_tech.extract_section_end_line == 0
assert len(combined_tech.extract_plane_order) == 14  # entries themselves still parse, just unmapped line_no
assert all(o.line_no == 0 for o in combined_tech.extract_plane_order)
print("PASS: parsed as part of ihp-sg13g2.tech's own combined view, plane-order entries still parse but line_no is 0.")

# --- No-edit export of the real fragment file is still byte-identical
# now that extract_plane_order is a second, real write-back group
# sharing the section with extract_misc ---
rendered = mtw.render_tech_file(EXTRACT_PATH, tech)
original = EXTRACT_PATH.read_text(encoding="utf-8", errors="replace")
if not original.endswith("\n"):
    original += "\n"
assert rendered == original
print("PASS: no-edit export of ihp-sg13g2-extract.tech is still byte-identical with two groups sharing the section.")

combined_rendered = mtw.render_tech_file(combined_path, combined_tech)
combined_original = combined_path.read_text(encoding="utf-8", errors="replace")
if not combined_original.endswith("\n"):
    combined_original += "\n"
assert combined_rendered == combined_original
print("PASS: ihp-sg13g2.tech's own export is still byte-identical.")

# --- GUI: SimpleListEditor-backed Plane order sub-pane ---
root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("ihp-sg13g2-extract")
mtv._refresh_all()
root.update()

print("Plane order rows:", len(mtv.extract_plane_order_editor.tree.get_children()))
assert len(mtv.extract_plane_order_editor.tree.get_children()) == 14

mtv.extract_plane_order_editor.tree.selection_set(mtv.extract_plane_order_editor.tree.get_children()[0])
mtv.extract_plane_order_editor._on_select()
root.update()
mtv.extract_plane_order_editor.field_vars["order_text"].set("42")
root.update()
assert mtv.extract_plane_order_editor.current_entry.order == 42
row_values = mtv.extract_plane_order_editor.tree.item(mtv.extract_plane_order_editor.tree.get_children()[0])["values"]
assert str(row_values[1]) == "42"
print("PASS: editing order_text round-trips into the real int order field.")

# New / Delete
before_count = len(mtv.extract_plane_order_editor.tree.get_children())
mtv.extract_plane_order_editor.new_entry()
root.update()
assert len(mtv.extract_plane_order_editor.tree.get_children()) == before_count + 1
new_entry = mtv.extract_plane_order_editor.current_entry
assert new_entry.line_no == 0
mtv.extract_plane_order_editor.delete_entry()
root.update()
assert len(mtv.extract_plane_order_editor.tree.get_children()) == before_count
print("PASS: New/Delete Plane Order Entry work in the GUI.")

# -- Save Edits / relaunch persistence -------------------------------
edited_line_no = mtv.extract_plane_order_editor.entries[0].line_no
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

reloaded = next(o for o in mtv2.extract_plane_order_editor.entries if o.line_no == edited_line_no)
print("reloaded order:", reloaded.order)
assert reloaded.order == 42
print("PASS: Plane order edit survives Save Edits + a simulated relaunch.")

# --- Real write-back export contains the edited value, and
# extract_misc (the other group sharing this section) is unaffected ---
import tempfile
from openpdkcreator import export as export_mod

with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    written = export_mod.export_magic_types(PDK_ROOT, mtv2.technologies, dest_root=export_dir)
    exported_path = [p for p in written if p.name == "ihp-sg13g2-extract.tech"][0]
    text = exported_path.read_text()
    assert f"{reloaded.name}" in text and " 42" in text
    print("PASS: real ihp-sg13g2-extract.tech write-back contains the edited plane order.")

    exported_combined = [p for p in written if p.name == "ihp-sg13g2.tech"][0]
    assert exported_combined.read_text() == combined_original
    print("PASS: ihp-sg13g2.tech's own export via the same App/technologies dict is still byte-identical.")

root2.destroy()
print("ALL MAGIC EXTRACT PLANE ORDER TESTS PASS")

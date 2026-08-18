import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.pdklib import magic_tech as mt
from openpdkcreator.pdklib import magic_tech_writer as mtw
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
DRC_PATH = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2-drc.tech"

# --- Real, direct parse of the fragment file: drc_angle_checks is now
# range-tracked, the drc section's first (and so far only) editable
# group ---
tech = mt.parse_tech_file(DRC_PATH)
print("angle checks:", len(tech.drc_angle_checks))
assert len(tech.drc_angle_checks) == 17
assert all(a.start_line > 0 for a in tech.drc_angle_checks)
assert len(tech.drc_checks) == 192  # width/spacing/maxwidth, also range-tracked, unaffected by this test's own angle edits
assert tech.drc_section_start_line == 23
assert tech.drc_section_end_line == 970

wrapped = [a for a in tech.drc_angle_checks if a.end_line > a.start_line]
print("real, backslash-wrapped multi-line entries:", [(a.layer, a.start_line, a.end_line) for a in wrapped])
assert len(wrapped) == 1
assert wrapped[0].layer == "allm7"
assert wrapped[0].end_line == wrapped[0].start_line + 1
single = [a for a in tech.drc_angle_checks if a.end_line == a.start_line]
assert len(single) == 16
print("PASS: 16 single-line + 1 real, backslash-wrapped two-line angle entry, all range-tracked correctly.")

allm7 = wrapped[0]
assert allm7.degrees == 45
assert allm7.message == "Only 45 and 90 degree angles permitted on metal7 (Grid Rules)"
print("PASS: the real, wrapped entry's own fields join correctly across its two real physical lines.")

# --- No-edit export is still byte-identical now that drc_angle_checks
# is a real ranged group sharing the drc section ---
rendered = mtw.render_tech_file(DRC_PATH, tech)
original = DRC_PATH.read_text(encoding="utf-8", errors="replace")
if not original.endswith("\n"):
    original += "\n"
assert rendered == original
print("PASS: no-edit export of ihp-sg13g2-drc.tech is byte-identical, including the also-editable width/spacing/maxwidth content.")

combined_path = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2.tech"
combined_tech = mt.parse_tech_file(combined_path)
assert combined_tech.drc_section_start_line == 0
assert len(combined_tech.drc_angle_checks) == 17  # entries still parse; just unmapped
assert all(a.start_line == 0 for a in combined_tech.drc_angle_checks)
combined_rendered = mtw.render_tech_file(combined_path, combined_tech)
combined_original = combined_path.read_text(encoding="utf-8", errors="replace")
if not combined_original.endswith("\n"):
    combined_original += "\n"
assert combined_rendered == combined_original
print("PASS: ihp-sg13g2.tech's own export is still byte-identical.")

# --- Editing the real, wrapped entry collapses it to one fresh line;
# every OTHER content in the section (width/spacing/maxwidth, other
# angles) stays untouched ---
allm7.degrees = 30
export_path = Path("/tmp/test_export_angles.tech")
mtw.export_tech_file(tech, export_path)
text = export_path.read_text()
edited_lines = [line for line in text.splitlines() if "allm7" in line and "30" in line and "angles" in line]
assert len(edited_lines) == 1
assert edited_lines[0].strip() == 'angles allm7 30 "Only 45 and 90 degree angles permitted on metal7 (Grid Rules)"'
reparsed = mt.parse_tech_file(export_path)
assert len(reparsed.drc_angle_checks) == 17
assert len(reparsed.drc_checks) == 192
re_allm7 = next(a for a in reparsed.drc_angle_checks if a.layer == "allm7")
assert re_allm7.degrees == 30
assert re_allm7.end_line == re_allm7.start_line  # collapsed to one line
print("PASS: editing the wrapped entry collapses it to one fresh line; width/spacing/maxwidth stay fully unaffected.")

# --- GUI: SimpleListEditor-backed angles sub-pane ---
root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("ihp-sg13g2-drc")
mtv._refresh_all()
root.update()

print("DRC angles rows:", len(mtv.drc_angles_editor.tree.get_children()))
assert len(mtv.drc_angles_editor.tree.get_children()) == 17
print("DRC width/spacing/maxwidth rows:", len(mtv.drc_checks_editor.tree.get_children()))
assert len(mtv.drc_checks_editor.tree.get_children()) == 192

mtv.drc_angles_editor.tree.selection_set(mtv.drc_angles_editor.tree.get_children()[0])
mtv.drc_angles_editor._on_select()
root.update()
mtv.drc_angles_editor.field_vars["degrees_text"].set("60")
root.update()
assert mtv.drc_angles_editor.current_entry.degrees == 60
row_values = mtv.drc_angles_editor.tree.item(mtv.drc_angles_editor.tree.get_children()[0])["values"]
assert str(row_values[1]) == "60"
print("PASS: editing degrees_text round-trips into the real int degrees field.")

before_count = len(mtv.drc_angles_editor.tree.get_children())
mtv.drc_angles_editor.new_entry()
root.update()
assert len(mtv.drc_angles_editor.tree.get_children()) == before_count + 1
new_entry = mtv.drc_angles_editor.current_entry
assert new_entry.start_line == 0 and new_entry.end_line == 0
mtv.drc_angles_editor.delete_entry()
root.update()
assert len(mtv.drc_angles_editor.tree.get_children()) == before_count
print("PASS: New/Delete Angle Check work in the GUI.")

# -- Save Edits / relaunch persistence -------------------------------
edited_start_line = mtv.drc_angles_editor.entries[0].start_line
app._save_project()
root.update()

root.destroy()
root2 = tk.Tk()
app2 = App(root2, PDK_ROOT)
root2.update()
mtv2 = app2.magic_tech_view
mtv2.tech_var.set("ihp-sg13g2-drc")
mtv2._refresh_all()
root2.update()

reloaded = next(a for a in mtv2.drc_angles_editor.entries if a.start_line == edited_start_line)
print("reloaded degrees:", reloaded.degrees)
assert reloaded.degrees == 60
print("PASS: Angle Check edit survives Save Edits + a simulated relaunch.")

# --- Real write-back export via the App/technologies dict ---
import tempfile
from openpdkcreator import export as export_mod

with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    written = export_mod.export_magic_types(PDK_ROOT, mtv2.technologies, dest_root=export_dir)
    exported_path = [p for p in written if p.name == "ihp-sg13g2-drc.tech"][0]
    text = exported_path.read_text()
    assert "60" in text
    print("PASS: real ihp-sg13g2-drc.tech write-back contains the edited degrees.")

    exported_combined = [p for p in written if p.name == "ihp-sg13g2.tech"][0]
    assert exported_combined.read_text() == combined_original
    print("PASS: ihp-sg13g2.tech's own export via the same App/technologies dict is still byte-identical.")

root2.destroy()
print("ALL MAGIC DRC ANGLES TESTS PASS")

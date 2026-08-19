import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.pdklib import magic_tech as mt
from openpdkcreator.pdklib import magic_tech_writer as mtw
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
DRC_PATH = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2-drc.tech"

# --- Real, direct parse of the fragment file: drc_misc covers every
# real drc-section keyword besides width/spacing/maxwidth/angles ---
tech = mt.parse_tech_file(DRC_PATH)
print("drc_misc entries:", len(tech.drc_misc))
assert len(tech.drc_misc) == 148
assert all(e.start_line > 0 for e in tech.drc_misc)
assert len(tech.drc_checks) == 192
assert len(tech.drc_angle_checks) == 17

from collections import Counter
counts = Counter(e.directive for e in tech.drc_misc)
expected = {
    "surround": 39, "edge4way": 24, "widespacing": 21, "cifmaxwidth": 15, "area": 12,
    "cifwidth": 9, "exact_overlap": 8, "cifspacing": 6, "overhang": 5, "extend": 5,
    "rect_only": 2, "cifarea": 1, "no_overlap": 1,
}
assert dict(counts) == expected, dict(counts)
assert "variants" not in counts and "style" not in counts and "scalefactor" not in counts and "cifstyle" not in counts
print("PASS: all 13 real directive keywords parsed with the exact real, confirmed counts; "
      "variants/style/scalefactor/cifstyle (section-level, not per-rule) correctly excluded.")

wrapped = [e for e in tech.drc_misc if e.end_line > e.start_line]
print("real, backslash-wrapped multi-line entries:", len(wrapped))
assert len(wrapped) == 103
from collections import Counter as _Counter
span_counts = _Counter(e.end_line - e.start_line for e in wrapped)
assert dict(span_counts) == {1: 100, 2: 3}  # 100 real two-line entries, 3 real three-line entries
print("PASS: the large majority (103 of 148) of real drc_misc entries wrap across more than one "
      "real physical line (100 two-line, 3 three-line), correctly range-tracked.")

# --- No-edit export is still byte-identical now that drc_misc is a
# real ranged group sharing the drc section alongside drc_checks/
# drc_angle_checks ---
rendered = mtw.render_tech_file(DRC_PATH, tech)
original = DRC_PATH.read_text(encoding="utf-8", errors="replace")
if not original.endswith("\n"):
    original += "\n"
assert rendered == original
print("PASS: no-edit export of ihp-sg13g2-drc.tech is byte-identical, including drc_misc.")

combined_path = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2.tech"
combined_tech = mt.parse_tech_file(combined_path)
assert len(combined_tech.drc_misc) == 148  # entries still parse; just unmapped (past the file's own first include)
assert all(e.start_line == 0 for e in combined_tech.drc_misc)
combined_rendered = mtw.render_tech_file(combined_path, combined_tech)
combined_original = combined_path.read_text(encoding="utf-8", errors="replace")
if not combined_original.endswith("\n"):
    combined_original += "\n"
assert combined_rendered == combined_original
print("PASS: ihp-sg13g2.tech's own export is still byte-identical.")

# --- Editing a real, wrapped entry collapses it to one fresh line;
# every OTHER content in the section (width/spacing/maxwidth, angles,
# every other drc_misc entry) stays untouched ---
target = next(e for e in tech.drc_misc if e.end_line > e.start_line and e.directive == "cifmaxwidth")
before_args = target.args
target.args_text = "EDITED_NAME 999 changed_filler \"a changed message\""
export_path = Path("/tmp/test_export_drc_misc.tech")
mtw.export_tech_file(tech, export_path)
text = export_path.read_text()
assert 'cifmaxwidth EDITED_NAME 999 changed_filler "a changed message"' in text
reparsed = mt.parse_tech_file(export_path)
assert len(reparsed.drc_misc) == 148
assert len(reparsed.drc_checks) == 192
assert len(reparsed.drc_angle_checks) == 17
re_target = next(e for e in reparsed.drc_misc if e.directive == "cifmaxwidth" and e.args[0] == "EDITED_NAME")
assert re_target.end_line == re_target.start_line  # collapsed to one line
untouched = [e for e in reparsed.drc_misc if not (e.directive == "cifmaxwidth" and e.args[0] == "EDITED_NAME")]
orig_untouched = [e for e in tech.drc_misc if e is not target]
assert [(e.directive, e.args) for e in untouched] == [(e.directive, e.args) for e in orig_untouched]
print("PASS: editing a wrapped entry collapses it to one fresh line; every other drc_misc entry, "
      "and width/spacing/maxwidth/angles, stay fully unaffected.")

# --- GUI: SimpleListEditor-backed misc pane ---
root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("ihp-sg13g2-drc")
mtv._refresh_all()
root.update()

print("DRC misc rows:", len(mtv.drc_misc_editor.tree.get_children()))
assert len(mtv.drc_misc_editor.tree.get_children()) == 148
assert len(mtv.drc_checks_editor.tree.get_children()) == 192
assert len(mtv.drc_angles_editor.tree.get_children()) == 17

mtv.drc_misc_editor.tree.selection_set(mtv.drc_misc_editor.tree.get_children()[0])
mtv.drc_misc_editor._on_select()
root.update()
mtv.drc_misc_editor.field_vars["args_text"].set("GUI_EDITED 42 note \"gui message\"")
root.update()
assert mtv.drc_misc_editor.current_entry.args == ("GUI_EDITED", "42", "note", '"gui', 'message"')
row_values = mtv.drc_misc_editor.tree.item(mtv.drc_misc_editor.tree.get_children()[0])["values"]
assert "GUI_EDITED" in str(row_values[1])
print("PASS: editing args_text round-trips into the real args tuple field.")

before_count = len(mtv.drc_misc_editor.tree.get_children())
mtv.drc_misc_editor.new_entry()
root.update()
assert len(mtv.drc_misc_editor.tree.get_children()) == before_count + 1
new_entry = mtv.drc_misc_editor.current_entry
assert new_entry.start_line == 0 and new_entry.end_line == 0
mtv.drc_misc_editor.delete_entry()
root.update()
assert len(mtv.drc_misc_editor.tree.get_children()) == before_count
print("PASS: New/Delete DRC Statement work in the GUI.")

# -- Save Edits / relaunch persistence -------------------------------
edited_start_line = mtv.drc_misc_editor.entries[0].start_line
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

reloaded = next(e for e in mtv2.drc_misc_editor.entries if e.start_line == edited_start_line)
print("reloaded args_text:", reloaded.args_text)
assert reloaded.args == ("GUI_EDITED", "42", "note", '"gui', 'message"')
print("PASS: DRC Statement edit survives Save Edits + a simulated relaunch.")

# --- Real write-back export via the App/technologies dict ---
import tempfile
from openpdkcreator import export as export_mod

with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    written = export_mod.export_magic_types(PDK_ROOT, mtv2.technologies, dest_root=export_dir)
    exported_path = [p for p in written if p.name == "ihp-sg13g2-drc.tech"][0]
    text = exported_path.read_text()
    assert "GUI_EDITED" in text
    print("PASS: real ihp-sg13g2-drc.tech write-back contains the edited args.")

    exported_combined = [p for p in written if p.name == "ihp-sg13g2.tech"][0]
    assert exported_combined.read_text() == combined_original
    print("PASS: ihp-sg13g2.tech's own export via the same App/technologies dict is still byte-identical.")

root2.destroy()
print("ALL MAGIC DRC MISC TESTS PASS")

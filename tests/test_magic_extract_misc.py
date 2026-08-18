import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.pdklib import magic_tech as mt
from openpdkcreator.pdklib import magic_tech_writer as mtw
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
EXTRACT_PATH = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2-extract.tech"

# --- Real, direct parse of the fragment file: extract_misc is now
# line-tracked and its own section bounds are safely mappable (no real
# 'include' line in this fragment file) ---
tech = mt.parse_tech_file(EXTRACT_PATH)
print("extract_misc entries:", len(tech.extract_misc))
assert len(tech.extract_misc) > 0
assert all(e.line_no > 0 for e in tech.extract_misc)
assert tech.extract_misc_section_start_line > 0
assert tech.extract_misc_section_end_line > tech.extract_misc_section_start_line
directives_present = {e.directive for e in tech.extract_misc}
assert directives_present <= {"contact", "devresist", "antenna", "disconnect", "substrate"}
print("PASS: real extract-section misc statements are now line-tracked when the fragment file is parsed directly.")

# A real 'contact' line repeats across variants(...) corner blocks --
# confirm more than one real row shares the same directive/first-arg
# pair, each with its own distinct line_no (not merged/deduped).
contact_rows = [e for e in tech.extract_misc if e.directive == "contact" and e.args and e.args[0] == "alldiffcont"]
print("real 'contact alldiffcont' rows across corners:", len(contact_rows))
assert len(contact_rows) >= 2
assert len({e.line_no for e in contact_rows}) == len(contact_rows)
print("PASS: a real 'contact' name repeated across variants(...) corners is kept as independent, distinct rows.")

# When parsed as part of ihp-sg13g2.tech's own combined view instead,
# extract's real lines sit well past that file's own safe_through
# boundary (the first real 'include' line) -- section bounds correctly
# come back 0, not guessed.
combined_path = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2.tech"
combined_tech = mt.parse_tech_file(combined_path)
assert combined_tech.extract_misc_section_start_line == 0
assert combined_tech.extract_misc_section_end_line == 0
print("PASS: parsed as part of ihp-sg13g2.tech's own combined view, extract_misc's section bounds are correctly 0.")

# --- No-edit export of the real fragment file is byte-identical ---
rendered = mtw.render_tech_file(EXTRACT_PATH, tech)
original = EXTRACT_PATH.read_text(encoding="utf-8", errors="replace")
if not original.endswith("\n"):
    original += "\n"
assert rendered == original
print("PASS: no-edit export of ihp-sg13g2-extract.tech is byte-identical to the real original.")

# The combined ihp-sg13g2.tech view (where extract_misc's own bounds
# are 0) must also stay completely untouched by this new domain.
combined_rendered = mtw.render_tech_file(combined_path, combined_tech)
combined_original = combined_path.read_text(encoding="utf-8", errors="replace")
if not combined_original.endswith("\n"):
    combined_original += "\n"
assert combined_rendered == combined_original
print("PASS: ihp-sg13g2.tech's own export is still byte-identical -- extract_misc write-back never touches it.")

# --- GUI: SimpleListEditor-backed Extract Misc tab ---
root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("ihp-sg13g2-extract")
mtv._refresh_all()
root.update()

print("Extract Misc rows:", len(mtv.extract_misc_editor.tree.get_children()))
assert len(mtv.extract_misc_editor.tree.get_children()) == len(tech.extract_misc)

# Edit an existing entry's args via the form.
mtv.extract_misc_editor.tree.selection_set(mtv.extract_misc_editor.tree.get_children()[0])
mtv.extract_misc_editor._on_select()
root.update()
mtv.extract_misc_editor.field_vars["args_text"].set("editedarg1 editedarg2")
root.update()
assert mtv.extract_misc_editor.current_entry.args == ("editedarg1", "editedarg2")
row_values = mtv.extract_misc_editor.tree.item(mtv.extract_misc_editor.tree.get_children()[0])["values"]
assert row_values[1] == "editedarg1 editedarg2"
print("PASS: editing args_text round-trips into the real args tuple, reflected in the row immediately.")

# New Extract Misc Statement / Delete
before_count = len(mtv.extract_misc_editor.tree.get_children())
mtv.extract_misc_editor.new_entry()
root.update()
assert len(mtv.extract_misc_editor.tree.get_children()) == before_count + 1
new_entry = mtv.extract_misc_editor.current_entry
assert new_entry.line_no == 0
mtv.extract_misc_editor.delete_entry()
root.update()
assert len(mtv.extract_misc_editor.tree.get_children()) == before_count
print("PASS: New/Delete Extract Misc Statement work in the GUI.")

# -- Save Edits / relaunch persistence -------------------------------
edited_line_no = mtv.extract_misc_editor.entries[0].line_no
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

reloaded = next(e for e in mtv2.extract_misc_editor.entries if e.line_no == edited_line_no)
print("reloaded args:", reloaded.args)
assert reloaded.args == ("editedarg1", "editedarg2")
print("PASS: Extract Misc edit survives Save Edits + a simulated relaunch.")

# --- Real write-back export contains the edited value ---
import tempfile
from openpdkcreator import export as export_mod

with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    written = export_mod.export_magic_types(PDK_ROOT, mtv2.technologies, dest_root=export_dir)
    exported_path = [p for p in written if p.name == "ihp-sg13g2-extract.tech"][0]
    text = exported_path.read_text()
    assert "editedarg1 editedarg2" in text
    print("PASS: real ihp-sg13g2-extract.tech write-back contains the edited args.")

    exported_combined = [p for p in written if p.name == "ihp-sg13g2.tech"][0]
    combined_text = exported_combined.read_text()
    assert combined_text == combined_original
    print("PASS: ihp-sg13g2.tech's own export via the same App/technologies dict is still byte-identical.")

root2.destroy()
print("ALL MAGIC EXTRACT MISC TESTS PASS")

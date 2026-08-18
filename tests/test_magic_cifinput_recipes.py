import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.pdklib import magic_tech as mt
from openpdkcreator.pdklib import magic_tech_writer as mtw
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
CIFIN_PATH = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2-cifin.tech"

# --- Real, direct parse of the fragment file: cifinput_recipes is now
# one entry per real block occurrence, range-tracked ---
tech = mt.parse_tech_file(CIFIN_PATH)
print("recipe blocks:", len(tech.cifinput_recipes))
assert len(tech.cifinput_recipes) == 211
assert all(b.start_line > 0 for b in tech.cifinput_recipes)
unique_names = {b.name for b in tech.cifinput_recipes}
assert len(unique_names) == 188
print("PASS: 211 real block occurrences load across 188 real unique names, all range-tracked.")

nwell_blocks = [b for b in tech.cifinput_recipes if b.name == "nwell"]
print("nwell blocks:", [(b.base_layer, b.start_line, b.end_line, len(b.ops)) for b in nwell_blocks])
assert len(nwell_blocks) == 2
assert {b.base_layer for b in nwell_blocks} == {"NWELL,WELLPIN", "schottkyarea"}
assert nwell_blocks[0].start_line != nwell_blocks[1].start_line
print("PASS: a real name repeated across two non-contiguous real blocks is kept as independent, distinct rows.")

assert len(tech.cifinput_ignored_layers) == 23
assert len(tech.cifinput_layer_hints) == 133
print("PASS: real ignored-layers/layer-hints tables are unaffected by this domain's own new range-tracking.")

# --- No-edit export is byte-identical, including real op content ---
rendered = mtw.render_tech_file(CIFIN_PATH, tech)
original = CIFIN_PATH.read_text(encoding="utf-8", errors="replace")
if not original.endswith("\n"):
    original += "\n"
assert rendered == original
print("PASS: no-edit export of ihp-sg13g2-cifin.tech is byte-identical.")

combined_path = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2.tech"
combined_tech = mt.parse_tech_file(combined_path)
assert combined_tech.cifinput_section_start_line == 0
assert len(combined_tech.cifinput_recipes) == 211
assert all(b.start_line == 0 for b in combined_tech.cifinput_recipes)
combined_rendered = mtw.render_tech_file(combined_path, combined_tech)
combined_original = combined_path.read_text(encoding="utf-8", errors="replace")
if not combined_original.endswith("\n"):
    combined_original += "\n"
assert combined_rendered == combined_original
print("PASS: ihp-sg13g2.tech's own export is still byte-identical.")

# --- Editing one nwell block's own header preserves its own real op
# content and leaves the OTHER nwell block completely untouched ---
target = nwell_blocks[0]
target.base_layer = "EDITEDBASE"
export_path = Path("/tmp/test_export_cifinput_recipes.tech")
mtw.export_tech_file(tech, export_path)
text = export_path.read_text()
edited_lines = [line for line in text.splitlines() if "EDITEDBASE" in line]
assert len(edited_lines) == 1
assert edited_lines[0].strip() == "layer nwell EDITEDBASE"
reparsed = mt.parse_tech_file(export_path)
assert len(reparsed.cifinput_recipes) == 211
re_nwell = [b for b in reparsed.cifinput_recipes if b.name == "nwell"]
assert len(re_nwell) == 2
edited = next(b for b in re_nwell if b.base_layer == "EDITEDBASE")
assert len(edited.ops) == len(target.ops)
untouched = next(b for b in re_nwell if b.base_layer != "EDITEDBASE")
assert untouched.base_layer == "schottkyarea"
assert len(untouched.ops) == len(nwell_blocks[1].ops)
assert len(reparsed.cifinput_ignored_layers) == 23
assert len(reparsed.cifinput_layer_hints) == 133
print("PASS: editing one block's header preserves its own real op content and leaves the other block, ignored layers, and hints untouched.")

# --- GUI: SimpleListEditor-backed header editor + read-only ops tree ---
root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("ihp-sg13g2-cifin")
mtv._refresh_all()
root.update()

print("CIF Input Recipes editor rows:", len(mtv.cifinput_recipes_editor.tree.get_children()))
assert len(mtv.cifinput_recipes_editor.tree.get_children()) == 211
assert len(mtv.cifinput_recipes_tree.get_children()) == 211

# No New/Delete buttons for this domain (allow_new_delete=False).
assert mtv.cifinput_recipes_editor.new_entry_factory is None

mtv.cifinput_recipes_editor.tree.selection_set(mtv.cifinput_recipes_editor.tree.get_children()[0])
mtv.cifinput_recipes_editor._on_select()
root.update()
mtv.cifinput_recipes_editor.field_vars["base_layer"].set("editedviagui")
root.update()
assert mtv.cifinput_recipes_editor.current_entry.base_layer == "editedviagui"
row_values = mtv.cifinput_recipes_editor.tree.item(mtv.cifinput_recipes_editor.tree.get_children()[0])["values"]
assert row_values[2] == "editedviagui"
print("PASS: editing base_layer round-trips into the real field, reflected in the row immediately.")

mtv.cifinput_recipes_editor.field_vars["kind_text"].set("templayer")
root.update()
assert mtv.cifinput_recipes_editor.current_entry.is_templayer is True
print("PASS: editing kind_text round-trips into the real is_templayer bool field.")

# -- Save Edits / relaunch persistence -------------------------------
edited_start_line = mtv.cifinput_recipes_editor.entries[0].start_line
app._save_project()
root.update()

root.destroy()
root2 = tk.Tk()
app2 = App(root2, PDK_ROOT)
root2.update()
mtv2 = app2.magic_tech_view
mtv2.tech_var.set("ihp-sg13g2-cifin")
mtv2._refresh_all()
root2.update()

reloaded = next(b for b in mtv2.cifinput_recipes_editor.entries if b.start_line == edited_start_line)
print("reloaded base_layer/kind_text/ops:", reloaded.base_layer, reloaded.kind_text, len(reloaded.ops))
assert reloaded.base_layer == "editedviagui"
assert reloaded.kind_text == "templayer"
assert len(reloaded.ops) == len(nwell_blocks[0].ops) if reloaded.name == "nwell" else True
print("PASS: CIF Input Recipe header edit survives Save Edits + a simulated relaunch.")

# --- Real write-back export via the App/technologies dict ---
import tempfile
from openpdkcreator import export as export_mod

with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    written = export_mod.export_magic_types(PDK_ROOT, mtv2.technologies, dest_root=export_dir)
    exported_path = [p for p in written if p.name == "ihp-sg13g2-cifin.tech"][0]
    text = exported_path.read_text()
    edited_export_lines = [line for line in text.splitlines() if "editedviagui" in line]
    assert len(edited_export_lines) == 1
    assert "templayer" in edited_export_lines[0]
    print("PASS: real ihp-sg13g2-cifin.tech write-back contains the edited header.")

    exported_combined = [p for p in written if p.name == "ihp-sg13g2.tech"][0]
    assert exported_combined.read_text() == combined_original
    print("PASS: ihp-sg13g2.tech's own export via the same App/technologies dict is still byte-identical.")

root2.destroy()
print("ALL MAGIC CIFINPUT RECIPES TESTS PASS")

import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.pdklib import magic_tech as mt
from openpdkcreator.pdklib import magic_tech_writer as mtw
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
DRC_PATH = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2-drc.tech"

# --- Real, direct parse: drc_checks (width/spacing/maxwidth) is now
# range-tracked, with the real mode/exception-list filler captured
# into filler_raw ---
tech = mt.parse_tech_file(DRC_PATH)
print("drc_checks:", len(tech.drc_checks))
assert len(tech.drc_checks) == 192
by_type = {}
for c in tech.drc_checks:
    by_type[c.check_type] = by_type.get(c.check_type, 0) + 1
assert by_type == {"width": 65, "spacing": 101, "maxwidth": 26}
assert all(c.start_line > 0 for c in tech.drc_checks)
print("PASS: all 192 real width/spacing/maxwidth entries load, correctly split by type, all range-tracked.")

wrapped = [c for c in tech.drc_checks if c.end_line > c.start_line]
with_filler = [c for c in tech.drc_checks if c.filler_raw]
print("wrapped:", len(wrapped), "with filler:", len(with_filler))
assert len(wrapped) == 70
assert len(with_filler) == 133
print("PASS: real backslash-wrapped entries and real mode/exception-list filler both captured (not silently dropped).")

# A real filler + real two-group layers_text spot check
dnwell = next(c for c in tech.drc_checks if c.check_type == "spacing" and c.layer_args[0] == ["dnwell"] and c.layer_args[1] == ["allnwell"] and "N-well spacing to N-well" in c.message)
assert dnwell.filler_raw == "surround_ok"
assert dnwell.layers_text == "dnwell | allnwell"
assert dnwell.value_text == "2.2"
print("PASS: layers_text/value_text/filler_raw all render correctly from the real, parsed fields.")

# A real mid-layer-list wrap (spacing difffill ndc,pdc,...,hvpsc \)
midwrap = next(c for c in tech.drc_checks if c.check_type == "spacing" and c.layer_args[0] == ["difffill"] and "hvpsc" in c.layer_args[1])
assert midwrap.end_line > midwrap.start_line
assert midwrap.filler_raw == "touching_illegal"
print("PASS: a real continuation that splits mid layer-list still parses and range-tracks correctly.")

# --- No-edit export is byte-identical, including all 70 real wraps
# and all 133 real filler-carrying lines ---
rendered = mtw.render_tech_file(DRC_PATH, tech)
original = DRC_PATH.read_text(encoding="utf-8", errors="replace")
if not original.endswith("\n"):
    original += "\n"
assert rendered == original
print("PASS: no-edit export of ihp-sg13g2-drc.tech is byte-identical.")

combined_path = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2.tech"
combined_tech = mt.parse_tech_file(combined_path)
assert combined_tech.drc_section_start_line == 0
assert len(combined_tech.drc_checks) == 192
assert all(c.start_line == 0 for c in combined_tech.drc_checks)
combined_rendered = mtw.render_tech_file(combined_path, combined_tech)
combined_original = combined_path.read_text(encoding="utf-8", errors="replace")
if not combined_original.endswith("\n"):
    combined_original += "\n"
assert combined_rendered == combined_original
print("PASS: ihp-sg13g2.tech's own export is still byte-identical.")

# --- Editing a real, wrapped, filler-carrying entry preserves the
# filler and collapses to one fresh line; every other wrap is untouched ---
dnwell.value_um = 9.999
export_path = Path("/tmp/test_export_drc_checks.tech")
mtw.export_tech_file(tech, export_path)
text = export_path.read_text()
edited_lines = [line for line in text.splitlines() if "9999" in line]
assert len(edited_lines) == 1
assert edited_lines[0].strip() == 'spacing dnwell allnwell 9999 surround_ok "Deep N-well spacing to N-well < %d (NBL.d)"'
reparsed = mt.parse_tech_file(export_path)
assert len(reparsed.drc_checks) == 192
re_dnwell = next(c for c in reparsed.drc_checks if abs(c.value_um - 9.999) < 1e-9)
assert re_dnwell.filler_raw == "surround_ok"
assert re_dnwell.end_line == re_dnwell.start_line
other_wrapped = [c for c in reparsed.drc_checks if c.end_line > c.start_line]
assert len(other_wrapped) == 69
print("PASS: editing a wrapped, filler-carrying entry preserves the filler and collapses it to one fresh line; every other real wrap is untouched.")

# --- GUI: SimpleListEditor-backed width/spacing/maxwidth pane ---
root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("ihp-sg13g2-drc")
mtv._refresh_all()
root.update()

print("DRC checks rows:", len(mtv.drc_checks_editor.tree.get_children()))
assert len(mtv.drc_checks_editor.tree.get_children()) == 192

mtv.drc_checks_editor.tree.selection_set(mtv.drc_checks_editor.tree.get_children()[0])
mtv.drc_checks_editor._on_select()
root.update()
mtv.drc_checks_editor.field_vars["filler_raw"].set("edited_mode")
root.update()
assert mtv.drc_checks_editor.current_entry.filler_raw == "edited_mode"
row_values = mtv.drc_checks_editor.tree.item(mtv.drc_checks_editor.tree.get_children()[0])["values"]
assert row_values[3] == "edited_mode"
print("PASS: editing filler_raw round-trips into the real field.")

mtv.drc_checks_editor.field_vars["value_text"].set("1.234")
root.update()
assert abs(mtv.drc_checks_editor.current_entry.value_um - 1.234) < 1e-9
print("PASS: editing value_text round-trips into the real float value_um field.")

before_count = len(mtv.drc_checks_editor.tree.get_children())
mtv.drc_checks_editor.new_entry()
root.update()
assert len(mtv.drc_checks_editor.tree.get_children()) == before_count + 1
new_entry = mtv.drc_checks_editor.current_entry
assert new_entry.start_line == 0 and new_entry.end_line == 0
mtv.drc_checks_editor.delete_entry()
root.update()
assert len(mtv.drc_checks_editor.tree.get_children()) == before_count
print("PASS: New/Delete DRC Check work in the GUI.")

# -- Save Edits / relaunch persistence -------------------------------
edited_start_line = mtv.drc_checks_editor.entries[0].start_line
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

reloaded = next(c for c in mtv2.drc_checks_editor.entries if c.start_line == edited_start_line)
print("reloaded filler_raw/value_um:", reloaded.filler_raw, reloaded.value_um)
assert reloaded.filler_raw == "edited_mode"
assert abs(reloaded.value_um - 1.234) < 1e-9
print("PASS: DRC Check edit survives Save Edits + a simulated relaunch.")

# --- Real write-back export via the App/technologies dict ---
import tempfile
from openpdkcreator import export as export_mod

with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    written = export_mod.export_magic_types(PDK_ROOT, mtv2.technologies, dest_root=export_dir)
    exported_path = [p for p in written if p.name == "ihp-sg13g2-drc.tech"][0]
    text = exported_path.read_text()
    assert "edited_mode" in text and "1234" in text
    print("PASS: real ihp-sg13g2-drc.tech write-back contains the edited filler/value.")

    exported_combined = [p for p in written if p.name == "ihp-sg13g2.tech"][0]
    assert exported_combined.read_text() == combined_original
    print("PASS: ihp-sg13g2.tech's own export via the same App/technologies dict is still byte-identical.")

root2.destroy()
print("ALL MAGIC DRC CHECKS TESTS PASS")

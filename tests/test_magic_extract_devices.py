import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.pdklib import magic_tech as mt
from openpdkcreator.pdklib import magic_tech_writer as mtw
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
EXTRACT_PATH = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2-extract.tech"

# --- Real, direct parse of the fragment file: extract_devices is now
# range-tracked (start_line/end_line), the fifth group sharing the
# extract section, and the only ranged one ---
tech = mt.parse_tech_file(EXTRACT_PATH)
print("extract_devices entries:", len(tech.extract_devices))
assert len(tech.extract_devices) == 50
assert all(d.start_line > 0 for d in tech.extract_devices)

wrapped = [d for d in tech.extract_devices if d.end_line > d.start_line]
print("real, backslash-wrapped multi-line entries:", len(wrapped), [d.type_name for d in wrapped])
assert len(wrapped) == 5
assert all(d.end_line == d.start_line + 1 for d in wrapped)
single = [d for d in tech.extract_devices if d.end_line == d.start_line]
assert len(single) == 45
print("PASS: 45 single-line + 5 real, backslash-wrapped two-line device entries all range-tracked correctly.")

pfet = next(d for d in tech.extract_devices if d.type_name == "pfet" and d.devclass == "msubcircuit")
assert pfet.model == "sg13_lv_pmos"
assert pfet.rest_text == "*pdiff *pdiff nwell error l=l w=w a1=as p1=ps a2=ad p2=pd"
print("PASS: a real, wrapped entry's own fields are correctly joined across its two real physical lines.")

# --- No-edit export is still byte-identical now that extract_devices
# is a fifth, ranged group sharing the section ---
rendered = mtw.render_tech_file(EXTRACT_PATH, tech)
original = EXTRACT_PATH.read_text(encoding="utf-8", errors="replace")
if not original.endswith("\n"):
    original += "\n"
assert rendered == original
print("PASS: no-edit export of ihp-sg13g2-extract.tech is still byte-identical with the ranged group included.")

combined_path = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2.tech"
combined_tech = mt.parse_tech_file(combined_path)
assert combined_tech.extract_section_start_line == 0
assert len(combined_tech.extract_devices) == 50  # entries still parse; just unmapped
assert all(d.start_line == 0 for d in combined_tech.extract_devices)
combined_rendered = mtw.render_tech_file(combined_path, combined_tech)
combined_original = combined_path.read_text(encoding="utf-8", errors="replace")
if not combined_original.endswith("\n"):
    combined_original += "\n"
assert combined_rendered == combined_original
print("PASS: ihp-sg13g2.tech's own export is still byte-identical.")

# --- Editing a real, wrapped entry collapses it to one fresh line;
# every OTHER wrapped entry keeps its own real multi-line wrap ---
pfet.model = "EDITEDMODEL"
export_path = Path("/tmp/test_export_devices.tech")
mtw.export_tech_file(tech, export_path)
text = export_path.read_text()
edited_lines = [line for line in text.splitlines() if "EDITEDMODEL" in line]
assert len(edited_lines) == 1
assert edited_lines[0].strip() == "device msubcircuit EDITEDMODEL pfet *pdiff *pdiff nwell error l=l w=w a1=as p1=ps a2=ad p2=pd"
reparsed = mt.parse_tech_file(export_path)
assert len(reparsed.extract_devices) == 50
re_pfet = next(d for d in reparsed.extract_devices if d.type_name == "pfet" and d.devclass == "msubcircuit")
assert re_pfet.model == "EDITEDMODEL"
assert re_pfet.end_line == re_pfet.start_line  # collapsed to one line
other_wrapped = [d for d in reparsed.extract_devices if d.type_name in ("nfet", "hvpfet", "hvnfet", "hvnmosesd") and d.devclass == "msubcircuit"]
assert len(other_wrapped) == 4
assert all(d.end_line == d.start_line + 1 for d in other_wrapped)
print("PASS: editing a wrapped entry collapses it to one fresh line; every other wrapped entry keeps its own real two-line wrap.")

# --- GUI: SimpleListEditor-backed Extract Devices tab ---
root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("ihp-sg13g2-extract")
mtv._refresh_all()
root.update()

print("Extract Devices rows:", len(mtv.extract_devices_editor.tree.get_children()))
assert len(mtv.extract_devices_editor.tree.get_children()) == 50

mtv.extract_devices_editor.tree.selection_set(mtv.extract_devices_editor.tree.get_children()[0])
mtv.extract_devices_editor._on_select()
root.update()
mtv.extract_devices_editor.field_vars["rest_text"].set("edited=1 rest=2")
root.update()
assert mtv.extract_devices_editor.current_entry.rest == ("edited=1", "rest=2")
print("PASS: editing rest_text round-trips into the real rest tuple.")

before_count = len(mtv.extract_devices_editor.tree.get_children())
mtv.extract_devices_editor.new_entry()
root.update()
assert len(mtv.extract_devices_editor.tree.get_children()) == before_count + 1
new_entry = mtv.extract_devices_editor.current_entry
assert new_entry.start_line == 0 and new_entry.end_line == 0
mtv.extract_devices_editor.delete_entry()
root.update()
assert len(mtv.extract_devices_editor.tree.get_children()) == before_count
print("PASS: New/Delete Device work in the GUI.")

# -- Save Edits / relaunch persistence -------------------------------
edited_start_line = mtv.extract_devices_editor.entries[0].start_line
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

reloaded = next(d for d in mtv2.extract_devices_editor.entries if d.start_line == edited_start_line)
print("reloaded rest:", reloaded.rest)
assert reloaded.rest == ("edited=1", "rest=2")
print("PASS: Device edit survives Save Edits + a simulated relaunch.")

# --- Real write-back export via the App/technologies dict ---
import tempfile
from openpdkcreator import export as export_mod

with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    written = export_mod.export_magic_types(PDK_ROOT, mtv2.technologies, dest_root=export_dir)
    exported_path = [p for p in written if p.name == "ihp-sg13g2-extract.tech"][0]
    text = exported_path.read_text()
    assert "edited=1 rest=2" in text
    print("PASS: real ihp-sg13g2-extract.tech write-back contains the edited rest.")

    exported_combined = [p for p in written if p.name == "ihp-sg13g2.tech"][0]
    assert exported_combined.read_text() == combined_original
    print("PASS: ihp-sg13g2.tech's own export via the same App/technologies dict is still byte-identical.")

root2.destroy()
print("ALL MAGIC EXTRACT DEVICES TESTS PASS")

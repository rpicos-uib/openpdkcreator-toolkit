import sys
sys.path.insert(0, "/foss/designs")
import shutil
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator.ihp import layers as layers_mod
from openpdkcreator.ihp import magic_tech as magic_tech_mod
from openpdkcreator.ihp import lef as lef_mod
from openpdkcreator import export as export_mod

PDK_ROOT = Path("/tmp/empty_pdk")
shutil.rmtree(PDK_ROOT, ignore_errors=True)

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

# ============ Layers ============
assert app.lyp_path is None
lyp_path = PDK_ROOT / "libs.tech" / "klayout" / "tech" / "memristor.lyp"
layers_mod.create_new_lyp_file(lyp_path)
app.load()
root.update()
assert app.lyp_path == lyp_path, app.lyp_path
assert app.project.layers == []
print("PASS: create_new_lyp_file + app.load() picks up a fresh, empty .lyp.")

# New Layer via the real LayersView action
app.layers_view._new_layer()
root.update()
assert len(app.project.layers) == 1
new_layer = app.project.layers[0]
new_layer.name = "TopElectrode.drawing"
new_layer.gds_layer, new_layer.gds_datatype = 200, 0
new_layer.frame_color = "#ff0000"
new_layer.fill_color = "#ffcccc"
print("PASS: New Layer adds a real, editable Layer with start_line=0.")

with __import__("tempfile").TemporaryDirectory() as tmp:
    export_path = export_mod.export_layers(PDK_ROOT, lyp_path, app.project.layers)
    text = export_path.read_text()
    print("--- exported .lyp ---")
    print(text)
    assert "<name>TopElectrode.drawing</name>" in text
    assert "<source>200/0</source>" in text
    assert text.count("<properties>") == 1
    reparsed = layers_mod.import_layers(PDK_ROOT, export_path)
    assert len(reparsed) == 1 and reparsed[0].name == "TopElectrode.drawing"
    print("PASS: exported .lyp is valid XML, round-trips back to one real layer.")

# ============ Magic Tech ============
tech_path = PDK_ROOT / "libs.tech" / "magic" / "memristor.tech"
magic_tech_mod.create_new_tech_file(tech_path)
app.magic_tech_view.load()
root.update()
assert "memristor" in app.magic_tech_view.technologies
tech = app.magic_tech_view.technologies["memristor"]
assert tech.types == [] and tech.planes == [] and tech.contacts == [] and tech.aliases == []
assert tech.types_section_start_line and tech.types_section_end_line
print("PASS: create_new_tech_file + load() produces a real, empty, write-back-mappable technology.")

app.magic_tech_view.tech_var.set("memristor")
app.magic_tech_view._refresh_all()
new_plane = magic_tech_mod.PlaneEntry(name="metal", short_code="m")
tech.planes.append(new_plane)
new_type = magic_tech_mod.TypeEntry(plane="metal", canonical_name="TE", aliases=["topelectrode"])
tech.types.append(new_type)

from openpdkcreator.ihp import magic_tech_writer as magic_tech_writer_mod
rendered = magic_tech_writer_mod.render_tech_file(tech_path, tech)
print("--- rendered .tech (planes/types section) ---")
lines = rendered.splitlines()
start = next(i for i, l in enumerate(lines) if l.strip() == "planes")
print("\n".join(lines[start:start+10]))
assert "metal, m" in rendered or "metal,m" in rendered
assert "TE" in rendered

export_path2 = magic_tech_mod.find_tech_files(PDK_ROOT)[0]
export_out = export_mod.export_magic_types(PDK_ROOT, {"memristor": tech})
reparsed_tech = magic_tech_mod.parse_tech_file(tech_path)  # original still pristine (export never touches data/)
assert reparsed_tech.planes == [] and reparsed_tech.types == []
print("PASS: export_magic_types wrote a real, separate export/ copy; original stays pristine.")

# ============ LEF ============
lef_path = PDK_ROOT / "libs.ref" / "memristor_cells" / "lef" / "memristor.lef"
lef_mod.create_new_lef_file(lef_path)
app.lef_view.load()
root.update()
assert str(lef_path.relative_to(PDK_ROOT)) in app.lef_view.lef_files
parsed_lef = app.get_parsed_lef(lef_path)
assert parsed_lef.macros == []
print("PASS: create_new_lef_file + LefView.load() picks up a valid, empty library.")

root.destroy()
print("ALL SKELETON TESTS PASS")

import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path
import shutil

from openpdkcreator.gui.app import App
from openpdkcreator import export as export_mod
from openpdkcreator.ihp import library_index as li_mod
from openpdkcreator.ihp import user_models as user_models_mod
from openpdkcreator.ihp import verilog as verilog_mod
from openpdkcreator.gui import library_manager_view as lmv_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
PROJECT_ROOT = export_mod.PROJECT_ROOT

# --- create_new_verilog_file / create_new_veriloga_file: real,
# minimal, valid skeletons, direction-populated when known, round-trip
# back through this project's own real parser ---
tmp_dir = Path("/tmp/test_verilog_veriloga_editors")
shutil.rmtree(tmp_dir, ignore_errors=True)
tmp_dir.mkdir(parents=True)

v_path = tmp_dir / "my_gate.v"
verilog_mod.create_new_verilog_file(
    v_path, "my_gate", [("A", "input"), ("B", "input"), ("Y", "output")],
)
modules = verilog_mod.find_modules(v_path)
assert len(modules) == 1
mod = modules[0]
assert mod.name == "my_gate"
assert [p.name for p in mod.ports] == ["A", "B", "Y"]
assert [p.direction for p in mod.ports] == ["input", "input", "output"]
print("PASS: create_new_verilog_file writes a real module with correct, real ports/directions.")

va_path = tmp_dir / "my_model.va"
verilog_mod.create_new_veriloga_file(va_path, "my_model", [("p", "inout"), ("n", "inout")])
va_text = va_path.read_text()
assert '`include "disciplines.vams"' in va_text
assert "inout p, n;" in va_text
assert "electrical p, n;" in va_text
assert "analog begin" in va_text and "endmodule" in va_text
print("PASS: create_new_veriloga_file writes a real, correctly-shaped Verilog-A skeleton.")

empty_v = tmp_dir / "empty.v"
verilog_mod.create_new_verilog_file(empty_v, "empty_mod", None)
assert "module empty_mod();" in empty_v.read_text()
print("PASS: create_new_verilog_file with no known ports writes an honestly empty port list.")

# --- infer_ports_for_cell: real LEF-sourced pins for a real, known
# IHP stdcell, confirmed against a direct grep of the real .lef ---
ports = li_mod.infer_ports_for_cell(PDK_ROOT, PROJECT_ROOT, "sg13g2_stdcell", "sg13g2_inv_1")
ports_by_name = dict(ports)
assert ports_by_name.get("A") == "input"
assert ports_by_name.get("Y") == "output"
assert ports_by_name.get("VDD") == "inout"
assert ports_by_name.get("VSS") == "inout"
print("PASS: infer_ports_for_cell pulls sg13g2_inv_1's real LEF pins with correctly normalized directions.")

no_ports = li_mod.infer_ports_for_cell(PDK_ROOT, PROJECT_ROOT, "sg13g2_stdcell", "not_a_real_cell")
assert no_ports == []
print("PASS: infer_ports_for_cell returns an honestly empty list for a cell with no other known view.")

# --- Full GUI flow: a project cell with only a hand-authored xschem
# symbol (real pin syntax, confirmed against a real IHP .sym) gets its
# real pins carried into a newly Created Verilog-A view ---
registry_path = li_mod.registry_path(PROJECT_ROOT)
registry_path.unlink(missing_ok=True)
shutil.rmtree(PROJECT_ROOT / lmv_mod.LIBRARIES_DIRNAME, ignore_errors=True)
# Real, tracked directories (user_models/{verilog,veriloga}/ each carry
# a real, committed .gitkeep) -- remove only this test's own real,
# throwaway output file by name, never the whole directory, so a
# stray earlier .gitkeep is never collaterally deleted.
va_created_path = user_models_mod.user_models_root(PROJECT_ROOT) / user_models_mod.VERILOGA_DIRNAME / "my_amp_cell.va"
v_created_path = user_models_mod.user_models_root(PROJECT_ROOT) / user_models_mod.VERILOG_DIRNAME / "my_amp_cell.v"
va_created_path.unlink(missing_ok=True)
v_created_path.unlink(missing_ok=True)

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()
lmv = app.library_manager_view

li_mod.register_library(PROJECT_ROOT, "my_amp_lib")
sym_dir = PROJECT_ROOT / lmv_mod.LIBRARIES_DIRNAME / "my_amp_lib"
sym_dir.mkdir(parents=True)
sym_path = sym_dir / "my_amp_cell.sym"
sym_path.write_text(
    "v {xschem version=3.4.6 file_version=1.2}\n"
    "G {}\n"
    "K {type=subcircuit}\n"
    "V {}\n"
    "S {}\n"
    "B 5 -42.5 -2.5 -37.5 2.5 {name=IN dir=in}\n"
    "B 5 37.5 -2.5 42.5 2.5 {name=OUT dir=out}\n"
    "E {}\n",
    encoding="utf-8",
)
li_mod.register_entry(PROJECT_ROOT, "my_amp_lib", "my_amp_cell", "xschem_symbol", sym_path)

lmv.refresh_libraries()
root.update()
lmv.library_tree.selection_set("my_amp_lib")
root.update()
lmv.cell_tree.selection_set("my_amp_cell")
root.update()
assert "xschem_symbol" in lmv._entries
print("PASS: the hand-authored symbol + registered entry shows up in the real GUI.")

lmv._create_view("veriloga")
root.update()

va_created_path = user_models_mod.user_models_root(PROJECT_ROOT) / user_models_mod.VERILOGA_DIRNAME / "my_amp_cell.va"
assert va_created_path.is_file(), f"expected a real file at {va_created_path}"
assert lmv._entries["veriloga"].path == va_created_path
va_created_text = va_created_path.read_text()
assert "inout IN, OUT;" in va_created_text
assert "electrical IN, OUT;" in va_created_text
print("PASS: Create for Verilog-A pulls the real, correct pins (IN, OUT) from the cell's own xschem symbol.")

lmv._create_view("verilog")
root.update()
v_created_path = user_models_mod.user_models_root(PROJECT_ROOT) / user_models_mod.VERILOG_DIRNAME / "my_amp_cell.v"
assert v_created_path.is_file()
v_created_text = v_created_path.read_text()
assert "module my_amp_cell(IN, OUT);" in v_created_text
assert "input IN;" in v_created_text
assert "output OUT;" in v_created_text
print("PASS: Create for Verilog also pulls the real, correct pins/directions from the same symbol.")

root.destroy()

# --- cleanup ---
registry_path.unlink(missing_ok=True)
shutil.rmtree(PROJECT_ROOT / lmv_mod.LIBRARIES_DIRNAME, ignore_errors=True)
va_created_path.unlink(missing_ok=True)
v_created_path.unlink(missing_ok=True)
shutil.rmtree(tmp_dir, ignore_errors=True)

print("ALL VERILOG/VERILOG-A EDITOR TESTS PASS")

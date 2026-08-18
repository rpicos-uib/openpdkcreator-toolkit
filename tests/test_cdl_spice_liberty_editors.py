import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path
import shutil

from openpdkcreator.gui.app import App
from openpdkcreator import export as export_mod
from openpdkcreator.pdklib import library_index as li_mod
from openpdkcreator.pdklib import liberty as liberty_mod
from openpdkcreator.pdklib import netlist as netlist_mod
from openpdkcreator.gui import library_manager_view as lmv_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
PROJECT_ROOT = export_mod.PROJECT_ROOT

# --- create_new_cdl_file/create_new_spice_file/create_new_liberty_file:
# real, minimal, valid skeletons, direction-populated when known,
# round-trip back through this project's own real parsers ---
tmp_dir = Path("/tmp/test_cdl_spice_liberty_editors")
shutil.rmtree(tmp_dir, ignore_errors=True)
tmp_dir.mkdir(parents=True)

cdl_path = tmp_dir / "my_gate.cdl"
netlist_mod.create_new_cdl_file(cdl_path, "my_gate", [("A", "input"), ("B", "input"), ("Y", "output")])
cdl_text = cdl_path.read_text()
assert ".SUBCKT my_gate A B Y" in cdl_text
assert "*.PININFO A:I B:I Y:O" in cdl_text
assert ".ENDS" in cdl_text
cdl_cells = netlist_mod.find_cells(cdl_path)
assert len(cdl_cells) == 1
assert cdl_cells[0].name == "my_gate"
assert [p.name for p in cdl_cells[0].ports] == ["A", "B", "Y"]
assert [p.direction for p in cdl_cells[0].ports] == ["INPUT", "INPUT", "OUTPUT"]
print("PASS: create_new_cdl_file writes a real .SUBCKT/*.PININFO/.ENDS skeleton that round-trips correctly.")

spice_path = tmp_dir / "my_gate.spice"
netlist_mod.create_new_spice_file(spice_path, "my_gate", [("A", "input"), ("Y", "output")])
spice_text = spice_path.read_text()
assert ".subckt my_gate A Y" in spice_text
assert "PININFO" not in spice_text, "real SPICE files never carry *.PININFO -- honestly matched here"
assert ".ends" in spice_text
spice_cells = netlist_mod.find_cells(spice_path)
assert len(spice_cells) == 1
assert [p.name for p in spice_cells[0].ports] == ["A", "Y"]
assert [p.direction for p in spice_cells[0].ports] == ["", ""], "SPICE ports honestly carry no direction"
print("PASS: create_new_spice_file writes a real .subckt/.ends skeleton with deliberately no *.PININFO.")

empty_cdl = tmp_dir / "empty.cdl"
netlist_mod.create_new_cdl_file(empty_cdl, "empty_cell", None)
assert ".SUBCKT empty_cell" in empty_cdl.read_text()
assert "PININFO" not in empty_cdl.read_text()
print("PASS: create_new_cdl_file with no known ports writes an honestly empty port list, no PININFO line.")

try:
    netlist_mod.create_new_cdl_file(cdl_path, "my_gate", [])
    raise AssertionError("expected FileExistsError")
except FileExistsError:
    pass
print("PASS: create_new_cdl_file refuses to overwrite an existing real file.")

lib_path = tmp_dir / "my_gate.lib"
liberty_mod.create_new_liberty_file(lib_path, "my_gate", [("A", "input"), ("B", "input"), ("Y", "output")])
lib_text = lib_path.read_text()
assert "library (my_gate) {" in lib_text
assert "cell (my_gate) {" in lib_text
assert "pin (A) {" in lib_text and "direction : input;" in lib_text
assert "pin (Y) {" in lib_text and "direction : output;" in lib_text
lib_cells = liberty_mod.find_cells(lib_path)
assert len(lib_cells) == 1
assert lib_cells[0].name == "my_gate"
pins_by_name = {p.name: p.direction for p in lib_cells[0].pins}
assert pins_by_name == {"A": "input", "B": "input", "Y": "output"}
print("PASS: create_new_liberty_file writes a real library/cell/pin skeleton that round-trips correctly.")

empty_lib = tmp_dir / "empty.lib"
liberty_mod.create_new_liberty_file(empty_lib, "empty_cell", None)
empty_lib_cells = liberty_mod.find_cells(empty_lib)
assert len(empty_lib_cells) == 1 and empty_lib_cells[0].pins == []
print("PASS: create_new_liberty_file with no known ports writes a real, empty-pin cell that still parses.")

# --- Full GUI flow: a project cell with only a hand-authored xschem
# symbol (real pin syntax, confirmed against a real IHP .sym) gets its
# real pins carried into newly Created CDL/SPICE/Liberty views, landing
# under libraries/<library>/ like every other Library-Manager-created
# view kind here (unlike Verilog/Verilog-A's own user_models/ default) ---
registry_path = li_mod.registry_path(PROJECT_ROOT)
registry_path.unlink(missing_ok=True)
shutil.rmtree(PROJECT_ROOT / lmv_mod.LIBRARIES_DIRNAME, ignore_errors=True)

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()
lmv = app.library_manager_view

li_mod.register_library(PROJECT_ROOT, "my_net_lib")
sym_dir = PROJECT_ROOT / lmv_mod.LIBRARIES_DIRNAME / "my_net_lib"
sym_dir.mkdir(parents=True)
sym_path = sym_dir / "my_net_cell.sym"
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
li_mod.register_entry(PROJECT_ROOT, "my_net_lib", "my_net_cell", "xschem_symbol", sym_path)

lmv.refresh_libraries()
root.update()
lmv.library_tree.selection_set("my_net_lib")
root.update()
lmv.cell_tree.selection_set("my_net_cell")
root.update()
assert "xschem_symbol" in lmv._entries
print("PASS: the hand-authored symbol + registered entry shows up in the real GUI.")

assert "cdl" in li_mod.CREATABLE_VIEW_KINDS
assert "spice" in li_mod.CREATABLE_VIEW_KINDS
assert "liberty" in li_mod.CREATABLE_VIEW_KINDS

lmv._create_view("cdl")
root.update()
cdl_created_path = sym_dir / "my_net_cell.cdl"
assert cdl_created_path.is_file(), f"expected a real file at {cdl_created_path}"
assert lmv._entries["cdl"].path == cdl_created_path
assert lmv._entries["cdl"].source == "registered"
cdl_created_text = cdl_created_path.read_text()
assert ".SUBCKT my_net_cell IN OUT" in cdl_created_text
assert "*.PININFO IN:I OUT:O" in cdl_created_text
print("PASS: Create for CDL pulls the real, correct pins (IN, OUT) from the cell's own xschem symbol, "
      "including a real *.PININFO comment.")

lmv._create_view("spice")
root.update()
spice_created_path = sym_dir / "my_net_cell.spice"
assert spice_created_path.is_file()
spice_created_text = spice_created_path.read_text()
assert ".subckt my_net_cell IN OUT" in spice_created_text
assert "PININFO" not in spice_created_text
print("PASS: Create for SPICE also pulls the same real pins, with no *.PININFO (matching real SPICE files).")

lmv._create_view("liberty")
root.update()
lib_created_path = sym_dir / "my_net_cell.lib"
assert lib_created_path.is_file()
lib_created_text = lib_created_path.read_text()
assert "cell (my_net_cell) {" in lib_created_text
assert "pin (IN) {" in lib_created_text and "direction : input;" in lib_created_text
assert "pin (OUT) {" in lib_created_text and "direction : output;" in lib_created_text
print("PASS: Create for Liberty also pulls the same real pins into real pin/direction blocks.")

# --- The default create path for these three lands under
# libraries/<library>/, not user_models/ -- unlike Verilog/Verilog-A ---
assert cdl_created_path.parent == sym_dir
assert spice_created_path.parent == sym_dir
assert lib_created_path.parent == sym_dir
print("PASS: CDL/SPICE/Liberty Create defaults land under libraries/<library>/, matching xschem/Qucs-S/mag.")

root.destroy()

# --- cleanup ---
registry_path.unlink(missing_ok=True)
shutil.rmtree(PROJECT_ROOT / lmv_mod.LIBRARIES_DIRNAME, ignore_errors=True)
shutil.rmtree(tmp_dir, ignore_errors=True)

print("ALL CDL/SPICE/LIBERTY EDITOR TESTS PASS")

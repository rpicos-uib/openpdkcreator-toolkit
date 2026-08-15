import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path
import shutil

from openpdkcreator.gui.app import App
from openpdkcreator import export as export_mod
from openpdkcreator.ihp import library_index as li_mod
from openpdkcreator.gui import library_manager_view as lmv_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
PROJECT_ROOT = export_mod.PROJECT_ROOT

# Clean any leftover registry/libraries/ dir from a prior interrupted run.
registry_path = li_mod.registry_path(PROJECT_ROOT)
registry_path.unlink(missing_ok=True)
shutil.rmtree(PROJECT_ROOT / lmv_mod.LIBRARIES_DIRNAME, ignore_errors=True)

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

lmv = app.library_manager_view

# --- Real libraries populate on load ---
lib_ids = lmv.library_tree.get_children()
print("libraries:", lib_ids)
assert set(lib_ids) == {"sg13g2_io", "sg13g2_pr", "sg13g2_sram", "sg13g2_stdcell"}
print("PASS: Library Manager tab lists all 4 real families on load.")

# --- Selecting a real library populates real cells; selecting a real
# cell populates real views with real, correct paths ---
lmv.library_tree.selection_set("sg13g2_stdcell")
root.update()
assert "sg13g2_inv_1" in lmv.cell_tree.get_children()
lmv.cell_tree.selection_set("sg13g2_inv_1")
root.update()
assert lmv.views_header_var.get() == "sg13g2_stdcell / sg13g2_inv_1"
assert "xschem_symbol" in lmv._entries
assert lmv._entries["xschem_symbol"].source == "real"
print("PASS: real library -> real cell -> real views, end to end through the actual GUI.")

# --- New Library... (mock the blocking simpledialog) ---
import openpdkcreator.gui.library_manager_view as lmv_module
original_askstring = lmv_module.simpledialog.askstring
lmv_module.simpledialog.askstring = lambda *a, **kw: "my_test_lib"
try:
    lmv._new_library()
finally:
    lmv_module.simpledialog.askstring = original_askstring
root.update()
assert "my_test_lib" in lmv.library_tree.get_children()
print("PASS: New Library... registers and shows a real, new, empty project library.")

# --- New Cell... (mock both blocking dialogs: the name prompt and the
# view-kind choice Toplevel) ---
lmv.library_tree.selection_set("my_test_lib")
root.update()
original_ask_kind = lmv._ask_creatable_view_kind
lmv._ask_creatable_view_kind = lambda *a, **kw: "xschem_symbol"
try:
    lmv_module.simpledialog.askstring = lambda *a, **kw: "my_memristor_cell"
    lmv._new_cell()
finally:
    lmv_module.simpledialog.askstring = original_askstring
    lmv._ask_creatable_view_kind = original_ask_kind
root.update()

created_path = PROJECT_ROOT / lmv_mod.LIBRARIES_DIRNAME / "my_test_lib" / "my_memristor_cell.sym"
assert created_path.is_file(), f"expected a real file at {created_path}"
assert "my_memristor_cell" in lmv.cell_tree.get_children()
lmv.cell_tree.selection_set("my_memristor_cell")
root.update()
assert lmv._entries["xschem_symbol"].path == created_path
assert lmv._entries["xschem_symbol"].source == "registered"
print(f"PASS: New Cell... creates a real, valid xschem symbol at {created_path} and registers it.")

# --- Create for a second, still-absent view kind on the same cell ---
lmv._create_view("xschem_schematic")
root.update()
sch_path = PROJECT_ROOT / lmv_mod.LIBRARIES_DIRNAME / "my_test_lib" / "my_memristor_cell.sch"
assert sch_path.is_file()
assert lmv._entries["xschem_schematic"].path == sch_path
print("PASS: Create adds a second real view to the same registered cell.")

# --- A non-creatable, absent view kind shows the honest gap, not a button ---
lmv.refresh_views()
root.update()
assert "lef" not in lmv._entries
print("PASS: LEF (no real create-from-scratch support) stays honestly absent for the new cell.")

# --- resolve_launch wiring: Open buttons build the correct, real argv
# without actually blocking on a launched GUI window. Mock check_tool
# (not subprocess.Popen globally -- check_tool's own real version-check
# also goes through subprocess.run/Popen internally, so a blanket
# subprocess.Popen patch collides with that unrelated call and breaks
# it with a confusing TypeError) so only our own, final launch-time
# subprocess.Popen(argv, cwd=cwd) call needs mocking.
import subprocess as subprocess_mod
import shutil as shutil_mod
from openpdkcreator import eda_tools as eda_tools_mod

original_check_tool = eda_tools_mod.check_tool


def _fast_check_tool(tool):
    for candidate in tool.check_commands:
        found_path = shutil_mod.which(candidate)
        if found_path:
            return eda_tools_mod.ToolStatus(tool=tool, found=True, path=found_path, version=None)
    return eda_tools_mod.ToolStatus(tool=tool, found=False, path=None, version=None)


eda_tools_mod.check_tool = _fast_check_tool

launched = []
original_popen = subprocess_mod.Popen
subprocess_mod.Popen = lambda argv, cwd=None: launched.append((argv, cwd))
try:
    lmv._open_xschem(lmv._entries["xschem_symbol"])
finally:
    subprocess_mod.Popen = original_popen
argv, cwd = launched[-1]
print("xschem launch argv:", argv)
assert argv[-1] == str(created_path)
assert argv[0].endswith("xschem")
print("PASS: Open in xschem resolves a real argv pointed at the real, just-created symbol file.")

lmv.library_tree.selection_set("sg13g2_stdcell")
root.update()
lmv.cell_tree.selection_set("sg13g2_inv_1")
root.update()
launched.clear()
subprocess_mod.Popen = lambda argv, cwd=None: launched.append((argv, cwd))
try:
    lmv._open_klayout(lmv._entries["gds"])
finally:
    subprocess_mod.Popen = original_popen
argv2, cwd2 = launched[-1]
print("klayout launch argv:", argv2)
assert argv2[-1] == str(lmv._entries["gds"].path)
assert "-l" in argv2
print("PASS: Open in KLayout resolves a real argv (real .lyp + the real, per-cell .gds).")

launched.clear()
subprocess_mod.Popen = lambda argv, cwd=None: launched.append((argv, cwd))
try:
    lmv._open_magic_gds(lmv._entries["gds"])
finally:
    subprocess_mod.Popen = original_popen
    eda_tools_mod.check_tool = original_check_tool
argv3, cwd3 = launched[-1]
print("magic launch argv:", argv3)
assert argv3[0].endswith("magic")
assert "-rcfile" in argv3
tcl_script_path = Path(argv3[-1])
tcl_text = tcl_script_path.read_text()
print("generated Tcl script:\n" + tcl_text)
assert "gds read" in tcl_text and str(lmv._entries["gds"].path) in tcl_text
assert "load sg13g2_inv_1" in tcl_text
tcl_script_path.unlink()
print("PASS: Open in Magic generates a real, correct 2-line GDS-loading Tcl script and launches with it.")

# --- Add...: registers a real, existing, external file for a view
# kind with NO real create-from-scratch support (LEF) ---
external_lef = Path("/tmp/external_hand_authored_cell.lef")
external_lef.write_text("MACRO my_memristor_cell\nEND my_memristor_cell\n")
lmv.library_tree.selection_set("my_test_lib")
root.update()
lmv.cell_tree.selection_set("my_memristor_cell")
root.update()
original_askopenfilename = lmv_module.filedialog.askopenfilename
lmv_module.filedialog.askopenfilename = lambda *a, **kw: str(external_lef)
try:
    lmv._add_view("lef")
finally:
    lmv_module.filedialog.askopenfilename = original_askopenfilename
root.update()
assert lmv._entries["lef"].path == external_lef
assert lmv._entries["lef"].source == "registered"
print("PASS: Add... registers a real, external file for LEF (no real create-from-scratch support) by location alone.")
external_lef.unlink()

# --- Automatic tracking: a file some other tool wrote directly into
# this library's own default directory is picked up on the next
# refresh, with no explicit Add... click ---
auto_path = PROJECT_ROOT / lmv_mod.LIBRARIES_DIRNAME / "my_test_lib" / "externally_saved_cell.sym"
auto_path.write_text("v {xschem version=3.4.4 file_version=1.2}\n")
lmv.refresh_cells()
root.update()
assert "externally_saved_cell" in lmv.cell_tree.get_children()
lmv.cell_tree.selection_set("externally_saved_cell")
root.update()
assert lmv._entries["xschem_symbol"].path == auto_path
assert lmv._entries["xschem_symbol"].source == "registered"
assert "Automatically tracked" in lmv.status_var.get()
print("PASS: a file written directly into the library's own directory is automatically tracked on refresh.")

root.destroy()

# --- cleanup ---
registry_path.unlink(missing_ok=True)
shutil.rmtree(PROJECT_ROOT / lmv_mod.LIBRARIES_DIRNAME, ignore_errors=True)

print("ALL LIBRARY MANAGER VIEW TESTS PASS")

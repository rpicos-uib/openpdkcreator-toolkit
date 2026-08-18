import sys
sys.path.insert(0, "/foss/designs")
import shutil
import tkinter as tk
from pathlib import Path

from openpdkcreator import export as export_mod
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

if export_mod.EXPORT_ROOT.is_dir():
    shutil.rmtree(export_mod.EXPORT_ROOT)

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

chv = app.cell_hub_view
chv.family_var.set("sg13g2_stdcell")
chv._refresh_cells()
root.update()
chv.cells_tree.selection_set("sg13g2_a21o_1")
chv._on_cell_select()
root.update()
cv = chv.current_cell

# Edit CDL ports live via the actual dialog machinery (construct the
# PortEditor the dialog would, without the blocking wait_window).
from openpdkcreator.gui.port_editor import PortEditor
from openpdkcreator.pdklib import netlist as netlist_mod

cdl_editor = PortEditor(root, port_factory=lambda name: netlist_mod.NetlistPort(name=name))
cdl_editor.set_ports(cv.cdl_cell.ports)
root.update()
cdl_port = cv.cdl_cell.ports[0]
cdl_port.direction = "INOUT" if cdl_port.direction != "INOUT" else "INPUT"

app._export_netlist_files()
root.update()
print("Netlist export status:", app.status.get())
cdl_export = export_mod.export_path_for(PDK_ROOT, cv.cdl_source)
from openpdkcreator.pdklib import netlist as nl
reexported = nl.find_cells(cdl_export)
re_cell = next(c for c in reexported if c.name == "sg13g2_a21o_1")
re_port = next(p for p in re_cell.ports if p.name == cdl_port.name)
assert re_port.direction == cdl_port.direction
print("PASS: Export > Export Edited CDL/SPICE Ports reflects the real edit.")

# Verilog
from openpdkcreator.pdklib import verilog as verilog_mod
v_editor = PortEditor(root, port_factory=lambda name: verilog_mod.VerilogPort(name=name), has_width=True)
v_editor.set_ports(cv.verilog_module.ports)
root.update()
v_port = cv.verilog_module.ports[0]
v_port.direction = "inout"

app._export_verilog_files()
root.update()
print("Verilog export status:", app.status.get())
v_export = export_mod.export_path_for(PDK_ROOT, cv.verilog_source)
reexported_v = verilog_mod.find_modules(v_export)
re_module = next(m for m in reexported_v if m.name == "sg13g2_a21o_1")
re_vport = next(p for p in re_module.ports if p.name == v_port.name)
assert re_vport.direction == "inout"
print("PASS: Export > Export Edited Verilog Ports reflects the real edit.")

if export_mod.EXPORT_ROOT.is_dir():
    shutil.rmtree(export_mod.EXPORT_ROOT)
root.destroy()
print("ALL PASS")

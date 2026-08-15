import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

chv = app.cell_hub_view
chv.family_var.set("sg13g2_stdcell")
chv._refresh_cells()
root.update()

target = "sg13g2_a21o_1"
chv.cells_tree.selection_set(target)
chv._on_cell_select()
root.update()

cv = chv.current_cell
assert cv is not None and cv.cdl_cell is not None
print("CDL ports before:", [(p.name, p.direction) for p in cv.cdl_cell.ports])

# Drive the port editor directly (bypass the modal's wait_window, which
# would block this script) -- construct the PortEditor the same way
# edit_ports_dialog does, without opening an actual Toplevel loop.
from openpdkcreator.gui.port_editor import PortEditor
from openpdkcreator.ihp import netlist as netlist_mod

editor = PortEditor(root, port_factory=lambda name: netlist_mod.NetlistPort(name=name))
editor.set_ports(cv.cdl_cell.ports)
root.update()

port = cv.cdl_cell.ports[0]
original_direction = port.direction
new_direction = "OUTPUT" if original_direction != "OUTPUT" else "INPUT"
editor.port_vars["direction"].set(new_direction)
root.update()
assert port.direction == new_direction, port.direction
print(f"PASS: edited CDL port {port.name} direction {original_direction} -> {port.direction}")

editor._new_port()
root.update()
assert len(cv.cdl_cell.ports) == 7
print(f"PASS: New Port added, count now {len(cv.cdl_cell.ports)}")

editor.ports_tree.selection_set(editor._port_iid(cv.cdl_cell.ports[0]))
editor._delete_port()
root.update()
assert len(cv.cdl_cell.ports) == 6
print(f"PASS: Delete Port works, count now {len(cv.cdl_cell.ports)}")

# --- Verilog port editing (with width) ---
chv.family_var.set("sg13g2_sram")
chv.show_all_var.set(False)
chv._refresh_cells()
root.update()
sram_target = "RM_IHPSG13_1P_1024x16_c2_bm_bist"
assert sram_target in chv.cells_tree.get_children()
chv.cells_tree.selection_set(sram_target)
chv._on_cell_select()
root.update()
sram_cv = chv.current_cell
assert sram_cv.verilog_module is not None, "real bug regression: multi-line SRAM verilog header not found"
print(f"PASS: SRAM top-level macro's Verilog module found ({len(sram_cv.verilog_module.ports)} ports) -- multi-line header bug fixed.")
addr_port = next(p for p in sram_cv.verilog_module.ports if p.name == "A_ADDR")
assert addr_port.direction == "input" and addr_port.width == "[9:0]", (addr_port.direction, addr_port.width)
print(f"PASS: real bus port A_ADDR correctly parsed: direction={addr_port.direction!r} width={addr_port.width!r}")

# --- Persistence across family switch (the bug this session already knows to check for) ---
chv.family_var.set("sg13g2_stdcell")
chv._refresh_cells()
root.update()
chv.family_var.set("sg13g2_sram")
chv._refresh_cells()
root.update()
chv.cells_tree.selection_set(sram_target)
chv._on_cell_select()
root.update()
re_cv = chv.current_cell
re_addr_port = next(p for p in re_cv.verilog_module.ports if p.name == "A_ADDR")
assert re_addr_port is addr_port, "family switch re-parsed instead of reusing the cached, possibly-edited module"
print("PASS: switching families and back reuses the same cached VerilogModule object (no silent data loss).")

root.destroy()
print("ALL PASS")

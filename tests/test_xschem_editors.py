import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

xv = app.xschem_view
sym_pane = xv._symbols
sch_pane = xv._schematics

# --- Symbols: Pins editing via PortEditor ---
target = "libs.tech/xschem/sg13g2_stdcells/sg13g2_inv_1.sym"
sym_pane.file_var.set(target)
sym_pane._refresh_all()
root.update()

pins = sym_pane.pins_editor.ports
assert len(pins) == 2, pins
a_pin = next(p for p in pins if p.name == "A")
sym_pane.pins_editor.set_ports(pins)  # ensure tree populated
iid = sym_pane.pins_editor._port_iid(a_pin)
sym_pane.pins_editor.ports_tree.selection_set(iid)
sym_pane.pins_editor._on_port_select()
root.update()
sym_pane.pins_editor.port_vars["direction"].set("inout")
root.update()
assert a_pin.direction == "inout"
print("PASS: xschem Symbols Pins editor commits an in-memory edit.")

# Verify it persists across a file switch and back (shared App cache).
sym_pane.file_var.set("libs.tech/xschem/sg13g2_pr/sg13_lv_nmos.sym")
sym_pane._refresh_all()
root.update()
sym_pane.file_var.set(target)
sym_pane._refresh_all()
root.update()
reloaded_a = next(p for p in sym_pane.pins_editor.ports if p.name == "A")
assert reloaded_a.direction == "inout"
print("PASS: pin edit survives switching xschem .sym files and back (App cache).")

# --- Schematics: Instances editing (name + net label) ---
sch_target = "libs.tech/xschem/sg13g2_stdcells/sg13g2_inv_1.sch"
sch_pane.file_var.set(sch_target)
sch_pane._refresh_all()
root.update()

mp0_iid = next(iid for iid, inst in sch_pane._instance_by_iid.items() if inst.name == "MP0")
sch_pane.instances_tree.selection_set(mp0_iid)
sch_pane._on_instance_select()
root.update()
sch_pane.instance_name_var.set("MP0_RENAMED")
root.update()
assert sch_pane.current_instance.name == "MP0_RENAMED"
assert str(sch_pane.instance_label_entry["state"]) == "disabled"  # not a pin instance
print("PASS: non-pin instance name edit committed, net-label field disabled.")

p1_iid = next(iid for iid, inst in sch_pane._instance_by_iid.items() if inst.name == "p1")
sch_pane.instances_tree.selection_set(p1_iid)
sch_pane._on_instance_select()
root.update()
assert str(sch_pane.instance_label_entry["state"]) == "normal"
sch_pane.instance_label_var.set("YOUT")
root.update()
assert sch_pane.current_instance.pin_label == "YOUT"
print("PASS: pin instance net-label edit committed, field enabled correctly.")

# --- Schematics: Wires editing (label) + delete ---
first_wire_iid = next(iter(sch_pane._wire_by_iid))
sch_pane.wires_tree.selection_set(first_wire_iid)
sch_pane._on_wire_select()
root.update()
sch_pane.wire_label_var.set("RENAMED_NET")
root.update()
assert sch_pane.current_wire.label == "RENAMED_NET"
print("PASS: wire label edit committed.")

wires_before = len(sch_pane.current.wires)
sch_pane._delete_wire()
root.update()
assert len(sch_pane.current.wires) == wires_before - 1
print("PASS: Delete Wire removed the wire from the in-memory schematic.")

instances_before = len(sch_pane.current.instances)
sch_pane.instances_tree.selection_set(mp0_iid)
sch_pane._on_instance_select()
sch_pane._delete_instance()
root.update()
assert len(sch_pane.current.instances) == instances_before - 1
print("PASS: Delete Instance removed the instance from the in-memory schematic.")

# --- Real write-back export for both domains ---
import tempfile
from openpdkcreator import export as export_mod

xv.commit_pending_edits()
with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    sym_written = export_mod.export_xschem_symbols(PDK_ROOT, app.xschem_symbol_cache, dest_root=export_dir)
    sch_written = export_mod.export_xschem_schematics(PDK_ROOT, app.xschem_schematic_cache, dest_root=export_dir)
    sym_path = [p for p in sym_written if p.name == "sg13g2_inv_1.sym"][0]
    sch_path = [p for p in sch_written if p.name == "sg13g2_inv_1.sch"][0]
    sym_text = sym_path.read_text()
    sch_text = sch_path.read_text()
    assert "dir=inout" in sym_text
    assert "MP0_RENAMED" not in sch_text  # deleted, should be entirely absent
    assert "lab=YOUT" in sch_text
    assert "RENAMED_NET" not in sch_text  # the wire carrying it was deleted
    print("PASS: real .sym/.sch write-back exports reflect all edits/deletions correctly.")

root.destroy()
print("ALL PASS")

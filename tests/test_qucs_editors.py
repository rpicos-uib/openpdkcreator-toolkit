import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

qv = app.qucs_view
comp_pane = qv._components
sym_pane = qv._symbols

# --- Components: Parameter value editing ---
target = "libs.tech/qucs-s/symbols/nmos.xml"
comp_pane.file_var.set(target)
comp_pane._refresh_all()
root.update()

w_iid = next(iid for iid, p in comp_pane._param_by_iid.items() if p.raw_attrs.get("name") == "w")
comp_pane.params_tree.selection_set(w_iid)
comp_pane._on_param_select()
root.update()
assert comp_pane.param_kind_var.get() == "default_value"
comp_pane.param_value_var.set("0.20u")
root.update()
w_param = comp_pane._param_by_iid[w_iid]
assert w_param.raw_attrs["default_value"] == "0.20u"
print("PASS: Components Parameter default_value edit committed.")

# Persist across file switch and back (App cache).
comp_pane.file_var.set("libs.tech/qucs-s/symbols/pmos.xml" if "libs.tech/qucs-s/symbols/pmos.xml" in comp_pane.files else sorted(comp_pane.files)[0])
comp_pane._refresh_all()
root.update()
comp_pane.file_var.set(target)
comp_pane._refresh_all()
root.update()
w_param2 = next(p for p in comp_pane.current.parameters if p.raw_attrs.get("name") == "w")
assert w_param2.raw_attrs["default_value"] == "0.20u"
print("PASS: Components Parameter edit survives switching files and back.")

# --- Symbols: PortSym editing (x/y/type/angle/condition) + New/Delete ---
sym_target = "libs.tech/qucs-s/symbols/Mos.sym"
sym_pane.file_var.set(sym_target)
sym_pane._refresh_all()
root.update()

first_iid = next(iter(sym_pane._port_by_iid))
sym_pane.ports_tree.selection_set(first_iid)
sym_pane._on_port_select()
root.update()
sym_pane.port_vars["angle"].set("90")
root.update()
port = sym_pane._port_by_iid[first_iid]
assert port.angle == 90
print("PASS: Symbols PortSym angle edit committed.")

before_count = len(sym_pane.current.ports)
sym_pane._new_port()
root.update()
assert len(sym_pane.current.ports) == before_count + 1
new_port = sym_pane.current_port
assert new_port.line_no == 0
sym_pane._delete_port()
root.update()
assert len(sym_pane.current.ports) == before_count
print("PASS: Symbols New/Delete Port works correctly.")

# --- Real write-back export for both domains (including the CRLF file) ---
import tempfile
from openpdkcreator import export as export_mod

qv.commit_pending_edits()
with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    sym_written = export_mod.export_qucs_symbols(PDK_ROOT, app.qucs_symbol_cache, dest_root=export_dir)
    comp_written = export_mod.export_qucs_components(PDK_ROOT, app.qucs_component_cache, dest_root=export_dir)
    sym_path = [p for p in sym_written if p.name == "Mos.sym"][0]
    comp_path = [p for p in comp_written if p.name == "nmos.xml"][0]
    assert "angle=\"90\"" in sym_path.read_text()
    assert 'default_value="0.20u"' in comp_path.read_text()
    print("PASS: real Qucs-S .sym/.xml write-back exports reflect edits correctly.")

root.destroy()
print("ALL PASS")

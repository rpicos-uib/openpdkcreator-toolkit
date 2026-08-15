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

print("component files:", len(comp_pane.files))
print("symbol files:", len(sym_pane.files))
assert len(comp_pane.files) == 34
assert len(sym_pane.files) == 22

target = "libs.tech/qucs-s/symbols/nmos.xml"
assert target in comp_pane.files
comp_pane.file_var.set(target)
comp_pane._refresh_all()
root.update()

overview = {row[0]: row[1] for row in (comp_pane.overview_tree.item(i)["values"] for i in comp_pane.overview_tree.get_children())}
print("overview:", overview)
assert overview["spice_model"] == "sg13_lv_nmos"
assert overview["symbol resolved?"] == "yes"

params = [comp_pane.params_tree.item(i)["values"] for i in comp_pane.params_tree.get_children()]
print("params:", params)
assert len(params) == 7
param_names = {p[0] for p in params}
assert "w" in param_names and "l" in param_names

netlists = {row[0]: row[1] for row in (comp_pane.netlists_tree.item(i)["values"] for i in comp_pane.netlists_tree.get_children())}
print("netlist kinds:", list(netlists.keys()))
assert "NgspiceNetlist" in netlists and "CDLNetlist" in netlists
assert netlists["NgspiceNetlist"]  # non-empty real template text

sym_target = "libs.tech/qucs-s/symbols/Mos.sym"
assert sym_target in sym_pane.files
sym_pane.file_var.set(sym_target)
sym_pane._refresh_all()
root.update()

ports = [sym_pane.ports_tree.item(i)["values"] for i in sym_pane.ports_tree.get_children()]
print("Mos.sym ports:", ports)
assert len(ports) == 8
hinted = [p for p in ports if p[5]]
print("hinted ports:", hinted)
assert len(hinted) == 8  # Mos.sym's own real D/G/S/B comments, confirmed earlier
assert {p[5] for p in hinted} == {"D", "G", "S", "B"}
print("summary:", sym_pane.summary_var.get())

root.destroy()
print("ALL PASS")

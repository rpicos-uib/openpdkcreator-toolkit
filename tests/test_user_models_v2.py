import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
PROJECT_ROOT = Path("/foss/designs")

# --- Self-contained fixtures: this test needs exactly 2 real Verilog
# modules (for batch relink) plus 1 real Verilog-A module named
# "my_custom_res" in a file "my_res.va" (for Link All Auto-Matches,
# Edit Ports write-back, and OSDI snippet generation) -- write them
# fresh here rather than depending on whatever a previous, unrelated
# session may have left behind in user_models/.
verilog_dir = PROJECT_ROOT / "user_models" / "verilog"
veriloga_dir = PROJECT_ROOT / "user_models" / "veriloga"
verilog_dir.mkdir(parents=True, exist_ok=True)
veriloga_dir.mkdir(parents=True, exist_ok=True)
fixture_paths = [
    verilog_dir / "my_and2_a.v",
    verilog_dir / "my_and2_b.v",
    veriloga_dir / "my_res.va",
]
for path, name in zip(fixture_paths, ("my_and2_a", "my_and2_b", "my_custom_res")):
    path.write_text(f"module {name}(A, B, Y);\ninput A;\ninput B;\noutput Y;\nendmodule\n")
links_path = PROJECT_ROOT / "user_models" / "links.yaml"
if links_path.is_file():
    links_path.unlink()

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

umv = app.user_models_view
umv.refresh()
root.update()

rows = umv.tree.get_children()
print("rows:", rows)
assert len(rows) == 3, rows

# --- 7b: batch relink -- select the two Verilog rows, link both to the
# same real cell name in one Save Link.
v_rows = [iid for iid in rows if umv.row_by_iid[iid][0].kind == "verilog"]
assert len(v_rows) == 2, v_rows
umv.tree.selection_set(v_rows)
umv._on_select()
assert umv.cell_name_var.get() == "", "batch mode should not prefill a single link"
umv.cell_name_var.set("sg13g2_and2_1")
umv._save_link()
root.update()

links_path = Path("/foss/designs/user_models/links.yaml")
text = links_path.read_text()
print("links.yaml after batch save:\n", text)
assert text.count("sg13g2_and2_1") == 2, text

rows2 = umv.tree.get_children()
for iid in rows2:
    model_file, module = umv.row_by_iid[iid]
    if model_file.kind == "verilog":
        values = umv.tree.item(iid)["values"]
        assert values[4] == "sg13g2_and2_1", values
print("PASS: batch relink applied to both Verilog modules.")

# --- 7b: Link All Auto-Matches -- the veriloga row has no explicit
# link yet; freeze it.
umv._link_all_auto()
root.update()
text2 = links_path.read_text()
print("links.yaml after Link All Auto-Matches:\n", text2)
assert "my_custom_res" in text2
print("PASS: Link All Auto-Matches froze the veriloga row's auto-match.")

# Re-running Link All Auto-Matches should now be a no-op (everything's explicit).
before = links_path.read_text()
umv._link_all_auto()
after = links_path.read_text()
assert before == after, "Link All Auto-Matches should be idempotent once everything is explicit"
print("PASS: Link All Auto-Matches is idempotent.")

# --- 7a: Edit Ports on the veriloga module -- add a new port, verify
# it's written back to the real .va file directly.
va_iid = [iid for iid in umv.tree.get_children() if umv.row_by_iid[iid][0].kind == "veriloga"][0]
print("DEBUG va_iid:", repr(va_iid))
umv.tree.selection_set(va_iid)
root.update()
print("DEBUG selection after set:", umv.tree.selection())
umv._on_select()
print("DEBUG edit_ports_button state:", repr(umv.edit_ports_button["state"]), type(umv.edit_ports_button["state"]))
print("DEBUG osdi_button state:", repr(umv.osdi_button["state"]), type(umv.osdi_button["state"]))
print("DEBUG state() method:", umv.edit_ports_button.state())
assert str(umv.edit_ports_button["state"]) == "normal"
assert str(umv.osdi_button["state"]) == "normal"

model_file, module = umv.row_by_iid[va_iid]
from openpdkcreator.pdklib.verilog import VerilogPort
module.ports.append(VerilogPort(name="new_port", direction="input", width=""))

import openpdkcreator.gui.user_models_view as umv_mod

# edit_ports_dialog is modal; monkeypatch it out so the test doesn't
# block on a Toplevel, while still exercising the real write-back call
# _edit_ports makes right after the dialog would have closed.
original_dialog = umv_mod.edit_ports_dialog
umv_mod.edit_ports_dialog = lambda *a, **kw: None
try:
    umv._edit_ports()
finally:
    umv_mod.edit_ports_dialog = original_dialog
root.update()

va_path = Path("/foss/designs/user_models/veriloga/my_res.va")
va_text = va_path.read_text()
print("my_res.va after port edit:\n", va_text)
assert "new_port" in va_text
print("PASS: Edit Ports wrote the new port back to the real .va file.")

# --- 7c: OSDI snippet generation for the (still-present) veriloga row.
rows3 = umv.tree.get_children()
va_iid2 = [iid for iid in rows3 if umv.row_by_iid[iid][0].kind == "veriloga"][0]
umv.tree.selection_set(va_iid2)
umv._on_select()

from openpdkcreator.pdklib import user_models as user_models_mod
mf, mod = umv.row_by_iid[va_iid2]
snippet = user_models_mod.osdi_snippet(umv._project_root(), mf, mod)
print("OSDI snippet:\n", snippet)
assert "openvaf" in snippet and "osdi '" in snippet and "my_custom_res" in snippet
print("PASS: OSDI snippet references the real module/file correctly.")

# Verify a plain Verilog module is correctly rejected (no real ngspice
# story for digital Verilog in this PDK's own toolchain).
v_iid = [iid for iid in rows3 if umv.row_by_iid[iid][0].kind == "verilog"][0]
mf_v, mod_v = umv.row_by_iid[v_iid]
try:
    user_models_mod.osdi_snippet(umv._project_root(), mf_v, mod_v)
    raise AssertionError("expected ValueError for a plain Verilog module")
except ValueError:
    print("PASS: OSDI snippet correctly refuses a plain Verilog module.")

root.destroy()
for path in fixture_paths:
    path.unlink(missing_ok=True)
if links_path.is_file():
    links_path.unlink()
print("ALL PASS")

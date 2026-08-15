import sys
sys.path.insert(0, "/foss/designs")
import shutil
import tkinter as tk
from pathlib import Path

from openpdkcreator import export as export_mod
from openpdkcreator import project_io
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

if export_mod.EXPORT_ROOT.is_dir():
    shutil.rmtree(export_mod.EXPORT_ROOT)
save_path = project_io.save_path_for(PDK_ROOT)
if save_path.is_file():
    save_path.unlink()

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

# --- Settings > Tools sub-tab ---
assert hasattr(app, "tools_view")
assert len(app.tools_view.tree.get_children()) > 0
print(f"Tools tab: {app.tools_view.summary_var.get()}")
# pick any tool and confirm the detail pane renders without error
first_id = app.tools_view.tree.get_children()[0]
app.tools_view.tree.selection_set(first_id)
app.tools_view._on_select()
root.update()
print(f"Detail for {first_id}: {app.tools_view.detail_var.get()}")
detail_text = app.tools_view.install_text.get("1.0", "end")
assert detail_text.strip()
print("PASS: Tools tab lists real tools and shows real detail text.")

# --- Edit a LEF pin via the LEF tab, then export via the File menu action ---
app.lef_view.file_var.set(sorted(app.lef_view.lef_files)[0])
app.lef_view._refresh_all()
root.update()
lef_relpath = app.lef_view.file_var.get()
macro = app.lef_view.current.macros[0]
app.lef_view.macros_tree.selection_set(macro.name)
app.lef_view._on_macro_select()
root.update()
pin = app.lef_view.pin_editor.current_pin
original_direction = pin.direction
new_direction = "OUTPUT" if original_direction != "OUTPUT" else "INPUT"
app.lef_view.pin_editor.pin_vars["direction"].set(new_direction)
root.update()
assert pin.direction == new_direction

app._export_lef_files()
root.update()
print(f"Export status: {app.status.get()}")

export_path = export_mod.export_path_for(PDK_ROOT, app.lef_view.lef_files[lef_relpath])
assert export_path.is_file(), export_path
from openpdkcreator.ihp import lef as lef_mod
reexported = lef_mod.parse_lef_file(export_path)
re_macro = next(m for m in reexported.macros if m.name == macro.name)
re_pin = next(p for p in re_macro.pins if p.name == pin.name)
assert re_pin.direction == new_direction, re_pin.direction
print(f"PASS: exported .lef file at {export_path} reflects the real edit ({original_direction} -> {new_direction}).")

# Confirm a file NEVER parsed this session (not in app.lef_cache --
# note CellHubView's own initial family load also parses every real
# .lef file under its first family, so "never visited via the LEF
# combo" isn't the same as "never parsed this session") was not
# exported.
untouched_path = next(p for r, p in app.lef_view.lef_files.items() if p not in app.lef_cache)
untouched_export = export_mod.export_path_for(PDK_ROOT, untouched_path)
assert not untouched_export.exists(), f"a never-parsed file should not have been exported: {untouched_path}"
print(f"PASS: a file never parsed this session ({untouched_path.name}) is correctly not exported.")

root.destroy()
print("ALL PASS")

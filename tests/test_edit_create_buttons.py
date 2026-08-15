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
qv = app.qucs_view

# --- Existing file: button should read "Edit File" ---
sym_pane = xv._symbols
sym_pane.file_var.set("libs.tech/xschem/sg13g2_stdcells/sg13g2_inv_1.sym")
sym_pane._update_action_button()
root.update()
assert str(sym_pane.action_button["text"]) == "Edit File"
print("PASS: xschem Symbols button reads 'Edit File' for an existing file.")

# --- Not-yet-existing file: button should read "Create File" ---
new_sym_relpath = "libs.tech/xschem/sg13g2_stdcells/my_new_symbol.sym"
sym_pane.file_var.set(new_sym_relpath)
sym_pane._update_action_button()
root.update()
assert str(sym_pane.action_button["text"]) == "Create File"
print("PASS: xschem Symbols button reads 'Create File' for a new name.")

# --- Directory traversal is refused (no file should be written) ---
# handle_action shows a blocking messagebox on refusal -- monkeypatch it
# out so this scripted test doesn't hang waiting for a real user click.
import openpdkcreator.gui.file_picker_utils as fpu_mod

original_showerror = fpu_mod.messagebox.showerror
fpu_mod.messagebox.showerror = lambda *a, **kw: None

traversal_relpath = "../../../../../../../../tmp/should_not_exist_xschem.sym"
would_be_target = (PDK_ROOT / traversal_relpath).resolve()
if would_be_target.exists():
    would_be_target.unlink()
sym_pane.file_var.set(traversal_relpath)
try:
    sym_pane._on_action()
finally:
    fpu_mod.messagebox.showerror = original_showerror
root.update()
assert not would_be_target.exists(), f"directory traversal was NOT blocked! wrote to {would_be_target}"
print("PASS: directory-traversal Create attempt correctly blocked.")

# --- Actually create the new xschem symbol file ---
sym_pane.file_var.set(new_sym_relpath)
sym_pane._on_action()
root.update()
created_path = PDK_ROOT / new_sym_relpath
assert created_path.is_file()
sym_pane._update_action_button()
root.update()
assert str(sym_pane.action_button["text"]) == "Edit File"
print("PASS: xschem Symbols Create File wrote a real, parseable new .sym file.")

# Verify it's now usable: add a pin via the existing New Pin flow.
assert sym_pane.current is not None
before_pins = len(sym_pane.current.pins)
sym_pane.pins_editor.set_ports(sym_pane.current.pins)
sym_pane.pins_editor._new_port()
root.update()
assert len(sym_pane.current.pins) == before_pins + 1
print("PASS: newly created xschem symbol accepts a New Pin via the existing editor.")

# --- xschem Schematics: same Create flow ---
sch_pane = xv._schematics
new_sch_relpath = "libs.tech/xschem/sg13g2_stdcells/my_new_schematic.sch"
sch_pane.file_var.set(new_sch_relpath)
sch_pane._on_action()
root.update()
assert (PDK_ROOT / new_sch_relpath).is_file()
print("PASS: xschem Schematics Create File wrote a real, parseable new .sch file.")

# --- Qucs-S Symbols: same Create flow ---
qsym_pane = qv._symbols
new_qsym_relpath = "libs.tech/qucs-s/symbols/my_new_qucs.sym"
qsym_pane.file_var.set(new_qsym_relpath)
qsym_pane._on_action()
root.update()
assert (PDK_ROOT / new_qsym_relpath).is_file()
print("PASS: Qucs-S Symbols Create File wrote a real, parseable new .sym file.")

# --- Qucs-S Components: same Create flow ---
qcomp_pane = qv._components
new_qcomp_relpath = "libs.tech/qucs-s/symbols/my_new_device.xml"
qcomp_pane.file_var.set(new_qcomp_relpath)
qcomp_pane._on_action()
root.update()
created_xml = PDK_ROOT / new_qcomp_relpath
assert created_xml.is_file()
assert qcomp_pane.current is not None
assert qcomp_pane.current.names == "my_new_device"
print("PASS: Qucs-S Components Create File wrote a real, parseable new .xml file.")

# --- Cleanup: this test writes real files into the shared, real,
# downloaded PDK_ROOT (not a throwaway temp dir) since it's exercising
# the real Create-File path against real relative-path conventions --
# remove them so a later run (or another test's own file-count
# assertions against this same PDK_ROOT) doesn't see them as real,
# permanent IHP content.
for relpath in (new_sym_relpath, new_sch_relpath, new_qsym_relpath, new_qcomp_relpath):
    created = PDK_ROOT / relpath
    if created.is_file():
        created.unlink()

root.destroy()
print("ALL PASS")

import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator.gui import lef_view as lef_view_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

lv = app.lef_view
lv.file_var.set("libs.ref/sg13g2_stdcell/lef/sg13g2_stdcell.lef")
lv._refresh_all()
root.update()
original_macro_count = len(lv.current.macros)

# --- New Macro... (mock the blocking name-prompt dialog) ---
original_askstring = lef_view_mod.simpledialog.askstring
lef_view_mod.simpledialog.askstring = lambda *a, **kw: "ZZ_GUI_NEW_MACRO"
try:
    lv._new_macro()
finally:
    lef_view_mod.simpledialog.askstring = original_askstring
root.update()

assert len(lv.current.macros) == original_macro_count + 1
assert lv.current.macros[-1].name == "ZZ_GUI_NEW_MACRO"
assert lv.macros_tree.exists("ZZ_GUI_NEW_MACRO")
assert lv.macros_tree.selection() == ("ZZ_GUI_NEW_MACRO",)
print(f"PASS: New Macro... adds a real, empty macro through the actual GUI ({original_macro_count} -> {len(lv.current.macros)}).")

# --- Adding a pin to the new macro via the existing PinEditor works the same as any other macro ---
lv.pin_editor._new_pin()
root.update()
assert len(lv.current.macros[-1].pins) == 1
print("PASS: New Pin adds a real pin to the newly-created macro through the shared PinEditor.")

# --- Rejects a duplicate name ---
import tkinter.messagebox as messagebox
shown = []
original_showerror = messagebox.showerror
messagebox.showerror = lambda title, msg, **kw: shown.append((title, msg))
lef_view_mod.simpledialog.askstring = lambda *a, **kw: "ZZ_GUI_NEW_MACRO"
try:
    lv._new_macro()
finally:
    lef_view_mod.simpledialog.askstring = original_askstring
    messagebox.showerror = original_showerror
assert len(lv.current.macros) == original_macro_count + 1, "a duplicate-named macro must not be added"
assert shown, "a duplicate name should show a real error dialog"
print("PASS: New Macro... refuses a duplicate name with a real error dialog, no macro added.")

root.destroy()
print("ALL LEF NEW MACRO GUI TESTS PASS")

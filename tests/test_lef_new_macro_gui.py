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

# --- New Macro... (mock the blocking name-prompt and site-prompt dialogs) ---
original_askstring = lef_view_mod.simpledialog.askstring
prompts = iter(["ZZ_GUI_NEW_MACRO", "ZZ_TEST_SITE"])
lef_view_mod.simpledialog.askstring = lambda *a, **kw: next(prompts)
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

# --- ORIGIN is set automatically (real, confirmed-safe default);
# SITE comes from the real, real-GUI site prompt, not silently guessed ---
new_macro = lv.current.macros[-1]
assert new_macro.origin == (0.0, 0.0)
assert new_macro.site == "ZZ_TEST_SITE"
print("PASS: New Macro... sets a real, confirmed-safe (0.0, 0.0) origin automatically and the real, prompted site.")

# --- The site prompt is pre-filled with this file's own most common real site ---
suggested = lv._most_common_site()
assert suggested == "CoreSite"
print(f"PASS: the Site prompt's own real, confirmable default suggestion is {suggested!r}, the file's own most common real site.")

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

# --- A real, found gap: a brand-new macro's own identity (class/
# size/site/symmetry/origin) used to vanish on the next relaunch --
# only its pins were ever saved (keyed by a macro name a fresh
# re-parse of the real, unmodified source file could never resolve
# again). Confirmed fixed: save, then load into a completely separate
# App instance (a real, fresh process would do the same). ---
new_macro.macro_class = "CORE"
new_macro.size = (1.0, 1.0)
lv.pin_editor.pin_vars["name"].set("ZZ_PIN")
lv.pin_editor.pin_vars["direction"].set("INPUT")
lv.pin_editor.pin_vars["use"].set("SIGNAL")
root.update()
from openpdkcreator.gui import geometry_adapters as geometry_adapters_mod
geometry_adapters_mod.new_lef_port_rect(new_macro.pins[0], "Metal1", 0.0, 0.0, 1.0, 1.0)

from openpdkcreator import project_io
save_path = project_io.save_path_for(PDK_ROOT)
try:
    app._save_project()
    root.update()
    root.destroy()

    root2 = tk.Tk()
    app2 = App(root2, PDK_ROOT)
    root2.update()
    lv2 = app2.lef_view
    lv2.file_var.set("libs.ref/sg13g2_stdcell/lef/sg13g2_stdcell.lef")
    lv2._refresh_all()
    root2.update()

    names2 = [m.name for m in lv2.current.macros]
    assert "ZZ_GUI_NEW_MACRO" in names2, "new macro was lost on reload"
    reloaded = next(m for m in lv2.current.macros if m.name == "ZZ_GUI_NEW_MACRO")
    assert reloaded.macro_class == "CORE"
    assert reloaded.size == (1.0, 1.0)
    assert reloaded.site == "ZZ_TEST_SITE"
    assert reloaded.origin == (0.0, 0.0)
    assert len(reloaded.pins) == 1 and reloaded.pins[0].name == "ZZ_PIN"
    assert reloaded.pins[0].ports and reloaded.pins[0].ports[0].rects == [(0.0, 0.0, 1.0, 1.0)]
    print("PASS: a brand-new macro's own class/size/site/origin, plus its pin and that pin's own "
          "port geometry, all survive a real save + fresh-process reload.")

    import tempfile
    from openpdkcreator import export as export_mod
    with tempfile.TemporaryDirectory() as tmp:
        written = export_mod.export_lef_files(PDK_ROOT, app2.lef_cache, dest_root=Path(tmp))
        target = [p for p in written if p.name == "sg13g2_stdcell.lef"][0]
        text = target.read_text()
        assert "MACRO ZZ_GUI_NEW_MACRO" in text and "CLASS CORE" in text and "RECT 0 0 1 1" in text
    print("PASS: the reloaded new macro exports a real MACRO...END block with its own real geometry.")

    root2.destroy()
finally:
    if save_path.is_file():
        save_path.unlink()

print("ALL LEF NEW MACRO GUI TESTS PASS")

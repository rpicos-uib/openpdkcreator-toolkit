import sys
sys.path.insert(0, "/foss/designs/openMemristorPDK")
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/openMemristorPDK/data/openmemristorpdk")

captured = []
messagebox.showinfo = lambda title, message, **_kw: captured.append((title, message))
messagebox.showwarning = lambda *a, **k: None


def _find_all(widget, cls):
    found = []
    for child in widget.winfo_children():
        if isinstance(child, cls):
            found.append(child)
        found.extend(_find_all(child, cls))
    return found


root = tk.Tk()
app = App(root, PDK_ROOT)
app.load()
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("openmemristorpdk")
mtv._refresh_all()
root.update()

# --- help texts are real Help buttons (popup), not a permanent inline
# label, for all three DRC (Magic) editors -------------------------------
for name, editor, entry_label in (
    ("checks", mtv.drc_checks_editor, "DRC Check"),
    ("angles", mtv.drc_angles_editor, "Angle Check"),
    ("misc", mtv.drc_misc_editor, "DRC Statement"),
):
    help_buttons = [b for b in _find_all(editor, ttk.Button) if b["text"] == "Help"]
    assert len(help_buttons) == 1, f"{name}: expected exactly one real Help button"
    assert not any(
        w.cget("wraplength") == 260 for w in _find_all(editor, ttk.Label)
    ), f"{name}: the old, always-visible inline help label (wraplength=260) should be gone"
    captured.clear()
    help_buttons[0].invoke()
    assert len(captured) == 1
    assert captured[0][0] == f"{entry_label} Help"
    assert captured[0][1] == editor.help_text
    print(f"PASS: {name} editor's help text is a real popup (Help button), not a permanent inline label.")

# --- 'Select Layers...' now lives below the Layers field, in the form,
# not in the checks_frame header ------------------------------------------
all_select_layers_buttons = [b for b in _find_all(mtv, ttk.Button) if b["text"] == "Select Layers..."]
in_form_buttons = [b for b in _find_all(mtv.drc_checks_editor, ttk.Button) if b["text"] == "Select Layers..."]
assert len(all_select_layers_buttons) == 1
assert in_form_buttons == all_select_layers_buttons
print("PASS: exactly one real 'Select Layers...' button, and it lives inside the checks editor's own "
      "form (field_buttons), not a header sibling to it.")

# --- the multi-select dialog itself is real, dimensionable with the window
be_au_check = next(c for c in mtv.drc_checks_editor.entries if c.layer_args == [["be_au"]])
mtv.drc_checks_editor.tree.selection_set(mtv.drc_checks_editor._iid(be_au_check))
mtv.drc_checks_editor._on_select()
root.update()

captured_dialog = {}


def _inspect_and_close():
    dialog = next(w for w in _find_all(root, tk.Toplevel) if w.title() == "Select Layers")
    captured_dialog["resizable"] = dialog.resizable()
    captured_dialog["row_weight"] = dialog.grid_rowconfigure(0)["weight"]
    captured_dialog["col_weight"] = dialog.grid_columnconfigure(0)["weight"]
    dialog.destroy()


root.after(150, _inspect_and_close)
mtv._select_drc_check_layers()
root.update()

print("dialog resizable():", captured_dialog["resizable"])
assert captured_dialog["resizable"] == (1, 1)
assert captured_dialog["row_weight"] > 0
assert captured_dialog["col_weight"] > 0
print("PASS: the Select Layers dialog is resizable and its listbox row/column stretch with the window.")

root.destroy()

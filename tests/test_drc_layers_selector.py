import sys
sys.path.insert(0, "/foss/designs/openMemristorPDK")
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/openMemristorPDK/data/openmemristorpdk")

messagebox.showinfo = lambda *a, **k: None
messagebox.showwarning = lambda *a, **k: None


def _find_all(widget, cls):
    found = []
    for child in widget.winfo_children():
        if isinstance(child, cls):
            found.append(child)
        found.extend(_find_all(child, cls))
    return found


def _select_layers_dialog(root):
    return next(w for w in _find_all(root, tk.Toplevel) if w.title() == "Select Layers")


root = tk.Tk()
app = App(root, PDK_ROOT)
app.load()
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("openmemristorpdk")
mtv._refresh_all()
root.update()

# --- width check: union two real types via a real multi-select (the
# Ctrl+click-equivalent: two entries selected in the same Listbox) ---------
be_au_check = next(c for c in mtv.drc_checks_editor.entries if c.layer_args == [["be_au"]])
mtv.drc_checks_editor.tree.selection_set(mtv.drc_checks_editor._iid(be_au_check))
mtv.drc_checks_editor._on_select()
root.update()


def _drive_width_union():
    dialog = _select_layers_dialog(root)
    listbox = _find_all(dialog, tk.Listbox)[0]
    items = listbox.get(0, "end")
    listbox.selection_set(items.index("be_au"))
    listbox.selection_set(items.index("te_au"))
    apply_button = next(b for b in _find_all(dialog, ttk.Button) if b["text"] == "Apply")
    apply_button.invoke()


root.after(150, _drive_width_union)
mtv._select_drc_check_layers()
root.update()

print("real union after multi-select:", be_au_check.layer_args)
assert be_au_check.layer_args == [["be_au", "te_au"]]
assert be_au_check.layers_text == "be_au,te_au"
row_values = mtv.drc_checks_editor.tree.item(mtv.drc_checks_editor._iid(be_au_check))["values"]
assert row_values[1] == "be_au,te_au"
print("PASS: multi-selecting two real types unions them into the correct comma-joined string, "
      "reflected immediately in the row and form.")

# --- spacing check: two independent real sides, each its own union --------
te_spacing_check = next(c for c in mtv.drc_checks_editor.entries if c.check_type == "spacing")
mtv.drc_checks_editor.tree.selection_set(mtv.drc_checks_editor._iid(te_spacing_check))
mtv.drc_checks_editor._on_select()
root.update()


def _drive_spacing_sides():
    dialog = _select_layers_dialog(root)
    listboxes = _find_all(dialog, tk.Listbox)
    assert len(listboxes) == 2
    left_items = listboxes[0].get(0, "end")
    listboxes[0].selection_clear(0, "end")
    listboxes[0].selection_set(left_items.index("te_au"))
    right_items = listboxes[1].get(0, "end")
    listboxes[1].selection_clear(0, "end")
    listboxes[1].selection_set(right_items.index("te_ti"))
    listboxes[1].selection_set(right_items.index("te_al"))
    apply_button = next(b for b in _find_all(dialog, ttk.Button) if b["text"] == "Apply")
    apply_button.invoke()


root.after(150, _drive_spacing_sides)
mtv._select_drc_check_layers()
root.update()

print("real per-side layer_args after edit:", te_spacing_check.layer_args)
assert te_spacing_check.layer_args == [["te_au"], ["te_ti", "te_al"]]
assert te_spacing_check.layers_text == "te_au | te_ti,te_al"
print("PASS: a spacing check gets two independent real Listboxes, each its own real union, "
      "correctly joined with the existing ' | ' two-side format.")

# --- an empty side is refused, not silently accepted ----------------------
def _drive_empty_side():
    dialog = _select_layers_dialog(root)
    listboxes = _find_all(dialog, tk.Listbox)
    listboxes[0].selection_clear(0, "end")
    apply_button = next(b for b in _find_all(dialog, ttk.Button) if b["text"] == "Apply")
    apply_button.invoke()
    # Apply must have refused (dialog still open) -- close it explicitly.
    cancel_button = next(b for b in _find_all(dialog, ttk.Button) if b["text"] == "Cancel")
    cancel_button.invoke()


unchanged_before = list(te_spacing_check.layer_args)
root.after(150, _drive_empty_side)
mtv._select_drc_check_layers()
root.update()
assert te_spacing_check.layer_args == unchanged_before
print("PASS: clearing a real side's selection is refused (each side needs at least one real type), "
      "the existing real layer_args is left untouched.")

root.destroy()

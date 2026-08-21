import sys
sys.path.insert(0, "/foss/designs/openMemristorPDK")
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from openpdkcreator.gui.app import App
from openpdkcreator.pdklib import magic_tech as mt

PDK_ROOT = Path("/foss/designs/openMemristorPDK/data/openmemristorpdk")

# Capture messagebox calls instead of popping a real, blocking modal.
captured = []


def _capture(kind):
    def _fn(title, message, **_kw):
        captured.append((kind, title, message))
    return _fn


messagebox.showinfo = _capture("info")
messagebox.showwarning = _capture("warning")
messagebox.showerror = _capture("error")

root = tk.Tk()
app = App(root, PDK_ROOT)
app.load()
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("openmemristorpdk")
mtv._refresh_all()
root.update()

# --- real DRC (Magic) content from this session's own real, authored
# drc-section lines is loaded and editable, not an empty tab -----------
print("real DRC checks:", len(mtv.drc_checks_editor.tree.get_children()))
print("real angle checks:", len(mtv.drc_angles_editor.tree.get_children()))
assert len(mtv.drc_checks_editor.tree.get_children()) == 6
assert len(mtv.drc_angles_editor.tree.get_children()) == 1
print("PASS: openmemristorpdk's own real drc section (width/spacing/maxwidth/angles) is loaded, not empty.")

# --- real, closed-enum comboboxes -----------------------------------------
assert mtv.drc_checks_editor.combo_widgets["check_type"]["values"] == mt.DRC_CHECK_TYPES
assert tuple(mtv.drc_misc_editor.combo_widgets["directive"]["values"]) == mt.DRC_MISC_DIRECTIVES
angle_layer_values = tuple(mtv.drc_angles_editor.combo_widgets["layer"]["values"])
print("real angle layer combobox values:", angle_layer_values)
assert set(angle_layer_values) == {"be_au", "te_au", "te_ti", "te_al", "mem_tio2", "mem_hfo2"}
print("PASS: check_type/directive are real fixed-enum comboboxes; angles' layer combobox lists this "
      "technology's own real, current Type names.")

# --- Copy to DRC Rules: a genuinely new check copies clean ----------------
rules_before = len(app.project.design_rules)
te_ti_check = next(c for c in mtv.drc_checks_editor.entries if c.layer_args == [["te_ti"]])
mtv.drc_checks_editor.tree.selection_set(mtv.drc_checks_editor._iid(te_ti_check))
mtv.drc_checks_editor._on_select()
root.update()
captured.clear()
mtv._copy_drc_check_to_rule()
root.update()
assert len(app.project.design_rules) == rules_before + 1
new_rule = app.project.design_rules[-1]
print("newly copied rule:", new_rule.rule_id, new_rule.check_type, new_rule.layers, new_rule.value)
assert new_rule.check_type == "min_width"
assert new_rule.layers == ["TE_Ti.drawing"]
assert new_rule.value == 0.15
assert captured and captured[0][0] == "info"
assert new_rule.rule_id in captured[0][2]
tree_rule_ids = [app.rules_view.tree.item(iid)["values"][0] for iid in app.rules_view.tree.get_children()]
assert new_rule.rule_id in tree_rule_ids
print("PASS: Copy to DRC Rules creates a real new DesignRule, refreshes the real DRC Rules tree, and confirms it.")

# --- Copy to DRC Rules: an exact real duplicate is correctly refused ------
be_au_check = next(c for c in mtv.drc_checks_editor.entries if c.layer_args == [["be_au"]])
mtv.drc_checks_editor.tree.selection_set(mtv.drc_checks_editor._iid(be_au_check))
mtv.drc_checks_editor._on_select()
root.update()
rules_before = len(app.project.design_rules)
captured.clear()
mtv._copy_drc_check_to_rule()
root.update()
assert len(app.project.design_rules) == rules_before
assert captured and captured[0][0] == "warning"
assert "already exists" in captured[0][2]
print("PASS: Copy to DRC Rules correctly refuses an exact real duplicate (BE.W.1), reporting why.")

# --- Copy to DRC Rules: maxwidth is correctly refused with a real reason --
maxwidth_check = next(c for c in mtv.drc_checks_editor.entries if c.check_type == "maxwidth")
mtv.drc_checks_editor.tree.selection_set(mtv.drc_checks_editor._iid(maxwidth_check))
mtv.drc_checks_editor._on_select()
root.update()
rules_before = len(app.project.design_rules)
captured.clear()
mtv._copy_drc_check_to_rule()
root.update()
assert len(app.project.design_rules) == rules_before
assert captured and captured[0][0] == "warning"
assert "maxwidth" in captured[0][2]
print("PASS: Copy to DRC Rules correctly refuses maxwidth (no real DRC Rules equivalent).")

root.destroy()

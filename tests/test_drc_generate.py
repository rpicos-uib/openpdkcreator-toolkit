import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path
import shutil

from openpdkcreator.gui.app import App
from openpdkcreator.ihp import drc as drc_mod
from openpdkcreator.ihp import layers as layers_mod
from openpdkcreator import export as export_mod
from openpdkcreator.models import Layer

PDK_ROOT = Path("/tmp/drc_test_pdk")
shutil.rmtree(PDK_ROOT, ignore_errors=True)
(PDK_ROOT / "libs.tech").mkdir(parents=True)
(PDK_ROOT / "libs.ref").mkdir(parents=True)

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

# --- New DRC Deck button, before any .lyp exists ---
assert app.drc_root is None
app._new_drc_deck()
root.update()
assert app.drc_root is not None and app.drc_root.is_dir()
assert app.project.design_rules == []
print("PASS: New DRC Deck works even before a .lyp exists (order-independent).")

# --- Now create Layers too, with two real layers to reference ---
lyp_path = PDK_ROOT / "libs.tech" / "klayout" / "tech" / "mem.lyp"
layers_mod.create_new_lyp_file(lyp_path)
app.load()
root.update()
app.layers_view._new_layer()
te = app.project.layers[-1]
te.name, te.gds_layer, te.gds_datatype = "TopElectrode.drawing", 200, 0
app.layers_view._new_layer()
via = app.project.layers[-1]
via.name, via.gds_layer, via.gds_datatype = "ViaCut.drawing", 210, 0
app.rules_view.refresh()
root.update()
print("PASS: two real layers created for DRC rules to reference.")

# --- New Rule: min_width on TopElectrode ---
app.rules_view._new_rule()
root.update()
rule_w = app.project.design_rules[-1]
rule_w.rule_id = "TE_W"
rule_w.description = "minimum TopElectrode width"
rule_w.check_type = "min_width"
rule_w.layers = ["TopElectrode.drawing"]
rule_w.value = 0.2
app.rules_view._load_rule_into_form(rule_w)

# --- New Rule: min_enclosure of Via by TopElectrode ---
app.rules_view._new_rule()
root.update()
rule_e = app.project.design_rules[-1]
rule_e.rule_id = "TE_VIA_ENC"
rule_e.description = "minimum enclosure of via by TopElectrode"
rule_e.check_type = "min_enclosure"
rule_e.layers = ["ViaCut.drawing", "TopElectrode.drawing"]
rule_e.value = 0.1
app.rules_view._load_rule_into_form(rule_e)

# --- New Rule: an ungeneratable check_type (min_area) ---
app.rules_view._new_rule()
root.update()
rule_bad = app.project.design_rules[-1]
rule_bad.rule_id = "TE_AREA"
rule_bad.description = "minimum TopElectrode area"
rule_bad.check_type = "min_area"
rule_bad.layers = ["TopElectrode.drawing"]
rule_bad.value = 0.05

print("real rule count:", len(app.project.design_rules))
assert len(app.project.design_rules) == 3

# --- Export ---
with __import__("tempfile").TemporaryDirectory() as tmp:
    dest = Path(tmp)
    written, failures = export_mod.export_drc_rules(PDK_ROOT, app.drc_root, app.project.design_rules, app.project.layers, dest_root=dest)
    print("written:", [str(p) for p in written])
    print("failures:", failures)
    assert len(failures) == 1 and failures[0][0] == "TE_AREA"
    custom_path = [p for p in written if p.name == "custom_rules.drc"][0]
    text = custom_path.read_text()
    print("--- custom_rules.drc ---")
    print(text)
    assert "input(200, 0)" in text
    assert "input(210, 0)" in text
    assert ".width(0.2.um)" in text
    assert ".enclosed(" in text and "0.1.um" in text
    assert 'output("TE_W"' in text
    assert 'output("TE_VIA_ENC"' in text
    assert "TE_AREA" not in text
    print("PASS: real, generated KLayout DRC Ruby is correct and runnable-shaped.")

    # --- Re-import: the generated file should parse back to 2 real rules ---
    reextracted, skipped = drc_mod.extract_design_rules(PDK_ROOT, custom_path.parent)
    reextracted_ids = {r.rule_id for r in reextracted}
    print("re-extracted rule ids:", reextracted_ids)
    assert reextracted_ids == {"TE_W", "TE_VIA_ENC"}
    print("PASS: exported custom_rules.drc re-imports (round-trips) back to the same 2 real rules.")

root.destroy()
print("ALL DRC GENERATE/EXPORT/IMPORT TESTS PASS")

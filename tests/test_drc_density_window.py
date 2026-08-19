import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path
import shutil

from openpdkcreator.gui.app import App
from openpdkcreator.pdklib import drc_writer as drc_writer_mod
from openpdkcreator.pdklib import skeleton as skeleton_mod
from openpdkcreator import export as export_mod
from openpdkcreator.models import DesignRule, Layer

PDK_ROOT = Path("/tmp/drc_density_test_pdk")
shutil.rmtree(PDK_ROOT, ignore_errors=True)
skeleton_mod.build_blank_pdk(PDK_ROOT)

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()
app._new_drc_deck()
root.update()

from openpdkcreator.pdklib import layers as layers_mod
lyp_path = PDK_ROOT / "libs.tech" / "klayout" / "tech" / "mem.lyp"
layers_mod.create_new_lyp_file(lyp_path)
app.load()
root.update()
app.layers_view._new_layer()
te = app.project.layers[-1]
te.name, te.gds_layer, te.gds_datatype = "TopElectrode.drawing", 200, 0
app.layers_view._new_layer()
extra = app.project.layers[-1]
extra.name, extra.gds_layer, extra.gds_datatype = "Extra.drawing", 201, 0
app.rules_view.refresh()
root.update()
layers_by_name = {"TopElectrode.drawing": te, "Extra.drawing": extra}

# --- Direct render_new_rule_block tests: both real patterns, both
# real directions, and both honest refusal paths ---
rule_global_min = DesignRule(
    rule_id="TE_DENS_MIN", description="minimum TopElectrode density", check_type="density_window",
    layers=["TopElectrode.drawing"], value=25.0, units="percent", condition="min",
)
lines, err = drc_writer_mod.render_new_rule_block(rule_global_min, layers_by_name)
assert err is None, err
assert "extent.sized(0.0).area" in "\n".join(lines)
assert "if te_dens_min_ratio < 25.0" in "\n".join(lines)
assert 'extent.output("TE_DENS_MIN"' in "\n".join(lines)
print("PASS: global min-direction density_window generates a real, correct whole-chip ratio check.")

rule_global_max = DesignRule(
    rule_id="TE_DENS_MAX", description="maximum combined density", check_type="density_window",
    layers=["TopElectrode.drawing", "Extra.drawing"], value=0.5, units="percent", condition="max",
)
lines2, err2 = drc_writer_mod.render_new_rule_block(rule_global_max, layers_by_name)
assert err2 is None, err2
text2 = "\n".join(lines2)
assert "te_dens_max_material = te_dens_max_l0 + te_dens_max_l1" in text2
assert "if te_dens_max_ratio > 0.5" in text2
print("PASS: global max-direction density_window sums two real layers via '+' (gf180mcu's own real convention).")

rule_windowed = DesignRule(
    rule_id="TE_DENS_WIN", description="windowed density check", check_type="density_window",
    layers=["TopElectrode.drawing"], value=10.0, units="percent", condition="min",
    window_size_um=20.0, window_step_um=10.0,
)
lines3, err3 = drc_writer_mod.render_new_rule_block(rule_windowed, layers_by_name)
assert err3 is None, err3
text3 = "\n".join(lines3)
assert "with_density(0.0 .. 0.1, tile_size(20.0.um), tile_step(10.0.um))" in text3
assert "te_dens_win_material = te_dens_win_material.merged" in text3
print("PASS: windowed density_window generates real, correct KLayout with_density()/tile_size()/tile_step() Ruby.")

rule_no_condition = DesignRule(
    rule_id="TE_DENS_BAD", description="no condition", check_type="density_window",
    layers=["TopElectrode.drawing"], value=10.0,
)
_, err4 = drc_writer_mod.render_new_rule_block(rule_no_condition, layers_by_name)
assert err4 == "density_window needs Condition set to exactly 'min' or 'max' to know which bound this value represents"
print("PASS: a density_window rule with no real min/max Condition is honestly refused, not guessed.")

rule_no_layers = DesignRule(
    rule_id="TE_DENS_NOLAYER", description="no layers", check_type="density_window",
    layers=[], value=10.0, condition="min",
)
_, err5 = drc_writer_mod.render_new_rule_block(rule_no_layers, layers_by_name)
assert err5 == "needs at least 1 real layer(s), has 0"
print("PASS: a density_window rule with no real layer is honestly refused (schema min_layers now 1, not 0).")

# --- GUI: New Rule with density_window, three real layer pickers now
# shown (schema.CHECK_TYPES['density_window'] widened from 0 to 3
# real "Layer" roles) ---
before_count = len(app.project.design_rules)
app.rules_view._new_rule()
root.update()
new_rule = app.project.design_rules[-1]
new_rule.rule_id = "TE_DENS_GUI"
new_rule.description = "gui-authored density rule"
new_rule.check_type = "density_window"
new_rule.layers = ["TopElectrode.drawing"]
new_rule.value = 30.0
new_rule.condition = "min"
app.rules_view._load_rule_into_form(new_rule)
root.update()
app.rules_view._update_layer_picker_state()
assert app.rules_view.layer_labels[0]["text"] == "Layer"
assert app.rules_view.layer_labels[1]["text"] == "Layer"
assert app.rules_view.layer_labels[2]["text"] == "Layer"
print("PASS: density_window now shows three real 'Layer' pickers in the GUI (was zero before this pass).")

app.rules_view.vars["window_size_um"].set("15")
app.rules_view.vars["window_step_um"].set("")
root.update()
app.rules_view._commit_form_to_rule()
assert new_rule.window_size_um == 15.0
assert new_rule.window_step_um is None
print("PASS: Window Size (um)/Window Step (um) fields round-trip into the real DesignRule fields.")

# --- Export: real, generated KLayout DRC Ruby for all three rules,
# actually runnable through the real, installed KLayout binary ---
app.project.design_rules = [rule_global_min, rule_global_max, rule_windowed]
app.rules_view.refresh()
root.update()

import tempfile
with tempfile.TemporaryDirectory() as tmp:
    dest = Path(tmp)
    written, failures = export_mod.export_drc_rules(
        PDK_ROOT, app.drc_root, app.project.design_rules, app.project.layers, dest_root=dest
    )
    assert failures == [], failures
    custom_path = [p for p in written if p.name == "custom_rules.drc"][0]
    text = custom_path.read_text()
    assert "TE_DENS_MIN" in text and "TE_DENS_MAX" in text and "TE_DENS_WIN" in text
    print("PASS: all three real density_window rules export into real, generated custom_rules.drc.")

    import subprocess

    make_gds_script = dest / "make_gds.rb"
    make_gds_script.write_text(
        'layout = RBA::Layout.new\n'
        'top = layout.create_cell("TOP")\n'
        'l200 = layout.layer(200, 0)\n'
        'l201 = layout.layer(201, 0)\n'
        'top.shapes(l200).insert(RBA::Box.new(0, 0, 2000, 2000))\n'
        'top.shapes(l201).insert(RBA::Box.new(500, 500, 1500, 1500))\n'
        f'layout.write("{dest / "test.gds"}")\n'
    )
    subprocess.run(["klayout", "-b", "-rx", "-r", str(make_gds_script)], check=True, timeout=30)
    assert (dest / "test.gds").is_file()

    report_path = dest / "report.lyrdb"
    result = subprocess.run(
        ["klayout", "-b", str(dest / "test.gds"), "-r", str(custom_path), "-rd", f"output={report_path}"],
        capture_output=True, text=True, timeout=30,
    )
    print("klayout stdout:", result.stdout)
    print("klayout stderr:", result.stderr)
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    report_text = report_path.read_text()
    # TE_DENS_MIN: TopElectrode covers 100% of its own extent -> never
    # below the real 25% minimum -> correctly NOT flagged.
    assert "<name>TE_DENS_MIN</name>" not in report_text
    # TE_DENS_MAX: combined material clearly exceeds the real 0.5% max
    # over its own extent -> correctly flagged.
    assert "<name>TE_DENS_MAX</name>" in report_text
    # TE_DENS_WIN: a real 2x2um shape can't sustain 10% density across
    # real, larger 20x20um tiles away from it -> correctly flagged.
    assert "<name>TE_DENS_WIN</name>" in report_text
    print("PASS: the real, generated custom_rules.drc actually runs cleanly through the real, installed "
          "KLayout DRC engine, and every real density_window rule's own violation behavior is physically "
          "correct (TE_DENS_MIN not flagged, TE_DENS_MAX/TE_DENS_WIN correctly flagged).")

root.destroy()
print("ALL DRC DENSITY WINDOW TESTS PASS")

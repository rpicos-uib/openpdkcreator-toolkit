import sys
sys.path.insert(0, "/foss/designs")
import shutil
from pathlib import Path

from openpdkcreator import export as export_mod
from openpdkcreator.ihp import drc as drc_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
drc_root = drc_mod.find_drc_root(PDK_ROOT)
assert drc_root is not None

if export_mod.EXPORT_ROOT.is_dir():
    shutil.rmtree(export_mod.EXPORT_ROOT)

# --- Test 1: no-edit export == byte-identical original for every real file touched ---
rules, skipped_extraction = drc_mod.extract_design_rules(PDK_ROOT, drc_root)
print(f"{len(rules)} real rules extracted, {len(skipped_extraction)} composite constructs skipped (unrelated to write-back).")

written, skipped_writeback = export_mod.export_drc_rules(PDK_ROOT, drc_root, rules)
assert not skipped_writeback, f"expected every real-extracted rule to have real provenance: {skipped_writeback}"
print(f"{len(written)} real file(s) written (no edits made).")

mismatches = []
for export_path in written:
    relpath = export_path.relative_to(export_mod.EXPORT_ROOT / PDK_ROOT.name)
    original_path = PDK_ROOT / relpath
    original = original_path.read_text(encoding="utf-8", errors="replace")
    exported = export_path.read_text(encoding="utf-8", errors="replace")
    if original != exported:
        mismatches.append((original_path, original, exported))

if mismatches:
    for path, original, exported in mismatches:
        o_lines, e_lines = original.splitlines(), exported.splitlines()
        print(f"MISMATCH: {path}")
        for i, (a, b) in enumerate(zip(o_lines, e_lines)):
            if a != b:
                print(f"  line {i+1}: {a!r} != {b!r}")
                break
    raise SystemExit(f"{len(mismatches)} real byte-identical mismatch(es) -- see above")
print(f"PASS: all {len(written)} real files (DRC scripts + JSON config) are byte-identical on no-edit export.")

# --- Test 2: edit a rule's value, confirm it patches the real JSON, everything else untouched ---
rule = next(r for r in rules if r.rule_id == "Act.a")
original_value = rule.value
assert original_value == 0.15, original_value
rule.value = 0.20

written2, _ = export_mod.export_drc_rules(PDK_ROOT, drc_root, rules)
json_export = export_mod.export_path_for(PDK_ROOT, drc_mod.find_json_config_path(drc_root))
assert json_export.is_file()

import json
exported_json = json.loads(json_export.read_text())
original_json = json.loads(drc_mod.find_json_config_path(drc_root).read_text())
assert exported_json["drc_rules"]["Act_a"] == 0.2, exported_json["drc_rules"]["Act_a"]
diffs = {k: (original_json["drc_rules"][k], v) for k, v in exported_json["drc_rules"].items() if original_json["drc_rules"].get(k) != v}
assert diffs == {"Act_a": (0.15, 0.2)}, diffs
print(f"PASS: editing Act.a's value (0.15 -> 0.20) patches only Act_a in the real JSON, {len(exported_json['drc_rules'])} other keys untouched.")

# Confirm the .drc file for Act.a is otherwise byte-identical (no value lives there).
act_rule_path = PDK_ROOT / "libs.tech/klayout/tech/drc/rule_decks/feol/5_5_activ.drc"
act_export_path = export_mod.export_path_for(PDK_ROOT, act_rule_path)
assert act_export_path.read_text() == act_rule_path.read_text()
print("PASS: the .drc script itself is untouched by a pure value edit (value lives only in JSON).")

rule.value = original_value  # restore for the next test

# --- Test 3: edit a rule's rule_id and description (with a real ' : ' prefix case) ---
rule_with_prefix = next(r for r in rules if "Min. Via1 space" in r.description)
print(f"Rule with real ' : ' prefix: {rule_with_prefix.rule_id!r} -> {rule_with_prefix.description!r}")
original_id, original_desc = rule_with_prefix.rule_id, rule_with_prefix.description
rule_with_prefix.rule_id = "V1.b.RENAMED"
rule_with_prefix.description = "A totally new description, no colon needed"

written3, _ = export_mod.export_drc_rules(PDK_ROOT, drc_root, rules)
via_relpath = drc_writer_relpath = drc_mod.find_json_config_path  # placeholder, real path below
via_original_path = PDK_ROOT / "libs.tech/klayout/tech/drc/rule_decks/beol/5_19_via1.drc"
via_export_path = export_mod.export_path_for(PDK_ROOT, via_original_path)
exported_text = via_export_path.read_text()
assert 'V1.b.RENAMED' in exported_text
assert '"5.19. V1.b : A totally new description, no colon needed"' in exported_text, exported_text
print("PASS: rule_id and description (real ' : ' prefix preserved) both patched correctly in the real .drc file.")

# Confirm every OTHER real .output() call in that same file is untouched.
original_text = via_original_path.read_text()
orig_lines, exp_lines = original_text.splitlines(), exported_text.splitlines()
assert len(orig_lines) == len(exp_lines)
real_diff_lines = [i for i, (a, b) in enumerate(zip(orig_lines, exp_lines)) if a != b]
print(f"Changed real line(s) in via1.drc: {real_diff_lines}")
assert len(real_diff_lines) <= 2, real_diff_lines  # just the id line and/or description line(s)

rule_with_prefix.rule_id, rule_with_prefix.description = original_id, original_desc

# --- Test 4: a hand-authored rule with no value/layers is reported, not silently dropped ---
from openpdkcreator.models import DesignRule
hand_rule = DesignRule(rule_id="NEW.RULE.1", description="hand-authored", check_type="min_width")
written4, failures4 = export_mod.export_drc_rules(PDK_ROOT, drc_root, rules + [hand_rule])
assert failures4 == [("NEW.RULE.1", "no value set")], failures4
print(f"PASS: a hand-authored rule with no value is correctly reported, not silently dropped: {failures4}")

# --- Test 5: a hand-authored rule WITH a resolvable value/layer generates real Ruby ---
from openpdkcreator.ihp import layers as layers_mod
lyp_path = layers_mod.find_lyp(PDK_ROOT)
real_layers = layers_mod.import_layers(PDK_ROOT, lyp_path) if lyp_path else []
real_layer = next((l for l in real_layers if l.gds_layer is not None), None)
assert real_layer is not None, "expected at least one real, GDS-resolvable layer in the real IHP .lyp"
generatable_rule = DesignRule(
    rule_id="CUSTOM.W", description="a hand-authored width check", check_type="min_width",
    layers=[real_layer.name], value=0.33,
)
written5, failures5 = export_mod.export_drc_rules(PDK_ROOT, drc_root, rules + [generatable_rule], real_layers)
custom_path = next(p for p in written5 if p.name == "custom_rules.drc")
custom_text = custom_path.read_text()
assert 'output("CUSTOM.W"' in custom_text and "0.33.um" in custom_text, custom_text
assert not any(rule_id == "CUSTOM.W" for rule_id, _reason in failures5), failures5
print("PASS: a hand-authored rule with a real value/layer generates real, runnable KLayout DRC Ruby.")

if export_mod.EXPORT_ROOT.is_dir():
    shutil.rmtree(export_mod.EXPORT_ROOT)
print("ALL PASS")

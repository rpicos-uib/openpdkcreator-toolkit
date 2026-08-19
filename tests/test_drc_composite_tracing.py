import sys
sys.path.insert(0, "/foss/designs")
from pathlib import Path

from openpdkcreator.pdklib import drc as drc_mod
from openpdkcreator.pdklib import drc_writer as drc_writer_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
drc_root = drc_mod.find_drc_root(PDK_ROOT)

rules, skipped = drc_mod.extract_design_rules(PDK_ROOT, drc_root)
by_id = {r.rule_id: r for r in rules}

print("total rules:", len(rules), "skipped:", len(skipped))
assert len(rules) == 85  # 77 + 8 real, safely-traced composite rules
assert len(skipped) == 82  # 90 - 8

# --- Every real, safely-resolvable composite rule, confirmed via a
# real, manual read of its own real source (not just trusted because
# the tracer emitted it) ---
EXPECTED = {
    "Ant.g": ("min_area", None),  # both real branches share the same value var, but it's used bare (no
                                    # .um suffix at the with_area() call site) -- a real, separate, pre-existing
                                    # value-resolution gap, not something composite tracing is expected to fix.
    "Pas.c": ("min_enclosure", 2.1),
    "MIM.c": ("min_enclosure", 0.6),
    "Padc.c": ("min_enclosure", 7.5),
    "Padb.c": ("min_enclosure", 10.0),
    "NW.b1": ("min_spacing", 1.8),
    "NBL.c": ("min_spacing", 3.2),
    "NBL.d": ("min_spacing", 2.2),
}
for rule_id, (check_type, value) in EXPECTED.items():
    rule = by_id[rule_id]
    assert rule.check_type == check_type, (rule_id, rule.check_type, check_type)
    assert rule.value == value, (rule_id, rule.value, value)
    assert "boolean-composed" in (rule.applies_to_override or "")
    assert rule.status == "placeholder"
print(f"PASS: all {len(EXPECTED)} real, safely-traced composite rules extracted with the exact real, "
      f"confirmed check_type/value.")

# --- Real, confirmed-unsafe composites correctly still NOT extracted,
# not silently guessed at -- found as real near-misses while building
# the tracer, not hypothetical ---
UNSAFE_STILL_SKIPPED = ("Sdiod.b", "Sdiod.c", "Padc.a", "Padb.a", "AFil.d")
for rule_id in UNSAFE_STILL_SKIPPED:
    assert rule_id not in by_id, f"{rule_id} should NOT be auto-extracted (real, confirmed-unsafe composite)"
print(f"PASS: real, confirmed-unsafe composites ({', '.join(UNSAFE_STILL_SKIPPED)}) correctly stay "
      f"unresolved, not guessed at -- each has at least one real branch this module can't safely verify "
      f"shares the same value (e.g. Sdiod.b's own second branch traces through a real .sized() call, not "
      f"one of the six directly-recognized check methods).")

# --- No-edit export stays byte-identical across the whole real deck,
# composite rules included ---
rendered_by_file = {}
for drc_file in sorted(drc_root.rglob("*.drc")):
    rel = drc_file.relative_to(PDK_ROOT)
    file_rules = [r for r in rules if str(rel) in (r.source_provenance or "")]
    if not file_rules:
        continue
    text, _value_edits = drc_writer_mod.render_drc_file(drc_file, file_rules)
    original = drc_file.read_text(encoding="utf-8", errors="replace")
    assert text == original, f"MISMATCH: {rel}"
print("PASS: no-edit export stays byte-identical for every real .drc file with at least one traced rule "
      "(direct or composite).")

# --- A composite rule's own real VALUE edit patches the real JSON
# correctly too -- not just rule_id/description -- via _locate's own
# real composite-aware fallback ---
import tempfile
from openpdkcreator import export as export_mod

nw_b1 = by_id["NW.b1"]
nw_b1.value = 2.5
with tempfile.TemporaryDirectory() as tmp:
    dest = Path(tmp)
    written, failures = export_mod.export_drc_rules(PDK_ROOT, drc_root, rules, [], dest_root=dest)
    assert failures == []
    json_path = [p for p in written if p.suffix == ".json"][0]
    import json
    data = json.loads(json_path.read_text())
    assert data["drc_rules"]["NW_b1"] == 2.5
    drc_path = [p for p in written if p.name == "5_1_nwell.drc"][0]
    orig_path = drc_root / "rule_decks" / "feol" / "5_1_nwell.drc"
    assert drc_path.read_text() == orig_path.read_text()  # value never lived in the .drc text itself
print("PASS: editing NW.b1's own real value (a composite-traced rule) correctly patches NW_b1 in the real "
      "JSON config, leaving the real .drc script itself untouched -- write-back works for a composite rule "
      "exactly like a direct one, not silently dropped.")
nw_b1.value = 1.8  # restore, in case anything downstream re-reads this in-process object

print("ALL DRC COMPOSITE TRACING TESTS PASS")

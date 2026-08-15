import sys
sys.path.insert(0, "/foss/designs")
from pathlib import Path
from openpdkcreator.ihp import lef as lef_mod

path = Path("data/ihp-sg13g2/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef")
tech = lef_mod.parse_lef_file(path)

assert len(tech.vias) == 70, len(tech.vias)
assert len(tech.via_rules) == 6, len(tech.via_rules)
print(f"PASS: 70 real vias, 6 real viarules found")

via_by_name = {v.name: v for v in tech.vias}

# Via1_XX: single-cut, RESISTANCE 20.00, Metal1/Via1/Metal2 each 1 rect
v = via_by_name["Via1_XX"]
assert v.is_default is True
assert v.resistance == 20.00, v.resistance
assert [l.layer for l in v.layers] == ["Metal1", "Via1", "Metal2"], [l.layer for l in v.layers]
assert v.layers[0].rects == [(-0.145, -0.105, 0.145, 0.105)], v.layers[0].rects
assert v.layers[1].rects == [(-0.095, -0.095, 0.095, 0.095)]
assert v.layers[2].rects == [(-0.145, -0.1, 0.145, 0.1)]
print("PASS: Via1_XX (single-cut) geometry matches real file exactly")

# Via1_DC1B: double-cut, Via1 layer appears TWICE with different rects
v = via_by_name["Via1_DC1B"]
assert v.resistance == 20.0, v.resistance
via1_entries = [l for l in v.layers if l.layer == "Via1"]
assert len(via1_entries) == 2, len(via1_entries)
assert via1_entries[0].rects == [(-0.095, -0.095, 0.095, 0.095)]
assert via1_entries[1].rects == [(-0.095, 0.315, 0.095, 0.505)]
print("PASS: Via1_DC1B (double-cut, repeated LAYER Via1) geometry matches real file exactly")

# ViaRULE via1Array
vr_by_name = {vr.name: vr for vr in tech.via_rules}
vr = vr_by_name["via1Array"]
assert vr.is_generate is True
assert [l.layer for l in vr.layers] == ["Metal1", "Metal2", "Via1"]
m1, m2, via1 = vr.layers
assert m1.enclosure == (0.050, 0.010), m1.enclosure
assert m1.rect is None and m1.spacing is None and m1.resistance is None
assert m2.enclosure == (0.050, 0.005), m2.enclosure
assert via1.enclosure is None
assert via1.rect == (-0.095, -0.095, 0.095, 0.095), via1.rect
assert via1.spacing == (0.480, 0.480), via1.spacing
assert via1.resistance == 20.0, via1.resistance
print("PASS: ViaRULE via1Array geometry matches real file exactly")

# Every real via/viarule has a resolvable name and at least one layer
assert all(v.name for v in tech.vias)
assert all(len(v.layers) >= 2 for v in tech.vias), "every real via should have at least 2 layers (metal-cut-metal)"
assert all(vr.name for vr in tech.via_rules)
assert all(len(vr.layers) == 3 for vr in tech.via_rules), "every real IHP viarule here is metal/metal/cut"
print("PASS: structural sanity checks across all 70 vias / 6 viarules")

# Cross-check against every other real .lef file: none besides the tech LEF should define any
other_files = [p for p in lef_mod.find_lef_files(Path("data/ihp-sg13g2/ihp-sg13g2")) if p != path]
assert other_files, "expected other real .lef files to check against"
for p in other_files:
    other = lef_mod.parse_lef_file(p)
    assert other.vias == [] and other.via_rules == [], p
print(f"PASS: {len(other_files)} other real .lef files correctly have zero vias/viarules")

print("ALL LEF VIA/VIARULE TESTS PASSED")

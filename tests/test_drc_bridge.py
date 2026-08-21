import sys
sys.path.insert(0, "/foss/designs")

from openpdkcreator.models import DesignRule, Layer
from openpdkcreator.pdklib import drc_bridge
from openpdkcreator.pdklib.magic_tech import CifOutputLayerMapping, MagicDrcCheck

LAYER = Layer(name="BE_Au.drawing", gds_layer=30, gds_datatype=0)
CIF = [CifOutputLayerMapping(name="BE_Au", gds_layer=30, gds_datatype=0, line_no=1, recipe_types=("be_au",))]


def make_width(value=0.2, layer_args=(("be_au",),), filler_raw=""):
    return MagicDrcCheck(
        check_type="width", layer_args=[list(g) for g in layer_args], value_um=value,
        message="min width", rule_ids_raw=None, filler_raw=filler_raw,
    )


def make_spacing(a="be_au", b="be_au", value=0.15):
    return MagicDrcCheck(
        check_type="spacing", layer_args=[[a], [b]], value_um=value,
        message="min spacing", rule_ids_raw=None,
    )


# --- clean width copy succeeds -----------------------------------------
r = drc_bridge.copy_magic_drc_check_to_rule(make_width(), CIF, [LAYER], [])
assert r.rule is not None, r.messages
assert r.rule.check_type == "min_width"
assert r.rule.layers == ["BE_Au.drawing"]
assert r.rule.value == 0.2
assert r.rule.units == "um"
assert r.messages == []
print("PASS: clean single-type width check copies to a real min_width rule.")

# --- clean self-spacing copy succeeds -----------------------------------
r = drc_bridge.copy_magic_drc_check_to_rule(make_spacing(), CIF, [LAYER], [])
assert r.rule is not None, r.messages
assert r.rule.check_type == "min_spacing"
assert r.rule.layers == ["BE_Au.drawing"]
assert r.rule.value == 0.15
print("PASS: true-self spacing check copies to a real min_spacing rule.")

# --- maxwidth has no equivalent, blocked ---------------------------------
maxwidth = MagicDrcCheck(
    check_type="maxwidth", layer_args=[["be_au"]], value_um=1.0, message="max width", rule_ids_raw=None,
)
r = drc_bridge.copy_magic_drc_check_to_rule(maxwidth, CIF, [LAYER], [])
assert r.rule is None
assert "maxwidth" in r.messages[0]
print("PASS: maxwidth is correctly reported as having no DRC Rules equivalent.")

# --- width unioning multiple types is blocked ----------------------------
r = drc_bridge.copy_magic_drc_check_to_rule(make_width(layer_args=(("be_au", "te_au"),)), CIF, [LAYER], [])
assert r.rule is None
assert "unions" in r.messages[0]
print("PASS: a width check unioning multiple real types is correctly blocked.")

# --- spacing between two different types is blocked ----------------------
r = drc_bridge.copy_magic_drc_check_to_rule(make_spacing(a="be_au", b="te_au"), CIF, [LAYER], [])
assert r.rule is None
assert "different real Magic types" in r.messages[0]
print("PASS: a different-layer spacing check is correctly blocked (no min_spacing equivalent).")

# --- no cifoutput mapping is blocked --------------------------------------
r = drc_bridge.copy_magic_drc_check_to_rule(make_width(layer_args=(("unmapped_type",),)), CIF, [LAYER], [])
assert r.rule is None
assert "cifoutput" in r.messages[0]
print("PASS: a Magic type with no real cifoutput mapping is correctly blocked.")

# --- ambiguous cifoutput mapping (2 distinct GDS pairs) is blocked -------
ambiguous_cif = [
    CifOutputLayerMapping(name="BE_Au", gds_layer=30, gds_datatype=0, line_no=1, recipe_types=("be_au",)),
    CifOutputLayerMapping(name="BE_Au2", gds_layer=31, gds_datatype=0, line_no=9, recipe_types=("be_au",)),
]
r = drc_bridge.copy_magic_drc_check_to_rule(make_width(), ambiguous_cif, [LAYER], [])
assert r.rule is None
assert "ambiguous" in r.messages[0]
print("PASS: a Magic type mapping to two different real GDS pairs is correctly blocked as ambiguous.")

# --- no matching registered Layer is blocked ------------------------------
r = drc_bridge.copy_magic_drc_check_to_rule(make_width(), CIF, [], [])
assert r.rule is None
assert "No real Layer registered" in r.messages[0]
print("PASS: a resolved GDS pair with no matching registered Layer is correctly blocked.")

# --- an exact duplicate rule already present is not re-created -----------
existing = DesignRule(
    rule_id="BE_Au.drawing.W.1", description="", check_type="min_width", layers=["BE_Au.drawing"], value=0.2,
)
r = drc_bridge.copy_magic_drc_check_to_rule(make_width(), CIF, [LAYER], [existing])
assert r.rule is None
assert "already exists" in r.messages[0]
print("PASS: an exact-duplicate rule already present blocks a second copy.")

# --- a real mode/exception filler is advisory-only, doesn't block --------
r = drc_bridge.copy_magic_drc_check_to_rule(make_width(filler_raw="touching_ok"), CIF, [LAYER], [])
assert r.rule is not None, r.messages
assert len(r.messages) == 1
assert "touching_ok" in r.messages[0]
print("PASS: a real Magic mode/exception filler is reported as advisory but still copies.")

# --- rule_id auto-naming increments per layer/check_type -----------------
first = drc_bridge.copy_magic_drc_check_to_rule(make_width(), CIF, [LAYER], []).rule
second = drc_bridge.copy_magic_drc_check_to_rule(make_width(value=0.25), CIF, [LAYER], [first])
assert second.rule is not None, second.messages
assert first.rule_id != second.rule.rule_id
print(f"PASS: rule_id auto-naming is distinct across repeated real copies ({first.rule_id!r} vs {second.rule.rule_id!r}).")

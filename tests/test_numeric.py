import sys
sys.path.insert(0, "/foss/designs")

from openpdkcreator.pdklib import numeric

# --- Plain decimals, unchanged from bare float()/int() behavior ---
PLAIN_CASES = [
    ("0.2", 0.2), ("-3.5", -3.5), ("+2", 2.0), ("1e3", 1000.0), ("1.5e-2", 0.015),
    (".5", 0.5), ("1", 1.0), ("  0.2  ", 0.2),
]
for text, expected in PLAIN_CASES:
    got = numeric.parse_number(text)
    assert got == expected, (text, got, expected)
print("PASS: plain decimal text (no SI suffix) parses identically to bare float().")

# --- Real, ngspice-manual-sourced SI suffix table, both directions of
# case (lowercase and uppercase all resolve, per the real, confirmed
# "letters immediately following a scale factor are ignored" rule) ---
SI_CASES = [
    ("1t", 1e12), ("1T", 1e12),
    ("1g", 1e9), ("1G", 1e9),
    ("1meg", 1e6), ("1Meg", 1e6), ("1MEG", 1e6),
    ("1k", 1e3), ("1K", 1e3),
    ("1mil", 25.4e-6), ("1MIL", 25.4e-6),
    ("1m", 1e-3), ("1M", 1e-3),
    ("1u", 1e-6), ("1U", 1e-6), ("1µ", 1e-6),
    ("1n", 1e-9), ("1N", 1e-9),
    ("1p", 1e-12), ("1P", 1e-12),
    ("1f", 1e-15), ("1F", 1e-15),
    ("1a", 1e-18), ("1A", 1e-18),
]
for text, expected in SI_CASES:
    got = numeric.parse_number(text)
    assert got is not None and abs(got - expected) <= abs(expected) * 1e-12, (text, got, expected)
print(f"PASS: all {len(SI_CASES)} real, ngspice-manual-sourced SI suffix cases resolve to the exact "
      f"real scale factor.")

# --- The real, well-known SPICE trap: bare "m"/"M" is always milli,
# never mega -- only "meg" (any case) means mega. Confirmed directly
# from the manual's own real worked examples. ---
assert numeric.parse_number("0.2u") == 0.2e-6
assert numeric.parse_number("0.2U") == 0.2e-6
assert numeric.parse_number("1.5MEGOHM") == 1.5e6  # trailing letters after "meg" ignored
assert numeric.parse_number("1MA") == 0.001  # "M" = milli, "A" ignored (real ngspice example)
assert numeric.parse_number("1MSec") == 0.001  # real ngspice example
assert numeric.parse_number("1MMhos") == 0.001  # real ngspice example
assert numeric.parse_number("10Hz") == 10.0  # no recognized suffix -- trailing unit ignored
assert numeric.parse_number("5V") == 5.0
print("PASS: bare 'm'/'M' is always milli, never mega; only 'meg' (any case) means mega -- the real, "
      "well-known SPICE trap this module is deliberately not caught by.")

# --- Invalid input: honest None, same as the old except ValueError: pass ---
for bad in ("", None, "abc", "u", "--1", "1.2.3"):
    assert numeric.parse_number(bad) is None, bad
print("PASS: invalid/empty text returns None, never raises, matching every real caller's old "
      "except ValueError: pass shape.")

# --- parse_int: plain, deliberately not SI-scaled (no physical unit
# a layer number/degree count/rank could sensibly take a prefix on) ---
INT_CASES = [("42", 42), ("-3", -3), ("  7 ", 7)]
for text, expected in INT_CASES:
    assert numeric.parse_int(text) == expected, (text, numeric.parse_int(text), expected)
for bad in ("", None, "1.5", "abc", "1u"):
    assert numeric.parse_int(bad) is None, bad
print("PASS: parse_int handles plain integers and honestly refuses anything else (including a real "
      "SI-suffixed string, since an int field has no physical unit to scale).")

# --- Real, driven, in-GUI confirmation: DRC Rules' own Value field
# (gui/rules_view.py) accepts a real SI-suffixed value end-to-end, not
# just via the standalone parse_number call above ---
import tkinter as tk
from pathlib import Path
import shutil

from openpdkcreator.gui.app import App
from openpdkcreator.pdklib import skeleton as skeleton_mod

PDK_ROOT = Path("/tmp/numeric_test_pdk")
shutil.rmtree(PDK_ROOT, ignore_errors=True)
skeleton_mod.build_blank_pdk(PDK_ROOT)

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()
app._new_drc_deck()
root.update()

app.rules_view._new_rule()
root.update()
rule = app.project.design_rules[-1]
app.rules_view._load_rule_into_form(rule)
root.update()
app.rules_view.vars["value"].set("0.2u")
root.update()
assert rule.value == 0.2e-6, rule.value
print("PASS: DRC Rules' own real Value field accepts a real SI-suffixed entry ('0.2u') end-to-end "
      "through the actual Tk form, not just via a standalone parse_number call.")

app.rules_view.vars["value"].set("0.5")
root.update()
assert rule.value == 0.5, rule.value
print("PASS: a plain, un-suffixed Value entry still parses identically to before.")

app.rules_view.vars["value"].set("")
root.update()
assert rule.value is None
print("PASS: clearing the Value field still sets it to None, same as before this change.")

root.destroy()
print("ALL NUMERIC TESTS PASS")

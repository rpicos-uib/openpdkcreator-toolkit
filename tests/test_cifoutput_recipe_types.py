import sys
sys.path.insert(0, "/foss/designs")
from pathlib import Path

from openpdkcreator.pdklib import magic_tech as mt
from openpdkcreator.pdklib import magic_tech_writer as mtw

PATH = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2/libs.tech/magic/ihp-sg13g2-cifout.tech")

# --- real, bare 'layer NAME TYPE ... calma L D' pass-throughs are captured;
# real geometry-recipe-in-between blocks correctly stay unresolved -------
tech = mt.parse_tech_file(PATH)
print("real cif_layers entries:", len(tech.cif_layers))
assert len(tech.cif_layers) > 0

with_types = [c for c in tech.cif_layers if c.recipe_types]
without_types = [c for c in tech.cif_layers if not c.recipe_types]
print("with real recipe_types (bare pass-through):", len(with_types))
print("without (real geometry recipe in between):", len(without_types))
assert len(with_types) > 0
assert len(without_types) > 0

by_name = {c.name: c for c in tech.cif_layers}
assert by_name["DIGITALID"].recipe_types == ("digisub",)
assert by_name["BIPOLARID"].recipe_types == ("trans",)
# A real, comma-separated multi-type pass-through.
assert by_name["EMITTER"].recipe_types == ("nec", "gec")
# A real block with a genuine geometry-recipe line before calma
# ('and-not schottkyarea') must NOT get a guessed recipe_types.
assert by_name["NWELL"].recipe_types == ()
print("PASS: real bare pass-through recipe_types are captured; real geometry-recipe blocks correctly aren't.")

# --- purely additive: no-edit export stays byte-identical ----------------
rendered = mtw.render_tech_file(PATH, tech)
original = PATH.read_text(encoding="utf-8", errors="replace")
if not original.endswith("\n"):
    original += "\n"
assert rendered == original
print("PASS: recipe_types is parse-only -- no-edit export of the real cifout fragment is still byte-identical.")

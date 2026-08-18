import sys
sys.path.insert(0, "/foss/designs")
from pathlib import Path

from openpdkcreator.pdklib import lef as lef_mod
from openpdkcreator.pdklib import lef_writer as lef_writer_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
LEF_PATH = PDK_ROOT / "libs.ref" / "sg13g2_stdcell" / "lef" / "sg13g2_stdcell.lef"

# --- Real ORIGIN parsing: every real macro's own ORIGIN is (0.0, 0.0) ---
tech = lef_mod.parse_lef_file(LEF_PATH)
print("macros:", len(tech.macros))
assert len(tech.macros) == 84
assert all(m.origin == (0.0, 0.0) for m in tech.macros)
print("PASS: every real macro's own ORIGIN statement parses to the real, confirmed (0.0, 0.0).")

# --- No-edit export is still byte-identical now that ORIGIN is parsed ---
rendered = lef_writer_mod.render_lef_file(LEF_PATH, tech)
original = LEF_PATH.read_text(encoding="utf-8", errors="replace")
if not original.endswith("\n"):
    original += "\n"
assert rendered == original
print("PASS: no-edit export is still byte-identical now that ORIGIN is parsed.")

# --- A brand-new macro gets a real ORIGIN 0 0 ; line automatically,
# plus SITE when set, in the same real order IHP's own headers use ---
new_macro = lef_mod.LefMacro(name="ZZ_ORIGIN_TEST", origin=(0.0, 0.0), site="CoreSite")
tech.macros.append(new_macro)
rendered2 = lef_writer_mod.render_lef_file(LEF_PATH, tech)
start = rendered2.index("MACRO ZZ_ORIGIN_TEST")
end = rendered2.index("END ZZ_ORIGIN_TEST") + len("END ZZ_ORIGIN_TEST")
block = rendered2[start:end]
print("new macro block:", repr(block))
assert "ORIGIN 0 0 ;" in block
assert "SITE CoreSite ;" in block
assert block.index("ORIGIN") < block.index("SITE")
print("PASS: a brand-new macro's own real block includes a real 'ORIGIN 0 0 ;' line before 'SITE ... ;'.")

export_path = Path("/tmp/test_export_lef_origin.lef")
export_path.write_text(rendered2, encoding="utf-8")
reparsed = lef_mod.parse_lef_file(export_path)
re_macro = next(m for m in reparsed.macros if m.name == "ZZ_ORIGIN_TEST")
assert re_macro.origin == (0.0, 0.0)
assert re_macro.site == "CoreSite"
assert len(reparsed.macros) == 85
print("PASS: the brand-new macro's own real ORIGIN/SITE round-trip correctly through a fresh re-parse.")

print("ALL LEF MACRO ORIGIN TESTS PASS")

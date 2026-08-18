import sys
sys.path.insert(0, "/foss/designs")
import dataclasses
from pathlib import Path

from openpdkcreator.pdklib import lef as lef_mod
from openpdkcreator.pdklib import lef_writer

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
STDCELL = PDK_ROOT / "libs.ref/sg13g2_stdcell/lef/sg13g2_stdcell.lef"
IO = PDK_ROOT / "libs.ref/sg13g2_io/lef/sg13g2_io.lef"
TECH = PDK_ROOT / "libs.ref/sg13g2_sram/lef/RM_IHPSG13_1P_1024x16_c2_bm_bist.lef"

# --- Test 1: no-edit export == byte-identical original, for several real files ---
for path in (STDCELL, IO, TECH):
    parsed = lef_mod.parse_lef_file(path)
    rendered = lef_writer.render_lef_file(path, parsed)
    original = path.read_text(encoding="utf-8", errors="replace")
    if not original.endswith("\n"):
        original += "\n"
    assert rendered == original, f"no-edit export mismatch for {path.name}"
    print(f"PASS: no-edit export of {path.name} ({len(parsed.macros)} macros) is byte-identical to the original.")

# --- Test 2: edit a pin's direction/use, export, re-parse, confirm ---
parsed = lef_mod.parse_lef_file(STDCELL)
macro = next(m for m in parsed.macros if m.name == "sg13g2_a21o_1")
pin = next(p for p in macro.pins if p.name == "A2")
original_direction, original_use = pin.direction, pin.use
pin.direction = "OUTPUT"
pin.use = "POWER"

export_path = Path("/tmp/test_export_stdcell.lef")
lef_writer.export_lef_file(parsed, export_path)
reparsed = lef_mod.parse_lef_file(export_path)

assert len(reparsed.macros) == len(parsed.macros) == 84, len(reparsed.macros)
re_macro = next(m for m in reparsed.macros if m.name == "sg13g2_a21o_1")
re_pin = next(p for p in re_macro.pins if p.name == "A2")
assert re_pin.direction == "OUTPUT" and re_pin.use == "POWER"
print(f"PASS: edited pin A2 ({original_direction}/{original_use} -> OUTPUT/POWER) reflected correctly in re-parsed export.")

# Confirm every OTHER pin/macro is untouched (compare against a truly fresh parse).
fresh = lef_mod.parse_lef_file(STDCELL)
assert len(fresh.macros) == len(reparsed.macros)
mismatches = []
for fm, rm in zip(fresh.macros, reparsed.macros):
    assert fm.name == rm.name
    if fm.name == "sg13g2_a21o_1":
        continue
    if [(p.name, p.direction, p.use, len(p.ports)) for p in fm.pins] != [(p.name, p.direction, p.use, len(p.ports)) for p in rm.pins]:
        mismatches.append(fm.name)
    if (fm.macro_class, fm.size, fm.site, fm.obs_layers) != (rm.macro_class, rm.size, rm.site, rm.obs_layers):
        mismatches.append(fm.name + " (macro fields)")
assert not mismatches, f"unexpected differences in untouched macros: {mismatches}"
print(f"PASS: all {len(fresh.macros) - 1} other macros in the export are unchanged vs. a fresh parse.")

# Also confirm the edited pin's ports (real geometry, untouched) survived intact.
orig_ports = [(p.layer, p.rect_count) for p in fresh.macros[
    [m.name for m in fresh.macros].index("sg13g2_a21o_1")
].pins[[p.name for p in macro.pins].index("A2")].ports]
re_ports = [(p.layer, p.rect_count) for p in re_pin.ports]
assert orig_ports == re_ports, (orig_ports, re_ports)
print(f"PASS: edited pin's real PORT geometry preserved exactly: {re_ports}")

# --- Test 3: new pin ---
parsed2 = lef_mod.parse_lef_file(STDCELL)
macro2 = next(m for m in parsed2.macros if m.name == "sg13g2_a21o_1")
new_pin = lef_mod.LefPin(name="ZZ_NEW_PIN", direction="OUTPUT", use="SIGNAL")
macro2.pins.append(new_pin)
export_path2 = Path("/tmp/test_export_newpin.lef")
lef_writer.export_lef_file(parsed2, export_path2)
reparsed2 = lef_mod.parse_lef_file(export_path2)
re_macro2 = next(m for m in reparsed2.macros if m.name == "sg13g2_a21o_1")
assert len(re_macro2.pins) == 7, len(re_macro2.pins)
re_new_pin = next(p for p in re_macro2.pins if p.name == "ZZ_NEW_PIN")
assert re_new_pin.direction == "OUTPUT" and re_new_pin.use == "SIGNAL"
assert re_new_pin.ports == []
print("PASS: a brand-new pin (New Pin) is exported correctly and re-parses with the right fields.")

# --- Test 4: deleted pin ---
parsed3 = lef_mod.parse_lef_file(STDCELL)
macro3 = next(m for m in parsed3.macros if m.name == "sg13g2_a21o_1")
original_pin_count = len(macro3.pins)
deleted_pin = next(p for p in macro3.pins if p.name == "B1")
macro3.pins.remove(deleted_pin)
export_path3 = Path("/tmp/test_export_delpin.lef")
lef_writer.export_lef_file(parsed3, export_path3)
reparsed3 = lef_mod.parse_lef_file(export_path3)
re_macro3 = next(m for m in reparsed3.macros if m.name == "sg13g2_a21o_1")
assert len(re_macro3.pins) == original_pin_count - 1
assert "B1" not in [p.name for p in re_macro3.pins]
assert [p.name for p in re_macro3.pins] == [p.name for p in macro3.pins]
print(f"PASS: a deleted pin (B1) is correctly omitted from the export ({original_pin_count} -> {len(re_macro3.pins)} pins).")

# --- Test 5: SRAM per-macro file (single, large macro with many real pins) ---
sram_parsed = lef_mod.parse_lef_file(TECH)
sram_rendered = lef_writer.render_lef_file(TECH, sram_parsed)
sram_original = TECH.read_text(encoding="utf-8", errors="replace")
if not sram_original.endswith("\n"):
    sram_original += "\n"
assert sram_rendered == sram_original
sram_macro = sram_parsed.macros[0]
sram_pin = sram_macro.pins[0]
sram_pin.direction = "INOUT" if sram_pin.direction != "INOUT" else "INPUT"
export_path5 = Path("/tmp/test_export_sram.lef")
lef_writer.export_lef_file(sram_parsed, export_path5)
reparsed5 = lef_mod.parse_lef_file(export_path5)
assert reparsed5.macros[0].pins[0].direction == sram_pin.direction
assert len(reparsed5.macros[0].pins) == len(sram_macro.pins)
print(f"PASS: SRAM hard-macro file ({len(sram_macro.pins)} real pins) no-edit byte-identical, and a real pin edit round-trips.")

# --- Test 6: new macro (New Macro...) ---
parsed6 = lef_mod.parse_lef_file(STDCELL)
original_macro_count = len(parsed6.macros)
new_macro = lef_mod.LefMacro(name="ZZ_NEW_MACRO", macro_class="CORE", size=(2.0, 3.0), symmetry=["X", "Y"])
new_macro.pins.append(lef_mod.LefPin(name="A", direction="INPUT", use="SIGNAL"))
new_macro.pins.append(lef_mod.LefPin(name="Y", direction="OUTPUT", use="SIGNAL"))
parsed6.macros.append(new_macro)
export_path6 = Path("/tmp/test_export_newmacro.lef")
lef_writer.export_lef_file(parsed6, export_path6)
reparsed6 = lef_mod.parse_lef_file(export_path6)
assert len(reparsed6.macros) == original_macro_count + 1
re_new_macro = reparsed6.macros[-1]
assert re_new_macro.name == "ZZ_NEW_MACRO"
assert re_new_macro.macro_class == "CORE"
assert re_new_macro.size == (2.0, 3.0)
assert re_new_macro.symmetry == ["X", "Y"]
assert [p.name for p in re_new_macro.pins] == ["A", "Y"]
assert [p.direction for p in re_new_macro.pins] == ["INPUT", "OUTPUT"]
# Every real, existing macro stays byte-for-byte the same as a fresh parse.
fresh6 = lef_mod.parse_lef_file(STDCELL)
for fm, rm in zip(fresh6.macros, reparsed6.macros[:-1]):
    assert fm.name == rm.name
    assert [(p.name, p.direction, p.use) for p in fm.pins] == [(p.name, p.direction, p.use) for p in rm.pins]
print(
    f"PASS: New Macro (ZZ_NEW_MACRO, 2 real pins) exports as a whole, freshly-generated block "
    f"after all {original_macro_count} real, existing macros, none of which changed."
)

print("ALL PASS")

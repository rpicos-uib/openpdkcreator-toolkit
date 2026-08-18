import sys
sys.path.insert(0, "/foss/designs")
from pathlib import Path

from openpdkcreator.pdklib import netlist as nl
from openpdkcreator.pdklib import netlist_writer as nlw
from openpdkcreator.pdklib import verilog as vl
from openpdkcreator.pdklib import verilog_writer as vlw

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

# --- Test 1: no-edit byte-identical across EVERY real .cdl/.spice/.v file ---
mismatches = []
total_cdl = total_spice = total_v = 0
for path in sorted(PDK_ROOT.glob("libs.ref/*/cdl/*.cdl")):
    cells = nl.find_cells(path)
    rendered = nlw.render_netlist_file(path, cells)
    original = path.read_text(encoding="utf-8", errors="replace")
    total_cdl += 1
    if rendered != original:
        mismatches.append(("cdl", path))

for path in sorted(PDK_ROOT.glob("libs.ref/*/spice/*.spice")):
    cells = nl.find_cells(path)
    rendered = nlw.render_netlist_file(path, cells)
    original = path.read_text(encoding="utf-8", errors="replace")
    total_spice += 1
    if rendered != original:
        mismatches.append(("spice", path))

for path in sorted(PDK_ROOT.glob("libs.ref/*/verilog/*.v")):
    modules = vl.find_modules(path)
    rendered = vlw.render_verilog_file(path, modules)
    original = path.read_text(encoding="utf-8", errors="replace")
    total_v += 1
    if rendered != original:
        mismatches.append(("verilog", path))

if mismatches:
    for kind, path in mismatches[:5]:
        print(f"MISMATCH ({kind}): {path}")
        if kind in ("cdl", "spice"):
            cells = nl.find_cells(path)
            rendered = nlw.render_netlist_file(path, cells)
        else:
            modules = vl.find_modules(path)
            rendered = vlw.render_verilog_file(path, modules)
        original = path.read_text(encoding="utf-8", errors="replace")
        if not original.endswith("\n"):
            original += "\n"
        r_lines, o_lines = rendered.splitlines(), original.splitlines()
        for i, (a, b) in enumerate(zip(r_lines, o_lines)):
            if a != b:
                print(f"  first diff at line {i+1}:")
                print(f"    rendered: {a!r}")
                print(f"    original: {b!r}")
                break
        else:
            print(f"  length mismatch: {len(r_lines)} vs {len(o_lines)}")
    raise SystemExit(f"\n{len(mismatches)} MISMATCH(ES) out of {total_cdl} cdl + {total_spice} spice + {total_v} verilog files")

print(f"PASS: all {total_cdl} real .cdl + {total_spice} real .spice + {total_v} real .v files are byte-identical on no-edit export.")

# --- Test 2: CDL edit round-trip (direction change + PININFO regen) ---
path = PDK_ROOT / "libs.ref/sg13g2_stdcell/cdl/sg13g2_stdcell.cdl"
cells = nl.find_cells(path)
cell = next(c for c in cells if c.name == "sg13g2_a21o_1")
port = next(p for p in cell.ports if p.name == "X")
port.direction = "INPUT"
export_path = Path("/tmp/test_export_cdl.cdl")
nlw.export_netlist_file(cells, path, export_path)
reparsed = nl.find_cells(export_path)
re_cell = next(c for c in reparsed if c.name == "sg13g2_a21o_1")
re_port = next(p for p in re_cell.ports if p.name == "X")
assert re_port.direction == "INPUT", re_port.direction
print("PASS: CDL port direction edit (X: OUTPUT -> INPUT) round-trips through the real PININFO line.")

# Confirm all OTHER cells in the file are untouched.
fresh = nl.find_cells(path)
mismatches2 = []
for fc, rc in zip(fresh, reparsed):
    if fc.name == "sg13g2_a21o_1":
        continue
    if [(p.name, p.direction) for p in fc.ports] != [(p.name, p.direction) for p in rc.ports]:
        mismatches2.append(fc.name)
assert not mismatches2, mismatches2
print(f"PASS: all {len(fresh) - 1} other CDL cells in the file are unchanged.")

# --- Test 3: new port + delete port (CDL) ---
cells3 = nl.find_cells(path)
cell3 = next(c for c in cells3 if c.name == "sg13g2_a21o_1")
new_port = nl.NetlistPort(name="ZZ_NEW", direction="INPUT")
cell3.ports.append(new_port)
deleted = next(p for p in cell3.ports if p.name == "B1")
cell3.ports.remove(deleted)
export_path3 = Path("/tmp/test_export_cdl_addremove.cdl")
nlw.export_netlist_file(cells3, path, export_path3)
reparsed3 = nl.find_cells(export_path3)
re_cell3 = next(c for c in reparsed3 if c.name == "sg13g2_a21o_1")
names3 = [p.name for p in re_cell3.ports]
assert "ZZ_NEW" in names3 and "B1" not in names3
re_new = next(p for p in re_cell3.ports if p.name == "ZZ_NEW")
assert re_new.direction == "INPUT"
print(f"PASS: CDL new port + deleted port round-trip correctly: {names3}")

# --- Test 4: SRAM CDL cell with no real PININFO -- assign a direction, expect a fresh PININFO line ---
sram_path = PDK_ROOT / "libs.ref/sg13g2_sram/cdl/RM_IHPSG13_1P_1024x16_c2_bm_bist.cdl"
sram_cells = nl.find_cells(sram_path)
sram_top = next(c for c in sram_cells if c.name == "RM_IHPSG13_1P_1024x16_c2_bm_bist")
assert sram_top.pininfo_line_no == 0
sram_port = sram_top.ports[0]
sram_port.direction = "INPUT"
export_path4 = Path("/tmp/test_export_sram_cdl.cdl")
nlw.export_netlist_file(sram_cells, sram_path, export_path4)
reparsed4 = nl.find_cells(export_path4)
re_top4 = next(c for c in reparsed4 if c.name == "RM_IHPSG13_1P_1024x16_c2_bm_bist")
assert re_top4.pininfo_line_no != 0, "expected a fresh PININFO line to be inserted"
re_port4 = next(p for p in re_top4.ports if p.name == sram_port.name)
assert re_port4.direction == "INPUT"
print(f"PASS: SRAM CDL cell with no real PININFO gets a fresh one inserted when a direction is assigned.")

# Confirm all OTHER sram cells in that huge file are unaffected.
fresh_sram = nl.find_cells(sram_path)
assert len(fresh_sram) == len(reparsed4)
mismatches4 = []
for fc, rc in zip(fresh_sram, reparsed4):
    if fc.name == sram_top.name:
        continue
    if [p.name for p in fc.ports] != [p.name for p in rc.ports]:
        mismatches4.append(fc.name)
assert not mismatches4, mismatches4[:5]
print(f"PASS: all {len(fresh_sram) - 1} other real SRAM CDL cells (including many with real + continuations) are unchanged.")

# --- Test 5: Verilog edit round-trip on a simple stdcell module ---
v_path = PDK_ROOT / "libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v"
modules = vl.find_modules(v_path)
module = next(m for m in modules if m.name == "sg13g2_a21o_1")
vport = next(p for p in module.ports if p.name == "X")
assert vport.direction == "output"
vport.direction = "inout"
export_path5 = Path("/tmp/test_export_verilog.v")
vlw.export_verilog_file(modules, v_path, export_path5)
reparsed5 = vl.find_modules(export_path5)
re_module5 = next(m for m in reparsed5 if m.name == "sg13g2_a21o_1")
re_vport5 = next(p for p in re_module5.ports if p.name == "X")
assert re_vport5.direction == "inout", re_vport5.direction
print("PASS: Verilog port direction edit (X: output -> inout) round-trips.")

fresh_v = vl.find_modules(v_path)
mismatches5 = []
for fm, rm in zip(fresh_v, reparsed5):
    if fm.name == "sg13g2_a21o_1":
        continue
    if [(p.name, p.direction, p.width) for p in fm.ports] != [(p.name, p.direction, p.width) for p in rm.ports]:
        mismatches5.append(fm.name)
assert not mismatches5, mismatches5
print(f"PASS: all {len(fresh_v) - 1} other real Verilog modules in the file are unchanged.")

# --- Test 6: Verilog on the multi-line-header SRAM module, with a real bus port ---
sram_v_path = PDK_ROOT / "libs.ref/sg13g2_sram/verilog/RM_IHPSG13_1P_1024x16_c2_bm_bist.v"
sram_modules = vl.find_modules(sram_v_path)
sram_module = sram_modules[0]
addr_port = next(p for p in sram_module.ports if p.name == "A_ADDR")
assert addr_port.width == "[9:0]"
addr_port.width = "[10:0]"  # widen it
export_path6 = Path("/tmp/test_export_sram_verilog.v")
vlw.export_verilog_file(sram_modules, sram_v_path, export_path6)
reparsed6 = vl.find_modules(export_path6)
assert len(reparsed6) == 1
re_addr6 = next(p for p in reparsed6[0].ports if p.name == "A_ADDR")
assert re_addr6.width == "[10:0]", re_addr6.width
print("PASS: real multi-line-header SRAM Verilog module's bus port width edit round-trips.")

# All other ports on that same module unchanged.
fresh_sram_v = vl.find_modules(sram_v_path)[0]
mismatches6 = []
for fp, rp in zip(fresh_sram_v.ports, reparsed6[0].ports):
    if fp.name == "A_ADDR":
        continue
    if (fp.name, fp.direction, fp.width) != (rp.name, rp.direction, rp.width):
        mismatches6.append(fp.name)
assert not mismatches6, mismatches6
print(f"PASS: all {len(fresh_sram_v.ports) - 1} other real ports on the SRAM module are unchanged.")

print("ALL PASS")

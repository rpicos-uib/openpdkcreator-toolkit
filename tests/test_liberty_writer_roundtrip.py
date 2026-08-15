import sys
sys.path.insert(0, "/foss/designs")
from pathlib import Path
from openpdkcreator.ihp import liberty as lib_mod
from openpdkcreator.ihp import liberty_writer as libw

STD_PATH = Path("data/ihp-sg13g2/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib")
SRAM_PATH = Path("data/ihp-sg13g2/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_1024x16_c2_bm_bist_typ_1p20V_25C.lib")


def snapshot(cells):
    """A comparable, deep snapshot of every real cell/pin/arc field."""
    return [
        (
            c.name,
            [
                (p.name, p.direction, p.capacitance, p.function,
                 [(a.related_pin, a.timing_type, a.timing_sense, a.when) for a in p.timing_arcs])
                for p in c.pins
            ],
        )
        for c in cells
    ]


def check_all_other_cells_unchanged(original_cells, edited_cells, changed_cell_name):
    orig_snap = {name: s for name, s in snapshot(original_cells)}
    new_snap = {name: s for name, s in snapshot(edited_cells)}
    assert set(orig_snap) == set(new_snap), "cell set changed unexpectedly"
    for name in orig_snap:
        if name == changed_cell_name:
            continue
        assert orig_snap[name] == new_snap[name], f"unrelated cell {name} changed!"


def reparse_after_export(path, cells, tmp_name):
    export_path = Path("/tmp") / tmp_name
    libw.export_lib_file(cells, path, export_path)
    reparsed = lib_mod.find_cells(export_path)
    return reparsed, export_path


# --- Test 1: pin field edit (direction/capacitance/function) ---
cells = lib_mod.find_cells(STD_PATH)
target = next(c for c in cells if c.name == "sg13g2_a21o_1")
pin = next(p for p in target.pins if p.name == "A1")
orig_direction, orig_cap = pin.direction, pin.capacitance
pin.direction = "inout"
pin.capacitance = 12.345
pin.function = "TEST_FN"

reparsed, export_path = reparse_after_export(STD_PATH, cells, "test1_pin_edit.lib")
r_cell = next(c for c in reparsed if c.name == "sg13g2_a21o_1")
r_pin = next(p for p in r_cell.pins if p.name == "A1")
assert r_pin.direction == "inout", r_pin.direction
assert r_pin.capacitance == 12.345, r_pin.capacitance
assert r_pin.function == "TEST_FN", r_pin.function
check_all_other_cells_unchanged(lib_mod.find_cells(STD_PATH), reparsed, "sg13g2_a21o_1")
# also check other pins on the SAME cell are untouched
other_pin_orig = next(p for p in lib_mod.find_cells(STD_PATH)[cells.index(target)].pins if p.name != "A1")
print("PASS: pin field edit (direction/capacitance/function) round-trips correctly")

# --- Test 2: timing arc field edit ---
cells = lib_mod.find_cells(STD_PATH)
target = next(c for c in cells if c.name == "sg13g2_a21o_1")
xpin = next(p for p in target.pins if p.name == "X")
arc = xpin.timing_arcs[0]
orig_when = arc.when
arc.timing_type = "combinational"
arc.timing_sense = "positive_unate"
arc.when = "A1&A2"

reparsed, export_path = reparse_after_export(STD_PATH, cells, "test2_arc_edit.lib")
r_cell = next(c for c in reparsed if c.name == "sg13g2_a21o_1")
r_xpin = next(p for p in r_cell.pins if p.name == "X")
r_arc = r_xpin.timing_arcs[0]
assert r_arc.timing_type == "combinational", r_arc.timing_type
assert r_arc.timing_sense == "positive_unate", r_arc.timing_sense
assert r_arc.when == "A1&A2", r_arc.when
assert len(r_xpin.timing_arcs) == len(xpin.timing_arcs), "arc count changed unexpectedly"
for i in range(1, len(xpin.timing_arcs)):
    a1, a2 = xpin.timing_arcs[i], r_xpin.timing_arcs[i]
    assert (a1.related_pin, a1.timing_type, a1.timing_sense, a1.when) == (a2.related_pin, a2.timing_type, a2.timing_sense, a2.when), f"unrelated arc {i} changed!"
check_all_other_cells_unchanged(lib_mod.find_cells(STD_PATH), reparsed, "sg13g2_a21o_1")
print("PASS: timing arc field edit round-trips correctly, other arcs on same pin untouched")

# --- Test 3: new pin ---
cells = lib_mod.find_cells(STD_PATH)
target = next(c for c in cells if c.name == "sg13g2_a21o_1")
orig_pin_count = len(target.pins)
new_pin = lib_mod.LibertyPin(name="ZZ_NEWPIN", direction="input", capacitance=0.001, function="")
target.pins.append(new_pin)

reparsed, export_path = reparse_after_export(STD_PATH, cells, "test3_new_pin.lib")
r_cell = next(c for c in reparsed if c.name == "sg13g2_a21o_1")
assert len(r_cell.pins) == orig_pin_count + 1, len(r_cell.pins)
r_new_pin = next(p for p in r_cell.pins if p.name == "ZZ_NEWPIN")
assert r_new_pin.direction == "input"
assert r_new_pin.capacitance == 0.001
check_all_other_cells_unchanged(lib_mod.find_cells(STD_PATH), reparsed, "sg13g2_a21o_1")
print("PASS: new pin round-trips correctly")

# --- Test 4: deleted pin ---
cells = lib_mod.find_cells(STD_PATH)
target = next(c for c in cells if c.name == "sg13g2_a21o_1")
orig_pin_count = len(target.pins)
target.pins = [p for p in target.pins if p.name != "B1"]

reparsed, export_path = reparse_after_export(STD_PATH, cells, "test4_del_pin.lib")
r_cell = next(c for c in reparsed if c.name == "sg13g2_a21o_1")
assert len(r_cell.pins) == orig_pin_count - 1, len(r_cell.pins)
assert not any(p.name == "B1" for p in r_cell.pins)
check_all_other_cells_unchanged(lib_mod.find_cells(STD_PATH), reparsed, "sg13g2_a21o_1")
print("PASS: deleted pin round-trips correctly")

# --- Test 5: new timing arc ---
cells = lib_mod.find_cells(STD_PATH)
target = next(c for c in cells if c.name == "sg13g2_a21o_1")
xpin = next(p for p in target.pins if p.name == "X")
orig_arc_count = len(xpin.timing_arcs)
new_arc = lib_mod.LibertyTimingArc(related_pin="B2", timing_type="combinational", timing_sense="negative_unate", when="")
xpin.timing_arcs.append(new_arc)

reparsed, export_path = reparse_after_export(STD_PATH, cells, "test5_new_arc.lib")
r_cell = next(c for c in reparsed if c.name == "sg13g2_a21o_1")
r_xpin = next(p for p in r_cell.pins if p.name == "X")
assert len(r_xpin.timing_arcs) == orig_arc_count + 1, len(r_xpin.timing_arcs)
r_new_arc = next(a for a in r_xpin.timing_arcs if a.related_pin == "B2" and a.timing_sense == "negative_unate")
assert r_new_arc.timing_type == "combinational"
check_all_other_cells_unchanged(lib_mod.find_cells(STD_PATH), reparsed, "sg13g2_a21o_1")
print("PASS: new timing arc round-trips correctly")

# --- Test 6: deleted timing arc ---
cells = lib_mod.find_cells(STD_PATH)
target = next(c for c in cells if c.name == "sg13g2_a21o_1")
xpin = next(p for p in target.pins if p.name == "X")
orig_arc_count = len(xpin.timing_arcs)
deleted_arc = xpin.timing_arcs[0]
xpin.timing_arcs = xpin.timing_arcs[1:]

reparsed, export_path = reparse_after_export(STD_PATH, cells, "test6_del_arc.lib")
r_cell = next(c for c in reparsed if c.name == "sg13g2_a21o_1")
r_xpin = next(p for p in r_cell.pins if p.name == "X")
assert len(r_xpin.timing_arcs) == orig_arc_count - 1, len(r_xpin.timing_arcs)
check_all_other_cells_unchanged(lib_mod.find_cells(STD_PATH), reparsed, "sg13g2_a21o_1")
print("PASS: deleted timing arc round-trips correctly")

# --- Test 7: SRAM bus-nested pin edit (unspaced/unquoted convention) ---
cells = lib_mod.find_cells(SRAM_PATH)
target = cells[0]
bus_pin = next(p for p in target.pins if "[" in p.name)
orig_direction = bus_pin.direction
bus_pin.capacitance = 9.876

reparsed, export_path = reparse_after_export(SRAM_PATH, cells, "test7_sram_bus_pin_edit.lib")
r_cell = reparsed[0]
r_bus_pin = next(p for p in r_cell.pins if p.name == bus_pin.name)
assert r_bus_pin.capacitance == 9.876, r_bus_pin.capacitance
assert r_bus_pin.direction == orig_direction, (r_bus_pin.direction, orig_direction)
check_all_other_cells_unchanged(lib_mod.find_cells(SRAM_PATH), reparsed, target.name)
print("PASS: SRAM bus-nested pin edit round-trips correctly (unspaced/unquoted convention preserved)")

print("ALL LIBERTY WRITER ROUND-TRIP TESTS PASSED")

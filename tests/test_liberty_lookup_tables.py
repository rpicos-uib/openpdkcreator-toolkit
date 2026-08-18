import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.pdklib import liberty as liberty_mod
from openpdkcreator.gui.liberty_editor import LibertyPinEditor

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

# --- Real parser coverage: Shape A (index_1/index_2 + values, the
# common case) and Shape B (values-only, real, confirmed minority) ---
stdcell_path = PDK_ROOT / "libs.ref" / "sg13g2_stdcell" / "lib" / "sg13g2_stdcell_typ_1p20V_25C.lib"
stdcell_cells = liberty_mod.find_cells(stdcell_path)
a21o = next(c for c in stdcell_cells if c.name == "sg13g2_a21o_1")

# --- Real, confirmed unit variance across the deck: stdcell declares
# "1ns"/"(1,pf)", sg13g2_io_dummy declares "1ps"/"(1,ff)" -- captured
# per-cell from the enclosing real library group, never assumed. ---
assert a21o.time_unit == "1ns"
assert a21o.capacitive_load_unit == "1,pf"
print("PASS: LibertyCell captures the real, declared time_unit/capacitive_load_unit (sg13g2_stdcell: 1ns/1,pf).")

pin_x = next(p for p in a21o.pins if p.name == "X")
assert pin_x.timing_arcs, "expected real timing arcs on sg13g2_a21o_1's X pin"
arc = pin_x.timing_arcs[0]
assert arc.lookup_tables, "expected real lookup tables nested inside the first real timing arc"
kinds_present = {lt.kind for lt in arc.lookup_tables}
assert kinds_present <= set(liberty_mod._LOOKUP_TABLE_KINDS)
shape_a = next(lt for lt in arc.lookup_tables if lt.index_1 is not None)
assert shape_a.index_1 == [0.0186, 0.0966, 0.174, 0.3294, 0.6408, 1.263, 2.5074]
assert shape_a.index_2 == [0.001, 0.0234, 0.039, 0.0648, 0.108, 0.18, 0.3]
assert len(shape_a.values) == 7 and len(shape_a.values[0]) == 7
print("PASS: Shape A (index_1 + index_2 + values) parses correctly on a real sg13g2_stdcell arc.")

dummy_path = PDK_ROOT / "libs.ref" / "sg13g2_io" / "lib" / "sg13g2_io_dummy.lib"
dummy_cells = liberty_mod.find_cells(dummy_path)
found_shape_b = None
for c in dummy_cells:
    for p in c.pins:
        for a in p.timing_arcs:
            for lt in a.lookup_tables:
                if lt.index_1 is None and lt.values:
                    found_shape_b = lt
                    break
assert found_shape_b is not None, "expected at least one real values-only lookup table in sg13g2_io_dummy.lib"
assert found_shape_b.index_1 is None and found_shape_b.index_2 is None
assert found_shape_b.values and all(len(row) == 2 for row in found_shape_b.values)
print("PASS: Shape B (values-only, no index_1/index_2) parses correctly on a real sg13g2_io_dummy arc.")

dummy_cell_with_arc = next(c for c in dummy_cells for p in c.pins for a in p.timing_arcs if found_shape_b in a.lookup_tables)
assert dummy_cell_with_arc.time_unit == "1ps"
assert dummy_cell_with_arc.capacitive_load_unit == "1,ff"
print("PASS: sg13g2_io_dummy's own real cells carry the real, DIFFERENT unit (1ps/1,ff) -- confirms real "
      "unit variance within the same deck, not a fixed project-wide assumption.")

# --- Real, exhaustive scan of the whole deck: no real lookup table is
# ever missing 'values' (confirmed, not assumed) ---
total_lt = 0
missing_values = 0
shape_b_count = 0
for lib_path in PDK_ROOT.rglob("*.lib"):
    for cell in liberty_mod.find_cells(lib_path):
        for pin in cell.pins:
            for timing_arc in pin.timing_arcs:
                for lt in timing_arc.lookup_tables:
                    total_lt += 1
                    if not lt.values:
                        missing_values += 1
                    if lt.index_1 is None:
                        shape_b_count += 1
assert total_lt > 0
assert missing_values == 0, "a real lookup table with no values would be a parsing bug, not real data"
print(f"PASS: real, whole-deck scan -- {total_lt} lookup tables, 0 missing 'values', "
      f"{shape_b_count} real Shape-B (values-only) tables.")

# --- GUI: LibertyPinEditor's new read-only Lookup Tables pane ---
root = tk.Tk()
editor = LibertyPinEditor(root)
editor.pack()
editor.set_cell(a21o)
root.update()

editor.pins_tree.selection_set(editor._pin_iid(pin_x))
editor._on_pin_select()
root.update()

assert editor.current_arc is not None
lt_rows = editor.lt_tree.get_children()
assert len(lt_rows) == len(editor.current_arc.lookup_tables)
assert len(lt_rows) > 0
print(f"PASS: Lookup Tables pane shows {len(lt_rows)} real rows for the selected arc.")

first_lt = editor._lt_by_iid[lt_rows[0]]
row_values = editor.lt_tree.item(lt_rows[0])["values"]
assert row_values[0] == first_lt.kind
assert row_values[1] == first_lt.template_name
print("PASS: Lookup Tables row values match the real, parsed LibertyLookupTable object.")

text_content = editor.lt_values_text.get("1.0", "end")
assert "values (real time_unit: 1ns):" in text_content, "a21o's own real cell declares time_unit : \"1ns\";"
if first_lt.index_1 is not None:
    assert "index_1 (unit per real template, not resolved):" in text_content
assert str(first_lt.values[0][0]) in text_content
print("PASS: the raw values matrix is rendered read-only in the text pane, labeled with the real time_unit.")

assert str(editor.lt_values_text.cget("state")) == "disabled"
print("PASS: the values text widget is genuinely read-only (state=disabled).")

root.destroy()
print("ALL LIBERTY LOOKUP TABLE TESTS PASS")

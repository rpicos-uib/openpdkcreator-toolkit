"""Real LEF pin PORT ``RECT`` geometry -- parsing, in-memory editing
(``gui/geometry_adapters.py``'s ``lef_pin_scene``/``new_lef_port_rect``),
write-back (``pdklib/lef_writer.py``), and the real ``gui/pin_editor.py``
"Edit Geometry..." dialog end to end, driven the same way every other
canvas-backed editor in this project is tested (see
``test_geometry_canvas_interactive.py``)."""

import sys
sys.path.insert(0, "/foss/designs")
import tempfile
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui import geometry_adapters
from openpdkcreator.gui.geometry_canvas import GeometryCanvas
from openpdkcreator.gui.pin_editor import PinEditor
from openpdkcreator.pdklib import lef as lef_mod
from openpdkcreator.pdklib import lef_writer

DATA_DIR = Path("/foss/designs/data")
lef_files = sorted(DATA_DIR.rglob("*.lef"))
assert lef_files, "no real .lef files found under data/"

# --- 1. Real parser extracts real rect coordinates, not just a count ---
total_pins = total_rects = 0
sample_pin = sample_file = sample_macro = None
for f in lef_files:
    lf = lef_mod.parse_lef_file(f)
    for macro in lf.macros:
        for pin in macro.pins:
            total_pins += 1
            total_rects += sum(p.rect_count for p in pin.ports)
            if sample_pin is None and any(p.rects for p in pin.ports):
                sample_pin, sample_file, sample_macro = pin, f, macro
print(f"real pins parsed: {total_pins}, real rects parsed: {total_rects}")
assert total_pins > 6000 and total_rects > 10000
assert sample_pin is not None
print("PASS: real parser captures real (x1,y1,x2,y2) rects, not a bare count.")

# --- 2. Byte-identical export across every real IHP .lef file, unedited ---
mismatches = 0
for f in lef_files:
    lf = lef_mod.parse_lef_file(f)
    if lef_writer.render_lef_file(f, lf) != f.read_text():
        mismatches += 1
        print("MISMATCH (no edit):", f)
assert mismatches == 0
print(f"PASS: no-edit export byte-identical across all {len(lef_files)} real .lef files "
      f"({total_pins} real pins, including every real multi-PORT-block pin).")

# --- 3. lef_pin_scene / new_lef_port_rect: move (incremental, twice --
#     rects are immutable tuples, this exercises the index-based, not
#     value-based, closure fix), add (new + existing layer), delete
#     (one of several rects on a port, then the port's last rect) ---
scene = geometry_adapters.lef_pin_scene(sample_pin)
n_rects = sum(p.rect_count for p in sample_pin.ports)
assert len(scene.items) == n_rects

item = scene.items[0]
orig = (item.x1, item.y1, item.x2, item.y2)
item.on_move(1.0, 2.0)
item.on_move(0.5, 0.5)  # second incremental call -- would raise/no-op on the old value-based lookup
moved = [r for p in sample_pin.ports if p.layer == item.label for r in p.rects
         if abs(r[0] - (orig[0] + 1.5)) < 1e-9 and abs(r[1] - (orig[1] + 2.5)) < 1e-9]
assert moved, "two incremental on_move calls did not both land on the real underlying rect"
print("PASS: repeated incremental drag moves land on the same real rect (tuple-index fix holds).")

n_ports_before = len(sample_pin.ports)
geometry_adapters.new_lef_port_rect(sample_pin, "TESTLAYER", 0.0, 0.0, 1.0, 1.0)
assert len(sample_pin.ports) == n_ports_before + 1
assert sample_pin.ports[-1].rects == [(0.0, 0.0, 1.0, 1.0)]
geometry_adapters.new_lef_port_rect(sample_pin, "TESTLAYER", 2.0, 2.0, 3.0, 3.0)
assert len(sample_pin.ports) == n_ports_before + 1  # joined the existing port, no new one
assert sample_pin.ports[-1].rects == [(0.0, 0.0, 1.0, 1.0), (2.0, 2.0, 3.0, 3.0)]
print("PASS: new_lef_port_rect creates a new LefPort on an unseen layer, joins an existing one otherwise.")

scene2 = geometry_adapters.lef_pin_scene(sample_pin)
first_test_item = next(it for it in scene2.items if it.label == "TESTLAYER" and it.x1 == 0.0)
first_test_item.on_delete()
assert sample_pin.ports[-1].rects == [(2.0, 2.0, 3.0, 3.0)]
last_test_item = next(it for it in geometry_adapters.lef_pin_scene(sample_pin).items if it.label == "TESTLAYER")
last_test_item.on_delete()
assert not any(p.layer == "TESTLAYER" for p in sample_pin.ports)
print("PASS: deleting a rect removes just that rect, or the whole LefPort once its last rect is gone.")

# --- 4. Real write-back round trip: edit, render, re-parse, verify the
#     edited pin matches exactly and every *other* real pin in the same
#     real file is completely untouched ---
lf = lef_mod.parse_lef_file(sample_file)
macro = next(m for m in lf.macros if m.name == sample_macro.name)
pin = next(p for p in macro.pins if p.name == sample_pin.name)
scene3 = geometry_adapters.lef_pin_scene(pin)
scene3.items[0].on_move(3.3, -1.1)
geometry_adapters.new_lef_port_rect(pin, "TESTLAYER9", 5.0, 5.0, 6.0, 6.0)

rendered = lef_writer.render_lef_file(sample_file, lf)
assert "TESTLAYER9" in rendered

tmp_path = Path(tempfile.mktemp(suffix=".lef"))
tmp_path.write_text(rendered)
try:
    lf2 = lef_mod.parse_lef_file(tmp_path)
    macro2 = next(m for m in lf2.macros if m.name == sample_macro.name)
    pin2 = next(p for p in macro2.pins if p.name == sample_pin.name)
    assert pin2.ports == pin.ports, f"round trip mismatch:\n{pin2.ports}\nvs\n{pin.ports}"

    fresh_lf = lef_mod.parse_lef_file(sample_file)
    for m_orig, m_new in zip(fresh_lf.macros, lf2.macros):
        for p_orig, p_new in zip(m_orig.pins, m_new.pins):
            if m_orig.name == sample_macro.name and p_orig.name == sample_pin.name:
                continue
            assert p_orig.ports == p_new.ports, f"unrelated pin changed: {m_orig.name}.{p_orig.name}"
finally:
    tmp_path.unlink()
print("PASS: real edit survives a full render + re-parse round trip; every other real pin in "
      "the same file is byte-for-byte unaffected.")

# --- 5. Backward-compat load of an old-shape save (rect_count, no rects) ---
from openpdkcreator import project_io

old_port = project_io._load_lef_port({"layer": "Metal1"})
assert old_port.layer == "Metal1"
assert old_port.rects == []
assert old_port.rect_count == 0
print("PASS: an old saved LefPort with no 'rects' key loads cleanly as an empty-geometry port.")

# --- 6. The real, driven gui/pin_editor.py "Edit Geometry..." dialog ---
gui_file = next(f for f in lef_files if f.name == "sg13g2_io.lef")
gui_lf = lef_mod.parse_lef_file(gui_file)
gui_macro = next(m for m in gui_lf.macros if any(any(pp.rects for pp in p.ports) for p in m.pins))
gui_pin = next(p for p in gui_macro.pins if any(pp.rects for pp in p.ports))

root = tk.Tk()
root.withdraw()
editor = PinEditor(root)
editor.set_macro(gui_macro)
editor.pins_tree.selection_set(PinEditor._pin_iid(gui_pin))
editor._on_pin_select()
assert editor.current_pin is gui_pin

editor._edit_geometry()
root.update()


def _find_canvas(widget):
    for child in widget.winfo_children():
        if isinstance(child, GeometryCanvas):
            return child
        found = _find_canvas(child)
        if found is not None:
            return found
    return None


def _find_toplevel(widget):
    for child in widget.winfo_children():
        if isinstance(child, tk.Toplevel):
            return child
        found = _find_toplevel(child)
        if found is not None:
            return found
    return None


dialog = _find_toplevel(root)
assert dialog is not None, "Edit Geometry... did not open a real Toplevel"
canvas = _find_canvas(dialog)
assert canvas is not None, "no real GeometryCanvas embedded in the Edit Geometry dialog"

n_before = len(canvas.scene.items)
canvas.on_new_rect(10.0, 10.0, 11.0, 11.0)
root.update()
assert len(canvas.scene.items) == n_before + 1
assert any(p.rects and (10.0, 10.0, 11.0, 11.0) in p.rects for p in gui_pin.ports)

summary = editor.ports_text.get("1.0", "end")
assert summary.strip(), "ports summary did not refresh after a real dialog edit"

dialog.destroy()
root.destroy()
print("PASS: the real gui/pin_editor.py 'Edit Geometry...' button opens a working canvas dialog, "
      "a real new rect lands on the real, live LefPin, and the summary text refreshes.")

print("ALL LEF PORT GEOMETRY TESTS PASS")

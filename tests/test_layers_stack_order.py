import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator.ihp import layers as layers_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
LYP_PATH = layers_mod.find_lyp(PDK_ROOT)

# --- import_layers assigns a real, distinct stack_order per layer,
# matching the real .lyp file's own block order -- regression test for
# a real bug: every real, imported layer used to default to the
# dataclass's own stack_order=0 (a .lyp genuinely can't encode a
# layer's real physical stack position), which meant every layer
# showed "0" in the GUI and, worse, Move Up/Down silently did nothing
# (it swaps two stack_order values -- swapping 0 with 0 is a no-op) ---
layers = layers_mod.import_layers(PDK_ROOT, LYP_PATH)
assert len(layers) == 377, len(layers)
stack_orders = [l.stack_order for l in layers]
assert len(set(stack_orders)) == len(layers), "stack_order must be distinct per real, imported layer"
assert stack_orders == list(range(len(layers))), "stack_order must match the real .lyp file's own block order"
assert [l.name for l in layers[:3]] == ["Substrate.drawing", "Substrate.text", "Activ.drawing"]
print(f"PASS: import_layers assigns {len(layers)} real, distinct stack_order values matching real .lyp file order.")

# --- End-to-end through the actual GUI: Move Down on a freshly-loaded,
# real layer genuinely changes the displayed order now (previously a
# no-op against real, freshly-imported data) ---
root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

lv = app.layers_view
before = [l.name for l in app.project.sorted_layers()[:3]]
assert before == ["Substrate.drawing", "Substrate.text", "Activ.drawing"]

first_layer = app.project.sorted_layers()[0]
lv.tree.selection_set(lv._iid(first_layer))
lv._move(1)  # Move Down
root.update()

after = [l.name for l in app.project.sorted_layers()[:3]]
print("order before Move Down:", before)
print("order after Move Down: ", after)
assert after != before, "Move Down must actually reorder real, freshly-imported layers"
assert after[0] == "Substrate.text" and after[1] == "Substrate.drawing", after
print("PASS: Move Down genuinely reorders real, freshly-imported layers (previously a silent no-op).")

# --- New Layer still continues numbering past the real, imported max,
# not just from 0 -- confirms _new_layer's next_order computation
# still works correctly now that real layers start non-zero ---
lv._new_layer()
root.update()
new_layer = app.project.sorted_layers()[-1]
assert new_layer.stack_order == max(l.stack_order for l in app.project.layers)
assert new_layer.stack_order >= 376, new_layer.stack_order
print(f"PASS: New Layer continues stack_order numbering past the real, imported max ({new_layer.stack_order}).")

root.destroy()
print("ALL LAYERS STACK ORDER TESTS PASS")

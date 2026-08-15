import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator.gui.pdk_wizard_view import _STAGES, _BOX_H, _BOX_W

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

wv = app.wizard_view
canvas = wv.canvas

overflow = []
for stage in _STAGES:
    box_id = wv._box_ids[stage.stage_id]
    label_id = wv._label_ids[stage.stage_id]
    bx0, by0, bx1, by1 = canvas.bbox(box_id)
    tx0, ty0, tx1, ty1 = canvas.bbox(label_id)
    over_h = (ty1 - ty0) > _BOX_H
    over_w = (tx1 - tx0) > _BOX_W
    print(f"{stage.stage_id:20s} title={stage.title!r:35s} text_h={ty1-ty0:3d} box_h={_BOX_H} text_w={tx1-tx0:3d} box_w={_BOX_W} overflow_h={over_h} overflow_w={over_w}")
    if over_h:
        overflow.append(stage.stage_id)

# Bounding boxes of any two node boxes must not overlap (grid should already guarantee this, verify anyway)
boxes = []
for stage in _STAGES:
    boxes.append((stage.stage_id, canvas.bbox(wv._box_ids[stage.stage_id])))
overlaps = []
for i in range(len(boxes)):
    for j in range(i + 1, len(boxes)):
        id_a, (ax0, ay0, ax1, ay1) = boxes[i]
        id_b, (bx0, by0, bx1, by1) = boxes[j]
        if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
            overlaps.append((id_a, id_b))

print()
print("Vertically-overflowing titles:", overflow)
print("Overlapping box pairs:", overlaps)
assert not overlaps, overlaps

root.destroy()
print("LAYOUT CHECK DONE")

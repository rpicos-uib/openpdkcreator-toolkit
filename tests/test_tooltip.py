import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk

from openpdkcreator.gui.tooltip import add_help_icon

root = tk.Tk()
frame = tk.Frame(root)
frame.pack()
icon = add_help_icon(frame, "This explains what the thing is.")
icon.pack()
root.update()

assert icon._tooltip.tip_window is None
icon.event_generate("<Enter>")
root.update()
assert icon._tooltip.tip_window is not None
assert icon._tooltip.tip_window.winfo_exists()
print("PASS: hovering the help icon shows a real tooltip window.")

icon.event_generate("<Leave>")
root.update()
assert icon._tooltip.tip_window is None
print("PASS: leaving the help icon hides the tooltip window again.")

# An icon with no text never shows an empty popup.
from openpdkcreator.gui.tooltip import Tooltip
blank = tk.Label(frame, text="?")
blank.pack()
tt = Tooltip(blank, "")
blank.event_generate("<Enter>")
root.update()
assert tt.tip_window is None
print("PASS: an empty tooltip text never opens a popup.")

# --- CanvasItemTooltip: same hover behavior, but for canvas items
# (the PDK Wizard's own drawn stage boxes have no widget of their own
# to attach a plain Tooltip to) ---
from openpdkcreator.gui.tooltip import CanvasItemTooltip

canvas = tk.Canvas(frame)
canvas.pack()
rect_id = canvas.create_rectangle(0, 0, 50, 50)
canvas_tt = CanvasItemTooltip(canvas, (rect_id,), "A real canvas item's own help text.")
assert canvas_tt.tip_window is None
canvas_tt._show(event=None)
root.update()
assert canvas_tt.tip_window is not None
assert canvas_tt.tip_window.winfo_exists()
canvas_tt._hide()
root.update()
assert canvas_tt.tip_window is None
print("PASS: CanvasItemTooltip shows and hides a real popup for a canvas item, mirroring Tooltip's own behavior.")

root.destroy()
print("ALL TOOLTIP TESTS PASS")

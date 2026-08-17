import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")


def rect_count(canvas: tk.Canvas) -> int:
    return len([i for i in canvas.find_all() if canvas.type(i) == "rectangle"])


def text_count(canvas: tk.Canvas) -> int:
    return len([i for i in canvas.find_all() if canvas.type(i) == "text"])


root = tk.Tk()
root.geometry("1000x800")
app = App(root, PDK_ROOT)
root.update()
# A ttk.Notebook only gives real, laid-out geometry to whichever tab
# is actually selected -- the Layers tab sits nested under PDK >
# Technology, not the default-selected Wizard tab, so it must actually
# be navigated to before its own widgets report real, non-1x1 sizes.
app.goto("Technology", "Layers")
root.update()

lv = app.layers_view
layers = app.project.sorted_layers()
assert len(layers) == 377, len(layers)

# --- Default (no zoom set) draws every real layer, matching the old,
# unzoomed behavior exactly ---
assert rect_count(lv.stack_canvas) == 377, rect_count(lv.stack_canvas)
print("PASS: with no zoom set, every real layer is drawn (377 bands).")

# --- Typing a narrow real Min/Max zooms the drawing to just that
# real, distinct stack_order sub-range ---
lv.zoom_min_var.set("0")
lv.zoom_max_var.set("5")
root.update()
assert rect_count(lv.stack_canvas) == 6, rect_count(lv.stack_canvas)  # stack_order 0..5 inclusive
print("PASS: setting Min=0/Max=5 zooms the drawing to exactly the 6 real layers in that range.")

# Zoomed-in bands, on a real 1000x800 window, are tall enough that
# real layer-name labels are shown again (unlike the unreadable,
# sub-pixel bands the full 377-layer view produces).
assert text_count(lv.stack_canvas) == 6, text_count(lv.stack_canvas)
print("PASS: zoomed-in bands are tall enough to show real layer-name labels.")

# --- An inverted range (Min > Max) is corrected, not left broken ---
lv.zoom_min_var.set("5")
lv.zoom_max_var.set("2")
root.update()
assert rect_count(lv.stack_canvas) == 4, rect_count(lv.stack_canvas)  # stack_order 2..5 inclusive
print("PASS: an inverted Min/Max range is silently corrected (swapped), not left broken.")

# --- Out-of-range values are clamped to the real, full stack_order
# range rather than crashing or showing nothing ---
lv.zoom_min_var.set("-500")
lv.zoom_max_var.set("999999")
root.update()
assert rect_count(lv.stack_canvas) == 377, rect_count(lv.stack_canvas)
print("PASS: an out-of-range Min/Max is clamped to the real full stack, not crashing or showing nothing.")

# --- Reset clears both bounds back to the real full range ---
lv.zoom_min_var.set("10")
lv.zoom_max_var.set("20")
root.update()
assert rect_count(lv.stack_canvas) == 11
lv._reset_zoom()
root.update()
assert lv.zoom_min_var.get() == "" and lv.zoom_max_var.get() == ""
assert rect_count(lv.stack_canvas) == 377, rect_count(lv.stack_canvas)
print("PASS: Reset restores the real, full 377-layer view.")

# --- The cross-section canvas's own real *viewport* genuinely grows
# with the real window (winfo_height()), but each real band's own
# height stays fixed (FIXED_BAND_H) regardless -- readability no
# longer depends on window size or how many layers are zoomed in ---
lv.zoom_min_var.set("0")
lv.zoom_max_var.set("9")
root.update()
short_ids = [i for i in lv.stack_canvas.find_all() if lv.stack_canvas.type(i) == "rectangle"]
short_bbox = lv.stack_canvas.bbox(short_ids[0])
short_band_h = short_bbox[3] - short_bbox[1]
short_canvas_h = lv.stack_canvas.winfo_height()

root.geometry("1000x1600")
root.update()
tall_canvas_h = lv.stack_canvas.winfo_height()
assert tall_canvas_h > short_canvas_h, (short_canvas_h, tall_canvas_h)
tall_ids = [i for i in lv.stack_canvas.find_all() if lv.stack_canvas.type(i) == "rectangle"]
tall_bbox = lv.stack_canvas.bbox(tall_ids[0])
tall_band_h = tall_bbox[3] - tall_bbox[1]
print(f"canvas viewport height {short_canvas_h} -> {tall_canvas_h}; band height {short_band_h} -> {tall_band_h}")
assert tall_canvas_h > short_canvas_h
from openpdkcreator.gui.layers_view import FIXED_BAND_H
# bbox() includes the rectangle's own outline stroke width, so it runs
# a couple pixels over the real FIXED_BAND_H constant -- the real claim
# here is that it stays IDENTICAL across window sizes, not the exact
# raw pixel count.
assert short_band_h == tall_band_h, (short_band_h, tall_band_h)
assert abs(short_band_h - FIXED_BAND_H) <= 4, (short_band_h, FIXED_BAND_H)
print("PASS: a real window resize grows the real viewport, but each real band's own height stays fixed.")

# --- Real sliding bars: both the layer list and the cross-section
# drawing carry a real, wired ttk.Scrollbar, not just built-in
# mouse-wheel support with no visible/draggable thumb ---
from tkinter import ttk as ttk_mod
assert isinstance(lv.tree_scrollbar, ttk_mod.Scrollbar)
assert lv.tree.cget("yscrollcommand") != ""
assert isinstance(lv.stack_scrollbar, ttk_mod.Scrollbar)
assert lv.stack_canvas.cget("yscrollcommand") != ""
print("PASS: both the layer list and the stack drawing carry a real, wired vertical Scrollbar.")

# --- The full, unzoomed 377-layer view is genuinely taller than the
# real viewport -- confirms the scrollbar has real content to scroll
# through, not a no-op ---
lv._reset_zoom()
root.update()
scrollregion = [float(v) for v in lv.stack_canvas.cget("scrollregion").split()]
content_h = scrollregion[3] - scrollregion[1]
viewport_h = lv.stack_canvas.winfo_height()
assert content_h > viewport_h, (content_h, viewport_h)
print(f"PASS: real scrollable content ({content_h:.0f}px) exceeds the real viewport ({viewport_h}px).")

# --- The very first draw starts scrolled to the real, physical bottom
# of the stack (stack_order 0, e.g. Substrate) -- matching this pane's
# own "(bottom -> top)" label -- not wherever Tk's default happens to
# land. Scrolling up, and an unrelated redraw (a form-field edit),
# must NOT silently reset that position back to the bottom. ---
first, last = lv.stack_canvas.yview()
assert last >= 0.99, (first, last)
print(f"PASS: the drawing starts scrolled to the real bottom of the stack (yview={first:.2f}..{last:.2f}).")

lv.stack_canvas.yview_moveto(0.0)
root.update()
scrolled_first, _ = lv.stack_canvas.yview()
assert scrolled_first < 0.01, scrolled_first
lv.vars["notes"].set("a real, unrelated edit")
root.update()
preserved_first, _ = lv.stack_canvas.yview()
assert abs(preserved_first - scrolled_first) < 0.01, (scrolled_first, preserved_first)
print("PASS: an unrelated form-field edit redraws the stack without resetting the user's own scroll position.")

# --- Changing the real Zoom bounds deliberately re-anchors the view
# back to the bottom of the new, real filtered range ---
lv.zoom_max_var.set("3")
root.update()
reanchored_first, reanchored_last = lv.stack_canvas.yview()
assert reanchored_last >= 0.99, (reanchored_first, reanchored_last)
print("PASS: changing the real Zoom bounds re-anchors the view to the bottom of the new range.")

root.destroy()
print("ALL LAYERS ZOOM TESTS PASS")

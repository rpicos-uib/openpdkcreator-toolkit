"""A small, reusable hover-tooltip -- a "?" label any tab can drop
next to a row/field to explain, in a sentence or two, what a kind of
file *is* or what a step is meant to accomplish, without needing a
click (unlike the PDK Wizard's own click-to-see detail panel). Plain
Tk has no built-in tooltip widget, so this is a minimal one: a
borderless ``Toplevel`` that appears near the "?" on ``<Enter>`` and
disappears on ``<Leave>``."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def _show_popup(owner: tk.Widget, x: int, y: int, text: str) -> tk.Toplevel:
    tw = tk.Toplevel(owner)
    tw.wm_overrideredirect(True)
    try:
        tw.wm_attributes("-topmost", True)
    except tk.TclError:
        pass
    tw.wm_geometry(f"+{x}+{y}")
    tk.Label(
        tw, text=text, justify="left", background="#ffffe0",
        relief="solid", borderwidth=1, wraplength=360, padx=6, pady=4,
    ).pack()
    return tw


class Tooltip:
    """Attaches a hover popup showing *text* to *widget*. Kept as a
    real attribute on the caller's own icon widget (see
    ``add_help_icon`` below) so it isn't garbage-collected -- a Tk
    ``bind`` alone doesn't keep a Python-side object alive."""

    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)
        widget.bind("<Destroy>", self._hide)

    def _show(self, _event=None):
        if self.tip_window is not None or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip_window = _show_popup(self.widget, x, y, self.text)

    def _hide(self, _event=None):
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


class CanvasItemTooltip:
    """Like ``Tooltip``, but for one or more items on a ``tk.Canvas``
    (e.g. the PDK Wizard's own drawn stage boxes) rather than a real
    child widget -- a canvas item has no ``winfo_rootx`` of its own, so
    position comes from the triggering ``<Enter>`` event instead. Kept
    alive the same way as ``Tooltip`` -- store the instance on a real
    attribute of the caller, not just a local variable."""

    def __init__(self, canvas: tk.Canvas, item_ids, text: str):
        self.canvas = canvas
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        for item_id in item_ids:
            canvas.tag_bind(item_id, "<Enter>", self._show)
            canvas.tag_bind(item_id, "<Leave>", self._hide)

    def _show(self, event=None):
        if self.tip_window is not None or not self.text:
            return
        x = (event.x_root if event is not None else self.canvas.winfo_rootx()) + 12
        y = (event.y_root if event is not None else self.canvas.winfo_rooty()) + 12
        self.tip_window = _show_popup(self.canvas, x, y, self.text)

    def _hide(self, _event=None):
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


def add_help_icon(parent: tk.Widget, text: str) -> ttk.Label:
    """A small "?" label wired to show *text* on hover -- pack/grid the
    returned widget wherever it belongs in the caller's own layout."""

    icon = ttk.Label(parent, text=" ? ", foreground="#1565c0", font=("TkDefaultFont", 8, "bold"))
    icon._tooltip = Tooltip(icon, text)  # keeps the Tooltip alive with the icon
    return icon

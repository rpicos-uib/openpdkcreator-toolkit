"""Shared helpers for a file-picker combobox whose typed/selected
value can point at a real, existing file (**Edit File** -- opens
``file_view_dialog.view_file_dialog``) or a not-yet-existing one
(**Create File** -- writes a real, minimal, valid starting file via a
domain's own ``create_new_*`` function, then reloads) -- used by every
domain that now has such a function (xschem ``.sym``/``.sch``, Qucs-S
``.sym``/``.xml``). The combobox itself becomes editable (not
``state="readonly"``) so a user can type a real, new relative path,
not just pick among files that already exist. A typed path that
resolves outside *root* (e.g. via ``..``) is refused before any real
file is ever written -- this project's own real files stay inside the
downloaded PDK tree, never wherever an arbitrary typed path might
otherwise point.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable

from .file_view_dialog import view_file_dialog


def current_file_path(root: Path, file_var: tk.StringVar) -> Path:
    return root / file_var.get().strip()


def update_action_button(button: ttk.Button, root: Path, file_var: tk.StringVar) -> None:
    exists = current_file_path(root, file_var).is_file()
    button.configure(text="Edit File" if exists else "Create File")


def handle_action(
    parent_widget: tk.Widget, root: Path, file_var: tk.StringVar,
    create_fn: Callable[[Path], None], on_created: Callable[[], None],
) -> None:
    """*create_fn*: one of the real ``pdklib/*.py`` ``create_new_*``
    functions, called with the real, full target path -- writes real,
    valid starting content or raises. *on_created*: called after a
    real file is successfully created, so the caller can reload its
    own file list/parse and select the new file (already reflected in
    *file_var*, unchanged by this call)."""

    path = current_file_path(root, file_var)
    if path.is_file():
        view_file_dialog(parent_widget, path)
        return
    if not file_var.get().strip():
        messagebox.showerror("Cannot create file", "Type a real, relative file path first.", parent=parent_widget)
        return
    resolved_root = root.resolve()
    try:
        resolved_path = path.resolve()
        resolved_path.relative_to(resolved_root)
    except ValueError:
        messagebox.showerror(
            "Cannot create file",
            f"'{file_var.get().strip()}' resolves outside {resolved_root} -- "
            f"type a real, relative path (no '..') inside it.",
            parent=parent_widget,
        )
        return
    try:
        create_fn(path)
    except (FileExistsError, OSError) as exc:
        messagebox.showerror("Cannot create file", str(exc), parent=parent_widget)
        return
    on_created()

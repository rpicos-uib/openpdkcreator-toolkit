"""A real, one-file View -> Edit -> Save dialog over the actual source
file behind whatever's currently shown in a tab (the selected LEF/tech
file, or the .lyp).

Deliberately two-stage, unlike OpenPDKCreator's own
``gui/file_view_dialog.py`` (always editable from the moment it
opens): most real files opened here are real, downloaded third-party
PDK data (see README.md's "IHP data in git" note), so opening one
always starts read-only -- an explicit **Edit** button, inside the
dialog, is what switches it to editable and reveals **Save**.

*edit_note* (below) used to be a single fixed string claiming every
real file opened here is "gitignored, never committed" -- true for
this project's own real IHP-based dev checkout (``data/`` really is
gitignored there), but real, found-live to be actively wrong for a
from-scratch project (``data/`` is that project's own tracked,
committed content instead -- confirmed via ``git check-ignore``
against both real cases). Rather than pushing every real caller to
work this out for itself, the default now asks git directly
(``_is_gitignored``, live, per real *path*, not assumed) and only
falls back to a caller-supplied *edit_note* when one real caller
already knows something more specific to say (e.g.
``user_models_view.py``'s own real Verilog/Verilog-A wording).
"""

from __future__ import annotations

import subprocess
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk

from .. import export as export_mod


def _is_gitignored(path: Path) -> bool:
    """Real, live answer via ``git check-ignore --quiet``, anchored at
    this project's own real git repo root (``export_mod.PROJECT_ROOT``
    -- ``-C``, not plain ``cwd=path.parent``): a real, found-live
    subtlety, not assumed -- the downloaded IHP PDK under ``data/``
    ships its own real, nested ``.git`` (IHP's own real clone, with
    IHP's own unrelated Python-project ``.gitignore``), so a bare
    ``cwd=path.parent`` lets git auto-discover *that* real, inner repo
    boundary instead of this project's own real, outer one -- caught
    live: a real ``.tech`` file under ``data/ihp-sg13g2/...`` came back
    "not ignored" that way, contradicting this project's own real,
    top-level ``data/`` rule (confirmed correct once anchored via
    ``-C``, verbose output naming exactly that real rule/line).
    Exit 0 means *path* really is ignored from this project's own real
    point of view, exit 1 means it's real, tracked (or trackable)
    project content. Falls back to ``True`` (this module's own
    original, real-downloaded-PDK-data assumption) only when git
    itself can't real-answer at all (no repo, git missing, timed out)
    -- an honest fallback for a genuinely unknown real case, never a
    silent guess presented as a live check."""

    try:
        proc = subprocess.run(
            ["git", "-C", str(export_mod.PROJECT_ROOT), "check-ignore", "--quiet", str(path)],
            capture_output=True, timeout=5,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return True


def view_file_dialog(
    parent: tk.Widget, path: Path,
    focus_start_line: int | None = None, focus_end_line: int | None = None,
    edit_note: str | None = None,
    on_save: Callable[[], None] | None = None,
) -> None:
    """*focus_start_line*/*focus_end_line* (1-indexed, both optional):
    when given, scrolls to and highlights that real line range on open
    -- used by ``cell_hub_view.py`` to jump straight to one real cell's
    own block inside a much larger, combined per-family file (e.g. a
    real ``.SUBCKT``/``.ends`` pair 25 lines into an 8000-line
    ``sg13g2_stdcell.cdl``), rather than making the user hunt for it.

    *edit_note*: what the status label/save confirmation call *path*
    while editing. Left ``None`` (the real default nearly every real
    call site relies on), it's decided live via ``_is_gitignored`` --
    never a fixed guess. A caller whose own real file's status it
    already knows for certain (e.g. ``user_models_view.py``'s own
    real Verilog/Verilog-A source, always real, tracked project
    content) can still pass its own, more specific real wording
    instead, skipping the live check.

    *on_save*: called (no arguments) right after a real, confirmed
    save -- lets a caller run its own real, immediate follow-up (e.g.
    ``user_models_view.py``'s own real compile-check) without this
    module needing to know anything about what that follow-up is."""

    if edit_note is None:
        edit_note = (
            "a real, local, downloaded PDK file -- only your local data/ copy (gitignored, never committed)"
            if _is_gitignored(path) else
            "a real, project-owned file -- part of this project's own tracked, committed content"
        )

    dialog = tk.Toplevel(parent)
    dialog.title(f"View: {path.name}")
    dialog.geometry("900x700")
    dialog.transient(parent.winfo_toplevel())

    dialog.columnconfigure(0, weight=1)
    dialog.rowconfigure(1, weight=1)

    status_var = tk.StringVar(value=str(path))
    ttk.Label(dialog, textvariable=status_var, font=("TkDefaultFont", 9, "bold")).grid(
        row=0, column=0, sticky="w", padx=8, pady=(8, 4)
    )

    text = tk.Text(dialog, wrap="none", font=("Courier", 10))
    text.grid(row=1, column=0, sticky="nsew", padx=8)
    scroll_y = ttk.Scrollbar(dialog, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=scroll_y.set)
    scroll_y.grid(row=1, column=1, sticky="ns")
    scroll_x = ttk.Scrollbar(dialog, orient="horizontal", command=text.xview)
    text.configure(xscrollcommand=scroll_x.set)
    scroll_x.grid(row=2, column=0, sticky="ew", padx=8)

    text.insert("1.0", path.read_text(encoding="utf-8", errors="replace"))
    text.configure(state="disabled")
    text.edit_modified(False)

    if focus_start_line is not None:
        end = focus_end_line if focus_end_line is not None else focus_start_line
        text.tag_configure("focus_range", background="#fff2a8")
        text.tag_add("focus_range", f"{focus_start_line}.0", f"{end + 1}.0")
        text.see(f"{end}.0")
        text.see(f"{focus_start_line}.0")

    button_row = ttk.Frame(dialog)
    button_row.grid(row=3, column=0, sticky="e", padx=8, pady=8)

    edit_button = ttk.Button(button_row, text="Edit")
    save_button = ttk.Button(button_row, text="Save", state="disabled")

    def _enable_edit():
        text.configure(state="normal")
        edit_button.configure(state="disabled")
        save_button.configure(state="normal")
        status_var.set(f"{path}  (editing -- {edit_note})")

    def _save():
        if not messagebox.askyesno(
            "Save changes?",
            f"Overwrite {edit_note}\n{path}\nwith these changes?",
            parent=dialog,
        ):
            return
        path.write_text(text.get("1.0", "end-1c"), encoding="utf-8")
        text.edit_modified(False)
        status_var.set(f"{path}  (saved)")
        if on_save is not None:
            on_save()

    def _close():
        if text.edit_modified() and not messagebox.askyesno(
            "Discard changes?", "You have unsaved edits. Close without saving?", parent=dialog
        ):
            return
        dialog.destroy()

    edit_button.configure(command=_enable_edit)
    save_button.configure(command=_save)
    edit_button.pack(side="left")
    save_button.pack(side="left", padx=(6, 0))
    ttk.Button(button_row, text="Close", command=_close).pack(side="left", padx=(6, 0))
    dialog.protocol("WM_DELETE_WINDOW", _close)

    dialog.grab_set()
    dialog.wait_window()

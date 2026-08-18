"""A reusable list + form pane for a simple, uniform "list of small,
flat-string-field dataclass entries" domain -- New/Delete Entry, the
same commit-on-switch pattern this project's own hand-written editors
(``pin_editor.PinEditor``, ``magic_tech_view.py``'s own Types editor)
already use, generalized here so a *new* simple domain (one real line
per entry, plain string fields, no nested structure or nested list
field the way Types' own ``aliases: list[str]`` needs special
handling) doesn't need its own hand-copied set of the same eight
methods. Introduced for Magic Tech's own Planes/Contacts/Aliases
editors (``pdklib/magic_tech.py``'s ``PlaneEntry``/``ContactEntry``/
``AliasEntry`` -- all plain-string-field dataclasses, a clean fit);
Types keeps its own existing, bespoke code unchanged (it has a real
comma-split aliases *list* field and a boolean obsolete combo, neither
of which this generic editor attempts to generalize to).

**``allow_new_delete=False``** (new): for a domain editable *only* in
place, no New/Delete -- introduced for cifoutput's own
``CifOutputLayerMapping`` (``gui/magic_tech_view.py``), the first real
Magic Tech domain where a brand-new entry has no coherent real
write-back target (a real ``calma`` line means nothing without the
real geometry recipe leading up to it, which this project doesn't
model or author). Hides the New/Delete buttons entirely rather than
leaving them present but broken; *new_entry_factory* is unused and may
be ``None`` in this mode.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from .list_filter import build_filter_row, matches


class SimpleListEditor(ttk.Frame):
    def __init__(
        self,
        parent,
        columns: list[tuple[str, str, int]],
        new_entry_factory: Callable[[], object] | None,
        entry_label: str = "Entry",
        help_text: str = "",
        allow_new_delete: bool = True,
    ):
        """*columns*: (field, label, tree_column_width) -- also the
        real form field order, one plain ``ttk.Entry`` per field, in
        this same order."""
        super().__init__(parent)
        self.columns = columns
        self.new_entry_factory = new_entry_factory
        self.entry_label = entry_label

        self.entries: list | None = None
        self.current_entry = None
        self._entry_by_iid: dict[str, object] = {}
        self._suspend_trace = False
        self._filter_query = ""

        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        button_row = ttk.Frame(self)
        button_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        if allow_new_delete:
            ttk.Button(button_row, text=f"New {entry_label}", command=self.new_entry).pack(side="left")
            ttk.Button(button_row, text=f"Delete {entry_label}", command=self.delete_entry).pack(
                side="left", padx=(6, 0)
            )
        self.filter_var = build_filter_row(button_row, self._on_filter_changed)

        tree_columns = tuple(field for field, _label, _width in columns)
        self.tree = ttk.Treeview(self, columns=tree_columns, show="headings", selectmode="browse")
        for (field, label, width) in columns:
            self.tree.heading(field, text=label)
            self.tree.column(field, width=width, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        right = ttk.Frame(self)
        right.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(8, 0))
        right.columnconfigure(1, weight=1)

        self.field_vars: dict[str, tk.StringVar] = {}
        for row, (field, label, _width) in enumerate(columns):
            ttk.Label(right, text=label).grid(row=row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_field_changed)
            ttk.Entry(right, textvariable=var).grid(row=row, column=1, sticky="ew", pady=2)
            self.field_vars[field] = var

        if help_text:
            ttk.Label(right, text=help_text, foreground="#666", wraplength=260, justify="left").grid(
                row=len(columns), column=0, columnspan=2, sticky="w", pady=(10, 0)
            )

    # -- public API ---------------------------------------------------------

    def set_entries(self, entries: list):
        self.entries = entries
        self._refresh()

    def commit_pending_edits(self):
        self._commit_form()

    # -- internals ------------------------------------------------------------

    @staticmethod
    def _iid(entry) -> str:
        return str(id(entry))

    def _row_values(self, entry) -> tuple:
        return tuple(getattr(entry, field) for field, _label, _width in self.columns)

    def _matches_filter(self, entry) -> bool:
        return matches(self._filter_query, *self._row_values(entry))

    def _on_filter_changed(self, query: str):
        self._filter_query = query
        self._refresh()

    def _refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._entry_by_iid = {}
        if self.entries is None:
            self._load_into_form(None)
            return
        shown = [e for e in self.entries if self._matches_filter(e)]
        for entry in shown:
            iid = self._iid(entry)
            self._entry_by_iid[iid] = entry
            self.tree.insert("", "end", iid=iid, values=self._row_values(entry))
        if shown:
            self.tree.selection_set(self._iid(shown[0]))
            self._load_into_form(shown[0])
        else:
            self._load_into_form(None)

    def _on_select(self, _event=None):
        self._commit_form()
        selection = self.tree.selection()
        entry = self._entry_by_iid.get(selection[0]) if selection else None
        self._load_into_form(entry)

    def _load_into_form(self, entry):
        self._suspend_trace = True
        self.current_entry = entry
        for field, var in self.field_vars.items():
            var.set(getattr(entry, field) if entry is not None else "")
        self._suspend_trace = False

    def _commit_form(self):
        entry = self.current_entry
        if entry is None:
            return
        for field, var in self.field_vars.items():
            value = var.get().strip()
            if value:
                setattr(entry, field, value)

    def _on_field_changed(self, *_args):
        if self._suspend_trace:
            return
        self._commit_form()
        if self.current_entry is not None:
            iid = self._iid(self.current_entry)
            if self.tree.exists(iid):
                self.tree.item(iid, values=self._row_values(self.current_entry))

    def new_entry(self):
        if self.entries is None:
            return
        self._commit_form()
        self.filter_var.set("")
        entry = self.new_entry_factory()
        self.entries.append(entry)
        iid = self._iid(entry)
        self._entry_by_iid[iid] = entry
        self.tree.insert("", "end", iid=iid, values=self._row_values(entry))
        self.tree.selection_set(iid)
        self.tree.see(iid)

    def delete_entry(self):
        if self.entries is None:
            return
        selection = self.tree.selection()
        if not selection:
            return
        entry = self._entry_by_iid.get(selection[0])
        if entry is None:
            return
        self.entries.remove(entry)
        self.current_entry = None
        self.tree.delete(selection[0])
        del self._entry_by_iid[selection[0]]
        remaining = self.tree.get_children()
        if remaining:
            self.tree.selection_set(remaining[0])
            self._load_into_form(self._entry_by_iid[remaining[0]])
        else:
            self._load_into_form(None)

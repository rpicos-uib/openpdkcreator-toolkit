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

**``combo_fields`` (new)**: a field whose own real values are genuinely
limited to a known, closed set (Magic Tech's own ``check_type``/
``directive`` keywords -- confirmed exhaustive against
``pdklib/magic_tech.py``'s own parser -- or a real, dynamic Magic type
name) gets a ``ttk.Combobox`` here instead of a plain ``ttk.Entry``,
the same "don't make the user retype something this project already
knows the real choices for" a hand-typed field otherwise risks a
silent typo on. ``{field: (values, readonly)}`` -- *values* a static
tuple for a real fixed keyword enum, or left empty and refreshed later
via ``combo_widgets[field]["values"] = ...`` for a real, dynamic list
(e.g. this technology's own current real Type names, which can change
between refreshes); *readonly* ``True`` only for a real, truly closed
enum with no other legal value ever -- a dynamic list stays editable
(``state="normal"``) since the real choice it suggests can itself be
mid-edit or not created yet."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
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
        combo_fields: dict[str, tuple[tuple[str, ...], bool]] | None = None,
        field_buttons: dict[str, tuple[str, Callable[[], None]]] | None = None,
        help_popup: bool = False,
    ):
        """*columns*: (field, label, tree_column_width) -- also the
        real form field order, one plain ``ttk.Entry`` per field
        (or a ``ttk.Combobox``, for a field named in *combo_fields*
        -- see this class's own docstring), in this same order.

        *field_buttons* (new): ``{field: (button_text, command)}`` --
        a real button placed directly below that one field's own row
        (pushing every field after it down by one row), for a field
        whose real editing needs more than a single-line widget can
        offer (introduced for the DRC-checks Layers field's own real
        multi-select popup, ``magic_tech_view.py``'s own
        ``_select_drc_check_layers``) -- the field itself stays a
        plain ``ttk.Entry``/``ttk.Combobox``, still hand-editable, the
        button is an additional real way in, not a replacement.

        *help_popup* (new): when true, *help_text* renders as a real
        **Help** button (a modal ``messagebox.showinfo``) instead of
        an always-visible wrapped label -- for a domain whose real
        help text is long enough to crowd the form (DRC (Magic)'s own
        three editors); every other real caller keeps the original,
        always-visible label unless it opts in."""
        super().__init__(parent)
        self.columns = columns
        self.new_entry_factory = new_entry_factory
        self.entry_label = entry_label
        self.combo_fields = combo_fields or {}
        self.combo_widgets: dict[str, ttk.Combobox] = {}
        self.field_buttons = field_buttons or {}
        self.help_text = help_text
        self.help_popup = help_popup

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
        form_row = 0
        for field, label, _width in columns:
            ttk.Label(right, text=label).grid(row=form_row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_field_changed)
            if field in self.combo_fields:
                values, readonly = self.combo_fields[field]
                widget = ttk.Combobox(
                    right, textvariable=var, values=values, state="readonly" if readonly else "normal",
                )
                self.combo_widgets[field] = widget
            else:
                widget = ttk.Entry(right, textvariable=var)
            widget.grid(row=form_row, column=1, sticky="ew", pady=2)
            self.field_vars[field] = var
            form_row += 1
            if field in self.field_buttons:
                button_text, command = self.field_buttons[field]
                ttk.Button(right, text=button_text, command=command).grid(
                    row=form_row, column=1, sticky="w", pady=(0, 4)
                )
                form_row += 1

        if help_text:
            if help_popup:
                ttk.Button(right, text="Help", command=self._show_help).grid(
                    row=form_row, column=0, sticky="w", pady=(10, 0)
                )
            else:
                ttk.Label(right, text=help_text, foreground="#666", wraplength=260, justify="left").grid(
                    row=form_row, column=0, columnspan=2, sticky="w", pady=(10, 0)
                )

    # -- public API ---------------------------------------------------------

    def set_entries(self, entries: list):
        self.entries = entries
        self._refresh()

    def commit_pending_edits(self):
        self._commit_form()

    def refresh_current_row(self):
        """Re-syncs the form and this row's own tree display from
        ``current_entry``'s real, current attribute values -- for a
        caller that edited an entry's own field(s) directly (bypassing
        ``field_vars``/its own text-entry widget entirely, e.g. a real
        multi-select popup writing straight into a list field this
        generic editor has no widget for), so both stay in step with
        that real edit."""

        entry = self.current_entry
        if entry is None:
            return
        self._load_into_form(entry)
        iid = self._iid(entry)
        if self.tree.exists(iid):
            self.tree.item(iid, values=self._row_values(entry))

    # -- internals ------------------------------------------------------------

    def _show_help(self):
        messagebox.showinfo(f"{self.entry_label} Help", self.help_text, parent=self)

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

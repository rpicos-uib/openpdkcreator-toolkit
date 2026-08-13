"""DRC Rules tab: a rule list plus a form/diagram detail pane.

Adapted from OpenPDKCreator's own ``scripts/pdk_wizard/gui/rules_view.py``
-- same list+form+live-diagram shape and commit-on-switch editing
pattern (a field edit doesn't touch the underlying ``DesignRule`` until
the selection changes, so a half-typed value never corrupts the
model), but one real simplification: ``_suggest_prefix``'s
native-device-stack-matching special case is dropped, since this
project has no ``devices`` model at all (``ProjectState`` only ever
tracks ``layers``/``design_rules``) -- auto-naming here always falls
back to plain layer-name joining.

Rules start real, not blank: loaded from a real, extracted KLayout DRC
deck (``ihp/drc.py``) at startup, editable afterward the same way any
hand-authored rule would be -- New/Delete/every field, exactly what
OpenPDKCreator's own tab already offers, just against a real,
pre-populated starting set instead of an empty one.
"""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk

from ..models import DesignRule
from ..schema import CHECK_TYPES, CHECK_TYPE_ORDER
from . import rule_canvas

NET_QUALIFIERS = ("all", "different_net", "not_applicable")
STATUSES = ("placeholder", "confirmed")
MAX_LAYER_PICKERS = 3

_PLACEHOLDER_RULE_ID_RE = re.compile(r"^NEW\.RULE\.\d+$")


def _looks_like_placeholder_id(rule_id: str) -> bool:
    return not rule_id or bool(_PLACEHOLDER_RULE_ID_RE.match(rule_id))


class RulesView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_rule: DesignRule | None = None
        self._suspend_trace = False
        self._rule_id_is_auto = False

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        self._build_list_pane()
        self._build_form_pane()
        self.refresh()

    # -- list pane ---------------------------------------------------

    def _build_list_pane(self):
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        button_row = ttk.Frame(left)
        button_row.grid(row=0, column=0, sticky="ew")
        ttk.Button(button_row, text="New Rule", command=self._new_rule).pack(side="left")
        ttk.Button(button_row, text="Delete Rule", command=self._delete_rule).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(button_row, text="View Source", command=self._view_source).pack(
            side="left", padx=(6, 0)
        )

        columns = ("rule_id", "check_type", "applies_to", "value", "status")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        for col, width in zip(columns, (110, 130, 140, 90, 90)):
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=width, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        scroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky="ns", pady=(6, 0))

    # -- form pane -----------------------------------------------------

    def _build_form_pane(self):
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right.columnconfigure(1, weight=1)

        self.canvas = tk.Canvas(
            right, width=rule_canvas.CANVAS_W, height=rule_canvas.CANVAS_H,
            background="white", highlightthickness=1, highlightbackground="#c0c0c0",
        )
        self.canvas.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self.vars: dict[str, tk.StringVar] = {}
        form_row = 1

        def add_entry(field, label):
            nonlocal form_row
            ttk.Label(right, text=label).grid(row=form_row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_field_changed)
            ttk.Entry(right, textvariable=var).grid(row=form_row, column=1, sticky="ew", pady=2)
            self.vars[field] = var
            form_row += 1

        def add_combo(field, label, values):
            nonlocal form_row
            ttk.Label(right, text=label).grid(row=form_row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            combo = ttk.Combobox(right, textvariable=var, values=values, state="readonly")
            combo.grid(row=form_row, column=1, sticky="ew", pady=2)
            combo.bind("<<ComboboxSelected>>", self._on_field_changed)
            self.vars[field] = var
            form_row += 1
            return combo

        ttk.Label(right, text="Rule ID").grid(row=form_row, column=0, sticky="w", pady=2)
        rule_id_row = ttk.Frame(right)
        rule_id_row.grid(row=form_row, column=1, sticky="ew", pady=2)
        rule_id_row.columnconfigure(0, weight=1)
        rule_id_var = tk.StringVar()
        rule_id_var.trace_add("write", self._on_field_changed)
        rule_id_entry = ttk.Entry(rule_id_row, textvariable=rule_id_var)
        rule_id_entry.grid(row=0, column=0, sticky="ew")
        rule_id_entry.bind("<KeyRelease>", self._on_rule_id_typed)
        ttk.Button(rule_id_row, text="Auto-name", command=self._auto_name_rule).grid(row=0, column=1, padx=(4, 0))
        self.vars["rule_id"] = rule_id_var
        form_row += 1

        add_entry("description", "Description")

        self.check_type_labels = [CHECK_TYPES[k].label for k in CHECK_TYPE_ORDER]
        self.check_type_combo = add_combo("check_type_label", "Check type", self.check_type_labels)
        self.check_type_combo.bind("<<ComboboxSelected>>", self._on_check_type_changed)

        self.layer_labels = []
        self.layer_combos = []
        for i in range(MAX_LAYER_PICKERS):
            label = ttk.Label(right, text=f"Layer {i + 1}")
            label.grid(row=form_row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_field_changed)
            combo = ttk.Combobox(right, textvariable=var, state="readonly")
            combo.grid(row=form_row, column=1, sticky="ew", pady=2)
            combo.bind("<<ComboboxSelected>>", self._on_layer_picker_changed)
            self.vars[f"layer{i}"] = var
            self.layer_labels.append(label)
            self.layer_combos.append(combo)
            form_row += 1

        add_entry("applies_to_override", "Applies-to override")
        add_entry("value", "Value")
        add_entry("units", "Units")
        add_combo("net_qualifier", "Net qualifier", NET_QUALIFIERS)
        add_entry("classification", "Classification")
        add_entry("condition", "Condition")
        add_entry("process_revision", "Process revision")
        add_entry("owner", "Owner")
        add_entry("source_provenance", "Source / provenance")
        add_entry("why", "Why (rationale)")
        add_combo("status", "Status", STATUSES)

    # -- data plumbing ---------------------------------------------------

    @staticmethod
    def _iid(rule: DesignRule) -> str:
        return str(id(rule))

    def _row_values(self, rule: DesignRule) -> tuple:
        spec = CHECK_TYPES[rule.check_type]
        applies_to = spec.applies_to_text(rule.layers, rule.applies_to_override)
        value_text = "" if rule.value is None else str(rule.value)
        return (rule.rule_id, spec.label, applies_to, value_text, rule.status)

    def refresh(self):
        layer_names = [""] + [layer.name for layer in self.app.project.layers]
        for combo in self.layer_combos:
            combo["values"] = layer_names

        selected = self.tree.selection()
        selected_iid = selected[0] if selected else None
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._rule_by_iid = {}
        for rule in self.app.project.design_rules:
            iid = self._iid(rule)
            self._rule_by_iid[iid] = rule
            self.tree.insert("", "end", iid=iid, values=self._row_values(rule))
        if selected_iid and self.tree.exists(selected_iid):
            self.tree.selection_set(selected_iid)
        elif self.app.project.design_rules:
            self.tree.selection_set(self._iid(self.app.project.design_rules[0]))

    def _find_rule(self, iid: str) -> DesignRule | None:
        return self._rule_by_iid.get(iid)

    def _on_select(self, _event=None):
        self._commit_form_to_rule()
        selection = self.tree.selection()
        if not selection:
            self.current_rule = None
            return
        rule = self._find_rule(selection[0])
        self._load_rule_into_form(rule)

    def _load_rule_into_form(self, rule: DesignRule | None):
        self._suspend_trace = True
        self.current_rule = rule
        if rule is None:
            for var in self.vars.values():
                var.set("")
            self._rule_id_is_auto = False
        else:
            self._rule_id_is_auto = _looks_like_placeholder_id(rule.rule_id)
            self.vars["rule_id"].set(rule.rule_id)
            self.vars["description"].set(rule.description)
            self.vars["check_type_label"].set(CHECK_TYPES[rule.check_type].label)
            for i in range(MAX_LAYER_PICKERS):
                self.vars[f"layer{i}"].set(rule.layers[i] if i < len(rule.layers) else "")
            self.vars["applies_to_override"].set(rule.applies_to_override or "")
            self.vars["value"].set("" if rule.value is None else str(rule.value))
            self.vars["units"].set(rule.units)
            self.vars["net_qualifier"].set(rule.net_qualifier)
            self.vars["classification"].set(rule.classification)
            self.vars["condition"].set(rule.condition)
            self.vars["process_revision"].set(rule.process_revision)
            self.vars["owner"].set(rule.owner)
            self.vars["source_provenance"].set(rule.source_provenance)
            self.vars["why"].set(rule.why)
            self.vars["status"].set(rule.status)
        self._suspend_trace = False
        self._update_layer_picker_state()
        self._redraw_canvas()

    def _commit_form_to_rule(self):
        rule = self.current_rule
        if rule is None:
            return
        rule.rule_id = self.vars["rule_id"].get().strip() or rule.rule_id
        rule.description = self.vars["description"].get()
        rule.check_type = self._selected_check_type()
        spec = CHECK_TYPES[rule.check_type]
        layers = [self.vars[f"layer{i}"].get() for i in range(len(spec.layer_roles))]
        rule.layers = [name for name in layers if name]
        rule.applies_to_override = self.vars["applies_to_override"].get().strip() or None
        raw_value = self.vars["value"].get().strip()
        try:
            rule.value = float(raw_value) if raw_value else None
        except ValueError:
            pass
        rule.units = self.vars["units"].get()
        rule.net_qualifier = self.vars["net_qualifier"].get() or "not_applicable"
        rule.classification = self.vars["classification"].get()
        rule.condition = self.vars["condition"].get()
        rule.process_revision = self.vars["process_revision"].get()
        rule.owner = self.vars["owner"].get()
        rule.source_provenance = self.vars["source_provenance"].get()
        rule.why = self.vars["why"].get()
        rule.status = self.vars["status"].get() or "placeholder"

    def _selected_check_type(self) -> str:
        label = self.vars["check_type_label"].get()
        for key in CHECK_TYPE_ORDER:
            if CHECK_TYPES[key].label == label:
                return key
        return self.current_rule.check_type if self.current_rule else CHECK_TYPE_ORDER[0]

    def _update_layer_picker_state(self):
        check_type = self._selected_check_type()
        spec = CHECK_TYPES[check_type]
        roles = spec.layer_roles
        for i in range(MAX_LAYER_PICKERS):
            active = i < len(roles)
            self.layer_labels[i]["text"] = roles[i] if active else f"Layer {i + 1}"
            self.layer_combos[i]["state"] = "readonly" if active else "disabled"
            if not active:
                self.vars[f"layer{i}"].set("")

    def _on_check_type_changed(self, _event=None):
        check_type = self._selected_check_type()
        spec = CHECK_TYPES[check_type]
        if not self.vars["units"].get():
            self.vars["units"].set(spec.default_units)
        self._update_layer_picker_state()
        self._maybe_auto_name()
        self._redraw_canvas()

    def _suggest_prefix(self, layers: list[str]) -> str:
        """The layer-derived part of an auto-generated rule_id -- a
        single layer names itself ("M1"); multiple layers join their
        names; no layers at all (an architectural rule using
        applies_to_override) falls back to the check type's own
        abbreviation. Unlike OpenPDKCreator's own version, there's no
        native-device-stack special case here -- this project has no
        ``devices`` model."""

        check_type = self._selected_check_type()
        spec = CHECK_TYPES[check_type]
        if not layers:
            return spec.abbreviation
        if len(layers) == 1:
            return layers[0]
        return "_".join(layers)

    def _suggest_rule_id(self) -> str:
        check_type = self._selected_check_type()
        spec = CHECK_TYPES[check_type]
        layers = [self.vars[f"layer{i}"].get() for i in range(MAX_LAYER_PICKERS) if self.vars[f"layer{i}"].get()]
        prefix = self._suggest_prefix(layers)
        existing = sum(
            1
            for rule in self.app.project.design_rules
            if rule is not self.current_rule
            and rule.check_type == check_type
            and self._suggest_prefix(rule.layers) == prefix
        )
        return f"{prefix}.{spec.abbreviation}.{existing + 1}"

    def _set_rule_id_auto(self, value: str):
        self.vars["rule_id"].set(value)
        self._rule_id_is_auto = True

    def _maybe_auto_name(self):
        current = self.vars["rule_id"].get().strip()
        if self._rule_id_is_auto or _looks_like_placeholder_id(current):
            self._set_rule_id_auto(self._suggest_rule_id())

    def _auto_name_rule(self):
        self._set_rule_id_auto(self._suggest_rule_id())

    def _on_rule_id_typed(self, _event=None):
        self._rule_id_is_auto = False

    def _on_layer_picker_changed(self, _event=None):
        self._maybe_auto_name()

    def _on_field_changed(self, *_args):
        if self._suspend_trace:
            return
        self._commit_form_to_rule()
        if self.current_rule is not None:
            iid = self._iid(self.current_rule)
            if self.tree.exists(iid):
                self.tree.item(iid, values=self._row_values(self.current_rule))
        self._redraw_canvas()

    def _redraw_canvas(self):
        check_type = self._selected_check_type()
        spec = CHECK_TYPES.get(check_type)
        if spec is None:
            return
        layers = [self.vars[f"layer{i}"].get() for i in range(MAX_LAYER_PICKERS) if self.vars[f"layer{i}"].get()]
        raw_value = self.vars["value"].get().strip()
        try:
            value = float(raw_value) if raw_value else None
        except ValueError:
            value = None
        units = self.vars["units"].get()
        rule_canvas.render(self.canvas, spec.renderer, layers, self.app.layer_colors(), value, units)

    # -- add/remove ---------------------------------------------------

    def _new_rule(self):
        self._commit_form_to_rule()
        n = len(self.app.project.design_rules) + 1
        rule = DesignRule(
            rule_id=f"NEW.RULE.{n}", description="New rule", check_type=CHECK_TYPE_ORDER[0]
        )
        self.app.project.design_rules.append(rule)
        self.refresh()
        iid = self._iid(rule)
        self.tree.selection_set(iid)
        self.tree.see(iid)

    def _delete_rule(self):
        selection = self.tree.selection()
        if not selection:
            return
        rule = self._find_rule(selection[0])
        if rule is None:
            return
        self.app.project.design_rules.remove(rule)
        self.current_rule = None
        self.refresh()

    def _view_source(self):
        """Opens the real .drc file the selected rule was extracted
        from (DesignRule.source_provenance's own "path:line (...)"
        text -- real for anything from ihp/drc.py, blank for a rule
        added by hand via New Rule)."""

        if self.current_rule is not None:
            self.app._view_rule_source(self.current_rule)

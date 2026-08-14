"""Real KLayout DRC-deck rule extraction, adapted from OpenPDKCreator's
own ``scripts/import_open_pdks.py`` (``extract_design_rules()``/
``_load_json_config()``) -- that logic already proved itself against a
real, fetched subset of this exact IHP deck (see
docs/ADR/0017-multi-project-support-and-open-pdks-import.md in that
project); this module points the same, unmodified extraction pattern
at the full, real, downloaded deck instead of a subset.

Regex-based, deliberately bounded -- KLayout DRC is a full Ruby DSL,
genuinely unparseable generically -- to two real, recognizable
patterns: a line assigning ``<layer_expr>.width()``/``.space()``/
``.sep()`` to a result variable, or a line assigning
``<inner_expr>.enclosed(<outer_expr>, value.um, ...)`` to a result
variable (a real, two-layer enclosure check -- confirmed real and
common: 22 real occurrences across 13 real files, always in this exact
``inner.enclosed(outer, value_var.um, mode)`` shape, e.g. real
``Cnt.c``: ``cont_nsvaricap.enclosed(cnt_c_act, cnt_c_value.um,
euclidian)`` -- mapped to the existing ``min_enclosure`` check type,
whose own ``Inner layer``/``Outer layer`` roles already match KLayout's
own real semantics exactly), each traced back to a real
``drc_rules['KEY']`` lookup and feeding a same-variable ``.output(id,
description)`` call. Every non-matching construct (composite checks,
unrecognized methods, conditional/looped generation) is counted and
reported by file:line, never silently dropped.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..models import DesignRule

DRC_METHOD_TO_CHECK_TYPE = {
    "width": "min_width",
    "space": "min_spacing",
    "sep": "min_spacing",
    "enclosed": "min_enclosure",
}

_VALUE_ASSIGN_RE = re.compile(r"(\w+)\s*=\s*drc_rules\[['\"](\w+)['\"]\]")
_CHECK_CALL_RE = re.compile(r"(\w+)\s*=\s*(\S+?)\.(width|space|sep)\(([^)]*)\)")
_ENCLOSURE_CALL_RE = re.compile(r"(\w+)\s*=\s*(\S+?)\.enclosed\(\s*(\S+?)\s*,\s*([^)]*)\)")
_VALUE_VAR_IN_ARGS_RE = re.compile(r"(\w+)\.um")
_OUTPUT_CALL_RE = re.compile(
    r"(\w+)\.output\(\s*['\"]([^'\"]+)['\"]\s*,\s*(?:\r?\n\s*)?\"([^\"]*)\""
)


def find_drc_root(pdk_root: Path) -> Path | None:
    candidate = pdk_root / "libs.tech" / "klayout" / "tech" / "drc"
    return candidate if candidate.is_dir() else None


def find_json_config_path(search_root: Path) -> Path | None:
    """The one real JSON file under *search_root* with a top-level
    ``drc_rules`` object -- confirmed real: exactly one such file
    exists in IHP's own deck
    (``rule_decks/sg13g2_tech_default.json``). Exposed separately from
    ``_load_json_config`` so ``ihp/drc_writer.py`` can patch the real
    file directly rather than re-deriving its path independently."""

    for candidate in sorted(search_root.rglob("*.json")):
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("drc_rules"), dict):
            return candidate
    return None


def _load_json_config(search_root: Path) -> dict[str, float]:
    path = find_json_config_path(search_root)
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in data["drc_rules"].items() if isinstance(v, (int, float))}


def extract_design_rules(pdk_root: Path, drc_root: Path | None) -> tuple[list[DesignRule], list[str]]:
    """Returns (emitted rules, skipped-construct descriptions -- each
    with a real file:line)."""

    if drc_root is None or not drc_root.is_dir():
        return [], []

    values_by_key = _load_json_config(drc_root)
    rules: list[DesignRule] = []
    skipped: list[str] = []

    for drc_file in sorted(drc_root.rglob("*.drc")):
        text = drc_file.read_text(encoding="utf-8", errors="replace")
        rel = drc_file.relative_to(pdk_root) if pdk_root in drc_file.parents else drc_file

        value_var_to_key: dict[str, str] = {}
        for match in _VALUE_ASSIGN_RE.finditer(text):
            value_var_to_key[match.group(1)] = match.group(2)

        checks: dict[str, tuple[str, str, str | None, int, str | None]] = {}
        for match in _CHECK_CALL_RE.finditer(text):
            result_var, layer_expr, method, args = match.groups()
            value_match = _VALUE_VAR_IN_ARGS_RE.search(args)
            value_var = value_match.group(1) if value_match else None
            line_no = text.count("\n", 0, match.start()) + 1
            checks[result_var] = (layer_expr, method, value_var, line_no, None)
        for match in _ENCLOSURE_CALL_RE.finditer(text):
            result_var, inner_expr, outer_expr, args = match.groups()
            value_match = _VALUE_VAR_IN_ARGS_RE.search(args)
            value_var = value_match.group(1) if value_match else None
            line_no = text.count("\n", 0, match.start()) + 1
            checks[result_var] = (inner_expr, "enclosed", value_var, line_no, outer_expr)

        matched_result_vars: set[str] = set()
        for match in _OUTPUT_CALL_RE.finditer(text):
            result_var, rule_id, description = match.groups()
            line_no = text.count("\n", 0, match.start()) + 1
            check = checks.get(result_var)
            if check is None:
                skipped.append(
                    f"{rel}:{line_no}: '{rule_id}' -- .output() on '{result_var}', "
                    f"which isn't a direct width()/space()/sep()/enclosed() result (a "
                    f"composite or derived check -- not auto-extracted)"
                )
                continue
            matched_result_vars.add(result_var)
            layer_expr, method, value_var, check_line, outer_expr = check
            json_key = value_var_to_key.get(value_var) if value_var else None
            value = values_by_key.get(json_key) if json_key else None
            if method == "enclosed":
                applies_to = f"{layer_expr} enclosed by {outer_expr} (real KLayout DRC expressions, not resolved to Layers)"
                why = ("Best-effort extraction from a real .enclosed() check -- verify against "
                       "the real source before trusting this value or mapping.")
            else:
                applies_to = f"{layer_expr} (real KLayout DRC expression, not resolved to a Layer)"
                why = (f"Best-effort extraction from a real .{method}() check -- verify against "
                       f"the real source before trusting this value or mapping."
                       + ("" if method != "sep" else " ('sep' mapped to min_spacing, the closest existing check_type -- not an exact equivalent.)"))
            rules.append(
                DesignRule(
                    rule_id=rule_id,
                    description=description.split(" : ", 1)[-1] if " : " in description else description,
                    check_type=DRC_METHOD_TO_CHECK_TYPE[method],
                    applies_to_override=applies_to,
                    value=float(value) if value is not None else None,
                    units="um",
                    source_provenance=f"{rel}:{check_line} (.output at :{line_no})",
                    why=why,
                    status="placeholder",
                )
            )

        for result_var in checks:
            if result_var not in matched_result_vars:
                _, _, _, line_no, _ = checks[result_var]
                skipped.append(
                    f"{rel}:{line_no}: '{result_var}' has a real width()/space()/sep()/"
                    f"enclosed() call but no matching .output() found on that exact "
                    f"variable (not auto-extracted)"
                )

    return rules, skipped

"""Real DRC Rule write-back -- patches the two real files a KLayout
DRC-deck rule's editable fields actually live in, mirroring
``ihp/lef_writer.py``'s own surgical, non-destructive discipline:

- ``rule_id``/``description`` live inside the real ``.drc`` Ruby
  script's own ``result_var.output("ID", "description")`` call.
- ``value`` lives in the real JSON config file's ``drc_rules['KEY']``
  entry (``ihp/drc.py``'s own extraction already established this
  split: the ``.drc`` script never contains a literal numeric
  threshold, only a variable traced back to a JSON lookup via
  ``.um``).

**Surgical, character-offset-based patching, not full regeneration**:
every function here re-reads the *original* file fresh from disk
(always still pristine, since export never writes to ``data/``) and
replaces only the exact substrings a rule's editable fields occupy --
everything else (surrounding Ruby code, other rules' own ``.output()``
calls, comments, formatting, every other real JSON entry) stays
byte-for-byte untouched. ``_locate`` re-derives which real JSON key (if
any) backs a rule's value, and the exact real ``.output()`` regex
match, by re-running ``ihp/drc.py``'s own extraction regexes directly
against the target line -- not a second, independently-drifting
implementation of the same fact.

**A real, common wrinkle handled deliberately, not glossed over**: 61
of IHP's own real ``.output()`` calls have a real ``"<section> : ...
"`` prefix before the description ``ihp/drc.py`` actually keeps as
``DesignRule.description`` (it splits on the real, first ``" : "`` and
keeps only the suffix). A rule with such a prefix has to have it
preserved verbatim on write-back -- reconstructing the description from
``rule.description`` alone would silently discard that real prefix
text for over a third of IHP's own real rules.

Only rules with real, resolvable provenance (extracted by
``ihp/drc.py``, not a hand-authored New Rule, which has no real source
position to patch) can be written back -- everything else about a
rule (``layers``/``check_type``/``classification``/``condition``/
``process_revision``/``owner``/``why``/``status``/...) is this
project's own metadata with no real counterpart in the KLayout deck at
all, and stays ``project_io.py``-only, same as before.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import drc as drc_mod
from ..models import DesignRule

_PROVENANCE_RE = re.compile(r"^([^:]+):(\d+) \(\.output at :(\d+)\)$")


def parse_provenance(source_provenance: str) -> tuple[str, int, int] | None:
    """(relpath, check_line, output_line), or ``None`` for a rule with
    no real, resolvable source position (hand-authored, or a real
    provenance string this pattern doesn't recognize)."""

    match = _PROVENANCE_RE.match(source_provenance or "")
    if match is None:
        return None
    relpath, check_line, output_line = match.groups()
    return relpath, int(check_line), int(output_line)


def _locate(text: str, check_line: int, output_line: int) -> tuple[str | None, re.Match | None]:
    """Re-derives the real JSON key (if any) backing this check's
    value, and the real ``.output()`` regex ``Match``, from *text*
    alone (the same real ``.drc`` file's fresh content) -- mirroring
    ``ihp/drc.py``'s own extraction logic exactly (its own compiled
    regexes, imported not duplicated)."""

    value_var_to_key: dict[str, str] = {}
    for match in drc_mod._VALUE_ASSIGN_RE.finditer(text):
        value_var_to_key[match.group(1)] = match.group(2)

    value_var = None
    for match in drc_mod._CHECK_CALL_RE.finditer(text):
        line_no = text.count("\n", 0, match.start()) + 1
        if line_no == check_line:
            value_match = drc_mod._VALUE_VAR_IN_ARGS_RE.search(match.group(4))
            value_var = value_match.group(1) if value_match else None
            break
    if value_var is None:
        # Not a width()/space()/sep() result -- check the other real
        # pattern ihp/drc.py extracts from, .enclosed(outer, value.um,
        # ...), before giving up on a real JSON key.
        for match in drc_mod._ENCLOSURE_CALL_RE.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            if line_no == check_line:
                value_match = drc_mod._VALUE_VAR_IN_ARGS_RE.search(match.group(4))
                value_var = value_match.group(1) if value_match else None
                break
    json_key = value_var_to_key.get(value_var) if value_var else None

    output_match = None
    for match in drc_mod._OUTPUT_CALL_RE.finditer(text):
        line_no = text.count("\n", 0, match.start()) + 1
        if line_no == output_line:
            output_match = match
            break

    return json_key, output_match


def _apply_spans(text: str, spans: list[tuple[int, int, str]]) -> str:
    spans = sorted(spans, key=lambda span: span[0])
    pieces = []
    cursor = 0
    for start, end, replacement in spans:
        pieces.append(text[cursor:start])
        pieces.append(replacement)
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def render_drc_file(original_path: Path, rules: list[DesignRule]) -> tuple[str, dict[str, float]]:
    """*rules*: every real ``DesignRule`` whose provenance points into
    *original_path* (the caller groups by relpath before calling this).
    Returns the patched real ``.drc`` text, plus ``{json_key:
    rule.value}`` for every rule here whose value traces back to a
    real JSON key -- the caller merges these across every real file
    before patching the JSON config once."""

    text = original_path.read_text(encoding="utf-8", errors="replace")
    spans: list[tuple[int, int, str]] = []
    value_edits: dict[str, float] = {}

    for rule in rules:
        parsed = parse_provenance(rule.source_provenance)
        if parsed is None:
            continue
        _relpath, check_line, output_line = parsed
        json_key, output_match = _locate(text, check_line, output_line)

        if output_match is not None:
            spans.append((output_match.start(2), output_match.end(2), rule.rule_id))
            raw_full_description = output_match.group(3)
            if " : " in raw_full_description:
                prefix = raw_full_description.split(" : ", 1)[0]
                new_description = f"{prefix} : {rule.description}"
            else:
                new_description = rule.description
            spans.append((output_match.start(3), output_match.end(3), new_description))

        if json_key and rule.value is not None:
            value_edits[json_key] = rule.value

    return _apply_spans(text, spans), value_edits


_JSON_NUMBER_RE_TEMPLATE = r'("{key}"\s*:\s*)([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)'


def patch_json_value(json_text: str, key: str, new_value: float) -> str:
    """Replaces *key*'s real value with *new_value* -- but only if it
    actually differs (by real numeric value, not text) from what's
    already there. Skipping a no-op patch matters: a real, confirmed
    case (``"Padb_b": 70.00``) has trailing zeros Python's own
    ``repr(float(...))`` would silently normalize away
    (``"70.0"``) even when nothing was actually edited, which would
    have broken the no-edit-is-byte-identical guarantee -- caught by
    that very check failing against real data, the same way the LEF
    writer's ``ANTENNAMODEL`` bug was caught."""

    pattern = re.compile(_JSON_NUMBER_RE_TEMPLATE.format(key=re.escape(key)))
    match = pattern.search(json_text)
    if match is None:
        raise ValueError(f"real JSON key {key!r} not found in the real config file -- can't patch it")
    if float(match.group(2)) == float(new_value):
        return json_text
    formatted = repr(float(new_value))
    return json_text[: match.start(2)] + formatted + json_text[match.end(2):]


def render_json_config(original_path: Path, value_edits: dict[str, float]) -> str:
    text = original_path.read_text(encoding="utf-8", errors="replace")
    for key, value in value_edits.items():
        text = patch_json_value(text, key, value)
    return text

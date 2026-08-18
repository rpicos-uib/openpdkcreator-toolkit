"""Real Qucs-S component ``.xml`` write-back for the in-memory
``QucsComponent.parameters`` this project's Components editor edits --
each real ``Parameter``'s own ``default_value``/``equation`` attribute
only; every other real element (``Description``/``Models``/
``Netlists``/``Symbols``, and every other real ``Parameter`` attribute
-- ``name``/``unit``/``show``) is left completely untouched.

Standard ``xml.etree.ElementTree`` is used for *reading*
(``pdklib/qucs_sym.py``, a read-only domain there), but deliberately
**not** for write-back: a full ElementTree round-trip
re-serialization would reformat the whole real file (attribute order,
quoting, whitespace) -- the same real risk that already ruled out
ElementTree for KLayout's own real ``.lyp`` write-back
(``pdklib/layers.py``/``layers_writer.py``). Instead, this module does
its own, separate, surgical text scan locating each real
``<Parameter ...>`` opening tag's own real character span (confirmed
real: not always a single physical line -- a long real ``equation=``
value can wrap the tag across several lines, e.g. ``rhigh.xml``'s own
real ``R`` parameter), and patches only the real ``default_value=``/
``equation=`` attribute value found inside that span.

**Position-based, not name-based, matching**: a real ``Parameter``
element has no other stable real identity to key off of, so this
project's own current parameter list is zipped against the real file's
own ``<Parameter ...>`` tags strictly by order -- this project's own
editor never adds/deletes/reorders a real Parameter, only edits an
existing one's own value, so order is always preserved. If the real
tag count and the in-memory parameter count ever disagree (a real,
unexpected shape this project doesn't produce), the whole file is
returned untouched rather than risk a wrong patch.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import qucs_sym as qucs_sym_mod
from . import text_utils

_PARAM_START_RE = re.compile(r"<Parameter\b")
_VALUE_ATTR_RE = re.compile(r'\b(default_value|equation)="((?:[^"\\]|\\.)*)"')


def _find_param_tag_spans(text: str) -> list[tuple[int, int]]:
    """[(start, end)] for every real ``<Parameter ...>`` opening tag,
    in real file order -- *end* points just past the tag's own real
    closing ``>``. Quote-aware: a real ``>`` can never appear inside a
    real attribute value here (confirmed by direct search across the
    whole downloaded deck), but this scan ignores one anyway rather
    than assume."""

    spans = []
    n = len(text)
    for match in _PARAM_START_RE.finditer(text):
        start = match.start()
        i = match.end()
        in_quotes = False
        while i < n:
            ch = text[i]
            if in_quotes:
                if ch == '"':
                    in_quotes = False
            elif ch == '"':
                in_quotes = True
            elif ch == ">":
                break
            i += 1
        spans.append((start, i + 1))
    return spans


def _patch_param_tag(tag_text: str, param: qucs_sym_mod.QucsParameter) -> str:
    attrs = param.raw_attrs
    new_tag = tag_text
    for key in ("default_value", "equation"):
        if key not in attrs:
            continue
        pattern = re.compile(rf'\b{key}="(?:[^"\\]|\\.)*"')
        if pattern.search(new_tag):
            new_tag = pattern.sub(f'{key}="{attrs[key]}"', new_tag, count=1)
    return new_tag


def render_component_file(original_path: Path, component: qucs_sym_mod.QucsComponent) -> str:
    """Real, patched Qucs-S component ``.xml`` text for *component*.
    With no edits at all, this is byte-identical to the real original
    file."""

    original_text = original_path.read_text(encoding="utf-8", errors="replace")
    spans = _find_param_tag_spans(original_text)

    if len(spans) != len(component.parameters):
        # a real, unexpected shape -- refuse to guess rather than risk a wrong patch.
        return text_utils.restore_crlf_if_needed(original_path, original_text)

    output: list[str] = []
    cursor = 0
    for (start, end), param in zip(spans, component.parameters):
        output.append(original_text[cursor:start])
        output.append(_patch_param_tag(original_text[start:end], param))
        cursor = end
    output.append(original_text[cursor:])
    text = "".join(output)
    return text_utils.restore_crlf_if_needed(original_path, text)


def export_component_file(component: qucs_sym_mod.QucsComponent, export_path: Path) -> None:
    text = render_component_file(component.source_path, component)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

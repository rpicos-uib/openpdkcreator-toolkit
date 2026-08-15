"""Real KLayout ``.lyp`` write-back -- the same surgical,
position-targeted discipline as every other writer here: re-reads the
real *original* file fresh from disk and patches only the exact real
tag lines a layer's editable fields occupy, leaving every other real
line -- including the ten real fields this project doesn't model
(``frame-brightness``/``fill-brightness``/``dither-pattern``/
``line-style``/``valid``/``visible``/``transparent``/``width``/
``marked``/``animation``) and the real, unrelated
``<custom-dither-pattern>``/``<custom-line-style>`` content that
follows the last real layer block in IHP's own file -- byte-for-byte
untouched.

**Only four of a real layer's fields have any real ``.lyp``
counterpart**: ``name``, ``gds_layer``/``gds_datatype`` (together, the
real ``<source>L/D</source>`` text), ``frame_color``, ``fill_color``.
Every other editable field on ``models.Layer`` (``purpose``, ``plane``,
``stack_order``, ``streamout_allowed``, ``notes``, ``status``) is this
project's own metadata with no real counterpart in a ``.lyp`` at all --
project-only, saved via ``project_io.py``, never written back here,
the same "only real, resolvable fields get real write-back" precedent
``ihp/drc_writer.py``'s own docstring already established for
``DesignRule``.

Per-field diffing against a fresh re-parse, not blanket re-emission:
matches every other writer here (see e.g. ``ihp/liberty_writer.py``'s
own docstring for why) -- an unedited field's real original line is
preserved exactly, not silently reformatted.
"""

from __future__ import annotations

from pathlib import Path

from . import layers as layers_mod
from . import text_utils
from ..models import Layer

_DEFAULT_NEW_LAYER_FIELDS = (
    ("frame-brightness", "0"),
    ("fill-brightness", "0"),
    ("dither-pattern", "I1"),
    ("line-style", "C0"),
    ("valid", "true"),
    ("visible", "true"),
    ("transparent", "false"),
    ("width", "1"),
    ("marked", "false"),
    ("animation", "0"),
)
"""Real, observed default values for a real layer's own unmodeled
fields (IHP's own real ``Substrate.drawing`` block, the first real
entry in ``sg13g2.lyp``, uses exactly these) -- used only when
rendering a brand-new layer this session, never touched for an
existing real one."""


def _format_source(gds_layer: int | None, gds_datatype: int | None) -> str | None:
    if gds_layer is None or gds_datatype is None:
        return None
    return f"{gds_layer}/{gds_datatype}"


def _leading_whitespace(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _field_updates(layer: Layer, fresh: Layer | None) -> dict[str, str | None]:
    updates: dict[str, str | None] = {}
    fresh_name = fresh.name if fresh else ""
    if layer.name != fresh_name:
        updates["name"] = layer.name
    fresh_source = _format_source(fresh.gds_layer, fresh.gds_datatype) if fresh else None
    current_source = _format_source(layer.gds_layer, layer.gds_datatype)
    if current_source != fresh_source:
        updates["source"] = current_source
    fresh_frame = fresh.frame_color if fresh else ""
    if layer.frame_color != fresh_frame:
        updates["frame-color"] = layer.frame_color
    fresh_fill = fresh.fill_color if fresh else ""
    if layer.fill_color != fresh_fill:
        updates["fill-color"] = layer.fill_color
    return updates


def _render_block_interior(interior: list[str], updates: dict[str, str | None]) -> list[str]:
    result: list[str] = []
    for line in interior:
        stripped = line.strip()
        matched_key = None
        for key in updates:
            if stripped.startswith(f"<{key}>") and stripped.endswith(f"</{key}>"):
                matched_key = key
                break
        if matched_key is None:
            result.append(line)
            continue
        new_value = updates[matched_key]
        if new_value is None:
            continue  # cleared -- real .lyp fields here are never legitimately empty; omit rather than guess.
        result.append(f"{_leading_whitespace(line)}<{matched_key}>{new_value}</{matched_key}>")
    return result


def _render_new_layer_block(layer: Layer, indent: str) -> list[str]:
    # Real, confirmed field order (all 377 real blocks in sg13g2.lyp
    # agree): frame-color, fill-color, then the ten unmodeled fields,
    # then name, source.
    inner = indent + "  "
    lines = [
        f"{indent}<properties>",
        f"{inner}<frame-color>{layer.frame_color}</frame-color>",
        f"{inner}<fill-color>{layer.fill_color}</fill-color>",
    ]
    for key, value in _DEFAULT_NEW_LAYER_FIELDS:
        lines.append(f"{inner}<{key}>{value}</{key}>")
    lines.append(f"{inner}<name>{layer.name}</name>")
    source = _format_source(layer.gds_layer, layer.gds_datatype) or "0/0"
    lines.append(f"{inner}<source>{source}</source>")
    lines.append(f"{indent}</properties>")
    return lines


def render_lyp_file(original_path: Path, layers: list[Layer]) -> str:
    original_text = original_path.read_text(encoding="utf-8", errors="replace")
    original_lines = original_text.splitlines()
    fresh_blocks = layers_mod.find_layer_blocks(original_path)

    if not fresh_blocks:
        # A brand-new skeleton .lyp (see layers.py's create_new_lyp_file)
        # with no real <properties> blocks at all to anchor a new one
        # after -- anchor instead just before the real closing
        # </layer-properties> tag, so New Layer works the same as
        # adding a layer to a real, downloaded file.
        close_idx = next(
            (i for i, line in enumerate(original_lines) if line.strip() == "</layer-properties>"),
            len(original_lines),
        )
        output = list(original_lines[:close_idx])
        for layer in layers:
            output.extend(_render_new_layer_block(layer, "  "))
        output.extend(original_lines[close_idx:])
        return text_utils.join_preserving_trailing_newline(original_text, output)

    fresh_by_start = {start: (start, end) for start, end, _fields in fresh_blocks}
    fresh_layers_by_start = {layer.start_line: layer for layer in layers_mod.import_layers(original_path.parent, original_path)}

    current_by_start = {layer.start_line: layer for layer in layers if layer.start_line}

    output: list[str] = []
    cursor = 0
    for start_line, end_line, _fields in fresh_blocks:
        start_idx, end_idx = start_line - 1, end_line - 1
        output.extend(original_lines[cursor:start_idx])
        layer = current_by_start.get(start_line)
        if layer is not None:
            full_span = original_lines[start_idx : end_idx + 1]
            fresh_layer = fresh_layers_by_start.get(start_line)
            updates = _field_updates(layer, fresh_layer)
            interior = _render_block_interior(full_span[1:-1], updates)
            output.append(full_span[0])
            output.extend(interior)
            output.append(full_span[-1])
        # else: this real layer was deleted this session -- omit its original text entirely.
        cursor = end_idx + 1

    new_layers = [layer for layer in layers if not layer.start_line]
    if new_layers:
        indent = _leading_whitespace(original_lines[fresh_blocks[-1][0] - 1]) if fresh_blocks else "  "
        for layer in new_layers:
            output.extend(_render_new_layer_block(layer, indent))

    output.extend(original_lines[cursor:])
    return text_utils.join_preserving_trailing_newline(original_text, output)


def export_lyp_file(layers: list[Layer], original_path: Path, export_path: Path) -> None:
    text = render_lyp_file(original_path, layers)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8")

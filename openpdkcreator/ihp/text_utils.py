"""Tiny, shared helper for this project's own real-file writers
(``lef_writer.py``/``drc_writer.py``/``magic_tech_writer.py``/
``netlist_writer.py``/``verilog_writer.py``) -- kept in one place so a
fix here never needs repeating across all five.
"""

from __future__ import annotations


def join_preserving_trailing_newline(original_text: str, output_lines: list[str]) -> str:
    """Joins *output_lines* with real newlines, adding a final one only
    if *original_text* (the real, pristine source this patched text is
    derived from) itself had one -- a real, confirmed case (21 of
    IHP's own real SRAM Verilog files have no trailing newline) where
    unconditionally adding one would silently change a real file's
    byte content even when nothing was actually edited. Found by
    ``main.py export-full``'s own smoking-gun round-trip test at full
    real-PDK scale, not by any one writer's own narrower per-file
    tests (which happened to normalize this exact difference away in
    their own comparison logic, masking it)."""

    text = "\n".join(output_lines)
    if original_text.endswith("\n"):
        text += "\n"
    return text

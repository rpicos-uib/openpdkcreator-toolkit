"""Tiny, shared helpers for this project's own real-file writers -- kept
in one place so a fix here never needs repeating across every writer.
"""

from __future__ import annotations

from pathlib import Path


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


def restore_crlf_if_needed(original_path: Path, text: str) -> str:
    """Reproduces a real, consistent CRLF (``\\r\\n``) line-ending
    convention some real files use (confirmed real: 5 of IHP's own
    real Qucs-S files under ``libs.tech/qucs-s/symbols/``, every real
    line-break in each one -- not a mix) -- undoing
    ``Path.read_text()``'s own universal-newline translation, which
    every writer here relies on for its own text processing but which
    silently discards the real distinction between ``\\r\\n`` and
    plain ``\\n`` before a writer ever sees it. *text* (built with
    plain ``\\n`` line breaks, as every writer here does) is converted
    wholesale to ``\\r\\n`` only when *original_path*'s own real,
    on-disk bytes are confirmed real, uniform CRLF -- a whole-file
    choice, matching every real occurrence found, not a per-line
    guess. Found the same way the trailing-newline bug above was:
    ``main.py export-full``'s own smoking-gun round-trip test at full
    real-PDK scale, not by any one writer's own narrower per-file
    test (whose own comparison logic, via ``Path.read_text()`` on
    *both* sides, happened to normalize this exact real difference
    away, masking it)."""

    raw = original_path.read_bytes()
    if b"\r\n" in raw and raw.count(b"\n") == raw.count(b"\r\n"):
        return text.replace("\r\n", "\n").replace("\n", "\r\n")
    return text

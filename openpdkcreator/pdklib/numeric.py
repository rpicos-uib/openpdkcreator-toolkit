"""Shared, tiny GUI-facing number parsing -- one place for the real,
repeated ``try: self.field = float(value) / except ValueError: pass``
(or ``int(...)``) shape that used to live copy-pasted across every
``*_text`` property setter and GUI form-commit method in this project
(``pdklib/magic_tech.py``, ``gui/rules_view.py``, ``gui/layers_view.py``,
``gui/liberty_editor.py``, ``gui/qucs_view.py``, ...) -- plus, on top
of that real consolidation, real support for typing a number with an
international (SI) scale-factor suffix (``"0.2u"``, ``"1.5k"``,
``"10n"``) instead of the fully-expanded decimal, per direct request.

**Deliberately GUI-facing only, never used for parsing a real,
downloaded PDK file's own text.** Every real file this project parses
(Magic ``.tech``, KLayout ``.drc``/JSON, LEF, Liberty, GDS, Qucs-S/
xschem XML) was hand-verified, deck-wide, to use plain decimal numbers
for every field this project currently reads -- confirmed real, not
assumed, by grepping this project's own real, downloaded IHP deck for
any of the suffixes below before writing this module (none found).
Retrofitting SI-suffix parsing into an existing *file*-parsing regex
would risk silently reinterpreting a real, already-correct value the
moment some future real file happens to contain a trailing letter this
module wasn't meant for it -- exactly the kind of real regression this
project's own "don't guess further" discipline exists to avoid. A
*user*, typing a value into a Tk ``Entry`` field, is a different,
real, and safe place to accept a wider real input format: it can only
ever *add* accepted spellings (a plain ``"0.2"`` still parses to
exactly ``0.2``, byte-for-byte the same real behavior as before), never
change how a real file's own existing text is read.

**Scale factors are real, from ngspice's own official manual (fetched
and read directly, not guessed or assumed from memory)** --
https://ngspice.sourceforge.io/docs/ngspice-html-manual/manual.xhtml's
own "Some Useful Conventions" table, the same real convention every
SPICE-family tool (and this project's own ngspice/xschem/Qucs-S
domains) already shares:

====== ===== ========
Suffix Name  Factor
====== ===== ========
T      Tera  1e12
G      Giga  1e9
Meg    Mega  1e6
K      Kilo  1e3
mil    Mil   25.4e-6
m      milli 1e-3
u      micro 1e-6
n      nano  1e-9
p      pico  1e-12
f      femto 1e-15
a      atto  1e-18
====== ===== ========

**The one real, well-known SPICE trap, handled deliberately, not
missed**: bare ``"m"``/``"M"`` always means *milli*, never mega --
``"Meg"`` (or any of its 3-letter-prefix spellings, matched
case-insensitively) is the only real way to mean mega. Confirmed
directly from the manual's own real, worked prose: "``M``, ``MA``,
``MSec``, and ``MMhos`` all represent the same [milli] scale factor."
``mil`` (1/1000 inch) is matched the same longest-prefix-first way, so
a real ``"1mil"`` doesn't wrongly parse as milli plus an ignored ``il``
suffix. Any other trailing letters (a real, ignored unit hint like
``"10Hz"``/``"5V"``, per that same real convention) are silently
dropped, exactly like real ngspice itself does -- not treated as a
parse failure.
"""

from __future__ import annotations

import re

_SI_SUFFIXES: dict[str, float] = {
    "meg": 1e6,
    "mil": 25.4e-6,
    "t": 1e12,
    "g": 1e9,
    "k": 1e3,
    "m": 1e-3,
    "u": 1e-6,
    "µ": 1e-6,
    "n": 1e-9,
    "p": 1e-12,
    "f": 1e-15,
    "a": 1e-18,
}
# Longest suffix first ("meg"/"mil" before the bare "m" they'd
# otherwise be swallowed by) -- see this module's own docstring.
_SI_SUFFIXES_BY_LENGTH = sorted(_SI_SUFFIXES.items(), key=lambda kv: -len(kv[0]))

_NUMBER_RE = re.compile(r"^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*([a-zA-Zµ]*)\s*$")


def parse_number(text: str) -> float | None:
    """A real, typed decimal (``"0.2"``, ``"-3.5e-2"``), optionally
    followed by a real SI scale-factor suffix (``"0.2u"``) and/or a
    real, ignored unit hint after that (``"10Hz"``) -- see this
    module's own docstring for the real, sourced suffix table. Returns
    ``None`` for anything that doesn't parse (empty text, not a real
    number at all), the same "don't guess, leave it alone" shape every
    caller's own previous ``except ValueError: pass`` already had --
    callers keep that exact behavior by simply checking for ``None``
    before assigning."""

    if not text:
        return None
    match = _NUMBER_RE.match(text)
    if match is None:
        return None
    mantissa, suffix = match.groups()
    value = float(mantissa)
    if not suffix:
        return value
    suffix_lower = suffix.lower()
    for name, factor in _SI_SUFFIXES_BY_LENGTH:
        if suffix_lower.startswith(name):
            return value * factor
    return value


def parse_int(text: str) -> int | None:
    """Same real ``None``-on-failure shape as ``parse_number``, for
    the real, plain (never SI-scaled -- a GDS layer number/angle
    degree count/rank has no physical unit an SI prefix could scale)
    integer fields sharing the exact same repeated
    ``try: ... except ValueError: pass`` boilerplate this module
    exists to consolidate. Real, deliberately stricter than
    ``int(float(text))`` would be -- ``"1.5"`` is a real, honest parse
    failure here, not silently truncated, matching every real caller's
    own previous bare ``int(value)`` behavior exactly."""

    if not text:
        return None
    try:
        return int(text.strip())
    except ValueError:
        return None

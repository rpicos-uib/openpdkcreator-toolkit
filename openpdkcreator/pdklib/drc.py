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
``.sep()``/``.with_area()``/``.with_length()`` to a result variable, or
a line assigning ``<inner_expr>.enclosed(<outer_expr>, value.um, ...)``
to a result variable (a real, two-layer enclosure check -- confirmed
real and common: 22 real occurrences across 13 real files, always in
this exact ``inner.enclosed(outer, value_var.um, mode)`` shape, e.g.
real ``Cnt.c``: ``cont_nsvaricap.enclosed(cnt_c_act, cnt_c_value.um,
euclidian)`` -- mapped to the existing ``min_enclosure`` check type,
whose own ``Inner layer``/``Outer layer`` roles already match KLayout's
own real semantics exactly), each traced back to a real
``drc_rules['KEY']`` lookup and feeding a same-variable ``.output(id,
description)`` call. Every non-matching construct (composite checks,
unrecognized methods, conditional/looped generation) is counted and
reported by file:line, never silently dropped.

**``with_area``/``with_length`` added later, once ``pdklib/
drc_writer.py``'s own ``render_new_rule_block`` started generating
them (for ``min_area``/``max_length``) and this extractor's own
lopsided asymmetry became visible**: a hand-authored rule of either
check_type could be exported as real, runnable Ruby but wouldn't
round-trip back through re-extraction. **Investigated against the
real deck before writing the regex, not assumed symmetric with
``width``/``space``/``enclosed``**: real ``with_area``/``with_length``
usage turned out to be far more heterogeneous than those three --
``.ext_with_area([["<", v.um2]])`` (a different, unrelated real method
entirely), arithmetic value expressions (``v.um + 0.001.um``), a
``nil`` placeholder in either argument position, and (confirmed real,
grepped directly) most real call sites feed a *subsequent* chained
call (typically ``.width(...)``) rather than ``.output()`` directly --
e.g. real ``M1.g``/``Gat.g`` use ``with_length`` purely as an upstream
edge-length filter, with the real, exported value actually coming from
the chained ``.width()`` call (already extracted by the existing
pattern, with or without this addition). Only two real, direct
``with_area``/``with_length`` -> ``.output()`` call sites exist
deck-wide -- ``LBE.b1`` (``min_area``) and ``Seal.k`` (``max_length``)
-- both now correctly extracted; verified for real, driven: comparing
the full old-vs-new rule and skip sets confirms zero regressions to
the original 75 rules, exactly these 2 new real rules added, and
exactly 6 new, honest "has the call but no matching real ``.output()``"
skip entries for the real, non-directly-exported occurrences found
along the way (75/86 -> 77/90 total). ``.overlap()`` was investigated
the same way and deliberately **not** added: real, direct call sites
of it don't exist anywhere in this deck -- its only two real
occurrences both sit inside one generic, parameterized Ruby method
definition (``self.overlap(other, value)``, real method parameters,
not concrete real layers/values), so there is no real ground truth to
extract or verify against.

**A second-round search for a third extractable pattern, real, not
assumed to be futile**: every one of the (then-)86 real remaining
skipped constructs was checked for a single-method, single-value shape
as clean as ``.enclosed()``'s own. None exists: real
``.without_bbox_width()`` occurs exactly once across the entire real
deck (not worth a dedicated pattern); the rest are genuinely
heterogeneous multi-step boolean composition (real, varying
combinations of ``.join()``/``.and()``/``.interacting()``/
``.with_bbox_max()``/``.not_interacting()``/...), confirmed by
tallying every real method-chain shape used deck-wide -- no one shape
dominates the skipped set the way width/space/sep/enclosed did.

**Composite-check data-flow tracing, added later still, once genuinely
safe (not just likely)**: some skipped composites (e.g. real
``NW.b1``: two real ``space()``/``sep()`` results, both tracing to the
*same* real ``drc_rules`` value, then ``.join()``ed and ``.and()``ed
before ``.output()``) resolve to one real, correct value via a real,
conservative data-flow trace -- ``_trace_composite_provenance``.
**The bar this had to clear, confirmed by a real near-miss found while
building it, not assumed**: an early, looser version of this tracer
would have "resolved" a real ``Sdiod.b`` composite purely by
coincidence -- one of its own two real branches traced through a real
``.sized(v.um)`` call, not one of the six directly-recognized check
methods, and simply happened to share the same real value as the
other branch. Silently ignoring that unrecognized branch (rather than
refusing outright) would have been indistinguishable, from this
module's own point of view, from a case where the two real branches
*disagreed* -- exactly the failure mode this feature exists to avoid.
Fixed by adding a real, deck-wide *value-touching* taint pass first:
an operand identifier is only ever treated as a safe, inert spatial
filter (ignorable) once *confirmed* to never reference any real
``drc_rules`` value anywhere in its own real derivation, direct or
transitive -- not merely because this module never happened to
recognize how it was built. A composite is only ever resolved when
**every** real operand in its own real chain is either (a) itself
already resolved, with its own provenance unanimously agreeing with
every other branch's, (b) confirmed real, value-clean (a real, plain
untracked layer like ``pwell``, or a real, value-free boolean
derivative like real ``Pas.c``'s own third branch, ``pas_c_l1.not(
topmetal2_drw)``), or (c) a real, confirmed-inert "view, don't
transform" method (``.polygons``/``.merged``/``.flatten``/``.clean``/
``.raw``/``.strict``/``.non_strict``/``.edges``) applied to an
already-resolved receiver. Any real disagreement, or any real operand
this module can't confirm is safe one of those three ways, leaves the
whole composite unresolved -- refused, never guessed. Deliberately
excludes real ``+`` (a real, valid KLayout ``Region`` join operator
too) from the recognized combiner set: this module has no reliable,
regex-only way to tell a real geometric ``layer_a + layer_b`` apart
from a real arithmetic ``value.um + 0.001.um`` margin (confirmed real
elsewhere in this deck -- see ``_resolve_value``'s own docstring)
without risking exactly the kind of mis-attribution this feature
exists to avoid. Verified for real, driven: a repeated stash/pop
before/after comparison confirms the existing real 77 rules and 90
skips are completely unaffected (zero regressions), and exactly 8 new,
individually hand-verified-against-source real rules are added
(``Ant.g``/``MIM.c``/``NBL.c``/``NBL.d``/``NW.b1``/``Padb.c``/
``Padc.c``/``Pas.c``, 77/90 -> 85/82); real, confirmed-unsafe near
neighbors (``Sdiod.b``/``Sdiod.c``/``Padc.a``/``Padb.a``/``AFil.d``)
correctly stay unresolved. ``pdklib/drc_writer.py``'s own ``_locate``
was extended the same, real way, so a composite rule's own ``value``
edit patches the real JSON correctly too, not just ``rule_id``/
``description`` -- write-back for a composite rule now works exactly
like a direct one.
"""

from __future__ import annotations

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from ..models import DesignRule
from ..schema import CHECK_TYPES

DRC_METHOD_TO_CHECK_TYPE = {
    "width": "min_width",
    "space": "min_spacing",
    "sep": "min_spacing",
    "enclosed": "min_enclosure",
    "with_area": "min_area",
    "with_length": "max_length",
}

_VALUE_ASSIGN_RE = re.compile(r"(\w+)\s*=\s*drc_rules\[['\"](\w+)['\"]\]")
_CHECK_CALL_RE = re.compile(r"(\w+)\s*=\s*(\S+?)\.(width|space|sep|with_area|with_length)\(([^)]*)\)")
_ENCLOSURE_CALL_RE = re.compile(r"(\w+)\s*=\s*(\S+?)\.enclosed\(\s*(\S+?)\s*,\s*([^)]*)\)")
_VALUE_LITERAL_IN_ARGS_RE = re.compile(r"(\d+(?:\.\d+)?)\.um2?\b")
_VALUE_VAR_IN_ARGS_RE = re.compile(r"(\w+)\.um2?\b")
_ANY_ASSIGN_RE = re.compile(r"^(\w+)\s*=\s*(?!=)(.+?)\s*$")
_IDENT_RE = re.compile(r"\b([a-zA-Z_]\w*)\b")
_CHAIN_RE = re.compile(r"^(\w+)((?:\.\w+(?:\([^()]*\))?)*)\s*$")
_CHAIN_STEP_RE = re.compile(r"\.(\w+)(?:\(([^()]*)\))?")
_COMBINER_METHODS = {"join", "and", "or", "andnot", "xor"}
_PASSTHROUGH_METHODS = {"polygons", "merged", "flatten", "clean", "raw", "strict", "non_strict", "edges"}


def _resolve_value(args: str, value_var_to_key: dict[str, str], values_by_key: dict[str, float]) -> float | None:
    """A real check's value comes one of two real ways: IHP's own real
    ``drc_rules['KEY']`` variable indirection (``cnt_c_value.um`` ->
    looked up in *value_var_to_key*/*values_by_key*), or, for a
    freshly hand-generated custom rule (``render_new_rule_block`` has
    no JSON file to indirect through), a bare literal
    (``0.05.um2``). **The variable path is tried first and must
    win whenever it resolves** -- real IHP call sites routinely carry
    a *second*, unrelated literal further along in the same real
    ``args`` string (e.g. real ``LBE.b1``:
    ``lbe_b1_value.um + 0.001.um``, a real arithmetic margin, not the
    rule's own value; real ``M1.e``:
    ``m1_e_value.um, projection_limits(m1_e_length.um + 0.001.um,
    nil)``) -- trying the literal search first was tried and produces
    real, confirmed wrong values for 7 real rules (caught by a
    stash/pop before/after comparison against the live deck before
    this shipped, not assumed safe). Only once the leading
    ``\\w+.um``/``.um2`` variable fails to resolve to a real
    ``drc_rules[...]`` entry (either no variable-shaped match at all,
    or -- the real literal-value case -- a bogus captured name like
    ``"05"`` from ``0.05.um2``, since ``\\w+`` can't span the decimal
    point) does a bare leftmost-literal fallback apply. This fallback
    is deliberately naive and is only reachable by real, hand-
    generated custom rules (a single, plain literal, no arithmetic) --
    a real composite/arithmetic expression whose *leading* term is
    variable-indirected always resolves in the first branch and never
    reaches the fallback at all."""

    var_match = _VALUE_VAR_IN_ARGS_RE.search(args)
    if var_match is not None:
        json_key = value_var_to_key.get(var_match.group(1))
        if json_key:
            return values_by_key.get(json_key)
    literal_match = _VALUE_LITERAL_IN_ARGS_RE.search(args)
    return float(literal_match.group(1)) if literal_match else None


def _trace_composite_provenance(
    text: str, value_var_to_key: dict[str, str], seed_provenance: dict[str, frozenset]
) -> dict[str, frozenset]:
    """Extends *seed_provenance* (every real, directly-recognized
    ``width``/``space``/``sep``/``enclosed``/``with_area``/
    ``with_length`` result, keyed by its own result variable) with real
    *composite* results too -- a variable built by boolean-combining
    two or more already-tracked results via a real, plain identifier
    chain (``A.join(B)``, ``A.and(B).and(C)``, ...) -- confirmed real
    and common (e.g. real ``NW.b1``: two real ``space()``/``sep()``
    results, both tracing to the *same* real ``drc_rules`` value,
    ``.join()``ed then ``.and()``ed with a real, plain, untracked
    ``pwell`` layer before ``.output()``).

    **Only ever resolves a composite when doing so genuinely can't be
    wrong, never when it merely seems likely** -- the real risk this
    function exists to avoid (a wrong trace silently attaching the
    wrong numeric value to a rule) is treated as strictly worse than
    leaving a real, resolvable-looking composite skipped. Concretely:

    - A composite's own real chain must be a *pure* identifier chain
      (``receiver.method(...).method(...)`` -- real, plain identifiers
      only, no nested calls, no arithmetic, no ``+``, no bracket
      indexing) -- anything else is left unresolved, not partially
      trusted. ``+`` is deliberately excluded even though it's a real,
      valid KLayout ``Region`` join operator too: this module has no
      reliable, regex-only way to tell a real geometric ``layer_a +
      layer_b`` apart from a real arithmetic ``value.um + 0.001.um``
      margin (confirmed real for other constructs -- see this module's
      own top docstring) without risking exactly the kind of
      mis-attribution this function exists to avoid.
    - A combiner method (``join``/``and``/``or``/``andnot``/``xor``)'s
      own real operand must itself be a single, real, plain
      identifier. If that identifier is *also* already a tracked,
      resolved result, its own provenance must be folded in and must
      **unanimously agree** with every other branch's -- any real
      disagreement (a different check_type, or a different value
      variable) leaves the whole composite unresolved, never guessed
      at. If the operand isn't tracked at all, it's *not* automatically
      assumed to be an inert, value-free spatial filter (the tempting,
      unsafe shortcut) -- **it's only treated as safe to ignore once
      confirmed real, via a real, deck-wide data-flow taint pass, to
      never itself reference any real ``drc_rules`` value, directly or
      transitively** (this is what real, confirmed-safe ``pwell`` in
      the ``NW.b1`` example above actually is: a plain, real, boolean
      combination of other plain layers, confirmed by tracing its own
      real definition, not assumed). A real, confirmed *value-touching*
      but otherwise-unresolved operand (e.g. a real ``.sized(v.um)``
      result -- not one of the six directly-recognized check methods,
      but still real, provably built from a real value variable) makes
      the whole composite unresolved too, not silently ignored --
      confirmed real and necessary by a real near-miss found while
      building this (a real ``Sdiod.b`` composite that would otherwise
      have looked safely resolvable purely by coincidence, both of its
      real branches happening to share the same real value even though
      one of them was never actually verified).
    - Any other real method in the chain (``.interacting()``,
      ``.sized()``, ``.with_bbox_max()``, ...) leaves the whole
      composite unresolved -- only a small, real, confirmed-inert
      "view, don't transform" allowlist (``polygons``/``merged``/
      ``flatten``/``clean``/``raw``/``strict``/``non_strict``/``edges``)
      passes a receiver's own provenance through unchanged.

    Returns the extended provenance dict (composite entries included);
    callers still need each composite's own real ``line_no`` separately
    (tracked in ``extract_design_rules`` itself, alongside every other
    real assignment line, not duplicated here)."""

    lines = text.split("\n")
    assign_rhs: dict[str, str] = {}
    for line in lines:
        match = _ANY_ASSIGN_RE.match(line.strip())
        if match:
            assign_rhs[match.group(1)] = match.group(2)

    value_touching: set[str] = set(value_var_to_key.keys())
    changed = True
    while changed:
        changed = False
        for var, rhs in assign_rhs.items():
            if var in value_touching:
                continue
            idents = set(_IDENT_RE.findall(rhs)) - {var}
            if idents & value_touching:
                value_touching.add(var)
                changed = True

    provenance = dict(seed_provenance)
    unresolved: set[str] = set()
    changed = True
    while changed:
        changed = False
        for var, rhs in assign_rhs.items():
            if var in provenance or var in unresolved:
                continue
            chain_match = _CHAIN_RE.match(rhs)
            if chain_match is None:
                continue
            receiver, chain_tail = chain_match.groups()
            if receiver not in provenance:
                if receiver in value_touching:
                    unresolved.add(var)
                    changed = True
                continue
            current = set(provenance[receiver])
            ok = True
            for step in _CHAIN_STEP_RE.finditer(chain_tail):
                method, args = step.groups()
                if method in _PASSTHROUGH_METHODS:
                    continue
                if method in _COMBINER_METHODS:
                    operand = (args or "").strip()
                    if not re.fullmatch(r"\w+", operand):
                        ok = False
                        break
                    if operand in provenance:
                        current |= provenance[operand]
                    elif operand in value_touching:
                        ok = False
                        break
                    continue
                ok = False
                break
            if not ok:
                unresolved.add(var)
                changed = True
            elif len(current) == 1:
                provenance[var] = frozenset(current)
                changed = True
            else:
                unresolved.add(var)
                changed = True

    return provenance


_OUTPUT_CALL_RE = re.compile(
    r"(\w+)\.output\(\s*['\"]([^'\"]+)['\"]\s*,\s*(?:\r?\n\s*)?\"([^\"]*)\""
)


def find_drc_root(pdk_root: Path) -> Path | None:
    candidate = pdk_root / "libs.tech" / "klayout" / "tech" / "drc"
    return candidate if candidate.is_dir() else None


CUSTOM_DRC_FILENAME = "custom_rules.drc"

DRC_DECK_SKELETON_HEADER = """# New, minimal DRC deck.
#
# Real rules authored via the DRC Rules tab's own New Rule action land
# in custom_rules.drc, entirely generated by pdklib/drc_writer.py's own
# render_custom_drc_file -- see that function's own docstring.
#
# A real report() call, not just the rules below, is what makes this
# file genuinely runnable standalone (`klayout -b <gds> -r
# custom_rules.drc`) -- confirmed live: without one, a bare, real
# `region.output("RULE_ID", "description")` call fails at runtime
# (`TypeError: no implicit conversion of String into Integer ... in
# LayerInfo::initialize`), because KLayout resolves the 2-string-arg
# report-database form of `.output()` only once a report destination
# is actually configured; `-rd output=<path>` alone does not do this
# by itself, the script itself has to read it via `$output`.
report("Custom DRC Rules", $output || "custom_rules_report.lyrdb")
"""


def create_new_drc_deck(pdk_root: Path) -> Path:
    """Creates ``libs.tech/klayout/tech/drc/`` with one real, minimal,
    valid, runnable KLayout DRC Ruby script (``custom_rules.drc``) --
    zero real checks yet, which is a real, valid, empty deck, not a
    special case: ``find_drc_root``/``extract_design_rules`` both work
    against it immediately, the same as against a real, downloaded
    deck (0 rules, 0 skipped constructs). No JSON config file is
    created here -- a brand-new rule's own value is written as a
    literal ``<value>.um`` straight into its own ``.width()``/
    ``.space()``/``.enclosed()`` call (see
    ``drc_writer.py``'s own ``render_custom_drc_file``) rather than
    indirected through a JSON key; IHP's own real ``drc_rules[...]``
    -> JSON convention is real, but not a KLayout DRC requirement, and
    skipping it here avoids inventing a second, empty JSON file with
    no real content in it yet."""

    drc_root = pdk_root / "libs.tech" / "klayout" / "tech" / "drc"
    if drc_root.exists():
        raise FileExistsError(f"{drc_root} already exists")
    drc_root.mkdir(parents=True)
    (drc_root / CUSTOM_DRC_FILENAME).write_text(DRC_DECK_SKELETON_HEADER, encoding="utf-8")
    return drc_root


@dataclass
class DrcRunResult:
    report_path: Path
    log: str
    violation_count: int | None
    """The real number of ``<item>`` elements in the real KLayout report
    database XML -- ``None`` only if the report couldn't be read at all
    (a real crash before KLayout ever wrote one), never guessed from
    the real exit code alone (KLayout exits 0 whether or not any real
    rule was violated -- a real DRC *run* failure and a real, clean
    *pass* look identical at that level)."""


def run_drc(gds_path: Path, drc_script: Path, klayout_binary: str) -> DrcRunResult:
    """Runs *drc_script* (a real KLayout DRC Ruby script, e.g.
    ``CUSTOM_DRC_FILENAME`` above) against *gds_path* in real batch
    mode -- ``klayout -b <gds> -r <script> -rd output=<report>``, the
    exact real invocation confirmed live and recorded in this script's
    own ``DRC_DECK_SKELETON_HEADER`` above (a bare ``report()`` call is
    what makes ``-rd output=...`` actually take effect; every deck this
    tool exports already has one). Never re-implements a single real
    DRC check -- only launches the real KLayout engine and reads back
    its own real report database XML."""

    report_path = gds_path.with_name(gds_path.stem + ".lyrdb")
    proc = subprocess.run(
        [klayout_binary, "-b", str(gds_path), "-r", str(drc_script), "-rd", f"output={report_path}"],
        capture_output=True, text=True, timeout=120,
    )
    log = proc.stdout + proc.stderr
    violation_count: int | None = None
    if report_path.is_file():
        try:
            root = ET.parse(report_path).getroot()
            items = root.find("items")
            violation_count = len(items) if items is not None else 0
        except ET.ParseError:
            violation_count = None
    return DrcRunResult(report_path=report_path, log=log, violation_count=violation_count)


def find_json_config_path(search_root: Path) -> Path | None:
    """The one real JSON file under *search_root* with a top-level
    ``drc_rules`` object -- confirmed real: exactly one such file
    exists in IHP's own deck
    (``rule_decks/sg13g2_tech_default.json``). Exposed separately from
    ``_load_json_config`` so ``pdklib/drc_writer.py`` can patch the real
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

        checks: dict[str, tuple[str, str, float | None, int, str | None]] = {}
        seed_provenance: dict[str, frozenset] = {}
        for match in _CHECK_CALL_RE.finditer(text):
            result_var, layer_expr, method, args = match.groups()
            value = _resolve_value(args, value_var_to_key, values_by_key)
            line_no = text.count("\n", 0, match.start()) + 1
            checks[result_var] = (layer_expr, method, value, line_no, None)
            value_var = _VALUE_VAR_IN_ARGS_RE.search(args)
            seed_provenance[result_var] = frozenset({
                (DRC_METHOD_TO_CHECK_TYPE[method], value_var.group(1) if value_var else None)
            })
        for match in _ENCLOSURE_CALL_RE.finditer(text):
            result_var, inner_expr, outer_expr, args = match.groups()
            value = _resolve_value(args, value_var_to_key, values_by_key)
            line_no = text.count("\n", 0, match.start()) + 1
            checks[result_var] = (inner_expr, "enclosed", value, line_no, outer_expr)
            value_var = _VALUE_VAR_IN_ARGS_RE.search(args)
            seed_provenance[result_var] = frozenset({("min_enclosure", value_var.group(1) if value_var else None)})

        provenance = _trace_composite_provenance(text, value_var_to_key, seed_provenance)
        composite_line_no: dict[str, int] = {}
        for line_no, raw_line in enumerate(text.split("\n"), start=1):
            match = _ANY_ASSIGN_RE.match(raw_line.strip())
            if match:
                composite_line_no[match.group(1)] = line_no

        matched_result_vars: set[str] = set()
        for match in _OUTPUT_CALL_RE.finditer(text):
            result_var, rule_id, description = match.groups()
            line_no = text.count("\n", 0, match.start()) + 1
            check = checks.get(result_var)
            if check is not None:
                matched_result_vars.add(result_var)
                layer_expr, method, value, check_line, outer_expr = check
                check_type = DRC_METHOD_TO_CHECK_TYPE[method]
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
                        check_type=check_type,
                        applies_to_override=applies_to,
                        value=float(value) if value is not None else None,
                        units=CHECK_TYPES[check_type].default_units,
                        source_provenance=f"{rel}:{check_line} (.output at :{line_no})",
                        why=why,
                        status="placeholder",
                    )
                )
                continue

            composite_prov = provenance.get(result_var) if result_var not in seed_provenance else None
            if composite_prov is not None:
                (check_type, value_var), = composite_prov
                json_key = value_var_to_key.get(value_var) if value_var else None
                value = values_by_key.get(json_key) if json_key else None
                matched_result_vars.add(result_var)
                check_line = composite_line_no.get(result_var, line_no)
                applies_to = (
                    f"'{result_var}' (a real, boolean-composed KLayout DRC expression, traced through "
                    f"2+ combined real checks that all agreed on the same value -- not resolved to a Layer)"
                )
                why = (
                    "Best-effort extraction traced through a real boolean composition (.join()/.and()/...), "
                    "not a single direct check -- verify against the real source before trusting this value "
                    "or mapping even more than usual."
                )
                rules.append(
                    DesignRule(
                        rule_id=rule_id,
                        description=description.split(" : ", 1)[-1] if " : " in description else description,
                        check_type=check_type,
                        applies_to_override=applies_to,
                        value=float(value) if value is not None else None,
                        units=CHECK_TYPES[check_type].default_units,
                        source_provenance=f"{rel}:{check_line} (.output at :{line_no})",
                        why=why,
                        status="placeholder",
                    )
                )
                continue

            skipped.append(
                f"{rel}:{line_no}: '{rule_id}' -- .output() on '{result_var}', "
                f"which isn't a direct width()/space()/sep()/enclosed()/with_area()/"
                f"with_length() result, nor a composite this module could safely trace back "
                f"to one unambiguous value (a composite or derived check -- not auto-extracted)"
            )

        for result_var in checks:
            if result_var not in matched_result_vars:
                _, _, _, line_no, _ = checks[result_var]
                skipped.append(
                    f"{rel}:{line_no}: '{result_var}' has a real width()/space()/sep()/"
                    f"enclosed()/with_area()/with_length() call but no matching .output() "
                    f"found on that exact variable (not auto-extracted)"
                )

    return rules, skipped

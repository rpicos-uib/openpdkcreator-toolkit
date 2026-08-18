"""Real Magic ``.tech`` technology-file parsing.

Magic's tech-file format has ~15 distinct sections (``tech``,
``version``, ``planes``, ``types``, ``contact``, ``aliases``,
``styles``, ``compose``, ``connect``, ``cifoutput``, ``cifinput``,
``drc``, ``extract``, ``lef``, ``mzrouter``, ``wiring``, ``router``,
``plowing``, ``plot``), each simply ``<keyword> ... end`` -- confirmed
by hand-reading IHP's own real, downloaded
``libs.tech/magic/ihp-sg13g2.tech`` (761 lines) and the four files it
``include``s (``ihp-sg13g2-{cifout,cifin,drc,extract}.tech``, spliced
in textually at the ``include`` line -- confirmed real: those four are
*fragments* of one logical technology, not standalone ones; only
``ihp-sg13g2-GDS.tech`` is a genuinely separate, second technology,
confirmed by its own distinct ``tech``/``version`` header).

Scoped like ``import_open_pdks.py``'s own DRC-rule extraction: parse
what's reliably tabular and structured in full (``tech``, ``version``,
``planes``, ``types``, ``contact``, ``aliases``, ``styles``,
``compose``, ``connect``), and pull one real, valuable pattern out of
each harder, mini-rule-language section rather than a full interpreter:

- ``cifoutput``: real "recipes" ending in a ``calma <layer> <datatype>``
  statement -- the Magic-type-name to real-GDS-layer/datatype mapping,
  cross-referenceable against ``pdklib/layers.py``'s own KLayout ``.lyp``
  layer list (``pdklib/reconcile.py``).
- ``drc``: the three dominant, cleanly tabular real statement kinds --
  ``width <layers> <value> "message"``,
  ``spacing <layer1> <layer2> <value> ... "message"``, and
  ``maxwidth <layer> <value> <mode> [exceptions] "message"`` (192 of
  the real section's statements combined, confirmed against the real
  file: 65/65 ``width``, 101/102 ``spacing``, and 26/26 ``maxwidth``
  lines match -- the one real ``spacing`` exception is a genuine
  defect in IHP's own file, a message string missing its closing
  quote, confirmed by direct inspection, not a parser bug). All three
  share the exact same real message-quoting shape, so ``maxwidth``
  reuses ``width``'s own regex structure exactly (skip any filler
  tokens -- ``mode``, an optional real exception-list like
  ``glass,pillar,solder`` -- up to the quoted message, same as
  ``width``/``spacing`` already do, rather than asserting what each
  filler token means). ``value`` is raw file units; empirically
  confirmed for ``width``/``spacing`` (cross-referenced against three
  independent, already-extracted real KLayout DRC rules sharing the
  same real rule ID -- Act.a, Gat.a, NW.b) that dividing by 1000 gives
  the real micron value Magic itself reports -- not from Magic's own
  documented unit spec, which this pass had no authoritative local
  source to confirm against, but a real, repeatable, cross-checked
  empirical fact; the same factor is applied to ``maxwidth`` too, on
  the reasonable inference that one real file's one real section
  shares one real internal unit scale, not a fresh independent
  confirmation of that specific check kind.

  A fourth real, cleanly tabular kind is extracted separately, into its
  own ``MagicAngleCheck``, not folded into the above: real
  ``angles <layer> <degrees> "message"`` statements (17/17 real lines
  match, including one real line needing the section's own backslash-
  continuation join). Same real message-quoting shape as
  ``width``/``maxwidth``, so it reuses that same regex structure -- but
  a real angle is a plain degree count (45/90), not a length, so the
  real, empirically-confirmed ``/1000`` micron conversion is
  deliberately *not* applied here; forcing it into ``MagicDrcCheck``'s
  own ``value_um`` field would have been a real, silent unit lie.

  ``surround``/``edge4way``/``variants``/``widespacing``/``cifwidth``/
  ``cifspacing``/``cifmaxwidth``/... remain real, separate future work
  -- their own real shapes are less uniform (variable argument counts,
  nested real layer-boolean expressions like
  ``~(alldiffhv,allpoly,*pdiff,*nsd,*ntap)/a``, or, for ``variants``, a
  real conditional-scoping directive rather than a check at all), so
  extending the ``width``-style pattern to them isn't a safe reuse.
- ``extract``: real per-layer sheet-resistance values
  (``resist <layer-spec> <value>``, milliohms/square per the file's own
  comment -- 30 of 33 real lines; the other 3 are real non-numeric
  config entries, ``blocktypes``/``obstypes``/``comment None``, not a
  parsing gap) and real plane ordering (``planeorder <name> <int>``,
  14/14). Also the real parasitic-capacitance-coefficient lines --
  ``defaultoverlap``/``defaultsideoverlap``/``defaultareacap``/
  ``defaultperimeter``/``defaultsidewall`` (506 real lines combined,
  every real line for a given directive sharing the exact same real
  token count -- confirmed directly, not assumed -- so leading args
  and trailing numeric value(s) split at a fixed, real, per-directive
  position; argument *semantics* deliberately not asserted, same
  "don't guess" discipline ``ComposeStatement`` already uses) -- and
  every real ``device <class> <model> <type> ...`` statement (50 real
  entries, some wrapped across lines with a trailing '\\' and joined
  via ``_join_backslash_continuations`` first, the same helper the
  ``drc`` section's own wrapped statements use; class/model/type kept
  as real, confirmed-positional fields, everything after kept raw).
  ``contact``/``devresist``/``antenna``/``disconnect``/``substrate``
  (41 real lines combined: 24/7/4/4/2) are also extracted, into one
  shared, generic, raw ``ExtractMiscStatement`` rather than five
  near-identical dataclasses -- each real, confirmed uniformly shaped
  (every real line for a given directive shares the exact same real
  token count), but too small and heterogeneous individually to
  justify five separate types.

- ``cifinput``: three real facts pulled out of the section in full.
  Every real ``ignore LAYERNAME`` statement (23 real entries, a
  simple, unambiguous "this GDS/CIF layer is ignored on read" fact),
  and a real, standalone ``calma NAME L D`` table (133 real entries,
  confirmed by reading the real file to sit together in one flat
  block, *not* nested inside any preceding boolean recipe -- unlike
  ``cifoutput``'s own per-recipe ``calma L D`` lines, which omit the
  name and inherit it from the enclosing ``layer``/``templayer``
  block, `cifinput`'s own real ``calma`` lines carry their own name
  token directly, a genuinely different real shape requiring its own
  regex, not a reuse of ``cifoutput``'s). Two of those 133 real
  entries use a literal ``*`` as their datatype (``calma BOUND 189
  *``) -- a real wildcard, confirmed by reading the file, kept as
  ``None`` rather than silently dropped or coerced to a fake integer.
  Third, the section's own real geometry-boolean recipe blocks
  (``layer``/``templayer NAME <base> ...`` followed by real
  ``and``/``and-not``/``or``/``grow``/``shrink``/``labels``/
  ``copyup``/``not-square``/``mask-hints``/... op lines) are also now
  extracted, into ``CifInputRecipe`` -- an honest, complete real
  *record* of each recipe (name, real ``templayer``-vs-``layer``
  distinction, base layer(s), every real op line in real order), not
  a working boolean-geometry interpreter: the ops are recorded, never
  evaluated or composed. **A real structural fact confirmed while
  building this, not assumed**: a real Magic type's own recipe can be
  built across more than one real, textually-separated block sharing
  the same NAME (e.g. real ``nwell`` has two real, separate
  ``layer nwell ...`` blocks with two different real base layers) --
  the same real fact ``cifoutput``'s own ``CifLayer`` already merges
  for its own real DNWELL; matched the same way here (188 real,
  unique recipe names across 211 real block occurrences, every real
  occurrence's own base layer and ops accumulated in real file order,
  none silently overwritten or dropped).

``lef``/``mzrouter``/``wiring``/``router``/``plowing``/``plot`` are
still deliberately NOT parsed this pass. Every section name found
(directly or via include) that this pass doesn't fully parse is
reported in ``MagicTechnology.unparsed_sections``, never silently
dropped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_TABULAR_SECTIONS = ("tech", "version", "planes", "types", "contact", "aliases", "styles")
_ALL_KNOWN_SECTIONS = _TABULAR_SECTIONS + (
    "compose", "connect", "cifoutput", "cifinput", "drc", "extract",
    "lef", "mzrouter", "wiring", "router", "plowing", "plot",
)

_SECTION_START_RE = re.compile(r"^(" + "|".join(_ALL_KNOWN_SECTIONS) + r")\s*$")
_INCLUDE_RE = re.compile(r"^include\s+(\S+)\s*$")
_LAYER_BLOCK_START_RE = re.compile(r"^\s*(?:layer|templayer)\s+(\S+)")
_CALMA_RE = re.compile(r"^\s*calma\s+(\d+)\s+(\d+)")
_CIFINPUT_IGNORE_RE = re.compile(r"^\s*ignore\s+(\S+)")
_CIFINPUT_CALMA_RE = re.compile(r"^\s*calma\s+(\S+)\s+(\d+)\s+(\d+|\*)")
_CIFINPUT_RECIPE_START_RE = re.compile(r"^\s*(layer|templayer)\s+(\S+)\s+(\S+)\s*$")
_COMPOSE_VERBS = ("compose", "decompose", "paint")
_WIDTH_RE = re.compile(r'^width\s+(\S+)\s+(-?\d+)\s+(?:\S+\s+)*"([^"]*)"\s*$')
_SPACING_RE = re.compile(r'^spacing\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(?:\S+\s+)*"([^"]*)"\s*$')
_MAXWIDTH_RE = re.compile(r'^maxwidth\s+(\S+)\s+(-?\d+)\s+(?:\S+\s+)*"([^"]*)"\s*$')
_ANGLES_RE = re.compile(r'^angles\s+(\S+)\s+(\d+)\s+(?:\S+\s+)*"([^"]*)"\s*$')
_TRAILING_PARENS_RE = re.compile(r"\(([^()]+)\)\s*$")
_RESIST_RE = re.compile(r"^resist\s+(\S+)\s+(-?\d+)\s*$")
_PLANEORDER_RE = re.compile(r"^planeorder\s+(\S+)\s+(\d+)\s*$")
_EXTRACT_CAP_DIRECTIVES = {
    # directive -> real, confirmed real leading-arg count (every real
    # line for that directive has the exact same real token count --
    # checked directly, not assumed; anything past the leading args is
    # the line's own trailing numeric value(s)).
    "defaultareacap": 2,
    "defaultperimeter": 2,
    "defaultsidewall": 2,
    "defaultoverlap": 4,
    "defaultsideoverlap": 4,
}
# Magic's own real value -> micron conversion for the drc section's
# width/spacing statements -- empirically confirmed (not from a local
# spec), see this module's own docstring.
_DRC_VALUE_TO_MICRONS = 1000.0


@dataclass
class PlaneEntry:
    name: str
    short_code: str
    line_no: int = 0
    """This plane's own real, 1-indexed source line number, tracked the
    same way ``TypeEntry.line_no`` is (see ``_safe_prefix_line_count``)
    -- ``0`` for a plane added this session, or one whose section this
    parser can't safely map back to real source line numbers. Used by
    ``pdklib/magic_tech_writer.py`` for write-back."""


@dataclass
class TypeEntry:
    plane: str
    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    obsolete: bool = False
    """The leading '-' flag Magic uses for internal/no-longer-directly-
    painted types (e.g. '-active hvnmosesd,...')."""
    line_no: int = 0
    """This type's own real, 1-indexed source line number in
    ``MagicTechnology.source_path`` -- ``0`` for a type created this
    session (New Type, no real source position) *or* one whose real
    ``types`` section this parser can't safely map back to
    ``source_path``'s own line numbers (see
    ``_safe_prefix_line_count``'s own docstring). Used by
    ``pdklib/magic_tech_writer.py`` to patch just this type's own real
    line in place on export."""


@dataclass
class ContactEntry:
    contact_type: str
    layer1: str
    layer2: str
    line_no: int = 0
    """Same real, source-mapped line tracking as ``PlaneEntry.line_no``."""


@dataclass
class AliasEntry:
    name: str
    members_raw: str
    """Real, unresolved member-list text (comma-separated, may contain
    '*name' wildcard-prefixed entries and references to other aliases)
    -- resolving wildcard/alias-of-alias semantics is real, separate
    future work; kept verbatim so nothing is silently lost."""
    line_no: int = 0
    """Same real, source-mapped line tracking as ``PlaneEntry.line_no``."""


@dataclass
class StyleEntry:
    type_name: str
    style_names: list[str] = field(default_factory=list)
    line_no: int = 0
    """Same real, source-mapped line tracking as ``PlaneEntry.line_no``
    (see ``_safe_prefix_line_count``) -- used by ``pdklib/magic_tech_
    writer.py`` to patch this entry's own real line in place."""

    @property
    def style_names_text(self) -> str:
        """A plain, space-joined string view of ``style_names`` -- the
        real GUI form field this dataclass's own list field can't be
        edited through directly (``gui/simple_list_editor.py``'s
        ``SimpleListEditor`` only knows plain string fields via
        ``getattr``/``setattr``, the same reason ``AliasEntry`` keeps
        its own real members as a single raw string rather than a real
        list -- see that dataclass's own docstring). The list itself
        stays the real, structured field every other consumer
        (``pdklib/magic_tech_writer.py``'s own ``_render_style_line``)
        reads and writes."""

        return " ".join(self.style_names)

    @style_names_text.setter
    def style_names_text(self, value: str) -> None:
        self.style_names = value.split()


@dataclass
class CifOutputLayerMapping:
    """One real 'calma LAYER DATATYPE' line inside a real cifoutput
    'layer'/'templayer' NAME ... block -- flattened to one row per
    real GDS layer/datatype pair, not one row per Magic type name: a
    real name can have more than one real block/pair (e.g. DNWELL,
    built across two separate real 'layer DNWELL ...' blocks,
    confirmed real), the same "flat, one real line per entry" shape
    every other editable Magic Tech domain already uses, rather than
    one row per name with an inner, merged list. ``name`` itself
    (declared on the enclosing real ``layer``/``templayer`` line, not
    this line) stays real, display-only context -- never written back
    here.

    **Deliberately editable in place only, no New/Delete** (unlike
    every other editable Magic Tech domain): the real geometry recipe
    (``shrink``/``or``/``bloat-all``/...) leading up to a real
    ``calma`` line is deliberately never modeled anywhere in this
    module (see this module's own docstring) -- a brand-new Magic type
    needs a real geometry recipe before a new ``calma`` line would mean
    anything, which this project has no way to author. Editing an
    *existing* line's own real layer/datatype is still real, useful,
    and safe, though -- exactly what's offered here."""

    name: str
    gds_layer: int
    gds_datatype: int
    line_no: int = 0
    """Same real, source-mapped line tracking as ``PlaneEntry.line_no``
    (see ``_safe_prefix_line_count``)."""

    @property
    def gds_layer_text(self) -> str:
        return str(self.gds_layer)

    @gds_layer_text.setter
    def gds_layer_text(self, value: str) -> None:
        try:
            self.gds_layer = int(value)
        except ValueError:
            pass

    @property
    def gds_datatype_text(self) -> str:
        return str(self.gds_datatype)

    @gds_datatype_text.setter
    def gds_datatype_text(self, value: str) -> None:
        try:
            self.gds_datatype = int(value)
        except ValueError:
            pass


@dataclass
class CifInputIgnoredLayer:
    """One real 'ignore LAYERNAME' statement from the cifinput section
    -- a real Magic-type-name to skip entirely on CIF/GDS read. Flat
    and standalone the same real way ``CifInputLayerHint`` below is
    (confirmed real: never nested inside a 'layer'/'templayer' recipe
    block -- ``_parse_cifinput_recipes``'s own docstring already
    excludes real 'ignore' content from being swept into whichever
    recipe happened to be open)."""

    name: str
    line_no: int = 0
    """Same real, source-mapped line tracking as ``PlaneEntry.line_no``
    (see ``_safe_prefix_line_count``)."""


@dataclass
class CifInputLayerHint:
    """One real 'calma NAME L D' statement from the cifinput section --
    unlike cifoutput's own per-recipe CifLayer, this real statement's
    own NAME token is self-contained, not inherited from an enclosing
    'layer'/'templayer' recipe block (confirmed real: all 133 real
    entries sit together in one flat, standalone table, immediately
    after the last real recipe block, not nested inside any of them).
    A real Magic-type-name to real GDS-layer/datatype hint used for
    CIF/GDS-read layer recognition -- the reverse direction of
    cifoutput's own real mapping."""

    name: str
    gds_layer: int
    gds_datatype: int | None
    """``None`` for a real wildcard datatype (the file's own literal
    ``*``, confirmed real -- e.g. ``calma BOUND 189 *`` -- meaning "any
    datatype", not a parsing gap)."""
    line_no: int = 0
    """Same real, source-mapped line tracking as ``PlaneEntry.line_no``
    (see ``_safe_prefix_line_count``)."""

    @property
    def gds_layer_text(self) -> str:
        """A plain-string view of the real ``gds_layer`` int -- the
        first real ``int``-typed editable field anywhere in this
        module (every other ``SimpleListEditor``-backed domain so far
        is all-string). ``SimpleListEditor`` only ever writes a plain
        string via ``setattr`` -- without this property, editing this
        field even once would silently replace the real int with a
        string. A non-numeric mid-edit value is ignored (keeps the
        last real, valid int) rather than raising out of a Tk trace
        callback."""

        return str(self.gds_layer)

    @gds_layer_text.setter
    def gds_layer_text(self, value: str) -> None:
        try:
            self.gds_layer = int(value)
        except ValueError:
            pass

    @property
    def gds_datatype_text(self) -> str:
        """Same real reasoning as ``gds_layer_text``, plus the real
        wildcard convention: the file's own literal ``*`` round-trips
        through this property as the literal string ``"*"``, matching
        ``gds_datatype``'s own real ``None`` meaning exactly."""

        return "*" if self.gds_datatype is None else str(self.gds_datatype)

    @gds_datatype_text.setter
    def gds_datatype_text(self, value: str) -> None:
        stripped = value.strip()
        if stripped == "*":
            self.gds_datatype = None
            return
        try:
            self.gds_datatype = int(stripped)
        except ValueError:
            pass


@dataclass
class CifInputOp:
    """One real op line inside a real cifinput recipe block (e.g.
    ``and NWELL``, ``grow 1140``, ``not-square``) -- kept fully raw
    (``verb`` + the line's own remaining raw text), same 'don't guess
    semantics' discipline as ``ComposeStatement``. Real verbs are not
    an enumerated, closed set (``and``/``and-not``/``or``/``grow``/
    ``shrink``/``labels``/``copyup``/``not-square``/``mask-hints``/...
    all confirmed real) -- whichever real word starts the real line."""

    verb: str
    args: str


@dataclass
class CifInputRecipe:
    """One real Magic type's worth of ``layer NAME <base>`` /
    ``templayer NAME <base>`` recipe content from the cifinput
    section, plus every real op line following each such block (or the
    section's own real ``ignore``/standalone ``calma`` content,
    explicitly excluded -- see this module's own docstring) -- an
    honest, complete real *record* of what each recipe says, not a
    working boolean-geometry interpreter: the ops are never evaluated
    or composed here.

    **A real Magic type's own recipe can be built across more than one
    real, textually-separated block with the same NAME** (confirmed
    real -- e.g. real ``nwell`` has two real, separate ``layer nwell
    ...`` blocks at different points in the file, each with its own
    real base layer: ``NWELL,WELLPIN`` and, later, ``schottkyarea``) --
    the same real structural fact ``cifoutput``'s own ``CifLayer``
    already merges (its own real DNWELL, built across two real
    ``layer DNWELL ...`` blocks). Matched here the same way:
    ``base_layers``/``ops`` accumulate across every real occurrence, in
    real file order, rather than only the first being kept and later
    real occurrences silently overwriting or duplicating it."""

    name: str
    is_templayer: bool
    """A real ``templayer`` is Magic's own real, intermediate/working
    layer (not directly emitted); a real ``layer`` is a real,
    permanent one -- confirmed real distinction, not asserted
    semantics beyond the keyword itself."""
    base_layers: list[str] = field(default_factory=list)
    """Raw, e.g. "NWELL,WELLPIN" -- one real entry per real block
    occurrence, in real file order, not decomposed further."""
    ops: list[CifInputOp] = field(default_factory=list)
    """Every real op line, concatenated across every real block
    occurrence for this name, in real file order."""


@dataclass
class ComposeStatement:
    """One real 'compose|decompose|paint <arg1> <arg2> <arg3>'
    statement from the compose section. Argument *semantics* (which
    slot means e.g. "result" vs. "under"/"over") are deliberately not
    asserted -- no authoritative real source for Magic's own
    compose-section argument order was available to confirm against
    this pass; kept raw and positional, the same 'don't guess'
    discipline ``AliasEntry.members_raw`` already uses."""

    verb: str
    args: tuple[str, str, str]
    line_no: int = 0
    """Same real, source-mapped line tracking as ``PlaneEntry.line_no``
    (see ``_safe_prefix_line_count``)."""

    @property
    def arg1(self) -> str:
        """A plain-string view of ``args[0]`` -- the real GUI form
        field this dataclass's own fixed 3-tuple can't be edited
        through directly (``gui/simple_list_editor.py``'s
        ``SimpleListEditor`` only knows plain string fields via
        ``getattr``/``setattr``, the same real reason ``StyleEntry``
        exposes its own list field through ``style_names_text``
        instead of editing it directly)."""

        return self.args[0]

    @arg1.setter
    def arg1(self, value: str) -> None:
        self.args = (value, self.args[1], self.args[2])

    @property
    def arg2(self) -> str:
        return self.args[1]

    @arg2.setter
    def arg2(self, value: str) -> None:
        self.args = (self.args[0], value, self.args[2])

    @property
    def arg3(self) -> str:
        return self.args[2]

    @arg3.setter
    def arg3(self, value: str) -> None:
        self.args = (self.args[0], self.args[1], value)


@dataclass
class ConnectRule:
    """One real connectivity-equivalence line from the connect
    section: two real, raw comma-separated Magic type-lists (wildcard
    prefixes kept verbatim, not resolved) that this technology's
    connectivity model treats as electrically connectable."""

    types_a: str
    types_b: str
    line_no: int = 0
    """Same real, source-mapped line tracking as ``PlaneEntry.line_no``
    (see ``_safe_prefix_line_count``)."""


@dataclass
class MagicDrcCheck:
    """One real 'width'/'spacing' statement from the drc section --
    see this module's own docstring for the real, empirically-confirmed
    value -> micron conversion and real match-rate numbers."""

    check_type: str
    """"width" or "spacing"."""
    layer_args: list[list[str]]
    """One raw, comma-split real Magic type-list for "width"; two for
    "spacing" (layer1, layer2)."""
    value_um: float
    message: str
    rule_ids_raw: str | None
    """Raw text of a trailing '(...)' in the message, when present
    (e.g. "NW.b", or a real compound case like "Sal.c + Sal.d") --
    kept as one raw string, not split, since a compound case doesn't
    cleanly separate into independent rule IDs without guessing."""


@dataclass
class MagicAngleCheck:
    """One real 'angles <layer> <degrees> "message"' statement from
    the drc section -- a real permitted-angle constraint. Deliberately
    a separate dataclass from ``MagicDrcCheck``, not folded into its
    own ``value_um`` field: a real angle is a plain degree count
    (45/90), not a length, so the real, empirically-confirmed
    ``/1000`` micron conversion ``width``/``spacing``/``maxwidth`` use
    would be a real, silent unit lie if applied here."""

    layer: str
    degrees: int
    message: str


@dataclass
class ExtractResist:
    """One real per-layer sheet-resistance value from the extract
    section (milliohms/square, per the real file's own comment). Real
    layers can repeat across different real PVT-corner ``variants``
    blocks (confirmed: IHP's own hvndiffres/active appears three times
    with three different real values) -- kept as a flat list, not a
    name-keyed dict, so no real corner value is silently dropped."""

    layer_spec: str
    """Raw, e.g. "(allm1)/metal1" -- not decomposed further."""
    milliohms_per_square: int


@dataclass
class ExtractPlaneOrder:
    """One real 'planeorder <name> <int>' line from the extract
    section -- unlike ``ExtractResist``/``ExtractMiscStatement``'s own
    ``contact`` entries, confirmed real to sit *before* the section's
    first real ``variants (...)`` line (no real repeat-per-corner
    wrinkle here), the same flat, single-occurrence-per-name shape
    ``PlaneEntry`` already has."""

    name: str
    order: int
    line_no: int = 0
    """Same real, source-mapped line tracking as
    ``ExtractMiscStatement.line_no`` (see ``_safe_prefix_line_count``)."""

    @property
    def order_text(self) -> str:
        """A plain-string view of ``order`` -- the real GUI form field
        this dataclass's own ``int`` field can't be edited through
        directly, same real reason ``CifInputLayerHint`` exposes
        ``gds_layer_text`` instead of its own ``int`` field. Invalid
        mid-edit text is simply ignored (keeps the last real, valid
        value), same discipline as that property."""

        return str(self.order)

    @order_text.setter
    def order_text(self, value: str) -> None:
        try:
            self.order = int(value)
        except ValueError:
            pass


@dataclass
class ExtractCapCoefficient:
    """One real 'defaultoverlap'/'defaultsideoverlap'/'defaultareacap'/
    'defaultperimeter'/'defaultsidewall' line from the extract
    section -- a real parasitic-capacitance coefficient. Argument
    *semantics* (which token means e.g. "over" vs "under", or which
    physical quantity a trailing number is) are deliberately not
    asserted -- no authoritative real source was available this pass
    to cross-check against (unlike the ``drc`` section's own
    empirically-confirmed ``/1000`` unit factor) -- kept raw and
    positional, same 'don't guess further' discipline
    ``ComposeStatement``/``AliasEntry`` already use. Every real line
    for a given ``directive`` has the exact same real token count
    (confirmed by direct inspection, not assumed), so ``args``/
    ``values`` split at a fixed, real, per-directive position -- see
    ``_EXTRACT_CAP_DIRECTIVES``."""

    directive: str
    args: tuple[str, ...]
    values: tuple[float, ...]


@dataclass
class ExtractDevice:
    """One real 'device <class> <model> <type> ...' statement from the
    extract section's own real transistor/resistor/capacitor-model
    mini-language. ``devclass``/``model``/``type_name`` are real,
    confirmed-positional fields (always tokens 2/3/4 across all 50 real
    entries); everything after is kept raw and positional (a mix of
    real terminal-layer references and 'key=value' parameter mappings)
    -- same 'don't guess further semantics' discipline as
    ``ExtractCapCoefficient``. Real lines can wrap across multiple
    physical lines with a trailing '\\' -- joined first via
    ``_join_backslash_continuations``, the same helper the ``drc``
    section's own real wrapped statements already use."""

    devclass: str
    model: str
    type_name: str
    rest: tuple[str, ...]


@dataclass
class ExtractMiscStatement:
    """One real 'contact'/'devresist'/'antenna'/'disconnect'/
    'substrate' line from the extract section -- each real, small
    (2-24 real lines) and uniformly shaped enough (every real line for
    a given directive shares the exact same real token count, confirmed
    directly, not assumed) that all five share one generic, raw,
    positional shape rather than five near-identical dataclasses.
    Argument semantics deliberately not asserted, same discipline as
    ``ExtractCapCoefficient``/``ComposeStatement``.

    **A real, confirmed wrinkle shared with ``ExtractResist``, not a
    complication unique to it**: a real ``contact`` line also repeats
    across the extract section's own real ``variants (...)``
    PVT-corner blocks (confirmed real: IHP's own ``contact
    alldiffcont`` appears three times, once per corner, with three
    different real values) -- this domain's own real, flat,
    line-number-keyed write-back (see ``pdklib/magic_tech_writer.py``)
    handles that the same way ``CifOutputLayerMapping``'s own repeated
    ``DNWELL`` rows already do: each real occurrence is its own real,
    independently-editable row, with no attempt made here to resolve or
    label *which* real corner a given row belongs to (that's the same
    real ``variants`` semantic interpretation this project's own DRC-
    deck work has deliberately deferred elsewhere -- see README's own
    Future Work)."""

    directive: str
    args: tuple[str, ...]
    line_no: int = 0
    """Same real, source-mapped line tracking as
    ``ComposeStatement.line_no``/``ConnectRule.line_no`` (see
    ``_safe_prefix_line_count``)."""

    @property
    def args_text(self) -> str:
        """A plain-string view of ``args`` -- the real GUI form field
        this dataclass's own variable-length tuple can't be edited
        through directly, same real reason ``StyleEntry`` exposes
        ``style_names_text`` instead of its own list field."""

        return " ".join(self.args)

    @args_text.setter
    def args_text(self, value: str) -> None:
        self.args = tuple(value.split())


@dataclass
class MagicTechnology:
    source_path: Path
    included_files: list[str] = field(default_factory=list)
    name: str = ""
    format: int | None = None
    version: str = ""
    description: str = ""
    requires: str = ""
    planes: list[PlaneEntry] = field(default_factory=list)
    types: list[TypeEntry] = field(default_factory=list)
    contacts: list[ContactEntry] = field(default_factory=list)
    aliases: list[AliasEntry] = field(default_factory=list)
    styles: list[StyleEntry] = field(default_factory=list)
    cif_layers: list[CifOutputLayerMapping] = field(default_factory=list)
    cifinput_ignored_layers: list[CifInputIgnoredLayer] = field(default_factory=list)
    """Real 'ignore LAYERNAME' statements from the cifinput section."""
    cifinput_layer_hints: list[CifInputLayerHint] = field(default_factory=list)
    """Real, standalone 'calma NAME L D' statements from the cifinput
    section -- see ``CifInputLayerHint``'s own docstring."""
    cifinput_recipes: list[CifInputRecipe] = field(default_factory=list)
    """Real 'layer'/'templayer' geometry-boolean recipe blocks -- see
    ``CifInputRecipe``'s own docstring."""
    compose: list[ComposeStatement] = field(default_factory=list)
    connect: list[ConnectRule] = field(default_factory=list)
    drc_checks: list[MagicDrcCheck] = field(default_factory=list)
    drc_angle_checks: list[MagicAngleCheck] = field(default_factory=list)
    """Real 'angles' statements -- see ``MagicAngleCheck``'s own
    docstring for why these are a separate list, not folded into
    ``drc_checks``."""
    drc_skipped: list[str] = field(default_factory=list)
    """Real 'width'/'spacing'/'maxwidth'/'angles' lines found but not
    matched -- e.g. the one real, confirmed defect in IHP's own file
    (a message string missing its closing quote). Every *other* real
    drc-section construct (surround/edge4way/variants/...) was never
    attempted and isn't listed here -- see this module's own
    docstring."""
    extract_resist: list[ExtractResist] = field(default_factory=list)
    extract_plane_order: list[ExtractPlaneOrder] = field(default_factory=list)
    extract_cap_coefficients: list[ExtractCapCoefficient] = field(default_factory=list)
    """Real defaultoverlap/defaultsideoverlap/defaultareacap/
    defaultperimeter/defaultsidewall lines -- see
    ``ExtractCapCoefficient``'s own docstring."""
    extract_devices: list[ExtractDevice] = field(default_factory=list)
    """Real 'device ...' statements -- see ``ExtractDevice``'s own
    docstring."""
    extract_misc: list[ExtractMiscStatement] = field(default_factory=list)
    """Real 'contact'/'devresist'/'antenna'/'disconnect'/'substrate'
    statements -- see ``ExtractMiscStatement``'s own docstring."""
    unparsed_sections: list[str] = field(default_factory=list)
    """Real section names found (directly or via include) that this
    pass deliberately does not parse -- see this module's own
    docstring for why."""
    all_parsed_type_line_nos: list[int] = field(default_factory=list)
    """Every real type's own line number as originally parsed, in real
    file order -- unlike ``types``, never mutated by editing (New/
    Delete Type); mirrors ``pdklib/lef.py``'s ``LefMacro.
    all_parsed_pin_ranges``, used by ``pdklib/magic_tech_writer.py`` to
    tell a real deleted type apart from a comment/blank-line gap.
    Excludes any real type line this parser couldn't safely map back
    to ``source_path``'s own line numbers (see
    ``_safe_prefix_line_count``)."""
    types_section_start_line: int = 0
    """The real, 1-indexed line number of the ``types`` keyword
    itself, in ``source_path`` -- ``0`` if the real ``types`` section
    wasn't found at a safely-mappable position (see
    ``_safe_prefix_line_count``'s own docstring); write-back leaves the
    whole file untouched in that case rather than guess."""
    types_section_end_line: int = 0
    """The real, 1-indexed line number of the ``types`` section's own
    closing ``end``, in ``source_path``."""
    all_parsed_plane_line_nos: list[int] = field(default_factory=list)
    planes_section_start_line: int = 0
    planes_section_end_line: int = 0
    all_parsed_contact_line_nos: list[int] = field(default_factory=list)
    contacts_section_start_line: int = 0
    contacts_section_end_line: int = 0
    all_parsed_alias_line_nos: list[int] = field(default_factory=list)
    aliases_section_start_line: int = 0
    aliases_section_end_line: int = 0
    """Planes/Contacts/Aliases each get the exact same real
    line-tracking bookkeeping as ``types`` above (see
    ``all_parsed_type_line_nos``/``types_section_start_line``/
    ``types_section_end_line``'s own docstrings) -- confirmed real,
    not assumed: all three sections sit in ``ihp-sg13g2.tech`` well
    before its first real ``include`` line, the same safely-mappable
    real region ``types`` itself already relies on."""
    all_parsed_style_line_nos: list[int] = field(default_factory=list)
    styles_section_start_line: int = 0
    styles_section_end_line: int = 0
    """Same real bookkeeping, for ``styles`` -- also confirmed to sit
    well before the first real ``include`` line in both real ``.tech``
    files that have one (``ihp-sg13g2.tech`` and ``ihp-sg13g2-GDS.
    tech``, the latter with no real ``include`` line at all). Unlike
    Planes/Contacts/Aliases, a real ``styles`` section also carries one
    real, non-entry ``styletype NAME`` header line right after its own
    opening keyword -- handled for free by ``_scan_single_line_section``
    's own generic "not a real entry, copy verbatim" gap logic (see
    ``_parse_style_line`` below), not a special case."""
    all_parsed_compose_line_nos: list[int] = field(default_factory=list)
    compose_section_start_line: int = 0
    compose_section_end_line: int = 0
    all_parsed_connect_line_nos: list[int] = field(default_factory=list)
    connect_section_start_line: int = 0
    connect_section_end_line: int = 0
    """Same real bookkeeping, for ``compose``/``connect`` -- confirmed
    real, not assumed: both sections (535-591/597-621 in IHP's own real
    ``ihp-sg13g2.tech``) also sit well before its first real ``include``
    line, the same safely-mappable region every other editable domain
    already relies on. Both are flat, one-real-line-per-entry sections
    (``verb arg1 arg2 arg3`` / ``types_a types_b``) -- no special-case
    gap logic needed the way ``styles`` needs for its own header line."""
    all_parsed_cifinput_ignore_line_nos: list[int] = field(default_factory=list)
    all_parsed_cifinput_hint_line_nos: list[int] = field(default_factory=list)
    cifinput_section_start_line: int = 0
    cifinput_section_end_line: int = 0
    """Real bookkeeping for ``cifinput``'s own two flat sub-structures
    (ignored layers, layer hints) -- **a real structural difference
    from every other editable domain above**: ``cifinput`` doesn't live
    in ``ihp-sg13g2.tech`` itself, it's spliced in from a separate real
    file, ``ihp-sg13g2-cifin.tech``, via ``include``. When parsed *as
    part of* ``ihp-sg13g2.tech``'s own combined view, its real lines
    sit well past that file's own ``safe_through`` boundary (the first
    real ``include`` line), so ``line_no``/these section bounds
    correctly come back ``0`` there -- refusing to guess, not a bug --
    and write-back for that parse correctly leaves this domain
    untouched. ``ihp-sg13g2-cifin.tech`` is also independently
    parseable as its own real file, though (``find_tech_files`` globs
    it too, same as every other real ``.tech`` file) -- confirmed to
    have no real ``include`` line of its own, so *that* parse's own
    ``cifinput`` content **is** safely, fully mappable, using the exact
    same machinery. The only real gap this closes is visibility:
    ``ihp-sg13g2-cifin.tech`` has no real ``tech``/``version`` header
    of its own, so it used to be silently filtered out of the
    Technology picker entirely; ``gui/magic_tech_view.py`` now falls
    back to the real file's own stem as a display name so it (and
    every other nameless fragment) shows up and can be selected,
    without inventing a fake real ``tech.name``. Both sub-structures
    share these same section bounds (one real ``cifinput``...``end``
    block, confirmed real: neither is nested inside a ``layer``/
    ``templayer`` recipe block) -- ``pdklib/magic_tech_writer.py``'s
    own ``render_tech_file`` was generalized to combine multiple,
    independently-tracked sub-structures into one real patch pass over
    a shared section, not two separate, mutually-clobbering passes over
    the same real lines."""
    all_parsed_cif_layer_line_nos: list[int] = field(default_factory=list)
    cifoutput_section_start_line: int = 0
    cifoutput_section_end_line: int = 0
    """Same real bookkeeping, for ``cifoutput``'s own flat, editable-
    in-place ``calma`` lines (``CifOutputLayerMapping``) -- structurally
    the same real "spliced in from a separate real file" situation as
    ``cifinput`` above (``ihp-sg13g2-cifout.tech`` this time), same real
    resolution: safely, fully mappable when that real file is parsed
    directly, correctly ``0`` when parsed as part of ``ihp-sg13g2.tech``
    's own combined view."""
    all_parsed_extract_misc_line_nos: list[int] = field(default_factory=list)
    all_parsed_extract_plane_order_line_nos: list[int] = field(default_factory=list)
    extract_section_start_line: int = 0
    extract_section_end_line: int = 0
    """Real bookkeeping for the ``extract`` section's own two flat,
    editable sub-structures, ``ExtractMiscStatement`` (``contact``/
    ``devresist``/``antenna``/``disconnect``/``substrate``) and
    ``ExtractPlaneOrder`` (``planeorder``) -- **structurally the same
    real "spliced in from a separate real file" situation as cifinput/
    cifoutput above**: the real ``extract`` section doesn't live in
    ``ihp-sg13g2.tech`` itself, it's spliced in from
    ``ihp-sg13g2-extract.tech`` via ``include`` (confirmed real: that
    fragment file has no real ``include`` line of its own, so its own
    content is safely, fully mappable when parsed directly -- same
    resolution as cifinput/cifoutput, no new mechanism needed). Both
    sub-structures share these same section bounds (one real
    ``extract``...``end`` block) the same way cifinput's own ignored-
    layers/layer-hints tables already share one section -- see
    ``pdklib/magic_tech_writer.py``'s own docstring for how write-back
    handles a section with more than one independently-tracked group.
    Every other real extract-section construct this parser also
    recognizes (``resist``/the four cap-coefficient directives/
    ``device``) shares this same section but stays read-only -- see
    this module's own docstring for why (real ``variants`` PVT-corner
    scoping for ``resist``, and, for ``device``, real backslash-
    continued lines, make those genuinely less uniform than these two
    domains' own flat, single-line shape; ``planeorder`` itself is
    confirmed real to sit before the section's own first real
    ``variants (...)`` line, so it never has ``resist``'s own real
    per-corner repeat)."""


def find_tech_files(pdk_root: Path) -> list[Path]:
    return sorted((pdk_root / "libs.tech" / "magic").glob("*.tech"))


_TECH_SKELETON_TEMPLATE = """tech
  format 35
  {name}
end

version
 version 0.1.0
 description "New technology -- edit this description"
end

planes
end

types
end

contact
end

aliases
end
"""


def create_new_tech_file(path: Path) -> None:
    """Writes a minimal, valid, real Magic ``.tech`` skeleton: real
    ``tech``/``version`` header sections (so it parses as a real,
    named technology, using *path*'s own stem as the real technology
    name -- ``tech.name`` below) plus real, empty ``planes``/``types``/
    ``contact``/``aliases`` sections. Genuinely usable from here, not
    just a stub: ``_scan_single_line_section`` (below) sets a real
    section's own start/end line correctly even with zero entries
    inside, and ``magic_tech_writer.py``'s own ``_render_section_patch``
    already anchors a brand-new entry just before its own section's
    real closing ``end`` line -- so **New Type**/**New Plane**/
    **New Contact**/**New Alias** in the Magic Tech tab, and a real
    export afterward, work immediately against a file created this
    way, no different from adding an entry to a real, downloaded one.
    No real ``include`` line here at all, so ``_safe_prefix_line_count``
    treats every real line as safely write-back-mappable."""

    if path.exists():
        raise FileExistsError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_TECH_SKELETON_TEMPLATE.format(name=path.stem), encoding="utf-8")


def _load_lines_with_includes(path: Path, included: list[str], _seen: set[Path] | None = None) -> list[str]:
    """Real textual splicing: an 'include NAME' line's content is
    replaced by NAME.tech's own real lines, read from the same
    directory Magic itself resolves against -- so section parsing
    below sees one combined, logically-complete technology, matching
    what Magic itself actually loads."""

    _seen = _seen or set()
    if path in _seen:
        return []
    _seen.add(path)

    lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _INCLUDE_RE.match(raw_line.strip())
        if match:
            include_name = match.group(1)
            included.append(include_name)
            include_path = path.parent / f"{include_name}.tech"
            if include_path.is_file():
                lines.extend(_load_lines_with_includes(include_path, included, _seen))
            else:
                lines.append(f"# [unresolved include: {include_name}.tech not found]")
            continue
        lines.append(raw_line)
    return lines


def _safe_prefix_line_count(path: Path) -> int:
    """How many of *path*'s own real leading lines are guaranteed to
    appear at the exact same real line number in
    ``_load_lines_with_includes``'s combined, spliced view -- every
    line before *path*'s own first real ``include`` statement (all of
    it, if there's none). Confirmed true for IHP's own real
    ``ihp-sg13g2.tech``: its real ``types`` section (and everything
    ``pdklib/magic_tech_writer.py`` needs to write back) sits well before
    its first real ``include`` line. Not assumed true in general --
    write-back for a real ``types`` line past this boundary is
    deliberately refused (``TypeEntry.line_no`` stays ``0``) rather
    than risk patching the wrong real position in the wrong real
    file."""

    text = path.read_text(encoding="utf-8", errors="replace")
    line_no = 0
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        if _INCLUDE_RE.match(raw_line.strip()):
            return line_no - 1
    return line_no


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    """{section_name: [body lines]} -- everything between a bare
    section-keyword line and the next bare 'end' line. A technology
    can (and does, for cifoutput's real recipes) repeat some
    structure across many 'layer NAME ...' sub-blocks inside one
    section; those are handled by the section-specific parser, not
    here."""

    sections: dict[str, list[str]] = {}
    current: str | None = None
    body: list[str] = []
    for line in lines:
        stripped = line.strip()
        if current is None:
            match = _SECTION_START_RE.match(stripped)
            if match:
                current = match.group(1)
                body = []
            continue
        if stripped == "end":
            sections.setdefault(current, []).extend(body)
            current = None
            continue
        body.append(line)
    return sections


def _scan_single_line_section(lines, section_name, safe_through, parse_entry):
    """Shared real line-tracking scan for a section whose every real
    entry sits on exactly one real line (``planes``/``contact``/
    ``aliases`` -- unlike ``types``, whose own real per-line shape is
    distinct enough it keeps its own ``_parse_types_with_lines``).
    Same real approach: scans the full, combined ``lines`` (not a
    pre-sectioned body, unlike ``_split_sections``'s own real body
    lists, which carry no line-number info at all), tracking each real
    entry's own line number only when ``line_no <= safe_through`` (see
    ``_safe_prefix_line_count``). *parse_entry(stripped_line)* returns
    a real entry object (with its own ``line_no`` field, set here) or
    ``None`` to skip a non-entry real line. Returns (entries,
    all_line_nos, section_start_line, section_end_line)."""

    entries = []
    all_line_nos: list[int] = []
    section_start = section_end = 0
    in_section = False

    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not in_section:
            if stripped == section_name:
                in_section = True
                if section_start == 0 and line_no <= safe_through:
                    section_start = line_no
            continue
        if stripped == "end":
            in_section = False
            if section_start and section_end == 0 and line_no <= safe_through:
                section_end = line_no
            continue
        if not stripped or stripped.startswith("#"):
            continue
        entry = parse_entry(stripped)
        if entry is None:
            continue
        safe_line_no = line_no if section_start and line_no <= safe_through else 0
        if safe_line_no:
            all_line_nos.append(safe_line_no)
        entry.line_no = safe_line_no
        entries.append(entry)

    return entries, all_line_nos, section_start, section_end


def _parse_plane_line(stripped: str) -> PlaneEntry | None:
    if "," not in stripped:
        return None
    name, _, short = stripped.partition(",")
    return PlaneEntry(name=name.strip(), short_code=short.strip())


def _parse_planes_with_lines(lines: list[str], safe_through: int):
    return _scan_single_line_section(lines, "planes", safe_through, _parse_plane_line)


def _parse_types_with_lines(
    lines: list[str], safe_through: int,
) -> tuple[list[TypeEntry], list[int], int, int]:
    """Unlike every other ``_parse_*`` function here, this one scans
    the full, combined (include-spliced) ``lines`` list itself, not a
    pre-sectioned body -- it needs each real type's own combined-space
    line number to decide whether write-back can safely map it back to
    *source_path*'s own real line numbers (``line_no <= safe_through``,
    see ``_safe_prefix_line_count``). Returns (entries,
    all_parsed_type_line_nos, section_start_line, section_end_line);
    the last two are ``0`` if no safely-mappable real ``types`` section
    was found at all."""

    entries: list[TypeEntry] = []
    all_line_nos: list[int] = []
    section_start = section_end = 0
    in_types = False

    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not in_types:
            if stripped == "types":
                in_types = True
                if section_start == 0 and line_no <= safe_through:
                    section_start = line_no
            continue
        if stripped == "end":
            in_types = False
            if section_start and section_end == 0 and line_no <= safe_through:
                section_end = line_no
            continue
        if not stripped or stripped.startswith("#"):
            continue
        obsolete = stripped.startswith("-")
        body = stripped[1:] if obsolete else stripped
        parts = body.split(None, 1)
        if len(parts) != 2:
            continue
        plane, names_raw = parts
        names = [n.strip() for n in names_raw.split(",") if n.strip()]
        if not names:
            continue
        safe_line_no = line_no if section_start and line_no <= safe_through else 0
        if safe_line_no:
            all_line_nos.append(safe_line_no)
        entries.append(TypeEntry(
            plane=plane, canonical_name=names[0], aliases=names[1:], obsolete=obsolete,
            line_no=safe_line_no,
        ))

    return entries, all_line_nos, section_start, section_end


def _parse_contact_line(stripped: str) -> ContactEntry | None:
    if stripped == "stackable":
        return None
    parts = stripped.split()
    if len(parts) != 3:
        return None
    return ContactEntry(contact_type=parts[0], layer1=parts[1], layer2=parts[2])


def _parse_contacts_with_lines(lines: list[str], safe_through: int):
    return _scan_single_line_section(lines, "contact", safe_through, _parse_contact_line)


def _parse_alias_line(stripped: str) -> AliasEntry | None:
    parts = stripped.split(None, 1)
    if len(parts) != 2:
        return None
    return AliasEntry(name=parts[0], members_raw=parts[1].strip())


def _parse_aliases_with_lines(lines: list[str], safe_through: int):
    return _scan_single_line_section(lines, "aliases", safe_through, _parse_alias_line)


def _parse_style_line(stripped: str) -> StyleEntry | None:
    if stripped.startswith("styletype"):
        return None  # a real section-level header, not an entry -- left as a verbatim gap.
    parts = stripped.split()
    if len(parts) < 2:
        return None
    return StyleEntry(type_name=parts[0], style_names=parts[1:])


def _parse_styles_with_lines(lines: list[str], safe_through: int):
    return _scan_single_line_section(lines, "styles", safe_through, _parse_style_line)


def _parse_cifoutput_layers_with_lines(lines: list[str], safe_through: int):
    """Every real 'layer NAME ... calma L D' line, one real
    ``CifOutputLayerMapping`` per real ``calma`` line (not merged by
    name -- see that dataclass's own docstring for why). A real block
    starts at a ``layer``/``templayer`` line and runs until the next
    such line (or the section end); every real ``calma`` line found
    inside it is attributed to that block's own real NAME. Mirrors
    ``_scan_single_line_section``'s own real line-tracking/
    ``safe_through`` discipline, but needs its own real scan (not a
    reuse) since a ``calma`` line's own real NAME comes from a
    *different*, preceding real line, not the ``calma`` line itself --
    genuinely stateful in a way no other single-line-section domain
    here needs to be. Returns ``(entries, all_line_nos, section_start,
    section_end)``, the same real shape ``_scan_single_line_section``
    returns."""

    entries: list[CifOutputLayerMapping] = []
    all_line_nos: list[int] = []
    section_start = section_end = 0
    in_section = False
    current_name: str | None = None

    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not in_section:
            if stripped == "cifoutput":
                in_section = True
                if section_start == 0 and line_no <= safe_through:
                    section_start = line_no
            continue
        if stripped == "end":
            in_section = False
            if section_start and section_end == 0 and line_no <= safe_through:
                section_end = line_no
            continue
        if not stripped or stripped.startswith("#"):
            continue
        start_match = _LAYER_BLOCK_START_RE.match(stripped)
        if start_match:
            current_name = start_match.group(1)
            continue
        if current_name is None:
            continue
        calma_match = _CALMA_RE.match(stripped)
        if calma_match is None:
            continue
        safe_line_no = line_no if section_start and line_no <= safe_through else 0
        if safe_line_no:
            all_line_nos.append(safe_line_no)
        entries.append(
            CifOutputLayerMapping(
                name=current_name, gds_layer=int(calma_match.group(1)), gds_datatype=int(calma_match.group(2)),
                line_no=safe_line_no,
            )
        )

    return entries, all_line_nos, section_start, section_end


def _parse_cifinput_ignore_line(stripped: str) -> CifInputIgnoredLayer | None:
    match = _CIFINPUT_IGNORE_RE.match(stripped)
    if not match:
        return None
    return CifInputIgnoredLayer(name=match.group(1))


def _parse_cifinput_ignored_layers_with_lines(lines: list[str], safe_through: int):
    return _scan_single_line_section(lines, "cifinput", safe_through, _parse_cifinput_ignore_line)


def _parse_cifinput_hint_line(stripped: str) -> CifInputLayerHint | None:
    match = _CIFINPUT_CALMA_RE.match(stripped)
    if not match:
        return None
    datatype_raw = match.group(3)
    return CifInputLayerHint(
        name=match.group(1), gds_layer=int(match.group(2)),
        gds_datatype=None if datatype_raw == "*" else int(datatype_raw),
    )


def _parse_cifinput_hints_with_lines(lines: list[str], safe_through: int):
    return _scan_single_line_section(lines, "cifinput", safe_through, _parse_cifinput_hint_line)


def _parse_cifinput_recipes(lines: list[str]) -> list[CifInputRecipe]:
    by_name: dict[str, CifInputRecipe] = {}
    order: list[str] = []
    current: CifInputRecipe | None = None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        block_match = _CIFINPUT_RECIPE_START_RE.match(line)
        if block_match:
            kind, name, base = block_match.groups()
            current = by_name.get(name)
            if current is None:
                current = CifInputRecipe(name=name, is_templayer=(kind == "templayer"))
                by_name[name] = current
                order.append(name)
            current.base_layers.append(base)
            continue
        if current is None:
            continue
        # The section's own real 'ignore'/standalone 'calma' content
        # is not part of any recipe (see this module's own docstring)
        # -- explicitly excluded rather than swept in as bogus 'ops'
        # of whichever recipe happened to be open last.
        if _CIFINPUT_IGNORE_RE.match(stripped) or _CIFINPUT_CALMA_RE.match(stripped):
            continue
        parts = stripped.split(None, 1)
        current.ops.append(CifInputOp(verb=parts[0], args=parts[1] if len(parts) > 1 else ""))
    return [by_name[name] for name in order]


def _parse_compose_line(stripped: str) -> ComposeStatement | None:
    parts = stripped.split()
    if len(parts) != 4 or parts[0] not in _COMPOSE_VERBS:
        return None
    return ComposeStatement(verb=parts[0], args=(parts[1], parts[2], parts[3]))


def _parse_compose_with_lines(lines: list[str], safe_through: int):
    return _scan_single_line_section(lines, "compose", safe_through, _parse_compose_line)


def _parse_connect_line(stripped: str) -> ConnectRule | None:
    parts = stripped.split()
    if len(parts) != 2:
        return None
    return ConnectRule(types_a=parts[0], types_b=parts[1])


def _parse_connect_with_lines(lines: list[str], safe_through: int):
    return _scan_single_line_section(lines, "connect", safe_through, _parse_connect_line)


def _join_backslash_continuations(lines: list[str]) -> list[str]:
    """Magic's real drc/extract sections wrap long statements across
    lines with a trailing '\\' -- collapse those before line-by-line
    parsing so a wrapped statement isn't silently mis-tokenized as two
    separate, incomplete lines."""

    joined: list[str] = []
    pending = ""
    for line in lines:
        if pending:
            line = pending + " " + line.strip()
            pending = ""
        if line.rstrip().endswith("\\"):
            pending = line.rstrip()[:-1].rstrip()
            continue
        joined.append(line)
    return joined


def _parse_drc_checks(lines: list[str]) -> tuple[list[MagicDrcCheck], list[MagicAngleCheck], list[str]]:
    checks: list[MagicDrcCheck] = []
    angle_checks: list[MagicAngleCheck] = []
    skipped: list[str] = []
    for line in _join_backslash_continuations(lines):
        stripped = line.strip()
        if stripped.startswith("width "):
            match = _WIDTH_RE.match(stripped)
            if match is None:
                skipped.append(stripped)
                continue
            layers_raw, value, message = match.groups()
            id_match = _TRAILING_PARENS_RE.search(message)
            checks.append(MagicDrcCheck(
                check_type="width", layer_args=[layers_raw.split(",")],
                value_um=int(value) / _DRC_VALUE_TO_MICRONS, message=message,
                rule_ids_raw=id_match.group(1) if id_match else None,
            ))
        elif stripped.startswith("spacing "):
            match = _SPACING_RE.match(stripped)
            if match is None:
                skipped.append(stripped)
                continue
            layer1, layer2, value, message = match.groups()
            id_match = _TRAILING_PARENS_RE.search(message)
            checks.append(MagicDrcCheck(
                check_type="spacing", layer_args=[layer1.split(","), layer2.split(",")],
                value_um=int(value) / _DRC_VALUE_TO_MICRONS, message=message,
                rule_ids_raw=id_match.group(1) if id_match else None,
            ))
        elif stripped.startswith("maxwidth "):
            match = _MAXWIDTH_RE.match(stripped)
            if match is None:
                skipped.append(stripped)
                continue
            layers_raw, value, message = match.groups()
            id_match = _TRAILING_PARENS_RE.search(message)
            checks.append(MagicDrcCheck(
                check_type="maxwidth", layer_args=[layers_raw.split(",")],
                value_um=int(value) / _DRC_VALUE_TO_MICRONS, message=message,
                rule_ids_raw=id_match.group(1) if id_match else None,
            ))
        elif stripped.startswith("angles "):
            match = _ANGLES_RE.match(stripped)
            if match is None:
                skipped.append(stripped)
                continue
            layer, degrees, message = match.groups()
            angle_checks.append(MagicAngleCheck(layer=layer, degrees=int(degrees), message=message))
    return checks, angle_checks, skipped


def _parse_extract_resist(lines: list[str]) -> list[ExtractResist]:
    entries = []
    for line in lines:
        match = _RESIST_RE.match(line.strip())
        if match is None:
            continue
        entries.append(ExtractResist(layer_spec=match.group(1), milliohms_per_square=int(match.group(2))))
    return entries


def _parse_plane_order_line(stripped: str) -> ExtractPlaneOrder | None:
    match = _PLANEORDER_RE.match(stripped)
    if match is None:
        return None
    return ExtractPlaneOrder(name=match.group(1), order=int(match.group(2)))


def _parse_extract_plane_order_with_lines(lines: list[str], safe_through: int):
    """Same real ``_scan_single_line_section`` machinery
    ``_parse_extract_misc_with_lines`` uses on this same shared
    ``extract`` section -- every real line that isn't a ``planeorder``
    statement (``resist``/cap-coefficient/``device``/``contact``/...
    lines, ``variants`` lines, comments) simply doesn't match
    ``_parse_plane_order_line`` and falls through as an untracked,
    verbatim gap at write-back time."""

    return _scan_single_line_section(lines, "extract", safe_through, _parse_plane_order_line)


def _parse_extract_cap_coefficients(lines: list[str]) -> list[ExtractCapCoefficient]:
    entries = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        arg_count = _EXTRACT_CAP_DIRECTIVES.get(parts[0])
        if arg_count is None or len(parts) <= arg_count:
            continue
        args = tuple(parts[1 : 1 + arg_count])
        value_tokens = parts[1 + arg_count :]
        try:
            values = tuple(float(token) for token in value_tokens)
        except ValueError:
            continue
        entries.append(ExtractCapCoefficient(directive=parts[0], args=args, values=values))
    return entries


def _parse_extract_devices(lines: list[str]) -> list[ExtractDevice]:
    entries = []
    for line in _join_backslash_continuations(lines):
        stripped = line.strip()
        if not stripped.startswith("device "):
            continue
        parts = stripped.split()
        if len(parts) < 4:
            continue
        entries.append(
            ExtractDevice(devclass=parts[1], model=parts[2], type_name=parts[3], rest=tuple(parts[4:]))
        )
    return entries


_EXTRACT_MISC_KEYWORDS = ("contact", "devresist", "antenna", "disconnect", "substrate")


def _parse_extract_misc_line(stripped: str) -> ExtractMiscStatement | None:
    parts = stripped.split()
    if not parts or parts[0] not in _EXTRACT_MISC_KEYWORDS:
        return None
    return ExtractMiscStatement(directive=parts[0], args=tuple(parts[1:]))


def _parse_extract_misc_with_lines(lines: list[str], safe_through: int):
    """Same real ``_scan_single_line_section`` machinery every other
    flat, editable domain uses, applied to the ``extract`` section --
    every real line this section carries that *isn't* a
    'contact'/'devresist'/'antenna'/'disconnect'/'substrate' statement
    (``resist``/``order``/cap-coefficient/``device``/``variants``
    lines, comments) simply doesn't match ``_parse_extract_misc_line``
    and falls through as an untracked, verbatim gap at write-back time
    -- the same way cifinput's own still-read-only recipe blocks do
    alongside its two editable sub-structures."""

    return _scan_single_line_section(lines, "extract", safe_through, _parse_extract_misc_line)


def parse_tech_file(path: Path) -> MagicTechnology:
    included: list[str] = []
    lines = _load_lines_with_includes(path, included)
    sections = _split_sections(lines)

    tech = MagicTechnology(source_path=path, included_files=included)

    for line in sections.get("tech", []):
        stripped = line.strip()
        if stripped.startswith("format"):
            parts = stripped.split()
            if len(parts) == 2 and parts[1].isdigit():
                tech.format = int(parts[1])
        elif stripped and not stripped.startswith("#"):
            tech.name = stripped

    for line in sections.get("version", []):
        stripped = line.strip()
        if stripped.startswith("version"):
            tech.version = stripped.split(None, 1)[1].strip() if " " in stripped else ""
        elif stripped.startswith("description"):
            tech.description = stripped.split(None, 1)[1].strip().strip('"')
        elif stripped.startswith("requires"):
            tech.requires = stripped.split(None, 1)[1].strip()

    safe_through = _safe_prefix_line_count(path)
    tech.types, tech.all_parsed_type_line_nos, tech.types_section_start_line, tech.types_section_end_line = (
        _parse_types_with_lines(lines, safe_through)
    )

    tech.planes, tech.all_parsed_plane_line_nos, tech.planes_section_start_line, tech.planes_section_end_line = (
        _parse_planes_with_lines(lines, safe_through)
    )
    tech.contacts, tech.all_parsed_contact_line_nos, tech.contacts_section_start_line, tech.contacts_section_end_line = (
        _parse_contacts_with_lines(lines, safe_through)
    )
    tech.aliases, tech.all_parsed_alias_line_nos, tech.aliases_section_start_line, tech.aliases_section_end_line = (
        _parse_aliases_with_lines(lines, safe_through)
    )
    tech.styles, tech.all_parsed_style_line_nos, tech.styles_section_start_line, tech.styles_section_end_line = (
        _parse_styles_with_lines(lines, safe_through)
    )
    tech.cif_layers, tech.all_parsed_cif_layer_line_nos, tech.cifoutput_section_start_line, tech.cifoutput_section_end_line = (
        _parse_cifoutput_layers_with_lines(lines, safe_through)
    )
    (
        tech.cifinput_ignored_layers, tech.all_parsed_cifinput_ignore_line_nos,
        tech.cifinput_section_start_line, tech.cifinput_section_end_line,
    ) = _parse_cifinput_ignored_layers_with_lines(lines, safe_through)
    tech.cifinput_layer_hints, tech.all_parsed_cifinput_hint_line_nos, _cifinput_start2, _cifinput_end2 = (
        _parse_cifinput_hints_with_lines(lines, safe_through)
    )
    # _cifinput_start2/_cifinput_end2 are the exact same real section
    # bounds as above (one shared cifinput...end block) -- discarded,
    # not asserted equal, matching this module's own "don't guess, but
    # don't over-verify either" discipline elsewhere.
    tech.cifinput_recipes = _parse_cifinput_recipes(sections.get("cifinput", []))
    tech.compose, tech.all_parsed_compose_line_nos, tech.compose_section_start_line, tech.compose_section_end_line = (
        _parse_compose_with_lines(lines, safe_through)
    )
    tech.connect, tech.all_parsed_connect_line_nos, tech.connect_section_start_line, tech.connect_section_end_line = (
        _parse_connect_with_lines(lines, safe_through)
    )
    tech.drc_checks, tech.drc_angle_checks, tech.drc_skipped = _parse_drc_checks(sections.get("drc", []))
    tech.extract_resist = _parse_extract_resist(sections.get("extract", []))
    tech.extract_cap_coefficients = _parse_extract_cap_coefficients(sections.get("extract", []))
    tech.extract_devices = _parse_extract_devices(sections.get("extract", []))
    (
        tech.extract_misc, tech.all_parsed_extract_misc_line_nos,
        tech.extract_section_start_line, tech.extract_section_end_line,
    ) = _parse_extract_misc_with_lines(lines, safe_through)
    tech.extract_plane_order, tech.all_parsed_extract_plane_order_line_nos, _extract_start2, _extract_end2 = (
        _parse_extract_plane_order_with_lines(lines, safe_through)
    )
    # _extract_start2/_extract_end2 are the exact same real section
    # bounds as above (one shared extract...end block) -- discarded,
    # not asserted equal, same "don't guess, but don't over-verify
    # either" discipline cifinput's own two sub-structures already use.

    parsed = set(_TABULAR_SECTIONS) | {"cifoutput", "cifinput", "compose", "connect", "drc", "extract"}
    tech.unparsed_sections = sorted(set(sections) - parsed)

    return tech

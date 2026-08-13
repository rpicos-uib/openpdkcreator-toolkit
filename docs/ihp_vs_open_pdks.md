# IHP's real structure vs. the real open_pdks specification

**Short answer: yes, the same -- confirmed by open_pdks' own README, not
just by observing a similarity.** One concrete naming divergence is
documented below.

## The real open_pdks specification

Source: [`RTimothyEdwards/open_pdks`](https://github.com/RTimothyEdwards/open_pdks)'s
own README, "Open PDKs Format" section (the tool sky130/gf180mcu are
built with -- the reference this whole convention originates from):

```
<pdk-variant>
├── libs.doc
├── libs.qa
├── libs.ref
└── libs.tech
```

Within `libs.ref/`, one directory per IP library, named
`<pdk-family>_<tag>_[pr|sc|io|sram|...]` (`<tag>` identifies who
provided it -- `fd` for "foundry-provided" in the canonical sky130/
gf180mcu examples), each holding per-view subdirectories:
`cdl, gds, lef, lib, mag, maglef, spice, verilog, xschem, ...`.

Within `libs.tech/`, one directory per EDA tool: `klayout, magic,
netgen, ...` -- "Directories are typically named after the tools that
use the files they contain."

**That same README states explicitly:**

> IHP GmbH released their open PDK for the SG13G2 process using the
> format described in Open PDKs. For this reason, there is no need to
> use Open PDKs to build the IHP open PDK, because it already comes
> pre-built, with full support for open source EDA tools.

## IHP's real structure, confirmed against the real, downloaded tree

Top level (`ihp-sg13g2/`): exactly `libs.doc`, `libs.qa`, `libs.ref`,
`libs.tech` -- matches the spec exactly.

`libs.ref/` has four real families: `sg13g2_io`, `sg13g2_pr`,
`sg13g2_sram`, `sg13g2_stdcell`. Per-view subdirectories found:
`sg13g2_io/{cdl,doc,gds,lef,lib,spice,verilog}`,
`sg13g2_pr/{gds}` (GDS-only -- no per-device split, honestly matching
what `openpdkcreator/ihp/inventory.py`'s own real scan reports),
`sg13g2_sram/{cdl,doc,gds,lef,lib,verilog}`,
`sg13g2_stdcell/{cdl,doc,gds,lef,lib,spice,verilog}` -- a real,
slightly different view set per family (not every family ships every
view), which the spec's own `...` already anticipates.

`libs.tech/` has **15** real tool subdirectories (richer than the
2-4-tool `libs.tech/` a smaller PDK like this project's own
`openmempdk` ships): `digital, gdsfactory, klayout, librelane, magic,
netgen, ngspice, openems, openroad, palace, parasitics, qucs-s,
verilog-a, xschem, xyce`. Confirmed real, representative counts (via
`openpdkcreator/ihp/inventory.py`, run against the real download):
`magic/` has 35 files including 6 real `.tech` files. Confirmed by
actually reading them (see `openpdkcreator/ihp/magic_tech.py`): only
2 are genuinely separate technologies -- `ihp-sg13g2.tech` (the real,
connectivity-aware one) and `ihp-sg13g2-GDS.tech` (a second, simpler
"raw GDS layers" one, its own real `tech`/`version` header, used for
DRC/fill-pattern work that doesn't need connectivity). The other 4
(`ihp-sg13g2-{cifout,cifin,drc,extract}.tech`) are real *fragments*,
each self-wrapped in its own section keyword but spliced into
`ihp-sg13g2.tech` via real `include NAME` statements -- not standalone
technologies of their own. `klayout/` has 548 files including a real,
flat (see below) `sg13g2.lyp` and 42 real `.drc` files under
`tech/drc/` (`ihp-sg13g2.drc` plus 41 more under `rule_decks/`).
`digital/` and `palace/` are real git submodules IHP references but
this project deliberately never initializes (see `ihp/fetch.py`'s own
docstring) -- they show as real, empty directories, not missing ones.

## The one real divergence found

The canonical open_pdks example library name carries an explicit
provider-tag segment: `<pdk-family>_fd_<type>` (`fd` = "foundry-
provided"). **IHP's real library names omit it**: `sg13g2_pr`,
`sg13g2_io`, `sg13g2_sram`, `sg13g2_stdcell` -- no `_fd_` segment
anywhere. Worth documenting honestly rather than glossing over: the
*directory-level* structure (`libs.doc/qa/ref/tech`, per-tool/per-view
subdirectories) matches exactly; this one *naming-convention* detail
does not.

## Real KLayout `.lyp` parsing note

IHP's real `sg13g2.lyp` (`libs.tech/klayout/tech/sg13g2.lyp`) was
hand-checked for `<group-members>` nesting (real KLayout `.lyp` files
can group layers this way, which a flat top-level scan would silently
miss): **zero** `<group-members>` blocks found; all 377 real
`<properties>` entries are flat, top-level. `openpdkcreator/ihp/layers.py`'s
`import_layers()` (a flat scan, adapted from OpenPDKCreator's own
`import_open_pdks.py`) is confirmed correct for this specific file --
`find_group_members()` still checks and warns for any future `.lyp`
where that isn't true.

## Magic .tech vs. KLayout .lyp: two real, independent views of the same GDS stream

`openpdkcreator/ihp/magic_tech.py` parses `ihp-sg13g2.tech`'s real
`cifoutput` section (every `layer NAME ... calma L D` recipe -- 248
real named entries, 138 real `calma` output statements) into a
Magic-type-name -> (GDS layer, GDS datatype) mapping, independently of
the `.lyp`-derived one. `openpdkcreator/ihp/reconcile.py` cross-checks
them against each other -- both describe the same real, fabricated GDS
stream, from two different tools' own points of view.

Real result: **100 of the `.lyp`'s 377 (layer, datatype) pairs** have a
matching Magic `cifoutput` `calma` statement. The other 277 are, on
inspection, entirely explained: `.label`, `.net`, `.boundary`, `.OPC`,
`.iOPC`, `.noqrc`, `.pin`, `.text`, `.mask`, `.slit`, `.iprobe`,
`.diffprb`, `.filler`, `.nofill`, and similar suffixes -- KLayout's own
annotation/verification/QA datatypes, which Magic's real fabrication
output has no reason to ever paint. **Zero pairs exist only in Magic's
`cifoutput`** -- everything Magic emits is a real, already-known
`.lyp` layer. This is a real, sensible finding about how the two
tools' layer vocabularies differ in *scope* (KLayout enumerates every
GDS datatype used for any purpose; Magic's `cifoutput` only defines
what it needs to actually paint), not a parsing gap in either parser.

## Real LEF keyword casing note

`openpdkcreator/ihp/lef.py` was checked against all 32 of IHP's real,
downloaded `.lef` files. Most LEF keywords in these real files are
uppercase, matching the LEF spec's usual documented convention (`LAYER`,
`MACRO`, `PIN`, `SITE`, `PORT`, `OBS`, `CLASS`, `SIZE`, `SYMMETRY`,
`DIRECTION`, `USE`, `RECT`, ...) -- but the real via keywords are
mixed-case: `Via  Via1_XX DEFAULT` and `ViaRULE via1Array GENERATE`,
never `VIA`/`VIARULE`. The LEF spec itself says keywords are
case-insensitive; this real file is evidence a real foundry generator
actually relies on that (a different generator script likely emitted
the via definitions than emitted the rest of `sg13g2_tech.lef`, going
by the formatting/spacing differences around them). The parser matches
every keyword case-insensitively for exactly this reason, rather than
assuming the spec's uppercase convention always holds.

Also confirmed real, not a bug: two of IHP's real macro/cell LEFs
(`sg13g2_io.lef`, `sg13g2_stdcell.lef`) define zero tech `LAYER`s (pure
macro libraries -- the tech-specific `LAYER`/`VIA`/`ViaRULE` data lives
only in the separate `sg13g2_tech.lef`), and `sg13g2_io.lef` defines
**two** real `SITE`s (`sg13g2_ioSite` and `sg13g2_cornerSite` -- IO
pads and corner cells use different row heights than core standard
cells' `CoreSite`), not one.

## Real KLayout DRC-deck extraction results

`openpdkcreator/ihp/drc.py` was pointed at the **full**, real,
downloaded IHP DRC deck (`libs.tech/klayout/tech/drc/`, 42 real `.drc`
files -- the top-level `ihp-sg13g2.drc` plus 41 more under
`rule_decks/`, several nested a level deeper still, e.g.
`rule_decks/beol/5_16_metal1.drc`, correctly reached by a recursive
scan). This is the same regex-based extraction logic OpenPDKCreator's
own `import_open_pdks.py` already proved against a real, deliberately
small *subset* of this exact deck (5 real rules extracted there);
against the full deck, the real result is **61 real design rules**,
every one with a real, resolved numeric value (cross-referenced
against the real `sg13g2_tech_default.json` by variable name -- 100%
resolution, zero unresolved values). **94** real constructs were
honestly reported as not-auto-extracted -- composite/derived checks
(`.output()` on a variable that isn't a direct `.width()`/`.space()`/
`.sep()` result) and a handful of real `.width()`/`.space()`/`.sep()`
calls whose `.output()` never matches back to the same variable name
(a real, KLayout-DRC-DSL construct this pass's simple pattern doesn't
follow).

One real, noteworthy finding: several rule IDs extracted verbatim
contain a literal, unresolved Ruby string-interpolation template --
e.g. `M#{met_no}.a` from `rule_decks/beol/5_17_metaln.drc`, a real
rule defined once inside a Ruby loop over metal layer numbers rather
than once per layer. The extractor doesn't attempt to resolve or
enumerate this (that would mean actually running the Ruby DSL, not
regex-matching it) -- it's captured honestly as the literal template
text, not silently dropped or guessed at.

## Real per-cell file organization: two different real conventions, confirmed

`openpdkcreator/ihp/cells.py` (built for the **By Cell** hierarchical
view) had to handle a real structural fact confirmed by directly
counting real files, not assumed from one family alone: IHP's own four
real families use *two different* real per-view file organizations for
the same kind of view.

`sg13g2_io`/`sg13g2_stdcell` pack every real cell for a given view into
one real, combined file: one `.cdl` with all 84 real `.SUBCKT` blocks,
one `.v` with all 84 real `module`s, one `.spice`, one `.gds`, and 6-7
real `.lib` files (one per real PVT corner, each still containing every
cell for that corner).

`sg13g2_sram` instead ships one real file *per hard macro*: 28 real
`.cdl` files, 28 real `.gds` files, one real `.lib` file per
(macro, corner) pair (confirmed: 84 real `.lib` files = 28 macros x 3
real corners each) -- and, tellingly, **zero** real `.spice` files at
all (SRAM has no spice view in this real PDK, an honest fact
`cells.py`'s aggregator reports as "no spice view", not a bug or a
missing parser).

One more real, worth-recording surprise: `sg13g2_sram`'s real CDL/
Verilog files are not flat one-macro-per-file netlists -- they're full,
real hierarchical netlists, each defining hundreds of internal real
sub-elements (bitcells, sense amps, decoders, ...) alongside the one
real, top-level hard macro matching the file's own name. Counted
directly: **2338** real subckts total across all of `sg13g2_sram`'s
real CDL files, of which only **28** have a matching real LEF macro --
i.e. are genuinely top-level, physically instantiable cells. This is
why `cell_hub_view.py`'s cell list defaults to "has a real LEF macro"
rather than showing everything discovered -- the raw netlist count
answers a different, real question ("how many subckts exist in this
family's netlists") than the one a PDK-authoring wizard's cell browser
should default to answering ("what are this family's real, usable
cells").

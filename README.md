# openPDKcreator

A general PDK-authoring toolkit, started from a real, complete PDK
(IHP's SG13G2, `github.com/IHP-GmbH/IHP-Open-PDK`, Apache-2.0) rather
than a toy example -- read/represent any PDK's real files first,
grow toward creating/editing/generating them.

A separate, independent project from
[`OpenPDKCreator`](https://github.com/rpicos-uib/OpenPDKCreator) (the
memristor-PDK-specific toolkit this one borrows its Layers interface
and EDA-tool checker from) -- that project stays scoped to its own six
fixed logical primitives; this one is meant to generalize beyond that.
Code was copied, not shared, since the two projects' scope has already
diverged -- see `openpdkcreator/eda_tools.py`'s and
`openpdkcreator/gui/layers_view.py`'s own docstrings for exactly what
was copied and what (if anything) was adapted.

## Quickstart

```
pip install pyyaml    # not currently used, but matches the sibling project; harmless to skip for now
python3 main.py fetch        # downloads the real IHP PDK into data/ (~734 MB, gitignored, run once)
python3 main.py inventory    # real per-tool file census, printed
python3 main.py magic-tech   # real Magic .tech parse + cross-reference against the .lyp
python3 main.py lef          # real LEF parse summary: tech layers + macro/cell footprints
python3 main.py gui          # Overview / Technology / Cells tabs (needs a real X11/Xvnc display)
```

## GUI structure

Tabs are grouped by what they represent, not left flat: **Overview**
(the real, per-tool file inventory, spanning every domain including
ones with no dedicated view yet), **Technology** (process/technology-
definition data -- **Layers** and **Magic Tech** as sub-tabs, one per
tool that defines it), and **Cells** (real cell/macro data -- `LefView`
directly, since LEF is currently the only real cell-data parser; a
sub-notebook is the right move once a second one exists, e.g. CDL/
Liberty/Verilog). No empty **Simulation** top-level group exists yet --
there's no real parser behind ngspice/xschem/Qucs-S model/schematic
data yet (see Future Work); adding one now would show fake
completeness. **Technology**/**Cells** are the pattern a future group
would repeat once a real parser exists for it.

## What's real here (first increment)

- **`openpdkcreator/ihp/fetch.py`** -- a real, depth-1, sparse-checkout
  clone of `ihp-sg13g2/{libs.doc,libs.qa,libs.ref,libs.tech}` (~734 MB),
  deliberately excluding IHP's own git submodules (separate third-party
  repos for digital synthesis / EM-solver integration, unrelated to PDK
  structure). Lands in `data/` -- **gitignored, never committed**; IHP's
  data stays local-only, this repo versions only original tooling code.
- **`openpdkcreator/ihp/inventory.py`** -- an honest, per-tool file
  census (file count, total size, extension breakdown) across all 15
  real `libs.tech/<tool>/` subdirectories and every real
  `libs.ref/<family>/<view>/` directory. No attempt at parsing any
  tool's proprietary format -- that's real, separate future work.
- **`openpdkcreator/ihp/layers.py`** -- real KLayout `.lyp` parsing
  (adapted from OpenPDKCreator's own, already-verified
  `import_open_pdks.py`), confirmed against IHP's real, downloaded
  `sg13g2.lyp`: 377 real layers, byte-accurate name/GDS-layer/GDS-
  datatype/frame-color/fill-color, hand-checked for `<group-members>`
  nesting (none found -- see `docs/ihp_vs_open_pdks.md`).
- **`openpdkcreator/gui/layers_view.py`** -- OpenPDKCreator's own
  Layers tab, copied verbatim, displaying the real parsed layers above.
- **`openpdkcreator/eda_tools.py`** -- OpenPDKCreator's own FOSS
  EDA-toolchain checker/installer/launcher, copied with one small,
  honest simplification (its two PDK-specific "pre-pointed" launch
  entries for Magic/KLayout were dropped -- see the module's own
  docstring for why).
- **`docs/ihp_vs_open_pdks.md`** -- a real, sourced comparison of IHP's
  actual structure against the canonical open_pdks specification
  (confirmed via open_pdks' own README: IHP genuinely follows it), with
  one real naming divergence documented, not glossed over.
- **`openpdkcreator/ihp/magic_tech.py`** -- a real (if deliberately
  partial) Magic `.tech` parser, hand-verified against IHP's real,
  downloaded files: the cleanly tabular sections
  (`tech`/`version`/`planes`/`types`/`contact`/`aliases`/`styles`) in
  full, plus one reliable pattern pulled out of the much harder
  `cifoutput` geometry DSL (every real `layer NAME ... calma L D`
  recipe -- a genuine Magic-type-name to GDS-layer/datatype mapping).
  Real `include` resolution confirmed: `ihp-sg13g2.tech` splices in 4
  fragment files (`cifout`/`cifin`/`drc`/`extract`) as one logical
  technology; `ihp-sg13g2-GDS.tech` is a second, genuinely separate
  technology with its own header. `drc`/`extract`/`cifinput`/`connect`/
  `compose`/`lef`/etc. are honestly reported as not-parsed-this-pass,
  never silently dropped (`MagicTechnology.unparsed_sections`).
- **`openpdkcreator/ihp/reconcile.py`** -- cross-references the Magic
  `cifoutput` GDS mapping above against the KLayout `.lyp` layers
  (`ihp/layers.py`), both real, independent descriptions of the same
  fabricated GDS stream. Real result against IHP's actual data:
  100/377 (GDS layer, datatype) pairs recognized by both; the 277
  `.lyp`-only pairs are all annotation/QA datatypes (`.label`, `.net`,
  `.boundary`, `.OPC`, ...) Magic's real fabrication output has no
  reason to paint -- a real, sensible finding, not a parsing gap (zero
  Magic-only pairs: everything Magic emits is a real, known layer).
- **`openpdkcreator/gui/magic_tech_view.py`** -- a Magic Tech tab
  (`MagicTechView`), matching the Layers tab's Treeview-based shape:
  a technology picker (`ihp-sg13g2` / `ihp-sg13g2-GDS`, the two real,
  separate technologies -- the `include`d fragments have no own header
  and aren't shown standalone) over six sub-tabs, one per real,
  parsed data domain (Planes/Types/Contacts/Aliases/Styles/CIF
  Layers). Read-only for now. Verified for real, driven against the
  actual downloaded data: all six sub-tabs' row counts match
  `magic-tech`'s own CLI output exactly, and switching technologies in
  the picker correctly reloads every sub-tab.
- **`openpdkcreator/ihp/lef.py`** -- a real (if deliberately partial)
  LEF parser, hand-verified against all 32 of IHP's real, downloaded
  `.lef` files (a tech LEF, `sg13g2_stdcell.lef`/`sg13g2_io.lef`, and
  28 real SRAM hard-macro LEFs). Fully parses tech-LEF `LAYER`s (type/
  direction/pitch/width/one simple spacing value/resistance), `SITE`s,
  and real `MACRO`s (class/size/site/symmetry) with their `PIN`s
  (direction/use/port layers+rect counts) and `OBS` layers. Found and
  handled a real, easy-to-miss detail: this file's actual via keywords
  are mixed-case (`Via`, `ViaRULE`), not `VIA`/`VIARULE` as the LEF
  spec's usual all-uppercase convention might suggest -- confirmed by
  reading the real file, not assumed; the parser matches keywords
  case-insensitively throughout. `VIA`/`ViaRULE` bodies (real via-stack
  geometry) are deliberately not parsed -- names recorded, bodies
  honestly skipped. Every value hand-checked against the real source:
  `sg13g2_a21o_1`'s 6 real pins (name/direction/use/rect-count each),
  a real SRAM macro's 113 real pins, `sg13g2_tech.lef`'s 19 real
  layers/70 real vias/6 real via-rules.
- **`openpdkcreator/gui/lef_view.py`** -- a Cells tab (`LefView`): a
  file picker over all 32 real `.lef` files, with LEF Layers and LEF
  Macros sub-tabs (the latter: a macro list, selecting one shows its
  real pins). Verified for real, driven against the actual data:
  correct counts across `sg13g2_io.lef` (22 macros)/`sg13g2_stdcell.lef`
  (84 macros)/a real SRAM macro, and selecting `sg13g2_and2_1` shows
  its exact 5 real pins.

## Future work

The stated end goal is much bigger than this first increment: an
application that can create/edit/generate arbitrary PDK file types
(Magic technology files, KLayout DRC decks, LEF, GDS, Liberty, SPICE
models, ...), not just read/display layers. Concretely, still open:

- Deep parsers for Magic's `drc`/`extract`/`cifinput`/`connect`/
  `compose` sections (each its own real, separate mini rule-language --
  `drc` and `extract` in particular are the Magic equivalent of
  KLayout's DRC Ruby DSL), plus GDS, Liberty, real KLayout DRC decks,
  and LEF's own `VIA`/`ViaRULE` via-stack geometry -- no generic
  parser for any of these exists yet.
- Editing/creating/generating PDK content, not just reading it.
- Re-add "pre-pointed" Magic/KLayout launch guidance in
  `eda_tools.py` once a real mapping to IHP's actual multi-file tech
  setup (6 real `.tech` files, not 1) is designed, not guessed.
- A **Simulation** top-level GUI group (ngspice/xschem/Qucs-S models
  and schematics), matching the **Technology**/**Cells** groups'
  pattern -- still inventory-only today (see the Overview tab), no real
  per-format parser exists yet.
- A CDL/Liberty/Verilog parser to give the **Cells** tab a real second
  sub-tab alongside LEF (at which point it becomes a sub-notebook, the
  same shape **Technology** already uses).
- Revisit copying vs. sharing code with `OpenPDKCreator` if the two
  projects' core models (`Layer`, the tool registry) diverge enough to
  need reconciling.

## License

Apache-2.0 (see `LICENSE`) -- matching `OpenPDKCreator`, the project
some of this code was copied from. IHP-Open-PDK itself (fetched
locally, never committed here) is also Apache-2.0 -- see
`github.com/IHP-GmbH/IHP-Open-PDK`'s own `LICENSE`.

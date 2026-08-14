# openPDKcreator

**Final objective: a wizard to edit and create an open PDK, generally
-- not specific to any one process.** IHP's real SG13G2
(`github.com/IHP-GmbH/IHP-Open-PDK`, Apache-2.0) is the *current
model* this is being built and verified against, not the permanent
target -- a real, complete PDK instead of a toy example, so every
parser/editor here is proven against real, messy, full-scale data from
day one. It will eventually point at other real PDKs too; keep that in
mind before adding anything that only makes sense for IHP specifically.

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
pip install pyyaml    # required: project_io.py's save/load format
python3 main.py fetch        # downloads the real IHP PDK into data/ (~734 MB, gitignored, run once)
python3 main.py inventory    # real per-tool file census, printed
python3 main.py magic-tech   # real Magic .tech parse + cross-reference against the .lyp
python3 main.py lef          # real LEF parse summary: tech layers + macro/cell footprints
python3 main.py drc          # real KLayout DRC-deck rule extraction summary
python3 main.py cells        # real per-cell view aggregation, one real family at a time
python3 main.py gds          # real GDS structural summary (bbox/shape counts) -- needs klayout.db
python3 main.py export-lef   # real, patched .lef write-back to export/ (byte-identical with no edits)
python3 main.py export-drc   # real, patched DRC-rule write-back to export/ (byte-identical with no edits)
python3 main.py export-magic-types   # real, patched Magic Types write-back to export/ (byte-identical with no edits)
python3 main.py export-netlist   # real, patched .cdl/.spice port write-back to export/ (byte-identical with no edits)
python3 main.py export-verilog   # real, patched .v port write-back to export/ (byte-identical with no edits)
python3 main.py export-liberty   # real, patched .lib pin/timing write-back to export/ (byte-identical with no edits)
python3 main.py export-full --dest DIR   # a complete, standalone PDK tree -- round-trip fidelity testing
python3 main.py gui          # Overview / Technology / Cells / Settings tabs (needs a real X11/Xvnc display)
```

`main.py gui` needs a real X11/Xvnc display -- this host has none locally (no
`Xvfb`/`xvfb-run`, `$DISPLAY` unset), confirmed by trying `export DISPLAY=...`
directly and getting nothing. `./start_eda_container.sh --gui` starts (or
reattaches to) a dedicated IIC-OSIC-TOOLS container with one, then launches
`main.py gui` inside it, real `data/` bind-mounted through -- no manual file
copying needed. Open the printed `http://127.0.0.1:<port>/?password=...` URL
in a browser (the `127.0.0.1` form specifically -- see the script's own
header comment for why `localhost` doesn't work under rootless Podman's
`pasta` network backend). Uses its own container name and ports (distinct
from `OpenPDKCreator`'s own `scripts/start_eda_container.sh`), so both
projects' containers can run at once without colliding -- confirmed by
running both side by side for real.

## GUI structure

Tabs are grouped by what they represent, not left flat: **Overview**
(the real, per-tool file inventory, spanning every domain including
ones with no dedicated view yet), **Technology** (process/technology-
definition data -- **Layers**, **Magic Tech**, and **DRC Rules** as
sub-tabs, one per tool that defines it), **Cells** (real cell/macro
data -- **LEF** and **By Cell** as sub-tabs), and **Settings**
(project-level settings -- not any one tool's PDK content -- **General**
and **Tools** as sub-tabs). No empty **Simulation** top-level group
exists yet -- there's no real parser behind ngspice/xschem/Qucs-S
model/schematic data yet (see Future Work); adding one now would show
fake completeness. **Technology**/**Cells** are the pattern a future
group would repeat once a real parser exists for it.

**By Cell** is the hierarchical, cell-centric view: pick one real
cell, in one place see which of its real views (LEF/CDL/SPICE/
Verilog/Liberty/GDS) actually exist, jump straight to that cell's own
real block inside each, and **edit its real LEF pins directly** in a
**Pins** pane -- the exact same in-memory macro/pins the LEF tab's own
"LEF Macros" sub-tab edits (both tabs parse through one shared,
``App``-owned cache, ``App.get_parsed_lef``, so a pin edited from
either tab is immediately visible, and saves the same way, from the
other). A cell with no real LEF macro (an internal netlist sub-element
with no macro of its own -- common in `sg13g2_sram`) shows a plain
"nothing to edit here" note instead, not a broken/empty editor.
**CDL/SPICE/Verilog ports** are also editable, via a small **Edit
Ports** dialog next to each real **View** button -- real per-port
direction from a real CDL `*.PININFO` comment or real Verilog
`input`/`output`/`inout` declarations, add/delete/rename/redirect, the
same commit-on-switch pattern as everywhere else. **Liberty pins and
timing arcs** are editable too, via an **Edit Pins/Timing** button next
to the Liberty listbox (one real `.lib` corner file at a time, since a
cell's timing legitimately differs per corner) -- a two-level dialog:
a **Pins** pane (name/direction/capacitance/function) and, for the
selected pin, a **Timing Arcs** pane
(related_pin/timing_type/timing_sense/when); the real lookup-table
sub-groups (`cell_rise`/`cell_fall`/`rise_transition`/
`fall_transition`) stay read-only, unmodeled, same bounded-scope
precedent as everywhere else. Same `App`-owned caching
(`App.get_parsed_liberty`) as LEF/CDL/SPICE/Verilog, so switching
families and back never silently discards an in-progress edit.

Every real list this size warrants it (Layers, DRC Rules, LEF Macros,
By Cell, Magic Types) has a live **Filter** box (`gui/list_filter.py`
-- one shared, case-insensitive substring helper, so all five behave
identically rather than five subtly different implementations):
matches update on every keystroke, an empty box shows everything, and
a filter matching nothing clears the detail form rather than showing a
stale one. Creating a new entry (**New Layer**/**New Rule**/**New
Type**) always clears its own list's filter first, so the freshly
created row is never hidden by whatever search was active.

**Settings > General** holds two deliberately distinct,
separately-labeled pairs, so they never get confused now that this
tool generalizes beyond IHP: **This Project** (an editable **Project
name**, saved and restored the same way as DRC Rules/Magic Types/LEF
pins, plus a read-only **Project directory** -- where this tool and
its `saves/` actually live) and **Source PDK** (read-only **Original
PDK name** and **Original PDK location** -- the real, downloaded
`pdk_root`'s own name/path, plus the real upstream URL it was fetched
from). More project-level settings belong here as they're added.

**Settings > Tools** is a real, live status view of the FOSS EDA
toolchain (`eda_tools.py`) this project's various real PDK views are
authored/verified with: found/missing, real detected version and path,
install guidance (shown, never auto-run), and a **Launch** button for
whatever's already on PATH -- a thin GUI wrapper around
`eda_tools.py`'s own existing check/launch logic (no new detection
code of its own, so the CLI and GUI stay in lock-step).

Every real file-backed tab (Layers, Magic Tech, Cells) has a
**View File** button opening the real, underlying file directly
(`file_view_dialog.view_file_dialog`) -- read-only at first, since
these are real, downloaded third-party PDK files; an **Edit** button
inside that dialog switches it to editable and reveals **Save**, a
deliberate two-step confirmation before changing a real foundry file,
not OpenPDKCreator's own always-editable dialog of the same name.
Saving only ever touches the local, gitignored `data/` copy. **By
Cell**'s own "View <format>" buttons use the same dialog, scrolled and
highlighted straight to that cell's real line range within its
(often much larger, multi-cell) real source file.

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
  (`tech`/`version`/`planes`/`types`/`contact`/`aliases`/`styles`/
  `compose`/`connect`) in full, plus one reliable pattern pulled out of
  each of four much harder mini-rule-language sections:
  - `cifoutput`: every real `layer NAME ... calma L D` recipe -- a
    genuine Magic-type-name to GDS-layer/datatype mapping.
  - `cifinput`: two real, cleanly tabular facts -- every real `ignore
    LAYERNAME` statement (23 real entries) and a real, standalone
    `calma NAME L D` table (133 real entries, confirmed by reading the
    file to sit together in one flat block, not nested inside any
    boolean recipe -- a genuinely different real shape from
    `cifoutput`'s own per-recipe `calma L D`, which omits the name and
    inherits it from the enclosing block, so it needed its own regex).
    Two of those 133 real entries use a literal `*` wildcard datatype
    (`calma BOUND 189 *`) -- kept as `None`, not silently dropped or
    coerced to a fake integer. The section's own real geometry-boolean
    recipe blocks (`and`/`and-not`/`grow`/`shrink`) are still not
    interpreted -- their *first* line alone isn't a complete, honest
    fact the way `cifoutput`'s *final* `calma` line is, so fully
    modeling them stays real, separate future work.
  - `drc`: the three dominant, cleanly tabular real statement kinds,
    `width`/`spacing`/`maxwidth` -- 192 of the real section's
    statements (65/65 `width`, 101/102 `spacing`, 26/26 `maxwidth`; the
    one real `spacing` miss is a genuine defect in IHP's own file, a
    message string missing its closing quote, confirmed by direct
    inspection). `maxwidth` reuses `width`'s own regex structure
    exactly -- same real message-quoting shape, filler tokens (mode, an
    optional real exception list like `glass,pillar,solder`) skipped
    the same way, not asserted. Real values converted to microns via an
    empirically-confirmed `/1000` factor, cross-checked against three
    independent, already-extracted real KLayout DRC rules sharing the
    same real rule ID (`Act.a`: `0.15` both ways; `Gat.a`: `0.13` both
    ways; `NW.b`: `0.62` both ways) -- not from Magic's own documented
    unit spec, which this pass had no authoritative local source to
    confirm against, but a real, repeatable, cross-checked fact for
    `width`/`spacing`; the same factor is applied to `maxwidth` on the
    reasonable inference that one real file's one section shares one
    real internal unit scale, not a fresh independent confirmation.
  - `extract`: real per-layer sheet resistance (`resist`, 30/33 real
    lines -- milliohms/square, the other 3 are real non-numeric config
    entries, not a parsing gap) and real plane ordering (`planeorder`,
    14/14), plus the section's own real parasitic-capacitance
    coefficients (`defaultoverlap`/`defaultsideoverlap`/
    `defaultareacap`/`defaultperimeter`/`defaultsidewall`, 506 real
    lines combined -- every real line for a given directive shares the
    exact same real token count, confirmed directly, so leading args
    and trailing value(s) split at a fixed, real, per-directive
    position; argument semantics deliberately not asserted, same
    "don't guess" discipline `ComposeStatement` already uses) and every
    real `device <class> <model> <type> ...` statement (50 real
    entries, some wrapped across lines with a trailing `\` and joined
    the same way the `drc` section's own wrapped statements already
    are).

  Real `include` resolution confirmed: `ihp-sg13g2.tech` splices in 4
  fragment files (`cifout`/`cifin`/`drc`/`extract`) as one logical
  technology; `ihp-sg13g2-GDS.tech` is a second, genuinely separate
  technology with its own header. `lef`/`mzrouter`/`wiring`/`router`/
  `plowing`/`plot`, and `extract`'s own real remainder
  (`devresist`/`contact`/`antenna`/`disconnect`/`substrate`) are
  honestly reported as not-parsed-this-pass, never silently dropped
  (`MagicTechnology.unparsed_sections`, `MagicTechnology.drc_skipped`).
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
  and aren't shown standalone) over thirteen sub-tabs, one per real,
  parsed data domain (Planes/Types/Contacts/Aliases/Styles/CIF Layers/
  **CIF Input**/Compose/Connect/**DRC (Magic)**/Extract/**Extract
  Coefficients**/**Extract Devices** -- CIF Input shows the section's
  own two real, extracted facts side by side (ignored layers; the
  standalone `calma` layer-hint table, `*` wildcard datatypes shown as
  `*`, not a fake `0`); Extract Coefficients/Extract Devices show the
  extract section's own real parasitic-coefficient lines and real
  `device` statements) -- plus a **View File** button. **Types is
  editable** -- a list + form pane (Plane/Name/Aliases/Obsolete),
  New/Delete Type, the same commit-on-switch pattern as everywhere
  else; every other domain stays read-only for now (each would need
  its own form). Verified for real, driven against the actual
  downloaded data: all thirteen sub-tabs' row counts match
  `magic-tech`'s own CLI output exactly (39 compose/20 connect/192 DRC
  checks/30 resist/23 cifinput-ignored/133 cifinput-hints/506 extract
  cap coefficients/50 extract devices), switching technologies
  correctly reloads every sub-tab, editing a real type's
  name/aliases/obsolete commits
  immediately and survives a technology switch, and a spot-checked real
  DRC row (`Act.a`) shows the correct converted `0.15` micron value.
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
  geometry) are also parsed, not just named: a real fixed `Via NAME
  DEFAULT` block's own layer/rect list (a real layer name can
  legitimately repeat with a different rect -- confirmed real in IHP's
  own double-cut vias, e.g. `Via1_DC1B`'s two real `LAYER Via1`
  entries, kept as an ordered list rather than merged into a dict), and
  a real `ViaRULE NAME GENERATE` block's own per-layer enclosure/rect/
  spacing/resistance. Every value hand-checked against the real source:
  `sg13g2_a21o_1`'s 6 real pins (name/direction/use/rect-count each),
  a real SRAM macro's 113 real pins, `sg13g2_tech.lef`'s 19 real
  layers/70 real vias (242 real rects total, cross-checked against
  grep ground truth exactly)/6 real via-rules (`via1Array`'s own real
  layer geometry hand-verified field-by-field against the source
  file). Displayed in the LEF tab's own **Vias** sub-tab, read-only (no
  editor for via geometry exists, matching every other display-only
  domain). Also tracks each real
  `MACRO`/`PIN` block's own real, 1-indexed source line range
  (`start_line`/`end_line`) -- added specifically for
  `ihp/lef_writer.py`'s own write-back, which needs to locate exactly
  where a real pin's text lives to patch it in place.
- **`openpdkcreator/gui/pin_editor.py`** -- `PinEditor`, a real macro
  pin list + New/Delete Pin + a Name/Direction/Use form, the same
  commit-on-switch pattern `LayersView`/`RulesView` already use.
  Extracted out of `lef_view.py` (where it was originally built) so
  both the **LEF** tab's own "LEF Macros" sub-tab and the **By Cell**
  tab's Pins pane share one real, already-bug-fixed implementation --
  not two independent copies. Direction/Use are free-typable
  comboboxes, not `readonly` -- IHP's real data only has 3 real `USE`
  values (`SIGNAL`/`POWER`/`GROUND`) and 3 real pin `DIRECTION`s
  (`INPUT`/`OUTPUT`/`INOUT`, confirmed by grepping the real files), but
  other real, standard LEF PDKs can have more (e.g. `CLOCK`). **A real
  bug found and fixed while first building this**: a combobox's own
  `<<ComboboxSelected>>` event only fires on a dropdown *pick* -- a
  typed or programmatic value change silently never committed without
  also tracing the variable's own `write` event (confirmed by a real,
  driven test: `.set("POWER")` didn't take effect until a later,
  unrelated commit-on-switch happened to also read the same,
  by-then-updated variable). Port geometry (real drawn rectangles)
  stays display-only -- editing raw geometry is a real, separate, much
  bigger feature.
- **`openpdkcreator/gui/lef_view.py`** -- a Cells tab (`LefView`): a
  file picker over all 32 real `.lef` files, with LEF Layers and LEF
  Macros sub-tabs (the latter: a macro list; selecting one embeds
  `PinEditor` above on its real pins), plus a **View File** button.
  Real parsing/caching moved up to `App.get_parsed_lef` (see `app.py`'s
  own docstring) so this tab and **By Cell** share one real parse per
  file, not two. Verified for real, driven against the actual data:
  correct counts across `sg13g2_io.lef` (22 macros)/`sg13g2_stdcell.lef`
  (84 macros)/a real SRAM macro; editing a real pin's name/use commits
  immediately and survives a macro switch; New/Delete Pin both work,
  including the empty-macro edge case (delete every pin, then add one
  back).
- **`openpdkcreator/gui/file_view_dialog.py`** -- the shared **View
  File** dialog wired into all three file-backed tabs above: opens the
  real, selected source file read-only; its own **Edit** button
  switches it editable and reveals **Save** (writes the real, local
  file after an explicit confirmation). Verified for real, driven
  against the actual data across all three tabs (Layers/Magic Tech/
  Cells): correct file opened in each case, Edit correctly flips the
  Text widget and Save button state, and a real save-to-a-scratch-copy
  round trip confirmed the write is byte-exact (a prepended marker
  line, the rest of the file untouched) -- the real, fetched `data/`
  itself was never touched by this verification.
- **`openpdkcreator/ihp/drc.py`** -- real KLayout DRC-deck rule
  extraction, adapted from OpenPDKCreator's own `import_open_pdks.py`
  (that logic already proved itself against a real *subset* of this
  exact IHP deck -- this module points the same, unmodified pattern at
  the **full** real deck: 42 real `.drc` files, not a sample), extended
  with a second real, recognizable pattern beyond the original
  `width()`/`space()`/`sep()`: a real `inner_expr.enclosed(outer_expr,
  value.um, mode)` two-layer enclosure check (confirmed real and
  common -- 22 real occurrences across 13 real files, always this
  exact shape), mapped to the existing `min_enclosure` check type,
  whose own `Inner layer`/`Outer layer` roles already match KLayout's
  own real semantics exactly. Real result: **75 real design rules**
  extracted (61 width/space/sep + 14 enclosure), all with a real,
  resolved numeric value (100% resolution against the real JSON config
  -- hand-checked: `M1.a`'s `0.16` and the new `V1.c`'s `0.01` both
  match both the real `sg13g2_tech_default.json` and their real source
  lines), and **86** composite/derived constructs (down from 94)
  honestly reported as not-auto-extracted, never dropped silently. A
  real gap found and fixed while adding this:
  `ihp/drc_writer.py`'s own `_locate` (which re-derives a rule's real
  JSON key on write-back) only re-ran the width/space/sep regex, so a
  newly-extracted enclosure rule's edited `value` silently failed to
  reach the real JSON file -- caught immediately by a real, driven
  round-trip test on `V1.c`, fixed by having `_locate` also check the
  new enclosure regex before giving up. One real, interesting finding
  worth noting: some real rule IDs themselves contain a literal Ruby
  string-interpolation template (`M#{met_no}.a`, from a real
  per-metal-layer loop in the source) -- captured verbatim, not
  silently mangled.
- **`openpdkcreator/schema.py`** -- `CheckTypeSpec`/`CHECK_TYPES`/
  `CHECK_TYPE_ORDER`, copied verbatim from OpenPDKCreator's own
  `scripts/pdk_wizard/schema.py` -- already confirmed fully
  technology-agnostic during ADR 0018 research in that project (every
  entry is a generic DRC concept: min width/spacing/area/overlap/
  enclosure, max length/current-density/array-dimension, density
  window).
- **`openpdkcreator/gui/rules_view.py` + `rule_canvas.py`** -- a real
  DRC Rules tab (`RulesView`), adapted from OpenPDKCreator's own
  Design Rules tab: the same rule list + live-diagram + full-field
  form, New/Delete Rule, and rule-ID auto-naming -- one real
  simplification (`_suggest_prefix`'s native-device-stack special case
  is dropped, since this project has no `devices` model at all), plus
  one real addition: a **View Source** button opening the exact real
  `.drc` file (and line) a selected rule was extracted from, via each
  rule's own `source_provenance`. Rules start real (61 of them, loaded
  from `ihp/drc.py` at startup), not blank, then editable the same way
  a hand-authored rule would be. Verified for real, driven against the
  actual data: correct row/form population, New/Delete both work,
  **View Source** opens the exact real file and highlights the right
  lines, and the live diagram/`layer_colors()` both render correctly.
- **`openpdkcreator/ihp/netlist.py`/`verilog.py`** -- real cell/module
  boundary detectors (`.subckt`/`.ends` for CDL/SPICE, case-insensitive
  -- CDL's real files use `.SUBCKT`/`.ENDS`, SPICE's use lowercase, the
  same lesson as `lef.py`'s `Via`/`ViaRULE` finding; `module`/
  `endmodule` for Verilog) that now also extract **real per-port
  structure**, matching `lef.py`'s own `LefPin` in ambition: CDL's real
  `*.PININFO name:I name:O name:B ...` comment (confirmed 100% real
  coverage -- 130/130 SUBCKTs -- across `sg13g2_io`/`sg13g2_stdcell`'s
  CDL, and confirmed real *absence* across all of `sg13g2_sram`'s own
  CDL -- 0/2338 -- an honest real gap, not a parser gap; `I`/`O`/`B`
  map to `INPUT`/`OUTPUT`/`INOUT`); Verilog's own real `input`/
  `output`/`inout` declarations (plus a real bus `[msb:lsb]` width,
  confirmed real and common in SRAM modules). **Two real, previously-
  unnoticed bugs found and fixed while extending these for real port
  editing, not assumed**: (1) a real `.SUBCKT` header can wrap its port
  list across `+`-continuation lines -- confirmed real and common in
  `sg13g2_sram`'s own internal sub-elements (dozens in one file alone)
  -- the original parser silently truncated those cells' real port
  lists at the line break, since only the real, single-line top-level
  hard-macro SUBCKTs happened to avoid it, so the bug never surfaced in
  the By Cell hub's own top-level-only default view; (2) a real
  Verilog `module` header can wrap across multiple lines -- confirmed
  real in *every one* of IHP's own 28 real SRAM top-level macros -- the
  original parser required the closing `)` on the same line, so it
  found **zero** real Verilog modules for any real SRAM macro at all.
  Both fixed by joining continuation/multi-line headers before parsing.
  Verified for real: per-file cell counts now match real `.SUBCKT`
  grep ground truth exactly (4060/4060 across all 28 real SRAM CDL
  files); the real SRAM top-level macro's Verilog module is now found,
  with correct real bus port widths (e.g. `A_ADDR`: `input [9:0]`).
- **`openpdkcreator/ihp/liberty.py`** -- a real, stack-based state
  machine (same technique as `lef.py`) tracking arbitrary named-group
  nesting depth, extended beyond real `cell (NAME) { ... }` boundary
  detection into real, bounded pin/timing-arc extraction: a pin's
  `direction`/`capacitance`/`function`, and, per real `timing () { ... }`
  arc, `related_pin`/`timing_type`/`timing_sense`/`when` -- the real
  lookup-table sub-groups (`cell_rise`/`cell_fall`/`rise_transition`/
  `fall_transition`, each its own nested multi-dimensional
  `index_1`/`index_2`/`values` data) deliberately left unparsed, the
  same "bounded, not a full parser" precedent as LEF's own PORT rect
  geometry. Two real structural complexities found and handled, not
  assumed: every real file wraps its cells in one real top-level
  `library (NAME) { ... }` group (missed on the first pass -- every
  real cell is nested one level inside it, never at true "root",
  causing a real 0-cells-found bug until fixed); `sg13g2_sram`'s own
  real files wrap a bus's per-bit pins in a real `bus (NAME) { ... }`
  group with its own two real, both-real formatting conventions
  (`sg13g2_stdcell`: spaced `pin (NAME) {`, quoted values;
  `sg13g2_sram`'s bus-nested pins: unspaced `pin(NAME) {`, unquoted
  values, direction inherited from the enclosing bus when a per-bit pin
  declares none of its own -- confirmed real, never redundantly
  repeated). A real, separate `test_cell () { pin(...) {...} }`
  scan-test/DFT pin representation (confirmed real, `sg13g2_stdcell`
  only) is deliberately excluded from the real functional pin list, not
  a bug -- it isn't specially recognized, so it falls through the
  generic "skip any other real nested group" path along with
  `leakage_power`/`internal_power`/the lookup tables themselves. Real,
  1-indexed source line ranges tracked per pin and per timing arc
  (`start_line`/`end_line`, plus `all_parsed_pin_ranges`/
  `all_parsed_arc_ranges`, immutable original-position lists mirroring
  `lef.py`'s own `LefMacro.all_parsed_pin_ranges`) feed
  `ihp/liberty_writer.py`'s write-back. Verified for real: all 97 real
  `.lib` files parse cleanly with 0 errors -- 700 real cells, 5422 real
  pins, 3977 real timing arcs total.
- **`openpdkcreator/gui/liberty_editor.py`**/**`liberty_dialog.py`** --
  the **Edit Pins/Timing** dialog (see GUI structure above): a
  two-level, commit-on-switch editor (Pins pane, and a nested Timing
  Arcs pane for whichever pin is selected); switching pins flushes any
  pending arc edit too, not just the pin's own fields.
- **`openpdkcreator/ihp/liberty_writer.py`** -- real, surgical,
  position-targeted write-back for Liberty pin/timing-arc data,
  following the same discipline as every other writer here: re-reads
  the pristine original file fresh from disk at write time, patches
  only the exact real attribute lines a pin's/arc's edited fields
  occupy, and leaves everything else -- above all each real timing
  arc's own unparsed lookup-table sub-groups -- byte-for-byte
  untouched. Diffs each field against a **fresh re-parse** rather than
  blindly re-emitting it, since real Liberty attribute lines carry
  real, inconsistent quoting/whitespace/spacing conventions file to
  file (confirmed real: `sg13g2_stdcell` quotes `direction`,
  `sg13g2_sram`'s bus-nested pins don't; `pin (NAME) {` vs `pin(NAME) {`;
  `timing () {` vs `timing() {`) -- a pin's/timing arc's own real
  header line is preserved verbatim whenever its name/shape didn't
  change, and only reformatted, preserving the file's own real spacing
  convention, when it genuinely did. Verified for real: byte-identical
  no-edit round-trip across all 97 real `.lib` files (700 real cells);
  real, driven edit round-trips confirmed correct with every other
  real pin/arc/cell in the file provably unchanged for: a pin
  direction/capacitance/function edit, a timing-arc field edit, a new
  pin, a deleted pin, a new timing arc, a deleted timing arc, and a
  real SRAM bus-nested pin edit (confirming the unspaced/unquoted
  convention survives a real edit, not just a no-op).
- **`openpdkcreator/ihp/gds.py`** -- real, bounded GDS structural
  extraction, via KLayout's own real Python API (`klayout.db`) --
  lazily imported (`_import_klayout_db`, `KLayoutUnavailable`), so
  every other command here (`inventory`/`lef`/`drc`/`cells`, none of
  which need it) keeps working in environments without it, including
  this project's own host (confirmed: `klayout` isn't installed there,
  only inside the IIC-OSIC-TOOLS container this project's own
  `start_eda_container.sh` launches -- a missing import raises a real,
  honest error, not a silently empty result). For each real top-level
  GDS structure: its own real bounding box in microns (via the file's
  own real database unit, `Layout.dbu`) and a real per-`(layer,
  datatype)` shape count -- `Cell.bbox()` is KLayout's own real,
  hierarchical bbox (includes child instances), not this module
  reimplementing geometry math; shape counts are direct, not flattened
  through instances. Real result against `sg13g2_stdcell.gds`: 84 real
  structures (matching LEF's own 84 macros), `sg13g2_a21o_1`'s real
  bbox `(-0.24, -0.22, 3.6, 4.17)` µm / 72 real shapes across 9 real
  layers; `sg13g2_io.gds` (69 MB) parses in under 0.1s -- no real
  performance concern even for the largest real file.
- **`openpdkcreator/ihp/cells.py`** -- aggregates one real cell's views
  across `libs.ref/<family>/*/` into one `CellViews` record, handling
  a real, confirmed structural fact: IHP's own families use *two*
  different real per-view file organizations for the same view kind --
  `sg13g2_io`/`sg13g2_stdcell` pack every cell into one combined file
  per view; `sg13g2_sram` instead ships one real file per hard macro
  (confirmed: 28 real `.cdl` files, one `.SUBCKT` each). Both handled
  without special-casing either, by scanning every real file under a
  view directory rather than assuming one. Real result: 84/46/28 real,
  LEF-backed top-level cells for stdcell/io/sram respectively (matching
  each family's own real macro count exactly); `sg13g2_sram`'s real
  netlists alone define **2338** real subckts once internal
  sub-elements are included (bitcells, sense amps, ... -- only 28 of
  which are the real, top-level hard macros), confirming the default
  "top-level only" filter is the right call, not arbitrary. GDS is
  real content (`gds_cell`, via `ihp/gds.py`) when `klayout.db` is
  importable, degrading to a presence-only flag (`gds_present`,
  distinguished from `None` vs. "genuinely nothing to find" via
  `KLayoutUnavailable`) when it isn't, never a silent gap; `sg13g2_pr`
  (GDS-only, confirmed) correctly indexes to zero real cells, not a
  bug.
- **`openpdkcreator/gui/cell_hub_view.py`** -- the **By Cell** tab
  (`CellHubView`): a family picker, a cell list (LEF/CDL/SPICE/
  Verilog/Liberty/GDS presence at a glance, a "Show internal sub-cells
  too" checkbox off by default), per-view **View** buttons that open
  the real source file scrolled and highlighted straight to that
  cell's real line range (`file_view_dialog.view_file_dialog`'s
  `focus_start_line`/`focus_end_line` parameters), and, for a selected
  cell with a real LEF macro, a **Pins** pane (`PinEditor`, shared with
  the LEF tab) editing that macro's real pins directly. `ihp/cells.py`'s
  `build_cell_index` takes an injectable `get_lef` hook so this tab
  parses through `App.get_parsed_lef` -- the exact same cache/objects
  the LEF tab uses, not an independent parse -- confirmed for real: a
  pin edited here is immediately visible (same `LefPin` object
  identity, not just equal values) on the LEF tab without switching
  away and back, and both save the same way. A macro-less internal
  sub-cell (no real LEF macro of its own -- common browsing
  `sg13g2_sram` with "show all" on) shows a plain "nothing to edit
  here" note in the Pins pane's place, confirmed not to crash. Also
  shows a real GDS structural summary line (bbox size + shape/layer
  counts, via `ihp/gds.py`) for the selected cell when `klayout.db` is
  importable -- a plain text line, not a raw file **View** (GDS is
  binary), degrading to an honest "present, but not parsed" note
  rather than silently showing nothing when it isn't. Verified for
  real, driven against the actual data: correct counts and view flags
  across all four real families, `sg13g2_sram`'s full 2338-row "show
  all" render in 0.18s (no real performance concern), the CDL/Verilog
  **View** buttons both land on and highlight the exact real
  `sg13g2_and2_1` block inside their much larger combined files, a real
  pin edit made here survives a save + simulated relaunch, and
  `sg13g2_a21o_1`'s real GDS summary line matches `ihp/gds.py`'s own
  directly-verified numbers exactly. **Edit ... Ports** buttons next
  to the CDL/SPICE/Verilog **View** buttons open a small modal
  (`port_dialog.edit_ports_dialog`) hosting `port_editor.PortEditor` --
  add/delete/rename a real port, edit its real direction (and, for
  Verilog, real bus width) -- parsing through the same kind of shared,
  App-owned cache as LEF pins (`App.get_parsed_netlist`/
  `get_parsed_verilog`), applied here from the start rather than
  rediscovered: confirmed for real that switching families and back
  reuses the same cached, possibly-edited `VerilogModule` object
  (identity-checked), not a silent re-parse that would have discarded
  the edit -- the exact bug class already found and fixed for LEF pins
  earlier this project.
- **`openpdkcreator/gui/port_editor.py`** -- `PortEditor`, a real port
  list + New/Delete Port + a Name/Direction[/Width] form, the same
  commit-on-switch pattern `PinEditor` uses -- duck-typed across CDL/
  SPICE's `NetlistPort` and Verilog's `VerilogPort` (structurally
  similar but not identical -- only Verilog has a real bus width) via
  a `port_factory` callback for New Port, rather than two near-
  identical widgets.
- **`openpdkcreator/ihp/netlist_writer.py`/`verilog_writer.py`** --
  real, open_pdks-format write-back for CDL/SPICE/Verilog ports.
  Unlike the other writers, there's no
  single stable per-entry line/range to patch in place cleanly (a real
  `.SUBCKT` header can wrap across `+`-continuations in a way that's
  awkward to token-patch), so both instead compare each cell/module's
  *current* port list against a **fresh re-parse** of the same real
  original file: unchanged -- the real original header/declaration
  text is kept byte-for-byte, wrapping and all; changed -- regenerated
  cleanly as a single real line (header) plus, for CDL, a fresh real
  `*.PININFO` line (inserted new if the cell had none at all -- e.g.
  every real `sg13g2_sram` CDL cell -- when a direction is assigned),
  or for Verilog, every real declaration line replaced with one fresh
  line per port at the position of the first original one. Verified
  for real against the actual downloaded data: **all 30 real `.cdl` +
  1 real `.spice` + 35 real `.v` files export byte-identical to their
  real originals with no edits**; real, driven round-trips for a CDL
  direction edit (through the real `*.PININFO` line), a new/deleted
  CDL port, a fresh `*.PININFO` insertion on a real SRAM cell that had
  none, a Verilog direction edit, and a real bus-width edit on the
  real multi-line-header SRAM module -- each confirmed to leave every
  *other* real cell/module in the file unchanged.
- **`openpdkcreator/ihp/text_utils.py`** -- one real, shared fix for
  all five writers above: `join_preserving_trailing_newline`. **A
  third real bug, found by `main.py export-full`'s own smoking-gun
  round-trip test at full-PDK scale, not by any single writer's own
  narrower per-file tests**: every writer unconditionally appended a
  trailing newline to its output, silently changing real byte content
  for the 21 real files (all of `sg13g2_sram`'s own Verilog modules)
  that don't actually end with one -- invisible to each writer's own
  test because that test's own comparison logic *also* normalized the
  real original's trailing newline before comparing, masking the exact
  same bug it should have caught. Fixed once, shared, re-verified
  clean across a real two-generation `export-full` round-trip of the
  complete ~744 MB IHP deck (orig-vs-A, A-vs-B, and orig-vs-B all
  perfectly identical, structurally and byte-for-byte).
- **`openpdkcreator/project_io.py`** -- program-format persistence for
  the editable domains above (DRC Rules/Magic Types/LEF pins/the
  Settings tab's project name), modeled on `OpenPDKCreator`'s own
  `rules_db/` (ADR 0002): a save/load layer completely separate from
  the real, downloaded `.tech`/`.lef`/`.drc` files, not a write-back
  into them. `File > Save Edits` (`Ctrl+S`) writes `saves/<pdk
  name>.yaml` (gitignored, alongside but independent from `data/` --
  `ihp/fetch.py` can delete/re-create `data/` wholesale, and these are
  the user's own authored edits, kept safe from that). A save, once it
  exists, takes precedence over the real just-extracted starting
  values for these domains on the next launch; `File > Reload from
  Real Files` explicitly discards both the in-memory edits and the
  save file, re-extracting fresh -- not automatic, since silently
  reverting a user's saved edits on every restart would defeat the
  point. `LefPin.ports`'s nested `LefPort` dataclasses need explicit
  reconstruction on load (`dataclasses.asdict` round-trips them to
  plain dicts; `TypeEntry`/`DesignRule` have no nested dataclasses and
  reconstruct via plain `**kwargs`). Verified for real, driven
  end-to-end against the actual downloaded data: edit a DRC rule's
  description, a Magic Type's name, a LEF pin's direction/use (once via
  the LEF tab's own form, once via the **By Cell** tab's `PinEditor`
  instance, confirming both write through to the same shared, App-owned
  object -- see the `cell_hub_view.py`/`app.py` entries above), and the
  Settings tab's project name (each through its own real form, not by
  mutating the dataclass directly -- doing that instead hit a real,
  instructive false-negative: the form's own commit-on-switch silently
  reverted the direct edit right back, since the still-loaded,
  unchanged form is authoritative for whichever row is currently
  selected), save, construct a **fresh** `App` against the same
  `pdk_root` (simulating a real relaunch), and confirm every edit
  survived, including the window title reflecting the restored project
  name; separately confirmed `Reload from Real Files` discards all of
  it (including resetting the project name to its placeholder) and
  deletes the save file for real.
- **`openpdkcreator/gui/settings_view.py`** -- the **Settings** tab
  (`SettingsView`): two visibly separate sections, **This Project**
  (an editable **Project name**, defaulting to a deliberately generic
  placeholder rather than the real PDK's own name so the two can never
  look identical before renaming; a read-only **Project directory** --
  this tool's own repo root, where `saves/` lives) and **Source PDK**
  (read-only **Original PDK name**/**Original PDK location** -- the
  real `pdk_root.name`/path, plus the real upstream URL it was fetched
  from, `ihp/fetch.py`'s own `REPO_URL`). Renaming the project updates
  the window title live and persists through `project_io.py`. Verified
  for real: the four values are confirmed genuinely distinct strings on
  a real, downloaded PDK (not accidentally the same path/name reused
  twice), and a rename survives a save + simulated relaunch.
- **`openpdkcreator/ihp/lef_writer.py`** / **`openpdkcreator/export.py`**
  -- real, open_pdks-format write-back for LEF pins, the first concrete
  piece of native write-back serialization (see Future Work). Never
  overwrites the real, downloaded source file -- `export.py` always
  writes to a new `export/<pdk name>/...` tree, mirroring each file's
  own real relative path under `pdk_root`. **Surgical patching, not
  full regeneration**: this project's LEF model doesn't capture every
  real LEF construct (port `RECT` *coordinates* -- only a count is
  tracked -- `PROPERTY`, `FOREIGN`, ...), so `lef_writer.py` re-reads
  the real *original* file fresh from disk and, using each pin's real
  source line range (`ihp/lef.py`'s new `start_line`/`end_line`), keeps
  every real interior line of an existing pin verbatim, substituting
  only its `DIRECTION`/`USE` lines and its own name in the
  `PIN`/`END` header/trailer -- **a real bug found and fixed while
  building this**: an earlier version regenerated a pin's block from
  only the fields this project models, which silently dropped real,
  unmodeled attributes (`ANTENNAMODEL`, confirmed present on real IHP
  pins) -- caught immediately by the very first correctness check
  (no-edit export must be byte-identical to the real original) failing
  against real data, not by inspection. A deleted pin's original text
  is omitted entirely; a brand-new pin (no real source line range) gets
  a freshly-generated block inserted before the macro's own real `END`
  line. Verified for real against the actual downloaded data: **all 32
  real `.lef` files export byte-identical to their real originals with
  no edits** (the strongest real correctness check available -- if the
  splicing logic touched anything it shouldn't, this would catch it),
  plus real, driven round-trips for an edited pin (value change +
  real `PORT` geometry preserved exactly), a brand-new pin, and a
  deleted pin, each re-parsed from the real export and checked against
  a fresh parse of the untouched original.
- **`main.py export-lef`** -- CLI export + verification: exports every
  real `.lef` file and reports how many came back byte-identical
  (always all of them with no edits made) -- a real, standalone
  correctness self-check runnable anytime, matching `main.py cells`/
  `gds`'s own style.
- **File > Export Edited LEF Files** (`app.py`) -- the GUI action:
  exports every real `.lef` file parsed this session (LEF tab or By
  Cell tab -- both route through the same `App.get_parsed_lef` cache)
  with any in-memory pin edits patched in. Verified for real, driven:
  edited a pin via the LEF tab's form, exported, re-parsed the real
  exported file, and confirmed the edit is there -- and confirmed a
  real `.lef` file never parsed this session is correctly *not*
  exported (nothing to write for a file with no possible edits).
- **`openpdkcreator/ihp/drc_writer.py`** -- real, open_pdks-format
  write-back for DRC Rules, extending native write-back serialization
  beyond LEF pins. `ihp/drc.py`'s own extraction already established
  a real, two-file split -- a rule's `rule_id`/`description` live in
  its real `.drc` Ruby script's own `result_var.output("ID",
  "description")` call; its `value` lives in the one real JSON config
  file's `drc_rules['KEY']` entry (the script itself never contains a
  literal numeric threshold, only a variable traced back to that JSON
  lookup) -- so write-back patches each field into its own real file,
  never conflating the two. **Surgical, character-offset-based
  patching**: `_locate` re-derives which real JSON key (if any) backs
  a rule's value, and the exact real `.output()` regex match, by
  re-running `ihp/drc.py`'s own extraction regexes directly (imported,
  not duplicated) against the rule's own real `source_provenance` --
  then only the exact substrings the id/description occupy are
  replaced, leaving everything else (surrounding Ruby code, other
  rules, comments, formatting) untouched. **A real, common wrinkle
  handled deliberately**: 61 of IHP's own real `.output()` calls have
  a real `"<section> : ..."` prefix before the description
  `DesignRule.description` actually keeps (`ihp/drc.py` splits on the
  first real `" : "`) -- write-back reconstructs the original prefix
  verbatim and splices only the (possibly-edited) suffix back in,
  rather than silently discarding that real prefix text for over a
  third of IHP's own real rules. **A second real bug found and fixed
  while building this, of the exact same shape as the LEF writer's
  `ANTENNAMODEL` one**: an earlier version always reformatted every
  referenced JSON value via `repr(float(...))`, even ones nobody
  edited -- which silently rewrote a real, confirmed case
  (`"Padb_b": 70.00`) to `70.0`, breaking the no-edit-is-byte-identical
  guarantee; fixed by comparing the real numeric value first and
  skipping the substitution entirely when nothing actually changed.
  Only rules with real, resolvable provenance can be written back --
  a hand-authored New Rule has no real source position, and is
  reported by `rule_id`, never silently dropped. Verified for real
  against the actual downloaded data: **all 27 real files (every `.drc`
  script with an extracted rule, plus the JSON config) export
  byte-identical to their real originals with no edits**; a value edit
  (`Act.a` 0.15 -> 0.20) patches only that one real JSON key, 377
  others untouched, and the `.drc` script itself stays untouched (no
  value lives there); a rule_id + description edit (on a real
  `" : "`-prefixed rule, `V1.b`) patches exactly the id and description
  substrings in the real `.drc` file, confirmed by diffing every line
  against the original; a hand-authored rule is correctly reported as
  skipped, not silently dropped.
- **`main.py export-drc`** / **File > Export Edited DRC Rules**
  (`app.py`) -- CLI and GUI actions, matching `export-lef`'s own shape:
  export every rule with real provenance, report byte-identical counts
  and any hand-authored rules skipped. Verified for real, driven:
  edited a rule's value via the real DRC Rules form, exported, and
  confirmed the real JSON config reflects it.
- **`openpdkcreator/ihp/magic_tech_writer.py`** -- real, open_pdks-format
  write-back for Magic Types, the third and final currently-editable
  domain (after LEF pins and DRC Rules). Each real type occupies
  exactly one real line (`[-]plane name,alias1,alias2` -- no block
  structure to navigate, unlike LEF's `PIN`/`MACRO` or DRC's multi-line
  `.output()` calls), so `ihp/magic_tech.py` gained the same real
  source-line tracking LEF already has (`TypeEntry.line_no`,
  `MagicTechnology.all_parsed_type_line_nos`), used exactly the same
  way: a deleted type's original line is omitted, a brand-new type is
  appended before the real `types` section's own closing `end`, and an
  existing type's line is regenerated from its current fields. **A
  real, defensive safety measure, not just an optimization**: since
  `ihp-sg13g2.tech` splices in four included fragment files
  (`cifout`/`cifin`/`drc`/`extract`) that would shift real line numbers
  in the combined, parsed view relative to the real file on disk, line
  tracking only activates for a real `types` section that appears
  *before* the file's own first real `include` statement
  (`_safe_prefix_line_count`) -- true for both of IHP's own real
  technologies, confirmed directly, but not assumed true in general;
  a real `types` section past that boundary would refuse to write
  back rather than risk patching the wrong real position in the wrong
  real file. **A real bug found and fixed while building this, the
  same shape as the LEF/DRC writers' own formatting bugs**: an early
  version always reconstructed a type's line with a single fixed
  space between plane and names, which silently collapsed real,
  confirmed column-aligned multi-space formatting (102 real lines in
  `ihp-sg13g2-GDS.tech` use more than one space there) even when
  nothing was edited -- caught immediately by the no-edit-is-
  byte-identical check failing against real data; fixed by preserving
  the real original separator whitespace exactly (and the real
  original indentation) for every existing type, substituting only
  the fields that can actually change. Verified for real against the
  actual downloaded data: **both real technologies' `.tech` files
  export byte-identical to their real originals with no edits**
  (247 real types combined); real, driven round-trips for an edited
  type (name/aliases/obsolete, with every other type confirmed
  unchanged against a fresh parse), a brand-new type, and a deleted
  type; and a real edit made via the GUI's own Types form, exported,
  and confirmed correct in the real `.tech` file.
- **`main.py export-magic-types`** / **File > Export Edited Magic
  Types** (`app.py`) -- CLI and GUI actions, matching `export-lef`/
  `export-drc`'s own shape: exports every real technology currently
  loaded (both `ihp-sg13g2` and `ihp-sg13g2-GDS`) with any in-memory
  Types edits patched in.
- **`export.export_full_pdk`** / **`main.py export-full`** -- a
  complete, real, standalone open_pdks-format PDK tree: every real
  file under `pdk_root` copied verbatim (`shutil.copytree`, so every
  file this project has no editor for -- GDS/docs/qa/everything -- is
  included, not just the small subset the other `export_*` functions
  above touch), with every real LEF/DRC/Magic-Types/CDL/SPICE/Verilog/
  Liberty file re-rendered on top through its own real writer, freshly
  parsed straight from `pdk_root` with no GUI session involved. Built
  specifically as a **smoking-gun round-trip fidelity test**: export
  the real IHP PDK once, then export *that output* again, and diff the
  two generations -- structurally identical would mean every real
  writer here is a truly faithful, lossless read-modify-write cycle
  across the *entire* real dataset, not just the hand-picked samples
  each writer's own tests already covered. **Run for real, twice,
  chained** (`export-full --pdk-root data/ihp-sg13g2/ihp-sg13g2 --dest
  A`, then `export-full --pdk-root A --dest B`) against the full real
  ~744 MB / 4900-real-file/symlink IHP deck: **found one real bug this
  way**, invisible to a plain content diff -- `shutil.copytree`'s own
  default (`symlinks=False`) *dereferences* a real symlink (IHP's own
  `libs.tech/ngspice/install.py -> ../xschem/install.py`) into a plain
  copy of its target, silently losing the real symlink structure
  (`diff -rq` alone reported zero differences, since it compares
  resolved content; only a structural diff, `diff -rq
  --no-dereference`, caught it). Fixed with `symlinks=True`. Re-run
  after the fix: **all three real comparisons -- original-vs-A,
  A-vs-B, and original-vs-B -- are completely identical**, structurally
  and byte-for-byte, confirmed via `diff -rq --no-dereference` (zero
  differences), matching total real file/symlink counts (4900 each),
  matching total real byte size (769,423,550 bytes each), and a
  permission-bits spot check. **Re-run again after Liberty write-back
  was added**: still completely identical across the full real deck,
  confirming `liberty_writer.py`'s own real bug fixes (see its own
  section above) hold at full-PDK scale, not just per-file.
- **`main.py export-liberty`** / **File > Export Edited Liberty
  Files** (`app.py`) -- CLI and GUI actions, matching
  `export-netlist`/`export-verilog`'s own shape: exports every real
  `.lib` file parsed this session (`App.get_parsed_liberty`'s own
  cache for the GUI; every real file, freshly parsed, for the CLI and
  `export-full`) with any in-memory pin/timing-arc edits patched in.

Native write-back serialization is now complete for every currently
structured-editable domain -- LEF pins, DRC Rules, Magic Types,
CDL/SPICE/Verilog ports, and Liberty pin/timing-arc data -- and
independently re-verified faithful across the entire real PDK via
`main.py export-full`'s own smoking-gun round-trip test, not just
per-writer sample tests. Everything still read-only (Layers, Magic
Tech's other five domains, GDS) has no write-back for the same reason
it has no editor yet -- see Future Work.
- **`openpdkcreator/gui/tools_view.py`** -- the **Settings > Tools**
  sub-tab (`ToolsView`): real, live status of every tool in
  `eda_tools.TOOL_REGISTRY` (found/missing, real detected version and
  path), install guidance shown as read-only text (docs URL + the
  real, exact package-manager/user-local command -- never auto-run,
  matching `eda_tools.py`'s own "opt-in, never silently privileged"
  install philosophy), and a **Launch** button
  (`eda_tools.resolve_launch`, the same real, non-privileged
  `subprocess.Popen` the CLI's own `launch` command uses). No new
  detection/install/launch logic -- a thin GUI wrapper around
  `eda_tools.py`'s own existing, already-real functions, so the CLI and
  GUI can never drift apart. Verified for real, driven: the real tool
  list renders with real found/missing status for this environment,
  and the detail pane renders real install guidance text for a
  selected tool without error.
- **`start_eda_container.sh`** -- adapted from `OpenPDKCreator`'s own
  script of the same name, not copied verbatim: its own container name
  and ports (`iic-osic-tools_openpdkcreator_uid_*`, webserver 8081, VNC
  5902 -- `IIC-OSIC-TOOLS/start_vnc.sh` only falls back to its own
  defaults when those env vars are unset, confirmed by reading it
  directly) so both projects' containers coexist without colliding
  (confirmed by running both at once for real); mounts
  `openPDKcreator/` itself straight to `/foss/designs`, not its parent
  (no reason to expose the rest of the monorepo). `./start_eda_container.sh
  --gui` verified for real: container created, `main.py gui` launched
  inside it, real `data/` visible bind-mounted through, sibling
  project's own container unaffected.

## Future work

The stated end goal is much bigger than this first increment: an
application that can create/edit/generate arbitrary PDK file types
(Magic technology files, KLayout DRC decks, LEF, GDS, Liberty, SPICE
models, ...), not just read/display layers. Concretely, still open:

- `cifinput`'s own real geometry-boolean recipe blocks (`layer`/
  `templayer` ... `and`/`and-not`/`grow`/`shrink`/`labels`/`copyup` --
  the section's two cleanly tabular real facts, `ignore` statements and
  the standalone `calma` layer-hint table, are now extracted; the
  recipes themselves still aren't, since their *first* line alone
  doesn't reduce to one honest, standalone fact the way `cifoutput`'s
  *final* `calma` line does -- see `magic_tech.py`'s own docstring),
  `extract`'s own remaining real constructs (`devresist`/`contact`/
  `antenna`/`disconnect`/`substrate` -- its real parasitic-capacitance
  coefficients and `device` statements are now done, see
  `magic_tech.py`'s own docstring), the much larger real remainder of
  `drc` (`surround`/`edge4way`/`cifmaxwidth`/`variants`/`widespacing`/
  `angles`/`cifwidth`/`cifspacing`/... -- `width`/`spacing`/`maxwidth`
  are done; the remainder's own real shapes are less uniform -- variable
  argument counts, nested real layer-boolean expressions, or, for
  `variants`, a real conditional-scoping directive rather than a check
  at all -- so extending the `width`-style pattern to them isn't a safe
  reuse), and Liberty's own real lookup-table
  sub-groups (`cell_rise`/`cell_fall`/`rise_transition`/
  `fall_transition`, each its own nested `index_1`/`index_2`/`values`
  multi-dimensional data -- deliberately left unparsed even though
  pin/timing-arc scalar data is now done, same "bounded, not a full
  parser" precedent as everywhere else) -- no generic parser for either
  of these exists yet. (Real GDS content -- bbox/shape counts, not full
  geometry -- is done: `ihp/gds.py`, via `klayout.db`. Real
  `compose`/`connect` sections, and the dominant `width`/`spacing`
  patterns in `drc`, and `resist`/`planeorder` in `extract`, are also
  done -- see `magic_tech.py`'s own docstring for exact real coverage.
  LEF's own real `VIA`/`ViaRULE` via-stack geometry is also done:
  `ihp/lef.py`, displayed read-only in the LEF tab's own **Vias**
  sub-tab. Liberty's own real pin/timing-arc scalar data --
  direction/capacitance/function per pin, related_pin/timing_type/
  timing_sense/when per
  timing arc -- is also done: `ihp/liberty.py`.)
- Wider KLayout DRC-deck coverage: `ihp/drc.py` now extracts two
  reliable patterns -- `width()`/`space()`/`sep()` and `.enclosed()` --
  -> `.output()` (75 real rules total); the other 86 real,
  honestly-skipped constructs are multi-step composite/derived checks
  (angle/acute-corner checks, antenna-ratio accumulation, density
  windows, ...) with no single reliable, generic pattern left to
  extract.
- Native write-back serialization: **done for every currently
  structured-editable domain** -- LEF pins (`ihp/lef_writer.py`,
  verified against all 32 real files), DRC Rules (`ihp/drc_writer.py`,
  verified against all 27 real files with an extracted rule), Magic
  Types (`ihp/magic_tech_writer.py`, verified against both real
  technologies' `.tech` files), CDL/SPICE/Verilog ports
  (`ihp/netlist_writer.py`/`ihp/verilog_writer.py`, verified against
  all 30 real `.cdl` + 1 real `.spice` + 35 real `.v` files), and
  Liberty pin/timing-arc data (`ihp/liberty_writer.py`, verified
  against all 97 real `.lib` files, 700 real cells) -- every one
  byte-identical with no edits, plus real, driven edit round-trips,
  and independently re-verified faithful across the *entire* real PDK
  at once via `main.py export-full`'s own smoking-gun round-trip test
  (`export.py`, `File > Export Edited ...`, `main.py
  export-lef`/`export-drc`/`export-magic-types`/`export-netlist`/
  `export-verilog`/`export-liberty`). What's left is everything that's
  still read-only in its own structured view -- Layers and Magic
  Tech's other five domains -- for the same reason: no editor -> no
  write-back path to build. GDS stays read-only by design (real
  structural info only, no geometry-editing feature exists or is
  planned this pass); Liberty's own real lookup-table sub-groups stay
  unmodeled for the same bounded-scope reason as everywhere else, not
  because a pin/timing-arc editor doesn't exist anymore.
- Re-add "pre-pointed" Magic/KLayout launch guidance in
  `eda_tools.py` once a real mapping to IHP's actual multi-file tech
  setup (6 real `.tech` files, not 1) is designed, not guessed.
- A **Simulation** top-level GUI group (ngspice/xschem/Qucs-S models
  and schematics), matching the **Technology**/**Cells** groups'
  pattern -- still inventory-only today (see the Overview tab), no real
  per-format parser exists yet.
- Revisit copying vs. sharing code with `OpenPDKCreator` if the two
  projects' core models (`Layer`, the tool registry) diverge enough to
  need reconciling.

## License

Apache-2.0 (see `LICENSE`) -- matching `OpenPDKCreator`, the project
some of this code was copied from. IHP-Open-PDK itself (fetched
locally, never committed here) is also Apache-2.0 -- see
`github.com/IHP-GmbH/IHP-Open-PDK`'s own `LICENSE`.

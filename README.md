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
  each of three much harder mini-rule-language sections:
  - `cifoutput`: every real `layer NAME ... calma L D` recipe -- a
    genuine Magic-type-name to GDS-layer/datatype mapping.
  - `drc`: the two dominant, cleanly tabular real statement kinds,
    `width`/`spacing` -- 166 of the real section's statements (65/65
    `width`, 101/102 `spacing`; the one real miss is a genuine defect
    in IHP's own file, a message string missing its closing quote,
    confirmed by direct inspection). Real values converted to microns
    via an empirically-confirmed `/1000` factor, cross-checked against
    three independent, already-extracted real KLayout DRC rules sharing
    the same real rule ID (`Act.a`: `0.15` both ways; `Gat.a`: `0.13`
    both ways; `NW.b`: `0.62` both ways) -- not from Magic's own
    documented unit spec, which this pass had no authoritative local
    source to confirm against, but a real, repeatable, cross-checked
    fact, not a guess.
  - `extract`: real per-layer sheet resistance (`resist`, 30/33 real
    lines -- milliohms/square, the other 3 are real non-numeric config
    entries, not a parsing gap) and real plane ordering (`planeorder`,
    14/14).

  Real `include` resolution confirmed: `ihp-sg13g2.tech` splices in 4
  fragment files (`cifout`/`cifin`/`drc`/`extract`) as one logical
  technology; `ihp-sg13g2-GDS.tech` is a second, genuinely separate
  technology with its own header. `cifinput`/`lef`/`mzrouter`/`wiring`/
  `router`/`plowing`/`plot`, and everything in `drc`/`extract` beyond
  the patterns above (`surround`/`edge4way`/`device`/505 real
  parasitic-capacitance-coefficient lines/...) are honestly reported as
  not-parsed-this-pass, never silently dropped
  (`MagicTechnology.unparsed_sections`, `MagicTechnology.drc_skipped`).
  `cifinput` specifically was left for its own future pass rather than
  reusing `cifoutput`'s pattern: its real recipes are geometry-boolean
  chains (`and`/`and-not`/`grow`/`shrink`) whose *first* line alone
  isn't a complete, honest fact the way `cifoutput`'s *final* `calma`
  line is.
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
  and aren't shown standalone) over ten sub-tabs, one per real, parsed
  data domain (Planes/Types/Contacts/Aliases/Styles/CIF Layers/
  Compose/Connect/**DRC (Magic)**/Extract -- the last four new, real
  content from `ihp/magic_tech.py`'s own `compose`/`connect`/`drc`/
  `extract` extraction described above), plus a **View File** button.
  **Types is editable** -- a list + form pane (Plane/Name/Aliases/
  Obsolete), New/Delete Type, the same commit-on-switch pattern as
  everywhere else; every other domain stays read-only for now (each
  would need its own form). Verified for real, driven against the
  actual downloaded data: all ten sub-tabs' row counts match
  `magic-tech`'s own CLI output exactly (39 compose/20 connect/166 DRC
  checks/30 resist), switching technologies correctly reloads every
  sub-tab, editing a real type's name/aliases/obsolete commits
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
  geometry) are deliberately not parsed -- names recorded, bodies
  honestly skipped. Every value hand-checked against the real source:
  `sg13g2_a21o_1`'s 6 real pins (name/direction/use/rect-count each),
  a real SRAM macro's 113 real pins, `sg13g2_tech.lef`'s 19 real
  layers/70 real vias/6 real via-rules. Also tracks each real
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
  the **full** real deck: 42 real `.drc` files, not a sample). Real
  result: **61 real design rules** extracted, all 61 with a real,
  resolved numeric value (100% resolution against the real JSON config
  -- hand-checked: `M1.a`'s `0.16` matches both the real
  `sg13g2_tech_default.json` and the real source line,
  `rule_decks/beol/5_16_metal1.drc:31`), and **94** composite/derived
  constructs honestly reported as not-auto-extracted, never dropped
  silently. One real, interesting finding worth noting: some real rule
  IDs themselves contain a literal Ruby string-interpolation template
  (`M#{met_no}.a`, from a real per-metal-layer loop in the source) --
  captured verbatim, not silently mangled.
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
- **`openpdkcreator/ihp/netlist.py`/`verilog.py`/`liberty.py`** -- real,
  deliberately lightweight "cell boundary" detectors: real
  `.subckt`/`.ends` pairs for CDL/SPICE (case-insensitive -- CDL's real
  files use `.SUBCKT`/`.ENDS`, SPICE's use lowercase, the same lesson
  as `lef.py`'s `Via`/`ViaRULE` finding), real `module`/`endmodule`
  pairs for Verilog, and real, brace-depth-counted `cell (NAME) { ...
  }` groups for Liberty (unlike the other three, a Liberty cell nests
  further real groups inside it, so a fixed closing keyword doesn't
  exist -- confirmed by reading the real file). Each is real, bounded
  scope: cell name + real source line range only, never a full
  netlist/behavioral/timing parser. Verified for real: all three found
  exactly 84 real cells in `sg13g2_stdcell`'s combined files, matching
  LEF's own 84 macros exactly.
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
  directly-verified numbers exactly.
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

- `cifinput` (Magic's own real GDS-import geometry-boolean mini
  language -- deliberately not attempted alongside `compose`/`connect`/
  `drc`/`extract`, since its recipes don't reduce to one honest,
  standalone fact the way `cifoutput`'s final `calma` line does -- see
  `magic_tech.py`'s own docstring), the much larger real remainder of
  `extract` (505 real parasitic-capacitance-coefficient lines --
  `defaultoverlap`/`defaultsideoverlap`/`defaultareacap`/
  `defaultperimeter`/`defaultsidewall` -- plus `device`, its own real
  transistor-model mini-language), the much larger real remainder of
  `drc` (`surround`/`edge4way`/`maxwidth`/`cifmaxwidth`/`variants`/...
  -- `width`/`spacing` are done), Liberty's own real pin/timing-arc data
  (still only real cell *boundaries* -- `liberty.py`), and LEF's own
  `VIA`/`ViaRULE` via-stack geometry -- no generic parser for any of
  these exists yet. (Real GDS content -- bbox/shape counts, not full
  geometry -- is done: `ihp/gds.py`, via `klayout.db`. Real
  `compose`/`connect` sections, and the dominant `width`/`spacing`
  patterns in `drc`, and `resist`/`planeorder` in `extract`, are also
  done -- see `magic_tech.py`'s own docstring for exact real coverage.)
- Wider KLayout DRC-deck coverage: `ihp/drc.py` only extracts the one
  reliable `width()/space()/sep()` -> `.output()` pattern (61 real
  rules); the other 94 real, honestly-skipped constructs are composite
  checks (`.enc()`, multi-step derived regions, ...) with no reliable,
  generic pattern to extract yet.
- Native write-back serialization: **LEF pins are done** -- real,
  surgical, line-range-targeted write-back into real `.lef` text
  (`ihp/lef_writer.py`/`export.py`, `File > Export Edited LEF Files`/
  `main.py export-lef`), verified against all 32 real files
  (byte-identical with no edits; real edit/new-pin/deleted-pin
  round-trips). **DRC Rules and Magic Types are not** -- both are
  genuinely *structured*-editable (add/edit/delete through a real
  form, not raw text) and persist across a relaunch (`project_io.py`,
  `saves/<pdk name>.yaml`), but that's still a separate program
  format, not a write into the real, on-disk `.drc`/`.tech` file
  itself. Each needs its own real design pass, harder than LEF's:
  Magic Types would need the same surgical, line-range approach
  extended to `magic_tech.py` (which doesn't track source lines yet);
  DRC Rules would need to patch a real KLayout Ruby DSL script (a
  `.output()` call's own real JSON-config-referenced value), a
  materially different real file format from LEF's block-structured
  text. Layers/Magic Tech's other domains/CDL/SPICE/Verilog/Liberty
  port and cell-boundary data (real boundaries only, no per-port model
  to edit yet) stay read-only in their own structured views for the
  same reason DRC Rules/Magic Types aren't write-back-capable yet (no
  write-back path -> no reason to build a form there first).
- Re-add "pre-pointed" Magic/KLayout launch guidance in
  `eda_tools.py` once a real mapping to IHP's actual multi-file tech
  setup (6 real `.tech` files, not 1) is designed, not guessed.
- A **Simulation** top-level GUI group (ngspice/xschem/Qucs-S models
  and schematics), matching the **Technology**/**Cells** groups'
  pattern -- still inventory-only today (see the Overview tab), no real
  per-format parser exists yet.
- Extending By Cell's editing beyond pins: CDL/SPICE/Verilog currently
  only expose a cell name + flat port-name list (no per-port direction/
  type model exists to edit -- see `ihp/netlist.py`/`verilog.py`'s own
  docstrings), and Liberty only real cell *boundaries*, no timing data
  -- each would need its own real, structured model first, the same way
  `ihp/lef.py`'s `LefPin` already exists for pins.
- Revisit copying vs. sharing code with `OpenPDKCreator` if the two
  projects' core models (`Layer`, the tool registry) diverge enough to
  need reconciling.

## License

Apache-2.0 (see `LICENSE`) -- matching `OpenPDKCreator`, the project
some of this code was copied from. IHP-Open-PDK itself (fetched
locally, never committed here) is also Apache-2.0 -- see
`github.com/IHP-GmbH/IHP-Open-PDK`'s own `LICENSE`.

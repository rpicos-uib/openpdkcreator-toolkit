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
`magic/` has 35 files including 6 real `.tech` files (`ihp-sg13g2.tech`,
`ihp-sg13g2-{GDS,cifin,cifout,drc,extract}.tech` -- the technology is
genuinely split across purpose-specific files, not one monolithic
`.tech`); `klayout/` has 548 files including a real,
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

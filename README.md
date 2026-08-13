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
python3 main.py gui          # Inventory + Layers tabs (needs a real X11/Xvnc display)
```

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

## Future work

The stated end goal is much bigger than this first increment: an
application that can create/edit/generate arbitrary PDK file types
(Magic technology files, KLayout DRC decks, LEF, GDS, Liberty, SPICE
models, ...), not just read/display layers. Concretely, still open:

- Deep parsers for Magic `.tech`/DRC Ruby DSL, LEF, GDS, Liberty, and
  the real KLayout DRC decks -- each a real, separate body of work; no
  generic parser for any of them exists anywhere in this codebase yet.
- Editing/creating/generating PDK content, not just reading it.
- Re-add "pre-pointed" Magic/KLayout launch guidance in
  `eda_tools.py` once a real mapping to IHP's actual multi-file tech
  setup (6 real `.tech` files, not 1) is designed, not guessed.
- Revisit copying vs. sharing code with `OpenPDKCreator` if the two
  projects' core models (`Layer`, the tool registry) diverge enough to
  need reconciling.

## License

Apache-2.0 (see `LICENSE`) -- matching `OpenPDKCreator`, the project
some of this code was copied from. IHP-Open-PDK itself (fetched
locally, never committed here) is also Apache-2.0 -- see
`github.com/IHP-GmbH/IHP-Open-PDK`'s own `LICENSE`.

# openPDKcreator

**Final objective: a wizard to edit and create an open PDK, generally
-- not specific to any one process.** IHP's real SG13G2
(`github.com/IHP-GmbH/IHP-Open-PDK`, Apache-2.0) is the *current
model* this is being built and verified against, not the permanent
target -- a real, complete PDK instead of a toy example, so every
parser/editor here is proven against real, messy, full-scale data from
day one. It will eventually point at other real PDKs too; keep that in
mind before adding anything that only makes sense for IHP specifically.
The internal parsing/writing package used to be named `ihp/` for
exactly that reason -- a naming leftover from when this only targeted
one real PDK -- and has since been renamed to **`pdklib/`**
(`openpdkcreator.pdklib`); every real reference throughout this
README/codebase was updated along with it. The GitHub repo itself was
renamed the same way, from `openpdkcreator-ihp-template` to
**`openpdkcreator-toolkit`** (`github.com/rpicos-uib/
openpdkcreator-toolkit`) -- `openpdkcreator` alone was already taken by
the separate, sibling project linked just below. Real, external
references to the actual IHP PDK/company itself (`ihp-sg13g2`,
`IHP-GmbH`, the real, downloaded deck) are unaffected by either
rename, and are kept deliberately, not scrubbed -- **IHP's real SG13G2
PDK is still the real template/reference deck this whole project is
built and verified against**, exactly as stated above; only the
internal module namespace and the repo's own name changed, not what
this project is actually grounded in.

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
python3 main.py ngspice      # real ngspice .lib model-card summary: .model/.subckt statements
python3 main.py xschem       # real xschem .sym symbol summary: device type + pin list
python3 main.py xschem-sch   # real xschem .sch schematic summary: instances/pins/wires
python3 main.py qucs         # real Qucs-S component .xml/symbol .sym summary
python3 main.py export-qucs-sym        # real, patched Qucs-S .sym write-back to export/ (byte-identical with no edits)
python3 main.py export-qucs-component  # real, patched Qucs-S component .xml write-back to export/ (byte-identical with no edits)
python3 main.py user-models  # list user_models/ Verilog/Verilog-A modules and their real cell links
python3 main.py drc          # real KLayout DRC-deck rule extraction summary
python3 main.py cells        # real per-cell view aggregation, one real family at a time
python3 main.py gds          # real GDS structural summary (bbox/shape counts) -- needs klayout.db
python3 main.py export-lef   # real, patched .lef write-back to export/ (byte-identical with no edits)
python3 main.py export-drc   # real, patched DRC-rule write-back to export/ (byte-identical with no edits)
python3 main.py export-magic-types   # real, patched Magic Types write-back to export/ (byte-identical with no edits)
python3 main.py export-netlist   # real, patched .cdl/.spice port write-back to export/ (byte-identical with no edits)
python3 main.py export-verilog   # real, patched .v port write-back to export/ (byte-identical with no edits)
python3 main.py export-liberty   # real, patched .lib pin/timing write-back to export/ (byte-identical with no edits)
python3 main.py export-layers    # real, patched .lyp write-back to export/ (byte-identical with no edits)
python3 main.py export-xschem-sym  # real, patched xschem .sym pin write-back to export/ (byte-identical with no edits)
python3 main.py export-xschem-sch  # real, patched xschem .sch instance/wire write-back to export/ (byte-identical with no edits)
python3 main.py export-full --dest DIR   # a complete, standalone PDK tree -- round-trip fidelity testing
python3 main.py --pdk-root DIR wizard --name "My PDK"   # start a new PDK project from the CLI, no GUI needed
python3 main.py gui          # PDK / Settings tabs (needs a real X11/Xvnc display)
```

`main.py --help` lists every one of the above with a one-line description;
`main.py <command> --help` (e.g. `main.py wizard --help`) shows that
command's own options -- both come straight from `argparse`'s own real
`help=` text, so they can never drift from what's actually implemented.

`wizard` is the CLI equivalent of the GUI's own **File > Create a New
PDK.../Create a Blank PDK...** -- no Tk/display needed. `--pdk-root DIR`
(the same global option every other command already takes, just used here
as the *destination* rather than an existing PDK to read) is where the new
PDK is created; `--name` is saved as the project's own display name and
(slugified) as the Layers/Magic Tech/LEF skeleton files' technology name;
add `--blank` for the bare `libs.tech`/`libs.ref` shape instead of the
default skeleton. It also generates the real, sourceable shell-env script
(same `pdklib/shell_env.py` Settings > Environment already exposes in the
GUI) -- `--env save` (default) writes `shell_env/pdk_env.sh` and prints its
path, `--env print` prints only the raw script to stdout (everything else
goes to stderr) so it can be sourced directly, e.g.:

```
source <(python3 main.py --pdk-root DIR wizard --name "My PDK" --env print)
```

`--open-gui` opens the GUI on the new project immediately afterward.

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

## Testing

`tests/` holds every real, driven integration test accumulated across
this project's own development -- each builds a real `App` (Tk),
drives real GUI actions, and asserts against real, parsed data or real
exported file text; no mocks of this project's own code. They only run
*inside* the IIC-OSIC-TOOLS container (`tkinter`/the real EDA
toolchain/the real, downloaded IHP data all live there, not on the
bare host):

```bash
podman exec -e DISPLAY=:1 <container-name> bash -lc 'bash tests/run_all.sh'
```

(the outer `bash -lc` matters -- see `tests/README.md` for a real,
confirmed case where skipping it silently hides an installed tool from
`eda_tools.py`'s own detection, hanging a test on an unmockable modal
dialog rather than failing cleanly.)

See `tests/README.md` for what each test needs, which ones exercise a
throwaway `/tmp/` PDK versus the real, downloaded one, and the shape
to follow when adding a new one.

## GUI structure

**Wizard** is the first tab shown, and its own top-level tab (not
nested inside **PDK** -- moved there deliberately so it's the very
first thing a new user sees, before any per-domain tab) -- a guided
flowchart (`gui/pdk_wizard_view.py`) laying out every real domain below
as a diagram:
starting from the real layout definition (**Layers**) at the top,
forking into a **Digital** path (Verilog / Liberty / CDL-SPICE, all
surfaced in **By Cell**) and an **Analog / Memristor** path (**User
Models** Verilog-A, **xschem Symbols/Schematics**, **Qucs-S Symbols/
Components**, **ngspice Models**), both converging back into **By
Cell**, then **GDS**, then **Export / Package**. Clicking a node shows
a detail panel (what it is, what it means for a from-scratch
**memristor** device specifically, and its real, live status computed
directly from whichever `pdk_root` is currently loaded -- a cheap
directory glob, never a full parse) plus a **Go to Tab** button
(`App.goto(*path)`, walking down as many nested `ttk.Notebook` levels
as needed) that jumps straight there. Every node also carries a
**hover** tooltip (no click needed) showing that exact same "what this
step is supposed to accomplish" text -- `gui/tooltip.py`'s new
`CanvasItemTooltip`, a sibling of the plain-widget `Tooltip` used
elsewhere (see the Library Manager section below) built specifically
for canvas-drawn items, which have no `winfo_rootx` of their own to
position a popup from -- it takes the triggering `<Enter>` event's
mouse position instead.

A real, honest gap is surfaced both as a legend color and per node.
**Layers, Magic Tech, DRC Rules, LEF, xschem Symbols/Schematics, and
Qucs-S Symbols/Components all support creating a brand-new file from
inside this GUI today** -- each domain's own file picker/toolbar
gained a **New .lyp File...**/**New .tech File...**/**New DRC
Deck...**/**Create File** action (`pdklib/layers.py`'s
`create_new_lyp_file`, `pdklib/magic_tech.py`'s `create_new_tech_file`,
`pdklib/drc.py`'s `create_new_drc_deck`, `pdklib/lef.py`'s
`create_new_lef_file`, plus xschem/Qucs-S's own already-existing ones)
that writes a real, minimal, valid skeleton -- an empty
`<layer-properties>` root, a `tech`/`version` header plus empty
Types/Planes/Contacts/Aliases sections, an empty DRC deck, or an
empty-library `.lef` -- genuinely usable immediately afterward, not
just a stub: **New Layer**/**New Type**/**New Plane**/**New
Contact**/**New Alias**/**New Rule** and a real export all work
against a skeleton the same as against a real, downloaded file.
**LEF** now also supports a whole new **MACRO**, not just a valid empty
*library*: the LEF Macros sub-tab's own **New Macro...** action adds a
real, brand-new, empty macro (pins added afterward through the same
**New Pin** flow an existing macro already uses); `pdklib/lef_writer.py`'s
`render_lef_file` renders it as a whole, freshly-generated block,
appended after every real, existing macro on export (`ORIGIN`/`SITE`
still aren't modeled -- real, separate future work). **DRC Rules' New
Rule is deliberately partial**: a hand-authored rule is genuinely exportable
-- real, *generated* KLayout DRC Ruby into a separate, tool-owned
`custom_rules.drc`, not just metadata -- but only for the three
`check_type`s with a real, single-method shape this project knows how
to emit (`min_width`/`min_spacing`/`min_enclosure`, the same three
`pdklib/drc.py`'s own extractor already recognizes coming the other way);
every other `check_type`, or a rule referencing a layer name with no
matching real `Layer`/GDS layer-datatype, still can't be written back
-- reported by rule ID and reason in the status line, never silently
dropped. Every remaining domain -- Verilog, Liberty, CDL/SPICE,
ngspice Models, and User Models' own `.va`/`.v` files -- requires a
real file to already exist on disk (hand-placed from a
template/reference PDK, or written in an external editor) before this
tool can load and edit it; nothing here pretends otherwise. A
from-scratch memristor PDK genuinely starts smallest at **User
Models** (write a `.va` compact model, drop it under
`user_models/veriloga/` -- no template needed, and `pdklib/cells.py`'s
own By Cell aggregation picks it up automatically by name) and the
xschem/Qucs-S symbol editors (draw a device symbol from nothing), then
grows outward through the newly-creatable Layers/Magic Tech/DRC
Rules/LEF skeletons above.

Tabs are grouped by what they represent, not left flat -- and, one
level up, **everything actually about the PDK's own content lives
under a single top-level PDK tab**, deliberately separate from
**Settings** (project naming/tool config, not PDK content itself, kept
outside so it doesn't compete for space with the actual PDK-authoring
tabs; **Wizard**, see above, is a third top-level tab of its own, for
the same reason -- a new user should see it before anything else, not
after opening **PDK**). Inside **PDK**: **Overview**
(the real, per-tool file inventory, spanning every domain including
ones with no dedicated view yet), **Technology** (process/technology-
definition data -- **Layers**, **Magic Tech**, and **DRC Rules** as
sub-tabs, one per tool that defines it), **Cells** (real cell/macro
data -- **LEF** and **By Cell** as sub-tabs), **Library Manager** (a
Cadence-style Libraries/Cells/Views browser spanning every domain at
once -- see its own section below), **Simulation** (**ngspice
Models** -- real `.model`/`.subckt` statements; **xschem** -- a
**Symbols** sub-tab (a real symbol's own device-attribute block,
read-only; an **editable** real pin list; and a real, interactive
**Graphical** canvas) and a **Schematics** sub-tab (**editable** real
component instances -- name, and a real pin instance's own net label;
a real, read-only Pins summary; **editable** real wire labels; and its
own real **Graphical** canvas, which also supports placing brand-new
instances/wires); **Qucs-S** -- a **Components** sub-tab (real device
definitions: models, read-only; **editable** real Parameter
default_value/equation) and a **Symbols** sub-tab (**editable** real
drawn-geometry ports -- no real port names, just position/type/angle,
a genuinely different tag syntax from xschem's own `.sym` -- plus its
own real **Graphical** canvas); **User Models** -- user-authored Verilog/Verilog-A
modules under `user_models/`, editable link to a real cell). That's
everything inside **PDK**. **Settings** itself sits alongside it, its
own separate top-level tab -- **General** (project name/directory,
source-PDK provenance), **Tools** (real per-tool install/PATH status),
and **Environment** (the generated shell-env script) as its own
sub-tabs. **Technology**/**Cells**/**Simulation** are the pattern a
future sub-tab would repeat once a real parser exists for a
still-unparsed domain.

**By Cell** is the hierarchical, cell-centric view: pick one real
cell, in one place see which of its real views (LEF/CDL/SPICE/
Verilog/Liberty/GDS, plus a **User** column counting any linked
user-authored Verilog/Verilog-A model) actually exist -- each column
also shows a `+` instead of `✓` for a project-authored view registered
via the Library Manager with no real counterpart -- jump straight
to that cell's own real block inside each, and **edit its real LEF
pins directly** in a **Pins** pane -- the exact same in-memory macro/pins the LEF tab's own
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
families and back never silently discards an in-progress edit. A
**User Models** listbox (double-click to view the real source file)
lists any user-authored Verilog/Verilog-A module connected to the
selected cell -- by plain name match or an explicit link, both set up
from **Simulation > User Models** -- and a wholly new, user-defined
cell name (not present in the real PDK at all) still gets its own row
here, so authoring a brand-new cell's model doesn't require first
faking a real view for it.

**Library Manager** is a Cadence-style Libraries | Cells | Views
browser (`pdklib/library_index.py`/`gui/library_manager_view.py`),
spanning every real domain at once, not just `libs.ref/`'s own six
(unlike **By Cell**, it also shows xschem Symbols/Schematics and
Qucs-S Symbols/Components). **A real design decision, not a default**:
new, project-authored libraries are tracked in a small, real,
committed index (`library_index.yaml` at the project root) rather than
forced into a directory convention mirroring `libs.ref/<family>/` --
because real family naming is *already* inconsistent across this
PDK's own real tool domains (`libs.ref/sg13g2_stdcell`, singular, vs.
`libs.tech/xschem/sg13g2_stdcells`, plural, with no `_io`/`_sram`
xschem directory at all; `libs.tech/qucs-s/symbols/` has no per-family
split whatsoever), so mirroring it would have bought nothing real.
Cross-domain cell matching goes by cell **name** (file stem)
instead, the same real pattern the existing GDS matching already used.
**New Library...**/**New Cell...** register a name; **Create** writes
a real, minimal, valid new file for the seven view kinds with genuine
create-from-scratch support (xschem Symbol/Schematic, Qucs-S
Symbol/Component, **Verilog**, **Verilog-A**, and **Magic Layout**
(`.mag` -- see below) -- the same real limit as everywhere else in this
project for the rest: LEF/CDL/SPICE/Liberty writers all explicitly
refuse a brand-new entry) to a real, tracked `libraries/<library>/`
directory -- except Verilog/Verilog-A, which default instead into the
already-established `user_models/{verilog, veriloga}/` convention (see
**Simulation > User Models** below), giving a newly-created one free
integration with its own "User Models" column and OSDI-snippet
generation. A newly-created `.mag` file declares whichever real Magic
technology is actually active for this PDK (`_default_tech_name()`,
`gui/library_manager_view.py`) -- picked as the *shortest* stem among
every real `.tech` file found under `libs.tech/magic/`, since real IHP
data names its per-domain fragment files `<main>-<suffix>.tech`
(confirmed empirically, see the changelog entry above for the real bug
this caught). **If the cell being created for
already has another known view with real pins** -- LEF first (the most
authoritative real physical source), then an xschem symbol, then an
existing Verilog/Verilog-A module of the same name
(`pdklib/library_index.py`'s own `infer_ports_for_cell`) -- the new
module's own port declaration is pre-populated with those real pins
(direction normalized from either real vocabulary -- LEF's uppercase
`INPUT`/`OUTPUT`/`INOUT`, xschem's lowercase `in`/`out`/`inout` -- down
to Verilog's own keywords) instead of an empty template. A generated
Verilog-A file declares every port `inout`+`electrical` (real Verilog-A
has no directional port concept) and opens with a real
`` `include "disciplines.vams" `` -- confirmed to compile via a live
`openvaf` invocation in this project's own container, with no local
`discipline.h` copy needed (OpenVAF ships that discipline set
natively, unlike IHP's own real `.va` files, which each carry their
own local copy under the older filename).
**Add...** registers a real, *existing* file for *any* view kind,
anywhere on disk -- the actual point of tracking file locations
instead of enforcing structure. **Automatic tracking**: every refresh
also scans a library's own `libraries/<library>/` directory for real
files this app didn't itself register (e.g. a real "Save As" from
xschem directly into that directory) and registers them immediately,
content-sniffed to tell a real xschem `.sym` from a real Qucs-S one
(both share the same real extension) -- confirmed real, not assumed: a
real xschem `.sym` always starts with `v {xschem`, a real Qucs-S one
starts with a bare drawing tag, no XML declaration at all.

**Open** launches the real, corresponding tool pointed at a view's own
real file, via a small, additive extension to `eda_tools.resolve_launch`
(a new `extra_argv` parameter, reused, not a separate launch
mechanism) -- each real invocation confirmed this session, from the
real, fetched FOSS source of each tool, not assumed:
- **Schematic/Symbol** -> `xschem <file>` -- a bare positional
  filename **is** real and supported (confirmed by fetching xschem's
  own real `src/options.c`; its `--help` prints nothing in this
  container, so this had to be verified from source).
- **GDS/Layout** -> two real, verified options: **Open in KLayout**
  (`klayout -l <real .lyp> <real .gds> -rr <script.rb>`, its own
  already-existing static launch guidance plus the new `extra_argv` --
  the script is a real, freshly-written one-liner,
  `RBA::CellView::active.cell_name = "<cell>"`, jumping straight to
  the requested real cell even inside a real, combined multi-macro
  GDS; `-rr` (not `-r`, which exits after running; not `-rm`, which
  runs *before* files load) is the one confirmed real, from KLayout's
  own local `-h` text, to run after loading and keep the GUI open) and
  **Open in Magic** (a real, freshly-written 2-line Tcl script -- `gds
  read <path>` then `load <cell>` -- verified live in this project's
  own container: reading a real IHP GDS this way printed every real
  cell name inside it).
- **Magic Layout** -> **Open in Magic**, a real, freshly-written
  self-contained one-line-load Tcl script (`cd <dir>; load <cell>`) --
  genuinely simpler than GDS's own two-step script above, since a
  `.mag` file is already Magic's own real, native format, so no `gds
  read` conversion step is needed first.
- **Qucs-S Symbol/Component** -> launches `qucs-s`, but **does not**
  claim to open the file: confirmed real, from Qucs-S's own fetched
  `qucs/main.cpp`, there is no CLI way to open a specific file in its
  interactive GUI (`-i` only applies in batch `--netlist`/`--print`
  mode) -- said plainly to the user before launching, not glossed
  over. A new `qucs-s` entry in `eda_tools.py`'s own tool registry
  records this real limit too (previously absent from the registry
  entirely, even though the real binary was already installed).
- **LEF/CDL/SPICE/Verilog/Liberty** -> the existing in-app
  `file_view_dialog`, matching **By Cell**'s own precedent -- no real
  external-tool identity exists for viewing a text snippet.

Every view-kind row also carries a small hover-help "?" icon (`gui/
tooltip.py`'s `add_help_icon`) explaining, in one real sentence, what
that kind of file actually is -- no click needed, and no separate
documentation to go find (see the GUI structure section above for the
matching PDK Wizard node tooltips).

**Prior art, checked, not assumed to be novel**: IHP-GmbH's own
[LibMan](https://github.com/IHP-GmbH/LibMan) (a separate, standalone
Qt/C++ desktop app, actively maintained) does something similar --
its own real "project file" also maps library names to real
directory *locations* rather than enforcing a fixed structure,
independently arriving at the same real design choice made here.

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

**Settings > Environment** generates a real, sourceable bash script
(`pdklib/shell_env.py`) for running this PDK's tools directly from a
terminal, outside this GUI entirely -- `export PDK_ROOT=...`/`export
PDK=...` (the real convention IHP's own `xschemrc`/README files
already use, confirmed by reading them directly, not assumed) plus
`magic_pdk`/`klayout_pdk`/`xschem_pdk`/`ngspice_pdk`/`librelane_pdk`
shell functions, each pre-pointed at this PDK's own real files (a
real, discovered `.magicrc`/`.lyp`, not a guessed filename -- see that
module's own docstring for exactly which real files/behaviors every
one of these was confirmed against, including two, real, working
end-to-end checks: `klayout_pdk -v` and a full `librelane_pdk
--smoke-test` flow). A wrapper for a real file that doesn't exist yet
(e.g. no `.lyp` in a from-scratch project) is emitted commented-out
with a plain note, never a function that would fail confusingly the
first time it's called. The real defined/not-yet-available function
names are echoed twice, from the one same list, never two
independently-derived copies: once by the sub-tab itself (a plain
label, so you don't have to scroll the script preview to see what's
actually usable), and once by the generated script's own final `echo`
line when you actually `source` it. **Save Script** writes it to
`shell_env/` (gitignored -- an absolute, machine-specific `PDK_ROOT`
baked in isn't shareable content) and makes it executable; **Copy to
Clipboard** skips the file entirely.

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

- **`openpdkcreator/pdklib/fetch.py`** -- a real, depth-1, sparse-checkout
  clone of `ihp-sg13g2/{libs.doc,libs.qa,libs.ref,libs.tech}` (~734 MB),
  deliberately excluding IHP's own git submodules (separate third-party
  repos for digital synthesis / EM-solver integration, unrelated to PDK
  structure). Lands in `data/` -- **gitignored, never committed**; IHP's
  data stays local-only, this repo versions only original tooling code.
- **`openpdkcreator/pdklib/inventory.py`** -- an honest, per-tool file
  census (file count, total size, extension breakdown) across all 15
  real `libs.tech/<tool>/` subdirectories and every real
  `libs.ref/<family>/<view>/` directory. No attempt at parsing any
  tool's proprietary format -- that's real, separate future work.
- **`openpdkcreator/pdklib/layers.py`** -- real KLayout `.lyp` parsing
  (adapted from OpenPDKCreator's own, already-verified
  `import_open_pdks.py`), confirmed against IHP's real, downloaded
  `sg13g2.lyp`: 377 real layers, byte-accurate name/GDS-layer/GDS-
  datatype/frame-color/fill-color, hand-checked for `<group-members>`
  nesting (none found -- see `docs/ihp_vs_open_pdks.md`). Switched from
  `ElementTree` to a real, text-based, line-tracking parser
  (`find_layer_blocks`) so each real `<properties>` block's own real
  source line range could be tracked -- stdlib `ElementTree` doesn't
  expose line numbers -- needed for `pdklib/layers_writer.py`'s own real
  write-back. Confirmed real and fully uniform before switching, not
  assumed: all 377 real blocks are exactly 16 real lines each, same
  14-tag field order; the new parser tracks real nesting depth so it
  still finds the correct real block boundaries rather than assuming
  no nesting exists.
- **`openpdkcreator/pdklib/layers_writer.py`** -- real, surgical
  write-back for Layers, the same discipline as every other writer
  here: only four of a real layer's fields have any real `.lyp`
  counterpart at all (`name`, `gds_layer`/`gds_datatype` together as
  the real `<source>L/D</source>` text, `frame_color`, `fill_color`) --
  every other editable field (`purpose`/`plane`/`stack_order`/
  `streamout_allowed`/`notes`/`status`) is this project's own metadata
  with no real `.lyp` counterpart, so it stays `project_io.py`-only,
  never written back, the same precedent `pdklib/drc_writer.py` already
  established for `DesignRule`'s own project-only fields. A real,
  found-before-shipping bug: the first version of `_render_new_layer_block`
  (for a brand-new layer added via **New Layer**) never emitted
  `frame-color`/`fill-color` at all -- caught immediately by a real,
  driven round-trip test asserting the new layer's own edited color
  survived export, before it could ship. Verified for real:
  byte-identical no-edit round-trip against the real 377-layer
  `sg13g2.lyp`; real, driven edit round-trips (color edit, rename, new
  layer, deleted layer) each confirmed correct with every other real
  layer in the file provably unchanged; re-verified via `main.py
  export-full`'s own smoking-gun round-trip test across the entire
  real PDK.
- **`openpdkcreator/gui/layers_view.py`** -- OpenPDKCreator's own
  Layers tab, copied (now with a live filter box added here -- see the
  GUI structure section), displaying the real parsed layers above.
  **Export > Export Edited Layers** (`app.py`) writes real, patched
  `.lyp` text reflecting whatever's currently in
  `self.project.layers` -- unlike every other writable domain here,
  Layers has no per-file cache to check first (the tab commits every
  field live, no pending-edit state, and there's only ever one real
  `.lyp` loaded per session).
- **`openpdkcreator/eda_tools.py`** -- OpenPDKCreator's own FOSS
  EDA-toolchain checker/installer/launcher. Its two PDK-specific
  "pre-pointed" launch entries for Magic/KLayout (originally pointed
  at `openmempdk`'s own single tech/layer-properties file) were
  dropped when this project started, then re-added once real files
  existed to point at instead of guessing: Magic launches with IHP's
  own real, official `ihp-sg13g2.magicrc` via the exact invocation
  IHP's own `libs.tech/magic/README.md` documents verbatim; KLayout
  launches with IHP's own real `sg13g2.lyp` via `-l` -- see the
  module's own docstring for exactly what's pre-configured and what
  isn't. A new `LaunchGuidance.requires_path` field makes
  `resolve_launch` fall back to a bare, unconfigured launch if the
  real file isn't there (`pdklib/fetch.py` hasn't run, or a non-default
  `--dest`), rather than launching with a flag pointed at nothing.
- **`docs/ihp_vs_open_pdks.md`** -- a real, sourced comparison of IHP's
  actual structure against the canonical open_pdks specification
  (confirmed via open_pdks' own README: IHP genuinely follows it), with
  one real naming divergence documented, not glossed over.
- **`openpdkcreator/pdklib/magic_tech.py`** -- a real (if deliberately
  partial) Magic `.tech` parser, hand-verified against IHP's real,
  downloaded files: the cleanly tabular sections
  (`tech`/`version`/`planes`/`types`/`contact`/`aliases`/`styles`/
  `compose`/`connect`) in full, plus one reliable pattern pulled out of
  each of four much harder mini-rule-language sections:
  - `cifoutput`: every real `layer NAME ... calma L D` recipe -- a
    genuine Magic-type-name to GDS-layer/datatype mapping.
  - `cifinput`: three real facts, all now extracted in full -- every
    real `ignore LAYERNAME` statement (23 real entries), a real,
    standalone `calma NAME L D` table (133 real entries, confirmed by
    reading the file to sit together in one flat block, not nested
    inside any boolean recipe -- a genuinely different real shape from
    `cifoutput`'s own per-recipe `calma L D`, which omits the name and
    inherits it from the enclosing block, so it needed its own regex;
    two of those 133 real entries use a literal `*` wildcard datatype,
    `calma BOUND 189 *`, kept as `None` rather than coerced to a fake
    integer), and the section's own real geometry-boolean recipe
    blocks (`layer`/`templayer NAME <base> ...` followed by real
    `and`/`and-not`/`or`/`grow`/`shrink`/`labels`/`copyup`/... op
    lines) -- recorded honestly and completely (name, real
    `templayer`-vs-`layer` distinction, base layer(s), every real op
    line in order) rather than interpreted or evaluated. **A real
    structural fact confirmed while building this**: a real Magic
    type's own recipe can be built across more than one real,
    textually-separated block sharing the same name (e.g. real
    `nwell` has two real, separate `layer nwell ...` blocks with two
    different real base layers) -- the same real fact `cifoutput`'s
    own `CifLayer` already merges for its own real DNWELL, matched the
    same way here (188 real, unique recipe names across 211 real block
    occurrences).
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
    A fourth real kind, `angles <layer> <degrees> "message"`, is
    extracted separately (17/17 real lines match) into its own
    `MagicAngleCheck` rather than folded into the above: a real angle
    is a plain degree count, not a length, so the real `/1000` micron
    conversion is deliberately not applied to it.
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
    are), and its own real `contact`/`devresist`/`antenna`/
    `disconnect`/`substrate` statements (41 real lines combined:
    24/7/4/4/2) -- each real, confirmed uniformly shaped, but small
    and heterogeneous enough that all five share one generic, raw
    `ExtractMiscStatement` rather than five near-identical dataclasses.

  Real `include` resolution confirmed: `ihp-sg13g2.tech` splices in 4
  fragment files (`cifout`/`cifin`/`drc`/`extract`) as one logical
  technology; `ihp-sg13g2-GDS.tech` is a second, genuinely separate
  technology with its own header. `lef`/`mzrouter`/`wiring`/`router`/
  `plowing`/`plot` are honestly reported as not-parsed-this-pass, never
  silently dropped (`MagicTechnology.unparsed_sections`,
  `MagicTechnology.drc_skipped`).
- **`openpdkcreator/pdklib/reconcile.py`** -- cross-references the Magic
  `cifoutput` GDS mapping above against the KLayout `.lyp` layers
  (`pdklib/layers.py`), both real, independent descriptions of the same
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
  and aren't shown standalone) over fifteen sub-tabs, one per real,
  parsed data domain (Planes/Types/Contacts/Aliases/Styles/CIF Layers/
  **CIF Input**/**CIF Input Recipes**/Compose/Connect/**DRC
  (Magic)**/Extract/**Extract Coefficients**/**Extract Devices**/
  **Extract Misc** -- CIF Input shows the section's own two flat, real,
  extracted facts side by side (ignored layers; the standalone `calma`
  layer-hint table, `*` wildcard datatypes shown as `*`, not a fake
  `0`); CIF Input Recipes shows the section's own real geometry-
  boolean recipe blocks, each real op rendered as `verb(args)` text;
  Extract Coefficients/Extract Devices/Extract Misc show the extract
  section's own real parasitic-coefficient lines, real `device`
  statements, and real `contact`/`devresist`/`antenna`/`disconnect`/
  `substrate` statements) -- plus a **View File** button. **Types is
  editable** -- a list + form pane (Plane/Name/Aliases/Obsolete),
  New/Delete Type, the same commit-on-switch pattern as everywhere
  else; every other domain stays read-only for now (each would need
  its own form). Verified for real, driven against the actual
  downloaded data: all fifteen sub-tabs' row counts match
  `magic-tech`'s own CLI output exactly (39 compose/20 connect/192 DRC
  checks + 17 angle checks/30 resist/23 cifinput-ignored/133
  cifinput-hints/188 cifinput-recipes/506 extract cap coefficients/50
  extract devices/41 extract misc), switching technologies
  correctly reloads every sub-tab, editing a real type's
  name/aliases/obsolete commits
  immediately and survives a technology switch, and a spot-checked real
  DRC row (`Act.a`) shows the correct converted `0.15` micron value.
- **`openpdkcreator/pdklib/lef.py`** -- a real (if deliberately partial)
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
  `pdklib/lef_writer.py`'s own write-back, which needs to locate exactly
  where a real pin's text lives to patch it in place.
- **`openpdkcreator/pdklib/spice_models.py`** -- a real, bounded ngspice
  `.lib` model-card parser, the first concrete piece of the
  **Simulation** GUI group (see Future Work): real
  `.model NAME TYPE (key=value ...)`/`.model NAME TYPE key=value ...`
  statements (both real, confirmed parenthesized and bare forms exist;
  real keyword case varies file to file, matched case-insensitively
  like every other keyword-driven parser here) and real
  `.subckt NAME port1 port2 ... / .ends` blocks (the same bounded
  shape `pdklib/netlist.py`'s own CDL/SPICE `.SUBCKT` extraction already
  uses). Real parameter values are kept as raw strings, not converted
  to float -- some real BSIM/PSP model cards use a quoted formula
  expression as a value (e.g. `vfbo = '-0.94312*sg13g2_lv_nmos_vfbo'`),
  not a plain number. Real statements wrapping across lines via a
  leading `+` continuation marker (SPICE's own convention, distinct
  from Magic's trailing `\`) are joined first. **A real structural
  fact found via a verification mismatch, not assumed**: a real
  `.model` can sit *inside* a real `.subckt` body (a locally-scoped
  model -- e.g. `resistors_mod.lib`'s own `rsil` subckt defines its own
  `rmod_rsil` model) -- an early version only checked for `.model` at
  top level and silently missed every nested one, caught by comparing
  the parser's own count (26) against a raw `grep` count (61) across
  all 32 real files; fixed by checking every real line for `.model`
  regardless of subckt nesting. Verified for real: 61/61 real models
  and 57/57 real subckts extracted exactly (including a real 371-real-
  parameter PSP MOSFET model card parsed cleanly). Real
  `.LIB NAME ... .ENDL NAME` PVT-corner blocks are also extracted (47
  real blocks across all 6 real `corner*.lib` files, every real
  `.LIB`/`.ENDL` pair balanced): each real corner's own real `.param
  KEY = VALUE` overrides (kept raw, same reasoning as `.model`'s own
  params) and real `.include FILE` statements. A real, confirmed-not-
  assumed distinction: a `.param` line found *inside* a real `.subckt`
  body (a device's own local default, e.g. `capacitors_mod_mismatch.lib`'s
  own `cap_carea_mm` mismatch parameter) is correctly NOT attributed to
  any corner -- only `.param` lines genuinely inside a real
  `.LIB`/`.ENDL` block are. Verified for real: 396/396 real corner
  params in `cornerMOSlv.lib`'s own 11 real corners cross-checked
  against an independent ground-truth scan exactly.
- **`openpdkcreator/gui/spice_models_view.py`** -- the **Simulation >
  ngspice Models** tab (`SpiceModelsView`), the same file-picker +
  Treeview shape as `lef_view.py` (no small, fixed set of "the real
  ones" to enumerate -- all 32 real `.lib` files are shown). Three
  sub-tabs, **Models**, **Subckts**, and **Corners**; a model's own
  real parameter list is shown as one raw `key=value` text column
  rather than a parameter-by-parameter breakdown, since some real PSP
  model cards carry 370+ real parameters. Read-only -- no editor exists
  for
  ngspice model data. Verified for real, driven: switching files
  reloads both trees with the correct real row counts.
- **`openpdkcreator/pdklib/xschem.py`** -- a real, bounded xschem `.sym`
  symbol parser, hand-verified against all 202 real, downloaded
  symbols. A real symbol is a flat sequence of top-level `TAG
  {content}` primitives; the real device-attribute block (`K { ... }`)
  and real pin list (`B ... {name=... dir=...}` primitives) are
  extracted in full, the symbol's own real drawing geometry
  (line/arc/text primitives) deliberately not parsed or rendered --
  the same "structure yes, graphics no" scope as `pdklib/lef.py`'s own
  PORT rect-count-only precedent. Two real structural complications
  found and handled, not assumed: a real block's own matching closing
  `}` needs a quote-aware, brace-depth-aware scan, not a naive
  first-`}` search -- a real, embedded, *escaped* brace inside a real
  quoted Tcl expression (`ptap1.sym`'s own `format="tcleval(...[ev
  \{...\}]...)"`) broke a first-draft naive version; a real `B`
  primitive's own property block can itself span multiple physical
  lines (confirmed real in `inductor.sym`). Not every real `B`
  primitive is a real pin -- four real, plain decorative boxes with no
  `name=`/`dir=` properties at all are correctly skipped, not a gap.
  The real `K` block's own `type=` field (`capacitor`/`primitive`/
  `nmos`/`subcircuit`/...) is exposed directly; its own real
  `template="key=value ..."` sub-value is parsed one level deeper;
  every other real `K`-field varies per device kind (confirmed:
  `cap_cmim.sym` and `sg13g2_a21o_1.sym` share almost no field names)
  and is kept raw, the same "don't guess further semantics" discipline
  `pdklib/magic_tech.py`'s own `ComposeStatement` uses. Verified for real:
  374 real pins extracted across all 202 real symbols (378 real `B`
  lines minus the 4 real non-pin decorative boxes), field-by-field
  spot-checked against the source text for a simple two-pin symbol, a
  four-pin digital stdcell symbol, the escaped-brace file, and the
  multi-line pin-block file.
- **`openpdkcreator/gui/xschem_view.py`** -- the **Simulation > xschem
  Symbols** tab (`XschemView`), the same file-picker + Treeview shape
  as `spice_models_view.py`. Two sub-tabs, **Device** (type +
  template params + raw fields) and **Pins** (name/direction).
  Read-only. Verified for real, driven: switching files reloads both
  trees with the correct real row counts.
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
- **`openpdkcreator/pdklib/drc.py`** -- real KLayout DRC-deck rule
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
  `pdklib/drc_writer.py`'s own `_locate` (which re-derives a rule's real
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
  from `pdklib/drc.py` at startup), not blank, then editable the same way
  a hand-authored rule would be. Verified for real, driven against the
  actual data: correct row/form population, New/Delete both work,
  **View Source** opens the exact real file and highlights the right
  lines, and the live diagram/`layer_colors()` both render correctly.
- **`openpdkcreator/pdklib/netlist.py`/`verilog.py`** -- real cell/module
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
- **`openpdkcreator/pdklib/liberty.py`** -- a real, stack-based state
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
  `pdklib/liberty_writer.py`'s write-back. Verified for real: all 97 real
  `.lib` files parse cleanly with 0 errors -- 700 real cells, 5422 real
  pins, 3977 real timing arcs total.
- **`openpdkcreator/gui/liberty_editor.py`**/**`liberty_dialog.py`** --
  the **Edit Pins/Timing** dialog (see GUI structure above): a
  two-level, commit-on-switch editor (Pins pane, and a nested Timing
  Arcs pane for whichever pin is selected); switching pins flushes any
  pending arc edit too, not just the pin's own fields.
- **`openpdkcreator/pdklib/liberty_writer.py`** -- real, surgical,
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
- **`openpdkcreator/pdklib/gds.py`** -- real, bounded GDS structural
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
- **`openpdkcreator/pdklib/cells.py`** -- aggregates one real cell's views
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
  real content (`gds_cell`, via `pdklib/gds.py`) when `klayout.db` is
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
  the LEF tab) editing that macro's real pins directly. `pdklib/cells.py`'s
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
  counts, via `pdklib/gds.py`) for the selected cell when `klayout.db` is
  importable -- a plain text line, not a raw file **View** (GDS is
  binary), degrading to an honest "present, but not parsed" note
  rather than silently showing nothing when it isn't. Verified for
  real, driven against the actual data: correct counts and view flags
  across all four real families, `sg13g2_sram`'s full 2338-row "show
  all" render in 0.18s (no real performance concern), the CDL/Verilog
  **View** buttons both land on and highlight the exact real
  `sg13g2_and2_1` block inside their much larger combined files, a real
  pin edit made here survives a save + simulated relaunch, and
  `sg13g2_a21o_1`'s real GDS summary line matches `pdklib/gds.py`'s own
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
- **`openpdkcreator/pdklib/user_models.py`** / **`gui/user_models_view.py`**
  -- user-defined Verilog/Verilog-A model support, plus two ways to
  link one to the rest of the PDK. Real files live under
  `user_models/verilog/*.v` and `user_models/veriloga/*.va` (a small,
  git-tracked directory -- deliberately *not* gitignored like `data/`/
  `saves/`, since this is the user's own authored content, not a
  derived edit of third-party PDK data). Verilog-A's real
  `module NAME(port, ...); ... endmodule` header/port syntax is
  identical to plain digital Verilog's (confirmed against IHP's own
  real `libs.tech/verilog-a/mosvar/mosvar.va`), so `pdklib/verilog.py`'s
  existing `find_modules` parser is reused directly for both `.v` and
  `.va` -- no new parser needed. Two linking mechanisms: (1) automatic
  -- a module named the same as a real cell attaches to it with no
  configuration, the same name-matching convention every other view in
  `pdklib/cells.py`'s `build_cell_index` already uses; (2) explicit --
  a `UserModelLink(module_name, file_relpath, cell_name)` record,
  persisted in `user_models/links.yaml` (also git-tracked), set from
  the **Simulation > User Models** tab's own Cell name field + **Save
  Link**/**Clear Link** buttons. A wholly new, user-defined cell name
  (not present in the real PDK at all) still gets its own real
  `CellViews` entry via `get_or_create` -- authoring a brand-new cell's
  model doesn't require first faking a real view for it. **Simulation
  > User Models** (`UserModelsView`) lists every real module found,
  its real ports, and its current linked-cell text (`(auto: NAME)`
  when implicit, the explicit cell name otherwise); **By Cell** gained
  a **User** column (real linked-model count) and a **User Models**
  listbox (double-click to view the real source, jumping straight to
  that module's own real line range via `file_view_dialog`). Verified
  for real, driven end-to-end in the container: a wholly-new module
  auto-attaches to its own new cell; saving an explicit link moves it
  onto a different, real existing cell (confirmed absorbed into that
  cell's own `CellViews`, no longer its own top-level row in **By
  Cell**); the link survives a `save_links`/`load_links` round-trip
  through the real `links.yaml`; **Clear Link** removes it, falling
  back to the automatic name match; and the **By Cell** listbox's
  double-click handler opens the real source file correctly (a real
  bug -- a missing `_view_selected_user_model` method, the binding's
  target -- was found and fixed by this same driven test before it
  ever reached the user). A second real bug was found and fixed the
  same way: `UserModelsView._build` mixed Tk's `pack` and `grid`
  geometry managers on the same parent frame, which raises
  `TclError: cannot use geometry manager grid ... which already has
  slaves managed by pack` the moment the tab is built -- fixed by
  switching the top toolbar row to `grid` as well. Its own three real
  follow-ons (in-GUI port editing, batch relinking, real ngspice/OSDI
  wiring) are done too -- see the Future Work section's own
  user-models entry for the full real design and verification.
- **`openpdkcreator/gui/port_editor.py`** -- `PortEditor`, a real port
  list + New/Delete Port + a Name/Direction[/Width] form, the same
  commit-on-switch pattern `PinEditor` uses -- duck-typed across CDL/
  SPICE's `NetlistPort` and Verilog's `VerilogPort` (structurally
  similar but not identical -- only Verilog has a real bus width) via
  a `port_factory` callback for New Port, rather than two near-
  identical widgets.
- **`openpdkcreator/pdklib/netlist_writer.py`/`verilog_writer.py`** --
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
- **`openpdkcreator/pdklib/text_utils.py`** -- one real, shared fix for
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
  the editable domains above (DRC Rules/Magic Types/LEF pins/Layers/the
  Settings tab's project name), modeled on `OpenPDKCreator`'s own
  `rules_db/` (ADR 0002): a save/load layer completely separate from
  the real, downloaded `.tech`/`.lef`/`.drc` files, not a write-back
  into them. `File > Save Edits` (`Ctrl+S`) writes `saves/<pdk
  name>.yaml` (gitignored, alongside but independent from `data/` --
  `pdklib/fetch.py` can delete/re-create `data/` wholesale, and these are
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
  from, `pdklib/fetch.py`'s own `REPO_URL`). Renaming the project updates
  the window title live and persists through `project_io.py`. Verified
  for real: the four values are confirmed genuinely distinct strings on
  a real, downloaded PDK (not accidentally the same path/name reused
  twice), and a rename survives a save + simulated relaunch.
- **`openpdkcreator/pdklib/lef_writer.py`** / **`openpdkcreator/export.py`**
  -- real, open_pdks-format write-back for LEF pins, the first concrete
  piece of native write-back serialization (see Future Work). Never
  overwrites the real, downloaded source file -- `export.py` always
  writes to a new `export/<pdk name>/...` tree, mirroring each file's
  own real relative path under `pdk_root`. **Surgical patching, not
  full regeneration**: this project's LEF model doesn't capture every
  real LEF construct (port `RECT` *coordinates* -- only a count is
  tracked -- `PROPERTY`, `FOREIGN`, ...), so `lef_writer.py` re-reads
  the real *original* file fresh from disk and, using each pin's real
  source line range (`pdklib/lef.py`'s new `start_line`/`end_line`), keeps
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
- **Export > Export Edited LEF Files** (`app.py`) -- the GUI action:
  exports every real `.lef` file parsed this session (LEF tab or By
  Cell tab -- both route through the same `App.get_parsed_lef` cache)
  with any in-memory pin edits patched in. Verified for real, driven:
  edited a pin via the LEF tab's form, exported, re-parsed the real
  exported file, and confirmed the edit is there -- and confirmed a
  real `.lef` file never parsed this session is correctly *not*
  exported (nothing to write for a file with no possible edits).
- **`openpdkcreator/pdklib/drc_writer.py`** -- real, open_pdks-format
  write-back for DRC Rules, extending native write-back serialization
  beyond LEF pins. `pdklib/drc.py`'s own extraction already established
  a real, two-file split -- a rule's `rule_id`/`description` live in
  its real `.drc` Ruby script's own `result_var.output("ID",
  "description")` call; its `value` lives in the one real JSON config
  file's `drc_rules['KEY']` entry (the script itself never contains a
  literal numeric threshold, only a variable traced back to that JSON
  lookup) -- so write-back patches each field into its own real file,
  never conflating the two. **Surgical, character-offset-based
  patching**: `_locate` re-derives which real JSON key (if any) backs
  a rule's value, and the exact real `.output()` regex match, by
  re-running `pdklib/drc.py`'s own extraction regexes directly (imported,
  not duplicated) against the rule's own real `source_provenance` --
  then only the exact substrings the id/description occupy are
  replaced, leaving everything else (surrounding Ruby code, other
  rules, comments, formatting) untouched. **A real, common wrinkle
  handled deliberately**: 61 of IHP's own real `.output()` calls have
  a real `"<section> : ..."` prefix before the description
  `DesignRule.description` actually keeps (`pdklib/drc.py` splits on the
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
- **`main.py export-drc`** / **Export > Export Edited DRC Rules**
  (`app.py`) -- CLI and GUI actions, matching `export-lef`'s own shape:
  export every rule with real provenance, report byte-identical counts
  and any hand-authored rules skipped. Verified for real, driven:
  edited a rule's value via the real DRC Rules form, exported, and
  confirmed the real JSON config reflects it.
- **`openpdkcreator/pdklib/magic_tech_writer.py`** -- real, open_pdks-format
  write-back for Magic Types, the third and final currently-editable
  domain (after LEF pins and DRC Rules). Each real type occupies
  exactly one real line (`[-]plane name,alias1,alias2` -- no block
  structure to navigate, unlike LEF's `PIN`/`MACRO` or DRC's multi-line
  `.output()` calls), so `pdklib/magic_tech.py` gained the same real
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
- **`main.py export-magic-types`** / **Export > Export Edited Magic
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
- **`main.py export-liberty`** / **Export > Export Edited Liberty
  Files** (`app.py`) -- CLI and GUI actions, matching
  `export-netlist`/`export-verilog`'s own shape: exports every real
  `.lib` file parsed this session (`App.get_parsed_liberty`'s own
  cache for the GUI; every real file, freshly parsed, for the CLI and
  `export-full`) with any in-memory pin/timing-arc edits patched in.
- **`main.py export-layers`** / **Export > Export Edited Layers**
  (`app.py`) -- exports the one real `.lyp` file this project ever has
  loaded at once (`pdklib/layers_writer.py`), with any in-memory
  name/GDS-layer/GDS-datatype/color edits patched in.

Native write-back serialization is now complete for every currently
structured-editable domain -- LEF pins, DRC Rules, Magic Types,
CDL/SPICE/Verilog ports, Liberty pin/timing-arc data, and Layers -- and
independently re-verified faithful across the entire real PDK via
`main.py export-full`'s own smoking-gun round-trip test, not just
per-writer sample tests. Everything still read-only (Magic Tech's
other domains, GDS) has no write-back for the same reason it has no
editor yet -- see Future Work.
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
- **`openpdkcreator/gui/pdk_wizard_view.py`** -- the **PDK Wizard** tab
  (see GUI structure above for the full design): 18 real stages laid
  out as a static, hand-laid-out flowchart on a plain `tk.Canvas`
  (deliberately *not* `geometry_canvas.py` -- that widget edits a real
  device's own real coordinates, this one is a conceptual diagram with
  no such data), starting from Layers, forking into Digital vs. Analog/
  Memristor, converging through By Cell/GDS/Export. Each node's status
  is computed live from whichever `pdk_root`/project is currently
  loaded via the same lightweight `find_*`/`discover_families` glob
  helpers every other tab already uses (never a full parse) -- verified
  for real against two very different real states: the full, ~734 MB
  downloaded IHP deck (every domain with real files correctly shows
  "present", with real counts -- e.g. 377 layers, 202 xschem symbols,
  4 cell families) and a genuinely empty `pdk_root` (every domain
  correctly shows "not started", with the four in-GUI-creatable
  domains -- xschem Symbols/Schematics, Qucs-S Symbols/Components --
  and User Models distinguished from the domains with a real, honestly
  surfaced "no create-from-scratch path yet" gap note). `App.goto(*path)`
  (`gui/app.py`) is a new, small, shared navigation helper -- walks down
  as many nested `ttk.Notebook` levels as given, silently stopping if a
  level isn't found -- that the Wizard's own **Go to Tab** button uses;
  verified for real to reach 2-level (`Technology > Layers`) and
  3-level (`Simulation > xschem > Schematics`, `Simulation > Qucs-S >
  Components`) targets, and to leave the button disabled (not crash)
  for the one node with no dedicated tab (Export/Package, a File-menu
  action). Every one of the 18 nodes was click-simulated for real
  (select -> detail panel populates -> Go to Tab navigates) with no
  errors; a geometry self-check confirmed no node's title text overflows
  its own box and no two node boxes overlap. **Found and fixed one real,
  pre-existing bug along the way**, unrelated to the Wizard itself:
  `XschemView` (`gui/xschem_view.py`) had no `load()` method of its own
  even though `App._reload_from_real_files` already called
  `self.xschem_view.load()` -- "Reload from Real Files" crashed with an
  `AttributeError` any time it was invoked; added the missing
  `load()` (delegating to its own Symbols/Schematics panes' existing
  `load()` methods), re-verified via the existing
  `test_no_lef_and_reload.py`-style scenario.
- **Create-from-scratch skeletons for Layers/Magic Tech/LEF**, closing
  three of the four real gaps the **PDK Wizard** tab surfaced (see its
  own README section above for exactly what remains -- LEF partially,
  DRC Rules not at all):
  - `pdklib/layers.py`'s `create_new_lyp_file` writes a minimal, valid,
    empty `<?xml...?><layer-properties></layer-properties>` skeleton.
    Required a real fix to `pdklib/layers_writer.py`'s own
    `render_lyp_file`, not just a new writer function: with zero real
    `<properties>` blocks to anchor after, its existing logic
    (designed only for "add a layer among existing ones") dumped a
    brand-new layer's own text *before* the file's own real XML
    declaration -- found by tracing the code, not by a failing test,
    before it ever shipped. Fixed by anchoring new blocks just before
    the real closing `</layer-properties>` tag in that one case.
  - `pdklib/magic_tech.py`'s `create_new_tech_file` writes a real `tech`/
    `version` header (using the file's own stem as the real technology
    name) plus empty `planes`/`types`/`contact`/`aliases` sections --
    no writer fix needed here: `_scan_single_line_section` already sets
    a real section's own start/end line correctly even with zero
    entries inside, and `magic_tech_writer.py`'s own
    `_render_section_patch` already anchors a brand-new entry just
    before its own section's real closing `end` line.
  - `pdklib/lef.py`'s `create_new_lef_file` writes a real `VERSION 5.7 ;`/
    `BUSBITCHARS`/`DIVIDERCHAR` header, zero macros (confirmed real:
    IHP's own real `.lef` files never carry a trailing `END LIBRARY`
    either -- they just end after the last macro's own `END <name>`
    line). Deliberately partial, not overclaimed: `pdklib/lef_writer.py`
    already explicitly refuses to write back a whole new macro with no
    real source position, and there's no **New Macro** action either,
    so this alone unblocks *loading* a brand-new family's `.lef`, not
    authoring a macro purely in-GUI -- see its own docstring and the
    Wizard's own LEF gap note.
  - GUI wiring differs per domain's own real selector shape rather
    than forcing one pattern: LEF's file picker already matched
    xschem/Qucs-S's own editable-combobox-plus-**Create
    File**/**Edit File** toggle (`gui/file_picker_utils.py`) exactly,
    so it was switched to reuse that shared helper directly (`state=
    "readonly"` removed, a `<KeyRelease>` binding added). Layers (a
    single global file, no file-picker combobox at all) and Magic Tech
    (its own combobox is keyed by *technology name*, not file path --
    a different real selection semantic) each instead got a small,
    separate **New .lyp File...**/**New .tech File...** button
    prompting for a name via `simpledialog.askstring`.
  - Verified for real, end-to-end, against a genuinely empty
    `pdk_root`: create each skeleton (via its own real button/action,
    not just the bare `create_new_*` function), add a real entry via
    the domain's own existing editor (**New Layer**/**New Type**+
    **New Plane**/loading pins), export, and confirm the exported text
    is valid and round-trips -- e.g. a new `TopElectrode.drawing` layer
    at GDS 200/0 exported into a real, single `<properties>` block
    nested correctly inside `<layer-properties>`, then re-parsed back
    to one real layer. Also verified the real "footgun" this design
    accepts rather than silently guards against: typing a LEF path
    that doesn't match the real `libs.ref/<family>/lef/*.lef`
    convention creates a real file that's simply not picked up by
    `find_lef_files` afterward (not a crash, not data loss) -- the
    LEF tab's own new hint label exists specifically to steer around
    this.
- **Generate real DRC rules, and export/import them** -- closes the
  remaining, most-genuinely-hard gap of the four the **PDK Wizard**
  surfaced (see its own README section above):
  - `pdklib/drc.py`'s `create_new_drc_deck` writes a real, minimal, valid,
    empty deck (a real `custom_rules.drc` skeleton under
    `libs.tech/klayout/tech/drc/`) -- **New DRC Deck...** in the DRC
    Rules tab, mirroring Layers/Magic Tech/LEF's own pattern. No JSON
    config file is created: a brand-new rule's own value is written as
    a literal `<value>.um` straight into its own Ruby call rather than
    indirected through a `drc_rules['KEY']` JSON lookup the way IHP's
    own real files use -- that indirection is a real IHP convention,
    not a KLayout requirement, and skipping it avoids inventing a
    second, empty JSON file with nothing real in it yet.
  - **The actual "generate" step** -- `pdklib/drc_writer.py`'s new
    `render_new_rule_block`: a hand-authored rule (**New Rule**,
    already a full, real form -- rule_id/description/check_type/up to
    3 layer pickers/value, nothing new needed there) becomes real,
    runnable KLayout DRC Ruby for the three `check_type`s with a real,
    single-method shape this project already recognizes coming the
    other way (`min_width` -> `.width()`, `min_spacing` -> `.space()`,
    `min_enclosure` -> `.enclosed()`). Each rule defines its own real
    layer(s) inline via KLayout's own `input(gds_layer, gds_datatype)`
    -- resolved from the rule's own `layers` field against
    `app.project.layers` by name -- since a from-scratch deck has no
    real, pre-existing common-include file defining shared Ruby layer
    variables the way IHP's own real deck does.
  - **A genuinely different write-back discipline than every other
    writer here**, not a copy-paste of the "surgical patch" pattern:
    `custom_rules.drc` is entirely tool-owned (born from New Rule,
    never a real, downloaded foundry file), so `render_custom_drc_file`
    fully *regenerates* its content from the current rule list on every
    export rather than position-tracking a surgical patch -- correct
    and far simpler here, since there's no third-party formatting to
    preserve. Real rules with real, resolvable provenance (extracted
    from IHP's own files) keep the existing surgical-patch path,
    completely unchanged.
  - `export.py`'s `export_drc_rules` gained a `layers` parameter and a
    richer `list[(rule_id, reason)]` failure return (was a bare
    `list[str]` of skipped IDs) -- every rule that still can't be
    written back (an unsupported `check_type`, a missing value, or a
    `layers` entry with no matching real, resolvable `Layer`) is
    reported with *why*, in the GUI status line and both CLI commands
    (`export-drc`, `export-full`) alike, never silently dropped. A
    real, caught-before-shipping bug from this signature change: the
    positional call inside `export_full_pdk` (`export_drc_rules(...,
    dest_root)`) would have silently passed *dest_root* as the new
    *layers* parameter -- fixed by passing `dest_root=dest_root`
    explicitly.
  - **Import** is the existing, unmodified extraction path
    (`find_drc_root`/`extract_design_rules`) -- verified for real that
    it round-trips: a `custom_rules.drc` exported from 2 hand-authored
    rules re-parses back to those same 2 real rules by ID.
  - Verified end-to-end against a genuinely empty `pdk_root` (deck
    created before Layers even existed, found a real, separate ordering
    bug in `App._new_drc_deck` this way -- see below) and confirmed
    byte-identical, zero-`custom_rules.drc` no-edit export against the
    full real IHP deck's own 75 real rules across 29 real files.
  - **Found and fixed a second real, pre-existing-shaped bug along the
    way**: `App.load()` early-returns before reaching DRC-root
    discovery when there's no real `.lyp` yet (a from-scratch project
    may well create its DRC deck *before* its Layers) -- `_new_drc_deck`
    now sets `self.drc_root`/re-extracts directly rather than assuming
    `load()` reached that point, avoiding a real `AttributeError` on
    the status-line message.
- **Library Manager** (`pdklib/library_index.py`/`gui/
  library_manager_view.py`) -- see its own GUI-structure section above
  for the full design (index-based, not directory-convention-based;
  the real, per-tool "open a specific file" research). Additional
  detail worth recording here:
  - `pdklib/cells.py`'s `CellViews`/`build_cell_index` gained four new
    fields (xschem Symbol/Schematic, Qucs-S Symbol/Component), matched
    by cell **name** across every real subdirectory under
    `libs.tech/xschem/` and the flat `libs.tech/qucs-s/symbols/` --
    real, additive, so **By Cell** could show these too in the future
    (not done this pass, tracked below) without any new plumbing.
  - **Found and fixed a real Tk timing bug** while testing **Create**
    twice in a row on the same cell: rebuilding the Libraries/Cells
    trees and re-selecting the "same" library re-fires
    `<<TreeviewSelect>>` (Tk treats a fresh insert + reselect of the
    same iid as a real selection change, and only dispatches the
    virtual event on the next real event-loop pass, not synchronously)
    -- which was running `_on_library_select`'s own real "the user
    picked a different library" reset of the current cell to `None`,
    even though the library never actually changed. Fixed at the root:
    that handler now only resets the current cell when the reported
    library selection *actually* differs from before.
  - Verified end-to-end, for real: created a new project library, a
    new cell, a symbol and a schematic for it (confirming real files
    land under `libraries/<library>/` and get registered), confirmed a
    real view kind with no create-from-scratch support (LEF) stays
    honestly absent with no fake button, resolved real, correct argv
    for xschem/KLayout/Magic opens (including the real, generated
    Magic GDS-loading Tcl script) without actually blocking on a
    launched GUI window (`subprocess.Popen`/`eda_tools.check_tool`
    both mocked at the right layer -- an earlier attempt that mocked
    `subprocess.Popen` globally broke `check_tool`'s own, unrelated
    internal use of `subprocess.run` with a confusing `TypeError`, a
    real test-design lesson, not a real application bug), registered a
    real, external, hand-authored file via **Add...** for LEF, and
    confirmed a file written directly into a library's own directory
    (simulating an external tool's "Save As") gets automatically
    tracked on the next refresh with no explicit click.
  - **Prior art check** (web search + `gh api`, not assumed novel):
    IHP-GmbH's own [LibMan](https://github.com/IHP-GmbH/LibMan) -- a
    separate, standalone Qt/C++ desktop app, actively maintained,
    last updated this same month -- does something similar, and its
    own real "project file" independently arrived at the same real
    design choice (track library locations, don't enforce a directory
    convention) this session was steered toward.
- **Verilog/Verilog-A editors for the Library Manager**
  (`pdklib/verilog.py`'s new `create_new_verilog_file`/
  `create_new_veriloga_file`, `pdklib/library_index.py`'s new
  `infer_ports_for_cell`) -- **Create** for these two now writes a
  real, minimal, valid skeleton pre-populated with a cell's own already
  -known real pins (not an empty template) whenever one exists.
  - **Real Verilog-A structure, empirically confirmed, not assumed**:
    read IHP's own real `libs.tech/verilog-a/mosvar/mosvar.va` and
    `r3_cmc/r3_cmc.va` -- every real port is declared both `inout` and
    `electrical` (a real Verilog-A analog terminal has no directional
    concept the way a digital Verilog port does). Then verified live,
    with a real `openvaf` compile in this project's own container,
    that a minimal file using the modern `` `include
    "disciplines.vams" `` (rather than IHP's own real files' local
    `discipline.h` copy) compiles cleanly with no external file
    dependency -- confirmed both ways: the same file *without* any
    include fails (`'electrical' was not found in the current scope`),
    *with* it produces a real, working `.osdi`.
  - **Pin-direction normalization across two real, confirmed
    vocabularies**: LEF's own real `DIRECTION` (`INPUT`/`OUTPUT`/
    `INOUT`, uppercase -- confirmed via a direct grep of real
    `sg13g2_stdcell/lef/*.lef`, being careful to only read
    `LefPin.direction`, never LEF's unrelated layer-level `DIRECTION
    HORIZONTAL`/`VERTICAL`) and xschem's own real `dir=` (`in`/`out`/
    `inout`, lowercase -- confirmed via a direct grep of real
    `sg13g2_stdcells/*.sym`), both mapped down to Verilog's own real
    `input`/`output`/`inout` keywords.
  - `infer_ports_for_cell` tries a cell's own already-known views in
    priority order -- LEF (most authoritative real physical source),
    then xschem symbol, then an existing Verilog/Verilog-A module of
    the same name -- stopping at the first real, non-empty port list;
    returns `[]` (an honestly empty template) for a wholly new cell.
  - A newly-**Create**d Verilog/Verilog-A view defaults into the
    already-established `user_models/{verilog,veriloga}/` convention
    (not `libraries/<library>/`, unlike every other creatable view kind
    here) -- real, project-authored model content, so it's picked up
    for free by **Simulation > User Models**'s own name-matching (its
    "User Models" column, OSDI-snippet generation) with no new
    plumbing. `library_index.yaml` still tags it with whichever library
    was open when it was created -- registration is just a grouping
    label, decoupled from physical file location, matching this whole
    index's own real design.
  - Verified end-to-end, for real: a project cell with only a
    hand-authored xschem symbol (real `dir=in`/`dir=out` pins) got a
    newly-**Create**d Verilog-A view with those same real pins
    correctly declared `inout`/`electrical`, and a newly-**Create**d
    Verilog view with the same real pins correctly declared
    `input`/`output`; separately confirmed `infer_ports_for_cell`
    against a real, known IHP stdcell (`sg13g2_inv_1`) pulls its real
    LEF pins (`A` input, `Y` output, `VDD`/`VSS` inout) with correctly
    normalized directions.
- **A real "PDK" top-level tab**, plus three real gaps closed, all
  found while building `openMemristorPDK` -- a genuinely independent,
  from-scratch memristor PDK, authored entirely through this tool's own
  GUI/CLI (a separate project, its own repo; the walkthrough is
  documented there, `docs/presentation/walkthrough.tex`).
  - **Everything actually about the PDK's own content now lives under
    one top-level `PDK` tab** (`gui/app.py`'s new `_build_pdk_tab`/
    `self.pdk_notebook`) -- PDK Wizard, Overview, Technology, Cells,
    Library Manager, Simulation all nested one level deeper than
    before; `Settings` stays its own, separate top-level tab, since
    project naming/tool config isn't PDK content. `App.goto(*path)`
    inserts the new intermediate hop itself (a real path like
    `("Technology", "Layers")` still works unchanged) so the PDK
    Wizard's own stage table never needed to know about the wrapping
    tab.
  - **A real "New Macro" action for LEF** (`gui/lef_view.py`'s LEF
    Macros sub-tab), closing the one remaining "no in-GUI create"
    domain among Layers/Magic Tech/DRC Rules/LEF -- pins are added to
    it afterward through the same **New Pin** flow an existing macro
    already uses. `pdklib/lef_writer.py`'s `render_lef_file` renders a
    brand-new macro (`start_line == 0`) as a whole, freshly-generated
    `MACRO ... END` block, appended after every real, existing macro on
    export -- verified round-tripping correctly through a real,
    downloaded 84-macro file (`tests/test_lef_writer.py`) and through
    the actual GUI action, mocked-dialog-and-all
    (`tests/test_lef_new_macro_gui.py`).
  - **Layers now persist through `saves/` like DRC Rules/Magic Types/
    LEF pins already did** (`project_io.py`'s `save_state`/`load_state`
    gained a `layers` dict, keyed by real `.lyp` path the same way
    `lef_pins` is keyed by `.lef` path) -- a real, found inconsistency:
    Layers was the one domain among the four where a GUI restart
    silently lost anything not already exported, since edits lived only
    in `app.project.layers` (in-memory). Verified for real: create a
    `.lyp` from scratch, add a layer, Save Edits, destroy and rebuild
    the whole `App` (simulating a real relaunch), confirm the layer
    survives (`tests/test_layers_persistence.py`) -- it no longer
    silently reverts to the real, on-disk (still-empty) `.lyp`.
  - **A real, live-session dead end investigated and corrected, not
    silently left as a false claim**: the DRC Rule form's own Layer
    picker combobox appeared to never populate a selectable list during
    that session's own noVNC walkthrough. Reproduced with a direct,
    scripted test against both the real IHP deck (377 real layers) and
    a from-scratch 4-layer project -- in both cases `combo.cget
    ("values")` came back correctly populated every time. No code
    defect exists here; the live symptom was a real interaction/
    rendering issue specific to that noVNC session, not a bug in
    `rules_view.py`. Documented here so the record stays honest, not
    because a fix was needed.
- **By Cell now surfaces `library_index.yaml`'s own registered entries
  too**, not just real `pdk_root` ones -- closing the Future Work item
  of the same name. `CellViews` gained a `registered_views` dict (view
  kind -> path); `build_cell_index` gained a `registered_by_cell`
  param, enriching an already-known cell exactly the same way xschem/
  Qucs-S already do (a registered-only cell never introduces a
  brand-new row here -- that's still the Library Manager's own job, a
  deliberate, documented boundary, not an oversight). `gui/
  cell_hub_view.py` computes it from `merged_entries`, filtered to
  `source == "registered"`, and reshapes it into the plain dict shape
  `cells.py` expects, keeping that module decoupled from
  `library_index.py`'s own dataclasses (the same reason
  `user_models_by_cell` is pre-computed by its own caller). The tree's
  own existing LEF/CDL/SPICE/Verilog/Liberty/GDS columns show a `+`
  instead of `✓` for a registered-only view (a new legend row spells
  out the difference); real always wins, matching `library_index.py`'s
  own merge rule -- a registered entry never touches a cell's real,
  parsed fields, only `registered_views`. **Deliberately out of
  scope this pass**: the View/Edit Ports buttons stay gated on the
  real, parsed object, so a registered-only entry doesn't get an
  in-app viewer yet -- a natural, small follow-on, not required for
  this one to be genuinely useful (the point was visibility, not full
  interactivity). Verified for real, driven: an isolated unit test
  (`build_cell_index` enriches a known cell, never fabricates a new
  one) plus an end-to-end GUI test registering a real SPICE file for a
  real IHP cell (`sg13g2_Corner`, which genuinely has no real per-cell
  SPICE) and confirming it shows up as `+` in the actual tree, with
  every real, unrelated column untouched.
- **ngspice Models gets a real "New..."/Create File action too**,
  closing one of the three domains the "Create-from-scratch flows for
  Liberty/CDL-SPICE/ngspice Models" Future Work item named (Liberty/
  CDL-SPICE remain -- see that item's own updated note for why they're
  a bigger lift: neither has a dedicated tab at all yet). `pdklib/
  spice_models.py`'s new `create_new_lib_file` writes a real, minimal,
  genuinely empty `.lib` skeleton -- just a bare comment line; real
  ngspice `.lib` grammar has no mandatory header the way LEF/Magic Tech
  do, so this parses cleanly to 0 models/subckts/corners, the same
  honest "empty, not broken" result a real file with genuinely nothing
  in it already gave. `gui/spice_models_view.py`'s file combobox
  switched from `state="readonly"` to the same editable **Edit
  File**/**Create File** toggle LEF/xschem/Qucs-S already share
  (`gui/file_picker_utils.py`) -- no new picker UI needed here, since
  this tab already had its own dedicated file picker, just a read-only
  one. Verified for real, driven: a unit test confirming the written
  file round-trips through `parse_lib_file` as honestly empty and
  correctly refuses to overwrite an existing real file, plus a real GUI
  test typing a new path, clicking **Create File**, and confirming the
  file exists, is selected, and the button flips to **Edit File**.
- **Real per-cell navigation inside a multi-cell GDS opened in
  KLayout** -- closing a Future Work item this README itself called
  "a real, accepted limit" until an actual, documented KLayout flag
  was found and verified: **Open in KLayout** now also writes a real,
  freshly-generated one-line Ruby script,
  `RBA::CellView::active.cell_name = "<cell>"`, launched via `-rr
  <script>` (`gui/library_manager_view.py`'s `_open_klayout`, the same
  `extra_argv` mechanism Magic's own GDS-loading Tcl script already
  uses). Getting the right flag took real, careful reading of
  KLayout's own local `-h` output, not just the first plausible-
  looking one: `-r <script>` runs "after having loaded files" (the
  right timing) but exits afterward (wrong -- closes the GUI); `-rm
  <script>` runs "before loading files" (too early --
  `RBA::CellView::active` has nothing loaded yet); `-rr <script>` is
  "like -r, but does not exit" -- the one that actually works.
  Confirmed live, for real, in this project's own container: opening a
  real, combined 84-macro `sg13g2_stdcell.gds` this way jumped straight
  to the requested cell, both the window title and the canvas
  correctly showing it -- not just the default top-level view. Real,
  driven test coverage: `tests/test_library_manager_view.py`'s own
  KLayout-launch assertion now also checks for `-rr` and reads the
  generated script's real content.
- **Real Magic layout-view (`.mag`) creation**, closing the "Real
  layout-view creation" Future Work item -- the one blocker that had
  stood since GDS support first landed ("no Magic `.mag` file parser at
  all"). Grounded in two real sources, not just the official manual
  alone (the real, current format has drifted from what the manual
  documents): Magic's own `mag_manpage.html`, **and** a real,
  live-exported ground-truth `.mag` file, generated by actually running
  the real, installed Magic binary against real IHP GDS data in this
  project's own container. Real, empirically confirmed structural facts
  the manual alone wouldn't have given: an undocumented `magscale <a>
  <b>` line right after `tech`; layer sections and the special `<<
  checkpaint >>` section share one identical shape; real pin labels use
  `flabel` (not the manual's own `rlabel`), each followed by its own
  `port N direction` line.
  - `pdklib/mag.py` (new): `parse_mag_file` (bounded -- section names +
    real rect counts, `use`/label/property counts, `magscale`, not full
    geometry, same "bounded, not a full parser" precedent as everywhere
    else here) and `create_new_mag_file` (a real, minimal, valid
    `magic`/`tech <name>`/`timestamp`/`<< end >>` skeleton -- confirmed
    live: the real Magic binary loads it cleanly and echoes the correct
    cell name back). `find_mag_files` scans a new, project-defined
    `libs.ref/<family>/mag/*.mag` convention (not an IHP one -- no real
    upstream precedent exists for where hand-drawn `.mag` files would
    live in this PDK).
  - **Magic Layout** is now Library Manager's seventh creatable view
    kind (`pdklib/library_index.py`'s `CREATABLE_VIEW_KINDS`) -- **Create**
    writes a real, minimal skeleton declaring the PDK's own real, active
    Magic technology name; **Open in Magic** writes a real,
    self-contained one-line-load Tcl script (`cd <dir>; load <cell>`,
    genuinely simpler than GDS's own two-step `gds read` + `load`, since
    a `.mag` file is already Magic's real, native format) and launches
    with it.
  - **A real bug found and fixed while adding this**: the first version
    of `_default_tech_name()` (the helper that picks which real
    technology name a new `.mag` skeleton declares) took
    `find_tech_files()[0]` -- alphabetically first, which is
    `ihp-sg13g2-GDS.tech`, a per-domain *fragment* meant to be
    `include`d by the real, complete `ihp-sg13g2.tech`, not a
    standalone loadable technology (confirmed live: `parse_tech_file`
    returns an empty `name` for every real fragment except this one,
    which parses its own name as literally `"ihp-sg13g2-GDS"` -- wrong).
    Caught by a real, driven GUI test asserting the picked name against
    the real IHP deck, not by inspection. Fixed with a real, generic
    heuristic instead of a special case: real IHP fragment files are
    always named `<main>-<suffix>.tech`, so the *shortest* stem among
    every real `.tech` file found is always the real, main, active
    technology's own name -- confirmed correct for real IHP data
    (`ihp-sg13g2`, 10 characters, shortest of all six real files found).
  - Verified for real, driven: `tests/test_mag.py` (new) --
    `create_new_mag_file`'s skeleton round-trips through this project's
    own parser *and* loads cleanly in the real, installed Magic binary;
    `parse_mag_file` reads a real `.mag` file generated fresh, at test
    time, by that same real binary from real IHP GDS data (not a
    committed fixture copy, so a real format drift would still be
    caught) and gets every real structural fact right (16 sections, 126
    rects, 4 labels, `magscale (1, 2)`); `find_mag_files` discovers a
    real probe file under the new `libs.ref/<family>/mag/` convention.
    `tests/test_library_manager_view.py` gained a full **Create** ->
    **Open in Magic** round trip against a real IHP cell
    (`sg13g2_inv_1`), confirming the real, correct tech name and the
    real, generated Tcl script's exact content.
- **Hover-help tooltips**: every Library Manager view-kind row and
  every PDK Wizard stage node now shows an explanatory tooltip on plain
  mouse hover, no click needed -- `gui/tooltip.py`'s `Tooltip` (for a
  real child widget, e.g. the new "?" icon next to each Library Manager
  view-kind label, one real sentence per kind in `VIEW_KIND_HELP`) and
  the new `CanvasItemTooltip` (for the Wizard's own canvas-drawn stage
  boxes, which have no `winfo_rootx` of their own to position a popup
  from -- it positions from the triggering `<Enter>` event's mouse
  location instead, reusing that same stage's existing `description`
  field, the same text its own click-to-select detail panel's "What
  this is" section already showed). Both share one internal
  `_show_popup` helper so the popup itself (a borderless, pale-yellow
  `Toplevel`) looks identical either way. Verified for real, driven:
  `tests/test_tooltip.py` (hover shows/leaving hides/empty text never
  opens a popup, for both `Tooltip` and `CanvasItemTooltip`) and a new
  assertion block in `tests/test_pdk_wizard.py` confirming every one of
  the 18 real stages carries a live tooltip reusing its own real
  description text.
- **The Wizard tab moved back out to top level**, no longer nested
  under **PDK** (renamed from "PDK Wizard" to plain "Wizard" at the
  same time) -- it's the very first thing a new user should see, before
  opening any per-domain tab, not one level deep inside PDK alongside
  Overview/Technology/Cells/Library Manager/Simulation. `gui/app.py`'s
  `_build_wizard_tab` now targets `self.notebook` directly instead of
  `self.pdk_notebook`, and runs first in `App`'s own tab-build order.
  `App.goto(*path)` is unaffected (Wizard was never one of its
  targets). Verified for real, driven: `tests/test_pdk_wizard.py`
  asserts the root notebook's first tab is literally titled `"Wizard"`
  and is the one selected on startup.
- **Real bug found and fixed: Layers' own Stack Order always showed
  `0`, and Move Up/Down silently did nothing about it.** `import_layers`
  (`pdklib/layers.py`) never set `stack_order` at all, so every real,
  freshly-imported layer sat at the `models.Layer` dataclass's own
  default (`0`) -- confirmed live against the real IHP deck, all 377
  real layers. That part alone was arguably an honest, already-
  documented gap (a `.lyp` file genuinely has no real stack-order field
  to import from). The real bug is what it broke downstream: the
  Layers tab's own Move Up/Down reorder helper (`gui/layers_view.py`'s
  `_move`) works by *swapping* the selected layer's `stack_order` with
  its neighbor's -- swapping two layers that are both `0` is a real
  no-op, confirmed live (Move Down on a freshly-loaded real layer
  changed nothing at all, silently). The list still *looked* right by
  accident (Python's `sorted()` is stable, so ties preserve the
  `.lyp`'s own real block order), which is exactly why this went
  unnoticed until someone actually looked at the Stack Order column's
  numbers. Fixed at the real source: `import_layers` now assigns
  `stack_order` from each layer's own real position among the `.lyp`
  file's real `<properties>` blocks (`stack_order=len(layers)` at
  append time -- contiguous `0..n-1` for whatever's actually kept, even
  if some real block were skipped for missing `name`/`source`) --
  `stack_order` has no real `.lyp` write-back counterpart either way
  (`pdklib/layers_writer.py`'s own docstring), so this is purely an
  import-time default, still a human-adjustable starting point via Move
  Up/Down, not a claim of verified physical stack order. Verified for
  real, driven: `tests/test_layers_stack_order.py` (new) -- all 377
  real, imported layers get distinct `stack_order` values matching the
  real `.lyp` file's own order; Move Down against the real, freshly-
  loaded deck now genuinely swaps the first two real layers instead of
  no-op'ing; **New Layer** still correctly continues numbering past the
  real, imported max. Full suite re-run clean (51/51) to confirm no
  round-trip/persistence regression, since `stack_order` is
  project-metadata-only and several existing tests already exercise
  `import_layers` without asserting on that field.
- **The Layers stack cross-section is now zoomable, scrollable, and its
  real viewport genuinely tracks the window.** A real, full IHP stack
  (377 real layers) on the old fixed 260px-tall canvas squeezed every
  band under a pixel -- unreadable regardless of window size, since the
  canvas never grew past that constant, and every band stretched to
  fit whatever height was available.
  - **The real viewport now comes from the canvas's own live
    `winfo_width()`/`winfo_height()`**, not `STACK_CANVAS_W`/`_H` (now
    just the initial size hint and pre-layout fallback) -- the
    containing frame is gridded `sticky="nsew"` with real row/column
    weight (was `sticky="n"`, capped to its packed content size
    regardless of available window space) and the canvas redraws on
    every real `<Configure>` event.
  - **Each real band is always drawn at one fixed, always-readable
    pixel height (`FIXED_BAND_H`)**, never stretched or shrunk to fit
    the viewport -- a real vertical `ttk.Scrollbar` (plus mouse-wheel
    binding) now scrolls through whatever doesn't fit, matching the
    layer list beside it, which gained the exact same real, wired
    `ttk.Scrollbar` (it previously had none at all -- only Tk's own
    unlabeled built-in wheel scrolling, no visible/draggable thumb).
    The very first draw, and every real Zoom-bound change, scrolls to
    the real, physical *bottom* of the (possibly zoomed) range --
    matching this pane's own "(bottom -> top)" label -- while an
    ordinary redraw (a form-field edit, a window resize) leaves the
    user's own current scroll position alone. Confirmed live, driven:
    growing the real window from 1000x800 to 1000x1600 genuinely grew
    the canvas's own real viewport (493px -> 1424px) while each real
    band's own height stayed exactly fixed; the real, unzoomed
    377-layer scrollregion (9842px) genuinely exceeds the real viewport,
    confirming the scrollbar has real content to scroll through, not a
    no-op.
  - **A "Zoom" control** (two editable Min/Max `stack_order` bounds,
    positioned beside the drawing -- a real, editable "lateral scale",
    not a draggable-handle range slider) filters which real layers get
    drawn *before* the fixed-height/scrollbar layout above ever runs;
    blank means no bound (full range) on either side, an inverted
    Min/Max is silently swapped rather than left broken, and an
    out-of-range value clamps to the real current stack instead of
    crashing or drawing nothing. **Reset** clears both back to blank.
  - **A real, found-before-shipping Tk quirk**: the first version
    called `Spinbox.configure(from_=..., to=...)` on every redraw to
    keep the widgets' own arrow-key bounds current -- confirmed live,
    empirically, that this silently **overwrites the Spinbox's own
    bound `textvariable` to the new `from_` value** on every single
    call, which stomped a real, just-typed Min/Max (or the blank
    "no bound" default) on the very next redraw, collapsing the
    drawing to one real layer. Fixed by never reconfiguring `from_`/
    `to` after construction at all -- real range clamping already
    happens in Python (`_current_zoom_bounds`) regardless of what the
    widget's own arrow-key bounds say, so the widget-level bounds were
    only ever cosmetic in the first place.
  - Verified for real, driven: `tests/test_layers_zoom.py` (new, 11
    real assertions) -- the default (no zoom) view draws all 377 real
    layers; a real Min=0/Max=5 zoom draws exactly those 6 with their
    real name labels; an inverted and an out-of-range real input are
    both handled correctly, not crashing; Reset restores the full view;
    both scrollbars are real and wired; the real scroll-to-bottom
    default and its preservation across an unrelated edit, and its
    real re-anchor on a Zoom-bound change; and the live window-resize
    assertions above. Verified live in the real, running GUI via noVNC
    too, not just the automated suite -- both scrollbar thumbs visibly
    present and correctly positioned. Full suite re-run clean (52/52).
- **Layers gained a real Name search + Type multi-select filter**, on
  top of the existing free-text substring box.
  - **Name** is the same free-text box as before, narrowed to search
    only `layer.name` -- it previously also substring-matched
    `purpose`/`status`, which meant searching e.g. "drawing" matched
    *every* real layer (every real, imported layer's `purpose` defaults
    to `"drawing"` -- see the `stack_order` bug entry above for the
    same root fact) or "placeholder" matched all of them via `status`,
    neither a real, useful name search.
  - **Type** is a real, multi-select `tk.Listbox` (a real "selection
    box", scrollable via its own `ttk.Scrollbar`) -- generated fresh
    from whatever real layer-name types this project's own currently
    loaded layers actually contain, never a static list. "Type" here is
    a new, derived-only concept (`_layer_type` -- the segment after a
    real layer's last `.`, e.g. `"pin"` for `"Activ.pin"`), computed
    directly from each real name, **not** the existing `purpose` field
    (project-only metadata that every real, imported layer gets set to
    a fixed `"drawing"`, unconnected to its real name -- filtering on
    that would be close to a no-op, confirmed empirically: the real IHP
    deck's own 377 layers span 51 distinct real name-derived types, but
    only one distinct real `purpose` value). Every real type starts
    selected (an untouched filter never hides real data); Name and Type
    combine (AND); deselecting every type honestly shows zero rows
    rather than silently falling back to "show everything".
  - Rebuilding the Type listbox's own items is skipped whenever the
    real, distinct type set hasn't actually changed (most `refresh()`
    calls, e.g. an unrelated form-field edit) -- only a real add/
    delete/rename that changes which types exist triggers a rebuild,
    which preserves each still-existing type's own checked state and
    defaults any brand-new type (e.g. **New Layer**'s dot-less
    `NEWLAYERn`, grouped under one honest `"(no dot)"` pseudo-type) to
    selected, so it's visible immediately.
  - Verified for real, driven: `tests/test_layers_type_filter.py` (new,
    9 real assertions) -- the Type listbox lists exactly the real IHP
    deck's own 51 distinct types, not a static list; selecting only
    "pin" filters to exactly the 24 real `.pin` layers; Name and Type
    combine correctly; deselecting everything shows zero rows; a
    brand-new, dot-less layer adds and auto-selects a new, real
    `"(no dot)"` entry; and Name no longer false-matches on
    `purpose`/`status`. Verified live in the real, running GUI via
    noVNC too: selecting "pin" in the real Type listbox visibly
    filtered the real tree down to exactly its real `.pin` layers
    (Activ.pin, Metal1.pin, TopMetal2.pin, IND.pin, ...). Full suite
    re-run clean (53/53).
- **The "Type" filter above was corrected to actually be "Purpose"**,
  per direct user feedback -- unifying two concepts that had been kept
  artificially separate. The previous version derived its filter value
  live from each real layer's own name (`_layer_type`, GUI-only,
  never stored) specifically *because* the existing `purpose` field
  was real, stored, project metadata that every imported layer's own
  `import_layers` set to a fixed `"drawing"`, disconnected from its
  real name -- a deliberate design note in `pdklib/layers.py`'s own
  docstring even argued this split was correct, since the real name's
  own 51 distinct trailing segments would never fit the old, small,
  fixed 6-value `PURPOSES` enum (`drawing`/`pin`/`label`/`marker`/
  `fill`/`exclude`). Corrected instead of left as two parallel
  concepts: `pdklib/layers.py` gained a new `purpose_from_name` (the same
  real derivation, now the *authoritative* one) and `import_layers`
  now sets each real layer's own real, stored `purpose` from it
  directly, reversing that earlier note. The GUI's own Purpose
  selector/filter (renamed from "Type") now reads `layer.purpose`
  itself -- a real, stored, independently-editable field again, not a
  shadow value recomputed from `name` on every redraw -- and the
  **Purpose** field in the edit form switched from a closed,
  `state="readonly"` 6-value combobox to a real, free-typed,
  per-project-suggested one (`values=` refreshed from the real,
  current project on every `refresh()`, confirmed live and empirically
  that `ttk.Combobox.configure(values=...)` does *not* share
  `tk.Spinbox`'s own textvariable-stomping quirk from the entry above,
  so this was safe to do unconditionally on every redraw without
  losing whatever the user is mid-typing). `PURPOSES` and the GUI-only
  `_layer_type`/`_NO_TYPE_LABEL` are gone; a brand-new, dot-less layer
  now simply gets the real `Layer` dataclass's own existing `"drawing"`
  default (matching `purpose_from_name`'s own fallback), needing no
  separate pseudo-value at all. Verified for real, driven:
  `tests/test_layers_purpose_filter.py` (replacing the prior test file,
  12 real assertions) -- `purpose_from_name` and `import_layers` both
  checked directly; the Purpose selector/combobox both reflect the
  real, current per-project data; filtering, combining with Name, and
  the empty-selection case all still behave the same as before; and a
  new one: free-typing a brand-new Purpose value in the edit form
  live-commits to the real layer and is immediately reflected in the
  Purpose selector. Verified live in the real, running GUI via noVNC
  too: typing a custom Purpose value into the edit form's own real
  Entry-like combobox updated that row's real Purpose column
  immediately. Full suite re-run clean (53/53).
- **Layers gained "Show All" and sortable column headers.** **Show
  All** (`_select_all_purposes`) re-selects every real purpose in the
  Purpose listbox in one click, instead of clicking/shift-clicking each
  one back individually after narrowing the filter. Clicking any real
  Treeview column header (Stack Order/Name/GDS/Purpose/Status) sorts
  the *displayed* list by that column, toggling ascending/descending on
  repeat clicks and marking the active one with a real ``▲``/``▼``
  glyph in its own header text. **Deliberately display-only**: Move
  Up/Down, the stack cross-section, and a brand-new layer's own
  ``stack_order`` numbering all keep reading real ``stack_order`` via
  ``sorted_layers()`` directly, regardless of which column the list
  happens to be sorted by at the time -- confirmed live, driven: Move
  Up/Down still swaps the correct real, physical layers even while the
  list is displayed sorted by Purpose. The GDS column sorts
  numerically by real ``(gds_layer, gds_datatype)``, not as text (so
  `9/0` sorts before `10/0`, not after). Verified for real, driven:
  `tests/test_layers_sort_and_showall.py` (new, 8 real assertions) --
  ascending/descending/column-switch behavior, sort surviving a Name
  filter change, numeric GDS sorting, Move Up/Down's real independence
  from display sort, and Show All restoring the full 377-layer view.
  Full suite re-run clean (54/54).
- **Real, native, bidirectional support for IHP-GmbH's own LibMan
  tool's `.projects` file format**, per direct user request ("would it
  be some way to use IHP file manager structure? ... I'd prefer
  natively"). Researched properly before writing a line of code, not
  guessed: fetched LibMan's own real repo
  (`github.com/IHP-GmbH/LibMan`, commit
  `84c5974a647c5d7d5a9ddc3bae7b6396e008ce33`, pushed 2026-08-12 --
  under real, active development) and found it has **two entirely
  separate real formats**, not one: a heavy, real Cap'n Proto "CORE"
  binary geometry-streaming layer (`capnp/*.capnp`, needs LibMan's own
  real `gds_to_core`/`xschem_to_core`/... converter toolchain to read
  at all -- genuinely out of scope, not attempted) and a **real,
  simple, plain-text library-registry format** (`.projects`/`.lib`
  files, `define("lib","path");`/`attach(design,tech);`/
  `include("other.projects");` statements) -- the one actually
  analogous to this project's own `library_index.yaml`, and genuinely
  tractable to implement for real.
  - **`pdklib/libman_project.py`** (new): a real, bounded parser/writer
    ported statement-for-statement from LibMan's own real, fetched
    `src/libfileparser.cpp` -- real `#`-comment stripping (respected
    inside string literals), real top-level-`;`-terminated statement
    splitting (respecting nested `()`/`[]`/strings), real `\n`/`\r`/
    `\t`/`\\`/`\"` string-literal escapes, both real `define()` forms
    (`define(path)`, library name inferred via Qt's own real
    `completeBaseName()` semantics -- strip everything from the
    *first* `.`, not just the last extension; and `define(name,
    path)`), `attach()`, and real, recursive `include()` with real
    cycle detection. Verified against a **second real source**, not
    just the parser: LibMan's own real, committed
    `tests/data/sg13g2.projects` -- a real ground-truth fixture for
    the exact same SG13G2 PDK this project already works with,
    embedded verbatim in `tests/test_libman_project.py`. Real, honest
    edge cases this fixture surfaced and the parser handles correctly:
    a bare, non-file reference (`define("analogLib", "analogLib");`,
    a well-known external library, not a real path at all) and a real
    relative path walking outside the project directory (`../../../`).
  - **A real, stated risk, not glossed over**: LibMan is under active
    development with **no version marker inside a real `.projects`
    file** and no live way for this project to detect a future grammar
    change -- this parser is pinned to the commit above; re-verify
    against LibMan's own current real source before trusting this
    against a newer LibMan build. This is exactly the tradeoff native
    support was asked for despite: a one-off, hand-triggered converter
    would have sidestepped the risk entirely, at the cost of never
    being able to just open the same real project file in both tools.
  - **Library Manager gained Import from LibMan Project.../Export to
    LibMan Project...** (new toolbar row, top of the tab). Export
    writes one real `define("library", "path");` per real view whose
    kind LibMan's own real Import feature actually understands (GDS/
    Xschem Symbol+Schematic/Qucs-S Symbol+Component -- confirmed from
    LibMan's own real `docs/setup/IMPORT.md`) across every real
    library at once; every other real kind here (LEF/CDL/SPICE/
    Verilog/Liberty/Magic Layout) has no LibMan counterpart and is
    skipped, counted (not hidden) in the real status-bar summary.
    Import registers every real `define()` whose own real path
    resolves to a real, existing file on this machine, reusing the
    exact same real, content-sniffed `infer_view_kind` **Automatic
    tracking** already established (disambiguating xschem vs. Qucs-S
    `.sym` the same way) -- or, for a real path this project's own
    formats don't cover at all (LibMan's own real `.layout.core`/
    `.schematic.core`/... Cap'n Proto files), a new, honestly
    **tracked-but-unopenable `libman_core`** view kind: real location
    known, real "View" button deliberately absent (would otherwise
    open through the generic text-preview dialog and show garbled
    binary -- actively misleading, not honestly absent) in favor of a
    plain label explaining why.
  - Verified for real, driven: `tests/test_libman_project.py` (new, 13
    real assertions, the real ground-truth fixture above) and
    `tests/test_libman_project_gui.py` (new, 5 real assertions) --
    Export against the real, full IHP deck produces a real,
    re-parseable `.projects` file with exactly the real count of
    LibMan-understood views; Import against a real, hand-authored
    fixture pointing at real files already in this project (a real
    `.gds`, a real xschem `.sym`, a real opaque `.layout.core`-style
    file, a nonexistent path, and the real `analogLib` bare reference)
    registers exactly the right real view kinds, honestly skips what
    it can't resolve, and a real syntax error surfaces an honest error
    dialog rather than a silent partial import. Full suite re-run
    clean (56/56).
- **DRC Rules: three more `check_type`s (`min_area`/`min_overlap`/
  `max_length`) get real, generated KLayout DRC Ruby**, closing half
  of the "remaining six" Future Work item -- self-selected as the next
  real, valuable, well-scoped increment. Grounded in real, local
  ground truth before writing any generation code, the same discipline
  as the original three: grepped this project's own real, downloaded
  IHP deck for each real method already in real use there --
  `antenna.drc`'s own real
  `dantenna_connected.with_area(0, ant_g_min_area)`;
  `sg13g2_maximal.drc`'s own real `self.overlap(other, value)`;
  `5_16_metal1.drc`'s own real
  `m1_g_l1.with_length(m1_g_length.um + 0.001.um, nil)` -- confirming
  `layer.with_area(0, v)`/`layer.overlap(other, v)`/
  `layer.edges.with_length(v, nil)` are real, valid KLayout DRC idioms
  before generating a single line from them. `min_area`/`min_overlap`
  both have a real `max_layers=None` in `schema.CHECK_TYPES` (a real
  rule *can* reference more, for shapes not attempted here) but the
  one real, single-method idiom each maps to only has a real meaning
  for exactly 1/exactly 2 layers -- a new `_FIXED_LAYER_COUNTS` check
  refuses anything else with an honest reason instead of guessing which
  wider real Boolean combination was meant.
  - **A real, pre-existing bug found while adding live verification for
    this** (not introduced by this pass -- it affected the original
    three just as much, simply never caught before): `custom_rules.drc`
    never called KLayout's own real `report(...)` function, so the
    real 2-string-arg report-database form of `.output("RULE_ID",
    "description")` failed at real runtime with a genuine
    `TypeError: no implicit conversion of String into Integer ... in
    LayerInfo::initialize` -- confirmed live by actually running a
    freshly-generated `custom_rules.drc` through the real, installed
    KLayout binary (`klayout -b <gds> -r custom_rules.drc`), something
    no previous test in this project had ever done for this file (prior
    tests only checked the generated *text*, and that it re-parses
    through this project's own extractor -- never that it's real,
    executable Ruby). Root cause confirmed via KLayout's own real,
    fetched `drc_runsets.html` documentation: the 2-string-arg
    "write to a report database" form of `.output()` only resolves once
    a real report destination is configured via `report(...)`; passing
    `-rd output=<path>` on the command line alone does not do this by
    itself, since the script itself has to read `$output`. Fixed by
    adding a real `report("Custom DRC Rules", $output || "custom_rules_
    report.lyrdb")` call to `DRC_DECK_SKELETON_HEADER` itself (shared by
    both the empty **New DRC Deck** skeleton and every rule-filled
    `custom_rules.drc` `render_custom_drc_file` generates), so the
    real, stated "genuinely runnable" claim now actually holds under a
    real, standalone `klayout -b` invocation, not just structurally
    plausible-looking text.
  - **A real, honest gap, not silently closed**: unlike the original
    three, none of these three feed straight into `.output()` anywhere
    in the real deck the simple way `width()`/`space()`/`enclosed()` do
    (confirmed by grepping for it) -- `pdklib/drc.py`'s own extractor
    still only recognizes the original three coming the other way, so
    a min_area/min_overlap/max_length rule generated here does not yet
    round-trip back through re-extraction. Extending the extractor for
    these three is real, separate, future work.
  - Verified for real, driven: `tests/test_drc_generate.py` (extended)
    -- all six now-generatable check_types produce correct, expected
    Ruby text; the three newer shapes honestly don't re-extract while
    the original two still do; and, new, a **live run through the
    real, installed KLayout DRC engine** against a real, freshly-built
    GDS (real rectangles on two real layers) -- exit code 0, and a
    real report database containing every one of the five real rule
    categories tested. Full suite re-run clean (56/56).
- **The internal `ihp/` package was renamed to `pdklib/`**, per direct
  user feedback: "I don't like having 'ihp' as an internal name" --
  a real, valid point given this README's own stated mission
  ("generally -- not specific to any one process... keep that in mind
  before adding anything that only makes sense for IHP specifically"),
  which the internal module namespace itself had been quietly
  contradicting since the very first commit. Every real
  `openpdkcreator.ihp`/`from ..ihp import`/`from .ihp import`
  reference (142 real matches) and every real `ihp/<file>.py` doc
  reference (163 real matches, spanning every `.py` file plus this
  README, `docs/ihp_vs_open_pdks.md`, and `user_models/README.md`) was
  updated -- a plain, unambiguous, word-boundary-safe pattern
  (confirmed empirically, not assumed: every real `ihp/` match in this
  codebase is immediately followed by a `.py` filename, never anything
  else) meant no real, external reference to the actual IHP PDK/
  company was at risk of being caught by the same sweep. **Explicitly,
  deliberately left untouched, by scope, not oversight**: real,
  external references to the real IHP entity itself (`ihp-sg13g2`,
  `IHP-GmbH`, `data/ihp-sg13g2/` -- real, downloaded, gitignored PDK
  content), and the entirely separate `openMemristorPDK` project (its
  own independent git repository, not this one -- see this README's
  own "Copy-vs-share" bullet for why the two stay independent). `git
  mv` preserved file history for the whole directory. Verified for
  real, driven: full suite re-run clean (56/56) after the rename;
  `main.py`'s own CLI (`magic-tech`) and a fresh `App()` build both
  confirmed working live in the container, not just import-checked.
- **GitHub repo renamed too** (`openpdkcreator-ihp-template` ->
  `openpdkcreator-toolkit`, same real reasoning as the internal package
  rename above), and its own **description** now explicitly states the
  real, native LibMan support and links to LibMan's own real repo
  (`github.com/IHP-GmbH/LibMan`) -- per direct user request, right
  alongside a reminder to keep it documented that IHP's real SG13G2
  PDK is still the real template/reference this whole project is built
  against (see this README's own opening paragraph).
- **Menu bar restructured**: **File** now holds only genuinely
  project-level actions (Save Edits, Reload from Real Files, and the
  two real LibMan `.projects` Import/Export actions, moved here from
  being Library-Manager-tab-only since they act across every real
  library at once) -- previously it also held all eleven individual,
  per-domain "Export Edited X (open_pdks format)" actions, which
  buried the two, real project-level ones among domain-specific noise.
  Those eleven now live in their own new **Export** menu. A new
  **Help** menu holds **About openPDKcreator** (repo URL, LibMan link,
  license) and a general **Help** quick-reference (every real tab and
  menu, in one screen) -- both real `gui/text_dialog.py` modals, reused
  rather than a new dialog type. Verified for real, driven:
  `tests/test_menu_structure.py` (new, 6 real assertions) -- the real
  menu bar's own three top-level cascades and their exact real
  contents (introspected via Tk's own `Menu.index`/`entrycget`, not
  guessed), File's LibMan actions really switching to the Library
  Manager tab and calling the real underlying methods, and both
  dialogs' real content (repo URL, LibMan link, license, tab guide).
  Verified live via noVNC too: all three menus opened and read
  correctly, and the real About dialog rendered with the right text.
- **Settings > General: real, working multi-project support** -- a
  **Browse...** button next to **Project directory** (previously
  read-only) picks a different real directory and calls the new
  `App.change_project_directory`, which switches this session's own
  project-level state (`saves/`, `library_index.yaml`, `libraries/`,
  `user_models/`) to it -- **not** the real PDK data itself
  (`self.pdk_root` is untouched). **Grounded in a real architecture
  check before writing any code**, not assumed: `export.PROJECT_ROOT`
  turned out to be one of *three* separate, independent,
  `__file__`-derived fixed constants (`export.PROJECT_ROOT`,
  `project_io.SAVE_DIR`, and an unrelated `pdklib/fetch.py` one for
  download defaults, confirmed to be a different, correctly-untouched
  concern) -- but every real consumer of the first two turned out to
  already access them as `export_mod.PROJECT_ROOT`/`project_io.
  SAVE_DIR` (module-qualified, re-read on every real call), not a name
  frozen at import time, confirmed by grepping for the one pattern that
  *would* have broken this (`from ... import PROJECT_ROOT`) and finding
  none. That meant a real, working implementation only needed to
  reassign those two shared constants plus fix the one real exception
  (`LibraryManagerView.__init__` caches it once into `self.project_root`
  at construction time) rather than a much larger refactor threading a
  new parameter through every consumer. A genuinely new, empty
  directory starts a fresh project there (created if missing); an
  existing one restores its own real saved state -- the same real, full
  reload sequence `_reload_from_real_files` already used for "start
  over," since a new directory's own saved Magic Types/LEF pin
  overrides must apply on top of a real, freshly re-parsed baseline,
  not whatever the *previous* project's own edits left in memory. A
  real confirmation prompt warns that unsaved edits are lost first.
  Verified for real, driven: `tests/test_change_project_directory.py`
  (new, 8 real assertions) -- switching to two different new, real
  directories each starts genuinely fresh with no leakage between them
  or from the original; switching back to each of three real
  directories in turn restores exactly its own real saved project
  name/registered library, never mixed; and the full, real GUI flow
  through Settings > General's own **Browse...** button, including
  declining the confirmation prompt leaving everything unchanged.
  Verified live via noVNC too: the real directory picker opens
  pre-filled at the current real project directory, listing the real
  `saves/`/`library_index.yaml`/`user_models/` alongside it. Full
  suite re-run clean (58/58).
- **`gui/text_dialog.py`'s Help/About modal (and the OSDI snippet
  dialog that already reused it) now genuinely word-wraps to the
  dialog's own current window size**, per direct user request. A real
  bug, not just a style choice: the previous `wrap="none"` had no
  horizontal scrollbar either, so a real line wider than the window
  was genuinely unreachable, not just inconvenient. Fixed with one
  real, well-understood Tk option, `wrap="word"` -- real, dynamic
  re-flow to the widget's own current pixel width, recalculated by Tk
  itself on every real resize, no extra code needed; never touches the
  real underlying text buffer, so a real select/copy still grabs
  exactly what was inserted. Verified for real, driven, not just a
  config-value check: `tests/test_menu_structure.py` (extended) drives
  the real, un-mocked `show_text_dialog` (via a real `Toplevel.after()`
  scheduled callback, since the function itself blocks on a real modal
  `wait_window()`), resizes the real dialog narrower, and confirms the
  real, displayed line count actually grows (12 -> 40 for a long,
  synthetic paragraph) -- proof the re-flow is live, not assumed from
  the option alone. Verified live via noVNC too: dragging the real
  Help window narrower visibly re-flowed its own real text on the
  spot. Full suite re-run clean (58/58).
- **File > Create a New PDK.../Create a Blank PDK...** -- two new
  actions, per direct user request, pointing this whole app at a
  genuinely new `pdk_root`. **Create a Blank PDK...** builds the bare
  `libs.tech`/`libs.ref` directory shape and nothing else -- the same
  empty-project starting point several tests already built by hand.
  **Create a New PDK...** layers a real, minimal, immediately-usable
  skeleton on top: one real file per domain this project can create
  from scratch today (Layers `.lyp`, Magic Tech `.tech`, DRC deck,
  LEF), each written by the *exact* real `create_new_*` function (and
  real path convention) its own individual "New X File..."/"New DRC
  Deck" actions already use -- a real, deliberate scope match, since no
  writer here supports a brand-new Verilog/Liberty/CDL-SPICE/GDS/
  xschem/Qucs-S cell either (same honest gap the PDK Wizard's own
  legend already surfaces). Both share one new, real module,
  `pdklib/skeleton.py` (`build_blank_pdk`/`build_new_pdk_skeleton`) --
  reused by `test_drc_generate.py` and `test_pdk_wizard_empty.py`
  themselves (refactored to call it, per direct user request, instead
  of hand-rolling the same directory shape a second time) as well as
  by the new GUI actions, so there's one real source of truth for
  "empty starting point," not two independently-drifting copies.
  `self.pdk_root` turned out to be cached directly at construction time
  in nine separate view classes (unlike `project_root` above, reassigned
  live everywhere by `change_project_directory`) -- confirmed by reading
  every real call site before writing any code, not assumed -- so live
  reassignment wasn't a safe option here; per direct user choice, this
  instead tears down and rebuilds the whole `App` fresh
  (`_restart_with_pdk_root`: `self.destroy()` then `App(self.root,
  new_pdk_root)`), the same real construction `main.py`'s own entry
  point already uses. A non-empty target directory prompts for
  confirmation first; a `FileExistsError` from any real `create_new_*`
  call is surfaced as a real error dialog, not swallowed. Verified for
  real, driven: `tests/test_create_pdk.py` (new) -- `build_blank_pdk`
  produces genuinely zero domain files; `build_new_pdk_skeleton`'s four
  real files each parse back through their own real reader
  (`parse_tech_file`/`parse_lef_file`/`extract_design_rules`), and a
  real `App` constructed against them finds every one through the
  exact same discovery path (`find_lyp`/`load()`) a real, loaded PDK
  uses; the full, real GUI flow for both actions through mocked
  `filedialog`/`simpledialog`/`messagebox` dialogs, confirming the old
  `App` frame is genuinely destroyed (`winfo_exists()` false) and the
  new one's window title reflects the new `pdk_root`; declining the
  directory picker, the name prompt, or the non-empty-directory
  confirmation each leave the current app and target directory
  untouched. `tests/test_menu_structure.py` extended for the two new
  File entries. Full suite re-run clean (59/59).
- **`main.py wizard`**: a new CLI subcommand, per direct user request,
  starting a new PDK project headlessly -- no Tk/display needed -- the
  CLI equivalent of the GUI's own **File > Create a New/Blank PDK...**
  above, reusing the exact same `pdklib/skeleton.py` builders (one real
  source of truth, not a second implementation). `--pdk-root DIR`
  (the same global option every other command already takes, here used
  as the *destination* rather than an existing PDK to read) is where
  the new PDK is created; `--name` is saved as the project's own
  display name (`project_io.save_state`, unslugified) and, slugified
  (`_slugify_name`: lowercased, non-alphanumeric runs collapsed to one
  `_`), reused as the Layers/Magic Tech/LEF skeleton files' own
  technology name; `--blank` swaps in the bare `libs.tech`/`libs.ref`
  shape instead; a non-empty `--pdk-root` refuses unless `--force` is
  given -- the same real confirmation the GUI action already shows,
  translated to a CLI flag rather than a dropped safety check. Also
  generates the real, sourceable shell-env script (`pdklib/
  shell_env.py`, the same one Settings > Environment already exposes
  in the GUI) via a new `--env {save,print,skip}` option: `save`
  (default) writes `shell_env/pdk_env.sh` under the project root and
  reports its path; `print` writes *only* the raw script text to
  stdout (every other message moves to stderr instead), so the whole
  invocation can be sourced directly -- `source <(python3 main.py
  --pdk-root DIR wizard --name NAME --env print)`; `skip` does
  neither. `--open-gui` chains straight into the existing `cmd_gui` on
  the freshly created project. Every subcommand here (this one
  included) already gets a one-line description in `main.py --help`
  and its own full option list in `main.py wizard --help` for free,
  straight from `argparse`'s own real `help=` text -- nothing new to
  keep in sync by hand. The GUI's own Help dialog gained a matching
  "Command line" section pointing back at it. Verified for real,
  driven: `tests/test_wizard_cli.py` (new) -- calls `main.main(argv)`
  directly (not a subprocess) and asserts on the real, on-disk result:
  the default skeleton and `--blank` cases; `--name`'s exact,
  unslugified value round-tripping through `project_io.load_state`;
  the non-empty-directory guard refusing then `--force` proceeding
  alongside the pre-existing file; `--env save`'s script byte-for-byte
  matching `generate_shell_env_script`'s own real output and being
  executable; `--env print` putting *only* the script on stdout with
  status on stderr, and leaving the real, on-disk script from the
  `--env save` case earlier in the same run untouched; `--env skip`
  writing no script; `--open-gui` chaining into a monkeypatched
  `cmd_gui` (never a real, blocking Tk window); and `--name`
  slugification on a deliberately messy input
  (`"  Weird!! Name--123  "` -> `weird_name_123`). Like
  `test_change_project_directory.py`, temporarily redirects
  `export.PROJECT_ROOT`/`project_io.SAVE_DIR` to a throwaway directory
  for its own duration, since `--env save` otherwise writes into the
  real, shared `saves/`/`shell_env/` trees. Full suite re-run clean
  (60/60).
- **Create-from-scratch flows for Liberty/CDL-SPICE**, closing the
  last two "no create path" gaps the PDK Wizard's own legend used to
  flag. Three new, real `create_new_*` functions, matching each
  format's own real, confirmed on-disk convention (see each module's
  own top docstring, grounded in the real, downloaded IHP deck, not
  assumed): `pdklib/netlist.py`'s `create_new_cdl_file` (uppercase
  `.SUBCKT`/`.ENDS`, plus a real `*.PININFO` comment when at least one
  port's direction is known -- the same real, 100%-coverage convention
  every real `sg13g2_stdcell`/`sg13g2_io` CDL file already has) and
  `create_new_spice_file` (lowercase `.subckt`/`.ends`, deliberately no
  `*.PININFO` -- no real, downloaded SPICE file carries one either),
  and `pdklib/liberty.py`'s `create_new_liberty_file` (a real
  `library (NAME) { cell (NAME) { pin (NAME) { direction : DIR; } } }`
  skeleton -- real lookup-table timing data stays out of scope, the
  same bounded precedent as everywhere else in this project). No
  dedicated top-level tab was added for either domain -- unlike every
  other create-from-scratch domain, both stay only per-cell (By Cell
  for viewing, **Library Manager** for creating), the same real path
  Verilog/Verilog-A already established: `pdklib/library_index.py`'s
  `CREATABLE_VIEW_KINDS` grew from seven entries to ten, and
  `gui/library_manager_view.py`'s existing `_create_view_file`
  dispatcher (already generic over *ports*, already wired to
  `infer_ports_for_cell`) needed only three new `elif` branches, not a
  new mechanism -- the "real new picker UI" the previous version of
  this Future Work bullet called for turned out to already exist,
  confirmed by reading `library_manager_view.py` before writing a
  single line, not assumed missing. A newly created CDL/SPICE/Liberty
  view therefore gets the exact same real pin pre-population as
  Verilog/Verilog-A (LEF, then xschem symbol, then an existing
  same-name module -- `infer_ports_for_cell`'s own existing priority
  order, unchanged), and defaults to
  `<project_root>/libraries/<library>/<cell>.<ext>` like every other
  Library-Manager-created view kind except Verilog/Verilog-A's own
  `user_models/` default. The **PDK Wizard** tab's own Liberty/CDL-SPICE
  gap notes were updated to point at this real path (Library Manager's
  own **Create**) instead of the now-inaccurate "no in-GUI way to
  author one from scratch" -- still counted as a real gap from each
  stage's own linked tab (`("Cells", "By Cell")`, which itself has no
  create button), the same honest distinction `_status_lef` already
  draws between "some real create support exists" and "fully closed."
  Verified for real, driven: `tests/test_cdl_spice_liberty_editors.py`
  (new) -- each `create_new_*` function's own direct output round-trips
  correctly back through its own real parser (`find_cells` for both
  CDL/SPICE and Liberty), including the empty-ports case and CDL's
  real refusal to overwrite an existing file; a full, real GUI flow
  registers a hand-authored xschem symbol for a project cell, then
  drives **Create** for all three new view kinds through the real
  `library_manager_view.LibraryManagerView`, confirming the real pins
  (`IN`/`OUT`) are correctly pulled from that symbol into each new
  file (including CDL's own real `*.PININFO` line and SPICE's
  deliberate lack of one), and that all three land under
  `libraries/<library>/`, not `user_models/`. Full suite re-run clean
  (61/61).
- **Magic Tech write-back extended to Styles** -- the fifth editable
  domain, alongside Types/Planes/Contacts/Aliases (124 real entries in
  IHP's own `ihp-sg13g2.tech`). `StyleEntry` gained the same real
  `line_no` tracking as the other four (`pdklib/magic_tech.py`'s new
  `_parse_style_line`/`_parse_styles_with_lines`, reusing the existing
  shared `_scan_single_line_section` scanner unchanged), and
  `pdklib/magic_tech_writer.py` gained a fifth `_render_section_patch`
  region. A real structural difference from the other four surfaced
  Styles' own one real quirk: a `styles` section opens with one
  real, non-entry `styletype NAME` header line -- handled for free by
  `_scan_single_line_section`'s existing "not a real entry, copy the
  line verbatim" gap logic (`_parse_style_line` returns `None` for it),
  not a special case. A second, real, found-not-assumed bug while
  wiring this up: `StyleEntry.style_names` is the one editable field
  here that's a real, variable-length list rather than a scalar, and
  IHP's own real file genuinely column-aligns it with more than one
  space between names (`nfet      ntransistor    ntransistor_stripes`)
  -- a first, naive single-space `" ".join(...)` re-render collapsed
  that real spacing even on a completely unedited entry, caught
  immediately by this project's own no-edit-must-be-byte-identical
  check (`tests/test_magic_tech_writer.py`, already covering every
  domain generically). Fixed the same way `pdklib/liberty_writer.py`
  already handles its own per-field diffing: `_render_style_line` now
  compares the real style-name list against a fresh split of the
  original line first, and only re-joins with a single space when the
  list itself is genuinely different -- an untouched entry's real
  original inter-name whitespace is preserved exactly, only a real,
  deliberate edit gets freshly (and honestly) normalized spacing. The
  GUI side reuses the existing generic `gui/simple_list_editor.py`
  (`SimpleListEditor`) rather than a fifth hand-copy or a new "list
  field" capability added to that shared component: `StyleEntry` gained
  a `style_names_text` property (a plain, space-joined string
  getter/setter over the real `style_names` list) that the editor's
  own `getattr`/`setattr`-based field access already works with
  unmodified -- the same real "expose a list field as one delimited
  string" shape `AliasEntry.members_raw` already uses directly (that
  one just never needed splitting back into a real list). Persists
  across a relaunch the same way Planes/Contacts/Aliases do
  (`project_io.py`'s new `magic_styles`). Verified for real, driven:
  `tests/test_magic_planes_contacts_aliases.py` (extended) -- 124 real
  rows load; in-GUI edit/New/Delete Style; edits survive Save Edits and
  a simulated relaunch; a real `main.py export-magic-types` write-back
  afterward contains the edited style-name list; the real, non-entry
  `styletype mos` header line still comes through byte-for-byte
  verbatim. `tests/test_magic_tech_writer.py` re-confirms both real
  `.tech` files with a real `styles` section (`ihp-sg13g2.tech` and
  `ihp-sg13g2-GDS.tech`, the latter with no real `include` line at all)
  still export byte-identical with zero edits, catching the exact real
  bug above. Full suite re-run clean (61/61).
- **Magic Tech write-back extended to Compose/Connect** -- the sixth
  and seventh editable domains, closing what was originally grouped
  with the "much harder mini-DSL sections" in this bullet's own
  earlier text. **Actually reading `ComposeStatement`/`ConnectRule`
  closely, not just trusting their old grouping, found they're both
  exactly as flat as Planes/Contacts/Aliases**: every real `compose`
  line is a fixed 4-token `verb arg1 arg2 arg3` (535-591 in IHP's own
  `ihp-sg13g2.tech`), every real `connect` line a fixed 2-token
  `types_a types_b` (597-621) -- both sit well before the file's first
  real `include` line, the same safely-mappable region every other
  editable domain already relies on, and neither carries a real
  non-entry header line the way `styles` does. `pdklib/magic_tech.py`
  gained `_parse_compose_line`/`_parse_compose_with_lines` and
  `_parse_connect_line`/`_parse_connect_with_lines`, both thin wrappers
  around the existing, unmodified `_scan_single_line_section` scanner
  -- no new parsing machinery needed. `pdklib/magic_tech_writer.py`
  gained two more `_render_section_patch` regions: Compose's own
  four-token line reuses `_render_contact_line`'s exact real approach
  (capture each real original separator, always reuse it verbatim
  regardless of which token changed -- safe here, unlike Styles'
  own bug, since every token slot is fixed and none of them packs a
  variable-length list); Connect needed nothing more than
  `_render_alias_line`'s own shape (`name`, separator, one raw `rest`
  string) since `types_a`/`types_b` are already plain strings, not
  lists. The GUI side reuses `SimpleListEditor` again: `ConnectRule`
  needed no new property at all (both fields already plain strings);
  `ComposeStatement`'s own fixed `args` 3-tuple gained `arg1`/`arg2`/
  `arg3` properties (getters/setters over the tuple), the same real
  "expose a non-string field as a plain string for the generic editor"
  shape `StyleEntry.style_names_text` already established. One real,
  necessary adaptation in `project_io.py`: `yaml.safe_dump` has no
  default representer for a plain Python tuple, so `magic_compose`'s
  own serialization casts `args` to a real list before dumping (and
  back to a tuple on load) -- found by reasoning about the real
  serialization path before writing it, not by a failed test. Persists
  across a relaunch via `project_io.py`'s new `magic_compose`/
  `magic_connect`, same as every other domain. A pre-existing test
  (`test_magic_new_tabs.py`) referenced the old, now-removed read-only
  `compose_tree`/`connect_tree` widgets directly; updated to the new
  `compose_editor.tree`/`connect_editor.tree` paths, same real
  underlying Treeview. Verified for real, driven:
  `tests/test_magic_planes_contacts_aliases.py` (extended) -- 39 real
  Compose rows and 20 real Connect rows load; in-GUI edit (including a
  Compose `arg2` edit through its own property) /New/Delete for both;
  edits survive Save Edits and a simulated relaunch; a real `main.py
  export-magic-types` write-back afterward contains the edited values.
  `tests/test_magic_tech_writer.py` re-confirms both real `.tech`
  files still export byte-identical with zero edits -- Compose/Connect
  needed no Styles-style whitespace-preservation fix, confirmed rather
  than assumed, since both are genuinely fixed-token-count lines with
  no variable-length blob to collapse. Full suite re-run clean
  (61/61). Verified live via noVNC too: both new tabs show a real
  list+form editor identical in shape to Planes/Contacts/Aliases, and
  a live field edit (Compose's own Arg 2) persists correctly across a
  sub-tab switch.
- **Magic Tech write-back extended to cifinput's own ignored-layers
  and layer-hints tables** -- and, as a real, necessary consequence,
  **the Technology picker now shows every real `.tech` file, not just
  the two with their own real `tech`/`version` header.** A real
  structural fact drove the whole design here, found before writing
  any code, not assumed: `cifinput`/`cifoutput` don't live in
  `ihp-sg13g2.tech` at all -- they're spliced in from two separate
  real files, `ihp-sg13g2-cifin.tech`/`ihp-sg13g2-cifout.tech`, via
  `include`, and (confirmed real) neither of those two, nor
  `ihp-sg13g2-drc.tech`/`ihp-sg13g2-extract.tech`, has its own real
  `tech`/`version` header -- so `tech.name` comes back empty for all
  four, and the Technology picker's own `if tech.name:` filter was
  silently hiding them entirely. Since `pdklib/magic_tech.py`'s own
  `find_tech_files`/`parse_tech_file` already parse each real `.tech`
  file completely independently regardless of picker visibility, the
  real fix turned out to be small: `gui/magic_tech_view.py`'s own
  `load()` now falls back to the real file's own stem as a display
  name (`tech.name or path.stem`) instead of skipping a nameless real
  file, and the same one-line fix was applied to `main.py`'s own
  `cmd_export_magic_types` and `export.py`'s own `export_full_pdk`
  smoking-gun test, for CLI/GUI parity and so the smoking-gun test
  genuinely exercises the new writer path too. This closes what would
  otherwise have been a real, first-of-its-kind problem for this
  project -- write-back needing to target a *different* real file than
  the one being viewed -- for free: `ihp-sg13g2-cifin.tech` (confirmed
  real: no `include` line of its own) is safely, fully line-mapped
  when parsed *as that file directly*, the exact same
  `_safe_prefix_line_count`/`safe_through` machinery every other
  domain already uses, so `render_tech_file(tech.source_path, tech)`
  for *that* parse naturally patches the right real file with no new
  mechanism. When `cifinput` is instead parsed as part of
  `ihp-sg13g2.tech`'s own combined view, its real lines correctly land
  past that file's own `safe_through` boundary, so this domain's own
  `line_no`/section bounds correctly come back `0` there and write-back
  for *that* file correctly leaves it untouched -- confirmed for real,
  driven, not just asserted. `CifInputIgnoredLayer` (new) and
  `CifInputLayerHint` (extended) both gained real `line_no` tracking
  via two thin wrappers around the existing, unmodified
  `_scan_single_line_section` scanner, same as every prior domain.
  **A real, new wrinkle these two share with each other that no prior
  domain had**: both live inside *one* real `cifinput`...`end` section
  (alongside the real, still-read-only `layer`/`templayer` recipe
  blocks) rather than each owning an exclusive section -- patching them
  independently, one full section-rewrite per sub-structure, would
  have silently discarded whichever one ran second. `pdklib/
  magic_tech_writer.py`'s own `_render_section_patch`/`render_tech_file`
  were generalized to take a real list of *groups* -- multiple,
  independently-tracked `(entries, all_line_nos, render_fn)` tuples
  sharing one real section -- merged into one real, combined pass;
  every other, single-group domain just wraps its own tuple in a
  one-element list now, unchanged in every other respect. **A second
  real, new wrinkle**: `CifInputLayerHint.gds_layer`/`gds_datatype` are
  the first `int`/`int | None`-typed editable fields anywhere in this
  module (every prior `SimpleListEditor`-backed domain is all-string)
  -- exposed to the generic editor through new `gds_layer_text`/
  `gds_datatype_text` properties (the latter also round-tripping the
  real file's own wildcard `*` convention through `gds_datatype is
  None`), same real "expose a non-string field as plain string"
  pattern as `StyleEntry.style_names_text`/`ComposeStatement.arg1`,
  with invalid mid-edit text simply ignored (keeps the last real,
  valid value) rather than raising out of a Tk trace callback. **A
  real, found-not-assumed formatting bug along the way**: some real
  `calma NAME LAYER DATATYPE` lines in `ihp-sg13g2-cifin.tech` carry a
  real trailing space (e.g. `calma DIFFFILL 1 22 `) -- an initial
  regex that didn't capture it silently dropped it even on a
  completely unedited line, caught immediately by this project's own
  no-edit-must-be-byte-identical check against the real file, fixed by
  capturing and preserving the real trailing whitespace explicitly.
  Verified for real, driven: `tests/test_magic_cifinput.py` (new) --
  the Technology picker now lists all 6 real `.tech` files (previously
  2); `ihp-sg13g2-cifin`'s own 23 real ignored layers and 133 real
  layer hints load correctly; in-GUI edit (including the real
  int/wildcard round-trips)/New/Delete for both; edits survive Save
  Edits and a simulated relaunch, keyed by the real fragment file's
  own name; a real `export_magic_types` write-back lands the edited
  values in `ihp-sg13g2-cifin.tech` specifically, while
  `ihp-sg13g2.tech`'s own export -- confirmed byte-identical to the
  real original -- is completely unaffected; the same real
  fallback-naming logic `main.py`'s own `export-magic-types` uses
  finds the fragment too. `tests/test_magic_tech_writer.py` and
  `main.py export-magic-types`'s own live run both re-confirm all 6
  real `.tech` files (up from 2) still export byte-identical with zero
  edits. Verified live via noVNC too: the Technology dropdown lists
  all 6 real files, `ihp-sg13g2-cifin`'s own CIF Input tab shows two
  real, working list+form editors side by side, and a live wildcard
  edit (`0` -> `*`) reflects correctly in the row immediately. Full
  suite re-run clean (62/62).

## Future work

The stated end goal is much bigger than this first increment: an
application that can create/edit/generate arbitrary PDK file types
(Magic technology files, KLayout DRC decks, LEF, GDS, Liberty, SPICE
models, ...), not just read/display layers. Concretely, still open:

- The much larger real remainder of
  `drc` (`surround`/`edge4way`/`cifmaxwidth`/`variants`/`widespacing`/
  `cifwidth`/`cifspacing`/... -- `width`/`spacing`/`maxwidth`/`angles`
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
  geometry -- is done: `pdklib/gds.py`, via `klayout.db`. Real
  `compose`/`connect` sections, and the dominant `width`/`spacing`
  patterns in `drc`, and `resist`/`planeorder` in `extract`, are also
  done -- see `magic_tech.py`'s own docstring for exact real coverage.
  LEF's own real `VIA`/`ViaRULE` via-stack geometry is also done:
  `pdklib/lef.py`, displayed read-only in the LEF tab's own **Vias**
  sub-tab. Liberty's own real pin/timing-arc scalar data --
  direction/capacitance/function per pin, related_pin/timing_type/
  timing_sense/when per
  timing arc -- is also done: `pdklib/liberty.py`.)
- Wider KLayout DRC-deck coverage: `pdklib/drc.py` now extracts two
  reliable patterns -- `width()`/`space()`/`sep()` and `.enclosed()` --
  -> `.output()` (75 real rules total); the other 86 real,
  honestly-skipped constructs are multi-step composite/derived checks
  (angle/acute-corner checks, antenna-ratio accumulation, density
  windows, ...) with no single reliable, generic pattern left to
  extract -- re-checked a second time (not just assumed still true):
  real `.without_bbox_width()` occurs exactly once deck-wide (not worth
  a pattern), and every real method-chain shape used across the
  remaining skipped constructs was tallied deck-wide with no one shape
  dominating the way `width`/`space`/`sep`/`enclosed` did. Some (e.g.
  real `NW.b1`) could in principle resolve via real data-flow tracing
  through arbitrary `.join()`/`.and()`/... composition, but that's
  real, separate, higher-risk future work -- a wrong trace would
  silently attach the wrong value to a rule, unlike an honestly-skipped
  one.
- Native write-back serialization: **done for every currently
  structured-editable domain** -- LEF pins (`pdklib/lef_writer.py`,
  verified against all 32 real files), DRC Rules (`pdklib/drc_writer.py`,
  verified against all 27 real files with an extracted rule), Magic
  Types/Planes/Contacts/Aliases (`pdklib/magic_tech_writer.py`, verified
  against both real technologies' `.tech` files -- see the dedicated
  bullet below for Planes/Contacts/Aliases), CDL/SPICE/Verilog ports
  (`pdklib/netlist_writer.py`/`pdklib/verilog_writer.py`, verified against
  all 30 real `.cdl` + 1 real `.spice` + 35 real `.v` files), Liberty
  pin/timing-arc data (`pdklib/liberty_writer.py`, verified against all
  97 real `.lib` files, 700 real cells), and Layers
  (`pdklib/layers_writer.py`, verified against the real 377-layer
  `sg13g2.lyp`) -- every one byte-identical with no edits, plus real,
  driven edit round-trips, and independently re-verified faithful
  across the *entire* real PDK at once via `main.py export-full`'s own
  smoking-gun round-trip test (`export.py`, `Export > Export Edited ...`,
  `main.py export-lef`/`export-drc`/`export-magic-types`/
  `export-netlist`/`export-verilog`/`export-liberty`/`export-layers`).
  What's left is everything that's still read-only in its own
  structured view -- Magic Tech's remaining eleven real sub-tabs (see
  the dedicated bullet below for exactly which, and why they're a
  deliberately different, harder shape) -- for the same reason: no
  editor -> no write-back path to build. GDS stays read-only by design
  (real structural info only, no geometry-editing feature exists or is
  planned this pass); Liberty's own real lookup-table sub-groups stay
  unmodeled for the same bounded-scope reason as everywhere else, not
  because a pin/timing-arc editor doesn't exist anymore.
- **Magic Tech write-back extended to Planes/Contacts/Aliases** --
  three more of the fifteen real sub-tabs are now editable, alongside
  Types. **A real, confirmed structural fact made this tractable
  without repeating `_safe_prefix_line_count`'s own real
  include-splicing caution per domain**: `planes` (83-98)/`types`
  (104-260)/`contact` (266-298)/`aliases` (304-382) all sit in
  `ihp-sg13g2.tech` well before its first real `include` line,
  confirmed by direct inspection -- so all four share the exact same
  real `safe_through` boundary already established for Types alone,
  needing no new per-domain complexity. `PlaneEntry`/`ContactEntry`/
  `AliasEntry` each gained a real `line_no` field, populated by one
  new, shared `_scan_single_line_section` helper (`pdklib/magic_tech.py`)
  generalizing `_parse_types_with_lines`'s own real line-tracking
  approach for domains whose every real entry sits on exactly one
  line (unlike `types`' own plane+alias-list shape, which keeps its
  own bespoke parser, unchanged). `pdklib/magic_tech_writer.py`'s own
  `render_tech_file` was generalized the same way, from a
  Types-only patch into a shared `_render_section_patch` applied to
  up to four active, non-overlapping real regions in one combined
  pass, sorted by real file order -- confirmed real, driven: **all 6
  real `.tech` files still export byte-identical with no edits**, and
  a real edit/add/delete round-trip across Planes+Contacts+Aliases
  simultaneously left Types/Compose/Connect and every untouched real
  entry in the same file completely unaffected. The GUI side reuses a
  new, generic `gui/simple_list_editor.py` (`SimpleListEditor`) --
  list + form + New/Delete/Filter, the same commit-on-switch pattern
  as Types' own bespoke editor, but written once and parameterized by
  column/field names rather than hand-copied three more times, since
  all three of these domains are flat, plain-string-field dataclasses
  (unlike Types' own comma-split aliases list and boolean obsolete
  combo, which stay hand-written). Planes/Contacts/Aliases edits also
  now persist across a relaunch via `saves/*.yaml`
  (`project_io.py`'s own `magic_planes`/`magic_contacts`/
  `magic_aliases`, alongside the existing `magic_types`), not just
  Types -- confirmed for real, driven: an edited plane/contact/alias
  survives `File > Save Edits` and a simulated relaunch, and a real
  `main.py export-magic-types` write-back afterward contains exactly
  those edited values. **Deliberately still out of scope this pass**
  (documented honestly, not silently dropped): `CifInputRecipe`
  (cifinput's own real `layer`/`templayer` recipe blocks) and `CifLayer`
  (cifoutput's own real layer/datatype mapping), plus `drc`/`extract`'s
  own remaining mini-DSL content -- none of these fit the "one flat
  entry per line" shape this pass's shared machinery relies on (both
  `CifInputRecipe`/`CifLayer` specifically merge real content across
  more than one non-contiguous real block sharing the same name, a
  genuinely harder write-back shape); each would need its own real
  editor design, real separate future work. (Styles/Compose/Connect/
  cifinput's own two flat sub-structures, once also in this list, are
  done -- see the dedicated changelog entries below; Compose/Connect/
  cifinput's ignored-layers/layer-hints turned out to be exactly as
  flat as Planes/Contacts/Aliases once actually read closely, not the
  harder shape they were originally grouped with.)
- "Pre-pointed" Magic/KLayout launch guidance is back in
  `eda_tools.py`, pointed at real files this project has since
  downloaded and read: Magic launches with IHP's own real, official
  `libs.tech/magic/ihp-sg13g2.magicrc` via the exact invocation
  IHP's own `README.md` documents verbatim (`-d XR -rcfile ...`);
  KLayout launches with IHP's own real `sg13g2.lyp` layer-properties
  file via `-l`, a real, stable KLayout flag -- honestly scoped to
  layer display only, not the full real DRC-deck/technology
  registration (no single-flag KLayout switch for that was
  found/verified). Both fall back to a bare, unconfigured launch if
  the real file isn't there yet (`LaunchGuidance.requires_path`).
- The **Simulation** top-level GUI group now has four real sub-tabs --
  **ngspice Models** (`pdklib/spice_models.py`, real `.model`/`.subckt`
  extraction), **xschem** (`pdklib/xschem.py`/`pdklib/xschem_sch.py`, real
  symbol and schematic extraction, see their own bullets), **Qucs-S**
  (see the dedicated bullet below), and **User Models** (see the
  user-defined Verilog/Verilog-A bullet below). ngspice's own real
  `.LIB NAME ... .ENDL` PVT-corner blocks are now done too
  (`pdklib/spice_models.py`'s own `Corners` sub-tab).
- **Qucs-S's own real component/symbol data is done** --
  `pdklib/qucs_sym.py`, hand-verified against all real, downloaded
  `libs.tech/qucs-s/symbols/` files. **A real, confirmed structural
  fact worth stating plainly, found before writing a single parser
  line**: this one real directory holds *two* genuinely different real
  formats sharing one file location, not one -- `.xml` (34 real
  files): a real, single-root, well-formed `<Component>` XML document
  (library/description/models, real `Parameters` each with a real
  `name`/`unit`/`show` plus either a real `default_value` or a real
  `equation` -- confirmed real variance, 177 of 188 real parameters
  carry the former, the other 11 the latter, never both -- real
  `Netlists`' `NgspiceNetlist`/`CDLNetlist`/optional `XyceNetlist`
  template strings, kept raw, and a reference to exactly one real
  `.sym` geometry file, confirmed to resolve for all 34 real files);
  `.sym` (22 real files, 350 real drawing primitives): a flat sequence
  of real, individually well-formed, self-closing tags -- Qucs-S's own
  real *drawn* geometry, confirmed genuinely different from xschem's
  own `.sym` as already flagged (real `<PortSym x=... y=... type=...
  angle=... [condition=...]/>` primitives carry no real port name at
  all, 66 real ports total). Unlike this project's other real
  XML-*shaped* format (KLayout's own `.lyp`, hand-rolled because
  write-back needs real line numbers), the standard
  `xml.etree.ElementTree` is used directly here -- this domain is
  read-only, confirmed to parse all 34 real `.xml` files with zero
  failures. **A real parsing bug found and fixed by a driven count
  check, not assumed correct**: a first-draft primitive scanner
  required a real drawing tag to be the *entire* line, undercounting
  ports 46-of-66 and primitives 330-of-350 -- traced to a real,
  partial convention this format actually uses, a trailing XML comment
  naming the physical pin (e.g. `<PortSym .../> <!--D-->`, confirmed
  present on 20 of the 66 real port lines, absent on the other 46) --
  fixed by relaxing the scanner to match just the tag itself and
  separately capture that comment as an honestly-partial `hint` field,
  not a real port-name substitute. A real, optional `condition=`
  attribute on a drawing primitive marks it as belonging to only one
  real symbol variant (e.g. a real BJT's own `npn`/`pnp` geometry) --
  the Qucs-S schematic-capture analog of Magic's own `variants`
  conditional-scoping construct, recorded raw, not evaluated.
  `gui/qucs_view.py` mirrors `xschem_view.py`'s own two-pane shape:
  **Components** (Overview/Parameters/Netlists sub-tabs, its own file
  picker over all 34 real files) and **Symbols** (a real Ports table,
  its own file picker over all 22 real files). `main.py qucs` gives
  the same real summary on the CLI. Verified for real, driven in the
  container: real counts match ground truth exactly (34 components,
  188 parameters, 22 symbols, 350 primitives, 66 ports, 20 hinted), a
  spot-checked real component (`nmos.xml`) and its own real symbol
  (`Mos.sym`, all 8 real ports correctly hinted `D`/`G`/`S`/`B` across
  its two real `nmos`/`pmos` variants) both render correctly.
- **Qucs-S Components and Symbols both gained real editors with
  write-back.** **Components > Parameters**: a real Parameter's own
  `default_value`/`equation` is editable; `pdklib/qucs_component_writer.py`
  patches it via a real, surgical text scan for each real
  `<Parameter ...>` opening tag's own real character span (confirmed
  real: not always a single physical line -- a long real `equation=`
  value can wrap the tag across several, e.g. `rhigh.xml`'s own real
  `R` parameter). Standard `xml.etree.ElementTree` stays for *reading*
  only; write-back deliberately avoids a full ElementTree
  re-serialization, the same real risk (reformatting attribute
  order/quoting/whitespace) that already ruled out ElementTree for
  KLayout's own real `.lyp` write-back. Real Parameters are matched to
  their own real file position strictly by order (no other stable real
  identity exists, and this project's own editor never adds/deletes/
  reorders one). **Symbols > Ports**: real `PortSym`
  `x`/`y`/`type`/`angle`/`condition` are editable (the real, partial
  `hint` comment stays read-only, preserved verbatim); New/Delete Port
  supported. `pdklib/qucs_sym_writer.py` handles write-back, reusing the
  same "unchanged -> keep the real original line verbatim" discipline
  `pdklib/verilog_writer.py` already established -- **a real, column-
  alignment formatting bug was found and fixed by this project's own
  byte-identical check**: some real files pad extra spaces between
  attributes for visual alignment (`Varicap.sym`'s own real ports,
  confirmed), which a naive always-regenerate approach silently
  collapsed even for an untouched port; fixed by only ever
  regenerating a port's own line when it's genuinely edited. **A
  second, more consequential real bug was found the same way**: 5 real
  files (`cap_cmim.xml`/`cap_rfcmim.xml`/`svaricap.xml`/
  `Capacitor.sym`/`rfcmim.sym`) use real, consistent CRLF (`\r\n`) line
  endings -- `Path.read_text()`'s own universal-newline translation
  (relied on by every writer here) silently discards this real
  distinction before a writer ever sees it, and, just as with the
  earlier real trailing-newline bug, every writer's own narrower
  per-file test happened to read *both* sides through the same
  translation, masking the exact difference it should have caught;
  only `main.py export-full`'s own smoking-gun round-trip test (a raw,
  untranslated `diff -rq --no-dereference`) caught it. Fixed once,
  shared (`pdklib/text_utils.py`'s new `restore_crlf_if_needed`, checking
  the real source file's own raw bytes directly), not per-writer.
  `gui/qucs_view.py` gained real forms for both (New/Delete Port for
  Symbols; Components' own read-only Overview/Netlists sub-tabs
  unchanged), and both share the parent `App`'s own per-file cache
  (`get_parsed_qucs_symbol`/`get_parsed_qucs_component`), the same
  "switching files and back never discards an edit" discipline
  everywhere else. `main.py export-qucs-sym`/`export-qucs-component`
  and their own `Export` menu entries add CLI/GUI parity. Verified for
  real, driven in the container: byte-identical no-edit export for all
  22 `.sym` + 34 `.xml` files (confirmed via raw bytes, not
  `read_text()`, after the CRLF fix), real edit/add/delete round-trips
  for both domains, and a full, complete-PDK, two-generation
  `export-full` smoking-gun round-trip producing zero differences.
- **Every file picker across xschem/Qucs-S can now create a brand-new
  real file, not just edit an existing one** -- each combobox is
  editable (not a closed real-file list); its own button reads **Edit
  File** for a real, existing typed/selected path, or **Create File**
  for one that doesn't exist yet, writing a real, minimal, valid
  skeleton via a new `create_new_*` function per domain
  (`pdklib/xschem.py`/`pdklib/xschem_sch.py`/`pdklib/qucs_sym.py`) -- a real
  xschem `.sym`/`.sch` header (`v`/`G`/`K`/`V`/`S`/`E`), an empty real
  Qucs-S `.sym`, or a real, valid `<Component>` skeleton, each
  confirmed to parse cleanly before shipping. A newly created file
  becomes real, ordinary editable content immediately -- xschem
  Symbols/Qucs-S Symbols accept New Pin/New Port right away; a new
  Qucs-S Component's own Description/Models/Netlists (no structured
  editor exists for those) can still be filled in via the same **Edit
  File** dialog's own raw-text Edit/Save, the same as any other real,
  downloaded file. `gui/file_picker_utils.py` shares this logic across
  all four panes rather than four hand-copies, and refuses a typed
  path that resolves outside the real PDK tree (e.g. via `..`) before
  ever writing anything. Verified for real, driven in the container:
  the button reads correctly for both an existing and a new name, a
  directory-traversal Create attempt is correctly blocked (confirmed
  no file written anywhere), and all four domains' Create actions each
  produce a real file that re-parses cleanly and immediately accepts
  further edits through the existing editors.
- **A real, shared, interactive graphical editor -- not just tables --
  now covers every real drawn-geometry domain: xschem Symbols,
  xschem Schematics, and Qucs-S Symbols.** One canvas widget
  (`gui/geometry_canvas.py`) is reused across all three (Qucs-S
  Components has no geometry of its own to edit) via a small,
  per-domain adapter layer (`gui/geometry_adapters.py`) that's the
  *only* place any real file format's own field names are known --
  the canvas itself works with one shared, format-agnostic
  `GeometryItem` shape.

  **Real geometry parsing came first**, extending every domain's own
  real parser to capture drawing primitives this project had
  deliberately left unparsed until now ("structure, not graphics," the
  precedent this very feature request superseded): `pdklib/xschem.py`
  gained real `XschemLine`/`XschemArc`/`XschemText`/`XschemBox`
  (plus real pin *geometry*, not just name/direction) -- verified
  against ground truth exactly (1,222 lines/145 arcs/851 texts/378
  `B` primitives, matching a real, hand-verified inverter symbol's own
  5 lines/1 arc/4 texts/2 pins one-for-one). `pdklib/xschem_sch.py`
  gained the same four shape kinds for a schematic's own real embedded
  decorative geometry (66 lines/0 arcs/112 texts/87 boxes, confirmed
  once `start_page.sch` -- the same real top-level-exception file
  found earlier -- was included in the ground truth). `pdklib/qucs_sym.py`
  gained real `QucsLine`/`QucsArc`/`QucsText` (253/8/23 real
  primitives, summing with the existing 66 real ports to exactly the
  already-known 350 real primitive total).

  **Real write-back for all of it**, extending every existing writer
  rather than adding new ones: `pdklib/xschem_writer.py` now patches pin
  *position* (previously name/direction only) and every new shape
  kind, using the same real "unchanged -> keep the original line
  verbatim" discipline throughout, since a real pin/text primitive can
  carry real properties beyond what's modeled (`goto=`/`propag=`/
  `sim_pinnumber=`/`layer=`, all confirmed real) that must survive a
  position-only edit untouched. `pdklib/xschem_sch_writer.py` gained
  instance position/rotation/flip write-back and, newly, **real
  New Instance/New Wire support** -- deliberately *not* offered by
  this project's own first-pass Schematics editor (no sensible way to
  choose a real position), now real and safe because the graphical
  canvas *is* that sensible way. `pdklib/qucs_sym_writer.py` gained
  Line/Arc/Text write-back with the same real, per-attribute
  column-alignment preservation already established for ports.
  Verified byte-identical against every real file in all three domains
  with no edits, plus real add/move/delete round-trips for every new
  shape kind including new-instance placement referencing a real
  symbol and new-wire drawing.

  **The canvas itself** (`gui/geometry_canvas.py`): a **Select** tool
  (click to select/drag to move any real shape, `Delete`/`BackSpace`
  to remove it) and **Line**/**Arc**/**Text** tools (click, or
  click-drag for Line/Arc, to place a real new shape -- Arc defaults
  to a real full circle, adjustable afterward). Schematics additionally
  get **Instance** (pick a real `.sym` from the whole downloaded
  symbol library via a real, filterable picker dialog, then click a
  position) and **Wire** (click two points) tools. Every edit mutates
  the exact same real, live domain object every other tab already
  shares (the same `App`-owned per-file cache discipline as
  everywhere else) -- a canvas drag/delete immediately updates the
  matching Pins/Instances/Wires table too, confirmed for real, driven
  in the container (deleting a pin on the canvas removes it from the
  Pins table; deleting/moving a wire updates the Wires table's own
  position columns). Verified end-to-end, driven, in the container:
  real scene population matches exact real shape counts for a
  hand-verified real inverter (symbol *and* schematic), dragging a
  real pin/port moves the real underlying object, drawing a new real
  Line/Arc/Text/Wire adds a real shape, placing a new real Instance
  (with a mocked symbol-picker dialog) adds a real, correctly-
  positioned `XschemInstance` referencing a real symbol, deleting a
  selected real shape removes it and keeps every table in sync, and a
  real write-back export afterward reflects every one of these edits
  correctly -- plus the existing `test_by_cell_and_settings.py`/
  `test_magic_new_tabs.py` regressions and a full, complete-PDK,
  two-generation `export-full` smoking-gun round-trip still producing
  zero differences.
- **xschem's own real schematic (`.sch`) files, as opposed to `.sym`
  symbols, are done** -- `pdklib/xschem_sch.py`, hand-verified against
  all 100 real, downloaded `.sch` files (99 real, one level under a
  family directory, plus one real, genuine exception,
  `start_page.sch`, sitting directly at the xschem root itself --
  found by cross-checking a full recursive real-file listing against
  a first-draft, naive one-level-deep glob before trusting a count,
  and now handled by `find_sch_files`). Reuses `pdklib/xschem.py`'s own
  real, quote-aware brace scanner and key=value parser directly rather
  than duplicating them, since a `.sch` file shares the same top-level
  `TAG {content}` primitive shape as a `.sym`, plus two schematic-only
  real primitives: `C {symbol_ref} x y rot flip {props}` component
  instances (1{,}920 real lines total, once the `start_page.sch` gap
  above was fixed -- a first count attempt landed at 1{,}905 and was
  traced to the exact same missed-file bug) and
  `N x1 y1 x2 y2 {props}` wire segments (1{,}979 real lines). A
  component instance's own symbol reference is confirmed real to
  resolve relative to `libs.tech/xschem/` itself, not the containing
  `.sch` file's own directory; 34 of 204 real, unique referenced
  symbols never resolve inside the downloaded PDK at all (xschem's own
  bundled pin/ground/generic-device symbols, referenced both bare and
  under a real `devices/` prefix) -- reported honestly via
  `resolved_path is None`, not treated as a parsing gap. A schematic's
  own exposed ports are identified by real, stable convention (an
  instance whose symbol stem is `ipin`/`opin`/`iopin`) -- **a real,
  driven cross-check against the matching `.sym`'s own Pins tab found
  a genuine, honest discrepancy, not agreement**: `sg13g2_inv_1.sch`'s
  four real pin instances (`Y`/`A`/`VDD`/`VSS`) are a real superset of
  its own `.sym`'s two real drawn ports (`A`/`Y` only) -- the symbol
  doesn't draw `VDD`/`VSS` as explicit visible pins, but the
  schematic instantiating real devices still wires real power rails to
  them; recorded as the real fact it is rather than silently claimed
  to match. `gui/xschem_view.py`'s **Simulation > xschem** tab gained
  a second major sub-tab, **Schematics** (its own file picker over all
  100 real files, with **Instances**/**Pins**/**Wires** sub-tabs,
  the Instances tab showing each real symbol reference's PDK-vs-
  external resolution at a glance), alongside the existing **Symbols**
  sub-tab (unchanged, confirmed still correct post-refactor). `main.py
  xschem-sch` gives the same real summary on the CLI. Verified for
  real, driven in the container: real counts match a corrected,
  independent grep-based ground truth exactly (100 files, 1{,}920
  instances, 1{,}979 wires, 34 unique external references), a spot-
  checked real file's Instances/Pins/Wires rows and PDK/external
  resolution flags are individually correct, and `start_page.sch`
  (the real top-level exception file) parses without error.
- **xschem Symbols and Schematics both gained real editors with
  write-back**, matching every other structured domain's own "list +
  form, commit-on-switch, then a real, patched export" pattern.
  **Symbols > Pins** reuses `port_editor.PortEditor` directly, unmodified
  -- `XschemPin`'s own real `name`/`direction` fields duck-type exactly
  onto what `PortEditor` already expects, needing zero new editor code.
  `pdklib/xschem_writer.py` writes real edits back (name/direction only;
  pin geometry and every other real `B`-primitive property stay
  untouched), verified byte-identical against all 202 real files with
  no edits, plus a real rename/redirect/add/delete round-trip.
  **Schematics** gained **editable Instances** (real `name=`, and for a
  real pin instance its real net label) and **Wires** (real `label=`)
  -- Delete only, deliberately no "New Instance/Wire": a real component
  needs a real symbol reference and real drawn position to mean
  anything, and this project has no schematic geometry editor to place
  one sensibly. `pdklib/xschem_sch_writer.py` handles write-back, reusing
  the same real `_C_HEAD_RE`/`_C_TAIL_RE`/`_N_HEAD_RE` matching
  `pdklib/xschem_sch.py`'s own parser already uses -- **a first-draft,
  naive raw-character brace scan was replaced after it corrupted real
  files during byte-identical verification**, and a second, deeper
  real bug was found the same way: 27 real files (26 under
  `sg13g2_tests_xyce/` plus `start_page.sch`) embed a
  `simulator_commands_shown.sym` instance whose own multi-line
  `value="..."`/`tclcommand="..."` text ends with a real, doubled
  quote-then-close-brace idiom (`"\n"}`, confirmed present verbatim by
  direct search) that even the parser's own quote-aware scanner
  (`pdklib/xschem.py`'s `_scan_braced`) cannot safely disambiguate --
  without real xschem's own source to confirm the intended grammar,
  two real, computable safety signals (overlapping parsed entry ranges;
  an odd unescaped-quote count within one entry's own text -- zero
  false positives across the whole downloaded deck) now detect every
  real occurrence and refuse to touch exactly the affected entry (or,
  when the mis-scan swallows a whole sibling instance, the whole file)
  rather than risk silent corruption -- every other real entry in an
  affected file still patches normally. Verified byte-identical against
  all 100 real files with no edits (after both fixes), plus a real
  rename/net-label-edit/delete round-trip, and a full, complete-PDK,
  two-generation `export-full` smoking-gun round-trip still producing
  zero differences. `main.py export-xschem-sym`/`export-xschem-sch`
  and `Export > Export Edited xschem Symbols/Schematics` add CLI/GUI
  parity with every other write-back domain.
- **User-defined Verilog/Verilog-A model inclusion, plus a way to link
  it to the rest of the PDK, is done** -- see the
  `pdklib/user_models.py`/`gui/user_models_view.py` bullet in "What's
  real here" for the full real design and verification. `main.py
  user-models` gives the same listing on the CLI. Its own three
  follow-ons are now done too: **editing a model's own ports** from
  inside **Simulation > User Models** (an **Edit Ports** button opens
  the same real port editor CDL/SPICE/Verilog already use, then writes
  straight back to the real, local `.v`/`.va` source via
  `pdklib/verilog_writer.py` -- unlike the real, downloaded PDK's own
  views, a user model's own file *is* the user's live edit surface, so
  there's no separate export step); **batch-relinking many modules at
  once** (the tree is real Tk `extended`-select, so Ctrl/Shift-clicking
  several rows and one **Save Link** applies the same cell name to all
  of them; a separate **Link All Auto-Matches** button freezes every
  row's *current* implicit name-match into an explicit, persisted link
  in one save -- confirmed idempotent once every row already has one);
  and **real ngspice/OSDI simulation-tool wiring** for Verilog-A
  modules (`pdklib/user_models.py`'s own `osdi_snippet`, rendered via a
  new, generically reusable `gui/text_dialog.py` -- a read-only modal
  for generated text with no real backing file, distinct from
  `file_view_dialog.py`'s own real-file view/edit/save dialog) -- not a guess,
  but IHP's own real, documented two-step workflow reproduced verbatim
  (confirmed against `libs.tech/verilog-a/README.md`,
  `openvaf-compile-va.sh`, and the real `osdi '...'` lines already
  present in IHP's own `libs.tech/ngspice/.spiceinit`): compile the
  real `.va` source to a binary OSDI module via OpenVAF, then load it
  into ngspice with its own real `osdi` command -- ngspice has no way
  to load raw Verilog-A source directly, so a plain digital Verilog
  module correctly raises rather than fabricating an equivalent
  recipe that doesn't exist in this PDK's own real toolchain.
  Verified for real, driven in the container: a batch Save Link across
  two selected modules, Link All Auto-Matches (and its idempotence),
  an Edit Ports write-back confirmed by re-reading the real `.va` file
  afterward, a real, correctly-worded OSDI snippet, and the plain-Verilog
  rejection path.
- **Copy-vs-share with `OpenPDKCreator`, revisited and re-confirmed**:
  diffed every genuinely-copied file against `OpenPDKCreator`'s own
  current originals rather than assuming. The core data shapes
  (`models.Layer`, `models.DesignRule`) are still byte-for-byte
  identical -- a real, still-valid shared seam -- but everything
  *around* them has diverged in concrete, structural ways since this
  project started: `schema.py`'s `CHECK_TYPES` there has grown a
  `csv_check_type` field this project never needed plus two entirely
  separate registries (`PARAMETER_TYPES`, `DEVICE_EXTRACTION_TYPES`)
  for memristor-specific compact-model data this project has no
  equivalent of; `eda_tools.py`'s own `LaunchGuidance` gained a new
  `requires_path` field here (see the Magic/KLayout launch-guidance
  entry above) that `OpenPDKCreator`'s copy doesn't have, and each
  project's `TOOL_REGISTRY` now points real launch guidance at
  genuinely different real files (`openmempdk.lyp` vs. `sg13g2.lyp`);
  `layers_view.py` gained a live filter/search box here (see the GUI
  structure section) with no equivalent upstream. **Verdict: keep
  copying.** The still-shared surface (two dataclasses) is too small
  to justify a shared-package dependency between two projects whose
  actual missions -- one memristor-specific end product, one general
  multi-PDK authoring tool -- keep pulling the surrounding code in
  different directions; introducing a shared library now would mean
  either splitting `schema.py`'s registries apart or forcing one
  project's `LaunchGuidance` shape onto the other, real refactoring
  work for a benefit that's mostly just avoiding ~150 lines of
  duplication. Worth re-checking again if the *data models themselves*
  (not just the code around them) start to diverge.
- **Create-from-scratch flows for Liberty/CDL-SPICE -- done** (see the
  dedicated changelog entry below): the two domains this bullet used to
  track are no longer a real gap, closed the same way Verilog/Verilog-A
  were -- through the **Library Manager** tab's own **Create**, not a
  new, dedicated top-level tab. LEF is not among them either for its
  own macro-level content -- see **New Macro...** above; `ORIGIN`/
  `SITE` still aren't modeled on a macro, real, separate future work.
- **Real Ruby generation for DRC Rules' remaining three
  `check_type`s** (`max_current_density`/`max_dimension`/
  `density_window`) -- half of the original six are now done (see the
  changelog entry below); these three still have no real, local
  ground truth found for a single-method KLayout shape (`density_window`
  in particular is a genuinely multi-step real computation in this same
  deck -- window tiling, material-area-over-window-area ratio, then a
  threshold compare -- not one method call). A **New Rule** of one of
  these three is still real, editable metadata -- it just can't be
  exported into a runnable check yet, reported honestly (rule ID +
  reason) rather than silently dropped.
## License

Apache-2.0 (see `LICENSE`) -- matching `OpenPDKCreator`, the project
some of this code was copied from. IHP-Open-PDK itself (fetched
locally, never committed here) is also Apache-2.0 -- see
`github.com/IHP-GmbH/IHP-Open-PDK`'s own `LICENSE`.

"""Magic Tech tab: real, parsed Magic ``.tech`` data
(``openpdkcreator/pdklib/magic_tech.py``), one real technology at a time.

**The Technology picker now shows every real ``.tech`` file found**,
not just the two with their own real ``tech``/``version`` header
(``ihp-sg13g2``/``ihp-sg13g2-GDS`` for IHP). The other four
(``ihp-sg13g2-cifin``/``-cifout``/``-drc``/``-extract``) are real
fragment files, ``include``d into ``ihp-sg13g2.tech`` and never meant
to carry their own header -- ``tech.name`` genuinely comes back empty
for them, so ``load()`` falls back to the real file's own stem as a
display name instead (``tech.name or path.stem``), rather than
inventing a fake real name on the parsed model itself. This used to
filter them out of the picker entirely; now they're real, independently
selectable/editable technologies in their own right, since
``pdklib/magic_tech.py``'s own ``parse_tech_file`` already parses each
real ``.tech`` file completely on its own regardless of picker
visibility -- confirmed real, not assumed: none of the four fragments
has an ``include`` line of its own, so each one's *own* real content is
safely, fully line-mapped when parsed as that file directly (see
``pdklib/magic_tech_writer.py``'s own docstring for exactly why this
matters for write-back).

A sub-`Notebook` per real, tabular data domain -- planes/types/
contacts/aliases/styles/compose/connect/**CIF Layers**/**CIF Input**/
**CIF Input Recipes**, plus **DRC (Magic)**/**Extract**/**Extract
Coefficients**/**Extract Devices**/**Extract Misc** (real
``cifinput``'s own recipe blocks/``drc``/``extract`` section content --
see ``pdklib/magic_tech.py``'s own docstring for exactly what's
extracted from each and why). **Types**/**Planes**/**Contacts**/
**Aliases**/**Styles**/**Compose**/**Connect**/**CIF Input**'s own two
flat sub-panes (ignored layers, layer hints)/**CIF Input Recipes**'s
own header fields/**CIF Layers**/**Extract Misc**/**Extract
Coefficients**/**Extract Devices**/**Extract**'s own **Plane order**
and **Sheet resistance** sub-panes/**DRC (Magic)**'s own **angles**
and **width/spacing/maxwidth** sub-panes are editable -- every real
construct this module recognizes in `extract`/`drc` is now editable,
no read-only sub-tab remains in either domain; **CIF Input Recipes**
alone is still split, its own real op content staying read-only (see
``CifInputRecipeBlock``'s own docstring, in ``pdklib/magic_tech.py``,
for why only the header fields are safe to edit). Types keeps its
own hand-written list + form pane (a real
comma-split aliases list, a boolean obsolete combo); every other one
shares one generic, reusable `simple_list_editor.SimpleListEditor`
instead (flat, plain-string-field dataclasses, a clean fit for one
shared implementation rather than a hand-copy per domain of the same
commit-on-switch pattern ``LayersView``/``RulesView``/``LefView``
already use) -- a non-string real field is always exposed to this
string-only editor through a real Python property, never edited
directly: Styles' own real `type_name -> list[style_names]` list field
(``StyleEntry.style_names_text``), Compose's own fixed `args` 3-tuple
(``ComposeStatement.arg1``/``arg2``/``arg3``), and CIF Input's/CIF
Layers' own real `int`/`int | None` fields -- the first ``int``-typed
editable fields anywhere in this module (``CifInputLayerHint.
gds_layer_text``/``gds_datatype_text``, the latter also round-tripping
the file's own real wildcard ``*`` convention; ``CifOutputLayerMapping.
gds_layer_text``/``gds_datatype_text``, no wildcard concept there) --
all the same real "expose a non-string field as a plain string for the
generic editor" shape ``AliasEntry.members_raw`` already uses directly
(that one just never needed converting back into anything more
structured). Compose/Connect turned out to be exactly as flat as
Planes/Contacts/Aliases once actually read closely -- a fixed 4-token
line and a fixed 2-token line respectively -- despite initially
looking like they belonged with the harder mini-DSL sections; CIF
Input's own ignored-layers/layer-hints tables are just as flat
individually, but real-world messier in two ways neither of those was:
they share one real section with each other (and with the real, still-
read-only ``layer``/``templayer`` recipe blocks -- see ``pdklib/
magic_tech_writer.py``'s own docstring for how write-back handles a
shared section), and they don't even live in the same real file as
most of what's editable above (see this docstring's own opening
paragraph). **CIF Layers is a real, deliberate exception to every
other editable domain here**: unlike them, it supports editing an
*existing* ``calma`` line's own real layer/datatype in place, but no
New/Delete at all (``SimpleListEditor``'s own new ``allow_new_delete=
False`` -- the buttons don't exist, not just disabled) -- a real
``calma`` line means nothing without the real geometry recipe
(``shrink``/``or``/``bloat-all``/...) leading up to it, which this
project has no way to author, so a brand-new entry has no coherent
real write-back target (see ``CifOutputLayerMapping``'s own
docstring). It's also flattened to one real row per real ``calma``
line, not one row per Magic type name (the same real name can appear
on more than one row -- e.g. real ``DNWELL``, built across two
separate real ``layer DNWELL ...`` blocks -- rather than merging them
into one row with an inner list, the shape this domain used to have
before write-back). ``CifInputRecipe`` (cifinput's own real recipe
blocks) stays read-only for now, and for a genuinely harder reason
than CIF Layers: real content merges across more than one
non-contiguous real block sharing the same name, *and* the current
data model doesn't even track which block each real op line came from
-- a real write-back would need a data-model redesign first, real
separate future work. **Extract Misc** (``ExtractMiscStatement`` --
``contact``/``devresist``/``antenna``/``disconnect``/``substrate``
statements) turned out to be another real, flat, editable domain once
looked at closely, despite living in the same real ``extract`` section
as several still-read-only constructs (``resist``/``order``/cap-
coefficients/``device``) -- the same "flat, one real line per entry"
shape ``SimpleListEditor`` already fits, with its own variable-length
``args`` tuple exposed via ``args_text``, the same pattern
``StyleEntry.style_names_text`` already established. A real ``contact``
line can repeat once per real ``variants(...)`` PVT-corner block with a
different value each time (the same real fact ``resist`` shares, still
undocumented as a check here) -- each real occurrence is just its own
independently-editable row, no attempt made to resolve which corner it
belongs to. **Extract**'s own **Plane order** sub-pane
(``ExtractPlaneOrder`` -- real ``planeorder NAME ORDER`` lines) is
editable the same way, sharing that same real ``extract`` section with
Extract Misc -- confirmed real to sit entirely before the section's
own first real ``variants (...)`` line, so (unlike ``contact``) it
never has a real per-corner repeat; its own ``int``-typed ``order``
field is exposed via ``order_text``, the same "expose a non-string
field as a plain string" pattern as everywhere else in this module.
**Extract**'s own **Sheet resistance** sub-pane (``ExtractResist`` --
real ``resist LAYER_SPEC VALUE`` lines) is also editable, the third
real group sharing that same ``extract`` section -- unlike
``planeorder``, a real ``resist`` line *does* repeat once per real
``variants(...)`` corner block (the same real fact ``contact``
shares), handled the same independently-editable-row way; its own
``int``-typed ``milliohms_per_square`` field is exposed via
``milliohms_text``. **Extract Coefficients** (``ExtractCapCoefficient``
-- real `default*` parasitic-capacitance directives) is the fourth
real group sharing that section: unlike the other three, its own
trailing content is a variable-length blob (per-directive token
count, split into a real ``args`` tuple and a real ``values`` float
tuple), exposed to this generic editor through two properties,
``args_text``/``values_text`` -- the same "expose a non-string field
as a plain string" pattern, just applied twice to one entry. A real
`default*` entry can also repeat once per real ``variants(...)``
corner block, the same real fact ``resist``/``contact`` share.
**Extract Devices** (``ExtractDevice`` -- real
``device <class> <model> <type> ...`` statements) is the fifth and
last real group sharing that section, and the only one whose own real
entries can span more than one real physical line (a trailing ``\\``
continuation -- confirmed real for 5 of the real 50 entries, every
real ``msubcircuit`` MOSFET): tracked by a real ``(start_line,
end_line)`` range rather than a single ``line_no``, mirroring
``pdklib/lef.py``'s own ``LefMacro.all_parsed_pin_ranges`` real
range-tracking precedent, and its own trailing ``rest`` tuple is
exposed via ``rest_text``. An unchanged, real multi-line entry's own
original wrapping/indentation is preserved completely verbatim; a
real, deliberate edit collapses it to one freshly formatted line
rather than attempting to reproduce the original author's own real
line-wrapping choice. Every real ``extract``-section construct this
parser recognizes is now editable -- this domain has no remaining
read-only sub-tab of its own. **DRC (Magic)**'s own **angles** sub-pane
(``MagicAngleCheck``) and **width/spacing/maxwidth** sub-pane
(``MagicDrcCheck``) are the same real ranged shape as Extract Devices
(``allm7`` and 70 of the real 192 ``MagicDrcCheck`` entries also wrap
across real physical lines) -- both share
``pdklib/magic_tech_writer.py``'s own ``_render_section_patch``'s
*range_groups* mechanism, generalized once and reused here rather than
rebuilt each time. ``MagicDrcCheck`` needed a real prerequisite first
(a new ``filler_raw`` field capturing the real ``mode``/exception-list
text those lines routinely carry, previously discarded entirely) --
see ``MagicAngleCheck``'s own docstring (``pdklib/magic_tech.py``) for
the full real reasoning. A third, wide pane below the two covers every
other real drc-section keyword at once -- ``surround``/``edge4way``/
``widespacing``/``cifmaxwidth``/``cifwidth``/``cifspacing``/``area``/
``exact_overlap``/``overhang``/``extend``/``rect_only``/``cifarea``/
``no_overlap`` (``MagicDrcMiscStatement``, 148 real lines across 13
real directives, none dominant enough to justify its own bespoke
parser the way ``width``/``spacing``/``maxwidth`` share one -- kept
fully raw and positional instead, edited as ``directive``/``args_text``,
the same "don't guess further" shape ``ComposeStatement``/``Extract
Misc`` already established; see that dataclass's own docstring, in
``pdklib/magic_tech.py``, for exactly why real ``variants``/``style``/
``scalefactor``/``cifstyle`` lines are deliberately excluded -- a
different real *kind* of line, section-level scope/config, not a
per-rule check). Every real construct both `extract` and
`drc` parse is now editable -- neither section has any remaining
read-only content of its own (real ``surround``/``edge4way``/
``variants``/... constructs used to be flagged as unparsed entirely;
now every one of the 13 real per-rule keywords is parsed and editable
too, real ``variants``/``style``/``scalefactor``/``cifstyle`` still
deliberately unparsed since they're a different kind of content, not
merely a differently-shaped one). **CIF Input Recipes**
(``CifInputRecipeBlock``) is editable in a more limited, deliberate
way: only its own real header fields (``name``/``kind_text``/
``base_layer``), not its own real op content, which stays read-only in
a separate ``Treeview`` for reference -- see that dataclass's own
docstring for why. Every other remaining domain across the rest of
Magic Tech stays read-only (each would need its own real editor design
-- the genuinely harder mini-DSL sections aren't a clean fit for any
existing editor shape; see README's own Future Work). Editing is
in-memory, same as
DRC Rules/LEF pins, with native write-back into the real ``.tech``
file via ``pdklib/magic_tech_writer.py`` (``File > Export Edited Magic
Types``/``main.py export-magic-types`` -- despite the menu/command
label, this now writes back every editable domain at once, not just
Types). "View
File" opens the real, underlying ``.tech`` file directly
(``file_view_dialog.view_file_dialog``), which *can* be edited, as raw
text.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from ..pdklib import drc_bridge
from ..pdklib import magic_tech as magic_tech_mod
from .file_view_dialog import view_file_dialog
from .list_filter import build_filter_row, matches
from .simple_list_editor import SimpleListEditor

OBSOLETE_VALUES = ("", "yes")


class MagicTechView(ttk.Frame):
    def __init__(self, parent, pdk_root: Path, app=None):
        super().__init__(parent)
        self.pdk_root = pdk_root
        self.app = app
        """The owning ``gui/app.py`` ``App`` -- only needed for **Copy
        to DRC Rules** (``drc_bridge.py``'s own real bridge into
        ``app.project.layers``/``design_rules`` and ``app.rules_view``'s
        own real refresh), so ``None`` is accepted for a standalone/test
        instantiation that never clicks that one button."""
        self.technologies: dict[str, magic_tech_mod.MagicTechnology] = {}
        self.current_type: magic_tech_mod.TypeEntry | None = None
        self._suspend_trace = False
        self._type_filter_query = ""

        self._build()
        self.load()

    # -- layout -----------------------------------------------------------

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="Technology:").pack(side="left")
        self.tech_var = tk.StringVar()
        self.tech_combo = ttk.Combobox(top, textvariable=self.tech_var, state="readonly", width=24)
        self.tech_combo.pack(side="left", padx=(4, 12))
        self.tech_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_all())

        ttk.Button(top, text="View File", command=self._view_file).pack(side="left")
        ttk.Button(top, text="New .tech File...", command=self._new_tech_file).pack(side="left", padx=(6, 0))

        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, anchor="w").pack(side="left", fill="x", expand=True)

        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.planes_editor = self._build_simple_editor(
            sub, "Planes", [("name", "Name", 200), ("short_code", "Short Code", 100)],
            lambda: magic_tech_mod.PlaneEntry(name="newplane", short_code="np"),
            entry_label="Plane",
            help_text="Real Magic .tech plane: 'name, short_code'.",
        )
        self._build_types_tab(sub)
        self.contacts_editor = self._build_simple_editor(
            sub, "Contacts",
            [("contact_type", "Contact Type", 140), ("layer1", "Layer 1", 160), ("layer2", "Layer 2", 160)],
            lambda: magic_tech_mod.ContactEntry(contact_type="newcontact", layer1="", layer2=""),
            entry_label="Contact",
            help_text="Real Magic .tech contact: 'type layer1 layer2'.",
        )
        self.aliases_editor = self._build_simple_editor(
            sub, "Aliases", [("name", "Name", 200), ("members_raw", "Members", 460)],
            lambda: magic_tech_mod.AliasEntry(name="newalias", members_raw=""),
            entry_label="Alias",
            help_text="Real Magic .tech alias: 'name member1,member2,...'.",
        )
        self.styles_editor = self._build_simple_editor(
            sub, "Styles", [("type_name", "Type Name", 200), ("style_names_text", "Style Names (space-separated)", 460)],
            lambda: magic_tech_mod.StyleEntry(type_name="newtype", style_names=[]),
            entry_label="Style",
            help_text="Real Magic .tech style: 'type_name style1 style2 ...'.",
        )
        self.cif_layers_editor = self._build_simple_editor(
            sub, "CIF Layers",
            [("name", "Name", 200), ("gds_layer_text", "GDS Layer", 100), ("gds_datatype_text", "GDS Datatype", 100)],
            None,
            entry_label="Layer Mapping",
            help_text="Real cifoutput 'calma LAYER DATATYPE' inside a 'layer'/'templayer' NAME block. "
                      "Edit an existing mapping's own layer/datatype -- no New/Delete: a new one needs a real "
                      "geometry recipe (shrink/or/bloat-all/...) this project doesn't author.",
            allow_new_delete=False,
        )
        self._build_cifinput_tab(sub)
        self._build_cifinput_recipes_tab(sub)
        self.compose_editor = self._build_simple_editor(
            sub, "Compose",
            [("verb", "Verb", 100), ("arg1", "Arg 1", 140), ("arg2", "Arg 2", 140), ("arg3", "Arg 3", 140)],
            lambda: magic_tech_mod.ComposeStatement(verb="paint", args=("a", "b", "c")),
            entry_label="Compose Statement",
            help_text="Real Magic .tech compose statement: 'compose|decompose|paint arg1 arg2 arg3'.",
        )
        self.connect_editor = self._build_simple_editor(
            sub, "Connect", [("types_a", "Types A", 330), ("types_b", "Types B", 330)],
            lambda: magic_tech_mod.ConnectRule(types_a="newtype", types_b="newtype"),
            entry_label="Connect Rule",
            help_text="Real Magic .tech connectivity rule: 'types_a types_b' (each a comma-separated type list).",
        )
        self._build_drc_tab(sub)
        self._build_extract_tab(sub)
        self.extract_coeff_editor = self._build_simple_editor(
            sub, "Extract Coefficients",
            [("directive", "Directive", 140), ("args_text", "Args", 220), ("values_text", "Values", 160)],
            lambda: magic_tech_mod.ExtractCapCoefficient(directive="defaultareacap", args=(), values=()),
            entry_label="Cap Coefficient",
            help_text="Real extract-section 'default*' parasitic-capacitance coefficient line "
                      "('defaultoverlap'/'defaultsideoverlap'/'defaultareacap'/'defaultperimeter'/"
                      "'defaultsidewall'). Argument semantics aren't asserted -- edited raw and positional. "
                      "A real entry can repeat once per real variants(...) corner block -- each row here is "
                      "its own independently-editable real line, not resolved to a specific corner.",
        )
        self.extract_devices_editor = self._build_simple_editor(
            sub, "Extract Devices",
            [("devclass", "Devclass", 110), ("model", "Model", 160), ("type_name", "Type", 110),
             ("rest_text", "Rest", 400)],
            lambda: magic_tech_mod.ExtractDevice(devclass="mosfet", model="None", type_name="newtype", rest=()),
            entry_label="Device",
            help_text="Real extract-section 'device <class> <model> <type> ...' statement. Argument semantics "
                      "past the first three tokens aren't asserted -- edited raw and positional. A real entry "
                      "can span more than one real physical line (a trailing '\\' continuation) -- editing it "
                      "collapses it to one fresh line, the original multi-line wrap isn't reproduced.",
        )
        self.extract_misc_editor = self._build_simple_editor(
            sub, "Extract Misc", [("directive", "Directive", 110), ("args_text", "Args", 500)],
            lambda: magic_tech_mod.ExtractMiscStatement(directive="contact", args=()),
            entry_label="Extract Misc Statement",
            help_text="Real extract-section 'contact|devresist|antenna|disconnect|substrate ...' statement. "
                      "A real 'contact' entry can repeat once per real variants(...) corner block -- each row "
                      "here is its own independently-editable real line, not resolved to a specific corner.",
        )

    def _build_drc_tab(self, notebook: ttk.Notebook):
        """Real ``width``/``spacing``/``maxwidth``/``angles`` DRC
        statements from the ``drc`` section -- both are now editable
        (see ``MagicDrcCheck``'s own docstring, in
        ``pdklib/magic_tech.py``, for the real ``mode``/exception-list
        filler that had to be captured into ``filler_raw`` first, and
        ``MagicAngleCheck``'s own for why ``angles`` needed no such
        prerequisite). A third, wide pane below covers every other real
        drc-section keyword (``surround``/``edge4way``/``widespacing``/
        ``cifmaxwidth``/... -- see ``MagicDrcMiscStatement``'s own
        docstring for the full real list and why they share one flat,
        raw/positional shape rather than a bespoke parser each)."""

        frame = ttk.Frame(notebook)
        notebook.add(frame, text="DRC (Magic)")
        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)
        frame.rowconfigure(3, weight=1)

        checks_header = ttk.Frame(frame)
        checks_header.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Label(checks_header, text="width/spacing/maxwidth:").pack(side="left")
        ttk.Button(
            checks_header, text="Copy to DRC Rules", command=self._copy_drc_check_to_rule,
        ).pack(side="right")
        checks_frame = ttk.Frame(frame)
        checks_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 4))
        self.drc_checks_editor = SimpleListEditor(
            checks_frame,
            [("check_type", "Check Type", 80), ("layers_text", "Layers", 200), ("value_text", "Value Um", 70),
             ("filler_raw", "Mode/Exceptions", 160), ("message", "Message", 280)],
            lambda: magic_tech_mod.MagicDrcCheck(
                check_type="width", layer_args=[["newlayer"]], value_um=0.0, message="new message",
                rule_ids_raw=None,
            ),
            entry_label="DRC Check",
            help_text="Real drc-section 'width|spacing|maxwidth LAYERS VALUE [mode] \"MESSAGE\"' statement. "
                      "'Layers' is one comma-separated real type-list for width/maxwidth, two ' | '-separated "
                      "lists for spacing -- typed here directly, or picked via 'Select Layers...' below the "
                      "Layers field (a real multi-select against this technology's own current, real Type "
                      "names -- Ctrl+click to union several onto one side; one list box per real side, two "
                      "for spacing). "
                      "'Mode/Exceptions' is the real, raw mode/exception-list text between "
                      "the value and the message (e.g. 'touching_ok') -- edited raw and positional, argument "
                      "semantics aren't asserted. A real rule ID lives inside the message's own trailing "
                      "'(...)' -- edit the message directly to change it. 'Copy to DRC Rules' above sends the "
                      "selected row into the real, unrelated KLayout DRC-deck rule model (Technology > DRC "
                      "Rules) when -- and only when -- the two real dialects actually agree on what the check "
                      "means; see that button's own real coherence-check messages for anything it won't copy.",
            combo_fields={"check_type": (magic_tech_mod.DRC_CHECK_TYPES, True)},
            field_buttons={"layers_text": ("Select Layers...", self._select_drc_check_layers)},
            help_popup=True,
        )
        self.drc_checks_editor.pack(fill="both", expand=True)

        ttk.Label(frame, text="angles:").grid(row=0, column=1, sticky="w")
        angles_frame = ttk.Frame(frame)
        angles_frame.grid(row=1, column=1, sticky="nsew")
        self.drc_angles_editor = SimpleListEditor(
            angles_frame, [("layer", "Layer", 120), ("degrees_text", "Degrees", 60), ("message", "Message", 260)],
            lambda: magic_tech_mod.MagicAngleCheck(layer="newlayer", degrees=90, message="new message"),
            entry_label="Angle Check",
            help_text="Real drc-section 'angles LAYER DEGREES \"MESSAGE\"' statement.",
            combo_fields={"layer": ((), False)},
            help_popup=True,
        )
        self.drc_angles_editor.pack(fill="both", expand=True)

        ttk.Label(
            frame, text="surround/edge4way/widespacing/cifmaxwidth/cifwidth/cifspacing/area/"
                        "exact_overlap/overhang/extend/rect_only/cifarea/no_overlap:",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        misc_frame = ttk.Frame(frame)
        misc_frame.grid(row=3, column=0, columnspan=2, sticky="nsew")
        self.drc_misc_editor = SimpleListEditor(
            misc_frame, [("directive", "Directive", 110), ("args_text", "Args", 600)],
            lambda: magic_tech_mod.MagicDrcMiscStatement(directive="surround", args=()),
            entry_label="DRC Statement",
            help_text="Every other real drc-section statement -- 'DIRECTIVE ARG1 ARG2 ...', kept fully raw and "
                      "positional (argument semantics vary too much per directive to assert, same 'don't guess "
                      "further' discipline as Compose/Extract Misc). A trailing quoted message, when present, "
                      "is just more whitespace-split tokens in Args -- edited as one plain string.",
            combo_fields={"directive": (magic_tech_mod.DRC_MISC_DIRECTIVES, True)},
            help_popup=True,
        )
        self.drc_misc_editor.pack(fill="both", expand=True)

    def _build_extract_tab(self, notebook: ttk.Notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Extract")
        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="Sheet resistance (real per-layer, milliohms/square):").grid(
            row=0, column=0, sticky="w", padx=(0, 4)
        )
        resist_frame = ttk.Frame(frame)
        resist_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 4))
        self.extract_resist_editor = SimpleListEditor(
            resist_frame, [("layer_spec", "Layer Spec", 220), ("milliohms_text", "milliohms/sq", 100)],
            lambda: magic_tech_mod.ExtractResist(layer_spec="(newlayer)/metal1", milliohms_per_square=0),
            entry_label="Resist Entry",
            help_text="Real extract-section 'resist LAYER_SPEC VALUE' line (milliohms/square). "
                      "A real layer can repeat once per real variants(...) corner block -- each row "
                      "here is its own independently-editable real line, not resolved to a specific corner.",
        )
        self.extract_resist_editor.pack(fill="both", expand=True)

        ttk.Label(frame, text="Plane order:").grid(row=0, column=1, sticky="w")
        order_frame = ttk.Frame(frame)
        order_frame.grid(row=1, column=1, sticky="nsew")
        self.extract_plane_order_editor = SimpleListEditor(
            order_frame, [("name", "Name", 140), ("order_text", "Order", 60)],
            lambda: magic_tech_mod.ExtractPlaneOrder(name="newplane", order=0),
            entry_label="Plane Order Entry",
            help_text="Real extract-section 'planeorder NAME ORDER' line.",
        )
        self.extract_plane_order_editor.pack(fill="both", expand=True)

    def _build_cifinput_tab(self, notebook: ttk.Notebook):
        """Real, editable list+form panes for cifinput's own two flat
        sub-structures, side by side -- unlike every other
        ``SimpleListEditor`` use in this file, these two share one
        real ``cifinput``...``end`` section (with each other, and with
        every real ``layer``/``templayer`` recipe block's own header,
        also editable -- see ``_build_cifinput_recipes_tab`` below)
        rather than each owning an exclusive section; see
        ``pdklib/magic_tech_writer.py``'s own docstring for how
        write-back handles that."""

        frame = ttk.Frame(notebook)
        notebook.add(frame, text="CIF Input")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)

        ignore_frame = ttk.Frame(frame)
        ignore_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.cifinput_ignore_editor = SimpleListEditor(
            ignore_frame, [("name", "Ignored Layer", 200)],
            lambda: magic_tech_mod.CifInputIgnoredLayer(name="NEWLAYER"),
            entry_label="Ignored Layer",
            help_text="Real cifinput 'ignore LAYERNAME' -- skipped entirely on CIF/GDS read.",
        )
        self.cifinput_ignore_editor.pack(fill="both", expand=True)

        hints_frame = ttk.Frame(frame)
        hints_frame.grid(row=0, column=1, sticky="nsew")
        self.cifinput_hints_editor = SimpleListEditor(
            hints_frame,
            [("name", "Name", 160), ("gds_layer_text", "GDS Layer", 90), ("gds_datatype_text", "GDS Datatype", 90)],
            lambda: magic_tech_mod.CifInputLayerHint(name="NEWLAYER", gds_layer=0, gds_datatype=0),
            entry_label="Layer Hint",
            help_text="Real cifinput 'calma NAME LAYER DATATYPE' -- standalone (not nested in a recipe). "
                       "Datatype '*' means any.",
        )
        self.cifinput_hints_editor.pack(fill="both", expand=True)

    def _build_cifinput_recipes_tab(self, notebook: ttk.Notebook):
        """cifinput's own ``layer``/``templayer`` recipe blocks -- one
        real entry per real block *occurrence* (``CifInputRecipeBlock``,
        not merged by name -- see that dataclass's own docstring in
        ``pdklib/magic_tech.py``). **Editable header fields only**
        (``name``/``kind_text``/``base_layer``) in the left-hand
        ``SimpleListEditor``, ``allow_new_delete=False`` since a
        brand-new block with no real op content would be functionally
        inert, the same real reasoning ``CifOutputLayerMapping``'s own
        edit-in-place-only mode already established. Real op content
        stays read-only, shown for reference (not editing) in the
        right-hand ``Treeview`` -- ``SimpleListEditor`` has no concept
        of a read-only column, so real op content that can't safely be
        edited here stays in a genuinely separate, non-form widget
        rather than a form field that looks editable but silently
        isn't."""

        frame = ttk.Frame(notebook)
        notebook.add(frame, text="CIF Input Recipes")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)

        editor_frame = ttk.Frame(frame)
        editor_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.cifinput_recipes_editor = SimpleListEditor(
            editor_frame, [("name", "Name", 140), ("kind_text", "Kind", 90), ("base_layer", "Base Layer", 160)],
            None,
            entry_label="Recipe Block",
            help_text="Real cifinput 'layer|templayer NAME BASE' recipe block header -- one real entry per "
                      "real block occurrence (a real name can appear more than once). Real op content "
                      "(right) stays read-only -- this project doesn't model or author real geometry-boolean "
                      "op semantics well enough to safely let one be added here.",
            allow_new_delete=False,
        )
        self.cifinput_recipes_editor.pack(fill="both", expand=True)

        self.cifinput_recipes_tree = self._make_tab_tree(
            frame, ("name", "kind", "base_layer", "ops"), (140, 90, 160, 400), column=1,
        )

    def _make_tab_tree(
        self, frame: ttk.Frame, columns: tuple[str, ...], widths: tuple[int, ...], column: int,
    ) -> ttk.Treeview:
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col, width in zip(columns, widths):
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=width, anchor="w")
        tree.grid(row=0, column=column, sticky="nsew")
        return tree

    def _make_tab(self, notebook: ttk.Notebook, title: str, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col, width in zip(columns, widths):
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        return tree

    def _build_simple_editor(
        self, notebook: ttk.Notebook, title: str, columns: list[tuple[str, str, int]],
        new_entry_factory, entry_label: str, help_text: str, allow_new_delete: bool = True,
    ) -> SimpleListEditor:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        editor = SimpleListEditor(
            frame, columns, new_entry_factory, entry_label=entry_label, help_text=help_text,
            allow_new_delete=allow_new_delete,
        )
        editor.pack(fill="both", expand=True)
        return editor

    def _build_types_tab(self, notebook: ttk.Notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Types")
        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)

        button_row = ttk.Frame(frame)
        button_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(button_row, text="New Type", command=self._new_type).pack(side="left")
        ttk.Button(button_row, text="Delete Type", command=self._delete_type).pack(side="left", padx=(6, 0))
        self.type_filter_var = build_filter_row(button_row, self._on_type_filter_changed)

        columns = ("plane", "name", "aliases", "obsolete")
        self.types_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        for col, width in zip(columns, (120, 160, 300, 80)):
            self.types_tree.heading(col, text=col.replace("_", " ").title())
            self.types_tree.column(col, width=width, anchor="w")
        self.types_tree.grid(row=1, column=0, sticky="nsew")
        self.types_tree.bind("<<TreeviewSelect>>", self._on_type_select)

        right = ttk.Frame(frame)
        right.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(8, 0))
        right.columnconfigure(1, weight=1)

        self.type_vars: dict[str, tk.StringVar] = {}
        form_row = 0

        def add_entry(field, label):
            nonlocal form_row
            ttk.Label(right, text=label).grid(row=form_row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_type_field_changed)
            ttk.Entry(right, textvariable=var).grid(row=form_row, column=1, sticky="ew", pady=2)
            self.type_vars[field] = var
            form_row += 1

        def add_combo(field, label, values, readonly=False):
            nonlocal form_row
            ttk.Label(right, text=label).grid(row=form_row, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            var.trace_add("write", self._on_type_field_changed)
            combo = ttk.Combobox(
                right, textvariable=var, values=values,
                state="readonly" if readonly else "normal",
            )
            combo.grid(row=form_row, column=1, sticky="ew", pady=2)
            self.type_vars[field] = var
            form_row += 1
            return combo

        # Not readonly: a new type can reference a plane not yet
        # created elsewhere (this project has no real Planes editor
        # yet -- see README's Future Work).
        self.type_plane_combo = add_combo("plane", "Plane", ())
        add_entry("name", "Name (canonical)")
        add_entry("aliases", "Aliases (comma-separated)")
        add_combo("obsolete", "Obsolete ('-' prefix)", OBSOLETE_VALUES, readonly=True)

        ttk.Label(
            right, text="Real Magic .tech type: 'plane name,alias1,alias2' --\n"
            "a leading '-' marks it obsolete/internal.",
            foreground="#666", wraplength=260, justify="left",
        ).grid(row=form_row, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _select_drc_check_layers(self):
        """A real multi-select popup for the selected check's own
        ``layer_args`` -- one real ``tk.Listbox`` (``selectmode=
        "extended"``, real Ctrl+click/Shift+click multi-select) per
        real side (one for ``width``/``maxwidth``, two for
        ``spacing``), listing this technology's own current, real
        Type names, pre-selecting whichever ones this check's own
        ``layer_args`` already names on that side. **Apply** writes
        the selection straight back as ``layer_args`` -- a real,
        comma-joined union per side when more than one real type is
        Ctrl+click-selected, exactly ``layers_text``'s own existing
        real format, just built from a real, closed list instead of
        hand-typed. A real type no longer among this technology's own
        current Types (renamed/removed since this check was last
        edited) still shows, pre-selected, as its own extra real row
        -- real, current state is never silently dropped just because
        this popup can't offer it as a fresh pick."""

        self.drc_checks_editor.commit_pending_edits()
        check = self.drc_checks_editor.current_entry
        if check is None:
            messagebox.showinfo("Select Layers", "Select a width/spacing/maxwidth check first.", parent=self)
            return
        tech = self._current_tech()
        type_names = [t.canonical_name for t in tech.types] if tech is not None else []

        num_sides = 2 if check.check_type == "spacing" else 1
        side_labels = ("Layer 1", "Layer 2") if num_sides == 2 else ("Layers",)

        dialog = tk.Toplevel(self)
        dialog.title("Select Layers")
        dialog.transient(self.winfo_toplevel())
        dialog.geometry("420x360" if num_sides == 1 else "640x360")
        dialog.minsize(240, 200)
        dialog.resizable(True, True)
        dialog.rowconfigure(0, weight=1)

        listboxes: list[tk.Listbox] = []
        for i in range(num_sides):
            dialog.columnconfigure(i, weight=1)
            col_frame = ttk.Frame(dialog)
            col_frame.grid(row=0, column=i, padx=8, pady=8, sticky="nsew")
            ttk.Label(col_frame, text=side_labels[i]).pack(anchor="w")
            existing = check.layer_args[i] if i < len(check.layer_args) else []
            height = min(max(len(type_names) + len(existing), 4), 15)
            listbox = tk.Listbox(col_frame, selectmode="extended", exportselection=False, height=height)
            listbox.pack(fill="both", expand=True)
            for name in type_names:
                listbox.insert("end", name)
            for idx, name in enumerate(type_names):
                if name in existing:
                    listbox.selection_set(idx)
            for name in existing:
                if name not in type_names:
                    listbox.insert("end", name)
                    listbox.selection_set(listbox.size() - 1)
            listboxes.append(listbox)

        def _apply():
            new_args = []
            for listbox in listboxes:
                selected = [listbox.get(i) for i in listbox.curselection()]
                if not selected:
                    messagebox.showwarning(
                        "Select Layers", "Each side needs at least one real type selected.", parent=dialog,
                    )
                    return
                new_args.append(selected)
            check.layer_args = new_args
            self.drc_checks_editor.refresh_current_row()
            dialog.destroy()

        button_row = ttk.Frame(dialog)
        button_row.grid(row=1, column=0, columnspan=num_sides, pady=(0, 8))
        ttk.Button(button_row, text="Apply", command=_apply).pack(side="left")
        ttk.Button(button_row, text="Cancel", command=dialog.destroy).pack(side="left", padx=(6, 0))

        dialog.grab_set()
        dialog.wait_window()

    def _copy_drc_check_to_rule(self):
        """Sends the selected width/spacing check into the real,
        unrelated KLayout DRC-deck rule model (Technology > DRC Rules)
        -- see ``pdklib/drc_bridge.py``'s own docstring for exactly
        which checks that real bridge can and can't cross (only a
        single-Magic-type ``width``, or a true-self ``spacing``, ever
        qualify), and why. Always checks real coherence first --
        resolving the Magic type through this technology's own real
        ``cifoutput`` mapping against this project's own registered
        Layers -- and only ever writes a real ``DesignRule`` when that
        check passes clean; every real mismatch found along the way is
        reported back, whether or not it blocked the copy."""

        if self.app is None:
            messagebox.showerror("Copy to DRC Rules", "No owning app -- can't reach DRC Rules.", parent=self)
            return
        self.drc_checks_editor.commit_pending_edits()
        check = self.drc_checks_editor.current_entry
        if check is None:
            messagebox.showinfo("Copy to DRC Rules", "Select a width/spacing check first.", parent=self)
            return
        tech = self._current_tech()
        if tech is None:
            return

        result = drc_bridge.copy_magic_drc_check_to_rule(
            check, tech.cif_layers, self.app.project.layers, self.app.project.design_rules,
        )
        if result.rule is None:
            messagebox.showwarning("Copy to DRC Rules -- not copied", "\n\n".join(result.messages), parent=self)
            return
        self.app.project.design_rules.append(result.rule)
        self.app.rules_view.refresh()
        summary = f"Copied as DRC Rules entry '{result.rule.rule_id}'."
        if result.messages:
            summary += "\n\n" + "\n\n".join(result.messages)
        messagebox.showinfo("Copy to DRC Rules", summary, parent=self)

    def _view_file(self):
        tech = self.technologies.get(self.tech_var.get())
        if tech is not None:
            view_file_dialog(self, tech.source_path)

    def _new_tech_file(self):
        """A real, minimal, valid Magic ``.tech`` skeleton
        (``pdklib/magic_tech.py``'s own ``create_new_tech_file``) --
        genuinely usable immediately afterward: **New Type**/**New
        Plane**/**New Contact**/**New Alias** below all work against
        it the same as against a real, downloaded file (see that
        function's own docstring)."""

        name = simpledialog.askstring(
            "New .tech File", "Technology name (also used as the file name):", parent=self,
        )
        if not name:
            return
        path = self.pdk_root / "libs.tech" / "magic" / f"{name}.tech"
        if path.exists():
            messagebox.showerror("New .tech File", f"{path} already exists.", parent=self)
            return
        magic_tech_mod.create_new_tech_file(path)
        self.load()
        self.tech_var.set(name)
        self._refresh_all()

    # -- persistence hooks (project_io.py) -----------------------------------

    def commit_pending_edits(self):
        """Flushes whatever's mid-edit in the Types/Planes/Contacts/
        Aliases forms into their own real entries before the caller
        reads/saves state -- otherwise a field typed but not yet
        committed (no selection change since) would be silently
        dropped from a save."""

        self._commit_form_to_type()
        self.planes_editor.commit_pending_edits()
        self.contacts_editor.commit_pending_edits()
        self.aliases_editor.commit_pending_edits()
        self.styles_editor.commit_pending_edits()
        self.compose_editor.commit_pending_edits()
        self.connect_editor.commit_pending_edits()
        self.cifinput_ignore_editor.commit_pending_edits()
        self.cifinput_hints_editor.commit_pending_edits()
        self.cifinput_recipes_editor.commit_pending_edits()
        self.cif_layers_editor.commit_pending_edits()
        self.extract_misc_editor.commit_pending_edits()
        self.extract_plane_order_editor.commit_pending_edits()
        self.extract_resist_editor.commit_pending_edits()
        self.extract_coeff_editor.commit_pending_edits()
        self.extract_devices_editor.commit_pending_edits()
        self.drc_angles_editor.commit_pending_edits()
        self.drc_checks_editor.commit_pending_edits()

    def collect_types_by_tech(self) -> dict[str, list[magic_tech_mod.TypeEntry]]:
        return {name: tech.types for name, tech in self.technologies.items()}

    def collect_planes_by_tech(self) -> dict[str, list[magic_tech_mod.PlaneEntry]]:
        return {name: tech.planes for name, tech in self.technologies.items()}

    def collect_contacts_by_tech(self) -> dict[str, list[magic_tech_mod.ContactEntry]]:
        return {name: tech.contacts for name, tech in self.technologies.items()}

    def collect_aliases_by_tech(self) -> dict[str, list[magic_tech_mod.AliasEntry]]:
        return {name: tech.aliases for name, tech in self.technologies.items()}

    def collect_styles_by_tech(self) -> dict[str, list[magic_tech_mod.StyleEntry]]:
        return {name: tech.styles for name, tech in self.technologies.items()}

    def collect_compose_by_tech(self) -> dict[str, list[magic_tech_mod.ComposeStatement]]:
        return {name: tech.compose for name, tech in self.technologies.items()}

    def collect_connect_by_tech(self) -> dict[str, list[magic_tech_mod.ConnectRule]]:
        return {name: tech.connect for name, tech in self.technologies.items()}

    def collect_cifinput_ignored_layers_by_tech(self) -> dict[str, list[magic_tech_mod.CifInputIgnoredLayer]]:
        return {name: tech.cifinput_ignored_layers for name, tech in self.technologies.items()}

    def collect_cifinput_layer_hints_by_tech(self) -> dict[str, list[magic_tech_mod.CifInputLayerHint]]:
        return {name: tech.cifinput_layer_hints for name, tech in self.technologies.items()}

    def collect_cifinput_recipes_by_tech(self) -> dict[str, list[magic_tech_mod.CifInputRecipeBlock]]:
        return {name: tech.cifinput_recipes for name, tech in self.technologies.items()}

    def collect_cif_layers_by_tech(self) -> dict[str, list[magic_tech_mod.CifOutputLayerMapping]]:
        return {name: tech.cif_layers for name, tech in self.technologies.items()}

    def collect_extract_misc_by_tech(self) -> dict[str, list[magic_tech_mod.ExtractMiscStatement]]:
        return {name: tech.extract_misc for name, tech in self.technologies.items()}

    def collect_extract_plane_order_by_tech(self) -> dict[str, list[magic_tech_mod.ExtractPlaneOrder]]:
        return {name: tech.extract_plane_order for name, tech in self.technologies.items()}

    def collect_extract_resist_by_tech(self) -> dict[str, list[magic_tech_mod.ExtractResist]]:
        return {name: tech.extract_resist for name, tech in self.technologies.items()}

    def collect_extract_cap_coefficients_by_tech(self) -> dict[str, list[magic_tech_mod.ExtractCapCoefficient]]:
        return {name: tech.extract_cap_coefficients for name, tech in self.technologies.items()}

    def collect_extract_devices_by_tech(self) -> dict[str, list[magic_tech_mod.ExtractDevice]]:
        return {name: tech.extract_devices for name, tech in self.technologies.items()}

    def collect_drc_angle_checks_by_tech(self) -> dict[str, list[magic_tech_mod.MagicAngleCheck]]:
        return {name: tech.drc_angle_checks for name, tech in self.technologies.items()}

    def collect_drc_checks_by_tech(self) -> dict[str, list[magic_tech_mod.MagicDrcCheck]]:
        return {name: tech.drc_checks for name, tech in self.technologies.items()}

    def collect_drc_misc_by_tech(self) -> dict[str, list[magic_tech_mod.MagicDrcMiscStatement]]:
        return {name: tech.drc_misc for name, tech in self.technologies.items()}

    # -- data ---------------------------------------------------------------

    def load(self):
        self.technologies = {}
        for path in magic_tech_mod.find_tech_files(self.pdk_root):
            tech = magic_tech_mod.parse_tech_file(path)
            # A real fragment file (ihp-sg13g2-cifin.tech/-cifout.tech/
            # -drc.tech/-extract.tech) has no own tech/version header,
            # so tech.name comes back empty -- falls back to the real
            # file's own stem so it's still selectable (previously
            # silently skipped entirely), rather than inventing a fake
            # tech.name on the parsed model itself. This is what makes
            # cifinput's own real ignored-layers/layer-hints tables
            # editable at all: their real write-back target is that
            # fragment file directly, not ihp-sg13g2.tech (see
            # pdklib/magic_tech_writer.py's own docstring).
            display_name = tech.name or path.stem
            self.technologies[display_name] = tech

        names = sorted(self.technologies)
        self.tech_combo["values"] = names
        if names and not self.tech_var.get():
            self.tech_var.set(names[0])
        self._refresh_all()

    def _current_tech(self) -> magic_tech_mod.MagicTechnology | None:
        return self.technologies.get(self.tech_var.get())

    def _refresh_all(self):
        self._commit_form_to_type()
        self.planes_editor.commit_pending_edits()
        self.contacts_editor.commit_pending_edits()
        self.aliases_editor.commit_pending_edits()
        self.styles_editor.commit_pending_edits()
        self.compose_editor.commit_pending_edits()
        self.connect_editor.commit_pending_edits()
        self.cifinput_ignore_editor.commit_pending_edits()
        self.cifinput_hints_editor.commit_pending_edits()
        self.cifinput_recipes_editor.commit_pending_edits()
        self.cif_layers_editor.commit_pending_edits()
        self.extract_misc_editor.commit_pending_edits()
        self.extract_plane_order_editor.commit_pending_edits()
        self.extract_resist_editor.commit_pending_edits()
        self.extract_coeff_editor.commit_pending_edits()
        self.extract_devices_editor.commit_pending_edits()
        self.drc_angles_editor.commit_pending_edits()
        self.drc_checks_editor.commit_pending_edits()
        self.drc_misc_editor.commit_pending_edits()
        for tree in (
            self.cifinput_recipes_tree,
        ):
            for row in tree.get_children():
                tree.delete(row)

        tech = self._current_tech()
        if tech is None:
            self.summary_var.set("No Magic .tech data loaded -- has pdklib/fetch.py been run?")
            self.planes_editor.set_entries(None)
            self.contacts_editor.set_entries(None)
            self.aliases_editor.set_entries(None)
            self.styles_editor.set_entries(None)
            self.compose_editor.set_entries(None)
            self.connect_editor.set_entries(None)
            self.cifinput_ignore_editor.set_entries(None)
            self.cifinput_hints_editor.set_entries(None)
            self.cifinput_recipes_editor.set_entries(None)
            self.cif_layers_editor.set_entries(None)
            self.extract_misc_editor.set_entries(None)
            self.extract_plane_order_editor.set_entries(None)
            self.extract_resist_editor.set_entries(None)
            self.extract_coeff_editor.set_entries(None)
            self.extract_devices_editor.set_entries(None)
            self.drc_angles_editor.set_entries(None)
            self.drc_checks_editor.set_entries(None)
            self.drc_misc_editor.set_entries(None)
            self._refresh_types()
            return

        self.planes_editor.set_entries(tech.planes)
        self.type_plane_combo["values"] = [plane.name for plane in tech.planes]
        self._refresh_types()
        self.contacts_editor.set_entries(tech.contacts)
        self.aliases_editor.set_entries(tech.aliases)
        self.styles_editor.set_entries(tech.styles)
        self.compose_editor.set_entries(tech.compose)
        self.connect_editor.set_entries(tech.connect)
        self.cifinput_ignore_editor.set_entries(tech.cifinput_ignored_layers)
        self.cifinput_hints_editor.set_entries(tech.cifinput_layer_hints)
        self.cifinput_recipes_editor.set_entries(tech.cifinput_recipes)
        self.cif_layers_editor.set_entries(tech.cif_layers)
        self.extract_misc_editor.set_entries(tech.extract_misc)
        self.extract_plane_order_editor.set_entries(tech.extract_plane_order)
        self.extract_resist_editor.set_entries(tech.extract_resist)
        self.extract_coeff_editor.set_entries(tech.extract_cap_coefficients)
        self.extract_devices_editor.set_entries(tech.extract_devices)
        self.drc_angles_editor.combo_widgets["layer"]["values"] = [t.canonical_name for t in tech.types]
        self.drc_angles_editor.set_entries(tech.drc_angle_checks)
        self.drc_checks_editor.set_entries(tech.drc_checks)
        self.drc_misc_editor.set_entries(tech.drc_misc)
        for recipe in tech.cifinput_recipes:
            ops_text = " ".join(f"{op.verb}({op.args})" if op.args else op.verb for op in recipe.ops)
            self.cifinput_recipes_tree.insert(
                "", "end",
                values=(
                    recipe.name, recipe.kind_text,
                    recipe.base_layer, ops_text,
                ),
            )
        summary = (
            f"format {tech.format} | v{tech.version} -- {tech.description} | "
            f"planes:{len(tech.planes)} types:{len(tech.types)} contacts:{len(tech.contacts)} "
            f"aliases:{len(tech.aliases)} styles:{len(tech.styles)} cif_layers:{len(tech.cif_layers)} "
            f"compose:{len(tech.compose)} connect:{len(tech.connect)} "
            f"drc_checks:{len(tech.drc_checks)}+{len(tech.drc_angle_checks)}angles+"
            f"{len(tech.drc_misc)}misc({len(tech.drc_skipped)} skipped) "
            f"extract_resist:{len(tech.extract_resist)} "
            f"extract_cap_coefficients:{len(tech.extract_cap_coefficients)} "
            f"extract_devices:{len(tech.extract_devices)} "
            f"extract_misc:{len(tech.extract_misc)} "
            f"extract_plane_order:{len(tech.extract_plane_order)}"
        )
        if tech.included_files:
            summary += f" | includes: {', '.join(tech.included_files)}"
        if tech.unparsed_sections:
            summary += f" | not parsed: {', '.join(tech.unparsed_sections)}"
        self.summary_var.set(summary)

    # -- types (editable) -----------------------------------------------------

    @staticmethod
    def _type_iid(type_entry: magic_tech_mod.TypeEntry) -> str:
        # Identity-based, not name-based: canonical_name is an editable field.
        return str(id(type_entry))

    def _type_row_values(self, type_entry: magic_tech_mod.TypeEntry) -> tuple:
        return (
            type_entry.plane, type_entry.canonical_name,
            ", ".join(type_entry.aliases), "yes" if type_entry.obsolete else "",
        )

    def _type_matches_filter(self, type_entry: magic_tech_mod.TypeEntry) -> bool:
        return matches(
            self._type_filter_query, type_entry.canonical_name, type_entry.plane, *type_entry.aliases,
        )

    def _on_type_filter_changed(self, query: str):
        self._type_filter_query = query
        self._refresh_types()

    def _refresh_types(self):
        for row in self.types_tree.get_children():
            self.types_tree.delete(row)
        self._type_by_iid = {}
        tech = self._current_tech()
        if tech is None:
            self._load_type_into_form(None)
            return
        shown = [t for t in tech.types if self._type_matches_filter(t)]
        for type_entry in shown:
            iid = self._type_iid(type_entry)
            self._type_by_iid[iid] = type_entry
            self.types_tree.insert("", "end", iid=iid, values=self._type_row_values(type_entry))
        if shown:
            self.types_tree.selection_set(self._type_iid(shown[0]))
            self._load_type_into_form(shown[0])
        else:
            self._load_type_into_form(None)

    def _on_type_select(self, _event=None):
        self._commit_form_to_type()
        selection = self.types_tree.selection()
        type_entry = self._type_by_iid.get(selection[0]) if selection else None
        self._load_type_into_form(type_entry)

    def _load_type_into_form(self, type_entry: magic_tech_mod.TypeEntry | None):
        self._suspend_trace = True
        self.current_type = type_entry
        if type_entry is None:
            for var in self.type_vars.values():
                var.set("")
        else:
            self.type_vars["plane"].set(type_entry.plane)
            self.type_vars["name"].set(type_entry.canonical_name)
            self.type_vars["aliases"].set(", ".join(type_entry.aliases))
            self.type_vars["obsolete"].set("yes" if type_entry.obsolete else "")
        self._suspend_trace = False

    def _commit_form_to_type(self):
        type_entry = self.current_type
        if type_entry is None:
            return
        type_entry.plane = self.type_vars["plane"].get().strip() or type_entry.plane
        type_entry.canonical_name = self.type_vars["name"].get().strip() or type_entry.canonical_name
        raw_aliases = self.type_vars["aliases"].get()
        type_entry.aliases = [a.strip() for a in raw_aliases.split(",") if a.strip()]
        type_entry.obsolete = self.type_vars["obsolete"].get() == "yes"

    def _on_type_field_changed(self, *_args):
        if self._suspend_trace:
            return
        self._commit_form_to_type()
        if self.current_type is not None:
            iid = self._type_iid(self.current_type)
            if self.types_tree.exists(iid):
                self.types_tree.item(iid, values=self._type_row_values(self.current_type))

    def _new_type(self):
        tech = self._current_tech()
        if tech is None:
            return
        self._commit_form_to_type()
        self.type_filter_var.set("")  # a freshly-created type must always be visible, even mid-search
        default_plane = tech.planes[0].name if tech.planes else ""
        type_entry = magic_tech_mod.TypeEntry(
            plane=default_plane, canonical_name=f"newtype{len(tech.types) + 1}",
        )
        tech.types.append(type_entry)
        iid = self._type_iid(type_entry)
        self._type_by_iid[iid] = type_entry
        self.types_tree.insert("", "end", iid=iid, values=self._type_row_values(type_entry))
        self.types_tree.selection_set(iid)
        self.types_tree.see(iid)

    def _delete_type(self):
        tech = self._current_tech()
        if tech is None:
            return
        selection = self.types_tree.selection()
        if not selection:
            return
        type_entry = self._type_by_iid.get(selection[0])
        if type_entry is None:
            return
        tech.types.remove(type_entry)
        self.current_type = None
        self.types_tree.delete(selection[0])
        del self._type_by_iid[selection[0]]
        remaining = self.types_tree.get_children()
        if remaining:
            self.types_tree.selection_set(remaining[0])
            self._load_type_into_form(self._type_by_iid[remaining[0]])
        else:
            self._load_type_into_form(None)

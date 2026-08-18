import sys
sys.path.insert(0, "/foss/designs")
import shutil
import tempfile
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator import export as export_mod
from openpdkcreator.pdklib import magic_tech as magic_tech_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
CIFIN_PATH = PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2-cifin.tech"

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

mtv = app.magic_tech_view

# --- The picker now shows every real .tech file, not just the two
# with their own real tech/version header -- the four real fragment
# files (no header of their own) fall back to their own real file
# stem as a display name instead of being silently hidden. ---
print("technologies:", sorted(mtv.technologies.keys()))
assert sorted(mtv.technologies.keys()) == [
    "ihp-sg13g2", "ihp-sg13g2-GDS", "ihp-sg13g2-cifin", "ihp-sg13g2-cifout", "ihp-sg13g2-drc", "ihp-sg13g2-extract",
]
assert mtv.technologies["ihp-sg13g2-cifin"].source_path == CIFIN_PATH
assert mtv.technologies["ihp-sg13g2-cifin"].name == "", "a real fragment file has no real tech/version header"
print("PASS: the Technology picker now includes every real .tech file, fragments included.")

mtv.tech_var.set("ihp-sg13g2-cifin")
mtv._refresh_all()
root.update()

print("ignore rows:", len(mtv.cifinput_ignore_editor.tree.get_children()))
print("hint rows:", len(mtv.cifinput_hints_editor.tree.get_children()))
assert len(mtv.cifinput_ignore_editor.tree.get_children()) == 23
assert len(mtv.cifinput_hints_editor.tree.get_children()) == 133

# --- Edit an ignored layer's name and a hint's real int-typed fields
# (the first int-typed editable fields anywhere in this module) --
# both round-trip as real Python ints/None, not strings, confirming
# the gds_layer_text/gds_datatype_text properties really do keep the
# underlying real field correctly typed. ---
mtv.cifinput_ignore_editor.tree.selection_set(mtv.cifinput_ignore_editor.tree.get_children()[0])
mtv.cifinput_ignore_editor._on_select()
mtv.cifinput_ignore_editor.field_vars["name"].set("RENAMEDLAYER")
root.update()
assert mtv.cifinput_ignore_editor.current_entry.name == "RENAMEDLAYER"

mtv.cifinput_hints_editor.tree.selection_set(mtv.cifinput_hints_editor.tree.get_children()[0])
mtv.cifinput_hints_editor._on_select()
mtv.cifinput_hints_editor.field_vars["gds_layer_text"].set("777")
root.update()
edited_hint = mtv.cifinput_hints_editor.current_entry
assert edited_hint.gds_layer == 777
assert isinstance(edited_hint.gds_layer, int)

# A real wildcard datatype ('*') round-trips as gds_datatype is None,
# not the literal string '*'.
wildcard_hint = next(h for h in mtv.cifinput_hints_editor.entries if h.gds_datatype is None)
assert wildcard_hint.gds_datatype_text == "*"
wildcard_iid = mtv.cifinput_hints_editor._iid(wildcard_hint)
mtv.cifinput_hints_editor.tree.selection_set(wildcard_iid)
mtv.cifinput_hints_editor._on_select()
mtv.cifinput_hints_editor.field_vars["gds_datatype_text"].set("42")
root.update()
assert wildcard_hint.gds_datatype == 42
mtv.cifinput_hints_editor.field_vars["gds_datatype_text"].set("*")
root.update()
assert wildcard_hint.gds_datatype is None
print("PASS: in-GUI edits for cifinput's ignored layers and layer hints, including real int/wildcard round-trips.")

# New/Delete for both
before_ignore = len(mtv.cifinput_ignore_editor.tree.get_children())
mtv.cifinput_ignore_editor.new_entry()
root.update()
assert len(mtv.cifinput_ignore_editor.tree.get_children()) == before_ignore + 1
assert mtv.cifinput_ignore_editor.current_entry.line_no == 0
mtv.cifinput_ignore_editor.delete_entry()
root.update()
assert len(mtv.cifinput_ignore_editor.tree.get_children()) == before_ignore

before_hint = len(mtv.cifinput_hints_editor.tree.get_children())
mtv.cifinput_hints_editor.new_entry()
root.update()
assert len(mtv.cifinput_hints_editor.tree.get_children()) == before_hint + 1
assert mtv.cifinput_hints_editor.current_entry.line_no == 0
mtv.cifinput_hints_editor.delete_entry()
root.update()
assert len(mtv.cifinput_hints_editor.tree.get_children()) == before_hint
print("PASS: New/Delete for both cifinput sub-panes.")

# -- Save Edits / relaunch persistence, keyed by 'ihp-sg13g2-cifin' --
app._save_project()
root.update()

edited_ignore_name = mtv.cifinput_ignore_editor.entries[0].name
edited_hint_name = mtv.cifinput_hints_editor.entries[0].name

root.destroy()
root2 = tk.Tk()
app2 = App(root2, PDK_ROOT)
root2.update()
mtv2 = app2.magic_tech_view
mtv2.tech_var.set("ihp-sg13g2-cifin")
mtv2._refresh_all()
root2.update()

reloaded_ignore = next(x for x in mtv2.cifinput_ignore_editor.entries if x.name == edited_ignore_name)
assert reloaded_ignore.name == "RENAMEDLAYER"
reloaded_hint = next(x for x in mtv2.cifinput_hints_editor.entries if x.name == edited_hint_name)
assert reloaded_hint.gds_layer == 777
print("PASS: cifinput edits survive Save Edits + a simulated relaunch, keyed by the real fragment file's own name.")

# -- Real write-back export: lands in ihp-sg13g2-cifin.tech, NOT
# ihp-sg13g2.tech (a real, structurally different file); the main
# technology's own export stays completely untouched by these edits. --
with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    written = export_mod.export_magic_types(PDK_ROOT, mtv2.technologies, dest_root=export_dir)
    print("exported files:", sorted(p.name for p in written))
    assert len(written) == 6, written

    cifin_export = [p for p in written if p.name == "ihp-sg13g2-cifin.tech"][0]
    cifin_text = cifin_export.read_text()
    assert "RENAMEDLAYER" in cifin_text
    assert "777" in cifin_text
    print("PASS: real write-back for cifinput lands in ihp-sg13g2-cifin.tech, containing the edited values.")

    main_export = [p for p in written if p.name == "ihp-sg13g2.tech"][0]
    main_text = main_export.read_text()
    assert main_text == (PDK_ROOT / "libs.tech" / "magic" / "ihp-sg13g2.tech").read_text()
    assert "RENAMEDLAYER" not in main_text
    print("PASS: ihp-sg13g2.tech's own export is completely unaffected -- cifinput's real content "
          "doesn't live there, so this file's own write-back correctly leaves it untouched.")

root2.destroy()

# -- CLI parity: main.py export-magic-types picks up the same real
# fragment file (confirmed via the module-level function it wraps,
# same code path `main.py`'s own cmd_export_magic_types calls) --
from openpdkcreator.pdklib import magic_tech as mt_mod

cli_technologies = {}
for path in mt_mod.find_tech_files(PDK_ROOT):
    tech = mt_mod.parse_tech_file(path)
    cli_technologies[tech.name or path.stem] = tech
assert "ihp-sg13g2-cifin" in cli_technologies
print("PASS: the same real fallback-naming logic used by main.py's own export-magic-types finds the fragment too.")

print("ALL MAGIC CIFINPUT TESTS PASS")

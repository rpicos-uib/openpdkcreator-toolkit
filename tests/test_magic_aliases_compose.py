import sys
sys.path.insert(0, "/foss/designs/openMemristorPDK")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator.pdklib import extraction as ext_mod
from openpdkcreator.pdklib import magic_tech as mt, magic_tech_writer as mtw

PDK_ROOT = Path("/foss/designs/openMemristorPDK/data/openmemristorpdk")
TECH_PATH = PDK_ROOT / "libs.tech" / "magic" / "openmemristorpdk.tech"

# --- real, direct parse: the m1/m2/active_tio2 aliases and the
# active_tio2 compose statement are real, not stale-save artifacts ---------
# Real Magic alias syntax is <new_alias_name> <existing_real_type> --
# confirmed live (not guessed) via a real Magic parse error
# ("Type alias 'be_au' shadows a defined type") when this was
# originally authored the other way around.
tech = mt.parse_tech_file(TECH_PATH)
print("real aliases:", [(a.name, a.members_raw) for a in tech.aliases])
assert [(a.name, a.members_raw) for a in tech.aliases] == [
    ("m1", "be_au"), ("m2", "te_au"), ("active_tio2", "mem_tio2"),
]
print("PASS: openmemristorpdk's own real aliases (m1->be_au, m2->te_au, active_tio2->mem_tio2) parse correctly.")

print("real compose:", [(c.verb, c.args) for c in tech.compose])
assert [(c.verb, c.args) for c in tech.compose] == [("compose", ("active_tio2", "te_au", "mem_tio2"))]
print("PASS: openmemristorpdk's own real compose statement (active_tio2 = te_au AND mem_tio2) parses correctly.")

# --- no-edit export stays byte-identical ----------------------------------
rendered = mtw.render_tech_file(TECH_PATH, tech)
original = TECH_PATH.read_text(encoding="utf-8", errors="replace")
if not original.endswith("\n"):
    original += "\n"
assert rendered == original
print("PASS: no-edit export of the real, edited .tech file is still byte-identical.")

# --- real, live: loaded end-to-end through the app, not shadowed by a
# stale saves/*.yaml override (the same real bug found and fixed for
# magic_contacts/magic_drc_checks/magic_drc_angle_checks/magic_cif_layers) -
root = tk.Tk()
app = App(root, PDK_ROOT)
app.load()
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("openmemristorpdk")
mtv._refresh_all()
root.update()

print("real, live Aliases rows:", len(mtv.aliases_editor.tree.get_children()))
assert len(mtv.aliases_editor.tree.get_children()) == 3
print("real, live Compose rows:", len(mtv.compose_editor.tree.get_children()))
assert len(mtv.compose_editor.tree.get_children()) == 1
print("PASS: real, live -- Aliases/Compose tabs show their real content after a real app.load(), "
      "not shadowed by a stale save.")

root.destroy()

# --- real, live: this project's own parser is more lenient than real
# Magic's own -- content that parses cleanly here previously still got
# rejected on a real load (a real, found-live bug: Contacts/Aliases/
# Compose all had real Magic syntax errors despite parsing fine
# through pdklib/magic_tech.py). Never trust that alone again --
# always also confirm a real Magic batch load produces zero real
# section errors for the whole file, not just this session's edits. ---
tech_file = ext_mod.default_tech_file(PDK_ROOT).resolve()
# Reuse any real, already-registered .mag cell purely as a load target --
# what's under test is the real .tech file's own section content, not
# this specific cell's own geometry.
import glob
mag_candidates = glob.glob("/foss/designs/openMemristorPDK/libraries/**/*.mag", recursive=True)
assert mag_candidates, "no real .mag file found to use as a real Magic load target"
gds_result = ext_mod.run_gds_export(Path(mag_candidates[0]).resolve(), tech_file, "magic")
assert "Unrecognized layer" not in gds_result.log
assert "contained errors" not in gds_result.log
print(f"PASS: real Magic itself loads the full, real .tech file with zero section errors "
      f"(checked via {Path(mag_candidates[0]).name}).")


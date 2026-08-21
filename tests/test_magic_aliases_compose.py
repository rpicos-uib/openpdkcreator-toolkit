import sys
sys.path.insert(0, "/foss/designs/openMemristorPDK")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator.pdklib import magic_tech as mt, magic_tech_writer as mtw

PDK_ROOT = Path("/foss/designs/openMemristorPDK/data/openmemristorpdk")
TECH_PATH = PDK_ROOT / "libs.tech" / "magic" / "openmemristorpdk.tech"

# --- real, direct parse: the m1/m2 aliases and the active_tio2 compose
# statement are real, not stale-save artifacts -----------------------------
tech = mt.parse_tech_file(TECH_PATH)
print("real aliases:", [(a.name, a.members_raw) for a in tech.aliases])
assert [(a.name, a.members_raw) for a in tech.aliases] == [("be_au", "m1"), ("te_au", "m2")]
print("PASS: openmemristorpdk's own real aliases (be_au->m1, te_au->m2) parse correctly.")

print("real compose:", [(c.verb, c.args) for c in tech.compose])
assert [(c.verb, c.args) for c in tech.compose] == [("compose", ("active_tio2", "be_au", "mem_tio2"))]
print("PASS: openmemristorpdk's own real compose statement (active_tio2 = be_au AND mem_tio2) parses correctly.")

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
assert len(mtv.aliases_editor.tree.get_children()) == 2
print("real, live Compose rows:", len(mtv.compose_editor.tree.get_children()))
assert len(mtv.compose_editor.tree.get_children()) == 1
print("PASS: real, live -- Aliases/Compose tabs show their real content after a real app.load(), "
      "not shadowed by a stale save.")

root.destroy()

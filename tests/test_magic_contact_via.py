import sys
sys.path.insert(0, "/foss/designs/openMemristorPDK")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator.pdklib import magic_tech as mt, magic_tech_writer as mtw

PDK_ROOT = Path("/foss/designs/openMemristorPDK/data/openmemristorpdk")
TECH_PATH = PDK_ROOT / "libs.tech" / "magic" / "openmemristorpdk.tech"

# --- real, direct parse: the via1 metal1<->metal2 contact is real,
# not a stale-save artifact -------------------------------------------
tech = mt.parse_tech_file(TECH_PATH)
print("real contacts:", len(tech.contacts))
assert len(tech.contacts) == 1
contact = tech.contacts[0]
assert (contact.contact_type, contact.layer1, contact.layer2) == ("via1", "be_au", "te_au")
print("PASS: openmemristorpdk's own real contact section (via1: be_au<->te_au) parses correctly.")

# --- no-edit export stays byte-identical ----------------------------------
rendered = mtw.render_tech_file(TECH_PATH, tech)
original = TECH_PATH.read_text(encoding="utf-8", errors="replace")
if not original.endswith("\n"):
    original += "\n"
assert rendered == original
print("PASS: no-edit export of the real, edited .tech file is still byte-identical.")

# --- real, live: loaded end-to-end through the app, not shadowed by a
# stale saves/*.yaml override (the same real bug found and fixed for
# magic_drc_checks/magic_drc_angle_checks/magic_cif_layers earlier) ------
root = tk.Tk()
app = App(root, PDK_ROOT)
app.load()
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("openmemristorpdk")
mtv._refresh_all()
root.update()

print("real, live Contacts rows:", len(mtv.contacts_editor.tree.get_children()))
assert len(mtv.contacts_editor.tree.get_children()) == 1
live_contact = mtv.contacts_editor.entries[0]
assert (live_contact.contact_type, live_contact.layer1, live_contact.layer2) == ("via1", "be_au", "te_au")
print("PASS: real, live -- Contacts tab shows via1 after a real app.load(), not shadowed by a stale save.")

root.destroy()

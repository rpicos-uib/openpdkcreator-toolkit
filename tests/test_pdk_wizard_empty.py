import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator.gui.pdk_wizard_view import _STAGES
from openpdkcreator.pdklib import skeleton as skeleton_mod

PDK_ROOT = Path("/tmp/empty_pdk_fresh")
import shutil
shutil.rmtree(PDK_ROOT, ignore_errors=True)
skeleton_mod.build_blank_pdk(PDK_ROOT)

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

wv = app.wizard_view
for stage in _STAGES:
    has_data, detail, gap_note = stage.status_fn(app)
    print(f"{stage.stage_id:20s} has_data={has_data!s:5s} gap={bool(gap_note)!s:5s} detail={detail!r}")
    wv._select(stage.stage_id)
    root.update()

# real gaps should be flagged for the genuinely no-create-path domains
by_id = {s.stage_id: s for s in _STAGES}
for sid in ("lef", "verilog", "liberty", "cdl_spice", "ngspice", "gds"):
    has_data, detail, gap = by_id[sid].status_fn(app)
    assert not has_data and gap, f"{sid} should be flagged as a real create-from-scratch gap, got has_data={has_data} gap={gap!r}"
print("PASS: every remaining no/partial-create-path domain is correctly flagged as a real gap against an empty pdk_root.")

for sid in ("layers", "magic_tech", "drc_rules", "xschem_sym", "xschem_sch", "qucs_sym", "qucs_components", "user_models"):
    has_data, detail, gap = by_id[sid].status_fn(app)
    assert not has_data and not gap, f"{sid} should be empty but NOT flagged as a gap (creatable in-GUI), got {gap!r}"
print("PASS: the six now-in-GUI-creatable domains + user_models are empty but not flagged as gaps.")

root.destroy()
print("ALL EMPTY-PDK WIZARD TESTS PASS")

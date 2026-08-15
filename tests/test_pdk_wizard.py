import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

wv = app.wizard_view
print("Wizard is tab 0:", app.notebook.tab(app.notebook.tabs()[0], "text"))
assert app.notebook.tab(app.notebook.tabs()[0], "text") == "PDK Wizard"
print("Currently selected tab:", app.notebook.tab(app.notebook.select(), "text"))
assert app.notebook.tab(app.notebook.select(), "text") == "PDK Wizard"

# --- Every stage's status_fn runs cleanly against the real, loaded IHP data ---
from openpdkcreator.gui.pdk_wizard_view import _STAGES, _EDGES

for stage in _STAGES:
    has_data, detail, gap_note = stage.status_fn(app)
    print(f"{stage.stage_id:20s} has_data={has_data!s:5s} detail={detail!r} gap={bool(gap_note)}")
    assert isinstance(has_data, bool)
    assert isinstance(detail, str) and detail

# Real IHP data should show real presence for most domains
by_id = {s.stage_id: s for s in _STAGES}
real_present = {"layers", "magic_tech", "drc_rules", "lef", "verilog", "liberty", "cdl_spice",
                 "xschem_sym", "xschem_sch", "qucs_sym", "qucs_components", "ngspice", "by_cell", "gds"}
for sid in real_present:
    has_data, detail, _ = by_id[sid].status_fn(app)
    assert has_data, f"{sid} should have real data against the full IHP deck, got: {detail}"
print("PASS: every real-data-bearing stage correctly reports data present against the real IHP deck.")

# user_models genuinely starts empty for this project (no .va authored yet)
has_data, detail, gap = by_id["user_models"].status_fn(app)
print("user_models (expected empty):", has_data, detail, gap)

# --- Edge/node graph integrity ---
ids = {s.stage_id for s in _STAGES}
for src, dst in _EDGES:
    assert src in ids and dst in ids, (src, dst)
print(f"PASS: all {len(_EDGES)} edges reference real stage ids ({len(ids)} stages).")

# --- Click simulation: select a node, check detail panel populates ---
wv._select("layers")
root.update()
print("detail title:", wv.detail_title.cget("text"))
print("detail status:", wv.detail_status.cget("text"))
assert wv.detail_title.cget("text") == "Layers (.lyp)"
assert "real layer" in wv.detail_status.cget("text")
assert str(wv.goto_button.cget("state")) == "normal"

# --- Go to Tab actually navigates ---
wv._on_goto()
root.update()
print("After Go to Tab, top tab:", app.notebook.tab(app.notebook.select(), "text"))
print("After Go to Tab, tech sub-tab:", app.technology_notebook.tab(app.technology_notebook.select(), "text"))
assert app.notebook.tab(app.notebook.select(), "text") == "Technology"
assert app.technology_notebook.tab(app.technology_notebook.select(), "text") == "Layers"
print("PASS: clicking a node then Go to Tab navigates to the real Technology > Layers tab.")

# --- 3-level goto: Simulation > xschem > Schematics ---
app.goto("Simulation", "xschem", "Schematics")
root.update()
print("sim tab:", app.notebook.tab(app.notebook.select(), "text"))
print("xschem sub:", app.xschem_view.outer.tab(app.xschem_view.outer.select(), "text"))
assert app.notebook.tab(app.notebook.select(), "text") == "Simulation"
assert app.simulation_notebook.tab(app.simulation_notebook.select(), "text") == "xschem"
assert app.xschem_view.outer.tab(app.xschem_view.outer.select(), "text") == "Schematics"
print("PASS: 3-level goto reaches Simulation > xschem > Schematics.")

# --- 3-level goto: Simulation > Qucs-S > Components ---
app.goto("Simulation", "Qucs-S", "Components")
root.update()
assert app.qucs_view.outer.tab(app.qucs_view.outer.select(), "text") == "Components"
print("PASS: 3-level goto reaches Simulation > Qucs-S > Components.")

# --- goto with no dedicated tab (export) never crashes ---
wv._select("export")
root.update()
assert str(wv.goto_button.cget("state")) == "disabled"
print("PASS: the Export/Package node (no dedicated tab) disables Go to Tab instead of crashing.")

# --- Refresh after project-name change flips Project Setup to done ---
app.set_project_name("memristor-pdk")
wv.refresh()
root.update()
has_data, detail, _ = by_id["project_setup"].status_fn(app)
assert has_data and "memristor-pdk" in detail
print("PASS: refresh() reflects a live project-name change.")

root.destroy()
print("ALL PDK WIZARD TESTS PASS")

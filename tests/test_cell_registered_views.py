import sys
sys.path.insert(0, "/foss/designs")
import shutil
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator.ihp import cells as cells_mod
from openpdkcreator.ihp import library_index as li_mod
from openpdkcreator import export as export_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
PROJECT_ROOT = export_mod.PROJECT_ROOT

# --- Isolated unit test: build_cell_index's own registered_by_cell -----

throwaway_pdk = Path("/tmp/test_registered_views_pdk")
shutil.rmtree(throwaway_pdk, ignore_errors=True)
lef_dir = throwaway_pdk / "libs.ref" / "fam" / "lef"
lef_dir.mkdir(parents=True)
(lef_dir / "fam.lef").write_text(
    "VERSION 5.7 ;\nMACRO mycell\n  CLASS CORE ;\nEND mycell\n"
)

index = cells_mod.build_cell_index(
    throwaway_pdk, "fam",
    registered_by_cell={
        "mycell": {"cdl": Path("/tmp/fake.cdl")},
        "ghostcell": {"lef": Path("/tmp/ghost.lef")},
    },
)
assert "mycell" in index
cv = index["mycell"]
assert cv.registered_views == {"cdl": Path("/tmp/fake.cdl")}
assert cv.cdl_source is None, "a registered entry must never populate the real field"
assert "ghostcell" not in index, "a registered-only cell must not introduce a brand-new entry here"
print("PASS: build_cell_index's registered_by_cell enriches an already-known cell, never introduces a new one.")

shutil.rmtree(throwaway_pdk, ignore_errors=True)

# --- Real, end-to-end GUI test against the real IHP deck ---------------

registry_path = li_mod.registry_path(PROJECT_ROOT)
registry_path.unlink(missing_ok=True)

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

hub = app.cell_hub_view
hub.family_var.set("sg13g2_io")
hub._refresh_cells()
root.update()

# sg13g2_io cells have no real per-cell SPICE (confirmed real, not
# assumed: sg13g2_io.spice simply doesn't exist under libs.ref/).
cv_before = hub.cell_index["sg13g2_Corner"]
assert cv_before.spice_cell is None
values_before = hub.cells_tree.item("sg13g2_Corner", "values")
assert values_before[3] == "", values_before  # spice column, real-absent

fake_spice = Path("/tmp/fake_sg13g2_corner.spice")
fake_spice.write_text("* placeholder\n")
li_mod.register_entry(PROJECT_ROOT, "sg13g2_io", "sg13g2_Corner", "spice", fake_spice)

hub._refresh_cells()
root.update()
cv_after = hub.cell_index["sg13g2_Corner"]
assert cv_after.spice_cell is None, "a registered entry must never populate the real, parsed field"
assert cv_after.registered_views.get("spice") == fake_spice
values_after = hub.cells_tree.item("sg13g2_Corner", "values")
assert values_after[3] == "+", values_after  # spice column, now marked registered
print("PASS: a Library Manager-registered SPICE entry for a real IHP cell shows up in By Cell as '+', not silently invisible.")

# Real, existing views (e.g. LEF) still show the real checkmark, unaffected.
assert values_after[1] == "✓", values_after
print("PASS: a real view's own checkmark is untouched by an unrelated registered entry on the same cell.")

root.destroy()

# --- cleanup ---
registry_path.unlink(missing_ok=True)
fake_spice.unlink(missing_ok=True)

print("ALL CELL REGISTERED VIEWS TESTS PASS")

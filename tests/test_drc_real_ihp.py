import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator import export as export_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

print("real DRC rules loaded:", len(app.project.design_rules))
assert len(app.project.design_rules) == 75

# No-edit export against the real deck should be byte-identical, and
# never touch/create custom_rules.drc (no hand-authored rules exist).
with __import__("tempfile").TemporaryDirectory() as tmp:
    dest = Path(tmp)
    written, failures = export_mod.export_drc_rules(PDK_ROOT, app.drc_root, app.project.design_rules, app.project.layers, dest_root=dest)
    print("written count:", len(written), "failures:", failures)
    assert failures == []
    assert not any(p.name == "custom_rules.drc" for p in written)
    mismatches = 0
    for p in written:
        rel = p.relative_to(dest)
        orig = PDK_ROOT / rel
        if p.read_text(encoding="utf-8", errors="replace") != orig.read_text(encoding="utf-8", errors="replace"):
            mismatches += 1
            print("MISMATCH:", rel)
    assert mismatches == 0
    print(f"PASS: no-edit export of the real IHP DRC deck is byte-identical across {len(written)} file(s), no custom_rules.drc created.")

root.destroy()
print("ALL REAL-IHP DRC REGRESSION TESTS PASS")

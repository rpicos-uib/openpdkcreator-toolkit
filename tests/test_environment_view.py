import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App
from openpdkcreator import export as export_mod
from openpdkcreator.gui import environment_view as ev_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

# --- New Environment sub-tab exists and is populated ---
assert hasattr(app, "environment_view")
text = app.environment_view.script_text.get("1.0", "end")
assert 'export PDK_ROOT="/foss/designs/data/ihp-sg13g2"' in text
assert "librelane_pdk() {" in text
print("PASS: Environment sub-tab exists and shows the real, generated script.")

# --- The sub-tab's own function-name label matches the script's own list ---
functions_msg = app.environment_view.functions_var.get()
print("functions label:", functions_msg)
assert functions_msg == "Defined: magic_pdk, klayout_pdk, xschem_pdk, ngspice_pdk, librelane_pdk", functions_msg
assert "Not yet available" not in functions_msg
print("PASS: the sub-tab shows the real, defined function names against the full IHP deck.")

# --- Save Script writes a real, executable file ---
dest_path = export_mod.PROJECT_ROOT / ev_mod.SHELL_ENV_DIRNAME / ev_mod.SCRIPT_NAME
dest_path.unlink(missing_ok=True)
app.environment_view._save_script()
root.update()
assert dest_path.is_file()
import stat
mode = dest_path.stat().st_mode
assert mode & stat.S_IXUSR
assert "Saved to" in app.environment_view.status_var.get()
print(f"PASS: Save Script wrote a real, executable file at {dest_path}.")

# --- The saved file matches what's shown in the preview ---
assert dest_path.read_text() == text.rstrip("\n") + "\n" or dest_path.read_text() == text
print("PASS: saved file content matches the preview.")

# --- Refresh regenerates correctly after switching pdk_root name (simulated) ---
app.environment_view.refresh()
root.update()
text2 = app.environment_view.script_text.get("1.0", "end")
assert text2 == text
print("PASS: Refresh is idempotent against an unchanged pdk_root.")

dest_path.unlink()
root.destroy()

# --- Against a genuinely empty, from-scratch PDK: the label shows the
# real "not yet available" reasons too, not just a silent short list ---
import shutil

EMPTY_ROOT = Path("/tmp/environment_view_empty_pdk")
shutil.rmtree(EMPTY_ROOT, ignore_errors=True)
(EMPTY_ROOT / "libs.tech").mkdir(parents=True)
(EMPTY_ROOT / "libs.ref").mkdir(parents=True)

root2 = tk.Tk()
app2 = App(root2, EMPTY_ROOT)
root2.update()
empty_functions_msg = app2.environment_view.functions_var.get()
print("empty-PDK functions label:", empty_functions_msg)
assert empty_functions_msg.startswith("Defined: librelane_pdk. Not yet available:"), empty_functions_msg
assert "magic_pdk (no real .magicrc found yet" in empty_functions_msg
root2.destroy()
print("PASS: against an empty, from-scratch PDK, the sub-tab shows the real, per-function missing reasons.")

print("ALL ENVIRONMENT VIEW TESTS PASS")

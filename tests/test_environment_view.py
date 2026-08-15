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
print("ALL ENVIRONMENT VIEW TESTS PASS")

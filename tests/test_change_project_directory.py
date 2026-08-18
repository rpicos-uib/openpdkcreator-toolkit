import sys
sys.path.insert(0, "/foss/designs")
import shutil
import tkinter as tk
from pathlib import Path

from openpdkcreator import export as export_mod
from openpdkcreator import project_io
from openpdkcreator.gui.app import App
from openpdkcreator.gui import settings_view as settings_view_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
ORIGINAL_PROJECT_ROOT = export_mod.PROJECT_ROOT
ORIGINAL_SAVE_DIR = project_io.SAVE_DIR

TMP = Path("/tmp/test_change_project_directory")
shutil.rmtree(TMP, ignore_errors=True)
dir_a = TMP / "project_a"
dir_b = TMP / "project_b"
dir_a.mkdir(parents=True)

# Clean any leftover real save/registry from a prior interrupted run, in
# both the real default directory this test starts in and the fixtures.
default_save_path = project_io.save_path_for(PDK_ROOT)
default_save_path.unlink(missing_ok=True)

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

try:
    # --- Starting state: the real, default project directory ---
    assert export_mod.PROJECT_ROOT == ORIGINAL_PROJECT_ROOT
    app.set_project_name("Default-Dir Project")
    app._save_project()
    root.update()
    assert default_save_path.is_file()
    print("PASS: starting project (the real, default directory) saved with a real, distinctive name.")

    # --- Switch to a genuinely new, empty directory: real module
    # constants reassigned, app fully reloaded, fresh/default state ---
    app.change_project_directory(dir_a)
    root.update()
    assert export_mod.PROJECT_ROOT == dir_a.resolve()
    assert export_mod.EXPORT_ROOT == dir_a.resolve() / "export"
    assert project_io.SAVE_DIR == dir_a.resolve() / "saves"
    assert app.library_manager_view.project_root == dir_a.resolve()
    assert app.project_name == settings_view_mod.DEFAULT_PROJECT_NAME
    assert app.settings_view.project_dir_var.get() == str(dir_a.resolve())
    print("PASS: change_project_directory reassigns every real, shared constant and fully reloads to a fresh project.")

    # --- Register a real library + save a distinctive project name in
    # this new directory ---
    from openpdkcreator.pdklib import library_index as li_mod
    li_mod.register_library(dir_a, "my_project_a_lib")
    app.set_project_name("Project-A")
    app._save_project()
    root.update()
    assert (dir_a / "saves" / f"{PDK_ROOT.name}.yaml").is_file()
    assert (dir_a / "library_index.yaml").is_file()
    print("PASS: real edits made after switching land in the new directory's own real saves/library_index.yaml.")

    # --- Switch to a second, different new directory -- confirms this
    # isn't a one-shot special case, and doesn't leak project_a's state ---
    app.change_project_directory(dir_b)
    root.update()
    assert app.project_name == settings_view_mod.DEFAULT_PROJECT_NAME
    assert "my_project_a_lib" not in [name for name, _ in li_mod.merged_libraries(PDK_ROOT, dir_b)]
    print("PASS: a second, different new directory starts fresh too, with none of project_a's own real state.")

    # --- Switch back to the real, default directory -- its own real
    # saved edits (from the very first step) are restored correctly ---
    app.change_project_directory(ORIGINAL_PROJECT_ROOT)
    root.update()
    assert export_mod.PROJECT_ROOT == ORIGINAL_PROJECT_ROOT
    assert project_io.SAVE_DIR == ORIGINAL_SAVE_DIR
    assert app.project_name == "Default-Dir Project"
    print("PASS: switching back to the original directory restores its own real saved project name.")

    # --- Switch to project_a again -- its own real saved state (not
    # the default directory's, not project_b's) comes back correctly ---
    app.change_project_directory(dir_a)
    root.update()
    assert app.project_name == "Project-A"
    assert "my_project_a_lib" in [name for name, _ in li_mod.merged_libraries(PDK_ROOT, dir_a)]
    print("PASS: switching back to project_a restores exactly its own real saved state, not mixed with the others.")

    # --- The GUI-level Browse... flow: a real directory picker plus a
    # real confirmation prompt, both real, blocking dialogs mocked the
    # same way every other test here already mocks them ---
    app.change_project_directory(ORIGINAL_PROJECT_ROOT)
    root.update()
    original_askdirectory = settings_view_mod.filedialog.askdirectory
    original_askyesno = settings_view_mod.messagebox.askyesno
    settings_view_mod.filedialog.askdirectory = lambda **kw: str(dir_b)
    settings_view_mod.messagebox.askyesno = lambda *a, **kw: True
    try:
        app.settings_view._browse_project_directory()
        root.update()
    finally:
        settings_view_mod.filedialog.askdirectory = original_askdirectory
        settings_view_mod.messagebox.askyesno = original_askyesno
    assert export_mod.PROJECT_ROOT == dir_b.resolve()
    print("PASS: Settings > General's own Browse... button drives the real switch end-to-end through the real GUI.")

    # --- Declining the confirmation prompt leaves everything untouched ---
    settings_view_mod.filedialog.askdirectory = lambda **kw: str(dir_a)
    settings_view_mod.messagebox.askyesno = lambda *a, **kw: False
    try:
        app.settings_view._browse_project_directory()
        root.update()
    finally:
        settings_view_mod.filedialog.askdirectory = original_askdirectory
        settings_view_mod.messagebox.askyesno = original_askyesno
    assert export_mod.PROJECT_ROOT == dir_b.resolve()
    print("PASS: declining the confirmation prompt leaves the current project directory unchanged.")

finally:
    # Restore the real, shared module state and clean up every real
    # file this test created, in both the fixture dirs and the real,
    # default project directory other tests also use.
    export_mod.PROJECT_ROOT = ORIGINAL_PROJECT_ROOT
    export_mod.EXPORT_ROOT = ORIGINAL_PROJECT_ROOT / "export"
    project_io.SAVE_DIR = ORIGINAL_SAVE_DIR
    root.destroy()
    default_save_path.unlink(missing_ok=True)
    shutil.rmtree(TMP, ignore_errors=True)

print("ALL CHANGE PROJECT DIRECTORY TESTS PASS")

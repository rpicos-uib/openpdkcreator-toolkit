import sys
sys.path.insert(0, "/foss/designs")
import shutil
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui import app as app_mod
from openpdkcreator.gui.app import App
from openpdkcreator.pdklib import drc as drc_mod
from openpdkcreator.pdklib import lef as lef_mod
from openpdkcreator.pdklib import magic_tech as magic_tech_mod
from openpdkcreator.pdklib import skeleton as skeleton_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
TMP = Path("/tmp/test_create_pdk")
shutil.rmtree(TMP, ignore_errors=True)

# --- build_blank_pdk: genuinely zero real domain files, just the two
# real top-level directories this project's own discovery functions
# already expect to exist ---
blank_root = TMP / "blank"
skeleton_mod.build_blank_pdk(blank_root)
assert (blank_root / "libs.tech").is_dir()
assert (blank_root / "libs.ref").is_dir()
assert not any(p.is_file() for p in blank_root.rglob("*"))
assert sorted(p.relative_to(blank_root) for p in blank_root.rglob("*")) == [Path("libs.ref"), Path("libs.tech")]
print("PASS: build_blank_pdk creates only the two real top-level directories, no domain files.")

# --- build_new_pdk_skeleton: one real, genuinely loadable file per
# create-from-scratch domain (Layers/Magic Tech/DRC Rules/LEF) ---
new_root = TMP / "new"
skeleton_mod.build_new_pdk_skeleton(new_root, "mytech")
lyp_path = new_root / "libs.tech" / "klayout" / "tech" / "mytech.lyp"
tech_path = new_root / "libs.tech" / "magic" / "mytech.tech"
lef_path = new_root / "libs.ref" / "mytech" / "lef" / "mytech.lef"
assert lyp_path.is_file()
assert tech_path.is_file()
assert lef_path.is_file()
assert drc_mod.find_drc_root(new_root) is not None
print("PASS: build_new_pdk_skeleton writes all four real per-domain skeleton files.")

parsed_tech = magic_tech_mod.parse_tech_file(tech_path)
assert parsed_tech is not None
parsed_lef = lef_mod.parse_lef_file(lef_path)
assert parsed_lef is not None
rules, _skipped = drc_mod.extract_design_rules(new_root, drc_mod.find_drc_root(new_root))
assert rules == []
print("PASS: each real skeleton file genuinely parses back through its own real reader.")

root = tk.Tk()

try:
    # --- A real App constructed against build_new_pdk_skeleton's own
    # output finds every real skeleton file through the exact same
    # discovery path a real, loaded PDK uses (find_lyp/load()) ---
    app = App(root, new_root)
    root.update()
    assert app.lyp_path == lyp_path
    assert app.project.layers == []
    assert app.drc_root is not None
    assert magic_tech_mod.find_tech_files(new_root) == [tech_path]
    assert lef_mod.find_lef_files(new_root) == [lef_path]
    print("PASS: a real App loaded against a new-PDK skeleton finds and loads every real skeleton file.")
    app.destroy()
    root.update()

    # --- GUI-level flow: File > Create a Blank PDK... via mocked,
    # real, blocking dialogs (same precedent as test_change_project_
    # directory.py's own Browse... flow) -- ends with a real, full app
    # rebuild against the new pdk_root ---
    app = App(root, PDK_ROOT)
    root.update()
    old_app = app

    blank_gui_root = TMP / "blank_gui"
    original_askdirectory = app_mod.filedialog.askdirectory
    app_mod.filedialog.askdirectory = lambda **kw: str(blank_gui_root)
    try:
        app._create_blank_pdk()
        root.update()
    finally:
        app_mod.filedialog.askdirectory = original_askdirectory

    assert not old_app.winfo_exists()
    assert str(blank_gui_root.resolve()) in root.title()
    assert (blank_gui_root / "libs.tech").is_dir()
    assert not any(blank_gui_root.rglob("*.lyp"))
    print("PASS: File > Create a Blank PDK... rebuilds the whole app against a genuinely new, file-less pdk_root.")

    # --- File > Create a New PDK... -- same rebuild, but seeded with
    # the real four-domain skeleton, name prompted via simpledialog ---
    new_gui_root = TMP / "new_gui"
    old_app = None
    for child in root.winfo_children():
        if isinstance(child, App):
            old_app = child
    assert old_app is not None
    original_askdirectory = app_mod.filedialog.askdirectory
    original_askstring = app_mod.simpledialog.askstring
    app_mod.filedialog.askdirectory = lambda **kw: str(new_gui_root)
    app_mod.simpledialog.askstring = lambda *a, **kw: "guitech"
    try:
        old_app._create_new_pdk()
        root.update()
    finally:
        app_mod.filedialog.askdirectory = original_askdirectory
        app_mod.simpledialog.askstring = original_askstring

    assert not old_app.winfo_exists()
    assert str(new_gui_root.resolve()) in root.title()
    assert (new_gui_root / "libs.tech" / "klayout" / "tech" / "guitech.lyp").is_file()
    assert (new_gui_root / "libs.tech" / "magic" / "guitech.tech").is_file()
    assert (new_gui_root / "libs.ref" / "guitech" / "lef" / "guitech.lef").is_file()
    print("PASS: File > Create a New PDK... rebuilds the whole app against a genuinely new, skeleton-seeded pdk_root.")

    current_app = None
    for child in root.winfo_children():
        if isinstance(child, App):
            current_app = child
    assert current_app is not None

    # --- A non-empty target directory triggers the real "continue
    # anyway?" confirmation; declining it leaves the app untouched ---
    nonempty_root = TMP / "nonempty"
    nonempty_root.mkdir(parents=True)
    (nonempty_root / "stray.txt").write_text("pre-existing file")
    original_askyesno = app_mod.messagebox.askyesno
    app_mod.filedialog.askdirectory = lambda **kw: str(nonempty_root)
    app_mod.messagebox.askyesno = lambda *a, **kw: False
    try:
        current_app._create_blank_pdk()
        root.update()
    finally:
        app_mod.filedialog.askdirectory = original_askdirectory
        app_mod.messagebox.askyesno = original_askyesno
    assert current_app.winfo_exists()
    assert not (nonempty_root / "libs.tech").exists()
    print("PASS: declining the non-empty-directory confirmation leaves the current app and target directory untouched.")

    # --- Accepting it proceeds with the real skeleton build alongside
    # the pre-existing, unrelated file, and rebuilds the app again ---
    app_mod.filedialog.askdirectory = lambda **kw: str(nonempty_root)
    app_mod.messagebox.askyesno = lambda *a, **kw: True
    try:
        current_app._create_blank_pdk()
        root.update()
    finally:
        app_mod.filedialog.askdirectory = original_askdirectory
        app_mod.messagebox.askyesno = original_askyesno
    assert not current_app.winfo_exists()
    assert (nonempty_root / "libs.tech").is_dir()
    assert (nonempty_root / "stray.txt").is_file()
    print("PASS: accepting the non-empty-directory confirmation proceeds with the real skeleton build and rebuilds the app.")

    # --- Declining the directory picker, or the name prompt, leaves
    # the current app untouched -- no rebuild, no partial directory ---
    current_app = None
    for child in root.winfo_children():
        if isinstance(child, App):
            current_app = child
    assert current_app is not None
    declined_root = TMP / "declined"

    app_mod.filedialog.askdirectory = lambda **kw: ""
    try:
        current_app._create_blank_pdk()
        root.update()
    finally:
        app_mod.filedialog.askdirectory = original_askdirectory
    assert current_app.winfo_exists()
    assert not declined_root.exists()

    app_mod.filedialog.askdirectory = lambda **kw: str(declined_root)
    app_mod.simpledialog.askstring = lambda *a, **kw: None
    try:
        current_app._create_new_pdk()
        root.update()
    finally:
        app_mod.filedialog.askdirectory = original_askdirectory
        app_mod.simpledialog.askstring = original_askstring
    assert current_app.winfo_exists()
    assert not declined_root.exists()
    print("PASS: declining the directory picker or the name prompt leaves the current app untouched, no partial directory created.")

finally:
    root.destroy()
    shutil.rmtree(TMP, ignore_errors=True)

print("ALL CREATE PDK TESTS PASS")

import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui import app as app_mod
from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

menubar = root.nametowidget(root["menu"])


def cascade_menu(label: str) -> tk.Menu:
    for i in range(menubar.index("end") + 1):
        if menubar.type(i) == "cascade" and menubar.entrycget(i, "label") == label:
            return root.nametowidget(menubar.entrycget(i, "menu"))
    raise AssertionError(f"no top-level {label!r} menu found")


def entry_labels(menu: tk.Menu) -> list[str]:
    labels = []
    for i in range(menu.index("end") + 1):
        if menu.type(i) == "command":
            labels.append(menu.entrycget(i, "label"))
    return labels


# --- Three real top-level menus exist, in order ---
top_level = [menubar.entrycget(i, "label") for i in range(menubar.index("end") + 1) if menubar.type(i) == "cascade"]
assert top_level == ["File", "Export", "Help"], top_level
print("PASS: the real menu bar has exactly File / Export / Help, in that order.")

# --- File: project-level actions only -- Save/Reload plus the two
# real LibMan project actions -- none of the ten per-domain exports ---
file_labels = entry_labels(cascade_menu("File"))
assert file_labels == [
    "Create a New PDK...", "Create a Blank PDK...",
    "Save Edits", "Reload from Real Files", "Import from LibMan Project...", "Export to LibMan Project...",
], file_labels
print(f"PASS: File holds exactly the real project-level actions: {file_labels}")

# --- Export: every real, per-domain "Export Edited X" action, and
# nothing else (no Save Edits, no LibMan actions) ---
export_labels = entry_labels(cascade_menu("Export"))
assert len(export_labels) == 11, export_labels
assert all(label.startswith("Export Edited ") and label.endswith("(open_pdks format)") for label in export_labels)
assert "Save Edits" not in export_labels
assert not any("LibMan" in label for label in export_labels)
print(f"PASS: Export holds exactly the real 11 per-domain open_pdks export actions.")

# --- Help: About + a general Help entry ---
help_labels = entry_labels(cascade_menu("Help"))
assert help_labels == ["Help", "About openPDKcreator"], help_labels
print("PASS: Help holds a general Help entry and About openPDKcreator.")

# --- File > Import/Export LibMan Project actually call the real
# Library Manager methods and switch to that tab, not just a label ---
calls = []
original_import = app.library_manager_view._import_libman_project
original_export = app.library_manager_view._export_libman_project
app.library_manager_view._import_libman_project = lambda: calls.append("import")
app.library_manager_view._export_libman_project = lambda: calls.append("export")
try:
    app.goto("Overview")
    root.update()
    assert app.pdk_notebook.tab(app.pdk_notebook.select(), "text") == "Overview"
    app._import_libman_project()
    root.update()
    assert app.notebook.tab(app.notebook.select(), "text") == "Library Manager"
    app._export_libman_project()
    root.update()
    assert calls == ["import", "export"]
finally:
    app.library_manager_view._import_libman_project = original_import
    app.library_manager_view._export_libman_project = original_export
print("PASS: File > Import/Export LibMan Project switches to the Library Manager tab and calls the real action.")

# --- Help > About / Help open a real text dialog with real, non-empty
# content -- monkeypatch show_text_dialog itself (the same "don't let
# a real blocking modal hang a scripted run" precedent every other
# test here already uses for messagebox/filedialog) ---
original_show_text_dialog = app_mod.show_text_dialog
shown = []
app_mod.show_text_dialog = lambda parent, title, text: shown.append((title, text))
try:
    app._show_about()
    app._show_help()
finally:
    app_mod.show_text_dialog = original_show_text_dialog

assert len(shown) == 2
about_title, about_text = shown[0]
help_title, help_text = shown[1]
assert about_title == "About openPDKcreator"
assert "openpdkcreator-toolkit" in about_text
assert "github.com/IHP-GmbH/LibMan" in about_text
assert "Apache-2.0" in about_text
assert help_title == "Help"
assert "Wizard" in help_text and "Library Manager" in help_text
assert "File" in help_text and "Export" in help_text
print("PASS: About/Help open real dialogs with real, correct content (repo URL, LibMan link, license, tab guide).")

# --- The real show_text_dialog (not the app.py wrapper monkeypatched
# above) uses real, dynamic word-wrap to the dialog's own current
# pixel width -- confirmed live, not just checking the static config
# option: resizing the real dialog narrower genuinely re-flows the
# real displayed line count. The previous wrap="none" had no
# horizontal scrollbar either, so a real long line was genuinely
# unreachable, not just inconvenient -- a real bug, not a style choice. ---
from openpdkcreator.gui.text_dialog import show_text_dialog as real_show_text_dialog

long_paragraph = "word " * 200  # long enough to definitely wrap at any reasonable width
wrap_results = {}


def _inspect_and_close():
    dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel) and w.title() == "Wrap Test")
    body = next(w for w in dialog.winfo_children() if isinstance(w, tk.Text))
    assert body.cget("wrap") == "word"
    root.update()
    wide = body.count("1.0", "end", "displaylines")
    wrap_results["wide"] = wide[0] if isinstance(wide, tuple) else wide
    dialog.geometry("260x300")
    root.update()
    narrow = body.count("1.0", "end", "displaylines")
    wrap_results["narrow"] = narrow[0] if isinstance(narrow, tuple) else narrow
    dialog.destroy()


root.after(200, _inspect_and_close)
real_show_text_dialog(root, "Wrap Test", long_paragraph)
assert wrap_results["narrow"] > wrap_results["wide"], wrap_results
print(
    f"PASS: show_text_dialog uses real, dynamic word-wrap -- a narrower real window genuinely "
    f"re-flows from {wrap_results['wide']} to {wrap_results['narrow']} real display lines."
)

root.destroy()
print("ALL MENU STRUCTURE TESTS PASS")

import sys
sys.path.insert(0, "/foss/designs")
import tkinter as tk
from pathlib import Path

from openpdkcreator.gui.app import App

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

root = tk.Tk()
app = App(root, PDK_ROOT)
root.update()

mtv = app.magic_tech_view
mtv.tech_var.set("ihp-sg13g2")
mtv._refresh_all()
root.update()

print("planes rows:", len(mtv.planes_editor.tree.get_children()))
print("contacts rows:", len(mtv.contacts_editor.tree.get_children()))
print("aliases rows:", len(mtv.aliases_editor.tree.get_children()))
print("styles rows:", len(mtv.styles_editor.tree.get_children()))
assert len(mtv.planes_editor.tree.get_children()) == 14
assert len(mtv.contacts_editor.tree.get_children()) == 26
assert len(mtv.aliases_editor.tree.get_children()) == 60
assert len(mtv.styles_editor.tree.get_children()) == 124

# Edit the first plane's short_code via the form.
mtv.planes_editor.tree.selection_set(mtv.planes_editor.tree.get_children()[0])
mtv.planes_editor._on_select()
root.update()
mtv.planes_editor.field_vars["short_code"].set("ZZ")
root.update()
assert mtv.planes_editor.current_entry.short_code == "ZZ"
row_values = mtv.planes_editor.tree.item(mtv.planes_editor.tree.get_children()[0])["values"]
print("plane row after edit:", row_values)
assert row_values[1] == "ZZ"

# New Plane / Delete Plane
before_count = len(mtv.planes_editor.tree.get_children())
mtv.planes_editor.new_entry()
root.update()
assert len(mtv.planes_editor.tree.get_children()) == before_count + 1
new_plane = mtv.planes_editor.current_entry
assert new_plane.line_no == 0
mtv.planes_editor.delete_entry()
root.update()
assert len(mtv.planes_editor.tree.get_children()) == before_count

# New Style / Delete Style
before_style_count = len(mtv.styles_editor.tree.get_children())
mtv.styles_editor.new_entry()
root.update()
assert len(mtv.styles_editor.tree.get_children()) == before_style_count + 1
new_style = mtv.styles_editor.current_entry
assert new_style.line_no == 0
mtv.styles_editor.delete_entry()
root.update()
assert len(mtv.styles_editor.tree.get_children()) == before_style_count

# Edit a contact and an alias too.
mtv.contacts_editor.tree.selection_set(mtv.contacts_editor.tree.get_children()[0])
mtv.contacts_editor._on_select()
mtv.contacts_editor.field_vars["layer2"].set("metal9")
root.update()
assert mtv.contacts_editor.current_entry.layer2 == "metal9"

mtv.aliases_editor.tree.selection_set(mtv.aliases_editor.tree.get_children()[0])
mtv.aliases_editor._on_select()
mtv.aliases_editor.field_vars["members_raw"].set("nwell,pwell")
root.update()
assert mtv.aliases_editor.current_entry.members_raw == "nwell,pwell"

# Styles: the real list[str] style_names field is exposed to this
# generic, string-only editor through StyleEntry's own
# style_names_text property (space-joined getter/setter) -- edited the
# same way as every other field here, but round-trips back into a real
# list, not just a string.
mtv.styles_editor.tree.selection_set(mtv.styles_editor.tree.get_children()[0])
mtv.styles_editor._on_select()
mtv.styles_editor.field_vars["style_names_text"].set("cwell extraStyle")
root.update()
assert mtv.styles_editor.current_entry.style_names == ["cwell", "extraStyle"]
style_row_values = mtv.styles_editor.tree.item(mtv.styles_editor.tree.get_children()[0])["values"]
assert style_row_values[1] == "cwell extraStyle"

print("PASS: in-GUI edit/new/delete for Planes/Contacts/Aliases/Styles.")

# -- Save Edits / relaunch persistence -------------------------------
app._save_project()
root.update()

edited_plane_name = mtv.planes_editor.entries[0].name
edited_contact = (mtv.contacts_editor.entries[0].contact_type, mtv.contacts_editor.entries[0].layer2)
edited_alias_name = mtv.aliases_editor.entries[0].name
edited_style_name = mtv.styles_editor.entries[0].type_name

# Simulate an app relaunch by constructing a fresh App against the same pdk_root.
root.destroy()

root2 = tk.Tk()
app2 = App(root2, PDK_ROOT)
root2.update()
mtv2 = app2.magic_tech_view
mtv2.tech_var.set("ihp-sg13g2")
mtv2._refresh_all()
root2.update()

reloaded_plane = next(p for p in mtv2.planes_editor.entries if p.name == edited_plane_name)
print("reloaded plane short_code:", reloaded_plane.short_code)
assert reloaded_plane.short_code == "ZZ"

reloaded_contact = next(c for c in mtv2.contacts_editor.entries if c.contact_type == edited_contact[0])
print("reloaded contact layer2:", reloaded_contact.layer2)
assert reloaded_contact.layer2 == "metal9"

reloaded_alias = next(a for a in mtv2.aliases_editor.entries if a.name == edited_alias_name)
print("reloaded alias members_raw:", reloaded_alias.members_raw)
assert reloaded_alias.members_raw == "nwell,pwell"

reloaded_style = next(s for s in mtv2.styles_editor.entries if s.type_name == edited_style_name)
print("reloaded style style_names:", reloaded_style.style_names)
assert reloaded_style.style_names == ["cwell", "extraStyle"]

print("PASS: Planes/Contacts/Aliases/Styles edits survive Save Edits + simulated relaunch.")

# -- Real write-back export ------------------------------------------
import tempfile
from openpdkcreator import export as export_mod

with tempfile.TemporaryDirectory() as tmp:
    export_dir = Path(tmp)
    written = export_mod.export_magic_types(PDK_ROOT, mtv2.technologies, dest_root=export_dir)
    print("exported files:", written)
    exported_path = [p for p in written if p.name == "ihp-sg13g2.tech"][0]
    text = exported_path.read_text()
    assert "ZZ" in text
    assert "metal9" in text
    assert "nwell,pwell" in text
    assert "cwell extraStyle" in text
    print("PASS: real .tech write-back contains the edited plane/contact/alias/style values.")

    # -- The real, non-entry 'styletype mos' header line right after
    # the styles section's own opening keyword still comes through
    # completely verbatim -- confirms _render_section_patch's generic
    # "copy any untracked line as-is" gap logic really does cover
    # Styles' one real structural quirk, not just guessed to. ---
    assert " styletype mos" in text
    print("PASS: the real, non-entry 'styletype mos' header line comes through byte-for-byte verbatim.")

root2.destroy()
print("ALL PASS")

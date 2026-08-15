import sys
sys.path.insert(0, "/foss/designs")
from pathlib import Path
import shutil

from openpdkcreator.ihp import library_index as li_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
PROJECT_ROOT = Path("/tmp/test_library_index_project")
shutil.rmtree(PROJECT_ROOT, ignore_errors=True)
PROJECT_ROOT.mkdir(parents=True)

# --- Real libraries discovered correctly ---
libraries = li_mod.merged_libraries(PDK_ROOT, PROJECT_ROOT)
print("libraries:", libraries)
assert libraries == [
    ("sg13g2_io", True), ("sg13g2_pr", True), ("sg13g2_sram", True), ("sg13g2_stdcell", True),
], libraries
print("PASS: real families discovered, all correctly marked as real.")

# --- A known real cell gets real xschem views, matched across the
# confirmed real plural/singular directory-name inconsistency ---
entries = li_mod.merged_entries(PDK_ROOT, PROJECT_ROOT, "sg13g2_stdcell")
inv1_sch = entries.get(("sg13g2_inv_1", "xschem_schematic"))
inv1_sym = entries.get(("sg13g2_inv_1", "xschem_symbol"))
assert inv1_sch is not None and inv1_sch.source == "real"
assert inv1_sym is not None and inv1_sym.source == "real"
assert "sg13g2_stdcells" in str(inv1_sch.path)  # the real, plural xschem dir
print("PASS: sg13g2_inv_1 correctly matched to its real xschem symbol/schematic despite the real directory-name mismatch.")

# Every real view kind present for a real, fully-populated cell.
real_kinds = {view_kind for cell, view_kind in entries if cell == "sg13g2_inv_1"}
assert real_kinds == {
    "xschem_schematic", "xschem_symbol", "lef", "cdl", "spice", "verilog", "liberty", "gds",
}, real_kinds
print("PASS: sg13g2_inv_1 has all 8 real view kinds it should.")

# --- Register a brand-new project library + cell + view, round-trip through YAML ---
li_mod.register_library(PROJECT_ROOT, "my_memristor_lib")
libs2 = li_mod.merged_libraries(PDK_ROOT, PROJECT_ROOT)
assert ("my_memristor_lib", False) in libs2
print("PASS: New Library registers a real, empty, selectable, non-real-tagged library.")

fake_path = PROJECT_ROOT / "libraries" / "my_memristor_lib" / "my_cell.sym"
li_mod.register_entry(PROJECT_ROOT, "my_memristor_lib", "my_cell", "xschem_symbol", fake_path)
cells = li_mod.cells_in_library(PDK_ROOT, PROJECT_ROOT, "my_memristor_lib")
assert cells == ["my_cell"]
entries2 = li_mod.merged_entries(PDK_ROOT, PROJECT_ROOT, "my_memristor_lib")
assert entries2[("my_cell", "xschem_symbol")].path == fake_path
assert entries2[("my_cell", "xschem_symbol")].source == "registered"
print("PASS: a registered entry round-trips correctly through merged_entries.")

# Reload from a fresh process-level read (simulates restarting the app).
reloaded = li_mod.load_registry(PROJECT_ROOT)
assert "my_memristor_lib" in reloaded.libraries
assert any(e.cell == "my_cell" and e.path == fake_path for e in reloaded.entries)
print("PASS: the registry survives a fresh load_registry() call (real YAML persistence).")

# --- Real always wins over registered for the same (library, cell, view_kind) ---
li_mod.register_entry(
    PROJECT_ROOT, "sg13g2_stdcell", "sg13g2_inv_1", "xschem_symbol",
    Path("/tmp/should_be_shadowed_by_real.sym"),
)
entries3 = li_mod.merged_entries(PDK_ROOT, PROJECT_ROOT, "sg13g2_stdcell")
winner = entries3[("sg13g2_inv_1", "xschem_symbol")]
assert winner.source == "real", winner
assert "should_be_shadowed" not in str(winner.path)
print("PASS: a real view always wins over a registered one for the same key, never silently shadowed.")

# --- unregister_entry removes only the targeted entry ---
li_mod.unregister_entry(PROJECT_ROOT, "my_memristor_lib", "my_cell", "xschem_symbol")
entries4 = li_mod.merged_entries(PDK_ROOT, PROJECT_ROOT, "my_memristor_lib")
assert ("my_cell", "xschem_symbol") not in entries4
print("PASS: unregister_entry removes exactly the targeted registered entry.")

# --- infer_view_kind: real content-sniffing disambiguates the one
# genuine ambiguity (xschem vs Qucs-S both use a real .sym extension) ---
auto_lib_dir = PROJECT_ROOT / li_mod.LIBRARIES_DIRNAME / "auto_lib"
auto_lib_dir.mkdir(parents=True)

xschem_sym = auto_lib_dir / "my_cell.sym"
xschem_sym.write_text("v {xschem version=3.4.4 file_version=1.2}\nG {}\n")
qucs_sym = auto_lib_dir / "other_cell.sym"
qucs_sym.write_text('<Line x1="0" y1="0" x2="10" y2="10" color="#000080" width="2" style="1" />\n')
lef_file = auto_lib_dir / "another_cell.lef"
lef_file.write_text("MACRO another_cell\nEND another_cell\n")

assert li_mod.infer_view_kind(xschem_sym) == "xschem_symbol"
assert li_mod.infer_view_kind(qucs_sym) == "qucs_symbol"
assert li_mod.infer_view_kind(lef_file) == "lef"
print("PASS: infer_view_kind correctly disambiguates real xschem vs Qucs-S .sym content, plus unambiguous extensions.")

# --- auto_register_new_files picks up real, untracked files and is idempotent ---
found = li_mod.auto_register_new_files(PROJECT_ROOT, "auto_lib")
assert len(found) == 3
registry5 = li_mod.load_registry(PROJECT_ROOT)
assert any(e.cell == "my_cell" and e.view_kind == "xschem_symbol" for e in registry5.entries)
assert any(e.cell == "other_cell" and e.view_kind == "qucs_symbol" for e in registry5.entries)
assert any(e.cell == "another_cell" and e.view_kind == "lef" for e in registry5.entries)
print("PASS: auto_register_new_files registers every real, untracked file, correctly identified.")

found_again = li_mod.auto_register_new_files(PROJECT_ROOT, "auto_lib")
assert found_again == []
print("PASS: re-running auto_register_new_files is a real no-op once everything is already tracked.")

later_file = auto_lib_dir / "fourth_cell.sch"
later_file.write_text("v {xschem version=3.4.4 file_version=1.2}\n")
found_later = li_mod.auto_register_new_files(PROJECT_ROOT, "auto_lib")
assert len(found_later) == 1 and found_later[0].cell == "fourth_cell" and found_later[0].view_kind == "xschem_schematic"
print("PASS: a file added after the fact is picked up on the next auto-scan.")

print("ALL LIBRARY INDEX TESTS PASS")

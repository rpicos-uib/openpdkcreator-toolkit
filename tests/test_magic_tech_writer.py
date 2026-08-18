import sys
sys.path.insert(0, "/foss/designs")
from pathlib import Path

from openpdkcreator.pdklib import magic_tech as mt
from openpdkcreator.pdklib import magic_tech_writer as mtw

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

# --- Test 1: no-edit export == byte-identical original, for both real technologies ---
for path in mt.find_tech_files(PDK_ROOT):
    tech = mt.parse_tech_file(path)
    if not tech.name:
        continue
    rendered = mtw.render_tech_file(path, tech)
    original = path.read_text(encoding="utf-8", errors="replace")
    if not original.endswith("\n"):
        original += "\n"
    if rendered != original:
        r_lines, o_lines = rendered.splitlines(), original.splitlines()
        print(f"MISMATCH: {path.name} ({len(r_lines)} vs {len(o_lines)} lines)")
        for i, (a, b) in enumerate(zip(r_lines, o_lines)):
            if a != b:
                print(f"  line {i+1}: {a!r} != {b!r}")
                break
        raise SystemExit(1)
    print(f"PASS: no-edit export of {path.name} ({len(tech.types)} types) is byte-identical to the original.")

# --- Test 2: edit a type's name/aliases/obsolete, export, re-parse, confirm ---
path = PDK_ROOT / "libs.tech/magic/ihp-sg13g2.tech"
tech = mt.parse_tech_file(path)
type_entry = next(t for t in tech.types if t.canonical_name == "dnwell")
original_name, original_aliases, original_obsolete = type_entry.canonical_name, list(type_entry.aliases), type_entry.obsolete
type_entry.canonical_name = "dnwell_renamed"
type_entry.aliases = ["dnw", "dnwell_extra_alias"]
type_entry.obsolete = True

export_path = Path("/tmp/test_export_types.tech")
mtw.export_tech_file(tech, export_path)
reparsed = mt.parse_tech_file(export_path)
assert len(reparsed.types) == len(tech.types) == 118, len(reparsed.types)
re_type = next(t for t in reparsed.types if t.canonical_name == "dnwell_renamed")
assert re_type.aliases == ["dnw", "dnwell_extra_alias"]
assert re_type.obsolete is True
print(f"PASS: edited type ({original_name}/{original_aliases}/obsolete={original_obsolete} -> "
      f"dnwell_renamed/['dnw', 'dnwell_extra_alias']/obsolete=True) reflected correctly in re-parsed export.")

# Confirm every OTHER type is untouched vs. a fresh parse.
fresh = mt.parse_tech_file(path)
mismatches = []
for ft, rt in zip(fresh.types, reparsed.types):
    if ft.canonical_name == "dnwell":
        continue
    if (ft.plane, ft.canonical_name, ft.aliases, ft.obsolete) != (rt.plane, rt.canonical_name, rt.aliases, rt.obsolete):
        mismatches.append((ft.canonical_name, rt.canonical_name))
assert not mismatches, mismatches
print(f"PASS: all {len(fresh.types) - 1} other types are unchanged vs. a fresh parse.")

# --- Test 3: new type ---
tech2 = mt.parse_tech_file(path)
new_type = mt.TypeEntry(plane="dwell", canonical_name="zz_new_type", aliases=["zzalias"], obsolete=False)
tech2.types.append(new_type)
export_path2 = Path("/tmp/test_export_newtype.tech")
mtw.export_tech_file(tech2, export_path2)
reparsed2 = mt.parse_tech_file(export_path2)
assert len(reparsed2.types) == 119, len(reparsed2.types)
re_new = next(t for t in reparsed2.types if t.canonical_name == "zz_new_type")
assert re_new.plane == "dwell" and re_new.aliases == ["zzalias"] and not re_new.obsolete
print("PASS: a brand-new type (New Type) is exported correctly and re-parses with the right fields.")

# --- Test 4: deleted type ---
tech3 = mt.parse_tech_file(path)
original_count = len(tech3.types)
deleted = next(t for t in tech3.types if t.canonical_name == "pblock")
tech3.types.remove(deleted)
export_path3 = Path("/tmp/test_export_deltype.tech")
mtw.export_tech_file(tech3, export_path3)
reparsed3 = mt.parse_tech_file(export_path3)
assert len(reparsed3.types) == original_count - 1
assert "pblock" not in [t.canonical_name for t in reparsed3.types]
assert [t.canonical_name for t in reparsed3.types] == [t.canonical_name for t in tech3.types]
print(f"PASS: a deleted type (pblock) is correctly omitted from the export ({original_count} -> {len(reparsed3.types)} types).")

# --- Test 5: GDS technology (a genuinely separate file, no includes at all) ---
gds_path = PDK_ROOT / "libs.tech/magic/ihp-sg13g2-GDS.tech"
gds_tech = mt.parse_tech_file(gds_path)
gds_type = gds_tech.types[5]
original_gds_name = gds_type.canonical_name
gds_type.canonical_name = "gds_renamed_type"
export_path5 = Path("/tmp/test_export_gds.tech")
mtw.export_tech_file(gds_tech, export_path5)
reparsed5 = mt.parse_tech_file(export_path5)
assert reparsed5.types[5].canonical_name == "gds_renamed_type"
assert len(reparsed5.types) == len(gds_tech.types)
print(f"PASS: GDS technology ({len(gds_tech.types)} real types) no-edit byte-identical, and a real type edit round-trips.")

print("ALL PASS")

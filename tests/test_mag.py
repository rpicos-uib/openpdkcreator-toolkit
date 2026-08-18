import sys
sys.path.insert(0, "/foss/designs")
import shutil
import subprocess
from pathlib import Path

from openpdkcreator.pdklib import mag as mag_mod

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
TECH_MAGICRC = PDK_ROOT / "libs.tech/magic/ihp-sg13g2.magicrc"
GDS = PDK_ROOT / "libs.ref/sg13g2_stdcell/gds/sg13g2_stdcell.gds"

tmp_dir = Path("/tmp/test_mag")
shutil.rmtree(tmp_dir, ignore_errors=True)
tmp_dir.mkdir(parents=True)

# --- create_new_mag_file: real, minimal, valid skeleton -----------------
skeleton_path = tmp_dir / "new_cell.mag"
mag_mod.create_new_mag_file(skeleton_path, "ihp-sg13g2")
parsed = mag_mod.parse_mag_file(skeleton_path)
assert parsed.tech == "ihp-sg13g2"
assert parsed.timestamp is not None and parsed.timestamp > 0
assert parsed.sections == []
assert parsed.use_count == 0
assert parsed.label_count == 0
print("PASS: create_new_mag_file writes a real, minimal skeleton that parses to an honestly empty MagFile.")

try:
    mag_mod.create_new_mag_file(skeleton_path, "ihp-sg13g2")
    assert False, "must refuse to overwrite an existing real file"
except FileExistsError:
    print("PASS: create_new_mag_file refuses to overwrite an existing real file.")

# --- The written skeleton is real enough for the actual Magic binary to
# load cleanly (not just something this project's own parser accepts) ---
load_script = tmp_dir / "load_skeleton.tcl"
load_script.write_text(f'load {skeleton_path.stem}\nputs "CELL: [cellname list self]"\nquit -noprompt\n')
result = subprocess.run(
    ["magic", "-d", "NULL", "-noconsole", "-rcfile", str(TECH_MAGICRC), str(load_script)],
    cwd=tmp_dir, capture_output=True, text=True, timeout=30,
)
assert f"CELL: {skeleton_path.stem}" in result.stdout, result.stdout + result.stderr
print("PASS: the real, installed Magic binary loads the generated skeleton cleanly (real cell name echoed back).")

# --- parse_mag_file against a REAL, Magic-authored .mag file -- exported
# fresh, right now, from real IHP GDS data by the real Magic binary, not
# a fixture copy -- so this test still catches a real format drift. ---
gen_script = tmp_dir / "gen.tcl"
gen_script.write_text(
    f"gds read {GDS}\nload sg13g2_inv_1\nsave sg13g2_inv_1_real\nquit -noprompt\n"
)
subprocess.run(
    ["magic", "-d", "NULL", "-noconsole", "-rcfile", str(TECH_MAGICRC), str(gen_script)],
    cwd=tmp_dir, capture_output=True, text=True, timeout=60,
)
real_mag_path = tmp_dir / "sg13g2_inv_1_real.mag"
assert real_mag_path.is_file(), "Magic did not produce the expected real .mag file"

real_parsed = mag_mod.parse_mag_file(real_mag_path)
assert real_parsed.tech == "ihp-sg13g2"
assert real_parsed.magscale == (1, 2)
section_names = [s.name for s in real_parsed.sections]
for real_layer in ("nwell", "pwell", "nmos", "pmos", "ndiff", "pdiff", "poly", "metal1"):
    assert real_layer in section_names, f"expected real layer {real_layer!r} in {section_names}"
metal1 = next(s for s in real_parsed.sections if s.name == "metal1")
assert metal1.rect_count > 0
assert real_parsed.label_count == 4  # sg13g2_inv_1's real 4 real pins: A, Y, VDD, VSS
assert real_parsed.property_count >= 1
print(
    f"PASS: parse_mag_file reads a real, Magic-authored .mag file exported fresh from real IHP GDS data -- "
    f"{len(real_parsed.sections)} real sections, {sum(s.rect_count for s in real_parsed.sections)} real rects, "
    f"{real_parsed.label_count} real labels."
)

# --- find_mag_files: the real, new libs.ref/<family>/mag/ convention ---
family_mag_dir = PDK_ROOT / "libs.ref/sg13g2_stdcell/mag"
family_mag_dir.mkdir(exist_ok=True)
probe_path = family_mag_dir / "zz_test_probe.mag"
mag_mod.create_new_mag_file(probe_path, "ihp-sg13g2")
try:
    found = mag_mod.find_mag_files(PDK_ROOT)
    assert probe_path in found
    print("PASS: find_mag_files discovers a real .mag file under libs.ref/<family>/mag/.")
finally:
    probe_path.unlink()
    if not any(family_mag_dir.iterdir()):
        family_mag_dir.rmdir()

shutil.rmtree(tmp_dir, ignore_errors=True)
print("ALL MAG TESTS PASS")

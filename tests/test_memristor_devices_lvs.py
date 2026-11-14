import sys
sys.path.insert(0, "/foss/designs")
# openPDKcreator from this checkout, pointed at the openMemristorPDK project
# (same as main.py --project-root openMemristorPDK).
from main import use_project_root as _use_project_root  # noqa: E402
_use_project_root(__import__("pathlib").Path("/foss/designs/openMemristorPDK"))
from pathlib import Path

from openpdkcreator.pdklib import extraction as ext_mod
from openpdkcreator.pdklib import memristor_extract as mx_mod

PDK_ROOT = Path("/foss/designs/openMemristorPDK/data/openmemristorpdk")
LIB_DIR = Path("/foss/designs/openMemristorPDK/libraries/openmemristorpdk_pr")

# --- Magic's own extraction finds each single-device cell's memristor.
# These cells draw be_au, the oxide and the top electrode as exactly
# coincident rects. via1 used to be declared as a second name of be_au
# (`botmetal be_au,via1`) with `contact via1 be_au te_au`, so Magic
# reclassified every be_au/te_* overlap as a via1 contact tile: the top
# electrode vanished, no be_au was left for `device subcircuit ...` and
# raw extraction found 0 devices (the GDS export lost the TE layer too).
# via1 is now its own type on its own GDS layer (15/0), present only
# where a via is drawn, so Magic sees the real device stack again. -------
tech_file = ext_mod.default_tech_file(PDK_ROOT)
for stem in ["memristor_tio2_au", "memristor_tio2_ti", "memristor_hfo2_al"]:
    mag_path = LIB_DIR / f"{stem}.mag"
    raw_result = ext_mod.run_extract(mag_path, tech_file, "magic", mode="lvs")
    assert raw_result.ok, raw_result.log
    raw_text = raw_result.spice_path.read_text()
    raw_device_count = sum(1 for line in raw_text.splitlines() if line.startswith("X"))
    assert raw_device_count == 1, (
        f"{stem}: Magic's own extraction should find exactly this cell's one memristor, found "
        f"{raw_device_count} -- check that via1 is still its own drawn type (not an alias of be_au) "
        "in openmemristorpdk.tech."
    )
print("PASS: Magic's own raw extraction finds the 1 real device in each of the 3 single-device cells.")

# --- the real fix: the same pdklib/memristor_extract.py geometry-driven
# patch built for the crossbar cells does not depend on Magic's own raw
# device count at all -- computed directly from real (gate_type,
# term_type) rect overlap, inserted before the real .ends/.ENDS line
# when there is no real X line left to replace. Real, live LVS now
# matches for all 3 real cells, not just the crossbars. ------------------
for stem in ["memristor_tio2_au", "memristor_tio2_ti", "memristor_hfo2_al"]:
    mag_path = LIB_DIR / f"{stem}.mag"
    cdl_path = LIB_DIR / f"{stem}.cdl"
    patched_result = mx_mod.run_extract_with_memristor_patch(mag_path, tech_file, "magic", mode="lvs")
    assert patched_result.ok, patched_result.log
    patched_text = patched_result.spice_path.read_text()
    patched_device_count = sum(1 for line in patched_text.splitlines() if line.startswith("X"))
    assert patched_device_count == 1, (stem, patched_device_count)

    patched_lvs = ext_mod.run_lvs(patched_result.spice_path, stem, cdl_path, stem, "netgen")
    assert patched_lvs.matched is True, (stem, patched_lvs.report_text)
    print(f"PASS: {stem} -- real, patched extraction finds its real device, real, live Netgen LVS "
          f"reports Circuits match uniquely.")

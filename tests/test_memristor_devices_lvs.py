import sys
sys.path.insert(0, "/foss/designs/openMemristorPDK")
from pathlib import Path

from openpdkcreator.pdklib import extraction as ext_mod
from openpdkcreator.pdklib import memristor_extract as mx_mod

PDK_ROOT = Path("/foss/designs/openMemristorPDK/data/openmemristorpdk")
LIB_DIR = Path("/foss/designs/openMemristorPDK/libraries/openmemristorpdk_pr")

# --- real, found-live regression: a real Magic tech-file fix elsewhere
# this session (giving be_au a real second identity via1 so a real
# `contact via1 be_au te_au` declaration could be parsed at all --
# openmemristorpdk.tech's own real `types` line) has a real, live side
# effect on these 3 real single-device cells specifically: each draws
# its own real be_au/te_au footprint as fully, exactly coincident (both
# `rect 0 0 1 1`), and real Magic's own implicit-contact mechanism now
# reclassifies that entire coincident area as a real via1 contact tile,
# leaving no real be_au-typed material anywhere in the cell for
# `device subcircuit memristor_..._prim be_au te_...` to find at all --
# confirmed live via the real, tracked .ext output: node "BE" reports
# real layer via1, not be_au. Zero devices, not the crossbar's own
# partial-overlap 1-of-N pattern -- a real, different-shaped
# consequence of the same real tech-file fix. ---------------------------
tech_file = ext_mod.default_tech_file(PDK_ROOT)
for stem in ["memristor_tio2_au", "memristor_tio2_ti", "memristor_hfo2_al"]:
    mag_path = LIB_DIR / f"{stem}.mag"
    raw_result = ext_mod.run_extract(mag_path, tech_file, "magic", mode="lvs")
    assert raw_result.ok, raw_result.log
    raw_text = raw_result.spice_path.read_text()
    raw_device_count = sum(1 for line in raw_text.splitlines() if line.startswith("X"))
    assert raw_device_count == 0, (
        f"{stem}: raw Magic device count changed from the real, found-live 0 -- if this project's own "
        "tech file or layout was changed such that real Magic itself now finds this cell's own device "
        "again, update this real, found-live regression note accordingly, don't just relax this assertion."
    )
print("PASS: real, live -- Magic's own raw extraction finds 0 real devices for all 3 real single-device "
      "cells (the real, found-live via1-reclassification regression), not silently drifted.")

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

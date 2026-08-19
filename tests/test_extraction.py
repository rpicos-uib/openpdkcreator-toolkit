"""Real, driven test of ``pdklib/extraction.py`` -- batch-mode Magic
layout extraction and Netgen LVS, run against real Magic/Netgen inside
this container (not mocked; see ``tests/README.md``).

Builds a real, minimal, from-scratch Magic technology (one plane, one
metal type, a real ``connect``/``extract`` section with a real
``resist`` directive -- found, empirically, to be required: a
conductor type with no ``resist`` line is treated by Magic's own real
extractor as a non-electrical type and silently dropped from the
output netlist entirely, not just left unparasitized) and a real
two-pad ``.mag`` test cell, then drives both real extraction modes and
a real Netgen LVS run against it."""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/foss/designs")

from openpdkcreator.pdklib import extraction as ex

MINI_TECH = """\
tech
  format 35
  mini
end

version
 version 0.1.0
 description "minimal extraction test tech"
end

planes
metal,m
end

types
metal m1
end

contact
end

aliases
end

styles
styletype mos
m1 metal1
end

compose
end

connect
m1 m1
end

drc
end

extract
style ngspice
    cscale 1
    lambda 1.0
    units microns
    step 7
    sidehalo 8
    planeorder metal 0
    resist m1/metal 100
end
"""

work = Path(tempfile.mkdtemp(prefix="openpdkcreator_extraction_test_"))
try:
    tech_file = work / "mini.tech"
    tech_file.write_text(MINI_TECH, encoding="utf-8")

    mag_path = work / "testcell.mag"
    build_script = work / "build.tcl"
    build_script.write_text(
        f"tech load {tech_file}\n"
        f"cd {work}\n"
        "load testcell\n"
        "box 0 0 2 5\n"
        "paint m1\n"
        "label A\n"
        "port make\n"
        "box 8 0 10 5\n"
        "paint m1\n"
        "label B\n"
        "port make\n"
        "port renumber\n"
        "save testcell\n"
        "quit -noprompt\n",
        encoding="utf-8",
    )
    import subprocess
    build = subprocess.run(
        ["magic", "-dnull", "-noconsole", str(build_script)],
        capture_output=True, text=True, cwd=work, timeout=60,
    )
    assert mag_path.is_file(), f"real Magic didn't write {mag_path}:\n{build.stdout}\n{build.stderr}"
    print("PASS: real Magic built a real, freshly-drawn two-pad test cell.")

    # --- 1. Parasitic-mode extraction produces a real subckt with both real, named ports ---
    result = ex.run_extract(mag_path, tech_file, "magic", mode="parasitic")
    assert result.ok, f"real Magic extraction (parasitic) failed:\n{result.log}"
    spice_text = result.spice_path.read_text(encoding="utf-8")
    assert ".subckt testcell" in spice_text and "A" in spice_text and "B" in spice_text, spice_text
    assert ".ends" in spice_text
    print("PASS: real parasitic-mode extraction wrote a real .subckt with both real ports.")

    # --- 2. LVS-preset extraction also produces the same real two-port subckt ---
    lvs_extract = ex.run_extract(mag_path, tech_file, "magic", mode="lvs")
    assert lvs_extract.ok, f"real Magic extraction (lvs) failed:\n{lvs_extract.log}"
    lvs_spice_text = lvs_extract.spice_path.read_text(encoding="utf-8")
    assert ".subckt testcell" in lvs_spice_text and "A" in lvs_spice_text and "B" in lvs_spice_text
    print("PASS: real LVS-preset extraction wrote the same real two-port subckt.")

    # --- 3. Real Netgen LVS: a matching reference reports no pin mismatch ---
    ref_match = work / "ref_match.spice"
    ref_match.write_text(".subckt testcell A B\n.ends\n", encoding="utf-8")
    lvs_match = ex.run_lvs(lvs_extract.spice_path, "testcell", ref_match, "testcell", "netgen")
    assert lvs_match.report_text, f"real netgen wrote no report:\n{lvs_match.log}"
    assert "no matching pin" not in lvs_match.report_text
    assert "Cell pin lists are equivalent." in lvs_match.report_text
    print("PASS: real Netgen LVS against a matching reference reports equivalent pin lists.")

    # --- 4. Real Netgen LVS: a reference with an extra pin is flagged as a real mismatch ---
    ref_mismatch = work / "ref_mismatch.spice"
    ref_mismatch.write_text(".subckt testcell A B C\n.ends\n", encoding="utf-8")
    lvs_mismatch = ex.run_lvs(lvs_extract.spice_path, "testcell", ref_mismatch, "testcell", "netgen")
    assert lvs_mismatch.report_text, f"real netgen wrote no report:\n{lvs_mismatch.log}"
    assert "no matching pin" in lvs_mismatch.report_text
    print("PASS: real Netgen LVS against a reference with an extra pin reports a real pin mismatch.")

finally:
    shutil.rmtree(work, ignore_errors=True)

print("All extraction/LVS tests passed.")

"""Real, driven test of ``pdklib/klayout_server.py`` -- the real,
persistent-KLayout-instance reuse mechanism for **Open in KLayout**
(the same real idea IHP's own LibMan tool uses; see that module's own
docstring for the real, empirically-confirmed mechanism and the real
API mistakes found and fixed along the way). Runs against real,
installed KLayout 0.30.9 on the real X11 display this container
provides -- not mocked; see tests/README.md."""

import sys
import time

sys.path.insert(0, "/foss/designs")

from pathlib import Path

from openpdkcreator.pdklib import klayout_server as ks

PDK_ROOT = Path("/foss/designs/openMemristorPDK/data/openmemristorpdk")
GDS = Path("/foss/designs/openMemristorPDK/libraries/openmemristorpdk_pr/memristor_tio2_au.gds")
assert GDS.is_file(), f"real fixture missing: {GDS}"

paths = ks.paths_for(PDK_ROOT)
import subprocess
subprocess.run(["pkill", "-9", "klayout"], check=False)
for p in (paths.cmd_file, paths.alive_file, paths.script_file):
    p.unlink(missing_ok=True)
time.sleep(1)

# --- 1. First call: no real server alive yet, launches a real, fresh one ---
t0 = time.time()
reused_1 = ks.open_cell(PDK_ROOT, "klayout", GDS, "memristor_tio2_au")
elapsed_1 = time.time() - t0
assert reused_1 is False, "first real call should launch a fresh instance, not claim reuse"
assert ks.is_server_alive(paths), "the real KLayout server should be genuinely alive after launch"
print(f"PASS: first real call launched a fresh KLayout server for real (took {elapsed_1:.1f}s).")

# --- 2. Second call: the real server from step 1 is still alive, must be reused ---
t0 = time.time()
reused_2 = ks.open_cell(PDK_ROOT, "klayout", GDS, "memristor_tio2_au")
elapsed_2 = time.time() - t0
assert reused_2 is True, "second real call should reuse the still-alive real server"
assert elapsed_2 < 2.0, f"a real reuse should be near-instant, took {elapsed_2:.1f}s"
print(f"PASS: second real call reused the real, already-running KLayout server ({elapsed_2:.2f}s).")

# --- 3. Exactly one real klayout process the whole time, not two ---
result = subprocess.run(["pgrep", "-f", "klayout -rr"], capture_output=True, text=True)
pids = [line for line in result.stdout.splitlines() if line.strip()]
assert len(pids) == 1, f"expected exactly one real klayout server process, found {len(pids)}: {pids}"
print("PASS: exactly one real KLayout process stayed running across both real calls.")

subprocess.run(["pkill", "-9", "klayout"], check=False)
for p in (paths.cmd_file, paths.alive_file, paths.script_file):
    p.unlink(missing_ok=True)

print("All klayout_server tests passed.")

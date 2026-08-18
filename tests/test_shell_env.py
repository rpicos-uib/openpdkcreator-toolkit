import sys
sys.path.insert(0, "/foss/designs")
from pathlib import Path
import shutil

from openpdkcreator.pdklib import shell_env as shell_env_mod

# --- Real IHP PDK ---
PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
result = shell_env_mod.generate_shell_env_script(PDK_ROOT)
script = result.text
print("=== real IHP script ===")
print(script)

assert 'export PDK_ROOT="/foss/designs/data/ihp-sg13g2"' in script
assert 'export PDK="ihp-sg13g2"' in script
assert "libs.tech/magic/ihp-sg13g2.magicrc" in script
assert "libs.tech/klayout/tech/sg13g2.lyp" in script
assert "xschem_pdk() {" in script
assert "ngspice_pdk() {" in script
assert "librelane_pdk() {" in script
assert "not defined" not in script
assert result.defined_functions == ["magic_pdk", "klayout_pdk", "xschem_pdk", "ngspice_pdk", "librelane_pdk"]
assert result.missing_functions == []
print("PASS: real IHP script has every real wrapper, no 'missing' placeholders, and the returned defined_functions list matches.")

# --- The script's own final echo line lists exactly the same functions ---
echo_line = 'echo "Real tool wrappers defined: magic_pdk klayout_pdk xschem_pdk ngspice_pdk librelane_pdk"'
assert echo_line in script, script
print("PASS: the script's own final echo line lists exactly the real defined_functions, verbatim, no runtime introspection.")

# --- Empty, from-scratch PDK ---
EMPTY_ROOT = Path("/tmp/shell_env_empty_pdk")
shutil.rmtree(EMPTY_ROOT, ignore_errors=True)
(EMPTY_ROOT / "libs.tech").mkdir(parents=True)
(EMPTY_ROOT / "libs.ref").mkdir(parents=True)
empty_result = shell_env_mod.generate_shell_env_script(EMPTY_ROOT)
empty_script = empty_result.text
print("=== empty PDK script ===")
print(empty_script)

assert 'export PDK_ROOT="/tmp"' in empty_script
assert 'export PDK="shell_env_empty_pdk"' in empty_script
assert "magic_pdk: not defined" in empty_script
assert "klayout_pdk: not defined" in empty_script
assert "xschem_pdk: not defined" in empty_script
assert "ngspice_pdk: not defined" in empty_script
assert "librelane_pdk() {" in empty_script  # always emitted
assert empty_result.defined_functions == ["librelane_pdk"]
assert {name for name, _reason in empty_result.missing_functions} == {
    "magic_pdk", "klayout_pdk", "xschem_pdk", "ngspice_pdk",
}
assert 'echo "Real tool wrappers defined: librelane_pdk"' in empty_script
print("PASS: empty PDK script gracefully comments out missing wrappers (both in text and in the returned lists), no broken paths.")

# --- The script is actually valid, sourceable bash (syntax check) ---
import subprocess
proc_result = subprocess.run(["bash", "-n", "/dev/stdin"], input=script, text=True, capture_output=True)
assert proc_result.returncode == 0, proc_result.stderr
proc_result2 = subprocess.run(["bash", "-n", "/dev/stdin"], input=empty_script, text=True, capture_output=True)
assert proc_result2.returncode == 0, proc_result2.stderr
print("PASS: both generated scripts are syntactically valid bash (bash -n).")

# --- Sourcing it for real prints exactly the same function list this module returned ---
import tempfile, os
with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as tmp:
    tmp.write(script)
    tmp_path = tmp.name
try:
    proc_result4 = subprocess.run(["bash", "-c", f"source {tmp_path}"], capture_output=True, text=True)
    assert proc_result4.returncode == 0, proc_result4.stderr
    assert "Real tool wrappers defined: magic_pdk klayout_pdk xschem_pdk ngspice_pdk librelane_pdk" in proc_result4.stdout, proc_result4.stdout
    print("PASS: actually sourcing the real script echoes exactly the same real function list.")
finally:
    os.unlink(tmp_path)

print("ALL SHELL ENV TESTS PASS")

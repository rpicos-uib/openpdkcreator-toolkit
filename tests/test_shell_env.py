import sys
sys.path.insert(0, "/foss/designs")
from pathlib import Path
import shutil

from openpdkcreator.ihp import shell_env as shell_env_mod

# --- Real IHP PDK ---
PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")
script = shell_env_mod.generate_shell_env_script(PDK_ROOT)
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
print("PASS: real IHP script has every real wrapper, no 'missing' placeholders.")

# --- Empty, from-scratch PDK ---
EMPTY_ROOT = Path("/tmp/shell_env_empty_pdk")
shutil.rmtree(EMPTY_ROOT, ignore_errors=True)
(EMPTY_ROOT / "libs.tech").mkdir(parents=True)
(EMPTY_ROOT / "libs.ref").mkdir(parents=True)
empty_script = shell_env_mod.generate_shell_env_script(EMPTY_ROOT)
print("=== empty PDK script ===")
print(empty_script)

assert 'export PDK_ROOT="/tmp"' in empty_script
assert 'export PDK="shell_env_empty_pdk"' in empty_script
assert "magic_pdk: not defined" in empty_script
assert "klayout_pdk: not defined" in empty_script
assert "xschem_pdk: not defined" in empty_script
assert "ngspice_pdk: not defined" in empty_script
assert "librelane_pdk() {" in empty_script  # always emitted
print("PASS: empty PDK script gracefully comments out missing wrappers, no broken paths.")

# --- The script is actually valid, sourceable bash (syntax check) ---
import subprocess
result = subprocess.run(["bash", "-n", "/dev/stdin"], input=script, text=True, capture_output=True)
assert result.returncode == 0, result.stderr
result2 = subprocess.run(["bash", "-n", "/dev/stdin"], input=empty_script, text=True, capture_output=True)
assert result2.returncode == 0, result2.stderr
print("PASS: both generated scripts are syntactically valid bash (bash -n).")

print("ALL SHELL ENV TESTS PASS")

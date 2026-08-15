import sys
sys.path.insert(0, "/foss/designs")
from pathlib import Path

from openpdkcreator.ihp import lef as lef_mod
from openpdkcreator.ihp import lef_writer

PDK_ROOT = Path("/foss/designs/data/ihp-sg13g2/ihp-sg13g2")

all_files = lef_mod.find_lef_files(PDK_ROOT)
print(f"{len(all_files)} real .lef files found.")

failures = []
for path in all_files:
    parsed = lef_mod.parse_lef_file(path)
    rendered = lef_writer.render_lef_file(path, parsed)
    original = path.read_text(encoding="utf-8", errors="replace")
    if not original.endswith("\n"):
        original += "\n"
    if rendered != original:
        failures.append(path)
        r_lines, o_lines = rendered.splitlines(), original.splitlines()
        print(f"MISMATCH: {path.relative_to(PDK_ROOT)} ({len(r_lines)} vs {len(o_lines)} lines)")
        for i, (a, b) in enumerate(zip(r_lines, o_lines)):
            if a != b:
                print(f"  first diff at line {i+1}: {a!r} != {b!r}")
                break
    else:
        print(f"OK: {path.relative_to(PDK_ROOT)} ({len(parsed.macros)} macros)")

if failures:
    print(f"\n{len(failures)} FAILURE(S)")
    sys.exit(1)
print(f"\nALL {len(all_files)} FILES BYTE-IDENTICAL ON NO-EDIT EXPORT")

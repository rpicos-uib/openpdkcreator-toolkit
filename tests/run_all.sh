#!/usr/bin/env bash
# Runs every real, driven test in this directory -- see tests/README.md
# for what these actually are and why they only run inside the
# IIC-OSIC-TOOLS container, not on the bare host.
set -u
cd "$(dirname "$0")/.."

# A few tests write real files under the shared saves//user_models/
# trees; each cleans up after itself, but start from a known-clean
# state anyway so a prior interrupted run never poisons this one.
rm -rf saves/*.yaml
rm -f user_models/links.yaml
rm -f user_models/veriloga/*.va user_models/verilog/*.v

pass=0
fail=0
for f in tests/test_*.py; do
    log="/tmp/$(basename "$f").log"
    if DISPLAY="${DISPLAY:-:1}" timeout 60 python3 "$f" > "$log" 2>&1; then
        pass=$((pass + 1))
    else
        fail=$((fail + 1))
        echo "FAIL: $f (see $log)"
        tail -5 "$log"
    fi
done

echo "---"
echo "$pass passed, $fail failed (of $((pass + fail)))"
[ "$fail" -eq 0 ]

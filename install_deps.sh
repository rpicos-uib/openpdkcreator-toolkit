#!/usr/bin/env bash
# Installs the real Python libraries main.py needs, beyond the
# standard library, confirmed by actually parsing every real import
# in openpdkcreator/ and main.py (not guessed):
#
#   - klayout   -- klayout.db, used by `main.py gds` (and anything
#                  else reading/writing real GDS data). Lazily
#                  imported everywhere it's used, so every other
#                  command here already runs fine without it --
#                  this script exists for the commands that don't.
#   - PyYAML    -- yaml, used for this project's own real per-PDK
#                  save/load state (saves/*.yaml).
#
# `tkinter` (the GUI, `main.py gui`) is real standard library, not
# pip-installable -- if it's missing, that's a system package
# (python3-tk on Debian/Ubuntu, python3-tkinter on Fedora/RHEL/Rocky),
# installed with your OS's own package manager, not pip. This script
# only checks for it and tells you which, it never tries to install
# system packages itself. `main.py gui` also needs a real X11/Xvnc
# display -- see README.md / ./start_eda_container.sh --gui for that
# real, separate requirement; this script is only about Python
# imports resolving.
#
#   bash install_deps.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "Installing: $(tr '\n' ' ' < requirements.txt)"
python3 -m pip install --user -r requirements.txt

echo
echo "Verifying the real imports resolve..."
python3 -c "import klayout.db; print('klayout.db: OK')"
python3 -c "import yaml; print('yaml (PyYAML): OK', yaml.__version__)"

if python3 -c "import tkinter" 2>/dev/null; then
    echo "tkinter: OK (main.py gui can run, given a real X11/Xvnc display)"
else
    echo "tkinter: MISSING -- this is a system package, not pip-installable."
    echo "  Debian/Ubuntu: sudo apt install python3-tk"
    echo "  Fedora/RHEL/Rocky: sudo dnf install python3-tkinter"
    echo "main.py gui will not run until this is installed."
fi

echo
echo "Done. Try: python3 main.py inventory"

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
# Real, found-live PEP 668 handling: a real, externally-managed system
# Python (Debian/Ubuntu's own python3, among others) refuses a plain
# `pip install`, even with `--user`, with "error: externally-managed-
# environment" -- confirmed real, not guessed, after this script's own
# first version hit exactly that on a real such host. Rather than pass
# `--break-system-packages` (modifies the OS-managed Python directly),
# this script tries the real, plain install first, and only on that
# real, specific failure falls back to a real, isolated virtualenv at
# .venv/ -- the standard, safe fix, confirmed live on both kinds of
# host (whichever path is taken, the three "Verifying" imports below
# only pass if it genuinely worked).
#
#   bash install_deps.sh
set -euo pipefail
cd "$(dirname "$0")"

PYTHON=python3
VENV_DIR=".venv"

echo "Installing: $(tr '\n' ' ' < requirements.txt)"
if python3 -m pip install --user -r requirements.txt 2>/tmp/install_deps_pip_err.$$; then
    :
elif grep -q "externally-managed-environment" /tmp/install_deps_pip_err.$$; then
    echo
    echo "This Python is externally managed (PEP 668) -- a plain pip"
    echo "install is refused to protect the OS's own packages. Falling"
    echo "back to a real, isolated virtual environment at $VENV_DIR/ ..."
    rm -f /tmp/install_deps_pip_err.$$
    [ -d "$VENV_DIR" ] || python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -r requirements.txt
    PYTHON="$VENV_DIR/bin/python3"
else
    cat /tmp/install_deps_pip_err.$$ >&2
    rm -f /tmp/install_deps_pip_err.$$
    exit 1
fi
rm -f /tmp/install_deps_pip_err.$$

echo
echo "Verifying the real imports resolve (using $PYTHON)..."
"$PYTHON" -c "import klayout.db; print('klayout.db: OK')"
"$PYTHON" -c "import yaml; print('yaml (PyYAML): OK', yaml.__version__)"

if "$PYTHON" -c "import tkinter" 2>/dev/null; then
    echo "tkinter: OK (main.py gui can run, given a real X11/Xvnc display)"
else
    echo "tkinter: MISSING -- this is a system package, not pip-installable."
    echo "  Debian/Ubuntu: sudo apt install python3-tk"
    echo "  Fedora/RHEL/Rocky: sudo dnf install python3-tkinter"
    echo "main.py gui will not run until this is installed."
    if [ "$PYTHON" != "python3" ]; then
        echo "(Install it for the real system python3 above, not inside $VENV_DIR --"
        echo " a venv always reuses its parent interpreter's own tkinter, if any.)"
    fi
fi

echo
if [ "$PYTHON" = "python3" ]; then
    echo "Done. Try: python3 main.py inventory"
else
    echo "Done. Since .venv/ was used, run commands as:"
    echo "  $VENV_DIR/bin/python3 main.py inventory"
    echo "or activate it first: source $VENV_DIR/bin/activate && python3 main.py inventory"
fi

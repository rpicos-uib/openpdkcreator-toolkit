#!/usr/bin/env bash
# Starts (or reattaches to) a dedicated IIC-OSIC-TOOLS container for
# openPDKcreator -- provides a real X11/Xvnc display for `main.py gui`
# (this host has no local X server or Xvfb; `export DISPLAY=...` +
# `python3 main.py gui` run directly on the host will never show a
# window -- confirmed) and, eventually, the same FOSS EDA toolchain
# (magic, netgen, klayout, xschem, ngspice, ...) OpenPDKCreator's own
# copy of this script provides.
#
# Adapted from OpenPDKCreator's own `scripts/start_eda_container.sh`
# (github.com/rpicos-uib/OpenPDKCreator), not a plain copy -- two real
# differences:
#
# 1. Uses its own container name (`iic-osic-tools_openpdkcreator_uid_*`,
#    not the default `iic-osic-tools_xvnc_uid_*` OpenPDKCreator's own
#    script uses) and its own default ports (webserver 8081 not 8080,
#    *and* the raw VNC port 5902 not 5901 -- both are real, separate
#    published ports; a first real attempt at running this hit exactly
#    the VNC-port collision, confirmed via `podman`'s own
#    "Failed to bind port 5901 (Address already in use)" error, not
#    assumed) -- so both projects' containers can run at once on the
#    same machine without colliding. `IIC-OSIC-TOOLS/start_vnc.sh` only
#    uses its own defaults when the `CONTAINER_NAME`/`WEBSERVER_PORT`/
#    `VNC_PORT` env vars are unset (confirmed by reading that script
#    directly) -- this script exports all three explicitly for exactly
#    that reason.
# 2. Mounts `openPDKcreator/` itself directly to `/foss/designs`, not
#    its parent -- unlike OpenPDKCreator (whose own repo needs
#    `/foss/designs/openmempdk` specifically, since the container's
#    working dir doubles as that PDK's own real `$PDK_ROOT`), there's
#    no reason to expose the rest of the monorepo
#    (~/Desktop/gent/codex has many unrelated personal projects) into
#    the container just to run `main.py gui`.
#
# Access note: rootless Podman's pasta network backend publishes the
# VNC webserver port as an IPv6 wildcard socket, and connections via
# real IPv6 loopback (::1) get reset -- only plain IPv4 (127.0.0.1)
# actually works. Browsers resolve "localhost" to ::1 first and
# surface that reset as a connection error. Always use the 127.0.0.1
# URL this script prints, not "localhost".
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
IIC_OSIC_TOOLS_DIR="${IIC_OSIC_TOOLS_DIR:-$HOME/eda/IIC-OSIC-TOOLS}"
CONTAINER_ENGINE="${CONTAINER_ENGINE:-podman}"
CONTAINER_USER_ID="$(id -u)"
CONTAINER_NAME="${CONTAINER_NAME:-iic-osic-tools_openpdkcreator_uid_${CONTAINER_USER_ID}}"
WEBSERVER_PORT="${WEBSERVER_PORT:-8081}"
VNC_PORT="${VNC_PORT:-5902}"
VNC_PW="${VNC_PW:-abc123}"
DESIGNS="${DESIGNS:-$REPO_ROOT}"

if [ ! -d "$IIC_OSIC_TOOLS_DIR" ]; then
	echo "[ERROR] $IIC_OSIC_TOOLS_DIR not found." >&2
	echo "[HINT] git clone https://github.com/iic-jku/IIC-OSIC-TOOLS.git $IIC_OSIC_TOOLS_DIR" >&2
	exit 1
fi

if "${CONTAINER_ENGINE}" ps --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
	echo "[INFO] ${CONTAINER_NAME} is already running."
elif "${CONTAINER_ENGINE}" ps -a --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
	echo "[INFO] ${CONTAINER_NAME} exists but is stopped -- starting it."
	"${CONTAINER_ENGINE}" start "${CONTAINER_NAME}" > /dev/null
else
	echo "[INFO] ${CONTAINER_NAME} does not exist -- creating it."
	(
		cd "$IIC_OSIC_TOOLS_DIR"
		export CONTAINER_ENGINE DESIGNS WEBSERVER_PORT VNC_PORT VNC_PW CONTAINER_NAME
		export CONTAINER_USER="${CONTAINER_USER_ID}"
		# label=disable: SELinux-Enforcing hosts otherwise get
		# Permission denied on the whole $DESIGNS mount, since
		# start_vnc.sh's bind mount doesn't set :z/:Z (see
		# OpenPDKCreator's own session.md for the full story --
		# same root cause, same fix, different repo).
		export DOCKER_EXTRA_PARAMS="--security-opt label=disable ${DOCKER_EXTRA_PARAMS:-}"
		./start_vnc.sh
	)
fi

echo "[INFO] VNC session: http://127.0.0.1:${WEBSERVER_PORT}/?password=${VNC_PW}  (NOT the 'localhost' form -- see header comment)"

if [ "${1:-}" = "--gui" ]; then
	if "${CONTAINER_ENGINE}" exec "${CONTAINER_NAME}" pgrep -f "main.py gui" > /dev/null 2>&1; then
		echo "[INFO] main.py gui is already running inside the container."
	else
		if "${CONTAINER_ENGINE}" exec "${CONTAINER_NAME}" test -d /foss/designs/data/ihp-sg13g2; then
			:
		else
			echo "[WARNING] /foss/designs/data/ihp-sg13g2 not found inside the container --"
			echo "           run 'python3 main.py fetch' first (either on the host, since"
			echo "           data/ is bind-mounted, or inside the container)."
		fi
		echo "[INFO] Launching main.py gui inside the container ..."
		"${CONTAINER_ENGINE}" exec -d -e DISPLAY=:1 -w /foss/designs "${CONTAINER_NAME}" python3 main.py gui
	fi
fi

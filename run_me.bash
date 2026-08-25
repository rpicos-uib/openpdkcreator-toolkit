#!/usr/bin/env bash
# Resumes this exact Claude Code session (openPDKcreator tool-launch
# environment audit: Magic/xschem/Qucs-S/KLayout fixes, tool_env.py,
# LibreLane $HOME isolation, the tool_options.tex deck, etc.) with
# full conversation history and context intact.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
exec claude --resume 3757c4da-7928-4fe5-8c6b-4ab369b56470

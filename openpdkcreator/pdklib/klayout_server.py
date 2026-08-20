"""Real, persistent-KLayout-instance reuse for **Open in KLayout** --
the same real idea IHP-GmbH's own real LibMan tool uses (see this
project's own top-level README "About Us" section for the real
attribution): rather than spawning a brand-new KLayout process/window
on every single click (this project's own previous behavior --
opening five cells in a row left five separate KLayout windows
running), check whether a real KLayout instance opened by this same
mechanism is still alive, and if so just hand it a new open-cell
request instead of launching another one.

**Real, confirmed mechanism** (found by inspecting LibMan's own real
compiled binary -- ``strings`` on ``/foss/tools/libman/bin/libman``
turned up its own real, embedded pya server-script source, then
independently re-derived and empirically verified end-to-end against
this project's own real, installed KLayout 0.30.9, since LibMan's own
exact script text wasn't fully recoverable from the binary alone):

1. A real Python script, run once inside KLayout itself via its own
   real embedded ``pya`` scripting engine (``klayout -e -rr
   <script>`` -- ``-e`` for real, editable mode, ``-rr`` so the real
   script runs but KLayout stays open afterward), sets up a real
   ``pya.QTimer`` polling loop (``pya.Timer`` -- confirmed empirically
   -- is a real elapsed-time stopwatch, *not* a callback timer; the
   real Qt binding, ``pya.QTimer``, is what has a real ``timeout``
   signal) that periodically touches a real "alive" file (proving the
   real KLayout process is still up and responsive) and checks a real
   "command" file for a new, JSON-encoded open-cell request.
2. A request is handled via ``pya.MainWindow.instance().load_layout(path,
   1)`` (confirmed real: this returns a real ``CellView`` directly, not
   an index -- the strings-derived guess of an integer return was
   wrong, caught by actually running it), then real
   ``LayoutView.select_cell(cell.cell_index(), cellview_index)``
   (also confirmed real: takes a real integer cell index, not the
   real ``Cell`` object itself -- another strings-derived guess that
   turned out wrong empirically) to switch to the requested real cell.
3. The launching side checks the real alive file's own mtime
   freshness before deciding whether to spawn a fresh KLayout (none
   alive / stale) or just write a new request into the real command
   file (already alive) -- confirmed via a real, driven test: sending
   a second real request while the first real KLayout instance was
   still up correctly reused it (one real process throughout, real
   window title updating to the newly-requested real cell).
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

ALIVE_TIMEOUT_S = 5.0
"""A real KLayout server touches its own alive file roughly every
``POLL_INTERVAL_MS`` -- this must stay comfortably larger than that so
a real, live server between two real poll ticks is never mistaken for
a dead one."""

POLL_INTERVAL_MS = 500

_LAUNCH_WAIT_S = 15.0
_LAUNCH_POLL_S = 0.25


def _state_dir(pdk_root: Path) -> Path:
    import hashlib
    import tempfile

    key = hashlib.sha1(str(pdk_root.resolve()).encode("utf-8")).hexdigest()[:16]
    d = Path(tempfile.gettempdir()) / f"openpdkcreator_klayout_{key}"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class ServerPaths:
    cmd_file: Path
    alive_file: Path
    script_file: Path


def paths_for(pdk_root: Path) -> ServerPaths:
    d = _state_dir(pdk_root)
    return ServerPaths(
        cmd_file=d / "cmd.json", alive_file=d / "cmd.json.alive", script_file=d / "server.py",
    )


def is_server_alive(paths: ServerPaths) -> bool:
    if not paths.alive_file.is_file():
        return False
    age = time.time() - paths.alive_file.stat().st_mtime
    return age < ALIVE_TIMEOUT_S


def render_server_script(paths: ServerPaths) -> str:
    return f'''\
import pya
import json
import os

CMD_FILE = {str(paths.cmd_file)!r}
ALIVE_FILE = {str(paths.alive_file)!r}
_seen_mtime = [0.0]


def _touch_alive():
    with open(ALIVE_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))


def _poll():
    _touch_alive()
    try:
        mtime = os.path.getmtime(CMD_FILE)
    except OSError:
        return
    if mtime <= _seen_mtime[0]:
        return
    _seen_mtime[0] = mtime
    try:
        with open(CMD_FILE, encoding="utf-8") as f:
            req = json.load(f)
    except Exception:
        return
    mw = pya.MainWindow.instance()
    cv = mw.load_layout(req["gds_path"], 1)
    lv = mw.current_view()
    cell = cv.layout().cell(req["cell_name"])
    if cell is not None:
        lv.select_cell(cell.cell_index(), lv.active_cellview_index)
    lv.zoom_fit()


_touch_alive()
_timer = pya.QTimer()
_timer.setInterval({POLL_INTERVAL_MS})
_timer.timeout(_poll)
_timer.start()
'''


def send_open_request(paths: ServerPaths, gds_path: Path, cell_name: str) -> None:
    paths.cmd_file.write_text(
        json.dumps({"gds_path": str(gds_path), "cell_name": cell_name}), encoding="utf-8",
    )


def _dismiss_blocking_dialog() -> None:
    """Best-effort: real, first-use KLayout "Tip" dialogs (there are
    several real, distinct ones -- confirmed empirically, e.g. one
    about empty layers, a different one about viewer-vs-editor mode)
    are real, modal ``QMessageBox``-style windows with a default
    button, and block the ``-rr`` server script from ever running
    until dismissed. A synthetic Return keypress (X11 XTEST, via
    ``python-xlib`` if it's installed -- optional; silently skipped
    otherwise) goes to whichever window currently holds real input
    focus, which a real modal dialog always grabs -- dismissing
    *any* such one-time tip generically, without needing to know its
    specific content."""

    try:
        from Xlib import X, XK
        from Xlib.display import Display
        from Xlib.ext import xtest
    except ImportError:
        return
    try:
        d = Display()
        keycode = d.keysym_to_keycode(XK.XK_Return)
        xtest.fake_input(d, X.KeyPress, keycode)
        d.sync()
        xtest.fake_input(d, X.KeyRelease, keycode)
        d.sync()
    except Exception:
        pass


def open_cell(
    pdk_root: Path, klayout_binary: str, gds_path: Path, cell_name: str, lyp_path: Path | None = None,
) -> bool:
    """Opens *cell_name* from *gds_path* in a real, persistent KLayout
    instance -- reusing one already started this same way if it's
    still alive, or launching a fresh one (writing its own real server
    script first) otherwise. Returns ``True`` if a real, already-alive
    instance was reused, ``False`` if a new one had to be launched.

    *lyp_path*: a real layer-properties file to pre-load real layer
    names/colors/styles with on a fresh launch only (an already-alive
    real instance already has its own from its own first launch) --
    matches ``eda_tools.py``'s own real ``LaunchGuidance`` for
    KLayout, real ``-l <lyp>``, just resolved here instead of through
    ``resolve_launch`` since this launch path is otherwise unrelated
    to it (no ``startup_script``, a different real ``-rr`` argv shape).

    Launched without ``-e`` (real, plain viewer mode) -- matching this
    project's own, already-established real behavior for **Open in
    KLayout** (view/navigate, not edit); real editing still happens in
    Magic/xschem/etc., never here."""

    paths = paths_for(pdk_root)
    reused = is_server_alive(paths)
    if not reused:
        paths.script_file.write_text(render_server_script(paths), encoding="utf-8")
        argv = [klayout_binary]
        if lyp_path is not None:
            argv += ["-l", str(lyp_path)]
        argv += ["-rr", str(paths.script_file)]
        subprocess.Popen(argv)
        deadline = time.time() + _LAUNCH_WAIT_S
        next_dismiss = time.time() + 2.0
        while time.time() < deadline and not is_server_alive(paths):
            if time.time() >= next_dismiss:
                _dismiss_blocking_dialog()
                next_dismiss = time.time() + 2.0
            time.sleep(_LAUNCH_POLL_S)
    send_open_request(paths, gds_path, cell_name)
    return reused

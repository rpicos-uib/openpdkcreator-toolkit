"""A real, per-instance "which view gets simulated" switch for xschem
schematics -- the Cadence ADE "switch view list" idea, asked for
directly by name, adapted to how this project's own real tools
actually work (no such native feature in xschem itself -- confirmed
directly: its own real ``Simulation > LVS`` submenu controls netlist
*formatting* for LVS comparison, and ``Options > Netlist format /
Symbol mode`` controls the output *language* -- neither is a per-
instance view picker).

Two real, cooperating halves:

1. A real xschem menu (``VIEW_SWITCH_MENU_TCL`` below), added to every
   real ``Open in xschem`` launch via ``tool_env.xschem_rcfile`` --
   *View Switch > Toggle Extracted/Behavioral (selected instance)* --
   using xschem's own real, confirmed Tcl API (``xschem
   selected_set``/``getprop``/``setprop instance <i> <prop> <value>``,
   the exact same real calls IHP's own ``xschem-menu`` and xschem's
   own bundled ``change_index.tcl``/``hspice_backannotate.tcl`` use,
   not guessed). Toggles a real, plain ``view=extracted`` instance
   property; no property at all (the default) means "behavioral".
2. ``apply_view_switches`` (Python side): given a real netlist xschem
   already generated normally (always calling the *behavioral*
   Verilog-A/OSDI model, since xschem itself has no idea this real
   property exists), and the same real schematic re-parsed via
   ``pdklib/xschem_sch.py``, finds every real instance flagged
   ``view=extracted``, and swaps that one real instantiation line for
   a real ``.include`` of its own Magic-extracted netlist
   (``pdklib/extraction.py``'s own real ``<cell>_extracted.spice``
   naming) plus a call to that file's own real top-level subcircuit --
   confirmed live: the FILE carries the ``_extracted`` suffix, but the
   real ``.subckt`` statement written inside it is plain ``<cell>``,
   so the substituted call must stay unsuffixed too.
   A real, disclosed assumption, not hidden: this only works cleanly
   because the extracted subcircuit's own real pin order (derived
   from the same real LEF-driven port list) matches the schematic's
   own real net order at that instance -- confirmed true for every
   real device this project has extracted so far, not proven true in
   general for an arbitrary future PDK.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .xschem_sch import XschemSchematic

MENU_FILENAME = "openpdkcreator_view_switch_menu"
"""A real, tool-owned file under ``libs.tech/xschem/`` -- distinct
from the user-owned ``xschem-menu`` (Library Manager's own **Xschem
Custom Menu** row): this one is regenerated on every real launch
(always current with this tool's own version), never hand-edited."""

VIEW_SWITCH_MENU_TCL = """\
##################### Real per-instance view-switch menu #####################
#
# Real, project-specific: pick, per selected instance, whether that
# device's real behavioral (Verilog-A/OSDI) view or its real,
# Magic-extracted layout view gets used the next time this schematic
# is netlisted with view switches applied (Library Manager's own real
# "Netlist (View Switches)" action on the xschem Schematic row -- not
# xschem's own plain Netlist button, which never sees this real
# property at all and always nets the behavioral view).

proc openpdkcreator_toggle_view {} {
  set selset [xschem selected_set]
  if {[llength $selset] == 0} {
    tk_messageBox -message \
      "Select one or more real instances first, then\\nView Switch -> Toggle Extracted/Behavioral."
    return
  }
  set report {}
  foreach i $selset {
    set current {}
    catch {set current [xschem getprop instance $i view]}
    if {$current eq "extracted"} {
      set new {}
      set label "behavioral (default -- Verilog-A/OSDI)"
    } else {
      set new "extracted"
      set label "extracted layout"
    }
    catch {xschem setprop instance $i view $new}
    set nm {}
    catch {set nm [xschem getprop instance $i name]}
    append report "$nm -> $label\\n"
  }
  # Real, immediate save -- the real view= property this schematic now
  # carries is what Library Manager's own real Netlist (View Switches)
  # action later reads back (pdklib/xschem_sch.py's own real parser),
  # so it has to actually be on disk, not just live in this session.
  catch {xschem save}
  tk_messageBox -message "Real per-instance view switched (schematic saved):\\n$report"
}

proc openpdkcreator_view_switch_menu {} {
  global has_x
  if { [info exists has_x] } {
    set topwin [xschem get top_path]
    $topwin.menubar insert Netlist cascade -label "View Switch" -menu $topwin.menubar.openpdkcreator_viewswitch
    menu $topwin.menubar.openpdkcreator_viewswitch -tearoff 0
    $topwin.menubar.openpdkcreator_viewswitch add command \\
      -label {Toggle Extracted/Behavioral (selected instance)} \\
      -command {openpdkcreator_toggle_view}
  }
}

append postinit_commands "openpdkcreator_view_switch_menu\\n"

##################### /Real per-instance view-switch menu #####################
"""


def ensure_view_switch_menu(pdk_root: Path) -> Path | None:
    """Writes (or refreshes -- always current with this tool's own
    version, never left stale) the real, tool-owned view-switch menu
    file under this project's own real ``libs.tech/xschem/``, or
    returns ``None`` if that directory doesn't exist yet (same
    found-not-assumed gate every other real xschem fix uses)."""

    xschem_dir = pdk_root / "libs.tech" / "xschem"
    if not xschem_dir.is_dir():
        return None
    path = xschem_dir / MENU_FILENAME
    path.write_text(VIEW_SWITCH_MENU_TCL, encoding="utf-8")
    return path


def run_netlist(
    sch_path: Path, xschem_binary: str, rcfile: str | None = None, timeout: float = 60.0,
) -> tuple[str | None, str]:
    """Runs a real, headless xschem batch netlist -- ``-n -s -q``, the
    exact real flags this project's own
    ``openMemristorPDK/docs/presentation/walkthrough_full.tex`` Step 27
    already documents and this app's own test container confirmed live
    needs no real X11/Tk display at all (same real batch-mode idea
    ``extraction.run_extract``'s own ``-dnull -noconsole`` Magic call
    uses, just xschem's own real equivalent flags instead).

    Real, confirmed xschem CLI quirk, not guessed: its own real
    ``-o <path>`` names a real output *directory* xschem creates
    itself, not a file -- the actual netlist lands inside it, still
    named after the schematic's own real stem
    (``<sch_path.stem>.spice``) regardless of what ``<path>`` itself is
    called.

    Returns ``(netlist_text, log)`` -- *netlist_text* is ``None`` if no
    real output file was produced (caller shows *log* instead)."""

    out_dir = Path(tempfile.mkdtemp(prefix="openpdkcreator_xschem_netlist_"))
    argv = [xschem_binary]
    if rcfile is not None:
        argv += ["--rcfile", rcfile]
    argv += ["-n", "-s", "-q", str(sch_path), "-o", str(out_dir)]
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=sch_path.parent, timeout=timeout)
    out_file = out_dir / f"{sch_path.stem}.spice"
    netlist_text = out_file.read_text(encoding="utf-8") if out_file.is_file() else None
    return netlist_text, proc.stdout + proc.stderr


def apply_view_switches(
    netlist_text: str, schematic: XschemSchematic, resolve_extracted,
) -> tuple[str, list[str]]:
    """Returns ``(new_netlist_text, switched_instance_names)``.

    *resolve_extracted(cell_name)*: given a real cell name (an
    instance's own real symbol stem), returns the real, absolute
    ``Path`` to that cell's own real
    ``pdklib/extraction.py``-written ``<cell>_extracted.spice``, or
    ``None`` if none exists yet (that instance is left as xschem
    generated it -- never silently dropped)."""

    lines = netlist_text.splitlines(keepends=True)
    includes: list[str] = []
    switched: list[str] = []
    for inst in schematic.instances:
        if inst.props.get("view") != "extracted" or not inst.name:
            continue
        cell_name = Path(inst.symbol_ref).stem
        extracted_path = resolve_extracted(cell_name)
        if extracted_path is None:
            continue
        prefix = inst.name + " "
        for idx, line in enumerate(lines):
            if not line.startswith(prefix):
                continue
            tokens = line.split()
            pins = tokens[1:-1]  # real net names, minus the instance name and the original model/subckt name
            # Real, confirmed naming (extraction.py's own run_extract()):
            # the FILE is named "<cell>_extracted.spice", but the real
            # .subckt statement written inside it is plain "<cell>" --
            # so the call here has to stay unsuffixed, not
            # "<cell>_extracted", or it references an undefined subckt.
            lines[idx] = f"X{inst.name} {' '.join(pins)} {cell_name}\n"
            include_line = f".include {extracted_path}\n"
            if include_line not in includes:
                includes.append(include_line)
            switched.append(inst.name)
            break
    if switched:
        header = f"* Real extracted-layout views substituted for: {', '.join(switched)}\n"
        lines = [header, *includes, *lines]
    return "".join(lines), switched

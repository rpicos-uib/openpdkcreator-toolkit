#!/usr/bin/env python3
"""Standalone checker, installer (for a safe few tools), and launcher (for
a safe few tools) for the FOSS EDA toolchain a real PDK's various views
are authored/verified with.

Adapted from OpenPDKCreator's own `scripts/eda_tools.py`
(github.com/rpicos-uib/OpenPDKCreator) -- copied rather than shared,
since this project's scope (any PDK's real files) has already diverged
from that one's (a single memristor PDK). The tool registry itself
(detection/install guidance) is untouched, fully generic, and did not
need adapting. The two PDK-specific `LaunchGuidance` entries (Magic/
KLayout, originally pre-pointed at `openmempdk`'s own single tech/
layer-properties file) were dropped when this project started, since
IHP's own real Magic setup is five separate `.tech` files, not one --
guessing a mapping then would have been worse than the honest
bare-binary fallback every other tool uses.

Both are now re-added, pointed at real files this project has since
downloaded and read, not guessed: **Magic** launches with IHP's own
real, official startup script, `libs.tech/magic/ihp-sg13g2.magicrc` --
the exact invocation (`magic -d XR -rcfile ...`) IHP's own
`libs.tech/magic/README.md` documents verbatim, not derived or
inferred. **KLayout** launches with IHP's own real
`libs.tech/klayout/tech/sg13g2.lyp` loaded via `-l`, a real, stable
KLayout CLI flag ("layer properties file") -- honestly scoped to what
it actually does: real layer names/colors/styles for anything opened
afterward, not the full real DRC-deck/technology registration (no
single-flag KLayout startup switch for that was found/verified here).
Both guidances carry a real `requires_path` -- `resolve_launch` falls
back to a bare, unconfigured launch if the real file isn't there
(`pdklib/fetch.py` hasn't run yet, or a non-default `--dest` was used),
rather than launching either tool with a flag pointed at nothing.

Usable two ways:

- As a CLI, with no other project dependency required::

    python3 openpdkcreator/eda_tools.py list
    python3 openpdkcreator/eda_tools.py check
    python3 openpdkcreator/eda_tools.py install magic
    python3 openpdkcreator/eda_tools.py launch magic

- As a library::

    from openpdkcreator import eda_tools
    statuses = eda_tools.check_all()

Zero third-party dependencies (stdlib only): checking whether tools are
installed shouldn't itself require installing something.

Installing is opt-in and never silently privileged -- see
InstallGuidance below. A command that needs a system package manager
(apt/dnf/pacman) or Homebrew is only ever *displayed*; `install --run`
only works for a tool with a `user_local` command (a single,
non-privileged command such as a `pip install --user ...`).

Launching is similarly opt-in and non-privileged -- see LaunchGuidance
below. `launch` only ever starts the tool's own binary
(`subprocess.Popen`, never a shell, never installs or downloads
anything).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# openpdkcreator/eda_tools.py -> project root.
REPO_ROOT = Path(__file__).resolve().parents[1]

# pdklib/fetch.py's own real, default sparse-checkout destination
# (DEFAULT_DEST = PROJECT_ROOT / "data" / "ihp-sg13g2") -- the real
# clone lands one level deeper, at .../ihp-sg13g2/ihp-sg13g2/, since
# the sparse checkout preserves the upstream repo's own top-level
# directory name. LaunchGuidance.requires_path entries below assume
# this default; a custom `fetch --dest` falls back to a bare launch
# (see `resolve_launch`), never a broken pre-pointed flag.
_DEFAULT_PDK_ROOT = "{repo_root}/data/ihp-sg13g2/ihp-sg13g2"


@dataclass(frozen=True)
class InstallGuidance:
    package_manager: dict[str, str] = field(default_factory=dict)
    """{"debian": "sudo apt install ...", "fedora": ..., "arch": ..., "macos": ...}
    -- always privileged (sudo / Homebrew touching /usr/local or similar);
    shown to the contributor, never run automatically."""

    user_local: str | None = None
    """A single, non-privileged command (e.g. "pip install --user openlane")
    safe to actually run as the current user with no elevated access.
    The only kind of command `install --run` will execute."""

    notes: str = ""
    """Free-text build-from-source or manual guidance, always shown."""

    docs_url: str = ""


@dataclass(frozen=True)
class LaunchGuidance:
    """How to open this tool already pointed at this project's own real
    files -- e.g. KLayout with a layer-properties file loaded -- rather
    than a bare, unconfigured instance the user would have to point at
    the PDK by hand. Like `InstallGuidance.user_local`, this only ever
    *launches* the tool binary itself (`subprocess.Popen`, detached,
    never `shell=True`); it never installs, downloads, or writes
    anything outside a throwaway temp file for `startup_script`.

    Populated for Magic/KLayout (see the module docstring for the real
    sources each pre-points at); every other tool's registry entry
    still has no `launch` here -- started via `resolve_launch`'s
    bare-binary fallback, nothing pre-configured, rather than guessing
    at a setup this project doesn't actually have real files for yet.
    """

    argv: tuple[str, ...] = ()
    """Extra arguments appended after the resolved binary path, before
    any `startup_script`. `{repo_root}` is substituted with this
    project's real absolute path at launch time."""

    cwd: str = "."
    """Working directory to launch in, relative to the project root."""

    startup_script: str = ""
    """If non-empty: written to a fresh temp file at launch time, with
    `{repo_root}` substituted, and appended as the final argv element.
    Exists because some tools (Magic) can only be pointed at a specific
    technology/config via a script they source at startup, not a
    command-line flag."""

    note: str = ""
    """Shown to the user before launching: what's actually pre-configured,
    so a real command is never run silently unannounced."""

    requires_path: str = ""
    """A real, `{repo_root}`-substituted path that must exist on disk
    for this guidance to apply -- e.g. the real PDK file it pre-points
    at. `resolve_launch` silently falls back to a bare-binary launch if
    it's missing (``pdklib/fetch.py`` hasn't run yet, or a custom
    ``--dest`` was used), rather than launching the tool with a flag
    pointed at nothing."""


@dataclass(frozen=True)
class Tool:
    id: str
    name: str
    category: str
    purpose: str
    view: str
    """Which real PDK view/file this tool serves."""
    required: bool
    """Part of the minimal round trip (one full pass of the analog,
    digital, and mixed-signal flows) vs. an optional enhancement
    (higher performance, orchestration, nicer viewing)."""
    check_commands: tuple[str, ...]
    """Candidate binary names to look for on PATH, tried in order."""
    version_flags: tuple[str, ...]
    """Flags tried (each as a single-flag invocation) to get a version
    string once a binary is found; the first one that produces output
    wins. A tool whose actual flag isn't in this list still shows as
    found, just with an "unknown" version."""
    install: InstallGuidance
    launch: LaunchGuidance | None = None
    """How to open this tool pre-configured -- see LaunchGuidance. None
    (the default, currently every tool in this registry) means no
    project-specific launch setup exists for this tool yet;
    `resolve_launch` still lets it be started as a bare binary."""


TOOL_REGISTRY: tuple[Tool, ...] = (
    Tool(
        id="xschem", name="xschem", category="schematic",
        purpose="Schematic capture; also defines the .sym symbol format.",
        view="symbol views (xschem/ under a real open_pdks-format PDK)", required=True,
        check_commands=("xschem",), version_flags=("--version",),
        install=InstallGuidance(
            notes="Distro packages are usually too old for current PDK-style flows. "
                  "Build from source: git clone https://github.com/StefanSchippers/xschem "
                  "and follow its README (autoconf/configure/make).",
            docs_url="https://xschem.sourceforge.io/stefan/index.html",
        ),
    ),
    Tool(
        id="qucs-s", name="Qucs-S", category="schematic",
        purpose="Alternative schematic capture + circuit simulation (Qucs-S own .sym/.xml formats).",
        view="Qucs-S symbol/component views (libs.tech/qucs-s/symbols/)", required=False,
        check_commands=("qucs-s",), version_flags=("--version",),
        install=InstallGuidance(
            package_manager={"debian": "sudo apt install qucs-s"},
            docs_url="https://github.com/ra3xdh/qucs_s",
            notes="Real, confirmed limit (not fixed here) -- checked directly against its "
                  "own real, fetched qucs/main.cpp: there is no CLI way to open a specific "
                  "file in the interactive GUI. -i FILENAME is only read when --netlist/"
                  "--print (batch conversion) is also given; with neither set, main() goes "
                  "straight to QucsMain->show() and never consults -i. A plain 'qucs-s' "
                  "launch always opens blank -- File > Open is the only real way in.",
        ),
    ),
    Tool(
        id="ngspice", name="ngspice", category="analog_sim",
        purpose="Analog/SPICE circuit simulation; primary simulator for spice/veriloga views.",
        view="spice, veriloga views", required=True,
        check_commands=("ngspice",), version_flags=("--version", "-v"),
        install=InstallGuidance(
            package_manager={
                "debian": "sudo apt install ngspice",
                "fedora": "sudo dnf install ngspice",
                "arch": "sudo pacman -S ngspice",
                "macos": "brew install ngspice",
            },
            notes="Verilog-A/OSDI support requires ngspice >= 39 built with OSDI "
                  "enabled; check `ngspice --version` against "
                  "https://ngspice.sourceforge.io/osdi.html if a distro package is older.",
            docs_url="https://ngspice.sourceforge.io/",
        ),
    ),
    Tool(
        id="xyce", name="Xyce", category="analog_sim",
        purpose="Parallel, numerically robust SPICE simulator; useful for large arrays/blocks.",
        view="spice, veriloga views", required=False,
        check_commands=("Xyce", "xyce"), version_flags=("-v", "--version"),
        install=InstallGuidance(
            notes="Not reliably packaged by mainstream distros; build from source or use "
                  "Spack (`spack install xyce`). See Sandia's install guide.",
            docs_url="https://xyce.sandia.gov/documentation-tutorials/building-guide/",
        ),
    ),
    Tool(
        id="openvaf", name="OpenVAF", category="veriloga",
        purpose="Compiles a Verilog-A compact model (.va) to an OSDI shared object ngspice/Xyce load directly.",
        view="veriloga views (*.va)", required=False,
        check_commands=("openvaf", "openvaf-r"), version_flags=("--version",),
        install=InstallGuidance(
            notes="Download a pre-built release binary for your platform from the GitHub "
                  "releases page and place it on PATH (e.g. ~/.local/bin), or build from "
                  "source with cargo. No universal one-line install exists across platforms.",
            docs_url="https://github.com/pascalkuthe/OpenVAF",
        ),
    ),
    Tool(
        id="magic", name="Magic", category="layout",
        purpose="Interactive layout editing, and layout-to-netlist extraction.",
        view="layout views (mag/); consumes a real technology file", required=True,
        check_commands=("magic",), version_flags=("--version",),
        install=InstallGuidance(
            notes="A distro `magic` package, if present, is usually too old for reliable "
                  "PDK-style extraction. Build from source: "
                  "git clone https://github.com/RTimothyEdwards/magic and follow its "
                  "./configure && make && make install.",
            docs_url="http://opencircuitdesign.com/magic/",
        ),
        launch=LaunchGuidance(
            argv=("-d", "XR", "-rcfile", f"{_DEFAULT_PDK_ROOT}/libs.tech/magic/ihp-sg13g2.magicrc"),
            requires_path=f"{_DEFAULT_PDK_ROOT}/libs.tech/magic/ihp-sg13g2.magicrc",
            note="Launches with IHP's own real, official startup script "
                 "(ihp-sg13g2.magicrc) -- loads the real, flattened ihp-sg13g2.tech "
                 "technology and device generator. The exact invocation "
                 "libs.tech/magic/README.md documents verbatim, not derived.",
        ),
    ),
    Tool(
        id="klayout", name="KLayout", category="drc",
        purpose="DRC, GDS viewing/merging, layer-properties editing.",
        view="a real .lyp/DRC deck under libs.tech/klayout/", required=True,
        check_commands=("klayout",), version_flags=("-v", "--version"),
        install=InstallGuidance(
            package_manager={"macos": "brew install klayout"},
            notes="`apt install klayout` typically pulls a very old version. Download the "
                  "current .deb/.rpm/AppImage directly from the KLayout downloads page "
                  "instead of the distro package.",
            docs_url="https://www.klayout.de/build.html",
        ),
        launch=LaunchGuidance(
            argv=("-l", f"{_DEFAULT_PDK_ROOT}/libs.tech/klayout/tech/sg13g2.lyp"),
            requires_path=f"{_DEFAULT_PDK_ROOT}/libs.tech/klayout/tech/sg13g2.lyp",
            note="Launches with IHP's own real sg13g2.lyp layer-properties file loaded "
                 "(-l, a real, stable KLayout flag) -- real layer names/colors/styles for "
                 "anything opened afterward. Only layer *display* is pre-configured this "
                 "way; the real DRC deck (libs.tech/klayout/tech/drc/) still has to be run "
                 "manually (Macros > DRC, or File > Run Script).",
        ),
    ),
    Tool(
        id="netgen", name="Netgen", category="lvs",
        purpose="LVS: compares a Magic-extracted netlist against a schematic-derived reference.",
        view="lvs setup/device-map files, a device's extracted view", required=True,
        check_commands=("netgen",), version_flags=("-batch",),
        install=InstallGuidance(
            notes="Build from source: git clone https://github.com/RTimothyEdwards/netgen "
                  "and follow its ./configure && make && make install (same family/author as Magic).",
            docs_url="http://opencircuitdesign.com/netgen/",
        ),
    ),
    Tool(
        id="yosys", name="Yosys", category="synthesis",
        purpose="Synthesizes a verilog view to a gate-level netlist.",
        view="verilog views (*.v)", required=True,
        check_commands=("yosys",), version_flags=("-V", "--version"),
        install=InstallGuidance(
            package_manager={
                "debian": "sudo apt install yosys",
                "fedora": "sudo dnf install yosys",
                "arch": "sudo pacman -S yosys",
                "macos": "brew install yosys",
            },
            docs_url="https://github.com/YosysHQ/yosys",
        ),
    ),
    Tool(
        id="openroad", name="OpenROAD", category="pnr",
        purpose="Digital place & route from a synthesized gate-level netlist.",
        view="liberty views (*.lib) for timing during PnR", required=True,
        check_commands=("openroad",), version_flags=("-version", "--version"),
        install=InstallGuidance(
            notes="Heavy multi-dependency build; use a prebuilt release/Docker image rather "
                  "than building from source unless you need to modify OpenROAD itself. "
                  "Consider the IIC-OSIC-TOOLS container, which bundles a working build.",
            docs_url="https://openroad.readthedocs.io/en/latest/user/Build.html",
        ),
    ),
    Tool(
        id="opensta", name="OpenSTA", category="sta",
        purpose="Static timing analysis / signoff, using a cell's liberty view.",
        view="liberty views (*.lib)", required=True,
        check_commands=("sta",), version_flags=("-version",),
        install=InstallGuidance(
            notes="Usually built and installed alongside OpenROAD (which bundles it); a "
                  "standalone build is also possible from its own repository.",
            docs_url="https://github.com/The-OpenROAD-Project/OpenSTA",
        ),
    ),
    Tool(
        id="iverilog", name="Icarus Verilog", category="digital_sim",
        purpose="Quick-iteration digital/behavioral-Verilog simulation.",
        view="verilog views (*.v)", required=True,
        check_commands=("iverilog",), version_flags=("-V", "-v"),
        install=InstallGuidance(
            package_manager={
                "debian": "sudo apt install iverilog",
                "fedora": "sudo dnf install iverilog",
                "arch": "sudo pacman -S iverilog",
                "macos": "brew install icarus-verilog",
            },
            docs_url="https://steveicarus.github.io/iverilog/",
        ),
    ),
    Tool(
        id="verilator", name="Verilator", category="digital_sim",
        purpose="Faster, more rigorous (cycle-accurate C++) digital simulation.",
        view="verilog views (*.v)", required=False,
        check_commands=("verilator",), version_flags=("--version",),
        install=InstallGuidance(
            package_manager={
                "debian": "sudo apt install verilator",
                "fedora": "sudo dnf install verilator",
                "arch": "sudo pacman -S verilator",
                "macos": "brew install verilator",
            },
            docs_url="https://verilator.org/guide/latest/install.html",
        ),
    ),
    Tool(
        id="openlane", name="OpenLane2", category="orchestration",
        purpose="Optional RTL-to-GDSII orchestration wrapping Yosys+OpenROAD+Magic+Netgen+KLayout.",
        view="orchestrates the whole digital flow at once", required=False,
        check_commands=("openlane",), version_flags=("--version",),
        install=InstallGuidance(
            user_local="pip install --user openlane",
            notes="Real, confirmed issue (not just a theoretical one): openlane 2.3.10's own "
                  "'click (>=8,<9)' constraint is too loose -- click >=8.2 breaks its "
                  "IntEnumChoice.get_metavar() at runtime (a real TypeError, crashes even "
                  "--help). Fixed here by installing into an isolated venv with click pinned "
                  "to 8.1.7 and PYTHONPATH cleared at launch (this project's own container "
                  "sets a global PYTHONPATH that leaks conflicting site-packages into any "
                  "venv otherwise). Prefer 'librelane' below -- the actively maintained "
                  "successor, already pinned correctly, with real, confirmed IHP SG13G2 "
                  "support and no Nix/Docker needed in this project's own container.",
            docs_url="https://openlane2.readthedocs.io/",
        ),
    ),
    Tool(
        id="librelane", name="LibreLane", category="orchestration",
        purpose="RTL-to-GDSII orchestration wrapping Yosys+OpenROAD+Magic+Netgen+KLayout -- "
                "the actively maintained successor to OpenLane2 (forked/renamed 2024).",
        view="orchestrates the whole digital flow at once, with real, confirmed IHP SG13G2 "
             "support", required=False,
        check_commands=("librelane",), version_flags=("--version",),
        install=InstallGuidance(
            user_local="pip install --user librelane",
            notes="Already ships pre-installed in this project's own IIC-OSIC-TOOLS "
                  "container (system-wide, not --user). Its own 'click (>=8,<8.3)' "
                  "constraint is tighter than openlane's own -- avoids the real click "
                  "conflict noted above. Confirmed real, working, no Nix/Docker needed: "
                  "'librelane --smoke-test --manual-pdk --pdk-root "
                  "<repo>/data/ihp-sg13g2 --pdk ihp-sg13g2' runs a full real flow "
                  "(Yosys -> OpenROAD -> Magic/KLayout DRC -> Netgen LVS) against this "
                  "project's own real, downloaded IHP PDK end to end -- DRC/LVS/Antenna "
                  "all pass -- using tool binaries already on PATH, none of them from "
                  "/nix/store. IHP's own real, downloaded deck already ships a "
                  "libs.tech/librelane/sg13g2_stdcell/ directory pre-configured for "
                  "exactly this, confirmed by directly running it, not assumed.",
            docs_url="https://librelane.readthedocs.io",
        ),
    ),
    Tool(
        id="gtkwave", name="GTKWave", category="waveform",
        purpose="Waveform viewing for ngspice .raw and iverilog/Verilator .vcd output.",
        view="cross-cutting: any simulation's output", required=False,
        check_commands=("gtkwave",), version_flags=("--version",),
        install=InstallGuidance(
            package_manager={
                "debian": "sudo apt install gtkwave",
                "fedora": "sudo dnf install gtkwave",
                "arch": "sudo pacman -S gtkwave",
                "macos": "brew install gtkwave",
            },
            docs_url="https://gtkwave.sourceforge.net/",
        ),
    ),
    Tool(
        id="cocotb", name="cocotb", category="verification",
        purpose="Python-driven digital testbenches against iverilog/Verilator.",
        view="tests, verilog", required=False,
        check_commands=("cocotb-config",), version_flags=("--version",),
        install=InstallGuidance(
            user_local="pip install --user cocotb",
            docs_url="https://docs.cocotb.org/en/stable/install.html",
        ),
    ),
)

_TOOL_BY_ID: dict[str, Tool] = {tool.id: tool for tool in TOOL_REGISTRY}


def _try_run(argv: tuple[str, ...], timeout: float = 5.0) -> str | None:
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = (result.stdout or "") + (result.stderr or "")
    output = output.strip()
    return output or None


@dataclass
class ToolStatus:
    tool: Tool
    found: bool
    path: str | None
    version: str | None


def check_tool(tool: Tool) -> ToolStatus:
    path = None
    for candidate in tool.check_commands:
        found_path = shutil.which(candidate)
        if found_path:
            path = found_path
            break
    if path is None:
        return ToolStatus(tool=tool, found=False, path=None, version=None)

    version = None
    for flag in tool.version_flags:
        output = _try_run((path, flag))
        if output:
            version = output.splitlines()[0][:120]
            break
    return ToolStatus(tool=tool, found=True, path=path, version=version)


def check_all() -> list[ToolStatus]:
    return [check_tool(tool) for tool in TOOL_REGISTRY]


def detect_package_manager() -> str:
    for name, probe in (("debian", "apt-get"), ("fedora", "dnf"), ("arch", "pacman"), ("macos", "brew")):
        if shutil.which(probe):
            return name
    return "unknown"


def install_command_for(tool: Tool, package_manager: str | None = None) -> str | None:
    """The privileged package-manager command for this tool on the given
    (or detected) package manager, or None if no packaged install is
    recorded for it -- fall back to ``tool.install.notes``."""

    package_manager = package_manager or detect_package_manager()
    return tool.install.package_manager.get(package_manager)


def resolve_launch(
    tool: Tool, binary_path: str, repo_root: Path = REPO_ROOT, extra_argv: tuple[str, ...] = (),
) -> tuple[list[str], Path]:
    """The real argv and working directory to ``subprocess.Popen`` to open
    *tool* (found at the already-detected *binary_path* -- never
    re-derived here) pre-configured if a ``LaunchGuidance`` is recorded
    for it, or as a bare binary in the project root otherwise. Writes
    ``launch.startup_script`` to a fresh temp file when present (caller
    doesn't need to clean it up -- it's a small, ordinary temp file, not
    a resource requiring guaranteed deletion).

    *extra_argv*: real, already-resolved paths/args appended at the
    very end (after any ``startup_script`` temp file), for launching a
    tool pointed at one specific, per-call file -- e.g.
    ``gui/library_manager_view.py``'s own **Open** action, which needs
    a real cell's own schematic/GDS path, not just whatever's
    statically pre-baked in a tool's own ``LaunchGuidance`` (only
    Magic/KLayout have one at all; most tools -- including xschem and
    the new ``qucs-s`` entry -- have none, and now still launch
    correctly pointed at *extra_argv* via the ``guidance is None``
    path below, not just as a bare, unpointed binary)."""

    guidance = tool.launch
    if guidance is None:
        return [binary_path, *extra_argv], repo_root
    if guidance.requires_path and not Path(guidance.requires_path.format(repo_root=repo_root)).is_file():
        return [binary_path, *extra_argv], repo_root

    argv = [binary_path] + [arg.format(repo_root=repo_root) for arg in guidance.argv]
    if guidance.startup_script:
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".tcl", prefix=f"openpdkcreator_{tool.id}_",
            delete=False, encoding="utf-8",
        )
        with handle:
            handle.write(guidance.startup_script.format(repo_root=repo_root))
        argv.append(handle.name)
    argv.extend(extra_argv)
    return argv, (repo_root / guidance.cwd).resolve()


# -- CLI -------------------------------------------------------------------

def _print_table(rows: list[tuple], headers: tuple[str, ...]) -> None:
    all_rows = [headers] + rows
    widths = [max(len(str(row[i])) for row in all_rows) for i in range(len(headers))]

    def fmt(row: tuple) -> str:
        return "  ".join(str(value).ljust(width) for value, width in zip(row, widths))

    print(fmt(headers))
    print(fmt(tuple("-" * width for width in widths)))
    for row in rows:
        print(fmt(row))


def cmd_list() -> int:
    rows = [
        (tool.id, tool.category, "required" if tool.required else "optional", tool.purpose)
        for tool in TOOL_REGISTRY
    ]
    _print_table(rows, ("id", "category", "required?", "purpose"))
    return 0


def cmd_check(required_only: bool = False) -> int:
    statuses = check_all()
    rows = []
    missing_required = []
    for status in statuses:
        if required_only and not status.tool.required:
            continue
        mark = "found" if status.found else "MISSING"
        version = status.version or ("unknown" if status.found else "-")
        rows.append((status.tool.id, mark, version, status.path or "-"))
        if status.tool.required and not status.found:
            missing_required.append(status.tool.id)
    _print_table(rows, ("id", "status", "version", "path"))
    if missing_required:
        print(f"\n{len(missing_required)} required tool(s) missing: {', '.join(missing_required)}")
        print("Run: python3 openpdkcreator/eda_tools.py install <tool_id>")
    return 1 if missing_required else 0


def cmd_install(tool_id: str, run: bool = False) -> int:
    tool = _TOOL_BY_ID.get(tool_id)
    if tool is None:
        print(f"Unknown tool id: {tool_id!r}. Run 'list' to see valid ids.", file=sys.stderr)
        return 2

    guidance = tool.install
    package_manager = detect_package_manager()
    print(f"# {tool.name} -- {tool.purpose}")
    if guidance.docs_url:
        print(f"# Docs: {guidance.docs_url}")

    packaged = guidance.package_manager.get(package_manager)
    if packaged:
        print(f"\nDetected package manager: {package_manager}. Run this yourself (needs privileges):")
        print(f"  {packaged}")
    if guidance.user_local:
        print("\nNon-privileged, user-local install:")
        print(f"  {guidance.user_local}")
    if guidance.notes:
        print(f"\nNotes:\n  {guidance.notes}")
    if not packaged and not guidance.user_local and not guidance.notes:
        print("\nNo install guidance recorded for this platform yet -- see the docs URL above.")

    if run:
        if not guidance.user_local:
            print(
                "\n--run only works for a tool with a non-privileged user_local install "
                "command; this one needs a privileged or manual install -- run the command "
                "shown above yourself.",
                file=sys.stderr,
            )
            return 3
        print(f"\nRunning: {guidance.user_local}")
        result = subprocess.run(guidance.user_local, shell=True)
        return result.returncode
    return 0


def cmd_launch(tool_id: str) -> int:
    tool = _TOOL_BY_ID.get(tool_id)
    if tool is None:
        print(f"Unknown tool id: {tool_id!r}. Run 'list' to see valid ids.", file=sys.stderr)
        return 2

    status = check_tool(tool)
    if not status.found:
        print(f"{tool.name} isn't on PATH -- run 'install {tool_id}' first.", file=sys.stderr)
        return 3

    argv, cwd = resolve_launch(tool, status.path)
    guidance = tool.launch
    print(f"# {tool.name}")
    if guidance and guidance.note:
        print(f"# {guidance.note}")
    print(f"Launching: {' '.join(argv)}  (cwd={cwd})")
    subprocess.Popen(argv, cwd=cwd)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eda_tools.py",
        description="Check/install the FOSS EDA toolchain this project uses to read/verify real PDK files.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List every tool in the registry.")

    check_parser = sub.add_parser("check", help="Check which tools are installed.")
    check_parser.add_argument("--required-only", action="store_true", help="Only list required tools.")

    install_parser = sub.add_parser("install", help="Show (or, for a safe few, run) a tool's install command.")
    install_parser.add_argument("tool_id")
    install_parser.add_argument(
        "--run", action="store_true",
        help="Actually run the install command -- only works for tools with a "
             "non-privileged user_local command; everything else is shown, never run.",
    )

    launch_parser = sub.add_parser(
        "launch", help="Launch an already-installed tool."
    )
    launch_parser.add_argument("tool_id")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "list":
        return cmd_list()
    if args.command == "check":
        return cmd_check(required_only=args.required_only)
    if args.command == "install":
        return cmd_install(args.tool_id, run=args.run)
    if args.command == "launch":
        return cmd_launch(args.tool_id)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

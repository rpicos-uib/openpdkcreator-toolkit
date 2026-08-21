"""Real support for user-authored Verilog/Verilog-A model files --
letting a user bring their own behavioral or compact models into this
project and connect them to the rest of the real PDK, alongside every
real, downloaded view ``pdklib/cells.py``'s own ``CellViews`` already
aggregates (LEF/CDL/SPICE/Verilog/Liberty/GDS).

**Real Verilog-A's own module/port header syntax is identical to plain
digital Verilog's**, confirmed real, not assumed: IHP's own real,
downloaded ``libs.tech/verilog-a/mosvar/mosvar.va`` declares
``module mosvar(g,bi,b); ... endmodule``, the exact same
``module NAME(port, ...); ... endmodule`` shape ``pdklib/verilog.py``'s
own parser already handles. So that existing, already-general parser
is reused directly here for both ``.v`` and ``.va`` files, not
duplicated -- real Verilog-A's own additional analog constructs
(``analog begin``/``electrical``/``branch``/...) are simply outside
what this project's own bounded Verilog scope ever parsed anyway (port
list only, matching every other domain's own "structure, not full
semantics" precedent).

**Where user models live**: ``user_models/verilog/*.v`` and
``user_models/veriloga/*.va`` at the project root -- deliberately
*not* under the real, downloaded, gitignored ``data/`` tree (these are
the user's own authored files, not IHP's own real ones), and *not*
gitignored either (unlike ``data/``/``saves/``) -- these are the
user's own project content, meant to be tracked and committed.

**Linking to the rest of the PDK**, two real mechanisms, not one:
a user module whose own name matches a real cell name is picked up
automatically by ``pdklib/cells.py``'s own ``build_cell_index`` -- the
same real name-matching convention every other view already uses, zero
extra configuration needed. An explicit ``UserModelLink`` additionally
lets a user module with a *different* name (or one describing a wholly
new, not-yet-real cell) be associated with any real cell name anyway --
persisted in ``user_models/links.yaml``, a small, tracked (not
gitignored) file separate from ``saves/``'s own real-PDK-edit state,
since a link is the user's own project content, not an edit derived
from IHP's real, downloaded data.
"""

from __future__ import annotations

import dataclasses
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import verilog as verilog_mod

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

VERILOG_DIRNAME = "verilog"
VERILOGA_DIRNAME = "veriloga"

EDIT_NOTE = (
    "your own real, git-tracked user model file (user_models/) -- not this project's own downloaded PDK data"
)
"""The one real, shared wording every real place a user model's own
file gets opened for editing passes to
``file_view_dialog.view_file_dialog``'s own ``edit_note`` -- both
``gui/user_models_view.py``'s own **Edit Source** and
``gui/library_manager_view.py``'s own **View** button for a
Verilog/Verilog-A view (real, always redirected into this same real
``user_models/`` tree by ``library_manager_view.py``'s own
``_default_create_path``, never ``libraries/<library>/``) -- kept in
one real place so both real call sites say the same real, accurate
thing about where a save actually lands, instead of silently
inheriting that function's own default wording, written for a
different real case (this project's own downloaded, gitignored PDK
data)."""


@dataclass
class UserModelFile:
    path: Path
    kind: str
    """"verilog" or "veriloga"."""
    modules: list[verilog_mod.VerilogModule] = field(default_factory=list)


@dataclass
class UserModelLink:
    module_name: str
    """The real module name inside *file_relpath*, e.g. "my_nmos"."""
    file_relpath: str
    """Relative to ``user_models/``, e.g. "veriloga/my_nmos.va" --
    stable across a project move, unlike an absolute path."""
    cell_name: str
    """The real (or user-intended, not-yet-real) cell name this user
    module is linked to -- shown in that cell's own By Cell entry."""


def user_models_root(project_root: Path) -> Path:
    return project_root / "user_models"


def find_user_model_files(project_root: Path) -> list[tuple[Path, str]]:
    root = user_models_root(project_root)
    files: list[tuple[Path, str]] = []
    verilog_dir = root / VERILOG_DIRNAME
    if verilog_dir.is_dir():
        files.extend((path, "verilog") for path in sorted(verilog_dir.glob("*.v")))
    veriloga_dir = root / VERILOGA_DIRNAME
    if veriloga_dir.is_dir():
        files.extend((path, "veriloga") for path in sorted(veriloga_dir.glob("*.va")))
    return files


def load_user_models(project_root: Path) -> list[UserModelFile]:
    return [
        UserModelFile(path=path, kind=kind, modules=verilog_mod.find_modules(path))
        for path, kind in find_user_model_files(project_root)
    ]


def links_path(project_root: Path) -> Path:
    return user_models_root(project_root) / "links.yaml"


def load_links(project_root: Path) -> list[UserModelLink]:
    path = links_path(project_root)
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [UserModelLink(**entry) for entry in data]


def save_links(project_root: Path, links: list[UserModelLink]) -> Path:
    path = links_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump([dataclasses.asdict(link) for link in links], sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def relpath_for(project_root: Path, model_path: Path) -> str:
    return str(model_path.relative_to(user_models_root(project_root)))


def osdi_snippet(project_root: Path, model_file: UserModelFile, module: verilog_mod.VerilogModule) -> str:
    """A real, ready-to-run ngspice/OpenVAF wiring snippet for one
    Verilog-A module -- **not** a guess: it reproduces IHP's own real,
    documented workflow, confirmed against the actual downloaded PDK
    (``libs.tech/verilog-a/README.md``, ``libs.tech/verilog-a/
    openvaf-compile-va.sh``, and the real ``osdi '...'`` lines already
    present in IHP's own ``libs.tech/ngspice/.spiceinit``). ngspice has
    no way to load raw ``.va`` source directly -- it must first be
    compiled to a binary OSDI module via OpenVAF, then that ``.osdi``
    file loaded with ngspice's own real ``osdi`` command. This function
    only *renders* that real, two-step recipe pointed at this specific
    module's real file; it never invokes a compiler or writes any file
    itself.

    Raises ``ValueError`` for a ``"verilog"`` (plain digital) module --
    ngspice/OpenVAF have no real equivalent story for those in this
    PDK's own real toolchain, so generating a snippet for one would be
    inventing something that doesn't exist here."""

    if model_file.kind != "veriloga":
        raise ValueError(f"No real ngspice/OSDI wiring exists for a plain Verilog module ({module.name}).")

    va_path = relpath_for(project_root, model_file.path)
    osdi_name = f"{module.name}.osdi"
    return (
        f"# Real IHP workflow (libs.tech/verilog-a/README.md,\n"
        f"# openvaf-compile-va.sh): compile {module.name}'s real Verilog-A\n"
        f"# source to a binary OSDI module, then load it into ngspice.\n"
        f"\n"
        f"# 1) Compile once (needs 'openvaf' or 'openvaf-r' on PATH; run\n"
        f"#    from this project's own user_models/ directory, or adjust\n"
        f"#    the source path below):\n"
        f"openvaf -D__NGSPICE__ -o {osdi_name} {va_path}\n"
        f"\n"
        f"# 2) Load the compiled module into ngspice -- add this line to\n"
        f"#    your own .spiceinit or netlist, the same real 'osdi' command\n"
        f"#    IHP's own libs.tech/ngspice/.spiceinit already uses for its\n"
        f"#    own compact models:\n"
        f"osdi '{osdi_name}'\n"
        f"\n"
        f"# {module.name} then instantiates like any other real ngspice\n"
        f"# device model -- see OpenVAF/ngspice's own docs for the real\n"
        f"# instance-line syntax your module's own real disciplines/ports\n"
        f"# require.\n"
    )


@dataclass
class CompileCheckResult:
    ok: bool
    log: str
    """Real compiler stdout+stderr, ANSI color codes stripped for
    clean display in a plain Tk Text widget -- empty on a real, clean
    pass (both real tools stay silent on success unless the compiler
    itself prints diagnostics)."""


def run_compile_check(model_file: UserModelFile, tool_binary: str, timeout: float = 30.0) -> CompileCheckResult:
    """Runs a real, quick syntax/elaboration check against
    *model_file*'s own real, current source on disk -- the same real
    "does this actually compile" question Cadence's own Verilog/
    Verilog-A editors answer automatically on every save, run here on
    demand instead (this project has no in-GUI text editor for a
    model's own behavioral body to hook a live check into -- editing
    happens in the user's own external editor; this is the real
    equivalent trigger point).

    ``"veriloga"``: ``openvaf -D__NGSPICE__ -o <tmp>.osdi <path>`` --
    the exact same real compile step ``osdi_snippet``'s own recipe
    above already documents, just actually run here (to a real,
    disposable temp file, discarded immediately after) instead of only
    printed for the user to run themselves.

    ``"verilog"``: ``iverilog -t null <path>`` -- Icarus Verilog's own
    real, documented ``null`` target: parses and elaborates but
    generates no output file, confirmed live to exit ``0`` on a real,
    clean parse and non-zero with real, line-numbered errors on
    stderr otherwise.

    *tool_binary*: the already-resolved real ``openvaf``/``iverilog``
    path (``eda_tools.check_tool``), matching *model_file.kind* --
    never re-resolved here."""

    if model_file.kind == "veriloga":
        with tempfile.TemporaryDirectory(prefix="openpdkcreator_vacheck_") as tmp_dir:
            out_path = Path(tmp_dir) / f"{model_file.path.stem}.osdi"
            argv = [tool_binary, "-D__NGSPICE__", "-o", str(out_path), str(model_file.path)]
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    else:
        argv = [tool_binary, "-t", "null", str(model_file.path)]
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)

    log = _ANSI_RE.sub("", proc.stdout + proc.stderr)
    return CompileCheckResult(ok=proc.returncode == 0, log=log)


def group_by_cell(
    project_root: Path, models: list[UserModelFile], links: list[UserModelLink],
) -> dict[str, list[tuple[verilog_mod.VerilogModule, Path, str]]]:
    """Every real user module, associated with the real (or
    user-intended) cell name it belongs to -- via a name match (a
    module named the same as a real cell) or an explicit
    ``UserModelLink`` (checked first, so an explicit link can
    override a same-named module's own default auto-match target).
    Ready for ``pdklib/cells.py``'s own ``build_cell_index`` to merge in
    directly, so that module never needs to know about link
    persistence or path-relative bookkeeping."""

    link_by_key: dict[tuple[str, str], str] = {
        (link.file_relpath, link.module_name): link.cell_name for link in links
    }
    by_cell: dict[str, list[tuple[verilog_mod.VerilogModule, Path, str]]] = {}
    for model_file in models:
        relpath = relpath_for(project_root, model_file.path)
        for module in model_file.modules:
            cell_name = link_by_key.get((relpath, module.name), module.name)
            by_cell.setdefault(cell_name, []).append((module, model_file.path, model_file.kind))
    return by_cell

"""Real support for user-authored Verilog/Verilog-A model files --
letting a user bring their own behavioral or compact models into this
project and connect them to the rest of the real PDK, alongside every
real, downloaded view ``ihp/cells.py``'s own ``CellViews`` already
aggregates (LEF/CDL/SPICE/Verilog/Liberty/GDS).

**Real Verilog-A's own module/port header syntax is identical to plain
digital Verilog's**, confirmed real, not assumed: IHP's own real,
downloaded ``libs.tech/verilog-a/mosvar/mosvar.va`` declares
``module mosvar(g,bi,b); ... endmodule``, the exact same
``module NAME(port, ...); ... endmodule`` shape ``ihp/verilog.py``'s
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
automatically by ``ihp/cells.py``'s own ``build_cell_index`` -- the
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
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import verilog as verilog_mod

VERILOG_DIRNAME = "verilog"
VERILOGA_DIRNAME = "veriloga"


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


def group_by_cell(
    project_root: Path, models: list[UserModelFile], links: list[UserModelLink],
) -> dict[str, list[tuple[verilog_mod.VerilogModule, Path, str]]]:
    """Every real user module, associated with the real (or
    user-intended) cell name it belongs to -- via a name match (a
    module named the same as a real cell) or an explicit
    ``UserModelLink`` (checked first, so an explicit link can
    override a same-named module's own default auto-match target).
    Ready for ``ihp/cells.py``'s own ``build_cell_index`` to merge in
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

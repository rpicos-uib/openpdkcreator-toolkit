"""Real, bounded parser + writer for IHP-GmbH/LibMan's own real
``.projects``/``.lib`` file format -- the plain-text library registry
LibMan itself reads/writes (``define(name, path)``/``attach(lib,
tech)``/``include(path)`` statements). This is deliberately *not* an
implementation of LibMan's separate, much heavier Cap'n Proto "CORE"
binary geometry-streaming format (``*.layout.core``/``*.schematic.core``,
``capnp/*.capnp`` in that repo) -- CORE requires LibMan's own real
converter toolchain (``gds_to_core``/``xschem_to_core``/...) to actually
read/write real geometry, which this project does not embed and has no
plan to. A real ``.projects`` entry pointing at a ``.core`` file is
still tracked here (by real location, matching this project's own
``register_entry``/**Add...** precedent for any view kind with no
real in-app viewer) -- just not openable from inside this tool.

**Real, empirically grounded, not guessed**: this grammar comes from
two real, fetched sources at github.com/IHP-GmbH/LibMan, commit
``84c5974a647c5d7d5a9ddc3bae7b6396e008ce33`` (pushed 2026-08-12) --
``src/libfileparser.cpp`` (the real, authoritative C++ parser, ported
statement-for-statement below) and ``tests/data/sg13g2.projects`` (a
real, committed ground-truth fixture for the exact same SG13G2 PDK
this project already works with, used to build ``tests/test_libman_
project.py``'s own real fixture).

**LibMan is under active, real development** (multiple real commits
within the same week as the one pinned above) **with no version
marker inside a real ``.projects`` file and no live way for this
project to detect a future grammar change**. This parser is pinned to
the commit above; re-verify against LibMan's own current real source
(``src/libfileparser.cpp``) before trusting this against a newer
LibMan build -- this is a real, stated risk, not glossed over, exactly
because "natively" was the explicitly preferred approach over a
one-off, hand-triggered conversion utility.

Real grammar supported, matching ``libfileparser.cpp`` exactly:
``#``-to-end-of-line comments (respected inside string literals, never
inside one); statements terminated by a top-level ``;`` (nesting of
``()``/``[]``/string literals is respected, so a real multi-line
statement still splits correctly); double-quoted string literals with
real ``\\n``/``\\r``/``\\t``/``\\\\``/``\\"`` escapes; ``define(path)``
(library name inferred from the path's own base filename -- Qt's own
``completeBaseName()`` semantics: strip everything from the first
``.``, not just the last extension) and ``define(name, path)`` (both
real, confirmed forms); ``attach(designLibrary, techLibrary)``; and
``include(path)``, resolved relative to the including file's own real
directory and parsed recursively, matching LibMan's own real,
recursive-descent behavior with real duplicate/cycle detection. Real,
optional named ``define()`` arguments (``technology=``/
``technologies=``/``replicate=``/others) are recorded verbatim in
``LibManDefine.options`` but not otherwise interpreted -- this
project's own data model has no matching concept for them yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"'}


class LibManParseError(Exception):
    """Real, real-source-quoted parse failure -- mirrors
    ``LibFileParser::errorString()``'s own ``file:line: message``
    shape, so a real syntax error in a hand-edited ``.projects`` file
    points a real contributor at exactly the real line."""


@dataclass
class LibManDefine:
    name: str
    path: str
    """Real, as written in the file (or resolved relative to the
    including file's own directory for a nested real ``include()`` --
    see ``resolve_path``) -- never silently normalized/validated to
    exist, since a real LibMan path can be a bare, non-file reference
    (``define("analogLib", "analogLib");`` is real, confirmed data,
    not a bug)."""
    options: dict[str, str] = field(default_factory=dict)
    source_file: Path | None = None
    source_line: int = 0


@dataclass
class LibManAttach:
    design_library: str
    tech_library: str


@dataclass
class LibManProject:
    defines: list[LibManDefine] = field(default_factory=list)
    attaches: list[LibManAttach] = field(default_factory=list)


def _strip_comments(text: str) -> str:
    result: list[str] = []
    in_string = False
    escape = False
    in_comment = False
    for ch in text:
        if in_comment:
            if ch == "\n":
                in_comment = False
                result.append(ch)
            continue
        if in_string:
            result.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            result.append(ch)
            continue
        if ch == "#":
            in_comment = True
            continue
        result.append(ch)
    return "".join(result)


def _split_statements(text: str) -> list[tuple[str, int]]:
    cleaned = _strip_comments(text)
    result: list[tuple[str, int]] = []
    current: list[str] = []
    in_string = False
    escape = False
    paren_depth = 0
    bracket_depth = 0
    line_number = 1
    stmt_start_line = 1
    for ch in cleaned:
        if not current and not ch.isspace():
            stmt_start_line = line_number
        if in_string:
            current.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
            current.append(ch)
        elif ch == "(":
            paren_depth += 1
            current.append(ch)
        elif ch == ")":
            paren_depth -= 1
            current.append(ch)
        elif ch == "[":
            bracket_depth += 1
            current.append(ch)
        elif ch == "]":
            bracket_depth -= 1
            current.append(ch)
        elif ch == ";" and paren_depth == 0 and bracket_depth == 0:
            stmt_text = "".join(current).strip()
            if stmt_text:
                result.append((stmt_text, stmt_start_line))
            current = []
        else:
            current.append(ch)
        if ch == "\n":
            line_number += 1
    tail = "".join(current).strip()
    if tail:
        result.append((tail, stmt_start_line))
    return result


def _split_top_level(text: str, separator: str) -> list[str]:
    result: list[str] = []
    current: list[str] = []
    in_string = False
    escape = False
    paren_depth = 0
    bracket_depth = 0
    for ch in text:
        if in_string:
            current.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            current.append(ch)
        elif ch == "(":
            paren_depth += 1
            current.append(ch)
        elif ch == ")":
            paren_depth -= 1
            current.append(ch)
        elif ch == "[":
            bracket_depth += 1
            current.append(ch)
        elif ch == "]":
            bracket_depth -= 1
            current.append(ch)
        elif ch == separator and paren_depth == 0 and bracket_depth == 0:
            result.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    result.append("".join(current).strip())
    return result


def _parse_string_literal(text: str) -> str | None:
    s = text.strip()
    if len(s) < 2 or not s.startswith('"') or not s.endswith('"'):
        return None
    out: list[str] = []
    escape = False
    for ch in s[1:-1]:
        if escape:
            out.append(_ESCAPES.get(ch, ch))
            escape = False
        elif ch == "\\":
            escape = True
        else:
            out.append(ch)
    if escape:
        return None
    return "".join(out)


def infer_library_name(path: str) -> str:
    """Qt's own ``QFileInfo::completeBaseName()``: the file name with
    its *complete* suffix removed -- everything from the first ``.``,
    not just the last extension (so ``sg13g2_stdcell.layout.core`` ->
    ``sg13g2_stdcell``, not ``sg13g2_stdcell.layout``). Used both for
    a real, bare ``define(path)`` (library name inferred from the
    path) and, in ``gui``'s own import path, to infer a real cell name
    from a LibMan-sourced path the same way."""

    stem = path.replace("\\", "/").rsplit("/", 1)[-1]
    return stem.split(".", 1)[0]


def _parse_file_into(path: Path, project: LibManProject, active: set[Path], seen: set[Path]) -> None:
    if not path.is_file():
        raise LibManParseError(f"Lib file does not exist: '{path}'.")
    if path in active:
        raise LibManParseError(f"Recursive include detected for '{path}'.")
    if path in seen:
        return
    text = path.read_text(encoding="utf-8")
    active.add(path)
    try:
        for stmt_text, line_number in _split_statements(text):
            _parse_statement(stmt_text, path, line_number, project, active, seen)
    finally:
        active.discard(path)
    seen.add(path)


def _parse_statement(
    stmt: str, path: Path, line: int, project: LibManProject, active: set[Path], seen: set[Path]
) -> None:
    open_pos = stmt.find("(")
    close_pos = stmt.rfind(")")
    if open_pos <= 0 or close_pos < open_pos:
        raise LibManParseError(f"{path}:{line}: Invalid statement syntax: '{stmt}'.")
    func_name = stmt[:open_pos].strip()
    args_text = stmt[open_pos + 1 : close_pos].strip()
    tail = stmt[close_pos + 1 :].strip()
    if tail:
        raise LibManParseError(f"{path}:{line}: Unexpected trailing characters in statement: '{stmt}'.")

    if func_name == "include":
        args = _split_top_level(args_text, ",")
        if len(args) != 1:
            raise LibManParseError(f"{path}:{line}: include() expects exactly 1 argument, got {len(args)}.")
        include_path = _parse_string_literal(args[0].strip())
        if include_path is None:
            raise LibManParseError(f"{path}:{line}: include() argument must be a string literal.")
        resolved = (path.parent / include_path).resolve()
        _parse_file_into(resolved, project, active, seen)
        return

    if func_name == "define":
        args = [a for a in _split_top_level(args_text, ",") if a]
        if not args:
            raise LibManParseError(f"{path}:{line}: define() expects at least 1 argument.")
        positional: list[str] = []
        options: dict[str, str] = {}
        for arg in args:
            eq_split = _split_top_level(arg, "=")
            if len(eq_split) >= 2:
                key = eq_split[0].strip()
                if not key:
                    raise LibManParseError(f"{path}:{line}: Empty named option in define().")
                options[key] = arg[arg.index("=") + 1 :].strip()
            else:
                positional.append(arg)
        if len(positional) not in (1, 2):
            raise LibManParseError(
                f"{path}:{line}: define() expects 1 or 2 positional arguments, got {len(positional)}."
            )
        if len(positional) == 1:
            raw_path = _parse_string_literal(positional[0])
            if raw_path is None:
                raise LibManParseError(f"{path}:{line}: define(path) requires path to be a string literal.")
            name = infer_library_name(raw_path)
        else:
            raw_name = _parse_string_literal(positional[0])
            raw_path = _parse_string_literal(positional[1])
            if raw_name is None or raw_path is None:
                raise LibManParseError(f"{path}:{line}: define(name, path) requires string literal arguments.")
            name = raw_name
        project.defines.append(
            LibManDefine(name=name, path=raw_path, options=options, source_file=path, source_line=line)
        )
        return

    if func_name == "attach":
        args = _split_top_level(args_text, ",")
        if len(args) != 2:
            raise LibManParseError(f"{path}:{line}: attach() expects exactly 2 arguments, got {len(args)}.")
        design_lib = _parse_string_literal(args[0].strip())
        tech_lib = _parse_string_literal(args[1].strip())
        if not design_lib or not tech_lib:
            raise LibManParseError(f"{path}:{line}: attach() arguments must be non-empty string literals.")
        project.attaches.append(LibManAttach(design_library=design_lib, tech_library=tech_lib))
        return

    raise LibManParseError(f"{path}:{line}: Unknown function '{func_name}' in statement '{stmt}'.")


def parse_project_file(path: Path) -> LibManProject:
    """Parses a real ``.projects``/``.lib`` file, following real
    ``include()`` statements recursively (matching LibMan's own real
    behavior) -- see this module's own docstring for the exact real
    grammar and the commit it was verified against."""

    project = LibManProject()
    _parse_file_into(path.resolve(), project, set(), set())
    return project


def resolve_path(define: LibManDefine) -> Path:
    """A real ``LibManDefine.path`` resolved relative to its own real
    ``source_file``'s directory (matching LibFileParser's own real
    ``resolvePathRelativeToFile``) -- an already-absolute real path is
    returned unchanged. May not point at a real, existing file (see
    ``LibManDefine.path``'s own docstring)."""

    p = Path(define.path)
    if p.is_absolute():
        return p
    base = define.source_file.parent if define.source_file else Path(".")
    return (base / p).resolve()


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def render_project_file(defines: list[LibManDefine], attaches: list[LibManAttach] = ()) -> str:
    """Writes a real, minimal, valid ``.projects`` file -- one
    ``define("library", "path");`` line per entry (in the two-argument
    real form, always, for clarity -- never the path-only
    name-inferring form), matching the real header comment style seen
    in LibMan's own real, committed ``tests/data/sg13g2.projects``
    fixture."""

    lines = ["# KLayout library definition file", "# Generated by openPDKcreator", ""]
    for d in defines:
        lines.append(f'define("{_escape(d.name)}", "{_escape(d.path)}");')
    if attaches:
        lines.append("")
        for a in attaches:
            lines.append(f'attach("{_escape(a.design_library)}", "{_escape(a.tech_library)}");')
    return "\n".join(lines) + "\n"

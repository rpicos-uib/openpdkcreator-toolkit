"""Real, per-project launch-time redirection for tools whose own,
container-wide default configuration silently points at IHP's own
real data instead of whatever real project this app is actually
pointed at (found for Magic/xschem/Qucs-S/KLayout -- see each real
fix's own history in README.md).

Pulled out of ``gui/library_manager_view.py`` (where each was first
built and verified live, one tool at a time) into free functions
taking a real ``pdk_root: Path`` directly, rather than staying
instance methods reading ``self.app.pdk_root`` -- a second, real
launch path (``gui/tools_view.py``'s own Settings > Tools > **Launch
Selected**, which has no per-cell file/entry to work from at all) was
found to bypass every one of these fixes entirely, going straight to
a bare ``subprocess.Popen`` with no real environment/argv additions.
Rather than re-deriving the same real logic a second time there (the
exact duplication this project's own earlier Wizard audit flagged and
fixed for a different pair of call sites), both real GUI views now
call these same free functions -- ``library_manager_view.py``'s own
methods are thin, ``self.app.pdk_root``-threading wrappers around
them."""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import extraction as extraction_mod
from . import xschem_view_switch as xschem_view_switch_mod


def xschem_menu_path(pdk_root: Path) -> Path:
    """This project's own real ``libs.tech/xschem/xschem-menu`` path
    -- may or may not exist on disk yet; callers check for
    themselves."""

    return pdk_root / "libs.tech" / "xschem" / "xschem-menu"


def xschem_project_rcfile_path(pdk_root: Path) -> Path:
    """This project's own real, persistent
    ``libs.tech/xschem/xschemrc`` -- the exact real filename/path
    IHP's own sg13g2 PDK uses for its own full rc file."""

    return pdk_root / "libs.tech" / "xschem" / "xschemrc"


def default_xschem_rcfile_content(pdk_root: Path) -> str:
    """A real, working ``xschemrc`` template, adapted from IHP's own
    real ``libs.tech/xschem/xschemrc`` for sg13g2 down to the handful
    of lines that actually matter for a from-scratch project -- see
    ``library_manager_view.py``'s own git history for the full real
    rationale (IHP's own file keys its paths off
    ``env(PDK_ROOT)``/``env(PDK)``, a real, install-wide convention a
    from-scratch project has no equivalent of; this project's own
    real, already-known, concrete ``pdk_root`` path is used directly
    instead).

    Includes a real, conditional ``source`` of the real, tool-owned
    view-switch menu (``xschem_view_switch.MENU_FILENAME``) -- only
    baked into a freshly-created persistent rc file from here on; a
    real, disclosed limitation, not a silent gap: an *already-existing*
    persistent rc file is never rewritten by this tool (see
    ``xschem_rcfile`` below), so one created before this feature
    existed won't pick it up automatically -- recreate it, or add the
    one real ``source`` line by hand, to get it."""

    xschem_dir = pdk_root / "libs.tech" / "xschem"
    menu_path = xschem_menu_path(pdk_root)
    view_switch_path = xschem_dir / xschem_view_switch_mod.MENU_FILENAME
    return (
        "#### Real, project-specific xschem startup file.\n"
        "#### Adapted from IHP-GmbH's own real libs.tech/xschem/xschemrc for\n"
        "#### sg13g2 -- hardcoded to this project's own real path instead of\n"
        "#### IHP's env-var-based PDK_ROOT/PDK convention. Edit freely; this\n"
        "#### file is only ever read, never overwritten by this app once it\n"
        "#### exists (see the Library Manager tab's own Xschem RC File row).\n"
        "\n"
        "###########################################################################\n"
        "#### PROJECT SYMBOL LIBRARY PATH\n"
        "###########################################################################\n"
        f"append XSCHEM_LIBRARY_PATH :{xschem_dir}\n"
        "\n"
        "###########################################################################\n"
        "#### DIRECTORY WHERE SIMULATIONS, NETLIST AND SIMULATOR OUTPUTS ARE PLACED\n"
        "###########################################################################\n"
        "set netlist_dir $env(PWD)/simulations\n"
        "\n"
        "###########################################################################\n"
        "#### GENERAL PREFERENCES (same real defaults as IHP's own xschemrc)\n"
        "###########################################################################\n"
        "set zoom_full_center 1\n"
        "set autotrim_wires 1\n"
        "set toolbar_visible 1\n"
        "set tabbed_interface 1\n"
        "set live_cursor2_backannotate 1\n"
        "set to_pdf {ps2pdf -dAutoRotatePages=/None}\n"
        "\n"
        "###########################################################################\n"
        "#### TCL FILES TO LOAD AT STARTUP\n"
        "###########################################################################\n"
        "set tcl_files {}\n"
        "lappend tcl_files ${XSCHEM_SHAREDIR}/ngspice_backannotate.tcl\n"
        "\n"
        "###########################################################################\n"
        "#### PROJECT-SPECIFIC CUSTOM MENU\n"
        "###########################################################################\n"
        "#### Sourced only if this project's own real xschem-menu file exists\n"
        "#### (Library Manager tab's own Xschem Custom Menu row).\n"
        f"if {{[file exists {{{menu_path}}}]}} {{\n"
        f"  source {menu_path}\n"
        "}\n"
        "\n"
        "###########################################################################\n"
        "#### PER-INSTANCE VIEW SWITCH (behavioral vs. extracted layout)\n"
        "###########################################################################\n"
        "#### Real, tool-owned -- regenerated on every launch, not hand-edited.\n"
        f"if {{[file exists {{{view_switch_path}}}]}} {{\n"
        f"  source {view_switch_path}\n"
        "}\n"
    )


def xschem_rcfile(pdk_root: Path) -> str | None:
    """The real ``--rcfile <path>`` value for the next **Open in
    xschem** launch. If this project has its own real, persistent
    ``libs.tech/xschem/xschemrc`` (``xschem_project_rcfile_path``),
    that real file is used directly, unmodified. Otherwise falls back
    to a real, freshly-written, minimal rc file (just the real
    ``XSCHEM_LIBRARY_PATH`` append plus a conditional ``xschem-menu``
    source) so **Open in xschem** still works correctly out of the
    box before a project bothers to create one -- or ``None`` if this
    technology has no real ``libs.tech/xschem`` directory at all yet.

    A real, found-not-assumed bug fix: this dev container's own real,
    global ``~/.xschem/xschemrc`` (part of the base image, not this
    project) unconditionally sources
    ``$PDK_ROOT/$PDK/libs.tech/xschem/xschemrc``, with both
    ``PDK_ROOT`` and ``PDK`` hardcoded container-wide to IHP's own
    real values -- so a plain ``xschem`` launch for *any* project
    silently pulls in IHP's own real symbol library path and its own
    real custom menu, never this project's own. Passed via xschem's
    own real ``--rcfile <file>`` flag (confirmed from its own real,
    installed man page), so the wrong, hardcoded default chain is
    replaced outright rather than layered under.

    Also (re)writes the real, tool-owned view-switch menu file
    (``xschem_view_switch.ensure_view_switch_menu``) every real call,
    unconditionally -- both the persistent-rcfile branch below and the
    ephemeral fallback reference the exact same real, stable path, so
    it has to actually exist on disk regardless of which branch runs,
    and staying current with this tool's own version (not a one-time,
    potentially-stale write) matches its own real "regenerated on
    every launch" docstring."""

    xschem_view_switch_mod.ensure_view_switch_menu(pdk_root)

    project_rcfile = xschem_project_rcfile_path(pdk_root)
    if project_rcfile.is_file():
        return str(project_rcfile)

    xschem_dir = pdk_root / "libs.tech" / "xschem"
    if not xschem_dir.is_dir():
        return None
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".tcl", prefix="openpdkcreator_xschemrc_", delete=False, encoding="utf-8",
    )
    with handle:
        handle.write(f"append XSCHEM_LIBRARY_PATH :{xschem_dir}\n")
        view_switch_file = xschem_dir / xschem_view_switch_mod.MENU_FILENAME
        if view_switch_file.is_file():
            handle.write(f"source {view_switch_file}\n")
        menu_file = xschem_menu_path(pdk_root)
        if menu_file.is_file():
            handle.write(f"source {menu_file}\n")
    return handle.name


def qucs_env(pdk_root: Path) -> dict[str, str] | None:
    """Real environment variables that redirect Qucs-S's own real
    ``QucsHomeDir`` (its Projects panel's own real workspace root) at
    this project's own real ``libs.tech/qucs-s``, or ``None`` if that
    directory doesn't exist yet -- same real bug class as
    ``xschem_rcfile`` above: this dev container's own real, global
    ``~/.config/qucs/qucs_s.conf`` hardcodes
    ``QucsHomeDir=/headless/QucsWorkspace``, itself a real symlink
    farm pointing at IHP's own real ``/foss/pdks`` -- so a plain
    ``qucs-s`` launch for *any* project shows IHP's own real Projects
    panel, never this project's own.

    Unlike Magic/xschem, Qucs-S has no real CLI flag for this
    (confirmed from its own real, fetched ``main.cpp``) and its
    settings live in one real, shared, global file
    (``QSettings("qucs", "qucs_s")``, which follows Qt's own standard
    ``$XDG_CONFIG_HOME``-aware lookup) -- so rather than mutating that
    real, shared file (which would leak into every other real Qucs-S
    session, including ones for a different project entirely), a
    real, fresh copy of it is written into a real, disposable temp
    directory each launch, with only ``QucsHomeDir=`` swapped, and
    pointed at via ``XDG_CONFIG_HOME`` for that one real subprocess
    alone."""

    qucs_dir = pdk_root / "libs.tech" / "qucs-s"
    if not qucs_dir.is_dir():
        return None
    real_conf = Path.home() / ".config" / "qucs" / "qucs_s.conf"
    if not real_conf.is_file():
        return None
    lines = real_conf.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    lines = [
        f"QucsHomeDir={qucs_dir}\n" if line.startswith("QucsHomeDir=") else line
        for line in lines
    ]
    tmp_config_home = Path(tempfile.mkdtemp(prefix="openpdkcreator_qucs_xdg_"))
    conf_dir = tmp_config_home / "qucs"
    conf_dir.mkdir(parents=True)
    (conf_dir / "qucs_s.conf").write_text("".join(lines), encoding="utf-8")
    return {"XDG_CONFIG_HOME": str(tmp_config_home)}


def magic_tech_load_line(pdk_root: Path) -> str:
    """A real ``tech load <path>`` Tcl line for this project's own
    real technology (``extraction.default_tech_file``), or an empty
    string if none exists yet -- a real, found-not-assumed bug fix:
    without this, Magic falls back to auto-sourcing whatever
    ``.magicrc`` its own compiled default/environment happens to
    point at, silently loading the wrong real technology."""

    tech_file = extraction_mod.default_tech_file(pdk_root)
    return f"tech load {tech_file}\n" if tech_file is not None else ""


def magic_tech_load_script(pdk_root: Path) -> str | None:
    """A real, freshly-written Tcl script's path containing just
    ``magic_tech_load_line``'s own real line, or ``None`` if none
    exists yet -- for a **Launch Selected** Magic click with no
    specific cell/file to also load (unlike
    ``library_manager_view.py``'s own per-cell
    ``_open_magic_gds``/``_open_magic_mag``, which prepend the same
    real line to their own generated scripts): still worth getting
    the real technology right before a user manually opens something
    inside, rather than leaving Magic to silently fall back to
    whatever its own compiled default happens to be."""

    line = magic_tech_load_line(pdk_root)
    if not line:
        return None
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".tcl", prefix="openpdkcreator_magic_techonly_", delete=False, encoding="utf-8",
    )
    with handle:
        handle.write(line)
    return handle.name

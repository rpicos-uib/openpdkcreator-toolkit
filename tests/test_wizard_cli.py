import sys
sys.path.insert(0, "/foss/designs")
import contextlib
import io
import shutil
import stat
from pathlib import Path

import main as main_mod
from openpdkcreator import export as export_mod
from openpdkcreator import project_io
from openpdkcreator.pdklib import shell_env as shell_env_mod

TMP = Path("/tmp/test_wizard_cli")
shutil.rmtree(TMP, ignore_errors=True)

# Real project-level state (saves/, shell_env/) is normally shared,
# repo-root state -- same real reason test_change_project_directory.py
# already redirects it for the duration of a test: this test must not
# pollute (or collide with) the real, shared saves/shell_env/ trees.
ORIGINAL_PROJECT_ROOT = export_mod.PROJECT_ROOT
ORIGINAL_SAVE_DIR = project_io.SAVE_DIR
project_root = TMP / "project_root"
export_mod.PROJECT_ROOT = project_root
project_io.SAVE_DIR = project_root / "saves"


def run(argv: list[str]) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main_mod.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


try:
    # --- default (non-blank): a real, immediately-usable skeleton,
    # named from a slugified --name, project name saved verbatim ---
    new_root = TMP / "new_pdk"
    code, out, err = run(["--pdk-root", str(new_root), "wizard", "--name", "My Memristor PDK"])
    assert code == 0, (code, out, err)
    assert (new_root / "libs.tech" / "klayout" / "tech" / "my_memristor_pdk.lyp").is_file()
    assert (new_root / "libs.tech" / "magic" / "my_memristor_pdk.tech").is_file()
    assert (new_root / "libs.tech" / "klayout" / "tech" / "drc" / "custom_rules.drc").is_file()
    assert (new_root / "libs.ref" / "my_memristor_pdk" / "lef" / "my_memristor_pdk.lef").is_file()
    print("PASS: wizard (default) writes the real four-domain skeleton, named from a slugified --name.")

    save_path = project_io.save_path_for(new_root)
    assert save_path.is_file()
    loaded = project_io.load_state(new_root)
    assert loaded.project_name == "My Memristor PDK"
    print("PASS: wizard saves the exact, unslugified --name as this project's own project_name.")

    env_path = project_root / "shell_env" / "pdk_env.sh"
    assert env_path.is_file()
    assert stat.S_IMODE(env_path.stat().st_mode) & 0o111, "shell-env script should be executable"
    expected_script = shell_env_mod.generate_shell_env_script(new_root, "pdk_env.sh").text
    assert env_path.read_text() == expected_script
    assert str(env_path) in out
    print("PASS: wizard --env save (default) writes the real, executable shell-env script and reports its path.")

    # --- --blank: genuinely zero domain files ---
    blank_root = TMP / "blank_pdk"
    code, out, err = run(["--pdk-root", str(blank_root), "wizard", "--name", "Blank One", "--blank"])
    assert code == 0, (code, out, err)
    assert (blank_root / "libs.tech").is_dir() and (blank_root / "libs.ref").is_dir()
    assert not any(p.is_file() for p in blank_root.rglob("*"))
    print("PASS: wizard --blank creates only the two real top-level directories, no domain files.")

    # --- non-empty target directory refuses without --force ---
    guarded_root = TMP / "guarded_pdk"
    guarded_root.mkdir(parents=True)
    (guarded_root / "stray.txt").write_text("pre-existing")
    code, out, err = run(["--pdk-root", str(guarded_root), "wizard", "--name", "Guarded"])
    assert code == 2, (code, out, err)
    assert not (guarded_root / "libs.tech").exists()
    assert "not empty" in err
    print("PASS: a non-empty --pdk-root refuses without --force, and creates nothing.")

    code, out, err = run(["--pdk-root", str(guarded_root), "wizard", "--name", "Guarded", "--force"])
    assert code == 0, (code, out, err)
    assert (guarded_root / "libs.tech").is_dir()
    assert (guarded_root / "stray.txt").is_file()
    print("PASS: --force proceeds anyway, alongside the pre-existing, unrelated file.")

    # --- --env print: stdout carries *only* the raw, sourceable
    # script; every status message moves to stderr instead, and the
    # shared, real shell_env/pdk_env.sh (written by the earlier --env
    # save case above) is left untouched ---
    saved_env_before = env_path.read_text()
    print_root = TMP / "print_pdk"
    code, out, err = run(["--pdk-root", str(print_root), "wizard", "--name", "PrintEnv", "--env", "print"])
    assert code == 0, (code, out, err)
    expected_script = shell_env_mod.generate_shell_env_script(print_root, "pdk_env.sh").text
    assert out == expected_script, (out, expected_script)
    assert "Created a new PDK" in err
    assert env_path.read_text() == saved_env_before
    print("PASS: --env print puts only the raw, sourceable script on stdout, status messages on stderr, "
          "and doesn't touch the on-disk shell-env script.")

    # --- --env skip: no shell-env script at all, project state still saved ---
    skip_root = TMP / "skip_pdk"
    code, out, err = run(["--pdk-root", str(skip_root), "wizard", "--name", "SkipEnv", "--env", "skip"])
    assert code == 0, (code, out, err)
    assert project_io.load_state(skip_root).project_name == "SkipEnv"
    assert "shell_env" not in out
    print("PASS: --env skip saves the project but writes no shell-env script.")

    # --- --open-gui chains into cmd_gui (verified without a real Tk
    # window: cmd_gui itself is monkeypatched, same "don't block a
    # scripted run on a real GUI" precedent every other test already
    # uses for blocking Tk calls) ---
    gui_calls = []
    original_cmd_gui = main_mod.cmd_gui
    main_mod.cmd_gui = lambda pdk_root: gui_calls.append(pdk_root) or 0
    try:
        gui_root = TMP / "gui_pdk"
        code, out, err = run(["--pdk-root", str(gui_root), "wizard", "--name", "GuiChain", "--open-gui"])
    finally:
        main_mod.cmd_gui = original_cmd_gui
    assert code == 0, (code, out, err)
    assert gui_calls == [gui_root]
    print("PASS: --open-gui chains into cmd_gui with the freshly created pdk_root.")

    # --- --name slugification: mixed case/punctuation collapses to
    # one real, filename-safe stem ---
    slug_root = TMP / "slug_pdk"
    run(["--pdk-root", str(slug_root), "wizard", "--name", "  Weird!! Name--123  "])
    assert (slug_root / "libs.tech" / "magic" / "weird_name_123.tech").is_file()
    print("PASS: --name is slugified to a real, filename-safe stem for the skeleton files.")

finally:
    export_mod.PROJECT_ROOT = ORIGINAL_PROJECT_ROOT
    project_io.SAVE_DIR = ORIGINAL_SAVE_DIR
    shutil.rmtree(TMP, ignore_errors=True)

print("ALL WIZARD CLI TESTS PASS")

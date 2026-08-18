# Tests

Real, driven integration tests -- each script builds a real `App`
(Tk), drives real GUI actions (button clicks, form edits, canvas
events), and asserts against real, parsed data or real, exported file
text. No mocks of this project's own code; the only things ever
monkeypatched are blocking Tk dialogs (`messagebox`/a modal
`Toplevel`) that would otherwise hang a scripted run waiting for a
real click.

**These only run inside the IIC-OSIC-TOOLS container** (`tkinter`,
the real EDA toolchain, and the real, downloaded IHP data all live
there -- see the main README's own Quickstart for
`./start_eda_container.sh`). They don't run on the bare host. Each
script hardcodes `sys.path.insert(0, "/foss/designs")` (the
container's own bind-mounted project root), so run them from inside a
shell in that container -- **through a real login shell** (`bash -lc`),
not a bare `podman exec ... python3 ...`: the container's own EDA
toolchain PATH is set up by its profile scripts, only sourced for a
login shell. A bare `podman exec` invocation without one is missing
that PATH -- confirmed real, not theoretical: `eda_tools.check_tool`
silently reports a real, installed tool (e.g. `qucs-s`) as not found
this way, and any test exercising it then blocks forever on a real,
unmockable `messagebox.showerror` modal waiting for a click that never
comes in a headless run. e.g.:

```bash
podman exec -e DISPLAY=:1 <container-name> bash -lc 'python3 tests/test_pdk_wizard.py'
```

or, to run the whole suite in one go:

```bash
podman exec -e DISPLAY=:1 <container-name> bash -lc 'bash tests/run_all.sh'
```

## What each test needs

Most tests point `PDK_ROOT` at the real, downloaded
`data/ihp-sg13g2/ihp-sg13g2` and assert against real IHP counts/data
-- run `python3 main.py fetch` first (see the main README) if that
directory doesn't exist yet.

A few build their own small, throwaway PDK tree under `/tmp/` instead,
for exercising a genuinely *empty*, from-scratch project (the
`create_new_*` skeleton functions, the PDK Wizard's own from-scratch
status) without needing the full real deck at all:
`test_skeletons.py`, `test_skeleton_buttons.py`, `test_drc_generate.py`,
`test_pdk_wizard_empty.py`.

A handful exercise a real **Create File** action against the shared,
real `data/` tree itself (not a throwaway dir) -- `test_edit_create_buttons.py`
-- since that's the only way to verify Create File writes into the
*real* PDK's own real relative-path conventions. These clean up their
own created files at the end; if a run is interrupted before cleanup,
re-run `run_all.sh` (it starts from a known-clean state) or manually
remove any stray `my_new_*` file under `data/ihp-sg13g2/ihp-sg13g2/`.

`test_user_models_gui.py`/`test_user_models_v2.py` write their own
real, throwaway fixture files into `user_models/` (not gitignored,
real tracked project content) at the start and remove them at the
end -- each is fully self-contained, runnable independently, in any
order, repeatedly.

## Recorded full-suite runs

`results/` holds occasional, dated, full-suite run logs -- a real,
committed record of "the whole suite passed, on this date, and here's
every real `PASS:` line from every test," not just the terse
`run_all.sh` summary (which only prints a failing test's own last few
lines, nothing at all on success). Not automated or regenerated on
every run -- added deliberately, by hand, when a record is worth
keeping (e.g. after a significant batch of changes). To make one:

```bash
podman exec -e DISPLAY=:1 <container-name> bash -lc '
cd /foss/designs
rm -f /tmp/test_*.py.log
bash tests/run_all.sh
for f in tests/test_*.py; do
  echo ""; echo "### $(basename "$f")"
  cat "/tmp/$(basename "$f").log"
done
' > tests/results/run_all_YYYY-MM-DD.log
```

`results/run_all_2026-08-18.log` is the first one -- 58/58 passing,
captured right after this project's own menu-restructuring/multi-
project-directory work (see the main README's own changelog).

## Adding a new test

Match the existing shape: a plain script, not a pytest `test_...()`
function -- `import sys; sys.path.insert(0, "/foss/designs")`, build a
real `App`, drive it, `assert` real outcomes, `print("PASS: ...")` per
checkpoint and a final `"ALL ... PASS"` line, `root.destroy()` at the
end. If it needs to write anywhere other than a throwaway `/tmp/`
directory it owns outright, clean up after itself (see above) so a
later run -- of this test or any other -- never inherits stale state.

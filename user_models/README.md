# User models

Bring your own Verilog/Verilog-A models into this project and connect
them to the rest of the real PDK.

- `verilog/*.v` -- your own behavioral Verilog models.
- `veriloga/*.va` -- your own Verilog-A compact/behavioral models.

Both are parsed the same way (`pdklib/user_models.py`, reusing
`pdklib/verilog.py`'s own real `module NAME(port, ...); ... endmodule`
parser -- real Verilog-A uses the exact same header/port syntax, so no
separate parser was needed). Only the module's own name and port list
are extracted -- the same bounded, structure-not-full-semantics scope
every other domain in this project already uses.

**Linking to a real cell**, two ways:

1. **Automatic**: name a module the same as a real cell (e.g. a real
   `sg13g2_lv_nmos` counterpart) and it's picked up automatically by
   `pdklib/cells.py`'s own cell aggregation, the same way LEF/CDL/SPICE/
   Verilog/Liberty/GDS views already are.
2. **Explicit**: use the **Simulation > User Models** tab in the GUI
   (or edit `links.yaml` directly) to link a module with a different
   name -- or one describing a wholly new, not-yet-real cell -- to any
   cell name. Links are stored in `links.yaml` next to this file,
   tracked by git (unlike `data/`/`saves/`, which hold real,
   downloaded PDK content or edits derived from it).

This directory and its contents are yours -- nothing here is touched
by `pdklib/fetch.py` or any real, downloaded PDK data.

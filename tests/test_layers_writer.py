import sys
sys.path.insert(0, "/foss/designs")
from pathlib import Path
from openpdkcreator.pdklib import layers as layers_mod
from openpdkcreator.pdklib import layers_writer

root = Path("data/ihp-sg13g2/ihp-sg13g2")
lyp_path = layers_mod.find_lyp(root)


def check_all_others_unchanged(original_layers, edited_layers, changed_name_before, allow_reorder=False):
    # After a deletion, every subsequent real layer's own start_line
    # legitimately shifts -- compare by name (stable here, since these
    # tests don't rename) rather than by position in that case.
    key = (lambda l: l.name) if allow_reorder else (lambda l: l.start_line)
    orig_by_key = {key(l): l for l in original_layers if l.start_line}
    new_by_key = {key(l): l for l in edited_layers if l.start_line}
    for k, orig in orig_by_key.items():
        if orig.name == changed_name_before:
            continue
        new = new_by_key.get(k)
        assert new is not None, f"layer {k} disappeared"
        assert (new.name, new.gds_layer, new.gds_datatype, new.frame_color, new.fill_color) == \
               (orig.name, orig.gds_layer, orig.gds_datatype, orig.frame_color, orig.fill_color), \
               f"unrelated layer {k} changed!"


def reparse_after_export(layers, tmp_name):
    export_path = Path("/tmp") / tmp_name
    layers_writer.export_lyp_file(layers, lyp_path, export_path)
    return layers_mod.import_layers(root, export_path), export_path


# --- Test 1: edit frame_color/fill_color/name/gds_layer ---
layers = layers_mod.import_layers(root, lyp_path)
target = next(l for l in layers if l.name == "Substrate.drawing")
orig_name = target.name
target.frame_color = "#123456"
target.fill_color = "#654321"
target.gds_layer = 999
reparsed, export_path = reparse_after_export(layers, "test1_layer_edit.lyp")
r = next(l for l in reparsed if l.start_line == target.start_line)
assert r.frame_color == "#123456", r.frame_color
assert r.fill_color == "#654321", r.fill_color
assert r.gds_layer == 999, r.gds_layer
assert r.gds_datatype == target.gds_datatype  # unedited field preserved
check_all_others_unchanged(layers_mod.import_layers(root, lyp_path), reparsed, orig_name)
print("PASS: frame_color/fill_color/gds_layer edit round-trips correctly, other layers unchanged")

# --- Test 2: rename a layer ---
layers = layers_mod.import_layers(root, lyp_path)
target = next(l for l in layers if l.name == "Activ.drawing")
orig_name = target.name
target.name = "Activ.RENAMED_TEST"
reparsed, export_path = reparse_after_export(layers, "test2_rename.lyp")
r = next(l for l in reparsed if l.start_line == target.start_line)
assert r.name == "Activ.RENAMED_TEST", r.name
check_all_others_unchanged(layers_mod.import_layers(root, lyp_path), reparsed, orig_name)
print("PASS: rename round-trips correctly")

# --- Test 3: new layer ---
layers = layers_mod.import_layers(root, lyp_path)
orig_count = len(layers)
from openpdkcreator.models import Layer
new_layer = Layer(name="ZZ_TEST_NEW_LAYER", gds_layer=250, gds_datatype=5, frame_color="#00ff00", fill_color="#00ff00")
layers.append(new_layer)
reparsed, export_path = reparse_after_export(layers, "test3_new_layer.lyp")
assert len(reparsed) == orig_count + 1, len(reparsed)
r = next(l for l in reparsed if l.name == "ZZ_TEST_NEW_LAYER")
assert r.gds_layer == 250 and r.gds_datatype == 5
assert r.frame_color == "#00ff00"
check_all_others_unchanged(layers_mod.import_layers(root, lyp_path), reparsed, "__none__")
print(f"PASS: new layer round-trips correctly, count now {len(reparsed)}")

# --- Test 4: deleted layer ---
layers = layers_mod.import_layers(root, lyp_path)
orig_count = len(layers)
deleted_name = layers[5].name
layers = [l for l in layers if l is not layers[5]] if False else [l for l in layers if l.name != deleted_name]
reparsed, export_path = reparse_after_export(layers, "test4_delete.lyp")
assert len(reparsed) == orig_count - 1, len(reparsed)
assert not any(l.name == deleted_name for l in reparsed)
check_all_others_unchanged(layers_mod.import_layers(root, lyp_path), reparsed, deleted_name, allow_reorder=True)
print(f"PASS: deleted layer round-trips correctly, count now {len(reparsed)}")

print("ALL LAYERS WRITER ROUND-TRIP TESTS PASSED")

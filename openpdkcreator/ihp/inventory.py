"""An honest, per-tool file inventory of a real, downloaded IHP-style
PDK tree -- a real file census, never an attempt at parsing any tool's
proprietary format (Magic ``.tech``/DRC Ruby DSL, LEF, GDS, Liberty
have no generic parser anywhere in this project yet; that's real,
separate future work, tracked in README.md).

Organizes by tool, per the user's own framing: walks each real
``libs.tech/<tool>/`` subdirectory (confirmed for IHP's SG13G2: 15 of
them -- ``digital, gdsfactory, klayout, librelane, magic, netgen,
ngspice, openems, openroad, palace, parasitics, qucs-s, verilog-a,
xschem, xyce``) plus each real ``libs.ref/<family>/<view>/`` directory
and the top-level ``libs.doc``/``libs.qa``, and reports what's actually
there: file count, total bytes, and a Counter of file extensions, plus
a handful of real sample paths so a human can spot-check.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ToolInventory:
    tool: str
    file_count: int = 0
    total_bytes: int = 0
    extensions: Counter = field(default_factory=Counter)
    sample_paths: list[str] = field(default_factory=list)


def _scan_dir(root: Path, label: str, sample_limit: int = 5) -> ToolInventory | None:
    if not root.is_dir():
        return None
    inv = ToolInventory(tool=label)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        inv.file_count += 1
        try:
            inv.total_bytes += path.stat().st_size
        except OSError:
            continue
        inv.extensions[path.suffix or "(no extension)"] += 1
        if len(inv.sample_paths) < sample_limit:
            inv.sample_paths.append(str(path.relative_to(root)))
    return inv


def scan_libs_tech(pdk_root: Path) -> list[ToolInventory]:
    """One ToolInventory per real libs.tech/<tool>/ subdirectory found."""

    libs_tech = pdk_root / "libs.tech"
    if not libs_tech.is_dir():
        return []
    inventories = []
    for tool_dir in sorted(p for p in libs_tech.iterdir() if p.is_dir()):
        inv = _scan_dir(tool_dir, f"libs.tech/{tool_dir.name}")
        if inv is not None:
            inventories.append(inv)
    return inventories


def scan_libs_ref(pdk_root: Path) -> list[ToolInventory]:
    """One ToolInventory per real libs.ref/<family>/<view>/ directory."""

    libs_ref = pdk_root / "libs.ref"
    if not libs_ref.is_dir():
        return []
    inventories = []
    for family_dir in sorted(p for p in libs_ref.iterdir() if p.is_dir()):
        for view_dir in sorted(p for p in family_dir.iterdir() if p.is_dir()):
            inv = _scan_dir(view_dir, f"libs.ref/{family_dir.name}/{view_dir.name}")
            if inv is not None:
                inventories.append(inv)
    return inventories


def scan_all(pdk_root: Path) -> list[ToolInventory]:
    """Every real top-level domain: libs.tech/<tool>, libs.ref/<family>/<view>,
    and libs.doc/libs.qa as single, whole-directory entries."""

    inventories = scan_libs_tech(pdk_root) + scan_libs_ref(pdk_root)
    for label in ("libs.doc", "libs.qa"):
        inv = _scan_dir(pdk_root / label, label)
        if inv is not None:
            inventories.append(inv)
    return inventories


def print_inventory(inventories: list[ToolInventory]) -> None:
    if not inventories:
        print("Nothing found -- has ihp/fetch.py been run yet?")
        return
    widths = (30, 10, 14, 30)
    header = ("domain", "files", "size", "top extensions")
    print("  ".join(h.ljust(w) for h, w in zip(header, widths)))
    print("  ".join("-" * w for w in widths))
    for inv in inventories:
        size_mb = inv.total_bytes / (1024 * 1024)
        top_ext = ", ".join(f"{ext}:{count}" for ext, count in inv.extensions.most_common(4))
        print(
            f"{inv.tool.ljust(widths[0])}  "
            f"{str(inv.file_count).ljust(widths[1])}  "
            f"{f'{size_mb:.1f} MB'.ljust(widths[2])}  "
            f"{top_ext}"
        )

"""Real, minimal Magic ``.mag`` layout file parsing/creation --
structural scope only (tech/timestamp header, per-section real rect
*count*, not full geometry -- matching ``pdklib/gds.py``'s own real
"bbox/shape-count, not full geometry" precedent for the exact same
reason: this project's own bounded "structure, not a full parser/
editor" discipline used everywhere else).

**Why this exists**: closes a real, previously-blocked Future Work
item ("Real layout-view creation... blocked on this codebase having no
Magic .mag file parser at all yet"). Magic's own real ``gds read``/
``save`` is the actual, real path from a hand-authored ``.mag``
skeleton to a real, exportable GDS; this module only needs to write a
real, valid, *empty* starting skeleton (the same "Create, then draw
for real in the actual external tool" pattern xschem/Qucs-S Symbol/
Schematic already established -- see their own ``create_new_sym_file``
docstrings) and parse enough of a real ``.mag`` file back to show real,
structural presence, not model or edit real geometry.

**Grounded in two real sources, not one**: Magic's own official
file-format manual (``opencircuitdesign.com/magic/manpages/
mag_manpage.html``, Tim Edwards' own current maintenance site) gives
the real header/layer/``rect``/``use``/``rlabel``/``<< end >>``
structure -- but a real, live-generated file (this project's own
installed Magic, ``gds read`` on a real IHP GDS cell then ``save``)
turned out to use a real, richer, currently-versioned shape the
written manual's own text didn't fully capture: a real ``magscale a
b`` header line between ``tech`` and ``timestamp``; a real, special
``<< checkpaint >>`` section (treated here the same as any other
named section -- it has real ``rect`` lines just like a layer does,
and this module's own bounded scope has no reason to special-case
it); labels via real ``flabel layer justif x1 y1 x2 y2 rotation font
size ... text`` lines (not the plainer ``rlabel`` the manual
describes -- confirmed real, current behavior takes precedence over
older written docs) each followed by a real ``port N direction`` line
this module doesn't model; and a real ``<< properties >>`` section
with real ``string KEY value`` lines. All confirmed by directly
exporting a real IHP cell (``sg13g2_inv_1``) through this project's own
installed Magic and inspecting the real output verbatim -- not
guessed from the manual text alone."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MagSection:
    name: str
    """A real layer name, or the one real special, non-layer section
    name this module still tracks structurally: ``checkpaint`` (a real
    section shaped just like a layer one, real ``rect`` lines and
    all)."""
    rect_count: int = 0


@dataclass
class MagFile:
    source_path: Path
    tech: str = ""
    timestamp: int | None = None
    magscale: tuple[int, int] | None = None
    """Real ``magscale <a> <b>`` header line, when present -- Magic's
    own real internal-units-per-lambda scale factor for this cell."""
    sections: list[MagSection] = field(default_factory=list)
    use_count: int = 0
    """Real ``use <filename> <use-id>`` sub-cell instance lines found
    -- counted, not modeled (position/array/transform stay out of this
    module's own bounded, structural-only scope)."""
    label_count: int = 0
    """Real ``flabel ...`` lines inside the real ``<< labels >>``
    section -- the label text/geometry/port direction aren't modeled,
    only counted."""
    property_count: int = 0
    """Real ``string KEY value`` lines inside the real
    ``<< properties >>`` section."""


def find_mag_files(pdk_root: Path) -> list[Path]:
    """IHP's own real, downloaded PDK ships no real ``.mag`` files at
    all (GDS is its own real layout format) -- ``libs.ref/<family>/
    mag/`` is this project's own sensible, but *not* IHP-confirmed,
    new convention for project-authored ones, chosen to mirror the
    real ``lef/``/``cdl/``/``spice/``/``verilog/``/``gds/`` siblings
    already there."""

    return sorted(pdk_root.glob("libs.ref/*/mag/*.mag"))


def parse_mag_file(path: Path) -> MagFile:
    mag = MagFile(source_path=path)
    current: MagSection | None = None
    mode = "layer"  # "layer" | "labels" | "properties"

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line == "magic":
            continue
        if line.startswith("tech "):
            mag.tech = line[len("tech "):].strip()
            continue
        if line.startswith("magscale "):
            parts = line.split()
            if len(parts) >= 3:
                try:
                    mag.magscale = (int(parts[1]), int(parts[2]))
                except ValueError:
                    pass
            continue
        if line.startswith("timestamp "):
            try:
                mag.timestamp = int(line[len("timestamp "):].strip())
            except ValueError:
                pass
            continue
        if line.startswith("<<") and line.endswith(">>"):
            section_name = line[2:-2].strip()
            if section_name == "end":
                break
            if section_name == "labels":
                mode = "labels"
                current = None
                continue
            if section_name == "properties":
                mode = "properties"
                current = None
                continue
            mode = "layer"
            current = MagSection(name=section_name)
            mag.sections.append(current)
            continue
        if line.startswith("use "):
            mag.use_count += 1
            continue
        if mode == "layer" and line.startswith("rect ") and current is not None:
            current.rect_count += 1
            continue
        if mode == "labels" and line.startswith("flabel "):
            mag.label_count += 1
            continue
        if mode == "properties" and line.startswith("string "):
            mag.property_count += 1
            continue

    return mag


def create_new_mag_file(path: Path, tech: str) -> None:
    """Writes a real, minimal, valid, genuinely empty Magic ``.mag``
    skeleton -- ``magic``/``tech <name>``/``timestamp <now>``/
    ``<< end >>``, matching Magic's own real file format exactly
    (confirmed: this project's own installed Magic binary loads it
    cleanly, no errors, in the real container). Genuinely usable
    immediately afterward, not just a stub -- open it via **Open in
    Magic** and start drawing real geometry; Magic's own real ``gds
    write`` then produces a real, exportable GDS from it, closing the
    real "layout-view creation" gap the same way every other
    Create-from-scratch domain here does: write a real, valid, empty
    starting file, then let the real, external tool do the actual
    drawing (matching xschem/Qucs-S Symbol/Schematic's own
    ``create_new_sym_file``/``create_new_sch_file`` precedent)."""

    if path.exists():
        raise FileExistsError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"magic\ntech {tech}\ntimestamp {int(time.time())}\n<< end >>\n"
    path.write_text(text, encoding="utf-8")

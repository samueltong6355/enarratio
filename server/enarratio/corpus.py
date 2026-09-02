"""The local text corpus, and how to walk it.

Perseus marks up its texts with about as much variety as the works themselves have. The
*Aeneid* divides into books of verse lines. Horace's *Odes* into books of poems of lines.
Catullus into poems, grouped under headings that are not part of the citation. Caesar's
*Gallic War* is prose, and its chapters and sections are not divisions at all but
``<milestone>`` markers punctuating a flat stream of text.

A single hard-coded shape cannot read all of that, so each work carries a small spec saying
which ``div`` types form its citation hierarchy, whether its leaves are verse lines or prose
sections, and which milestone units to follow. Everything downstream -- the passage index
and the commentary lookup -- then speaks one language: a *reference path* (a tuple of
numbers such as ``(1,)`` for *Aeneid* 1, ``(1, 5)`` for *Odes* 1.5, ``(1, 1)`` for *BG*
1.1) plus a leaf number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator
from xml.etree import ElementTree as ET

from .commentary import _readable_xml

__all__ = ["Work", "WORKS", "extract_units", "Unit", "work_by_key", "format_citation"]


@dataclass(frozen=True)
class Work:
    key: str
    author: str
    title: str
    filename: str
    #: div ``type`` values, outermost first, whose ``n`` attributes build the reference path.
    divs: tuple[str, ...] = ("book",)
    #: "line" for verse (leaves are ``<l>``), "section" for prose (leaves are milestones).
    leaf: str = "line"
    #: For prose: the milestone unit that extends the reference path, then the leaf unit.
    milestones: tuple[str, ...] = ()
    #: How a citation reads, e.g. "Aeneid 1.1" vs "BG 1.1.1".
    labels: tuple[str, ...] = ("book", "line")
    verse: bool = True


WORKS: tuple[Work, ...] = (
    # --- verse, book -> line ---
    Work("vergil.aeneid", "Vergil", "Aeneid", "Vergil/opensource/verg.a_lat.xml"),
    Work("vergil.georgics", "Vergil", "Georgics", "Vergil/opensource/verg.g_lat.xml"),
    Work("vergil.eclogues", "Vergil", "Eclogues", "Vergil/opensource/verg.ecl_lat.xml",
         divs=("poem",), labels=("poem", "line")),
    Work("ovid.metamorphoses", "Ovid", "Metamorphoses", "Ovid/opensource/ovid.met_lat.xml"),
    # --- verse, book -> poem -> line ---
    Work("horace.odes", "Horace", "Odes", "Horace/opensource/hor.carm_lat.xml",
         divs=("book", "poem"), labels=("book", "poem", "line")),
    Work("horace.epodes", "Horace", "Epodes", "Horace/opensource/hor.epodes_lat.xml",
         divs=("poem",), labels=("poem", "line")),  # verse as <p>, not <l>
    Work("horace.satires", "Horace", "Satires", "Horace/opensource/hor.sat_lat.xml",
         divs=("book", "poem"), labels=("book", "poem", "line")),
    Work("horace.epistles", "Horace", "Epistles", "Horace/opensource/hor.epist_lat.xml",
         divs=("book", "poem"), labels=("book", "poem", "line")),
    Work("horace.ars", "Horace", "Ars Poetica", "Horace/opensource/hor.ap_lat.xml",
         divs=(), labels=("line",)),
    Work("catullus.carmina", "Catullus", "Carmina", "Catullus/opensource/cat_lat.xml",
         divs=("poem",), labels=("poem", "line")),
    # --- prose, book -> chapter -> section, marked by milestones ---
    Work("caesar.bg", "Caesar", "De Bello Gallico", "Caesar/opensource/caes.bg_lat.xml",
         divs=("book",), leaf="section", milestones=("chapter", "section"),
         labels=("book", "chapter", "section"), verse=False),
    # BC marks chapters as divs where BG marks them as milestones -- same author, same
    # publisher, different decade of digitisation.
    # Cicero's orations: sections run continuously through each speech, which is exactly
    # how they are cited (*Cat.* 1.4 is speech 1, section 4). Chapters are an older parallel
    # division and are ignored for citation.
    Work("cicero.catilinam", "Cicero", "In Catilinam", "Cicero/opensource/cic.oct1_lat.xml",
         divs=("speech",), leaf="section", milestones=("section",),
         labels=("speech", "section"), verse=False),
    Work("cicero.philippics", "Cicero", "Philippics", "Cicero/opensource/cic.oct2_lat.xml",
         divs=("speech",), leaf="section", milestones=("section",),
         labels=("speech", "section"), verse=False),
    Work("cicero.agraria", "Cicero", "De Lege Agraria", "Cicero/opensource/cic.oct4_lat.xml",
         divs=("speech",), leaf="section", milestones=("section",),
         labels=("speech", "section"), verse=False),
    Work("caesar.bc", "Caesar", "De Bello Civili", "Caesar/opensource/caes.bc_lat.xml",
         divs=("book", "chapter"), leaf="section", milestones=("section",),
         labels=("book", "chapter", "section"), verse=False),
)


def work_by_key(key: str) -> Work | None:
    return next((w for w in WORKS if w.key == key), None)


@dataclass
class Unit:
    """One addressable chunk of text: a verse line, or a prose section."""

    ref: tuple[int, ...]   # the citation path above the leaf, e.g. (1,) or (1, 5)
    leaf: int              # line number, or section number
    text: str


def _num(value: str | None) -> int | None:
    if not value:
        return None
    m = re.match(r"\d+", value.strip())
    return int(m.group()) if m else None


def _iter_divs(root: ET.Element, types: tuple[str, ...]) -> Iterator[tuple[tuple[int, ...], ET.Element]]:
    """Walk the div hierarchy named by ``types``, yielding (ref path so far, element).

    Perseus capitalises div types inconsistently (``book`` vs ``Book`` vs ``Poem``), so the
    comparison is case-insensitive throughout.
    """
    if not types:
        yield (), root
        return

    def rec(el: ET.Element, depth: int, path: tuple[int, ...]) -> Iterator:
        want = types[depth].lower()
        found = False
        for child in el.iter():
            if child is el or not child.tag.startswith("div"):
                continue
            if (child.get("type") or "").lower() != want:
                continue
            n = _num(child.get("n"))
            if n is None:
                continue
            found = True
            new_path = path + (n,)
            if depth + 1 == len(types):
                yield new_path, child
            else:
                yield from rec(child, depth + 1, new_path)
        if not found and depth == 0:
            return

    yield from rec(root, 0, ())


def _text_of(el: ET.Element) -> str:
    parts: list[str] = []
    for node in el.iter():
        if node.tag in ("note", "pb", "milestone", "gap", "bibl"):
            # Keep the tail: text following a milestone is part of the running text.
            if node.tail:
                parts.append(node.tail)
            continue
        if node.text:
            parts.append(node.text)
        if node.tail:
            parts.append(node.tail)
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _verse_units(root: ET.Element, w: Work) -> Iterator[Unit]:
    for path, div in _iter_divs(root, w.divs):
        lines = list(div.iter("l"))
        if not lines:
            # Horace's *Epodes* and *Epistles* are printed as <p> with the verses separated
            # by newlines rather than tagged as <l>. The line breaks are the only markup
            # there is, so they are what gets counted.
            counter = 0
            for para in div.iter("p"):
                for raw in "".join(para.itertext()).split("\n"):
                    text = raw.strip()
                    if text:
                        counter += 1
                        yield Unit(path, counter, text)
            continue
        counter = 0
        for el in lines:
            counter += 1
            n = _num(el.get("n"))
            if n is not None:
                # Perseus numbers only every fifth line; snapping to each anchor fills the
                # gaps and catches drift.
                counter = n
            text = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
            if text:
                yield Unit(path, counter, text)


def _prose_units(root: ET.Element, w: Work) -> Iterator[Unit]:
    """Prose whose subdivisions are milestones punctuating a flat stream.

    A section's text is everything between its milestone and the next, so the only way to
    recover it is to walk in document order and accumulate. Two shapes occur: *BG* marks
    both chapter and section as milestones, while *BC* makes the chapter a div and leaves
    only the section as a milestone.
    """
    leaf_unit = w.milestones[-1] if w.milestones else "section"
    path_unit = w.milestones[0] if len(w.milestones) > 1 else None

    for path, div in _iter_divs(root, w.divs):
        state = {"extra": None, "leaf": 1, "buf": []}

        def flush() -> Iterator[Unit]:
            text = re.sub(r"\s+", " ", "".join(state["buf"])).strip()
            state["buf"] = []
            if not text:
                return
            ref = path + ((state["extra"],) if state["extra"] is not None else ())
            if path_unit is not None and state["extra"] is None:
                return
            yield Unit(ref, state["leaf"] or 1, text)

        for node in div.iter():
            if node.tag == "milestone":
                unit = (node.get("unit") or "").lower()
                if unit in (leaf_unit, path_unit or ""):
                    yield from flush()
                    raw = node.get("n") or ""
                    n = _num(raw)
                    if path_unit is not None and unit == path_unit:
                        state["extra"], state["leaf"] = n, 1
                    elif "." in raw and path_unit is not None:
                        # BG writes section milestones as "chapter.section".
                        a, _, b = raw.partition(".")
                        state["extra"] = _num(a) or state["extra"]
                        state["leaf"] = _num(b) or 1
                    else:
                        state["leaf"] = n or 1
                if node.tail:
                    state["buf"].append(node.tail)
                continue
            if node.tag in ("note", "pb", "gap", "bibl", "head"):
                if node.tail:
                    state["buf"].append(node.tail)
                continue
            if node.text:
                state["buf"].append(node.text)
            if node.tail:
                state["buf"].append(node.tail)
        yield from flush()


def extract_units(source_dir: Path, w: Work) -> list[Unit]:
    path = source_dir / w.filename
    if not path.exists():
        return []
    # Walk the whole document rather than the first <text>/<body>. Perseus splits some
    # files into one <text> per speech -- cic.oct1 has seven, and none of the four
    # Catilinarians is in the first -- so stopping at the first body silently yielded
    # nothing at all. The header carries no div elements, so including it is harmless.
    root = ET.fromstring(_readable_xml(path))
    return list(_verse_units(root, w) if w.verse else _prose_units(root, w))


def format_citation(w: Work, ref: tuple[int, ...], leaf: int, leaf_end: int | None = None) -> str:
    """Render a citation the way a classicist writes it."""
    parts = [str(x) for x in ref] + [str(leaf)]
    cite = ".".join(parts)
    if leaf_end is not None and leaf_end != leaf:
        cite += f"-{leaf_end}"
    return f"{w.author}, {w.title} {cite}"

"""Editorial commentary, keyed to the line it comments on.

Perseus publishes Servius and Conington on the *Aeneid* in TEI P4 where every note is a
``<div2 type="commline" n="LINE">`` inside a ``<div1 type="book" n="BOOK">``. That means a
note's address is literally ``(book, line)`` -- the same key that identifying a passage
produces -- so no alignment heuristics, fuzzy matching or scraping is needed. Parse once
into SQLite and look notes up by position.

Servius (fl. c. 400) is the ancient commentary: a grammarian's line-by-line exposition that
preserves Republican scholarship and a great deal of Roman religion, antiquarian lore and
etymology found nowhere else. Conington (1863) is the standard Victorian English commentary.
Between them a reader gets both the ancient and the modern view of the same line.

Two things about the source files complicate parsing, and both are handled here:

- The TEI declares entities in an external Perseus DTD (``&responsibility;``, ``&fund.NEH;``)
  that are not resolvable offline, so a strict parser fails on the first one.
- Conington addresses notes to line *ranges* (``n="1-7"``) as well as single lines, and uses
  ``type="Book"`` where Servius uses ``type="book"``.

Licence: the underlying texts are public domain; Perseus's TEI markup is CC BY-SA 3.0, so
the database built from it is redistributable under the same terms. It is written to
``data/`` and not vendored.
"""

from __future__ import annotations

import re
import sqlite3
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from xml.etree import ElementTree as ET

__all__ = ["ingest", "notes_for", "commentary_db", "SOURCES"]


@dataclass(frozen=True)
class Source:
    key: str
    author: str
    work: str
    language: str
    filename: str
    #: div ``type`` values, outermost first, whose ``n`` values build the reference path.
    #: Compared case-insensitively: Perseus writes both ``book`` and ``Book``.
    divs: tuple[str, ...] = ("book",)
    #: "commline" -- notes addressed to a verse line, the usual shape.
    #: "lemma-prose" -- a prose chapter whose glossed words are tagged <lemma>, which is how
    #: Allen & Greenough's Caesar is marked up. Those notes attach to a word, not a line.
    style: str = "commline"


SOURCES: tuple[Source, ...] = (
    # Vergil -- the ancient commentary and the standard Victorian one.
    Source("servius-aen", "Servius", "vergil.aeneid", "la",
           "Vergil/opensource/serv.verg.aen_lat.xml"),
    Source("servius-ecl", "Servius", "vergil.eclogues", "la",
           "Vergil/opensource/serv.verg.ecl_lat.xml", divs=("poem",)),
    Source("servius-geo", "Servius", "vergil.georgics", "la",
           "Vergil/opensource/serv.verg.georg_lat.xml"),
    Source("conington-aen1", "Conington", "vergil.aeneid", "en",
           "Vergil/opensource/c.verg.aen1_eng.xml"),
    Source("conington-aen2", "Conington", "vergil.aeneid", "en",
           "Vergil/opensource/c.verg.aen2_eng.xml"),
    # Horace: Shorey on the Odes, addressed book.poem.line.
    Source("shorey-horace", "Shorey", "horace.odes", "en",
           "Horace/opensource/shore.hor_eng.xml", divs=("book", "poem")),
    # Catullus: Merrill, addressed poem.line.
    Source("merrill-catullus", "Merrill", "catullus.carmina", "en",
           "Catullus/opensource/merrill.cat_eng.xml", divs=("poem",)),
    # Caesar: Allen & Greenough, glossing word by word within each chapter, with their own
    # grammar's section numbers cited inline -- the same grammar this project cites.
    Source("ag-caesar-bg", "Allen & Greenough", "caesar.bg", "en",
           "Caesar/opensource/ag.caes.bg_eng.xml", divs=("book", "chapter"),
           style="lemma-prose"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS note (
    id          INTEGER PRIMARY KEY,
    source      TEXT NOT NULL,
    author      TEXT NOT NULL,
    work        TEXT NOT NULL,
    language    TEXT NOT NULL,
    -- Citation path above the line: "1" for Aeneid book 1, "1.5" for Odes 1.5,
    -- "1.1" for BG book 1 chapter 1.
    ref         TEXT NOT NULL,
    line_start  INTEGER,
    line_end    INTEGER,
    lemma       TEXT,
    grammar     TEXT,
    text        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS note_loc ON note (work, ref, line_start, line_end);
CREATE INDEX IF NOT EXISTS note_lemma ON note (work, lemma);
"""


def _readable_xml(path: Path) -> str:
    """Strip the unresolvable DTD and any entity it would have defined."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"<!DOCTYPE.*?\]>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"<!DOCTYPE[^>]*>", "", raw)
    # Keep the five XML built-ins and numeric references; drop Perseus's own.
    raw = re.sub(
        r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9A-Fa-f]+);)[A-Za-z._][\w.-]*;", "", raw
    )
    return raw


def _text_of(el: ET.Element) -> str:
    """Flatten an element to readable prose, dropping editorial scaffolding."""
    parts: list[str] = []
    for node in el.iter():
        if node.tag in ("pb", "milestone", "anchor", "delSpan", "gap"):
            continue
        # Separate every node's contents from its neighbours. Concatenating them directly
        # welded quotations to the words around them -- "arma virumque ferens.arma acri" --
        # because the markup carries no whitespace across element boundaries.
        if node.text:
            parts.append(node.text)
            parts.append(" ")
        if node.tail:
            parts.append(node.tail)
            parts.append(" ")
    text = unicodedata.normalize("NFC", "".join(parts))
    text = re.sub(r"\s+", " ", text)
    # Undo the spaces that landed before punctuation or inside quotes.
    text = re.sub(r"\s+([,.;:!?\)\]])", r"\1", text)
    text = re.sub(r"([\(\[])\s+", r"\1", text)
    text = re.sub(r"\s+'\s*(.*?)\s*'", r" '\1'", text)
    return text.strip()


def _lemma_of(el: ET.Element) -> str:
    """The word or phrase the note is about.

    Servius marks it ``<hi rend="caps">arma</hi>`` at the head of the note, which is what
    lets a note attach to a single token rather than only to a line.
    """
    for hi in el.iter("hi"):
        if hi.get("rend") in ("caps", "CAPS") and hi.text:
            # Editions bracket supplements and mark line ends inside the lemma itself
            # ("regina]"), which must not become part of the headword.
            return re.sub(r"\s+", " ", hi.text).strip().strip("[](){}.,;:\u2020*").lower()
    return ""


def _parse_n(n: str) -> tuple[int | None, int | None]:
    """Read a ``n`` attribute: ``"12"``, ``"1-7"``, or something unnumbered like ``"pr"``."""
    if not n:
        return None, None
    m = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", n.strip())
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"^(\d+)", n.strip())
    if m:
        v = int(m.group(1))
        return v, v
    return None, None


def _ref_of(el, parents: dict, divs: tuple[str, ...]) -> tuple[int, ...] | None:
    """The citation path of an element, read from its div ancestors."""
    want = [d.lower() for d in divs]
    found: dict[str, int] = {}
    cur = parents.get(el)
    while cur is not None:
        if cur.tag.startswith("div"):
            t = (cur.get("type") or "").lower()
            if t in want:
                n = _parse_n(cur.get("n", ""))[0]
                if n is not None and t not in found:
                    found[t] = n
        cur = parents.get(cur)
    if len(found) != len(want):
        return None
    return tuple(found[t] for t in want)


def _commline_notes(src: Source, root) -> Iterator[tuple]:
    parents = {c: p for p in root.iter() for c in p}
    for el in root.iter():
        if (el.get("type") or "").lower() != "commline":
            continue
        ref = _ref_of(el, parents, src.divs)
        if ref is None:
            continue
        start, end = _parse_n(el.get("n", ""))
        text = _text_of(el)
        if not text:
            continue
        yield (src.key, src.author, src.work, src.language,
               ".".join(str(x) for x in ref), start, end, _lemma_of(el), "", text)


def _lemma_prose_notes(src: Source, root) -> Iterator[tuple]:
    """Split a prose chapter into one note per glossed word.

    Allen & Greenough tag every word they discuss as ``<lemma>``, so a chapter's commentary
    is really a sequence of word-notes run together in a paragraph. Splitting on the lemma
    boundaries recovers them, which lets a note attach to the token a reader clicked rather
    than to the whole chapter. ``<bibl n="AG 495">`` references are kept: they point into
    the same grammar this project cites everywhere else.
    """
    parents = {c: p for p in root.iter() for c in p}
    for chapter in root.iter():
        if (chapter.get("type") or "").lower() != src.divs[-1].lower():
            continue
        ref = _ref_of(chapter, parents, src.divs[:-1])
        n = _parse_n(chapter.get("n", ""))[0]
        if ref is None or n is None:
            # Allen & Greenough uses <div1 type="chapter"> for its own introductory chapters
            # as well as <div2 type="Chapter"> for Caesar's. Only the latter sits under a
            # Book, so requiring the reference to resolve tells them apart.
            continue
        full_ref = ".".join(str(x) for x in (ref + (n,)))

        for para in chapter.iter("p"):
            current: str | None = None
            buf: list[str] = []
            refs: list[str] = []

            def emit():
                text = re.sub(r"\s+", " ", "".join(buf))
                text = re.sub(r"\s+([,.;:])", r"\1", text)
                # Dropping <bibl> elements leaves their separators behind: ";;;".
                text = re.sub(r"([,;:])\s*(?=[,;:])", "", text)
                text = re.sub(r"\s{2,}", " ", text).strip(" ,;:")
                if current and len(text) > 2:
                    return (src.key, src.author, src.work, src.language, full_ref,
                            None, None, current.lower().strip(" ,.:"),
                            ", ".join(dict.fromkeys(refs)), text)
                return None

            for node in para.iter():
                if node.tag == "lemma":
                    row = emit()
                    if row:
                        yield row
                    current = "".join(node.itertext()).strip()
                    buf, refs = [], []
                    if node.tail:
                        buf.append(node.tail)
                    continue
                if node.tag == "bibl":
                    label = (node.get("n") or "").strip()
                    if label:
                        refs.append(label)
                    if node.tail:
                        buf.append(node.tail)
                    continue
                if node.tag in ("pb", "milestone", "anchor", "gap"):
                    if node.tail:
                        buf.append(node.tail)
                    continue
                if node.text:
                    buf.append(node.text)
                    buf.append(" ")
                if node.tail:
                    buf.append(node.tail)
                    buf.append(" ")
            row = emit()
            if row:
                yield row


def _notes(src: Source, path: Path) -> Iterator[tuple]:
    # Walk the whole document, not text/body. Several of these files contain more than one
    # <text> element -- Allen & Greenough's Caesar has one per book -- so finding the first
    # body and stopping there silently lost 332 of its 341 chapters, and all of Merrill's
    # Catullus. The header carries no div elements, so including it costs nothing.
    root = ET.fromstring(_readable_xml(path))
    if src.style == "lemma-prose":
        yield from _lemma_prose_notes(src, root)
    else:
        yield from _commline_notes(src, root)


def commentary_db(path: Path | None = None) -> Path:
    return path or Path(__file__).resolve().parents[2] / "data" / "commentary.db"


def ingest(hopper_dir: Path, db_path: Path | None = None) -> dict[str, int]:
    """Build the commentary database. Returns note counts per source."""
    db_path = commentary_db(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    counts: dict[str, int] = {}
    for src in SOURCES:
        path = hopper_dir / src.filename
        if not path.exists():
            counts[src.key] = 0
            continue
        conn.execute("DELETE FROM note WHERE source = ?", (src.key,))
        rows = list(_notes(src, path))
        conn.executemany(
            "INSERT INTO note (source, author, work, language, ref, line_start, "
            "line_end, lemma, grammar, text) VALUES (?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
        counts[src.key] = len(rows)
    conn.commit()
    conn.close()
    return counts


def notes_for(
    work: str,
    ref: str,
    line: int | None = None,
    db_path: Path | None = None,
    limit: int = 12,
    lemma: str | None = None,
) -> list[dict]:
    """Every note bearing on one place in a text.

    ``ref`` is the citation path above the line -- "1" for *Aeneid* book 1, "1.5" for *Odes*
    1.5, "1.1" for *BG* book 1 chapter 1. ``line`` selects a verse; prose notes carry no
    line and match on the reference alone. Ancient commentary is returned before modern, and
    word-level notes before line-level ones, because a reader who clicked a word wants the
    note about that word first.
    """
    db_path = commentary_db(db_path)
    if not db_path.exists():
        return []
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    sql = (
        "SELECT author, source, language, ref, line_start, line_end, lemma, grammar, text "
        "FROM note WHERE work = ? AND ref = ?"
    )
    args: list = [work, ref]
    if line is not None:
        # A prose note has no line at all and must not be excluded by a line filter.
        sql += " AND (line_start IS NULL OR (line_start <= ? AND line_end >= ?))"
        args += [line, line]
    if lemma:
        sql += " AND lemma = ?"
        args.append(lemma.lower())
    sql += (
        " ORDER BY CASE WHEN lemma <> '' THEN 0 ELSE 1 END,"
        " CASE WHEN language = 'la' THEN 0 ELSE 1 END, line_start LIMIT ?"
    )
    args.append(limit)
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return [
        {
            "author": r["author"], "source": r["source"], "language": r["language"],
            "ref": r["ref"], "lineStart": r["line_start"], "lineEnd": r["line_end"],
            "lemma": r["lemma"], "grammar": r["grammar"], "text": r["text"],
        }
        for r in rows
    ]


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "ingest":
        print("usage: python -m enarratio.commentary ingest <hopper opensource dir>")
        raise SystemExit(2)
    result = ingest(Path(sys.argv[2]).expanduser())
    for key, n in result.items():
        print(f"  {key:20} {n:6,} notes")
    print(f"  {'TOTAL':20} {sum(result.values()):6,}  ->  {commentary_db()}")

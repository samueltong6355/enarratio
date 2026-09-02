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
    #: Perseus is inconsistent here: Servius on the Aeneid and Georgics divides by
    #: ``type="book"``, Conington by ``type="Book"``, and the Eclogues -- which have poems
    #: rather than books -- by ``type="poem"``. All three are accepted.
    book_types: tuple[str, ...] = ("book", "Book", "poem")


SOURCES: tuple[Source, ...] = (
    Source("servius-aen", "Servius", "vergil.aeneid", "la", "serv.verg.aen_lat.xml"),
    Source("servius-ecl", "Servius", "vergil.eclogues", "la", "serv.verg.ecl_lat.xml"),
    Source("servius-geo", "Servius", "vergil.georgics", "la", "serv.verg.georg_lat.xml"),
    Source("conington-aen1", "Conington", "vergil.aeneid", "en", "c.verg.aen1_eng.xml"),
    Source("conington-aen2", "Conington", "vergil.aeneid", "en", "c.verg.aen2_eng.xml"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS note (
    id          INTEGER PRIMARY KEY,
    source      TEXT NOT NULL,
    author      TEXT NOT NULL,
    work        TEXT NOT NULL,
    language    TEXT NOT NULL,
    book        INTEGER,
    line_start  INTEGER,
    line_end    INTEGER,
    lemma       TEXT,
    text        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS note_loc ON note (work, book, line_start, line_end);
CREATE INDEX IF NOT EXISTS note_lemma ON note (lemma);
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
            return re.sub(r"\s+", " ", hi.text).strip().lower()
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


def _notes(src: Source, path: Path) -> Iterator[tuple]:
    root = ET.fromstring(_readable_xml(path))
    body = root.find(".//text/body")
    if body is None:
        body = root
    for div1 in body.iter("div1"):
        if div1.get("type") not in src.book_types:
            continue
        book, _ = _parse_n(div1.get("n", ""))
        for div2 in div1.iter("div2"):
            if div2.get("type") != "commline":
                continue
            start, end = _parse_n(div2.get("n", ""))
            text = _text_of(div2)
            if not text:
                continue
            yield (src.key, src.author, src.work, src.language,
                   book, start, end, _lemma_of(div2), text)


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
            "INSERT INTO note (source, author, work, language, book, line_start, "
            "line_end, lemma, text) VALUES (?,?,?,?,?,?,?,?,?)",
            rows,
        )
        counts[src.key] = len(rows)
    conn.commit()
    conn.close()
    return counts


def notes_for(
    work: str, book: int, line: int, db_path: Path | None = None, limit: int = 12
) -> list[dict]:
    """Every note bearing on one line, ancient commentary first."""
    db_path = commentary_db(db_path)
    if not db_path.exists():
        return []
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT author, source, language, book, line_start, line_end, lemma, text "
        "FROM note WHERE work = ? AND book = ? AND line_start <= ? AND line_end >= ? "
        # Servius before Conington: the ancient view first, then the modern.
        "ORDER BY CASE WHEN language = 'la' THEN 0 ELSE 1 END, line_start LIMIT ?",
        (work, book, line, line, limit),
    ).fetchall()
    conn.close()
    return [
        {
            "author": r["author"],
            "source": r["source"],
            "language": r["language"],
            "book": r["book"],
            "lineStart": r["line_start"],
            "lineEnd": r["line_end"],
            "lemma": r["lemma"],
            "text": r["text"],
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

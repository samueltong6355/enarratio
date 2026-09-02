"""Identifying a pasted excerpt and returning its canonical citation.

Without this, commentary is unreachable: Servius's note on *Aeneid* 1.1 is addressed to
``(book 1, line 1)``, and a pasted passage carries no address at all. This module supplies
the missing key.

The method is a hashed word-*n*-gram inverted index over a normalised token stream, which
the research measured against the alternatives and preferred to FTS5, MinHash/LSH and
embeddings alike -- all of which are heavier and none of which is more accurate on this
problem. It works because the task is not fuzzy semantic search but near-exact matching of
a quotation against a corpus, where the only real obstacle is orthography.

Normalisation absorbs that obstacle: case, macrons, *j/v*, ligatures, punctuation and
editorial brackets all disappear before hashing, so a student pasting *Lāvīniaque* from a
macronised school text matches Perseus's *Laviniaque*.

Alignment is what makes it precise. Every matching shingle votes not for a work but for an
*offset alignment* -- if query token 0 corresponds to corpus token 4,312, then every other
shingle should agree. A run of consistent votes is a real match; scattered votes are the
coincidental reuse of a common phrase, and are rejected.
"""

from __future__ import annotations

import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from .commentary import _readable_xml

__all__ = ["build_index", "identify", "index_db", "WORKS"]

#: Five words is long enough that a shingle is nearly unique in a corpus this size, and
#: short enough that a two-line paste still yields several.
N = 5


@dataclass(frozen=True)
class Work:
    key: str
    author: str
    title: str
    filename: str
    #: How the citation reads: the Aeneid has books, the Eclogues poems.
    unit: str = "book"


WORKS: tuple[Work, ...] = (
    Work("vergil.aeneid", "Vergil", "Aeneid", "verg.a_lat.xml"),
    Work("vergil.eclogues", "Vergil", "Eclogues", "verg.ecl_lat.xml", unit="poem"),
    Work("vergil.georgics", "Vergil", "Georgics", "verg.g_lat.xml"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS work (
    id INTEGER PRIMARY KEY, key TEXT UNIQUE, author TEXT, title TEXT, unit TEXT
);
CREATE TABLE IF NOT EXISTS loc (
    work_id INTEGER, tok_offset INTEGER, book INTEGER, line INTEGER
);
CREATE TABLE IF NOT EXISTS shingle (
    hash INTEGER, work_id INTEGER, tok_offset INTEGER
);
CREATE INDEX IF NOT EXISTS shingle_hash ON shingle (hash);
CREATE INDEX IF NOT EXISTS loc_off ON loc (work_id, tok_offset);
"""


def normalise(text: str) -> list[str]:
    """Reduce to the token stream both sides of the comparison can agree on."""
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.replace("æ", "ae").replace("œ", "oe")
    t = t.replace("j", "i").replace("v", "u")
    t = re.sub(r"[^a-z\s]", " ", t)
    return t.split()


def _hash(words: Iterable[str]) -> int:
    """A stable 63-bit hash. Python's own is salted per process and unusable here."""
    h = 1469598103934665603
    for w in words:
        for b in w.encode():
            h = ((h ^ b) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
        h = ((h ^ 0x20) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h & 0x7FFFFFFFFFFFFFFF


def _lines_of(path: Path, unit: str) -> list[tuple[int, int, str]]:
    """(book, line, text) for every verse, numbering by position.

    Perseus marks only every fifth line with ``n``, so lines are counted sequentially and
    the counter is snapped to each anchor it meets -- which both fills in the gaps and
    catches any drift.
    """
    root = ET.fromstring(_readable_xml(path))
    out: list[tuple[int, int, str]] = []
    for div in root.iter("div1"):
        if div.get("type", "").lower() not in (unit, "book", "poem"):
            continue
        book = int(re.match(r"\d+", div.get("n", "") or "0").group()) if re.match(r"\d+", div.get("n", "") or "") else None
        if book is None:
            continue
        counter = 0
        for el in div.iter("l"):
            counter += 1
            n = el.get("n")
            if n and n.isdigit():
                counter = int(n)
            text = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
            if text:
                out.append((book, counter, text))
    return out


def index_db(path: Path | None = None) -> Path:
    return path or Path(__file__).resolve().parents[2] / "data" / "passages.db"


def build_index(source_dir: Path, db_path: Path | None = None) -> dict[str, int]:
    db_path = index_db(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    counts: dict[str, int] = {}
    for w in WORKS:
        path = source_dir / w.filename
        if not path.exists():
            counts[w.key] = 0
            continue
        conn.execute(
            "INSERT OR IGNORE INTO work (key, author, title, unit) VALUES (?,?,?,?)",
            (w.key, w.author, w.title, w.unit),
        )
        wid = conn.execute("SELECT id FROM work WHERE key = ?", (w.key,)).fetchone()[0]
        conn.execute("DELETE FROM shingle WHERE work_id = ?", (wid,))
        conn.execute("DELETE FROM loc WHERE work_id = ?", (wid,))

        stream: list[str] = []
        locs: list[tuple[int, int, int, int]] = []
        for book, line, text in _lines_of(path, w.unit):
            locs.append((wid, len(stream), book, line))
            stream.extend(normalise(text))
        conn.executemany("INSERT INTO loc VALUES (?,?,?,?)", locs)
        conn.executemany(
            "INSERT INTO shingle VALUES (?,?,?)",
            ((_hash(stream[i : i + N]), wid, i) for i in range(len(stream) - N + 1)),
        )
        counts[w.key] = len(stream)
    conn.commit()
    conn.close()
    return counts


def identify(text: str, db_path: Path | None = None, min_votes: int = 3) -> dict | None:
    """Locate a passage, or return None if it is not confidently in the corpus.

    Returning nothing is the right answer far more often than not -- most pasted Latin is
    not one of the indexed works -- so the threshold is deliberately unforgiving.
    """
    db_path = index_db(db_path)
    if not db_path.exists():
        return None
    words = normalise(text)
    if len(words) < N:
        return None
    hashes = [(i, _hash(words[i : i + N])) for i in range(len(words) - N + 1)]

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    votes: Counter[tuple[int, int]] = Counter()
    for i, h in hashes:
        for r in conn.execute(
            "SELECT work_id, tok_offset FROM shingle WHERE hash = ?", (h,)
        ):
            # Vote for the alignment, not merely the work: a genuine match agrees on where
            # the excerpt begins, whereas a common phrase reused elsewhere does not.
            votes[(r["work_id"], r["tok_offset"] - i)] += 1
    if not votes:
        conn.close()
        return None

    ranked = votes.most_common(2)
    (wid, base), n_votes = ranked[0]
    possible = len(hashes)

    # A short excerpt cannot clear a fixed vote floor: a single hexameter of five words
    # yields exactly one shingle. But one five-word phrase occurring in exactly one place
    # in the corpus is strong evidence on its own, so when the evidence is necessarily thin
    # the test becomes uniqueness instead of volume -- the winning alignment must be the
    # only one. A phrase common enough to appear twice produces a tie and is rejected.
    if possible < min_votes:
        if len(ranked) > 1 and ranked[1][1] >= n_votes:
            conn.close()
            return None
    elif n_votes < min_votes:
        conn.close()
        return None

    work = conn.execute("SELECT * FROM work WHERE id = ?", (wid,)).fetchone()
    start = conn.execute(
        "SELECT book, line FROM loc WHERE work_id = ? AND tok_offset <= ? "
        "ORDER BY tok_offset DESC LIMIT 1", (wid, base)
    ).fetchone()
    end = conn.execute(
        "SELECT book, line FROM loc WHERE work_id = ? AND tok_offset <= ? "
        "ORDER BY tok_offset DESC LIMIT 1", (wid, base + len(words) - 1)
    ).fetchone()
    conn.close()
    if start is None:
        return None

    return {
        "work": work["key"],
        "author": work["author"],
        "title": work["title"],
        "unit": work["unit"],
        "book": start["book"],
        "lineStart": start["line"],
        "lineEnd": (end or start)["line"],
        "confidence": round(min(1.0, n_votes / possible), 3),
        "matchedShingles": n_votes,
        "possibleShingles": possible,
        "citation": (
            f"{work['author']}, {work['title']} {start['book']}.{start['line']}"
            + (f"-{end['line']}" if end and end["line"] != start["line"] else "")
        ),
    }


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "build":
        print("usage: python -m enarratio.identify build <perseus opensource dir>")
        raise SystemExit(2)
    for key, n in build_index(Path(sys.argv[2]).expanduser()).items():
        print(f"  {key:22} {n:7,} tokens indexed")
    print(f"  -> {index_db()}")

"""Indexing The Latin Library for passage identification.

The Latin Library (thelatinlibrary.com) is a plain-text archive of Latin literature,
released under a Public Domain Mark. It is worth being clear about what it is and is not:
it carries **no commentary, no notes and no editorial apparatus at all** -- only the texts.
So it cannot extend Enarratio's commentary; what it extends is *reach*, letting the tool
name a passage from far more of the canon than Perseus's curated TEI covers.

Its markup is minimal, which sets the limits of the citation it can support:

- Prose files often carry ``[ 1 ]`` chapter markers, which give a real chapter reference.
- Verse files carry none, so lines are counted from the top of the file. That is accurate
  where the file is a whole book and the text is complete, and it is the reason these
  citations are reported at lower confidence than the Perseus ones.
- Where a work is already indexed from Perseus, that version wins: it has real line
  numbers, and commentary hangs off it.

Only the classical authors are indexed. The full archive runs to 13.7 million words, which
would produce an index several gigabytes wide for a marginal gain -- the medieval and
neo-Latin material is rarely what a student is translating.
"""

from __future__ import annotations

import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from .identify import _hash, N, index_db, normalise

__all__ = ["index_latin_library", "CLASSICAL_AUTHORS"]

#: Author directories worth the index space. Names are The Latin Library's own.
CLASSICAL_AUTHORS = (
    "caesar", "cicero", "vergil", "ovid", "horace", "catullus", "livy", "tacitus",
    "sallust", "lucretius", "juvenal", "martial", "seneca", "propertius", "tibullus",
    "persius", "lucan", "statius", "plautus", "terence", "quintilian", "pliny",
    "suetonius", "nepos", "curtius", "apuleius", "gellius", "ammianus", "columella",
    "varro", "vitruvius", "frontinus", "justin", "florus", "valeriusmaximus",
    "sen",  # Seneca, filed under the abbreviation
)

#: Some authors are not directories at all but loose files at the archive root, named by a
#: prefix. Sallust is the notable classical case.
ROOT_FILE_AUTHORS = {
    "sall": "Sallust", "prop": "Propertius", "tib": "Tibullus", "pers": "Persius",
    "quintilian": "Quintilian", "manilius": "Manilius", "silius": "Silius Italicus",
    "valeriusflaccus": "Valerius Flaccus", "germanicus": "Germanicus",
}

#: Files that are apparatus rather than text.
SKIP_FILES = {"index", "contents", "readme", "license"}

#: The archive files a few authors under an abbreviation; show the real name.
DISPLAY_NAMES = {
    "sen": "Seneca", "vergil": "Vergil", "livy": "Livy", "sall": "Sallust",
    "valeriusmaximus": "Valerius Maximus", "curtius": "Curtius Rufus",
}


@dataclass
class LLUnit:
    ref: str
    leaf: int
    text: str


def _title_of(lines: list[str], fallback: str) -> str:
    for ln in lines[:6]:
        t = ln.strip()
        if len(t) > 3 and not t.isdigit():
            return re.sub(r"\s+", " ", t)[:90]
    return fallback


def _units(path: Path) -> tuple[str, list[LLUnit]]:
    """Split one file into addressable units, using chapter markers where they exist."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = [ln.strip() for ln in raw.splitlines()]
    content = [ln for ln in lines if len(ln.split()) > 2]
    if not content:
        return "", []
    title = _title_of(lines, path.stem)

    # The Latin Library writes chapter markers as "[ 1 ]" or "[1]" inline.
    if re.search(r"\[\s*\d+\s*\]", raw):
        units: list[LLUnit] = []
        chapter = 0
        buf: list[str] = []
        for ln in content[1:]:
            for piece in re.split(r"\[\s*(\d+)\s*\]", ln):
                if piece is None:
                    continue
                if piece.isdigit() and len(piece) <= 4:
                    if buf and chapter:
                        units.append(LLUnit(str(chapter), 1, " ".join(buf)))
                    chapter, buf = int(piece), []
                elif piece.strip():
                    buf.append(piece.strip())
        if buf and chapter:
            units.append(LLUnit(str(chapter), 1, " ".join(buf)))
        if units:
            return title, units

    # Otherwise treat each line as a unit, counted from the top. Skip the header line.
    return title, [LLUnit("", i + 1, ln) for i, ln in enumerate(content[1:])]


def index_latin_library(
    root: Path, db_path: Path | None = None, authors: tuple[str, ...] = CLASSICAL_AUTHORS
) -> dict[str, int]:
    """Add The Latin Library's classical texts to the passage index."""
    db_path = index_db(db_path)
    if not db_path.exists():
        raise SystemExit("Build the Perseus index first: python -m enarratio.identify build")
    conn = sqlite3.connect(db_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(work)")}
    if "source" not in cols:
        conn.execute("ALTER TABLE work ADD COLUMN source TEXT DEFAULT 'perseus'")
    conn.commit()

    def add_file(path: Path, author: str, key_prefix: str) -> int:
        if path.stem.lower() in SKIP_FILES:
            return 0
        title, units = _units(path)
        if not units:
            return 0
        key = f"ll.{key_prefix}.{path.stem}"
        conn.execute(
            "INSERT OR IGNORE INTO work (key, author, title, unit, source) "
            "VALUES (?,?,?,?,'latin_library')",
            (key, author, title, "line"),
        )
        row = conn.execute("SELECT id FROM work WHERE key = ?", (key,)).fetchone()
        if row is None:
            return 0
        wid = row[0]
        conn.execute("DELETE FROM shingle WHERE work_id = ?", (wid,))
        conn.execute("DELETE FROM loc WHERE work_id = ?", (wid,))
        stream: list[str] = []
        locs = []
        for u in units:
            locs.append((wid, len(stream), u.ref, u.leaf, u.text[:400]))
            stream.extend(normalise(u.text))
        conn.executemany("INSERT INTO loc VALUES (?,?,?,?,?)", locs)
        conn.executemany(
            "INSERT INTO shingle VALUES (?,?,?)",
            ((_hash(stream[i : i + N]), wid, i) for i in range(len(stream) - N + 1)),
        )
        return len(stream)

    counts: dict[str, int] = {}
    for prefix, author in ROOT_FILE_AUTHORS.items():
        total = sum(add_file(p, author, prefix)
                    for p in sorted(root.glob(f"{prefix}.*.txt")))
        if total:
            counts[author.lower()] = total

    for author in authors:
        adir = root / author
        if not adir.is_dir():
            continue
        total = 0
        for path in sorted(adir.glob("*.txt")):
            total += add_file(path, DISPLAY_NAMES.get(author, author.title()), author)

        if total:
            counts[author] = total
    conn.commit()
    conn.execute("ANALYZE")
    conn.close()
    return counts


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "build":
        print("usage: python -m enarratio.latinlibrary build <lat_text_latin_library dir>")
        raise SystemExit(2)
    result = index_latin_library(Path(sys.argv[2]).expanduser())
    for author, n in sorted(result.items(), key=lambda kv: -kv[1]):
        print(f"  {author:20} {n:9,} tokens")
    print(f"  {'TOTAL':20} {sum(result.values()):9,}  ->  {index_db()}")

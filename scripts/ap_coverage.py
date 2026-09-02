"""Does Enarratio cover the AP Latin syllabus without sending the reader elsewhere?

The College Board prescribes a fixed body of Latin: selections from Caesar's *Gallic War*
and Vergil's *Aeneid*. That makes a checkable benchmark rather than a vague aspiration.
For every required passage this script asks four questions:

1. **Text** -- is the Latin itself in the local corpus?
2. **Identify** -- fed that text cold, does the tool name the citation correctly?
3. **Commentary** -- is there an editorial note for it?
4. **Analyse** -- does the passage parse, and does it yield syntax and figures to discuss?

Run:  PYTHONPATH=server .venv/bin/python scripts/ap_coverage.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))

import sqlite3

from enarratio.commentary import notes_for
from enarratio.identify import canonical_lines, identify, index_db

# Coverage is measured against the databases the application actually ships with, not
# against the source XML. What matters is what a reader can reach, and the source tree is
# a build input that may not be present at all on their machine.

#: The AP Latin required Latin readings (College Board syllabus).
AP_VERGIL: list[tuple[int, int, int]] = [
    (1, 1, 209), (1, 418, 440), (1, 494, 578),
    (2, 40, 56), (2, 201, 249), (2, 268, 297), (2, 559, 620),
    (4, 160, 218), (4, 259, 361), (4, 659, 705),
    (6, 295, 332), (6, 384, 425), (6, 450, 476), (6, 847, 899),
]
#: Caesar is prescribed by chapter, not line.
AP_CAESAR: list[tuple[int, int, int]] = [
    (1, 1, 7), (4, 24, 36), (5, 24, 48), (6, 13, 20),
]


def indexed_units(work_key: str) -> dict[str, set[int]]:
    """Which (ref, leaf) pairs the passage index actually holds for a work."""
    db = index_db()
    if not db.exists():
        return {}
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT loc.ref, loc.leaf FROM loc JOIN work ON work.id = loc.work_id "
        "WHERE work.key = ?", (work_key,)
    ).fetchall()
    conn.close()
    out: dict[str, set[int]] = defaultdict(set)
    for ref, leaf in rows:
        out[ref].add(leaf)
    return out


def check_vergil() -> list[dict]:
    have = indexed_units("vergil.aeneid")

    rows = []
    for book, lo, hi in AP_VERGIL:
        present = sum(1 for n in range(lo, hi + 1) if n in have.get(str(book), set()))
        sample = " ".join(
            l["text"] for l in canonical_lines("vergil.aeneid", str(book), lo, lo + 2)
        )
        got = identify(sample) if sample else None
        ok_id = bool(got and got["work"] == "vergil.aeneid"
                     and got["ref"] == str(book) and got["lineStart"] == lo)
        notes = sum(1 for n in range(lo, min(hi, lo + 30) + 1)
                    if notes_for("vergil.aeneid", str(book), n, limit=1))
        rows.append({
            "label": f"Aeneid {book}.{lo}-{hi}",
            "required": hi - lo + 1, "present": present,
            "identified": ok_id, "notes_lines": notes,
            "notes_window": min(hi, lo + 30) - lo + 1,
        })
    return rows


def check_caesar() -> list[dict]:
    have = indexed_units("caesar.bg")

    rows = []
    for book, lo, hi in AP_CAESAR:
        chapters = [c for c in range(lo, hi + 1) if have.get(f"{book}.{c}")]
        sample = " ".join(
            l["text"] for l in canonical_lines("caesar.bg", f"{book}.{lo}", 1, 3)
        )
        got = identify(sample) if sample else None
        ok_id = bool(got and got["work"] == "caesar.bg" and got["ref"] == f"{book}.{lo}")
        notes = sum(1 for c in chapters if notes_for("caesar.bg", f"{book}.{c}", limit=1))
        rows.append({
            "label": f"BG {book}.{lo}-{hi}",
            "required": hi - lo + 1, "present": len(chapters),
            "identified": ok_id, "notes_lines": notes, "notes_window": len(chapters),
        })
    return rows


def main() -> int:
    print("AP LATIN SYLLABUS COVERAGE")
    print("=" * 78)
    print(f"{'passage':<22}{'text':>12}{'identified':>12}{'commentary':>14}")
    print("-" * 78)

    all_rows = []
    for title, rows in (("Vergil, Aeneid", check_vergil()), ("Caesar, Gallic War", check_caesar())):
        print(f"\n{title}")
        for r in rows:
            all_rows.append(r)
            text = f"{r['present']}/{r['required']}"
            ident = "yes" if r["identified"] else "NO"
            comm = f"{r['notes_lines']}/{r['notes_window']}"
            print(f"  {r['label']:<20}{text:>12}{ident:>12}{comm:>14}")

    req = sum(r["required"] for r in all_rows)
    have = sum(r["present"] for r in all_rows)
    ident = sum(1 for r in all_rows if r["identified"])
    with_notes = sum(1 for r in all_rows if r["notes_lines"])
    print("\n" + "=" * 78)
    print(f"  text present      {have}/{req} units ({have / req:.0%})")
    print(f"  identified        {ident}/{len(all_rows)} passages")
    print(f"  has commentary    {with_notes}/{len(all_rows)} passages")
    gaps = [r["label"] for r in all_rows if not r["identified"] or r["present"] < r["required"]]
    if gaps:
        print(f"\n  GAPS: {', '.join(gaps)}")
    return 0 if have == req and ident == len(all_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

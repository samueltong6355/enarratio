"""Passage identification and commentary lookup.

These tests need the built databases in `data/`; they skip cleanly without them, because
the data is large, separately licensed and deliberately not vendored (see scripts/build-data.sh).
"""

from __future__ import annotations

import pytest

from enarratio.commentary import commentary_db, notes_for
from enarratio.identify import identify, index_db, normalise

needs_index = pytest.mark.skipif(
    not index_db().exists(), reason="passages.db not built — run scripts/build-data.sh"
)
needs_commentary = pytest.mark.skipif(
    not commentary_db().exists(), reason="commentary.db not built — run scripts/build-data.sh"
)


def test_normalisation_collapses_orthography() -> None:
    """A student's macronised school text and Perseus's must reduce to the same stream."""
    assert normalise("Arma virumque canō") == normalise("ARMA VIRVMQVE CANO")
    assert normalise("Lāvīniaque") == normalise("Laviniaque")


@needs_index
@pytest.mark.parametrize(
    "text,work,book,line",
    [
        ("Arma virumque cano, Troiae qui primus ab oris", "vergil.aeneid", 1, 1),
        # Macrons, and all-caps V-for-U orthography, must land in the same place.
        ("Arma virumque canō, Trōiae quī prīmus ab ōrīs", "vergil.aeneid", 1, 1),
        ("ARMA VIRVMQVE CANO TROIAE QVI PRIMVS AB ORIS", "vergil.aeneid", 1, 1),
        ("Infandum, regina, iubes renovare dolorem", "vergil.aeneid", 2, 3),
        ("Tityre, tu patulae recubans sub tegmine fagi", "vergil.eclogues", 1, 1),
        ("Quid faciat laetas segetes, quo sidere terram", "vergil.georgics", 1, 1),
    ],
)
def test_identifies(text: str, work: str, book: int, line: int) -> None:
    r = identify(text)
    assert r is not None, f"failed to identify {text!r}"
    assert (r["work"], r["book"], r["lineStart"]) == (work, book, line)


@needs_index
@pytest.mark.parametrize(
    "text",
    [
        "Gallia est omnis divisa in partes tres, quarum unam incolunt Belgae",
        "Quo usque tandem abutere, Catilina, patientia nostra",
        "In principio erat Verbum, et Verbum erat apud Deum",
    ],
)
def test_declines_to_guess(text: str) -> None:
    """Most pasted Latin is not in the corpus. Saying nothing is the right answer."""
    assert identify(text) is None


@needs_index
def test_too_short_is_not_identified() -> None:
    assert identify("Arma virumque") is None


@needs_commentary
def test_servius_on_the_first_line_of_the_aeneid() -> None:
    notes = notes_for("vergil.aeneid", 1, 1)
    assert notes, "expected commentary on Aeneid 1.1"
    servius = next(n for n in notes if n["author"] == "Servius")
    assert servius["lemma"] == "arma"
    # The substance of the note: arma stands for war by metonymy.
    assert "metonymia" in servius["text"]
    # Ancient commentary is ordered before modern.
    assert notes[0]["author"] == "Servius"


@needs_commentary
def test_flattened_text_is_readable() -> None:
    """Element boundaries must not weld words together ('ferens.arma acri')."""
    text = notes_for("vergil.aeneid", 1, 1)[0]["text"]
    import re

    assert not re.search(r"[a-z]\.[a-z]{2,}", text), "words welded across element boundary"
    assert " ," not in text and " ." not in text

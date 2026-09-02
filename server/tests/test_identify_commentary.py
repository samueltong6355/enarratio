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
    "text,work,ref,line",
    [
        ("Arma virumque cano, Troiae qui primus ab oris", "vergil.aeneid", "1", 1),
        # Macrons, and all-caps V-for-U orthography, must land in the same place.
        ("Arma virumque canō, Trōiae quī prīmus ab ōrīs", "vergil.aeneid", "1", 1),
        ("ARMA VIRVMQVE CANO TROIAE QVI PRIMVS AB ORIS", "vergil.aeneid", "1", 1),
        ("Infandum, regina, iubes renovare dolorem", "vergil.aeneid", "2", 3),
        # volnus is the archaic spelling Perseus prints; a modern text reads vulnus.
        ("At regina gravi iamdudum saucia cura vulnus alit venis", "vergil.aeneid", "4", 1),
        ("Tityre, tu patulae recubans sub tegmine fagi", "vergil.eclogues", "1", 1),
        ("Quid faciat laetas segetes, quo sidere terram", "vergil.georgics", "1", 1),
        # The four AP Latin Caesar selections.
        ("Gallia est omnis divisa in partes tres, quarum unam incolunt Belgae",
         "caesar.bg", "1.1", 1),
        ("At barbari consilio Romanorum cognito praemisso equitatu et essedariis",
         "caesar.bg", "4.24", 1),
        ("Subductis navibus concilioque Gallorum Samarobrivae peracto", "caesar.bg", "5.24", 1),
        ("In omni Gallia eorum hominum qui aliquo sunt numero atque honore genera sunt duo",
         "caesar.bg", "6.13", 1),
        # Lyric, cited book.poem.line.
        ("Tu ne quaesieris, scire nefas, quem mihi, quem tibi", "horace.odes", "1.11", 1),
        ("Exegi monumentum aere perennius regalique situ", "horace.odes", "3.30", 1),
        ("Vivamus mea Lesbia atque amemus", "catullus.carmina", "5", 1),
        ("In nova fert animus mutatas dicere formas", "ovid.metamorphoses", "1", 1),
        # Cicero's orations, cited speech.section as the editions cite them.
        ("Quo usque tandem abutere, Catilina, patientia nostra", "cicero.catilinam", "1", 1),
        ("O tempora, o mores! Senatus haec intellegit, consul videt",
         "cicero.catilinam", "1", 2),
    ],
)
def test_identifies(text: str, work: str, ref: str, line: int) -> None:
    r = identify(text)
    assert r is not None, f"failed to identify {text!r}"
    assert (r["work"], r["ref"], r["lineStart"]) == (work, ref, line)


@needs_index
@pytest.mark.parametrize(
    "text",
    [
        "In principio erat Verbum, et Verbum erat apud Deum",
        "Respondeo dicendum quod necesse est dicere omne quod quocumque modo est",
        "Computatrum meum electronicum interretialiter cum aliis computatris communicat",
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
    notes = notes_for("vergil.aeneid", "1", 1)
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
    text = notes_for("vergil.aeneid", "1", 1)[0]["text"]
    import re

    assert not re.search(r"[a-z]\.[a-z]{2,}", text), "words welded across element boundary"
    assert " ," not in text and " ." not in text


@needs_commentary
def test_caesar_notes_are_word_level_and_cite_the_grammar() -> None:
    """Allen & Greenough gloss individual words and cite their own grammar by section."""
    notes = notes_for("caesar.bg", "1.1")
    assert notes, "expected commentary on BG 1.1"
    lemmas = {n["lemma"] for n in notes}
    assert "gallia" in lemmas and "omnis" in lemmas
    assert any("AG" in (n["grammar"] or "") for n in notes), "expected an A&G section citation"


@needs_commentary
def test_lemma_filter_returns_the_note_for_one_word() -> None:
    notes = notes_for("caesar.bg", "1.1", lemma="omnis")
    assert notes and all(n["lemma"] == "omnis" for n in notes)


@needs_commentary
@pytest.mark.parametrize(
    "work,ref,line",
    [("horace.odes", "1.5", 1), ("catullus.carmina", "5", 1), ("vergil.aeneid", "4", 1)],
)
def test_commentary_reaches_beyond_vergil(work: str, ref: str, line: int) -> None:
    assert notes_for(work, ref, line), f"no commentary for {work} {ref}.{line}"

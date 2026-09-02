"""Scansion, checked against verse whose scansion is not in dispute.

Every line here is real, and each was chosen because it breaks something. Invented examples
would have caught none of the four bugs these tests now guard:

- *qui* counted as two syllables (``qu`` treated as vowel + consonant), which made every
  hexameter containing *qui*, *quae* or *quod* come out two syllables too long;
- *v* folded to *u* and parsed as a vowel, so *virumque* scanned as four syllables;
- vowel quantities from the database misaligned against syllables whenever a consonantal
  *i* or *u* shifted the count;
- elided syllables dropping their consonants, so *multum ille* left *mul-* light when the
  *t* still closes it.
"""

from __future__ import annotations

import pytest

from enarratio.scansion import fold_syll, scan_line, syllabify

D, S = "dactyl", "spondee"


def feet(line: str) -> list[str]:
    s = scan_line(line)
    assert s.ok, f"failed to scan: {line!r} — {s.note}"
    return [f.kind for f in s.feet]


@pytest.mark.parametrize(
    "line,expected",
    [
        # Aeneid 1.1. The line every Latin student meets first.
        ("Arma virumque cano, Troiae qui primus ab oris", [D, D, S, S, D, "final"]),
        # Aeneid 1.3 — two elisions, and the reason elided consonants must still make position.
        ("litora, multum ille et terris iactatus et alto", [D, S, S, S, D, "final"]),
        ("multa quoque et bello passus, dum conderet urbem", [D, S, S, S, D, "final"]),
        # Eclogues 1.1.
        ("Tityre, tu patulae recubans sub tegmine fagi", [D, D, D, S, D, "final"]),
        # Aeneid 8.596 — the galloping line, famously all dactyls.
        ("Quadrupedante putrem sonitu quatit ungula campum", [D, D, D, D, D, "final"]),
        # Ovid, Metamorphoses 1.1.
        ("In nova fert animus mutatas dicere formas", [D, D, S, S, D, "final"]),
        # Aeneid 1.4.
        ("vi superum saevae memorem Iunonis ob iram", [D, S, D, S, D, "final"]),
        # Lucretius 1.1.
        ("Aeneadum genetrix, hominum divomque voluptas", [D, D, D, S, D, "final"]),
    ],
)
def test_hexameter(line: str, expected: list[str]) -> None:
    assert feet(line) == expected


@pytest.mark.parametrize(
    "word,syllables",
    [
        ("virumque", ["vi", "rum", "que"]),   # v is a consonant; qu is one consonant
        ("qui", ["qui"]),                      # not "qu-i"
        ("Troiae", ["tro", "iae"]),            # intervocalic i is consonantal; ae is a diphthong
        ("arma", ["ar", "ma"]),
        ("iactatus", ["iac", "ta", "tus"]),    # initial i before a vowel is consonantal
        ("lingua", ["lin", "gua"]),            # gu after a nasal is one consonant
    ],
)
def test_syllabification(word: str, syllables: list[str]) -> None:
    assert [s.text for s in syllabify(word)] == syllables


def test_elision_is_reported_not_hidden() -> None:
    """An elided syllable is still on the page, so the reader must be told about it."""
    s = scan_line("litora, multum ille et terris iactatus et alto")
    assert len(s.elisions) == 2
    assert any("multum" in e and "ille" in e for e in s.elisions)
    assert sum(1 for x in s.syllables if x.elided) == 2


def test_elided_syllable_still_makes_position() -> None:
    """*multum ille* is spoken "mult' ille": the t still closes *mul-*, which is heavy."""
    s = scan_line("litora, multum ille et terris iactatus et alto")
    mul = next(x for x in s.syllables if x.text == "mul")
    assert mul.quantity == "long"


def test_main_caesura_is_found() -> None:
    s = scan_line("Arma virumque cano, Troiae qui primus ab oris")
    assert any(c["name"] == "penthemimeral" for c in s.caesurae)


def test_quantities_carry_their_reason() -> None:
    """A quantity the reader cannot check is not worth showing."""
    s = scan_line("Arma virumque cano, Troiae qui primus ab oris")
    for syl in s.syllables:
        if syl.quantity in ("long", "short") and not syl.elided:
            assert syl.reason, f"no reason recorded for {syl.text!r}"


def test_prose_does_not_scan_as_hexameter() -> None:
    """The fitter must fail honestly rather than forcing a shape onto prose."""
    s = scan_line("Gallia est omnis divisa in partes tres quarum unam incolunt Belgae")
    assert not s.ok
    assert "hexameter" in s.note


def test_v_is_kept_as_a_consonant() -> None:
    assert fold_syll("Virumque") == "virumque"

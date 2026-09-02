"""Literary figures, tested on lines where the figure is not in dispute.

Several cases here encode false positives that were found and fixed. The parser reads the
first word of *veni, vidi, vici* as a vocative proper noun, which both hid the most famous
asyndeton in Latin and invented an apostrophe; and it attached *per* to the wrong noun,
which looked like anastrophe. Detectors that depend on the parse need surface evidence to
fall back on, and guards against parses that contradict themselves.
"""

from __future__ import annotations

import pytest

from enarratio.pipeline import analyse


def devices(text: str) -> set[str]:
    return {d["key"] for d in analyse(text)["devices"]}


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Veni, vidi, vici.", "asyndeton"),
        ("Magno misceri murmure pontum.", "alliteration"),
        ("Non ignara mali miseris succurrere disco.", "litotes"),
        ("Qualis apes aestate nova per florea rura exercet labor.", "simile"),
        ("Nihil te fugit. Nihil me fallit. Nihil nos terret.", "anaphora"),
        ("Manus manum lavat et vir virum servat.", "polyptoton"),
        ("Aurea purpuream subnectit fibula vestem.", "golden_line"),
        ("Quo usque tandem abutere, Catilina, patientia nostra?", "apostrophe"),
        # Hyperbaton is the figure behind most apparent "agreement errors" in verse.
        ("Arma virumque cano, Troiae qui primus ab oris Italiam fato profugus "
         "Laviniaque venit litora.", "hyperbaton"),
    ],
)
def test_detects(text: str, expected: str) -> None:
    assert expected in devices(text), f"{expected!r} not found in {text!r}"


@pytest.mark.parametrize(
    "text,forbidden,why",
    [
        (
            "Quo usque tandem abutere, Catilina, patientia nostra?", "asyndeton",
            "commas around a parenthetical vocative are not a list of parallel members",
        ),
        (
            "Qualis apes aestate nova per florea rura exercet labor.", "anastrophe",
            "per precedes its object; the parser merely attached it to the wrong noun",
        ),
        (
            "Veni, vidi, vici.", "apostrophe",
            "veni is a perfect verb the parser mistagged as a vocative proper noun",
        ),
    ],
)
def test_no_false_positive(text: str, forbidden: str, why: str) -> None:
    assert forbidden not in devices(text), why


def test_every_device_explains_its_effect() -> None:
    """Naming a figure is worth nothing; an examiner wants what it does."""
    r = analyse("Arma virumque cano, Troiae qui primus ab oris Italiam fato profugus "
                "Laviniaque venit litora.")
    assert r["devices"]
    for d in r["devices"]:
        assert d["evidence"], d
        assert d["effect"], d
        assert len(d["effect"]) > 40, f"effect too thin to be useful: {d}"


def test_hyperbaton_reports_the_intervening_words() -> None:
    """The words filling the gap are the point of the figure, so they must be shown."""
    r = analyse("Arma virumque cano, Troiae qui primus ab oris Italiam fato profugus "
                "Laviniaque venit litora.")
    hyp = next(d for d in r["devices"] if d["key"] == "hyperbaton")
    assert "words stand between them" in hyp["evidence"]


def test_prose_does_not_attract_verse_figures() -> None:
    """A golden line is a five-word verse pattern and must not fire on ordinary prose."""
    assert "golden_line" not in devices(
        "Gallia est omnis divisa in partes tres, quarum unam incolunt Belgae."
    )

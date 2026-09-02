"""Construction detection, checked against sentences chosen to isolate one construction.

These are regression tests in the strict sense: every case here has been verified by hand
against Allen & Greenough, and several encode bugs that were found and fixed (the
gerund-tagged-as-participle case, the dative attached to a copular predicate, the
comparative with no Degree feature, and the *Caesarem*/*Italiam* false positives).

Detection is probabilistic, so the tests assert that the right construction is *present*,
not that nothing else is -- overlapping readings are intended behaviour.
"""

from __future__ import annotations

import pytest

from enarratio.pipeline import analyse


def keys(text: str) -> set[str]:
    return {c["key"] for c in analyse(text)["constructions"]}


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Urbe capta cives fugerunt.", "ablative_absolute"),
        ("His rebus gestis Caesar profectus est.", "ablative_absolute"),
        ("Cicerone consule coniuratio detecta est.", "ablative_absolute_nominal"),
        ("Nemo nostrum tam stultus est.", "partitive_genitive"),
        ("Caesar militibus persuasit.", "dative_special_verb"),
        ("Haec omnia facienda sunt.", "passive_periphrastic"),
        ("Carthago delenda est nobis.", "dative_of_agent"),
        ("Gladio utitur miles.", "ablative_deponent"),
        ("Nihil est virtute pulchrius.", "ablative_comparison"),
        ("Mihi est liber.", "dative_of_possession"),
        ("Os umerosque deo similis erat.", "dative_with_adjective"),
        ("Dicit Caesarem venire.", "indirect_statement"),
        ("Venit ut videret.", "purpose_clause"),
        ("Tam fortis est ut omnes vincat.", "result_clause"),
        ("Cum haec dixisset, discessit.", "cum_clause"),
        ("Rogavit quis venisset.", "indirect_question"),
        ("Timeo ne veniat.", "fear_clause"),
        ("Memini illius diei.", "genitive_memory"),
        ("Legatos misit rogatum auxilium.", "supine"),
        ("Ad discendum venit.", "gerund"),
        ("Vivamus atque amemus.", "subjunctive_independent"),
        ("Romam contendit.", "accusative_place_to_which"),
    ],
)
def test_detects(text: str, expected: str) -> None:
    assert expected in keys(text), f"{expected!r} not found in {text!r}"


@pytest.mark.parametrize(
    "text,forbidden,why",
    [
        (
            "Dicit Caesarem venire.", "accusative_place_to_which",
            "Caesarem is the accusative subject of an infinitive, not a destination",
        ),
        (
            "Arma virumque cano, Troiae qui primus ab oris Italiam fato profugus "
            "Laviniaque venit litora.",
            "greek_accusative",
            "Italiam belongs with venit; profugus is an adjective, not a participle",
        ),
        (
            "Os umerosque deo similis erat.", "dative_of_possession",
            "deo is governed by the adjective similis, not by the copula",
        ),
    ],
)
def test_no_false_positive(text: str, forbidden: str, why: str) -> None:
    assert forbidden not in keys(text), why


def test_ablative_absolute_reports_both_words() -> None:
    """The construction must span the noun and its participle, not just one of them."""
    r = analyse("Urbe capta cives fugerunt.")
    abl = next(c for c in r["constructions"] if c["key"] == "ablative_absolute")
    words = {r["tokens"][i]["text"].lower() for i in abl["tokens"]}
    assert words == {"urbe", "capta"}


def test_every_construction_cites_a_grammar_section() -> None:
    """An uncited grammatical claim is exactly what this project exists to avoid."""
    r = analyse("His rebus gestis Caesar militibus persuasit ut Romam contenderent.")
    assert r["constructions"], "expected at least one construction"
    for c in r["constructions"]:
        assert c["grammarRef"].startswith("A&G"), c
        assert c["evidence"], c
        assert c["explanation"], c

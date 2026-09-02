"""The case-usage inventory: what an oblique case is *doing* in its sentence.

Latin's five working cases carry some sixty distinct functions between them, and the ending
never says which. Each test below isolates one use with a sentence whose reading is not in
dispute.

Several of these encode parser failures that the detectors now work around, because the
lesson recurs: rules keyed on the parse need surface evidence to fall back on.
"""

from __future__ import annotations

import pytest

from enarratio.pipeline import analyse


def uses(text: str) -> set[str]:
    return {c["key"] for c in analyse(text)["constructions"]}


@pytest.mark.parametrize(
    "text,expected",
    [
        # --- genitive ---
        ("Accusavit Verrem avaritiae.", "genitive_of_charge"),
        ("Magni aestimo virtutem.", "genitive_of_value"),
        ("Cupidus gloriae erat miles.", "genitive_with_adjective"),
        ("Vir magnae virtutis venit.", "genitive_of_description"),
        ("Nemo nostrum tam stultus est.", "partitive_genitive"),
        ("Memini illius diei.", "genitive_memory"),
        # --- dative ---
        ("Librum puellae dedit.", "dative_indirect_object"),
        ("Auxilio sociis venerunt.", "dative_of_purpose"),
        ("Eripuit mihi libertatem.", "dative_of_separation"),
        ("Caesar militibus persuasit.", "dative_special_verb"),
        ("Mihi est liber.", "dative_of_possession"),
        ("Carthago delenda est nobis.", "dative_of_agent"),
        ("Os umerosque deo similis erat.", "dative_with_adjective"),
        # --- accusative ---
        ("Docuit pueros grammaticam.", "two_accusatives_person_thing"),
        ("Ciceronem consulem creaverunt.", "two_accusatives_predicate"),
        ("Dicit Caesarem venire.", "accusative_subject_of_infinitive"),
        ("Romam contendit.", "accusative_place_to_which"),
        # --- ablative: all three merged cases ---
        ("Emit agrum multo auro.", "ablative_of_price"),
        ("Urbs a Caesare capta est.", "ablative_of_agent"),
        ("Cum amicis venit.", "ablative_of_accompaniment"),
        ("Multo maior est.", "ablative_degree_of_difference"),
        ("Iove natus heros.", "ablative_of_origin"),
        ("Caret patria miser.", "ablative_of_separation"),
        ("Timore fugit exercitus.", "ablative_of_cause"),
        ("Magna celeritate venit.", "ablative_of_manner"),
        ("In urbe manet.", "ablative_of_place_where"),
        ("Maior natu frater erat.", "ablative_of_specification"),
        ("Gladio utitur miles.", "ablative_deponent"),
        ("Urbe capta cives fugerunt.", "ablative_absolute"),
        # --- gerund and gerundive ---
        ("Ad pacem petendam venerunt.", "gerund_accusative_purpose"),
        ("Discendi causa venit.", "gerund_genitive_purpose"),
        ("Legendo discimus.", "gerund_ablative_means"),
        ("Haec omnia facienda sunt.", "passive_periphrastic"),
    ],
)
def test_case_use_detected(text: str, expected: str) -> None:
    assert expected in uses(text), f"{expected!r} not found in {text!r}"


def test_ambiguous_genitive_offers_both_readings() -> None:
    """Subjective and objective genitives are formally identical, so both must be shown."""
    found = uses("Amor patris magnus est.")
    assert "genitive_subjective" in found and "genitive_objective" in found


def test_parser_case_error_is_overridden_by_the_governing_adjective() -> None:
    """*gloriae* is tagged dative; *cupidus* governs a genitive, and wins."""
    r = analyse("Cupidus gloriae erat miles.")
    note = next(c for c in r["constructions"] if c["key"] == "genitive_with_adjective")
    assert note["caveat"], "an overridden parse must say so"


def test_gerund_survives_a_mistagged_word() -> None:
    """*legendo* comes back as a proper noun; the -nd- stem identifies it anyway."""
    assert "gerund_ablative_means" in uses("Legendo discimus.")


def test_every_case_use_cites_the_grammar() -> None:
    r = analyse("Magna cum celeritate Caesar legiones in hostium fines duxit.")
    assert r["constructions"]
    for c in r["constructions"]:
        assert c["grammarRef"].startswith("A&G"), c
        assert c["evidence"] and c["explanation"], c

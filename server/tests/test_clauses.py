"""Rule fixtures isolate syntax from parser accuracy; integration tests exercise both."""
import pytest
from enarratio.clauses import subordinate_clauses, relative_purpose, dative_direction
from enarratio.constructions import Tok, detect_all


def clause(marker, governor="uenio", mood="Sub", dep="advcl"):
    return [Tok(0, governor, governor, "VERB", "ROOT", 0, {"Mood": "Ind"}),
            Tok(1, marker, marker, "SCONJ", "mark", 2, {}),
            Tok(2, "faciat", "facio", "VERB", dep, 0, {"Mood": mood, "VerbForm": "Fin"})]


@pytest.mark.parametrize("marker,governor,mood,dep,key", [
    ("quominus", "impedio", "Sub", "ccomp", "hindering_clause"),
    ("ut", "impero", "Sub", "ccomp", "substantive_purpose"),
    ("ne", "moneo", "Sub", "ccomp", "substantive_purpose"),
    ("ut", "accido", "Sub", "csubj", "substantive_result"),
    ("quia", "uenio", "Ind", "advcl", "causal_clause"),
    ("quod", "gaudeo", "Ind", "ccomp", "substantive_quod"),
    ("quamvis", "uenio", "Sub", "advcl", "concessive_clause"),
    ("dummodo", "uenio", "Sub", "advcl", "proviso_clause"),
    ("antequam", "uenio", "Ind", "advcl", "temporal_before"),
    ("priusquam", "uenio", "Sub", "advcl", "temporal_before"),
    ("donec", "uenio", "Ind", "advcl", "temporal_until"),
    ("si", "uenio", "Ind", "advcl", "conditional_clause"),
    ("nisi", "uenio", "Sub", "advcl", "conditional_clause"),
])
def test_clause_types(marker, governor, mood, dep, key):
    found = subordinate_clauses(clause(marker, governor, mood, dep))
    assert key in {c.key for c in found}
    assert all(c.grammar_ref and c.evidence and c.caveat for c in found)


def test_dum_ambiguity_is_preserved():
    assert {c.key for c in subordinate_clauses(clause("dum"))} == {"proviso_clause", "temporal_until"}


def test_indicative_dum_is_not_proviso():
    assert {c.key for c in subordinate_clauses(clause("dum", mood="Ind"))} == {"temporal_until"}


def test_quin_requires_negative_governor():
    tokens = clause("quin", "dubito")
    assert not subordinate_clauses(tokens)
    tokens.append(Tok(3, "non", "non", "PART", "advmod", 0, {}))
    assert subordinate_clauses(tokens)[0].key == "hindering_clause"


def test_relative_quod_is_not_conjunction():
    tokens = clause("quod", mood="Ind")
    tokens[1].dep = "obj"
    tokens[1].pos = "PRON"
    assert not subordinate_clauses(tokens)


def test_no_finite_verb_no_clause():
    tokens = clause("si")
    tokens[2].morph = {"VerbForm": "Inf"}
    assert not subordinate_clauses(tokens)


def test_copular_clause():
    tokens = clause("quia", mood="Ind")
    tokens[2].pos, tokens[2].morph = "ADJ", {}
    tokens.append(Tok(3, "est", "sum", "AUX", "cop", 2, {"Mood": "Ind"}))
    assert subordinate_clauses(tokens)[0].key == "causal_clause"


def test_specific_complement_replaces_generic_purpose():
    keys = {c.key for c in detect_all(clause("ut", "impero", dep="ccomp"))}
    assert "substantive_purpose" in keys
    assert "purpose_clause" not in keys


def test_relative_purpose_needs_sending_and_relative():
    tokens = [Tok(0, "misit", "mitto", "VERB", "ROOT", 0, {"Mood": "Ind"}),
              Tok(1, "legatos", "legatus", "NOUN", "obj", 0, {"Case": "Acc"}),
              Tok(2, "qui", "qui", "PRON", "nsubj", 3, {"PronType": "Rel"}),
              Tok(3, "peterent", "peto", "VERB", "acl:relcl", 1, {"Mood": "Sub"})]
    assert relative_purpose(tokens)[0].confidence < .7
    tokens[0].lemma = "uideo"
    assert not relative_purpose(tokens)


def test_directional_dative_is_tentative_and_place_only():
    tokens = [Tok(0, "it", "eo", "VERB", "ROOT", 0, {"Mood": "Ind"}),
              Tok(1, "caelo", "caelum", "NOUN", "obl", 0, {"Case": "Dat"})]
    assert dative_direction(tokens)[0].confidence == .55
    tokens[1].lemma = "amicus"
    assert not dative_direction(tokens)


@pytest.mark.parametrize("text,key", [
    ("Caesar imperavit ut milites venirent.", "substantive_purpose"),
    ("Accidit ut luna plena esset.", "substantive_result"),
    ("Si hoc facis, erras.", "conditional_clause"),
])
def test_live_pipeline(text, key):
    from enarratio.pipeline import analyse
    assert key in {c["key"] for c in analyse(text)["constructions"]}

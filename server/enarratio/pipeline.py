"""The analysis pipeline: from pasted text to fully annotated tokens.

Stage order and the reason for it:

1. **Normalise** for display, preserving offsets, so a click on screen maps to a token.
2. **Parse** with LatinCy, which supplies the contextual reading: lemma, UPOS, morphology
   and dependencies.
3. **Enumerate** every morphologically possible reading with Whitaker's analyser. LatinCy
   says what is *likely*; Whitaker says what is *possible*. The reader needs both.
4. **Rank** the possible readings using the morphologizer's own probability distribution,
   so the interface can say "genitive, 92% -- but it could be 2nd person singular".
5. **Gate** on language identity only.
6. **Detect constructions** from morphology plus dependencies.
7. **Assemble** dictionary entries, paradigm information and human-readable glosses.

The model is loaded once and reused; loading costs several seconds and holding it resident
is what makes interactive clicking feel instant.
"""

from __future__ import annotations

import functools
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from . import constructions as cx
from .gate import GateResult, assess
from .commentary import notes_for
from .devices import detect_devices
from .identify import identify
from .scansion import scan_line

__all__ = ["analyse", "load_nlp", "MODEL_NAME"]

MODEL_NAME = "la_core_web_lg"


# --------------------------------------------------------------------------------------
# Making morphology readable
#
# "Case=Abl|Gender=Fem|Number=Sing" is not an explanation. These tables turn the parser's
# feature bundle into the words a grammar book would use.
# --------------------------------------------------------------------------------------

CASE_NAMES = {
    "Nom": "nominative", "Gen": "genitive", "Dat": "dative", "Acc": "accusative",
    "Abl": "ablative", "Voc": "vocative", "Loc": "locative",
}
CASE_FORCE = {
    "Nom": "the case of the subject, and of anything predicated of it",
    "Gen": "broadly the 'of' case: possession, description, and the whole from which a part is taken",
    "Dat": "the case of the person concerned -- to whom, for whom, in whose interest",
    "Acc": "the case of the direct object, and of extent and motion towards",
    "Abl": "Latin's catch-all oblique case, absorbing the old instrumental and locative: by, with, from, in",
    "Voc": "the case of direct address",
    "Loc": "a relic case for place where, surviving in a handful of words",
}
NUMBER_NAMES = {"Sing": "singular", "Plur": "plural"}
GENDER_NAMES = {"Masc": "masculine", "Fem": "feminine", "Neut": "neuter"}
TENSE_NAMES = {"Pres": "present", "Past": "perfect", "Fut": "future", "Pqp": "pluperfect"}
MOOD_NAMES = {"Ind": "indicative", "Sub": "subjunctive", "Imp": "imperative"}
VOICE_NAMES = {"Act": "active", "Pass": "passive"}
ASPECT_NAMES = {"Imp": "imperfective", "Perf": "perfective", "Inch": "inchoative", "Prosp": "prospective"}
VERBFORM_NAMES = {
    "Fin": "finite", "Inf": "infinitive", "Part": "participle", "Ger": "gerund",
    "Gdv": "gerundive", "Sup": "supine",
}
POS_NAMES = {
    "NOUN": "noun", "PROPN": "proper noun", "VERB": "verb", "AUX": "auxiliary verb",
    "ADJ": "adjective", "ADV": "adverb", "PRON": "pronoun", "DET": "determiner",
    "ADP": "preposition", "CCONJ": "coordinating conjunction",
    "SCONJ": "subordinating conjunction", "NUM": "numeral", "PART": "particle",
    "INTJ": "interjection", "PUNCT": "punctuation", "X": "unclassified",
}
DECLENSION_NAMES = {
    "1": "first declension", "2": "second declension", "3": "third declension",
    "4": "fourth declension", "5": "fifth declension",
}
CONJUGATION_NAMES = {
    "1": "first conjugation", "2": "second conjugation", "3": "third conjugation",
    "4": "fourth conjugation", "5": "irregular / third-io",
}

#: Whitaker's frequency codes, which are genuinely useful to a reader deciding how much
#: weight to give a rare reading.
FREQ_NAMES = {
    "A": "very frequent", "B": "frequent", "C": "common", "D": "lesser used",
    "E": "uncommon", "F": "very rare", "I": "inscription", "N": "Pliny only",
}
AGE_NAMES = {
    "A": "archaic", "B": "early", "C": "classical", "D": "late", "E": "later",
    "F": "medieval", "G": "scholastic", "H": "modern", "X": "all periods",
}


ORDINALS = {"1": "1st person", "2": "2nd person", "3": "3rd person"}


def describe_morph(morph: dict[str, str], pos: str) -> str:
    """A one-line parse in the order and wording a grammar book uses.

    Nominals read gender-case-number ("feminine ablative singular noun"); finite verbs read
    person-number-tense-voice-mood; participles get their tense and voice before the word
    'participle' and their agreement after it, which is how a Latin paradigm is recited.
    """
    verbform = morph.get("VerbForm")
    noun_word = POS_NAMES.get(pos, pos.lower())

    def agreement() -> list[str]:
        bits = []
        if morph.get("Gender"):
            bits.append(GENDER_NAMES[morph["Gender"]])
        if morph.get("Case"):
            bits.append(CASE_NAMES.get(morph["Case"], morph["Case"]))
        if morph.get("Number"):
            bits.append(NUMBER_NAMES.get(morph["Number"], morph["Number"]))
        return bits

    # Participles, gerunds, gerundives and supines: verbal features, then agreement.
    if verbform in ("Part", "Ger", "Gdv", "Sup"):
        bits: list[str] = []
        aspect, voice = morph.get("Aspect"), morph.get("Voice")
        if verbform == "Part":
            if aspect == "Perf" or morph.get("Tense") == "Past":
                bits.append("perfect")
            elif aspect == "Prosp" or morph.get("Tense") == "Fut":
                bits.append("future")
            elif aspect == "Imp" or morph.get("Tense") == "Pres":
                bits.append("present")
            if voice:
                bits.append(VOICE_NAMES[voice])
        name = ("gerundive" if verbform == "Gdv"
                else "gerund" if verbform == "Ger"
                else "supine" if verbform == "Sup" else "participle")
        # A prospective passive participle is a gerundive under another name.
        if verbform == "Part" and aspect == "Prosp" and voice == "Pass":
            bits, name = [], "gerundive"
        return " ".join(bits + [name] + agreement()).strip()

    # Finite verbs and infinitives.
    if verbform == "Inf" or pos in ("VERB", "AUX"):
        bits = []
        if morph.get("Person"):
            bits.append(ORDINALS.get(morph["Person"], morph["Person"]))
        if morph.get("Number"):
            bits.append(NUMBER_NAMES.get(morph["Number"], morph["Number"]))
        if morph.get("Tense"):
            bits.append(TENSE_NAMES.get(morph["Tense"], morph["Tense"]))
        if morph.get("Voice"):
            bits.append(VOICE_NAMES[morph["Voice"]])
        if verbform == "Inf":
            bits.append("infinitive")
        elif morph.get("Mood"):
            bits.append(MOOD_NAMES.get(morph["Mood"], morph["Mood"]))
        bits.append("verb" if pos == "VERB" else noun_word)
        return " ".join(bits).strip()

    # Nominals.
    bits = agreement()
    return " ".join(bits + [noun_word]).strip() if bits else noun_word


@functools.lru_cache(maxsize=1)
def load_nlp(model: str = MODEL_NAME):
    """Load the pipeline once. Cached -- reloading costs seconds."""
    import spacy

    nlp = spacy.load(model)
    if "whitakers_words" not in nlp.pipe_names:
        nlp.add_pipe("whitakers_words")
    return nlp


def _candidate_readings(nlp, doc) -> list[list[dict]]:
    """Per-token ranked morphological readings from the morphologizer's distribution.

    The encoder must be run before the classifier is queried, otherwise the distribution
    is uniform -- a mistake that cost one probe iteration and is worth the comment.
    """
    import numpy as np

    try:
        morph = nlp.get_pipe("morphologizer")
    except Exception:
        return [[] for _ in doc]
    try:
        staged = nlp.make_doc(doc.text)
        for name in ("enclitic_splitter", "tok2vec"):
            if name in nlp.pipe_names:
                staged = nlp.get_pipe(name)(staged)
        scores = np.asarray(morph.model.predict([staged])[0])
    except Exception:
        return [[] for _ in doc]

    out: list[list[dict]] = []
    for i in range(len(doc)):
        if i >= scores.shape[0]:
            out.append([])
            continue
        row = scores[i]
        e = np.exp(row - row.max())
        probs = e / e.sum()
        ranked = []
        for j in np.argsort(probs)[::-1][:5]:
            p = float(probs[j])
            if p < 0.01:
                break
            label = morph.labels[j]
            feats = dict(kv.split("=", 1) for kv in label.split("|") if "=" in kv)
            pos = feats.pop("POS", "")
            ranked.append({
                "probability": round(p, 4),
                "features": feats,
                "pos": pos,
                "description": describe_morph(feats, pos),
            })
        out.append(ranked)
    return out


def _lexicon_entries(tok) -> list[dict]:
    """Dictionary entries from Whitaker's, cleaned for display."""
    entries = getattr(tok._, "lexicon", None) or []
    out = []
    for e in entries[:4]:
        if not isinstance(e, dict):
            continue
        decl = str(e.get("decl_which") or "")
        pos = e.get("pos", "")
        out.append({
            "headword": e.get("headword"),
            "pos": pos,
            "glosses": e.get("glosses") or [],
            "principalParts": e.get("principal_parts") or [],
            "gender": GENDER_NAMES.get(
                {"M": "Masc", "F": "Fem", "N": "Neut"}.get(e.get("gender", ""), ""), None),
            "declension": (DECLENSION_NAMES.get(decl) if pos == "N" or pos == "ADJ"
                           else CONJUGATION_NAMES.get(decl) if pos == "V" else None),
            "frequency": FREQ_NAMES.get(e.get("freq", ""), None),
            "age": AGE_NAMES.get(e.get("age", ""), None),
            "sourceRefs": e.get("source_refs") or [],
        })
    return out


def _whitaker_parses(tok) -> list[dict]:
    """Every reading Whitaker's stem+ending engine allows for this surface form."""
    ww = getattr(tok._, "ww", None) or []
    out = []
    seen = set()
    for p in ww[:12]:
        if not isinstance(p, dict):
            continue
        feats = {}
        if p.get("case"):
            feats["Case"] = p["case"].title()[:3].replace("Abl", "Abl")
        if p.get("number"):
            feats["Number"] = "Sing" if p["number"] == "S" else "Plur"
        key = (p.get("lemma"), p.get("case"), p.get("number"), p.get("pos"))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "lemma": p.get("lemma"),
            "headword": p.get("headword"),
            "pos": p.get("pos"),
            "stem": p.get("stem"),
            "ending": p.get("ending"),
            "case": CASE_NAMES.get((p.get("case") or "").title()[:3], p.get("case")),
            "number": NUMBER_NAMES.get("Sing" if p.get("number") == "S" else "Plur")
                      if p.get("number") else None,
            "declension": p.get("decl"),
            "meaning": (p.get("meaning") or "").strip().rstrip(";"),
        })
    return out


def _maybe_scan(text: str) -> list[dict] | None:
    """Scan the passage if it looks like verse.

    Verse is not declared, it is discovered: each line is offered to the hexameter fitter,
    and if enough of them fit, the passage is verse. Prose does not accidentally scan --
    a hexameter is a tight template and 15-odd syllables rarely fall into it by chance --
    so a majority of lines fitting is strong evidence. Requiring *every* line to fit would
    be wrong, since a single proper name with an unrecorded quantity can defeat one line.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None
    scans = [scan_line(ln) for ln in lines]
    fitted = [s for s in scans if s.ok]
    if not fitted:
        return None
    # One line out of many fitting is chance; a majority is a metre.
    if len(lines) > 2 and len(fitted) * 2 < len(lines):
        return None
    return [s.as_dict() for s in scans]


def _commentary_for(passage: dict | None) -> list[dict]:
    """Editorial notes bearing on the identified lines.

    Notes are gathered per line and tagged with the line they belong to, so the interface
    can show them beside the right verse rather than as an undifferentiated heap. The line
    span is capped because a long paste would otherwise pull in hundreds of notes.
    """
    if not passage:
        return []
    out: list[dict] = []
    seen: set[tuple] = set()
    first, last = passage["lineStart"], min(passage["lineEnd"], passage["lineStart"] + 24)
    for line in range(first, last + 1):
        for note in notes_for(passage["work"], passage["ref"], line, limit=8):
            # A prose note carries no line and would otherwise repeat for every line in the
            # range; a verse note spanning lines would repeat likewise.
            key = (note["author"], note["lemma"], note["text"][:60])
            if key in seen:
                continue
            seen.add(key)
            note["line"] = line
            out.append(note)
    return out


def analyse(text: str, model: str = MODEL_NAME) -> dict[str, Any]:
    """Analyse a Latin excerpt end to end."""
    nlp = load_nlp(model)
    doc = nlp(text)

    gate: GateResult = assess(doc, text)

    # Identify the passage before anything else needs it: the citation is the key that
    # unlocks commentary, and it costs a few milliseconds against the shingle index.
    passage = identify(text)

    candidates = _candidate_readings(nlp, doc)

    tokens: list[dict] = []
    for t in doc:
        morph = t.morph.to_dict()
        # LatinCy's uv_normalizer rewrites *virumque* to *uirumque* internally. That is the
        # right form to analyse and the wrong one to display: a reader who pasted a modern
        # text should see it back unchanged. Recover the original slice by offset, falling
        # back to the parser's form if the lengths disagree (an enclitic split, say).
        surface = text[t.idx : t.idx + len(t.text)]
        display = surface if len(surface) == len(t.text) else t.text
        tokens.append({
            "i": t.i,
            "text": display,
            "whitespace": t.whitespace_,
            "start": t.idx,
            "end": t.idx + len(t.text),
            "isWord": bool(t.is_alpha),
            "lemma": t.lemma_,
            "pos": t.pos_,
            "posName": POS_NAMES.get(t.pos_, t.pos_.lower()),
            "tag": t.tag_,
            "dep": t.dep_,
            "head": t.head.i,
            "morph": morph,
            "description": describe_morph(morph, t.pos_),
            "caseForce": CASE_FORCE.get(morph.get("Case", ""), None),
            "gloss": getattr(t._, "gloss", None),
            "lexicon": _lexicon_entries(t),
            "possibleReadings": _whitaker_parses(t),
            "rankedReadings": candidates[t.i] if t.i < len(candidates) else [],
            "constructions": [],
            "devices": [],
            "sentence": 0,
        })

    # Constructions are detected per sentence, since every rule is clause-scoped.
    found: list[cx.Construction] = []
    sentence_views: list[list[cx.Tok]] = []
    for s_i, sent in enumerate(doc.sents):
        offset = sent.start
        toks = [
            cx.Tok(
                i=t.i, text=t.text, lemma=t.lemma_, pos=t.pos_, dep=t.dep_,
                head=t.head.i, morph=t.morph.to_dict(),
                candidates=tuple(getattr(t._, "ww", None) or ()),
                ent=t.ent_type_ or "",
                gloss=getattr(t._, "gloss", None) or "",
            )
            for t in sent
        ]
        # Detectors index by absolute position, so give them an absolute-indexed view.
        indexed: list[cx.Tok | None] = [None] * len(doc)
        for tk in toks:
            indexed[tk.i] = tk
        filled = [tk if tk is not None else cx.Tok(i, "", "", "X", "dep", i, {})
                  for i, tk in enumerate(indexed)]
        for t in sent:
            tokens[t.i]["sentence"] = s_i
        found.extend(cx.detect_all(filled))
        sentence_views.append(filled)

    devices = detect_devices(sentence_views)

    # An adjective far from its noun is hyperbaton, not a fault. The gate reports such
    # pairs as agreement anomalies because it runs before the figures are known; now that
    # they are, drop any anomaly the figure already accounts for. Reporting the same pair
    # once as art and again as error is worse than reporting it either way.
    explained = {
        pair
        for d in devices if d.key == "hyperbaton"
        for pair in (frozenset(d.tokens),)
    }
    gate_dict = gate.as_dict()
    kept = []
    for a in gate_dict["anomalies"]:
        if a["kind"] == "agreement":
            tok = a["token"]
            if any(tok in pair for pair in explained):
                continue
        kept.append(a)
    gate_dict["anomalies"] = kept
    for d in devices:
        for i in d.tokens:
            if 0 <= i < len(tokens):
                tokens[i].setdefault("devices", []).append(d.key)

    for c in found:
        for i in c.tokens:
            if 0 <= i < len(tokens):
                tokens[i]["constructions"].append(c.key)

    return {
        "text": text,
        "gate": gate_dict,
        "tokens": tokens,
        "constructions": [c.as_dict() for c in found],
        "devices": [d.as_dict() for d in devices],
        "sentences": [
            {"i": i, "start": s.start, "end": s.end, "text": s.text}
            for i, s in enumerate(doc.sents)
        ],
        "scansion": _maybe_scan(text),
        "passage": passage,
        "commentary": _commentary_for(passage),
        "model": model,
    }

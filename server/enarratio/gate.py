"""Deciding whether a pasted excerpt is Latin, and flagging what looks irregular.

Two separate questions, deliberately kept apart because only one of them can be answered
reliably (see docs/research/empirical-probe-latincy.md, Finding 8):

**Is this Latin?** Yes -- answerable. Two complementary signals separate cleanly on every
sample tested: Whitaker's morphological analyser recognises 86-100% of tokens in genuine
Latin and at most 58% in anything else, while `lingua` rejects the Romance languages and
English at confidences below 0.05. Each covers the other's blind spot: `lingua` is fooled
by Lorem ipsum (0.996), which Whitaker catches at 58%; Whitaker handles two-word inputs
where `lingua` collapses.

**Is this *good* Latin?** No -- not answerable, and the attempt is actively harmful.
Agreement checking flags 5 of 6 modifiers in the opening of the *Aeneid*, because poetic
hyperbaton separates adjective from noun and the parser mis-attaches them. A gate built on
it would reject Vergil and Horace while passing a list of unrelated nouns. So irregularities
are reported as observations attached to tokens, and never block analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

__all__ = ["GateResult", "Anomaly", "assess"]

#: Below this share of morphologically analysable tokens, the text is not Latin.
#: Measured separation on the probe set: genuine Latin >= 0.86, everything else <= 0.58.
#: 0.75 sits in the empty middle with margin on both sides.
ANALYSABLE_FLOOR = 0.75

#: Between the floor and this, accept but warn -- likely Latin with heavy corruption,
#: unusual orthography, or a great many proper nouns.
ANALYSABLE_DOUBT = 0.85

#: `lingua` is unreliable under this many words, so it is not consulted for short inputs.
LINGUA_MIN_WORDS = 5


@dataclass
class Anomaly:
    """Something irregular, reported without judgement."""

    token: int
    kind: str
    message: str
    #: The benign explanation, always offered first when one exists.
    likely_benign: str = ""


@dataclass
class GateResult:
    is_latin: bool
    confidence: float
    analysable_rate: float
    lingua_latin: float | None
    competing_language: str | None
    unrecognised: tuple[str, ...]
    anomalies: tuple[Anomaly, ...] = ()
    message: str = ""

    def as_dict(self) -> dict:
        return {
            "isLatin": self.is_latin,
            "confidence": round(self.confidence, 3),
            "analysableRate": round(self.analysable_rate, 3),
            "linguaLatin": round(self.lingua_latin, 3) if self.lingua_latin is not None else None,
            "competingLanguage": self.competing_language,
            "unrecognised": list(self.unrecognised),
            "anomalies": [
                {"token": a.token, "kind": a.kind, "message": a.message,
                 "likelyBenign": a.likely_benign} for a in self.anomalies
            ],
            "message": self.message,
        }


def _lingua_scores(text: str):
    """Latin confidence and the strongest competing language, or (None, None)."""
    try:
        from lingua import Language, LanguageDetectorBuilder
    except ImportError:
        return None, None
    det = (
        LanguageDetectorBuilder.from_languages(
            Language.LATIN, Language.ITALIAN, Language.SPANISH, Language.ENGLISH,
            Language.ROMANIAN, Language.FRENCH, Language.PORTUGUESE, Language.CATALAN,
            Language.GERMAN, Language.GREEK,
        ).build()
    )
    values = det.compute_language_confidence_values(text)
    latin = next((v.value for v in values if v.language == Language.LATIN), 0.0)
    other = next((v for v in values if v.language != Language.LATIN), None)
    return latin, (other.language.name.title() if other and other.value > 0.3 else None)


def assess(doc, text: str) -> GateResult:
    """Judge a parsed document.

    ``doc`` is a spaCy ``Doc`` that has been through the ``whitakers_words`` component, so
    each token carries ``._.ww``. Only alphabetic tokens count: punctuation and numerals
    say nothing about the language.
    """
    toks = [t for t in doc if t.is_alpha]
    if not toks:
        return GateResult(
            is_latin=False, confidence=0.0, analysable_rate=0.0, lingua_latin=None,
            competing_language=None, unrecognised=(),
            message="No words found to analyse.",
        )

    analysed = [t for t in toks if getattr(t._, "ww", None)]
    rate = len(analysed) / len(toks)
    unrecognised = tuple(t.text for t in toks if not getattr(t._, "ww", None))

    lingua_latin, competitor = (None, None)
    if len(toks) >= LINGUA_MIN_WORDS:
        lingua_latin, competitor = _lingua_scores(text)

    # The analysability rate is the primary signal; lingua explains a rejection and can
    # veto a borderline pass when it is confident the text is a specific other language.
    is_latin = rate >= ANALYSABLE_FLOOR
    if is_latin and lingua_latin is not None and lingua_latin < 0.15 and competitor:
        is_latin = False

    if not is_latin:
        if competitor and (lingua_latin or 0) < 0.15:
            msg = (
                f"This does not look like Latin -- only {rate:.0%} of the words can be "
                f"morphologically analysed, and the text scores as {competitor}."
            )
        elif rate < 0.2:
            msg = (
                f"This does not look like Latin: almost nothing in it ({rate:.0%}) can be "
                f"analysed as a Latin form."
            )
        else:
            msg = (
                f"This does not look like Latin. Only {rate:.0%} of the words yield a Latin "
                f"morphological analysis, against at least 86% for genuine Latin of any period. "
                f"Text that merely imitates Latin -- Lorem ipsum, for instance -- lands in "
                f"exactly this range."
            )
        confidence = 1.0 - rate
    elif rate < ANALYSABLE_DOUBT:
        msg = (
            f"Analysed as Latin, but {len(unrecognised)} word(s) could not be parsed. That is "
            f"normal for proper names, textual corruption, or late and medieval spelling."
        )
        confidence = rate
    else:
        msg = ""
        confidence = rate

    return GateResult(
        is_latin=is_latin, confidence=confidence, analysable_rate=rate,
        lingua_latin=lingua_latin, competing_language=competitor,
        unrecognised=unrecognised, anomalies=tuple(_anomalies(doc)), message=msg,
    )


def _anomalies(doc) -> list[Anomaly]:
    """Irregularities worth showing the reader. Never used to reject.

    Every agreement mismatch carries the reminder that displaced word order is the more
    likely explanation, because on real poetry it usually is.
    """
    out: list[Anomaly] = []
    for t in doc:
        if t.dep_ in ("amod", "det", "nummod") and t.pos_ in ("ADJ", "DET", "NUM"):
            h = t.head
            for feat in ("Case", "Number", "Gender"):
                a, b = t.morph.get(feat), h.morph.get(feat)
                if a and b and set(a).isdisjoint(set(b)):
                    out.append(Anomaly(
                        token=t.i, kind="agreement",
                        message=(
                            f"'{t.text}' ({feat.lower()} {'/'.join(a)}) does not agree with "
                            f"'{h.text}' ({feat.lower()} {'/'.join(b)}), which the parser takes "
                            f"to be the word it modifies."
                        ),
                        likely_benign=(
                            "In verse this usually means the parser has attached the adjective to "
                            "the wrong noun -- hyperbaton routinely separates them by several "
                            "words. Look for another noun nearby that it agrees with before "
                            "concluding the Latin is faulty."
                        ),
                    ))
                    break
    if not any("Fin" in t.morph.get("VerbForm") for t in doc):
        out.append(Anomaly(
            token=0, kind="no_finite_verb",
            message="No finite verb found in this passage.",
            likely_benign=(
                "Perfectly normal in Latin: *esse* is frequently omitted (*omnia praeclara "
                "rara*), and the passage may be a sentence fragment, a heading, or a list."
            ),
        ))
    return out

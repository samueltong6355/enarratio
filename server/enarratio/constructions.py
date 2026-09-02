"""Detection of Latin syntactic constructions from morphology and dependencies.

This is the part of Enarratio that a dictionary cannot do. Knowing that ``duce`` is the
ablative singular of *dux* is a lookup; knowing that ``Caesare duce`` is an ablative
absolute setting the circumstances of the main clause, and that it must be rendered "with
Caesar as leader" rather than "by Caesar the leader", is a reading.

Every detector here follows the same contract:

- it fires on evidence drawn from morphology and the dependency parse, never on a guess;
- it reports the *evidence* that made it fire, so the reader can check the reasoning;
- it carries a confidence, because the parse underneath is ~91% accurate on morphology
  (see docs/research/empirical-probe-latincy.md) and rules built on it inherit that error;
- it cites Allen & Greenough, so the reader can go and read the grammar.

Detectors are deliberately allowed to overlap. A word can be simultaneously the ablative
of an ablative absolute and the object of a preposition in a competing reading, and Latin
students are best served by seeing both with their relative confidence, not by an
arbitrator picking one silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

__all__ = ["Construction", "detect_all", "DETECTORS", "CONSTRUCTION_INDEX"]


# --------------------------------------------------------------------------------------
# Result type
# --------------------------------------------------------------------------------------


@dataclass
class Construction:
    """One syntactic construction found in the text."""

    key: str
    name: str
    latin_name: str
    #: Indices of every token participating, anchor first where it matters.
    tokens: tuple[int, ...]
    #: The token this construction is "about" -- the one whose case is being explained.
    anchor: int
    #: What fired the rule, in the reader's terms.
    evidence: str
    #: What the construction means here, in this sentence.
    explanation: str
    #: How to render it in English.
    translation_hint: str
    grammar_ref: str
    confidence: float
    #: Ways this detection could be wrong, shown when confidence is low.
    caveat: str = ""

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "latinName": self.latin_name,
            "tokens": list(self.tokens),
            "anchor": self.anchor,
            "evidence": self.evidence,
            "explanation": self.explanation,
            "translationHint": self.translation_hint,
            "grammarRef": self.grammar_ref,
            "confidence": round(self.confidence, 2),
            "caveat": self.caveat,
        }


# --------------------------------------------------------------------------------------
# Lexical classes that license particular constructions
#
# These closed classes are what make case-usage detection possible at all. A bare
# ablative is ambiguous between a dozen uses; a bare ablative governed by `utor` is not.
# --------------------------------------------------------------------------------------

#: Intransitive verbs that take a dative where English uses a direct object. A&G 367.
#: The commonest source of student error ("he persuaded the king" is *regi* persuasit).
DATIVE_VERBS = {
    "credo", "faveo", "fido", "confido", "diffido", "ignosco", "impero", "indulgeo",
    "irascor", "medeor", "minor", "noceo", "nubo", "parco", "pareo", "placeo", "displiceo",
    "persuadeo", "resisto", "servio", "studeo", "suadeo", "supplico", "invideo", "obsto",
    "occurro", "subvenio", "succurro", "prosum", "obsum", "praesum", "desum", "adsum",
    "assentior", "blandior", "cedo", "concedo", "obtempero", "obedio", "oboedio",
    "gratulor", "nubo", "maledico", "benedico", "satisfacio", "tempero", "moderor",
}

#: Adjectives governing a dative -- A&G 384. Mostly words of likeness, nearness,
#: fitness, friendliness and their opposites.
DATIVE_ADJECTIVES = {
    "similis", "dissimilis", "par", "dispar", "aequalis", "proximus", "propinquus",
    "vicinus", "amicus", "inimicus", "carus", "fidelis", "infestus", "aptus", "utilis",
    "inutilis", "idoneus", "necessarius", "gratus", "ingratus", "facilis", "difficilis",
    "notus", "ignotus", "communis", "proprius", "contrarius", "adversus", "benignus",
}

#: Deponents governing the ablative. A&G 410. The classic memorised list.
ABLATIVE_DEPONENTS = {"utor", "fruor", "fungor", "potior", "vescor"}

#: Verbs of remembering and forgetting take the genitive. A&G 350.
GENITIVE_MEMORY_VERBS = {"memini", "obliviscor", "reminiscor", "recordor"}

#: Impersonals of feeling take genitive of the cause. A&G 354.
GENITIVE_IMPERSONALS = {"miseret", "paenitet", "piget", "pudet", "taedet"}

#: Nouns and quantity words that take a partitive genitive. A&G 346.
PARTITIVE_HEADS = {
    "pars", "nemo", "nihil", "quis", "aliquis", "quisquam", "nullus", "multus", "multum",
    "plus", "plurimum", "minus", "satis", "parum", "numerus", "copia", "vis", "modus",
    "quantum", "tantum", "aliquid", "quid", "unus", "solus", "uterque", "quisque",
    "milia", "acervus", "turba", "medius", "reliquus", "ceterus", "summus",
}

#: Nouns predicated of a person in a nominal ablative absolute: *Cicerone consule*.
#: Without a participle there is nothing but this closed class to key on. A&G 419a.
ABL_ABS_ROLE_NOUNS = {
    "dux", "consul", "rex", "auctor", "testis", "iudex", "praetor", "imperator",
    "magister", "comes", "socius", "adiutor", "princeps", "tribunus", "dictator",
    "censor", "aedilis", "quaestor", "pontifex", "augur", "legatus", "puer", "senex",
    "adulescens", "natura", "deus", "fortuna",
}

#: Predicative adjectives found in nominal ablative absolutes: *me invito*, *vivo Caesare*.
ABL_ABS_ROLE_ADJS = {"invitus", "inscius", "vivus", "salvus", "incolumis", "conscius", "ignarus"}

#: Body parts and aspects, the usual host of the Greek accusative of respect. A&G 397b.
GREEK_ACC_NOUNS = {
    "os", "caput", "pectus", "latus", "umerus", "manus", "pes", "crinis", "coma",
    "capillus", "oculus", "frons", "genu", "bracchium", "cervix", "collum", "corpus",
    "membrum", "vultus", "facies", "tergum", "dorsum", "venter", "cor", "animus", "mens",
}

#: Verbs of saying, thinking, perceiving: heads of indirect statement. A&G 579.
INDIRECT_STATEMENT_VERBS = {
    "dico", "nego", "aio", "inquam", "narro", "nuntio", "respondeo", "scribo", "trado",
    "puto", "existimo", "arbitror", "credo", "spero", "confido", "censeo", "reor",
    "iudico", "intellego", "sentio", "video", "audio", "cognosco", "scio", "nescio",
    "disco", "memini", "spero", "promitto", "polliceor", "simulo", "fateor", "confiteor",
    "constat", "apparet", "patet", "placet", "videtur", "accipio", "comperio", "reperio",
}

#: Verbs of fearing: take *ne* for what is feared. A&G 564. The polarity inverts, which
#: is the single most confusing thing about them for a learner.
FEARING_VERBS = {"timeo", "metuo", "vereor", "paveo", "extimesco", "pertimesco", "formido"}

#: Verbs of hindering and preventing: *ne* / *quominus* / *quin*. A&G 558.
HINDERING_VERBS = {
    "impedio", "prohibeo", "deterreo", "obsto", "obsisto", "resisto", "recuso",
    "interdico", "caveo", "vito", "dubito", "cunctor",
}

#: Correlatives that signal a result clause rather than a purpose clause. A&G 537.
RESULT_CORRELATIVES = {"tam", "ita", "sic", "adeo", "tantus", "talis", "tot", "totiens", "eo"}

#: Prepositions governing the accusative, used to rule *out* bare-case readings.
ACC_PREPOSITIONS = {
    "ad", "ante", "apud", "circum", "circa", "contra", "erga", "extra", "infra", "inter",
    "intra", "iuxta", "ob", "per", "post", "praeter", "prope", "propter", "secundum",
    "supra", "trans", "ultra", "adversus", "penes", "pone", "cis", "citra",
}
ABL_PREPOSITIONS = {
    "a", "ab", "abs", "cum", "de", "e", "ex", "prae", "pro", "sine", "coram", "palam",
    "tenus", "absque",
}

#: Time-words: an ablative of these is almost always time-when. A&G 423.
TIME_NOUNS = {
    "annus", "mensis", "dies", "nox", "hora", "tempus", "aetas", "hiems", "aestas",
    "ver", "autumnus", "bellum", "pax", "consulatus", "principium", "initium", "finis",
    "vesper", "lux", "aurora", "meridies",
}

#: Cities and small islands take locative/accusative without a preposition. A&G 427.
PLACE_EXCEPTIONS = {"domus", "rus", "humus", "militia", "bellum", "focus"}


# --------------------------------------------------------------------------------------
# Token adapter
#
# Detectors are written against this minimal protocol rather than against spaCy directly,
# so the rules stay testable without loading a 500 MB model and remain portable if the
# parser is ever swapped.
# --------------------------------------------------------------------------------------


#: Verbs of motion, which license the prepositionless accusative of place to which.
MOTION_VERBS = {
    "eo", "venio", "advenio", "pervenio", "redeo", "abeo", "exeo", "ineo", "proficiscor",
    "contendo", "propero", "festino", "curro", "navigo", "migro", "revertor", "reverto",
    "descendo", "ascendo", "mitto", "duco", "fugio", "confugio", "concurro",
}

#: Irregular comparatives and superlatives, whose form gives no clue.
IRREGULAR_COMPARATIVES = {
    "melior", "peior", "maior", "minor", "plus", "plures", "prior", "propior",
    "ulterior", "interior", "exterior", "superior", "inferior", "senior", "iunior",
}
IRREGULAR_SUPERLATIVES = {
    "optimus", "pessimus", "maximus", "minimus", "plurimus", "primus", "proximus",
    "ultimus", "intimus", "extremus", "summus", "infimus", "imus", "postremus",
}


@dataclass
class Tok:
    """The slice of a parsed token that construction rules actually need."""

    i: int
    text: str
    lemma: str
    pos: str
    dep: str
    head: int
    morph: dict[str, str]
    #: Every reading Whitaker's analyser allows, for ambiguity-aware rules.
    candidates: tuple[dict, ...] = ()
    #: Named-entity label from the parser ("LOC", "PERSON", "NORP", or "").
    ent: str = ""
    #: Short dictionary gloss, used so explanations can name the English sense instead of
    #: fabricating English inflections ("gero-ed" helps nobody).
    gloss: str = ""

    def sense(self) -> str:
        """The first dictionary sense, for use inside a prose explanation."""
        if not self.gloss:
            return ""
        return self.gloss.split(",")[0].split(";")[0].strip()

    def case(self) -> str | None:
        return self.morph.get("Case")

    def number(self) -> str | None:
        return self.morph.get("Number")

    def gender(self) -> str | None:
        return self.morph.get("Gender")

    def is_(self, **feats) -> bool:
        return all(self.morph.get(k) == v for k, v in feats.items())

    def degree(self) -> str | None:
        """Comparative or superlative, derived from the form.

        LatinCy does **not** emit a ``Degree`` feature -- its morphological inventory has
        no such key (verified against ``morphologizer.labels``). Degree therefore has to be
        recovered from the ending, which for Latin is reliable: comparatives end in *-ior*
        (m./f.) or *-ius* (n.), superlatives in *-issimus*, *-errimus*, *-illimus*. The
        handful of suppletive forms are listed explicitly.
        """
        if self.pos not in ("ADJ", "ADV"):
            return None
        form = self.text.lower().replace("v", "u").replace("j", "i")
        lem = self.lemma.lower().replace("v", "u").replace("j", "i")
        if lem in IRREGULAR_SUPERLATIVES or form.endswith(
            ("issimus", "issima", "issimum", "errimus", "errima", "errimum",
             "illimus", "illima", "illimum", "issime")
        ):
            return "Sup"
        if lem in IRREGULAR_COMPARATIVES or form.endswith(
            ("ior", "ioris", "iori", "iorem", "iore", "iores", "iorum", "ioribus", "iora")
        ):
            return "Cmp"
        # Neuter comparative in -ius (*pulchrius*, *fortius*). The lemma is the positive
        # (*pulcher*), so the test is that the form ends -ius while the dictionary form
        # does not -- which separates *pulchrius* from adjectives whose stem is itself
        # -ius. Genitives like *eius*/*huius* are excluded, and the ADJ/ADV check above
        # already keeps pronouns out.
        if (form.endswith("ius") and not form.endswith(("eius", "uius", "aius", "cuius"))
                and not lem.endswith("ius")):
            return "Cmp"
        return None

    def is_gerundive(self) -> bool:
        """Gerund/gerundive, however the parser happens to have labelled it.

        LatinCy is inconsistent here: *facienda* comes back as ``VerbForm=Gdv``, but
        *discendum* as ``VerbForm=Part|Voice=Pass|Aspect=Prosp``. Both are the same verbal
        adjective, so both spellings of the analysis are accepted.
        """
        if self.morph.get("VerbForm") in ("Gdv", "Ger"):
            return True
        return (
            self.morph.get("VerbForm") == "Part"
            and self.morph.get("Voice") == "Pass"
            and self.morph.get("Aspect") == "Prosp"
        )


Sentence = Sequence[Tok]


def _children(sent: Sentence, i: int) -> list[Tok]:
    return [t for t in sent if t.head == i and t.i != i]


def _head_of(sent: Sentence, t: Tok) -> Tok | None:
    if t.head == t.i or not (0 <= t.head < len(sent)):
        return None
    return sent[t.head]


def _has_preposition(sent: Sentence, t: Tok) -> Tok | None:
    """The preposition governing this token, if any.

    Crucial as a negative check: a bare-case construction is only 'bare' if no preposition
    governs it. ``cum Caesare`` is accompaniment, not an ablative absolute.
    """
    for c in _children(sent, t.i):
        if c.dep == "case" and c.pos in ("ADP", "SCONJ"):
            return c
    return None


def _agrees(a: Tok, b: Tok, feats: Iterable[str] = ("Case", "Number")) -> bool:
    for f in feats:
        av, bv = a.morph.get(f), b.morph.get(f)
        if av and bv and av != bv:
            return False
    return True


# --------------------------------------------------------------------------------------
# Detectors
# --------------------------------------------------------------------------------------

DetectorFn = Callable[[Sentence], list[Construction]]
DETECTORS: list[tuple[str, DetectorFn]] = []


def detector(key: str):
    def wrap(fn: DetectorFn) -> DetectorFn:
        DETECTORS.append((key, fn))
        return fn
    return wrap


@detector("ablative_absolute")
def _ablative_absolute(sent: Sentence) -> list[Construction]:
    """Ablative absolute -- A&G 419.

    Two routes. LatinCy emits a dedicated ``advcl:abs`` label, which is reliable for the
    participial type (*his rebus gestis*). It is **not** reliable for the nominal type
    (*Cicerone consule*, *me duce*), which the probe showed being labelled plain ``obl``
    about half the time -- so that type is detected structurally instead: two ablatives
    agreeing in number, the predicate drawn from the closed class of role nouns, and
    critically no preposition governing either.
    """
    out: list[Construction] = []
    seen: set[int] = set()

    for t in sent:
        if t.dep == "advcl:abs" and t.case() == "Abl":
            subj = next(
                (c for c in _children(sent, t.i)
                 if c.dep in ("nsubj", "nsubj:pass") and c.case() == "Abl"), None
            )
            parts = tuple(sorted({t.i} | ({subj.i} if subj else set())))
            seen.update(parts)
            is_part = t.morph.get("VerbForm") == "Part"
            noun = sent[subj.i].text if subj else "the implied subject"
            tense = t.morph.get("Tense")
            named = f" (*{t.lemma}*, '{t.sense()}')" if t.sense() else f" (*{t.lemma}*)"
            if is_part and t.morph.get("Voice") == "Pass":
                sense = (f"a perfect passive participle{named}, so the action it names is "
                         f"already complete when the main verb happens")
                hint = f"after {noun} had been …, / with {noun} …"
            elif is_part and tense == "Pres":
                sense = (f"a present active participle{named}, so its action is going on at "
                         f"the same time as the main verb")
                hint = f"while {noun} was …"
            else:
                sense = "a predicate standing outside the syntax of the main clause"
                hint = f"with {noun} as …"
            out.append(Construction(
                key="ablative_absolute",
                name="Ablative Absolute",
                latin_name="ablativus absolutus",
                tokens=parts, anchor=t.i,
                evidence=f"parser labelled '{t.text}' advcl:abs, in the ablative"
                         + (f", with '{sent[subj.i].text}' as its ablative subject" if subj else ""),
                explanation=(
                    f"'{' '.join(sent[i].text for i in parts)}' is an ablative absolute: a "
                    f"self-contained phrase, grammatically detached ('absolute' = *absolutus*, "
                    f"loosened) from the rest of the sentence, setting the circumstances under "
                    f"which the main action happens. '{t.text}' is {sense}. Neither word has any "
                    f"other syntactic role in the main clause -- that detachment is what makes it "
                    f"absolute."
                ),
                translation_hint=hint,
                grammar_ref="A&G 419", confidence=0.9,
            ))

    # Nominal type: noun + predicate noun/adjective, both ablative, no preposition.
    for t in sent:
        if t.i in seen or t.case() != "Abl" or _has_preposition(sent, t):
            continue
        if not (t.lemma in ABL_ABS_ROLE_NOUNS or t.lemma in ABL_ABS_ROLE_ADJS):
            continue
        for other in sent:
            if other.i == t.i or other.case() != "Abl" or _has_preposition(sent, other):
                continue
            if abs(other.i - t.i) > 2 or not _agrees(t, other, ("Number",)):
                continue
            if other.pos not in ("NOUN", "PROPN", "PRON"):
                continue
            parts = tuple(sorted((t.i, other.i)))
            if parts[0] in seen:
                continue
            seen.update(parts)
            out.append(Construction(
                key="ablative_absolute_nominal",
                name="Ablative Absolute (nominal)",
                latin_name="ablativus absolutus",
                tokens=parts, anchor=t.i,
                evidence=(f"'{other.text}' and '{t.text}' are both ablative, agree in number, "
                          f"stand adjacent, are governed by no preposition, and '{t.lemma}' is a "
                          f"role-word of the kind that takes a nominal ablative absolute"),
                explanation=(
                    f"'{sent[parts[0]].text} {sent[parts[1]].text}' is a nominal ablative "
                    f"absolute -- the type with no participle at all, because Latin has no "
                    f"present participle of *sum*. Supply 'being': '{other.text} being "
                    f"{t.text}'. It dates the action or states the circumstances, and is the "
                    f"standard Roman way of giving a year ('in the consulship of ...')."
                ),
                translation_hint=f"with {other.text} as {t.text} / when {other.text} was {t.text}",
                grammar_ref="A&G 419a", confidence=0.7,
                caveat=("No participle is present, so this rests on the two words being adjacent "
                        "ablatives with a role-noun. Check it is not an ablative of means or "
                        "attendant circumstance."),
            ))
            break
    return out


@detector("partitive_genitive")
def _partitive_genitive(sent: Sentence) -> list[Construction]:
    """Genitive of the whole -- A&G 346."""
    out = []
    for t in sent:
        if t.case() != "Gen":
            continue
        head = _head_of(sent, t)
        if head is None:
            continue
        superlative = head.morph.get("Degree") in ("Sup", "Cmp")
        if not (head.lemma in PARTITIVE_HEADS or superlative
                or (head.pos in ("NUM", "PRON") and head.case() != "Gen")):
            continue
        out.append(Construction(
            key="partitive_genitive",
            name="Partitive Genitive",
            latin_name="genetivus partitivus",
            tokens=(t.i, head.i), anchor=t.i,
            evidence=(f"'{t.text}' is genitive and depends on "
                      f"'{head.text}'" + (", a superlative" if superlative else
                                          f", a word of quantity or number")),
            explanation=(
                f"'{t.text}' is a partitive genitive -- it names the whole from which "
                f"'{head.text}' selects a part. Latin says 'something OF the citizens' where "
                f"English often just says 'some citizens'. Note that this is the one genitive "
                f"that is not possessive: nobody owns anything here."
            ),
            translation_hint=f"of the {t.text} / among the {t.text}",
            grammar_ref="A&G 346", confidence=0.75,
            caveat=("A genitive depending on a noun could instead be possessive, objective or "
                    "of description. Partitive is likeliest when the head expresses quantity."),
        ))
    return out


@detector("dative_special_verb")
def _dative_special_verb(sent: Sentence) -> list[Construction]:
    """Dative with intransitive verbs -- A&G 367."""
    out = []
    for t in sent:
        if t.case() != "Dat":
            continue
        head = _head_of(sent, t)
        if head is None or head.lemma not in DATIVE_VERBS:
            continue
        out.append(Construction(
            key="dative_special_verb",
            name="Dative with a Special Verb",
            latin_name="dativus cum verbis specialibus",
            tokens=(t.i, head.i), anchor=t.i,
            evidence=f"'{t.text}' is dative and governed by '{head.lemma}', which takes a dative",
            explanation=(
                f"'{head.lemma}' is intransitive in Latin and takes a dative, even though its "
                f"English equivalent takes a direct object. So '{t.text}' is not the object of "
                f"'{head.text}' -- it is the person *to* or *for* whom the action happens. "
                f"Translate as though it were an object ('{head.lemma} the {t.text}'), but "
                f"remember it cannot be made the subject of a personal passive: Latin can only "
                f"say *{t.text} persuasum est*, impersonally."
            ),
            translation_hint=f"(treat '{t.text}' as the English object)",
            grammar_ref="A&G 367", confidence=0.88,
        ))
    return out


@detector("dative_of_agent")
def _dative_of_agent(sent: Sentence) -> list[Construction]:
    """Dative of agent with the passive periphrastic -- A&G 374."""
    out = []
    gerundives = [t for t in sent if t.is_gerundive()]
    for g in gerundives:
        for t in sent:
            if t.case() != "Dat" or _has_preposition(sent, t):
                continue
            if t.head != g.i and _head_of(sent, t) is not None and _head_of(sent, t).i != g.i:
                # allow the dative to hang off the copula instead of the gerundive
                h = _head_of(sent, t)
                if not (h and h.lemma == "sum"):
                    continue
            out.append(Construction(
                key="dative_of_agent",
                name="Dative of Agent",
                latin_name="dativus auctoris",
                tokens=(t.i, g.i), anchor=t.i,
                evidence=f"'{t.text}' is a bare dative alongside the gerundive '{g.text}'",
                explanation=(
                    f"With a passive periphrastic (gerundive + *sum*) Latin marks the agent with "
                    f"a bare dative, not with *ab* + ablative. '{t.text}' is the person who has "
                    f"to do it: '{g.text}' must be done BY {t.text}. Meeting a dative next to a "
                    f"gerundive and translating it 'to/for' is one of the commonest ways to lose "
                    f"a sentence."
                ),
                translation_hint=f"by {t.text}",
                grammar_ref="A&G 374", confidence=0.85,
            ))
            break
    return out


@detector("passive_periphrastic")
def _passive_periphrastic(sent: Sentence) -> list[Construction]:
    """Gerundive of obligation -- A&G 500."""
    out = []
    for t in sent:
        if not t.is_gerundive():
            continue
        cop = next((c for c in sent if c.lemma == "sum"
                    and (c.head == t.i or t.head == c.i)), None)
        if cop is None:
            # Without a copula this is a gerund/gerundive, not an obligation. The gerund
            # detector handles it; firing here would assert an obligation that is not there.
            continue
        toks = (t.i, cop.i)
        out.append(Construction(
            key="passive_periphrastic",
            name="Passive Periphrastic (gerundive of obligation)",
            latin_name="coniugatio periphrastica passiva",
            tokens=toks, anchor=t.i,
            evidence=(f"'{t.text}' is a gerundive"
                      + (f" with the copula '{cop.text}'" if cop else ", copula elided")),
            explanation=(
                f"The gerundive '{t.text}' with a form of *sum* expresses necessity or "
                f"obligation, not simple passivity: the action of *{t.lemma}*"
                + (f" ('{t.sense()}')" if t.sense() else "")
                + f" is something that *must* happen. This is the construction behind "
                  f"*Carthago delenda est*, 'Carthage must be destroyed'. The agent, if "
                  f"expressed, appears in the dative rather than with *ab*."
            ),
            translation_hint="must be … / ought to be …",
            grammar_ref="A&G 500", confidence=0.85,
        ))
    return out


@detector("greek_accusative")
def _greek_accusative(sent: Sentence) -> list[Construction]:
    """Accusative of respect, the 'Greek accusative' -- A&G 397b.

    A poetic Grecism: an accusative limiting an adjective or participle rather than
    receiving a verb's action. *Os umerosque deo similis* -- 'like a god AS TO his face and
    shoulders'. Keyed on an accusative depending on an adjective or a participle, with the
    noun typically a body part, and no preposition and no governing transitive verb.
    """
    out = []
    for t in sent:
        if t.case() != "Acc" or _has_preposition(sent, t):
            continue
        head = _head_of(sent, t)
        if head is None:
            continue
        head_is_adjectival = (
            head.pos == "ADJ"
            or head.morph.get("VerbForm") == "Part"
            or head.pos == "VERB" and head.morph.get("Voice") == "Pass"
        )
        if not head_is_adjectival:
            continue
        body_part = t.lemma in GREEK_ACC_NOUNS
        # Without a body-part noun, insist the head be a participle (the middle/reflexive
        # use, *cinctus tempora*). A plain adjective head with an ordinary noun produced a
        # false positive on *Italiam ... profugus* in Aen. 1.2, where *Italiam* actually
        # goes with *venit*.
        if not body_part and head.morph.get("VerbForm") != "Part":
            continue
        conf = 0.72 if body_part else 0.55
        out.append(Construction(
            key="greek_accusative",
            name="Accusative of Respect (Greek accusative)",
            latin_name="accusativus Graecus / accusativus respectus",
            tokens=(t.i, head.i), anchor=t.i,
            evidence=(f"'{t.text}' is accusative, governed by no preposition, and depends on "
                      f"'{head.text}', which is adjectival rather than transitive"
                      + (f"; '{t.lemma}' is a part of the body, the usual host of this "
                         f"construction" if body_part else "")),
            explanation=(
                f"'{t.text}' is an accusative of respect -- it specifies the respect IN WHICH "
                f"'{head.text}' is true, rather than receiving any action. Latin borrowed this "
                f"from Greek, and it is a marker of elevated, usually poetic style; Vergil uses "
                f"it constantly for physical description. Do not look for a verb governing it."
            ),
            translation_hint=f"in respect of {t.text} / as to {t.text}",
            grammar_ref="A&G 397b", confidence=conf,
            caveat=("Accusatives are usually objects. This reading only applies because the head "
                    "is adjectival; if the head turns out to be transitive, it is a plain object."),
        ))
    return out


@detector("ablative_deponent")
def _ablative_deponent(sent: Sentence) -> list[Construction]:
    """Ablative with utor, fruor, fungor, potior, vescor -- A&G 410."""
    out = []
    for t in sent:
        if t.case() != "Abl" or _has_preposition(sent, t):
            continue
        head = _head_of(sent, t)
        if head is None or head.lemma not in ABLATIVE_DEPONENTS:
            continue
        out.append(Construction(
            key="ablative_deponent",
            name="Ablative with a Special Deponent",
            latin_name="ablativus cum verbis deponentibus",
            tokens=(t.i, head.i), anchor=t.i,
            evidence=f"'{t.text}' is a bare ablative governed by the deponent '{head.lemma}'",
            explanation=(
                f"*{head.lemma}* is one of the five deponents that take an ablative instead of "
                f"an accusative (*utor, fruor, fungor, potior, vescor*). '{t.text}' looks like "
                f"an instrument because it is ablative, and historically that is exactly what it "
                f"is -- *utor* originally meant 'I benefit myself BY something'. Translate it as "
                f"an English direct object."
            ),
            translation_hint=f"(translate '{t.text}' as the object)",
            grammar_ref="A&G 410", confidence=0.9,
        ))
    return out


@detector("ablative_comparison")
def _ablative_comparison(sent: Sentence) -> list[Construction]:
    """Ablative of comparison -- A&G 406."""
    out = []
    has_quam = any(t.lemma == "quam" for t in sent)
    for t in sent:
        if t.case() != "Abl" or _has_preposition(sent, t):
            continue
        head = _head_of(sent, t)
        if head is None or head.degree() != "Cmp":
            continue
        out.append(Construction(
            key="ablative_comparison",
            name="Ablative of Comparison",
            latin_name="ablativus comparationis",
            tokens=(t.i, head.i), anchor=t.i,
            evidence=(f"'{t.text}' is a bare ablative depending on the comparative "
                      f"'{head.text}'" + ("; no *quam* present" if not has_quam else "")),
            explanation=(
                f"With a comparative, Latin may drop *quam* ('than') and put the thing compared "
                f"straight into the ablative. '{head.text} {t.text}' means '{head.text} than "
                f"{t.text}'. This is only available when the compared word would have been "
                f"nominative or accusative; otherwise *quam* is required."
            ),
            translation_hint=f"than {t.text}",
            grammar_ref="A&G 406", confidence=0.8 if not has_quam else 0.5,
        ))
    return out


@detector("dative_of_possession")
def _dative_of_possession(sent: Sentence) -> list[Construction]:
    """Dative of possession with sum -- A&G 373."""
    out = []
    for t in sent:
        if t.case() != "Dat" or _has_preposition(sent, t):
            continue
        head = _head_of(sent, t)
        if head is None:
            continue
        # *sum* may be the head, or -- far more often, since the parser makes the predicate
        # the root of a copular clause -- a `cop` child hanging off that predicate.
        cop = next((c for c in _children(sent, head.i) if c.dep == "cop" and c.lemma == "sum"), None)
        if head.lemma != "sum" and cop is None:
            continue
        # *deo similis erat* is a dative with an adjective, not possession, even though a
        # copula is present. The adjective governs the dative; *sum* is incidental.
        if head.lemma in DATIVE_ADJECTIVES:
            continue
        out.append(Construction(
            key="dative_of_possession",
            name="Dative of Possession",
            latin_name="dativus possessivus",
            tokens=(t.i, head.i), anchor=t.i,
            evidence=f"'{t.text}' is a bare dative with a form of *sum*",
            explanation=(
                f"*Sum* with a dative expresses possession: literally 'there is X TO {t.text}', "
                f"idiomatically '{t.text} has X'. The thing possessed is the grammatical subject, "
                f"in the nominative -- which is the reverse of the English arrangement. Latin "
                f"chooses this over *habeo* when the emphasis is on the thing possessed."
            ),
            translation_hint=f"{t.text} has …",
            grammar_ref="A&G 373", confidence=0.82,
        ))
    return out


@detector("dative_with_adjective")
def _dative_with_adjective(sent: Sentence) -> list[Construction]:
    """Dative with adjectives of likeness, nearness and fitness -- A&G 384."""
    out = []
    for t in sent:
        if t.case() != "Dat" or _has_preposition(sent, t):
            continue
        head = _head_of(sent, t)
        if head is None or head.lemma not in DATIVE_ADJECTIVES:
            continue
        out.append(Construction(
            key="dative_with_adjective",
            name="Dative with an Adjective",
            latin_name="dativus cum adiectivis",
            tokens=(t.i, head.i), anchor=t.i,
            evidence=f"'{t.text}' is a bare dative depending on the adjective '{head.lemma}'",
            explanation=(
                f"Adjectives meaning near, like, fit, friendly -- and their opposites -- take a "
                f"dative of the person or thing concerned. '{head.text} {t.text}' means "
                f"'{head.lemma} TO {t.text}'. Note that *similis* also takes the genitive, "
                f"traditionally for close personal resemblance and the dative for general "
                f"likeness, though the distinction is not observed consistently."
            ),
            translation_hint=f"{head.lemma} to/for {t.text}",
            grammar_ref="A&G 384", confidence=0.85,
        ))
    return out


@detector("indirect_statement")
def _indirect_statement(sent: Sentence) -> list[Construction]:
    """Accusative and infinitive -- A&G 579-580."""
    out = []
    for inf in sent:
        if inf.morph.get("VerbForm") != "Inf":
            continue
        head = _head_of(sent, inf)
        if head is None or head.lemma not in INDIRECT_STATEMENT_VERBS:
            continue
        subj = next((c for c in _children(sent, inf.i)
                     if c.dep in ("nsubj", "nsubj:pass", "obj") and c.case() == "Acc"), None)
        toks = tuple(sorted({inf.i, head.i} | ({subj.i} if subj else set())))
        tense = inf.morph.get("Tense")
        rel = {"Pres": "at the same time as", "Past": "before", "Fut": "after"}.get(tense, "relative to")
        out.append(Construction(
            key="indirect_statement",
            name="Indirect Statement (accusative and infinitive)",
            latin_name="oratio obliqua / accusativus cum infinitivo",
            tokens=toks, anchor=inf.i,
            evidence=(f"the infinitive '{inf.text}' depends on '{head.lemma}', a verb of saying "
                      f"or thinking" + (f", with accusative subject '{sent[subj.i].text}'" if subj else "")),
            explanation=(
                f"'{head.text}' introduces indirect statement, so what is reported goes into the "
                f"accusative-and-infinitive: the subject '{subj.text if subj else '(understood)'}' "
                f"is accusative and the verb is the infinitive '{inf.text}'. English needs 'that': "
                f"'{head.lemma}s that ...'. Crucially the infinitive's tense is *relative* to the "
                f"main verb, not absolute -- a {tense or 'present'} infinitive places the reported "
                f"action {rel} the act of saying."
            ),
            translation_hint=f"that {subj.text if subj else '…'} {inf.lemma}s",
            grammar_ref="A&G 579", confidence=0.85,
        ))
    return out


@detector("purpose_clause")
def _purpose_clause(sent: Sentence) -> list[Construction]:
    """Purpose and result clauses -- A&G 531, 537.

    Both use *ut* + subjunctive, so they are distinguished by the correlative: a *tam*,
    *ita*, *sic*, *adeo* or *tantus* in the main clause points to result. Negation
    disambiguates too -- purpose negates with *ne*, result with *ut non*.
    """
    out = []
    for mark in sent:
        if mark.lemma not in ("ut", "ne", "quo", "quominus") or mark.dep != "mark":
            continue
        verb = _head_of(sent, mark)
        if verb is None or verb.morph.get("Mood") != "Sub":
            continue
        correlative = next((t for t in sent if t.lemma in RESULT_CORRELATIVES), None)
        negated_non = any(t.lemma == "non" for t in _children(sent, verb.i))
        is_result = correlative is not None or (mark.lemma == "ut" and negated_non)
        if is_result:
            out.append(Construction(
                key="result_clause", name="Result Clause (consecutive)",
                latin_name="propositio consecutiva",
                tokens=(mark.i, verb.i), anchor=verb.i,
                evidence=(f"'{mark.text}' + subjunctive '{verb.text}'"
                          + (f", anticipated by the correlative '{correlative.text}'" if correlative else "")
                          + (", negated with *non* rather than *ne*" if negated_non else "")),
                explanation=(
                    f"This is a result clause: it states what actually followed, not what was "
                    f"intended. The giveaway is "
                    + (f"'{correlative.text}' in the main clause, which sets up the 'so ... that'." if correlative
                       else "the negative *non* rather than *ne*.")
                    + " Latin uses the subjunctive here even though the result is a fact -- the "
                      "mood marks the clause type, not any doubt about it."
                ),
                translation_hint="so ... that / with the result that",
                grammar_ref="A&G 537", confidence=0.75,
            ))
        else:
            neg = mark.lemma in ("ne", "quominus")
            out.append(Construction(
                key="purpose_clause", name="Purpose Clause (final)",
                latin_name="propositio finalis",
                tokens=(mark.i, verb.i), anchor=verb.i,
                evidence=(f"'{mark.text}' + subjunctive '{verb.text}', with no result correlative "
                          f"in the main clause"),
                explanation=(
                    f"This is a purpose clause: it gives the aim of the main action. "
                    + (f"*{mark.text}* is the negative form -- 'so that ... not', 'lest'. " if neg else "")
                    + f"The subjunctive is required because a purpose is not asserted as a fact "
                      f"but as something aimed at. Latin has no infinitive of purpose in classical "
                      f"prose, so this construction does the work English does with 'to ...'."
                    + (" *Quo* is used instead of *ut* when the clause contains a comparative."
                       if mark.lemma == "quo" else "")
                ),
                translation_hint=("so that ... not / lest" if neg else "in order to / so that"),
                grammar_ref="A&G 531", confidence=0.75,
            ))
    return out


@detector("cum_clause")
def _cum_clause(sent: Sentence) -> list[Construction]:
    """Cum-clauses -- A&G 545-549. Mood decides the flavour."""
    out = []
    for t in sent:
        if t.lemma != "cum" or t.dep != "mark":
            continue
        verb = _head_of(sent, t)
        if verb is None:
            continue
        mood = verb.morph.get("Mood")
        tense = verb.morph.get("Tense")
        if mood == "Sub":
            if tense in ("Past", "Pqp"):
                kind, hint = ("circumstantial or causal",
                              "when / since")
                expl = ("With the imperfect or pluperfect subjunctive, *cum* is circumstantial "
                        "or causal -- it describes the situation in which the main action took "
                        "place, or gives its reason. This is the ordinary narrative *cum* in "
                        "classical prose.")
            else:
                kind, hint = ("causal or concessive", "since / although")
                expl = ("*Cum* with the subjunctive here is causal ('since') or concessive "
                        "('although'). If the main clause contains *tamen*, it is concessive.")
            conf = 0.7
        else:
            kind, hint = ("purely temporal", "when")
            expl = ("*Cum* with the indicative is purely temporal -- it dates the main action "
                    "and asserts nothing about cause or circumstance. The indicative is the "
                    "signal: had the author wanted circumstance, the subjunctive was available.")
            conf = 0.8
        out.append(Construction(
            key="cum_clause", name=f"Cum-clause ({kind})",
            latin_name="propositio cum coniunctione 'cum'",
            tokens=(t.i, verb.i), anchor=verb.i,
            evidence=f"*cum* introducing '{verb.text}', which is {mood or 'unmarked'}"
                     + (f" {tense}" if tense else ""),
            explanation=expl, translation_hint=hint,
            grammar_ref="A&G 545-549", confidence=conf,
        ))
    return out


@detector("relative_characteristic")
def _relative_characteristic(sent: Sentence) -> list[Construction]:
    """Relative clause of characteristic -- A&G 535."""
    out = []
    for t in sent:
        if t.dep != "acl:relcl" or t.morph.get("Mood") != "Sub":
            continue
        rel = next((c for c in _children(sent, t.i) if c.lemma in ("qui", "quis")), None)
        out.append(Construction(
            key="relative_characteristic",
            name="Relative Clause of Characteristic",
            latin_name="propositio relativa characteristica",
            tokens=(t.i,) + ((rel.i,) if rel else ()), anchor=t.i,
            evidence=f"relative clause '{t.text}' stands in the subjunctive, not the indicative",
            explanation=(
                "A relative clause with the subjunctive does not identify a particular person or "
                "thing; it describes the *sort* of person or thing. 'There is nobody who would "
                "do this' -- the clause characterises rather than picks out. An indicative here "
                "would have made it a statement about a definite individual."
            ),
            translation_hint="the sort of … who / such as to",
            grammar_ref="A&G 535", confidence=0.7,
        ))
    return out


@detector("indirect_question")
def _indirect_question(sent: Sentence) -> list[Construction]:
    """Indirect question -- A&G 574."""
    out = []
    INTERROG = {"quis", "quid", "qualis", "quantus", "ubi", "unde", "quo", "quando",
                "cur", "quomodo", "quot", "uter", "num", "an", "necne", "-ne"}
    for t in sent:
        # The subjunctive verb's own dependency label is unreliable here -- the parser
        # labelled *venisset* in "rogavit quis venisset" as `nsubj`. What actually
        # identifies the construction is an interrogative word inside a subjunctive clause
        # that is subordinate to something, so only the ROOT is excluded.
        if t.morph.get("Mood") != "Sub" or t.dep == "ROOT":
            continue
        q = next((c for c in _children(sent, t.i) if c.lemma in INTERROG), None)
        if q is None:
            continue
        head = _head_of(sent, t)
        out.append(Construction(
            key="indirect_question", name="Indirect Question",
            latin_name="interrogatio obliqua",
            tokens=(q.i, t.i), anchor=t.i,
            evidence=(f"interrogative '{q.text}' introducing the subjunctive verb '{t.text}'"
                      + (f" under '{head.lemma}'" if head else "")),
            explanation=(
                f"'{q.text}' introduces an indirect question, and Latin puts its verb in the "
                f"subjunctive -- always, regardless of how factual the answer is. English keeps "
                f"the indicative here ('he asked who was coming'), so the subjunctive should not "
                f"be translated as doubt. Tense follows the sequence-of-tenses rule."
            ),
            translation_hint=f"{q.text} … (indicative in English)",
            grammar_ref="A&G 574", confidence=0.72,
        ))
    return out


@detector("accusative_duration")
def _accusative_duration(sent: Sentence) -> list[Construction]:
    """Accusative of duration and extent -- A&G 423, 425."""
    out = []
    for t in sent:
        if t.case() != "Acc" or _has_preposition(sent, t):
            continue
        if t.lemma not in TIME_NOUNS and t.lemma not in ("passus", "pes", "miliarium", "stadium"):
            continue
        head = _head_of(sent, t)
        if head is None or head.pos not in ("VERB", "AUX", "ADJ"):
            continue
        spatial = t.lemma in ("passus", "pes", "miliarium", "stadium")
        out.append(Construction(
            key="accusative_duration",
            name="Accusative of Extent" + (" (space)" if spatial else " (duration of time)"),
            latin_name="accusativus extensionis",
            tokens=(t.i,), anchor=t.i,
            evidence=(f"'{t.text}' is a bare accusative of "
                      f"{'distance' if spatial else 'time'} depending on '{head.text}'"),
            explanation=(
                f"A bare accusative measures *how long* or *how far*, without a preposition. "
                f"Contrast the ablative, which would give time *when* or *within which*. The "
                f"case alone carries the distinction: accusative extends, ablative locates."
            ),
            translation_hint=("for a distance of …" if spatial else "for … (duration)"),
            grammar_ref="A&G 423, 425", confidence=0.7,
        ))
    return out


@detector("ablative_time")
def _ablative_time(sent: Sentence) -> list[Construction]:
    """Ablative of time when or within which -- A&G 423."""
    out = []
    for t in sent:
        if t.case() != "Abl" or t.lemma not in TIME_NOUNS or _has_preposition(sent, t):
            continue
        out.append(Construction(
            key="ablative_time", name="Ablative of Time When / Within Which",
            latin_name="ablativus temporis",
            tokens=(t.i,), anchor=t.i,
            evidence=f"'{t.text}' is a bare ablative of a time-word, governed by no preposition",
            explanation=(
                f"A bare ablative of a time-word gives the time *at which* (or *within which*) "
                f"something happens. No preposition is used or needed -- the case does the work. "
                f"If it were accusative it would instead measure duration."
            ),
            translation_hint=f"in / at / within the {t.text}",
            grammar_ref="A&G 423", confidence=0.75,
        ))
    return out


@detector("genitive_memory")
def _genitive_memory(sent: Sentence) -> list[Construction]:
    """Genitive with verbs of remembering and impersonals of feeling -- A&G 350, 354."""
    out = []
    for t in sent:
        if t.case() != "Gen":
            continue
        head = _head_of(sent, t)
        if head is None:
            continue
        if head.lemma in GENITIVE_MEMORY_VERBS:
            out.append(Construction(
                key="genitive_memory", name="Genitive with a Verb of Remembering",
                latin_name="genetivus memoriae",
                tokens=(t.i, head.i), anchor=t.i,
                evidence=f"'{t.text}' is genitive under '{head.lemma}', a verb of memory",
                explanation=(
                    f"*{head.lemma}* takes a genitive of the thing remembered or forgotten. "
                    f"Translate '{t.text}' as an English object; the genitive is a survival of an "
                    f"older sense, 'to be mindful OF'."
                ),
                translation_hint=f"(treat '{t.text}' as the object)",
                grammar_ref="A&G 350", confidence=0.85,
            ))
        elif head.lemma in GENITIVE_IMPERSONALS:
            out.append(Construction(
                key="genitive_impersonal", name="Genitive with an Impersonal of Feeling",
                latin_name="genetivus cum verbis impersonalibus",
                tokens=(t.i, head.i), anchor=t.i,
                evidence=f"'{t.text}' is genitive under the impersonal '{head.lemma}'",
                explanation=(
                    f"*{head.lemma}* is impersonal: the person feeling is accusative and the "
                    f"cause of the feeling -- here '{t.text}' -- is genitive. *Me paenitet "
                    f"stultitiae* is literally 'it repents me of my folly', i.e. 'I regret my "
                    f"folly'. There is no nominative subject at all."
                ),
                translation_hint=f"… of {t.text}",
                grammar_ref="A&G 354", confidence=0.85,
            ))
    return out


@detector("fear_clause")
def _fear_clause(sent: Sentence) -> list[Construction]:
    """Clauses of fearing -- A&G 564. The polarity inverts."""
    out = []
    for t in sent:
        if t.lemma not in ("ne", "ut") or t.dep != "mark":
            continue
        verb = _head_of(sent, t)
        if verb is None or verb.morph.get("Mood") != "Sub":
            continue
        head = _head_of(sent, verb)
        if head is None or head.lemma not in FEARING_VERBS:
            continue
        feared = t.lemma == "ne"
        out.append(Construction(
            key="fear_clause", name="Clause of Fearing",
            latin_name="propositio timoris",
            tokens=(t.i, verb.i, head.i), anchor=verb.i,
            evidence=f"'{t.text}' + subjunctive under the verb of fearing '{head.lemma}'",
            explanation=(
                "After a verb of fearing the particles reverse their usual sense: *ne* introduces "
                "what you are afraid WILL happen, and *ut* what you are afraid will NOT happen. "
                + (f"Here *{t.text}* means 'that ... will'." if feared
                   else f"Here *{t.text}* means 'that ... will not'.")
                + " The clause was originally an independent wish ('may it not happen!'), which "
                  "is why the polarity looks inverted."
            ),
            translation_hint=("that … (will happen)" if feared else "that … not (will fail to)"),
            grammar_ref="A&G 564", confidence=0.8,
        ))
    return out


@detector("double_dative")
def _double_dative(sent: Sentence) -> list[Construction]:
    """Double dative: dative of purpose + dative of reference -- A&G 382."""
    out = []
    for verb in sent:
        if verb.pos not in ("VERB", "AUX"):
            continue
        datives = [c for c in _children(sent, verb.i)
                   if c.case() == "Dat" and not _has_preposition(sent, c)]
        if len(datives) < 2:
            continue
        purpose, reference = datives[0], datives[1]
        out.append(Construction(
            key="double_dative", name="Double Dative",
            latin_name="dativus finalis cum dativo commodi",
            tokens=(purpose.i, reference.i, verb.i), anchor=purpose.i,
            evidence=f"two bare datives, '{purpose.text}' and '{reference.text}', under '{verb.text}'",
            explanation=(
                f"Two datives with one verb: one of purpose (what the thing serves AS) and one of "
                f"reference (whom it serves FOR). The idiom *auxilio venire alicui* means 'to come "
                f"AS a help TO someone'. Identify which is which by asking which could be replaced "
                f"by a person -- that one is the dative of reference."
            ),
            translation_hint="as a … for/to …",
            grammar_ref="A&G 382", confidence=0.65,
            caveat="Depends on the parser attaching both datives to the same verb.",
        ))
    return out


@detector("locative_and_place")
def _locative_and_place(sent: Sentence) -> list[Construction]:
    """Locative and prepositionless place constructions -- A&G 427."""
    out = []
    for t in sent:
        if _has_preposition(sent, t):
            continue
        if t.case() == "Loc":
            out.append(Construction(
                key="locative", name="Locative Case",
                latin_name="locativus", tokens=(t.i,), anchor=t.i,
                evidence=f"'{t.text}' is in the locative",
                explanation=(
                    "The locative is a rare sixth case surviving only in names of towns and "
                    "small islands and a few nouns (*domi*, *ruri*, *humi*, *belli*, *militiae*). "
                    "It expresses place where without a preposition. In the first and second "
                    "declensions singular it looks like the genitive; elsewhere like the ablative."
                ),
                translation_hint=f"at/in {t.text}",
                grammar_ref="A&G 427", confidence=0.9,
            ))
        elif t.case() == "Acc" and (t.ent == "LOC" or t.lemma in PLACE_EXCEPTIONS):
            head = _head_of(sent, t)
            # Requiring a verb of motion is what keeps this off ordinary objects. Without
            # it the rule fired on *Caesarem* in "dicit Caesarem venire" -- an accusative
            # subject of an infinitive, not a destination.
            if (head and head.lemma in MOTION_VERBS
                    and t.dep in ("obl", "obj", "advmod", "nmod")):
                out.append(Construction(
                    key="accusative_place_to_which",
                    name="Accusative of Place to Which (no preposition)",
                    latin_name="accusativus loci",
                    tokens=(t.i,), anchor=t.i,
                    evidence=f"'{t.text}' is accusative with a verb of motion and no preposition",
                    explanation=(
                        "Names of towns and small islands, plus *domum*, *rus* and *foras*, take "
                        "a bare accusative for motion towards -- *ad* is omitted. With any other "
                        "noun the preposition would be obligatory, so its absence here is the "
                        "grammatical signal, not an ellipsis."
                    ),
                    translation_hint=f"to {t.text}",
                    grammar_ref="A&G 427", confidence=0.6,
                    caveat="A bare accusative is far more often a direct object; check the verb "
                           "is one of motion.",
                ))
    return out


@detector("gerund_gerundive")
def _gerund_gerundive(sent: Sentence) -> list[Construction]:
    """Gerund vs gerundive -- A&G 502-507."""
    out = []
    for t in sent:
        if not t.is_gerundive():
            continue
        # A gerundive with a copula is the passive periphrastic, already reported.
        if any(c.lemma == "sum" and (c.head == t.i or t.head == c.i) for c in sent):
            continue
        prep = _has_preposition(sent, t)
        out.append(Construction(
            key="gerund", name="Gerund",
            latin_name="gerundium", tokens=(t.i,), anchor=t.i,
            evidence=f"'{t.text}' is a gerund ({t.case() or 'oblique'} case)"
                     + (f", governed by *{prep.text}*" if prep else ""),
            explanation=(
                f"The gerund is a verbal noun -- the '-ing' form of *{t.lemma}*"
                + (f" ('{t.sense()}')" if t.sense() else "")
                + f" -- and supplies the cases the "
                f"infinitive lacks. It is active and neuter singular, and has no nominative "
                f"(the infinitive serves there). "
                + (f"With *{prep.text}* + accusative it commonly expresses purpose."
                   if prep and prep.lemma == "ad" else
                   ("The genitive with *causa* or *gratia* also expresses purpose."
                    if t.case() == "Gen" else
                    "The bare ablative expresses means: 'by ...ing'."
                    if t.case() == "Abl" else ""))
                + " If it had a direct object, Latin would usually prefer the gerundive "
                  "construction instead, making the object agree with the verbal adjective."
            ),
            translation_hint="…-ing (verbal noun)",
            grammar_ref="A&G 502", confidence=0.8,
        ))
    return out


@detector("supine")
def _supine(sent: Sentence) -> list[Construction]:
    """Supines -- A&G 509-510."""
    out = []
    for t in sent:
        if t.morph.get("VerbForm") != "Sup":
            continue
        acc = t.text.endswith("um")
        out.append(Construction(
            key="supine", name="Supine" + (" (accusative, purpose)" if acc else " (ablative, respect)"),
            latin_name="supinum", tokens=(t.i,), anchor=t.i,
            evidence=f"'{t.text}' is a supine",
            explanation=(
                ("The accusative supine in *-um* expresses purpose after a verb of motion: "
                 "*legatos misit rogatum auxilium*, 'he sent envoys TO ASK for help'. It is the "
                 "one place classical prose allows something close to an infinitive of purpose."
                 ) if acc else
                ("The ablative supine in *-u* is one of the rarest forms in Latin, used with "
                 "adjectives to specify respect: *mirabile dictu*, 'wonderful TO SAY'. It occurs "
                 "with barely a dozen verbs.")
            ),
            translation_hint=("to …" if acc else "to … / in the …ing"),
            grammar_ref="A&G 509", confidence=0.8,
        ))
    return out


@detector("subjunctive_independent")
def _subjunctive_independent(sent: Sentence) -> list[Construction]:
    """Independent uses of the subjunctive -- A&G 439-447."""
    out = []
    for t in sent:
        if t.morph.get("Mood") != "Sub" or t.dep != "ROOT":
            continue
        person = t.morph.get("Person")
        tense = t.morph.get("Tense")
        negated = any(c.lemma in ("ne", "non") for c in _children(sent, t.i))
        if person == "1":
            kind = "Hortatory" if t.number() == "Plur" else "Deliberative"
            expl = ("A first-person subjunctive in a main clause exhorts ('let us ...') when "
                    "plural, or deliberates ('am I to ...?') when singular and questioning. "
                    "Negative is *ne*, never *non*.")
            hint = "let us … / am I to …?"
        elif person == "3":
            kind = "Jussive"
            expl = ("A third-person subjunctive in a main clause gives a command -- Latin's way "
                    "of saying 'let him ...', since the imperative exists only in the second "
                    "person. Negative is *ne*.")
            hint = "let him/her/it …"
        else:
            kind = "Optative or Potential"
            expl = ("A second-person subjunctive standing alone is usually potential ('you "
                    "would ...') or, with *utinam*, optative ('if only you would ...').")
            hint = "you would … / may you …"
        out.append(Construction(
            key="subjunctive_independent", name=f"{kind} Subjunctive",
            latin_name="coniunctivus independens",
            tokens=(t.i,), anchor=t.i,
            evidence=(f"'{t.text}' is a {tense or ''} subjunctive as the main verb, person "
                      f"{person or '?'}" + (", negated with *ne*" if negated else "")),
            explanation=expl, translation_hint=hint,
            grammar_ref="A&G 439-444", confidence=0.7,
        ))
    return out


# --------------------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------------------

#: Every construction this module can report, for the UI's reference index.
CONSTRUCTION_INDEX = {
    "ablative_absolute": ("Ablative Absolute", "A&G 419"),
    "ablative_absolute_nominal": ("Ablative Absolute (nominal)", "A&G 419a"),
    "partitive_genitive": ("Partitive Genitive", "A&G 346"),
    "dative_special_verb": ("Dative with a Special Verb", "A&G 367"),
    "dative_of_agent": ("Dative of Agent", "A&G 374"),
    "passive_periphrastic": ("Passive Periphrastic", "A&G 500"),
    "greek_accusative": ("Accusative of Respect (Greek accusative)", "A&G 397b"),
    "ablative_deponent": ("Ablative with a Special Deponent", "A&G 410"),
    "ablative_comparison": ("Ablative of Comparison", "A&G 406"),
    "dative_of_possession": ("Dative of Possession", "A&G 373"),
    "indirect_statement": ("Indirect Statement", "A&G 579"),
    "purpose_clause": ("Purpose Clause", "A&G 531"),
    "result_clause": ("Result Clause", "A&G 537"),
    "cum_clause": ("Cum-clause", "A&G 545-549"),
    "relative_characteristic": ("Relative Clause of Characteristic", "A&G 535"),
    "indirect_question": ("Indirect Question", "A&G 574"),
    "accusative_duration": ("Accusative of Extent", "A&G 423, 425"),
    "ablative_time": ("Ablative of Time", "A&G 423"),
    "genitive_memory": ("Genitive with a Verb of Remembering", "A&G 350"),
    "genitive_impersonal": ("Genitive with an Impersonal", "A&G 354"),
    "fear_clause": ("Clause of Fearing", "A&G 564"),
    "double_dative": ("Double Dative", "A&G 382"),
    "locative": ("Locative Case", "A&G 427"),
    "accusative_place_to_which": ("Accusative of Place to Which", "A&G 427"),
    "gerund": ("Gerund", "A&G 502"),
    "supine": ("Supine", "A&G 509"),
    "dative_with_adjective": ("Dative with an Adjective", "A&G 384"),
    "subjunctive_independent": ("Independent Subjunctive", "A&G 439-444"),
}


def detect_all(sent: Sentence) -> list[Construction]:
    """Run every detector over one parsed sentence.

    Overlaps are kept deliberately: the reader is better served by two competing readings
    with their confidences than by a silent arbitration. Results are ordered by confidence
    so the interface can show the strongest first.
    """
    found: list[Construction] = []
    for _key, fn in DETECTORS:
        try:
            found.extend(fn(sent))
        except Exception:
            # One broken rule must never take down the analysis of a whole passage.
            continue
    found.sort(key=lambda c: -c.confidence)
    return found

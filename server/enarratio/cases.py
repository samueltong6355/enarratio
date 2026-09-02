"""The complete inventory of Latin case usage.

:mod:`enarratio.constructions` detects the constructions a student meets by name -- the
ablative absolute, indirect statement, the passive periphrastic. This module covers the
other half of the syllabus: what an oblique case is *doing* in its sentence. It is the
question every translation exercise turns on, because Latin's five working cases carry
between them some sixty distinct functions, and the ending alone never says which.

The ablative is the extreme case. Latin merged three Indo-European cases into one form --
the ablative proper (*from*), the instrumental (*with*), and the locative (*in*) -- so a
single ending can mean separation, means, manner, accompaniment, price, respect, cause,
place or time. Nothing in the morphology distinguishes them. What distinguishes them is
the governing word, the presence or absence of a preposition, and the semantic class of
the noun, and those are exactly what a parse plus a few closed lexical lists can supply.

Every detector states the evidence that fired it and cites Allen & Greenough, and several
deliberately overlap: *magno labore* is means and manner at once, and a reader is better
served by seeing both readings than by an arbitrary choice between them.
"""

from __future__ import annotations

from .constructions import (
    Construction, DATIVE_ADJECTIVES, DATIVE_VERBS, Sentence, TIME_NOUNS, Tok,
    _children, _has_preposition, _head_of, detector,
)

__all__ = ["CASE_USE_INDEX"]


# --------------------------------------------------------------------------------------
# Lexical classes. These are what make case-usage detection possible: a bare ablative is
# ambiguous between a dozen uses, but a bare ablative governed by *emo* is a price.
# --------------------------------------------------------------------------------------

#: Adjectives governing the genitive -- A&G 349.
GENITIVE_ADJECTIVES = {
    "cupidus", "avidus", "studiosus", "peritus", "imperitus", "memor", "immemor",
    "plenus", "inanis", "expers", "particeps", "conscius", "inscius", "ignarus", "gnarus",
    "similis", "dissimilis", "proprius", "communis", "dives", "egenus", "indigus",
    "capax", "tenax", "peculiaris", "peritus", "peritissimus", "reus",
}

#: Verbs of valuing, which take a genitive of indefinite value -- A&G 417.
VALUING_VERBS = {"aestimo", "facio", "duco", "puto", "habeo", "pendo", "existimo"}
VALUE_GENITIVES = {"magnus", "parvus", "tantus", "quantus", "plus", "minor", "nihilum",
                   "maximus", "minimus", "pluris", "flocci", "nauci", "assis"}

#: Verbs of buying, selling and costing, which take an ablative of price -- A&G 416.
PRICE_VERBS = {"emo", "vendo", "veneo", "consto", "sto", "liceo", "conduco", "loco",
               "redimo", "muto", "commuto"}

#: Verbs of accusing and condemning: genitive of the charge -- A&G 352.
CHARGE_VERBS = {"accuso", "damno", "condemno", "arguo", "insimulo", "convinco", "absolvo",
                "coarguo", "postulo", "defero"}

#: Verbs of filling and lacking: genitive or ablative -- A&G 356, 401.
PLENTY_WANT_VERBS = {"impleo", "compleo", "expleo", "repleo", "egeo", "indigeo", "careo",
                     "vaco", "abundo", "affluo", "orbo", "privo", "spolio", "nudo",
                     "libero", "solvo", "levo", "exuo", "fraudo"}

#: Verbs of separation, which take the ablative with or without a preposition -- A&G 400.
SEPARATION_VERBS = {"abstineo", "cedo", "decedo", "discedo", "excedo", "desisto", "absum",
                    "removeo", "prohibeo", "arceo", "deterreo", "expello", "eicio",
                    "pello", "moveo", "libero", "solvo", "exsolvo", "interdico"}

#: Participles and adjectives of origin: ablative of source -- A&G 403.
#: The tagger lemmatises these to the deponent verb, not to the participle, so both forms
#: are listed.
ORIGIN_WORDS = {"natus", "ortus", "genitus", "creatus", "satus", "editus", "prognatus",
                "oriundus", "nascor", "orior", "gigno", "sero", "edo", "creo"}

#: Verbs of teaching, asking, concealing and demanding: two accusatives -- A&G 396.
TWO_ACC_VERBS = {"doceo", "edoceo", "rogo", "interrogo", "celo", "posco", "reposco",
                 "flagito", "oro", "exoro", "moneo", "admoneo", "commoneo"}

#: Verbs of making, calling, choosing and regarding: object + predicate accusative -- A&G 393.
PREDICATE_ACC_VERBS = {"facio", "efficio", "reddo", "creo", "designo", "declaro", "appello",
                       "voco", "nomino", "dico", "habeo", "duco", "existimo", "puto",
                       "iudico", "eligo", "deligo", "constituo", "praeficio"}

#: Verbs of giving, telling and showing: the ordinary indirect object -- A&G 362.
GIVING_VERBS = {"do", "dono", "reddo", "trado", "tribuo", "concedo", "praebeo", "offero",
                "mitto", "nuntio", "dico", "narro", "monstro", "ostendo", "commendo",
                "scribo", "respondeo", "promitto", "polliceor", "permitto", "committo",
                "adfero", "affero", "impertio", "largior", "attribuo"}

#: Prefixes whose compounds take a dative -- A&G 370.
DATIVE_COMPOUND_PREFIXES = ("ad", "ante", "circum", "com", "con", "in", "inter", "ob",
                            "prae", "pro", "sub", "super", "post", "re")

#: Nouns that appear as the dative of purpose -- A&G 382. Nearly a closed list.
PURPOSE_DATIVES = {"auxilium", "praesidium", "subsidium", "usus", "cura", "odium",
                   "honor", "dedecus", "exemplum", "documentum", "impedimentum",
                   "detrimentum", "saluti", "bonum", "malum", "argumentum", "testimonium"}

#: Verbs taking a dative of separation -- A&G 381.
DATIVE_SEPARATION_VERBS = {"eripio", "adimo", "detraho", "aufero", "demo", "surripio",
                           "extorqueo", "excutio"}

#: Abstract nouns of emotion, the usual ablative of cause -- A&G 404.
CAUSE_NOUNS = {"metus", "timor", "ira", "dolor", "gaudium", "laetitia", "amor", "odium",
               "spes", "desperatio", "cupiditas", "avaritia", "invidia", "misericordia",
               "pudor", "terror", "fames", "inopia", "vis", "virtus", "iussus", "fides"}

#: Nouns of respect: the ablative of specification -- A&G 418.
RESPECT_NOUNS = {"natus", "natu", "nomen", "genus", "numerus", "natura", "specie", "aetas", "corpus",
                 "animus", "mens", "ingenium", "virtus", "pes", "manus", "lingua", "res",
                 "modus", "ratio", "consilium", "opinio", "vita", "moribus", "facies"}

#: Nouns of manner: an ablative of these, with or without *cum* -- A&G 412.
MANNER_NOUNS = {"modus", "ratio", "mos", "consuetudo", "silentium", "clamor", "cura",
                "diligentia", "celeritas", "virtus", "studium", "labor", "vis", "ira",
                "gaudium", "voluntas", "iure", "iniuria", "casus", "fraus", "dolus"}

#: Words of measure, used with a comparative -- A&G 414.
DEGREE_WORDS = {"multus", "paulus", "paulum", "tantus", "quantus", "aliquantus", "nihil",
                "nihilum", "dimidium", "altero"}

#: Route words: the ablative of way -- A&G 429.a.
ROUTE_NOUNS = {"via", "iter", "terra", "mare", "flumen", "porta", "pons", "campus"}


def _governing_verb(sent: Sentence, t: Tok) -> Tok | None:
    """The nearest verb above a token, not merely its immediate head.

    The parser routinely hangs an oblique noun off the neighbouring noun rather than off
    the verb that governs it -- *avaritiae* in "accusavit Verrem avaritiae" is attached to
    *Verrem*, and *puellae* in "librum puellae dedit" to *librum*. Rules keyed on a verb's
    lemma therefore have to climb.
    """
    seen: set[int] = set()
    cur = t
    for _ in range(6):
        if cur.i in seen:
            break
        seen.add(cur.i)
        nxt = _head_of(sent, cur)
        if nxt is None:
            break
        if nxt.pos in ("VERB", "AUX"):
            return nxt
        cur = nxt
    return None


#: Whitaker case abbreviations as they appear in a candidate parse.
_WW_CASE = {"Nom": "NOM", "Gen": "GEN", "Dat": "DAT", "Acc": "ACC", "Abl": "ABL", "Voc": "VOC"}


def _could_be(t: Tok, case: str) -> bool:
    """Could this form be in ``case``, whatever the parser decided?

    Latin's first declension writes the genitive and dative singular identically, and the
    morphologizer picks one. It read *gloriae* in "cupidus gloriae" as a dative, which no
    genitive rule could then fire on. Whitaker's analyser enumerates every possibility, so
    it can be consulted when the parser's single answer blocks an otherwise strong reading.
    """
    if t.case() == case:
        return True
    want = _WW_CASE.get(case, case.upper())
    return any((c.get("case") or "").upper() == want for c in t.candidates if isinstance(c, dict))


def _looks_like_gerund(t: Tok) -> bool:
    """Gerund or gerundive by ending, for when the tagger has given up entirely.

    *Legendo* in "legendo discimus" comes back tagged as a proper noun, so no
    morphological test can find it. The *-nd-* stem is unmistakable in Latin.
    """
    if t.is_gerundive():
        return True
    form = t.text.lower().replace("v", "u").replace("j", "i")
    return form.endswith(("ndum", "ndi", "ndo", "ndae", "ndis", "ndorum", "ndarum"))


def _prep_lemma(sent: Sentence, t: Tok) -> str | None:
    p = _has_preposition(sent, t)
    return p.lemma.lower().replace("v", "u") if p else None


def _is_bare(sent: Sentence, t: Tok) -> bool:
    return _has_preposition(sent, t) is None


def _make(key, name, latin, tokens, anchor, evidence, explanation, hint, ref, conf,
          caveat=""):
    return Construction(
        key=key, name=name, latin_name=latin, tokens=tuple(tokens), anchor=anchor,
        evidence=evidence, explanation=explanation, translation_hint=hint,
        grammar_ref=ref, confidence=conf, caveat=caveat,
    )


# ======================================================================================
# GENITIVE -- A&G 342-359
# ======================================================================================


@detector("genitive_uses")
def _genitive_uses(sent: Sentence) -> list[Construction]:
    out: list[Construction] = []
    for t in sent:
        head = _head_of(sent, t)
        if head is None:
            continue
        hl, tl = head.lemma.lower(), t.lemma.lower()
        if t.case() != "Gen":
            # The one exception to trusting the parser's case: a genitive-governing
            # adjective is strong enough evidence to override it, since the ambiguity is
            # purely orthographic (first-declension -ae is genitive or dative alike).
            if hl in GENITIVE_ADJECTIVES and _could_be(t, "Gen"):
                out.append(_make(
                    "genitive_with_adjective", "Genitive with an Adjective",
                    "genetivus cum adiectivis", (t.i, head.i), t.i,
                    f"'{head.lemma}' governs a genitive, and '{t.text}' can be genitive -- "
                    f"though the parser read it as {(t.case() or 'unmarked').lower()}",
                    f"Adjectives of desire, knowledge, memory and fullness take a genitive of "
                    f"the thing concerned. First-declension *-ae* is genitive and dative "
                    f"alike, so the form alone cannot decide; *{head.lemma}* does.",
                    f"of {t.text}", "A&G 349", 0.6,
                    caveat="The parser read this as another case; the adjective is the "
                           "evidence for taking it as genitive."))
            continue

        # --- genitive with an adjective (A&G 349) ---
        if hl in GENITIVE_ADJECTIVES:
            out.append(_make(
                "genitive_with_adjective", "Genitive with an Adjective",
                "genetivus cum adiectivis", (t.i, head.i), t.i,
                f"'{t.text}' is genitive under the adjective '{head.lemma}'",
                f"Adjectives of desire, knowledge, memory, fullness and sharing take a "
                f"genitive of the thing concerned. *{head.lemma}* is one of them, so "
                f"'{t.text}' names what the {head.text} is full of, mindful of, or eager for.",
                f"of {t.text}", "A&G 349", 0.85))
            continue

        # --- genitive of the charge (A&G 352) ---
        gov = _governing_verb(sent, t)
        if hl in CHARGE_VERBS or (gov is not None and gov.lemma.lower() in CHARGE_VERBS):
            head = gov if hl not in CHARGE_VERBS and gov is not None else head
            out.append(_make(
                "genitive_of_charge", "Genitive of the Charge",
                "genetivus criminis", (t.i, head.i), t.i,
                f"'{t.text}' is genitive under '{head.lemma}', a verb of accusing or condemning",
                f"Verbs of accusing, convicting and acquitting put the charge in the "
                f"genitive: *{head.lemma} {t.text}* is to accuse (or condemn) *of* "
                f"{t.text}. The penalty, if named, goes into the ablative.",
                f"of {t.text} / on a charge of {t.text}", "A&G 352", 0.85))
            continue

        # --- genitive of value (A&G 417) ---
        if tl in VALUE_GENITIVES and (hl in VALUING_VERBS or
                                      (gov is not None and gov.lemma.lower() in VALUING_VERBS)):
            head = head if hl in VALUING_VERBS else gov
            out.append(_make(
                "genitive_of_value", "Genitive of Indefinite Value",
                "genetivus pretii", (t.i, head.i), t.i,
                f"'{t.text}' is one of the value-genitives, under the verb of valuing "
                f"'{head.lemma}'",
                f"Verbs of valuing take a genitive of *indefinite* worth -- *magni*, "
                f"*parvi*, *tanti*, *pluris*. It says how highly a thing is rated, not what "
                f"it costs; a definite price would be ablative instead.",
                f"at {t.text} worth / very highly, very little", "A&G 417", 0.8))
            continue

        # --- genitive with impersonal interest / refert (A&G 355) ---
        if hl in ("interest", "refert", "intersum"):
            out.append(_make(
                "genitive_with_interest", "Genitive with *interest* / *refert*",
                "genetivus cum 'interest'", (t.i, head.i), t.i,
                f"'{t.text}' is genitive with the impersonal '{head.lemma}'",
                f"*Interest* and *refert* -- 'it matters to' -- take a genitive of the "
                f"person concerned. The personal pronouns are the exception: they use the "
                f"ablative feminine possessive (*mea*, *tua*, *nostra*) instead.",
                f"it matters to {t.text}", "A&G 355", 0.8))
            continue

        # --- verbal noun: subjective vs objective (A&G 347-348) ---
        if head.pos in ("NOUN", "PROPN"):
            verbal = hl.endswith(("tio", "sio", "tus", "sus", "or", "men", "ntia", "ura"))
            animate = t.pos == "PROPN" or tl.endswith(("or", "tor", "sor")) or t.pos == "PRON"
            if verbal:
                out.append(_make(
                    "genitive_subjective", "Subjective Genitive",
                    "genetivus subiectivus", (t.i, head.i), t.i,
                    f"'{t.text}' depends on '{head.text}', a noun of action or feeling"
                    + (f"; '{t.text}' names a person, the likelier agent" if animate else ""),
                    f"*{head.text}* names an action or feeling, so *{t.text}* may be the one "
                    f"who *does* or *feels* it -- 'the {t.text}'s {head.text}'. The same "
                    f"phrase can equally be objective ('{head.text} directed AT {t.text}'), "
                    f"and only the sense of the passage decides. *Amor patris* is either the "
                    f"father's love or love for the father.",
                    f"{t.text}'s {head.text}", "A&G 343.a", 0.55 if animate else 0.45,
                    caveat="Subjective and objective genitives are formally identical; this "
                           "is a reading, not a parse."))
                out.append(_make(
                    "genitive_objective", "Objective Genitive",
                    "genetivus obiectivus", (t.i, head.i), t.i,
                    f"'{t.text}' depends on '{head.text}', a noun of action or feeling",
                    f"*{head.text}* implies a verb, and *{t.text}* may be its *object*: "
                    f"'{head.text} of/for {t.text}', where {t.text} is what the action is "
                    f"directed at. English often needs a different preposition -- *metus "
                    f"hostium* is 'fear OF the enemy', not 'the enemy's fear'.",
                    f"{head.text} for/of {t.text}", "A&G 347", 0.5,
                    caveat="Formally identical to the subjective genitive; decide from sense."))
                continue

            # --- genitive of description (A&G 345) ---
            has_adj = any(c.case() == "Gen" and c.pos == "ADJ" for c in _children(sent, t.i))
            if has_adj:
                out.append(_make(
                    "genitive_of_description", "Genitive of Description (Quality)",
                    "genetivus qualitatis", (t.i, head.i), t.i,
                    f"'{t.text}' is genitive with an adjective of its own, describing "
                    f"'{head.text}'",
                    f"A genitive carrying its own adjective describes a quality: *vir magnae "
                    f"virtutis*, 'a man of great courage'. The adjective is obligatory -- a "
                    f"bare genitive cannot describe in this way.",
                    f"of {t.text}", "A&G 345", 0.7))
                continue

            # --- possessive (A&G 343) ---
            out.append(_make(
                "genitive_possessive", "Possessive Genitive",
                "genetivus possessivus", (t.i, head.i), t.i,
                f"'{t.text}' is genitive depending on the noun '{head.text}'",
                f"The commonest use of the case: *{t.text}* owns, belongs to, or is "
                f"otherwise attached to *{head.text}*. English marks it with 'of' or an "
                f"apostrophe.",
                f"{t.text}'s {head.text} / the {head.text} of {t.text}", "A&G 343", 0.6,
                caveat="A genitive on a noun may instead be partitive, descriptive, "
                       "subjective or objective; possession is only the default reading."))
            continue

        # --- predicate genitive (A&G 343.b) ---
        # *Sapientis est* -- the genitive is predicated through a copula that the parser
        # rarely makes its head; what identifies the construction is a genitive in a clause
        # containing *sum* and depending on something other than a noun.
        if (hl == "sum" or any(c.lemma == "sum" for c in _children(sent, head.i))
                or (gov is not None and gov.lemma == "sum")
                or (head.pos not in ("NOUN", "PROPN")
                    and any(c.lemma == "sum" for c in sent))):
            out.append(_make(
                "genitive_predicate", "Predicate Genitive",
                "genetivus praedicativus", (t.i, head.i), t.i,
                f"'{t.text}' is genitive as the complement of *sum*",
                f"A genitive with *sum* says whose a thing is, or -- idiomatically -- that "
                f"it is characteristic of someone: *sapientis est* means 'it is the mark of "
                f"a wise man'. Supply 'the part', 'the duty' or 'the mark' in English.",
                f"it is the mark/duty of {t.text}", "A&G 343.b", 0.6))
    return out


# ======================================================================================
# DATIVE -- A&G 360-385
# ======================================================================================


@detector("dative_uses")
def _dative_uses(sent: Sentence) -> list[Construction]:
    out: list[Construction] = []
    datives = [t for t in sent if t.case() == "Dat" and _is_bare(sent, t)]
    for t in datives:
        head = _head_of(sent, t)
        if head is None:
            continue
        # The verb that governs a dative is often not its parse head: "librum puellae
        # dedit" attaches *puellae* to *librum*.
        if head.pos not in ("VERB", "AUX", "ADJ"):
            gov = _governing_verb(sent, t)
            if gov is not None:
                head = gov
        hl = head.lemma.lower()

        # Handled with fuller explanations in constructions.py.
        if hl in DATIVE_VERBS or hl in DATIVE_ADJECTIVES or hl == "sum":
            continue

        # --- dative of separation (A&G 381) ---
        if hl in DATIVE_SEPARATION_VERBS:
            out.append(_make(
                "dative_of_separation", "Dative of Separation",
                "dativus separativus", (t.i, head.i), t.i,
                f"'{t.text}' is a bare dative under '{head.lemma}', a verb of taking away",
                f"Verbs of taking away use a dative of the *person deprived*, where English "
                f"says 'from'. The case is chosen because Latin sees the person as "
                f"interested in the loss, not merely as a source -- a thing would take *ab* "
                f"+ ablative instead.",
                f"from {t.text}", "A&G 381", 0.8))
            continue

        # --- dative of purpose, and the double dative (A&G 382) ---
        if t.lemma.lower() in PURPOSE_DATIVES:
            other = next((d for d in datives
                          if d.i != t.i and d.lemma.lower() not in PURPOSE_DATIVES), None)
            toks = [t.i, head.i] + ([other.i] if other else [])
            out.append(_make(
                "dative_of_purpose", "Dative of Purpose (Service)",
                "dativus finalis", toks, t.i,
                f"'{t.text}' is one of the closed set of purpose-datives"
                + (f", alongside '{other.text}' as the person concerned" if other else ""),
                f"*{t.text}* states what something *serves as* rather than to whom it is "
                f"given: 'as a help', 'as a protection', 'for a disgrace'."
                + (f" With *{other.text}* it forms the double dative -- '*as* {t.text} "
                   f"*to* {other.text}'." if other else ""),
                f"as a {t.text}", "A&G 382", 0.75))
            continue

        # --- dative with a compound verb (A&G 370) ---
        if head.pos in ("VERB", "AUX") and hl.startswith(DATIVE_COMPOUND_PREFIXES) and len(hl) > 5:
            out.append(_make(
                "dative_with_compound", "Dative with a Compound Verb",
                "dativus cum verbis compositis", (t.i, head.i), t.i,
                f"'{t.text}' is a bare dative under '{head.lemma}', a verb compounded with "
                f"a preposition",
                f"Verbs compounded with *ad, ante, con, in, inter, ob, prae, sub* and "
                f"*super* often take a dative, the prefix's own sense governing it: "
                f"*praeesse exercitui*, 'to be in command *of* the army'. The dative belongs "
                f"to the prefix as much as to the verb.",
                f"(dative governed by the prefix of {head.lemma})", "A&G 370", 0.6,
                caveat="Not every compound takes a dative; some keep an accusative object."))
            continue

        # --- indirect object (A&G 362) ---
        if hl in GIVING_VERBS:
            out.append(_make(
                "dative_indirect_object", "Dative of the Indirect Object",
                "dativus obiecti indirecti", (t.i, head.i), t.i,
                f"'{t.text}' is a bare dative under '{head.lemma}', a verb of giving, "
                f"telling or showing",
                f"The plainest use of the case: *{t.text}* is the person to whom something "
                f"is given, said or shown. English usually needs 'to' unless the word order "
                f"makes it clear.",
                f"to {t.text}", "A&G 362", 0.8))
            continue

        # --- ethical dative (A&G 380) ---
        if t.lemma.lower() in ("ego", "tu") and t.text.lower() in ("mihi", "tibi"):
            out.append(_make(
                "dative_ethical", "Ethical Dative",
                "dativus ethicus", (t.i,), t.i,
                f"'{t.text}' is a bare first- or second-person dative with no syntactic role "
                f"in the clause",
                f"*{t.text}* is not required by any verb; it draws the listener in, marking "
                f"their interest in what is said. It is colloquial and almost untranslatable "
                f"-- English gets closest with 'now', 'I tell you', or simply omits it.",
                "(often best left untranslated)", "A&G 380", 0.5,
                caveat="Only an ethical dative if no verb in the clause governs it."))
            continue

        # --- dative of direction, poetic (A&G 428.h) ---
        if head.pos in ("VERB", "AUX") and t.pos in ("NOUN", "PROPN"):
            out.append(_make(
                "dative_of_reference", "Dative of Reference (Advantage or Disadvantage)",
                "dativus commodi et incommodi", (t.i, head.i), t.i,
                f"'{t.text}' is a bare dative under '{head.text}' that no rule of the verb "
                f"requires",
                f"The dative names the person in whose interest -- or against whose interest "
                f"-- the action happens. It is the loosest use of the case, and often best "
                f"rendered 'for', 'to the advantage of', or by recasting the sentence.",
                f"for {t.text} / in {t.text}'s interest", "A&G 376", 0.45,
                caveat="A catch-all reading: check first whether the verb, an adjective or a "
                       "compound prefix governs the dative more specifically."))
    return out


# ======================================================================================
# ACCUSATIVE -- A&G 386-397
# ======================================================================================


@detector("accusative_uses")
def _accusative_uses(sent: Sentence) -> list[Construction]:
    out: list[Construction] = []
    for t in sent:
        if t.case() != "Acc":
            continue
        head = _head_of(sent, t)
        prep = _has_preposition(sent, t)

        if prep is not None:
            out.append(_make(
                "accusative_with_preposition", "Accusative with a Preposition",
                "accusativus cum praepositione", (prep.i, t.i), t.i,
                f"'{t.text}' is governed by the preposition '{prep.text}'",
                f"*{prep.text}* takes the accusative. Prepositions with the accusative "
                f"generally express motion towards or extension over something, as against "
                f"the ablative's sense of rest or separation.",
                f"{prep.text} {t.text}", "A&G 220", 0.9))
            continue

        if head is None:
            continue
        hl = head.lemma.lower()

        # --- two accusatives: person and thing (A&G 396) ---
        if hl in TWO_ACC_VERBS:
            others = [c for c in sent
                      if c.case() == "Acc" and c.i != t.i and _is_bare(sent, c)
                      and (c.head == head.i or c.head == t.i)]
            if others:
                out.append(_make(
                    "two_accusatives_person_thing", "Two Accusatives (Person and Thing)",
                    "duo accusativi", (t.i, others[0].i, head.i), t.i,
                    f"'{head.lemma}' governs two accusatives: '{t.text}' and "
                    f"'{others[0].text}'",
                    f"Verbs of teaching, asking, demanding and concealing take *two* "
                    f"accusatives -- one of the person, one of the thing. In the passive "
                    f"only the person becomes subject; the thing stays accusative.",
                    "(one is the person, one the thing)", "A&G 396", 0.75))
                continue

        # --- object and predicate accusative (A&G 393) ---
        if hl in PREDICATE_ACC_VERBS:
            others = [c for c in sent
                      if c.case() == "Acc" and c.i != t.i and _is_bare(sent, c)
                      and c.pos in ("NOUN", "PROPN", "ADJ")
                      and (c.head == head.i or c.head == t.i)]
            if others:
                out.append(_make(
                    "two_accusatives_predicate", "Object and Predicate Accusative",
                    "accusativus duplex", (t.i, others[0].i, head.i), t.i,
                    f"'{head.lemma}' -- a verb of making, calling or regarding -- governs "
                    f"'{t.text}' and '{others[0].text}', both accusative",
                    f"Verbs of making, calling, choosing and thinking take a second "
                    f"accusative predicated *of* the object: 'they made him consul'. The two "
                    f"accusatives are not parallel -- one is the object, the other says what "
                    f"the object became or was called.",
                    "made/called X (to be) Y", "A&G 393", 0.7))
                continue

        # --- cognate accusative (A&G 390) ---
        if head.pos == "VERB" and t.lemma.lower()[:4] == hl[:4] and len(hl) > 3:
            out.append(_make(
                "cognate_accusative", "Cognate Accusative",
                "accusativus cognatus", (t.i, head.i), t.i,
                f"'{t.text}' shares a root with its verb '{head.text}'",
                f"An intransitive verb may take an object of its own meaning -- *vitam "
                f"vivere*, 'to live a life'. The accusative adds nothing but a place to hang "
                f"an adjective, which is usually why it is there.",
                f"to {head.lemma} a {t.text}", "A&G 390", 0.6))
            continue

        # --- adverbial accusative (A&G 397.a) ---
        if t.lemma.lower() in ("multus", "nihil", "quis", "magnus", "pars", "ceterus",
                               "primus", "summus") and head.pos in ("VERB", "AUX", "ADJ"):
            out.append(_make(
                "adverbial_accusative", "Adverbial Accusative",
                "accusativus adverbialis", (t.i,), t.i,
                f"'{t.text}' is an accusative used adverbially with '{head.text}'",
                f"Certain neuter accusatives have frozen into adverbs -- *multum*, *nihil*, "
                f"*plerumque*, *magnam partem*. They modify the verb rather than receiving "
                f"its action.",
                f"(adverbially: {t.text})", "A&G 397.a", 0.55))
            continue

        # --- accusative subject of an infinitive (A&G 397.e) ---
        if head.morph.get("VerbForm") == "Inf" and t.dep in ("nsubj", "nsubj:pass"):
            out.append(_make(
                "accusative_subject_of_infinitive", "Accusative Subject of an Infinitive",
                "accusativus cum infinitivo", (t.i, head.i), t.i,
                f"'{t.text}' is the accusative subject of the infinitive '{head.text}'",
                f"An infinitive's subject stands in the accusative, not the nominative. "
                f"This is what makes indirect statement possible, and it is the single most "
                f"important thing to recognise when a sentence seems to have two objects.",
                f"that {t.text} …", "A&G 397.e", 0.8))
            continue

        # --- plain direct object (A&G 387) ---
        if head.pos == "VERB" and t.dep == "obj":
            out.append(_make(
                "accusative_direct_object", "Accusative of the Direct Object",
                "accusativus obiecti", (t.i, head.i), t.i,
                f"'{t.text}' is the object of the transitive verb '{head.text}'",
                f"The basic use of the case: *{t.text}* receives the action of "
                f"*{head.text}*.",
                f"{head.lemma}s the {t.text}", "A&G 387", 0.85))
    return out


# ======================================================================================
# ABLATIVE -- A&G 398-420. Three cases merged into one form.
# ======================================================================================


@detector("ablative_uses")
def _ablative_uses(sent: Sentence) -> list[Construction]:
    out: list[Construction] = []

    # *Multo*, *paulo* and *tanto* beside a comparative are ablatives of measure, but the
    # tagger usually calls them adverbs and gives them no case at all, so they are matched
    # on form before the case filter runs.
    for t in sent:
        if t.lemma.lower() not in DEGREE_WORDS or not t.text.lower().endswith("o"):
            continue
        head = _head_of(sent, t)
        if head is None or head.degree() != "Cmp":
            continue
        out.append(_make(
            "ablative_degree_of_difference", "Ablative of Degree of Difference",
            "ablativus mensurae", (t.i, head.i), t.i,
            f"'{t.text}' stands beside the comparative '{head.text}'",
            f"With a comparative, a bare ablative says *by how much*: *multo maior*, "
            f"'greater by much'. English usually drops the 'by' and says 'much greater'.",
            f"by {t.text} / {t.text} more", "A&G 414", 0.75))

    for t in sent:
        if t.case() != "Abl":
            continue
        head = _head_of(sent, t)
        prep = _prep_lemma(sent, t)
        tl = t.lemma.lower()
        hl = head.lemma.lower() if head else ""

        # --- ablative of agent (A&G 405) ---
        if prep in ("a", "ab", "abs"):
            if head is not None and head.morph.get("Voice") == "Pass":
                out.append(_make(
                    "ablative_of_agent", "Ablative of Personal Agent",
                    "ablativus auctoris", (t.i, head.i), t.i,
                    f"'{t.text}' follows *{prep}* with the passive verb '{head.text}'",
                    f"*A/ab* with the ablative names the *person* by whom a passive action "
                    f"is done. A thing would take a bare ablative of means instead -- the "
                    f"distinction between being killed *by Caesar* and *by a sword* is "
                    f"marked by the preposition alone.",
                    f"by {t.text}", "A&G 405", 0.85))
            else:
                out.append(_make(
                    "ablative_of_separation", "Ablative of Separation",
                    "ablativus separationis", (t.i,), t.i,
                    f"'{t.text}' follows the preposition *{prep}*",
                    f"*A/ab* with the ablative marks motion or distance away from something "
                    f"-- the case's original meaning, from which most of its other uses "
                    f"descend.",
                    f"from {t.text}", "A&G 402", 0.7))
            continue

        # --- accompaniment vs manner, both with cum (A&G 412-413) ---
        if prep == "cum":
            if t.pos in ("NOUN", "PROPN", "PRON") and (
                    t.pos == "PROPN" or tl not in MANNER_NOUNS):
                out.append(_make(
                    "ablative_of_accompaniment", "Ablative of Accompaniment",
                    "ablativus sociativus", (t.i,), t.i,
                    f"'{t.text}' follows *cum* and names a person or thing accompanying",
                    f"*Cum* + ablative says who or what goes along with the action. Latin "
                    f"requires the preposition here -- a bare ablative would mean *by means "
                    f"of*, which is why *cum* is never omitted with a person.",
                    f"with {t.text}", "A&G 413", 0.8))
            if tl in MANNER_NOUNS:
                out.append(_make(
                    "ablative_of_manner", "Ablative of Manner",
                    "ablativus modi", (t.i,), t.i,
                    f"'{t.text}' follows *cum* and is a noun of manner",
                    f"*Cum* + ablative of an abstract noun says *how* the action is done. "
                    f"When the noun carries an adjective, *cum* may be dropped: *magna (cum) "
                    f"celeritate*.",
                    f"with {t.text} / {t.text}-ly", "A&G 412", 0.75))
            continue

        if prep in ("in", "sub"):
            out.append(_make(
                "ablative_of_place_where", "Ablative of Place Where",
                "ablativus loci", (t.i,), t.i,
                f"'{t.text}' follows *{prep}* in the ablative, not the accusative",
                f"*In* with the ablative means *in* or *on* -- rest in a place. With the "
                f"accusative the same preposition means *into* -- motion towards. The case, "
                f"not the preposition, carries the difference.",
                f"in/on {t.text}", "A&G 426", 0.85))
            continue

        if prep in ("de", "e", "ex"):
            out.append(_make(
                "ablative_of_separation", "Ablative of Separation / Source",
                "ablativus separationis", (t.i,), t.i,
                f"'{t.text}' follows *{prep}*",
                f"*{prep.upper()}* + ablative expresses motion out of or down from, and by "
                f"extension the source or material of a thing.",
                f"from/out of {t.text}", "A&G 402", 0.8))
            continue

        if prep in ("sine", "pro", "prae", "coram"):
            out.append(_make(
                "ablative_with_preposition", "Ablative with a Preposition",
                "ablativus cum praepositione", (t.i,), t.i,
                f"'{t.text}' is governed by *{prep}*",
                f"*{prep.upper()}* takes the ablative.",
                f"{prep} {t.text}", "A&G 220", 0.85))
            continue

        if prep:
            continue

        # ---------------- bare ablatives ----------------

        if head is None:
            continue

        # --- price (A&G 416) ---
        if hl in PRICE_VERBS:
            out.append(_make(
                "ablative_of_price", "Ablative of Price",
                "ablativus pretii", (t.i, head.i), t.i,
                f"'{t.text}' is a bare ablative under '{head.lemma}', a verb of buying, "
                f"selling or costing",
                f"A definite price stands in the ablative -- a survival of the instrumental, "
                f"since the money is the means of the transaction. An *indefinite* value "
                f"(*magni*, *pluris*) uses the genitive instead, which is the distinction "
                f"worth remembering.",
                f"for {t.text}", "A&G 416", 0.8))
            continue

        # --- separation and want (A&G 400-401) ---
        if hl in SEPARATION_VERBS or hl in PLENTY_WANT_VERBS:
            out.append(_make(
                "ablative_of_separation", "Ablative of Separation",
                "ablativus separationis", (t.i, head.i), t.i,
                f"'{t.text}' is a bare ablative under '{head.lemma}', a verb of separating, "
                f"freeing or lacking",
                f"Verbs of freeing, depriving, lacking and abstaining take an ablative of the "
                f"thing removed or missing, often without any preposition at all. *Careo "
                f"patria* is 'I lack a homeland'.",
                f"from/of {t.text}", "A&G 401", 0.8))
            continue

        # --- source and origin (A&G 403) ---
        if hl in ORIGIN_WORDS or (head.morph.get("VerbForm") == "Part" and hl in ORIGIN_WORDS):
            out.append(_make(
                "ablative_of_origin", "Ablative of Source or Origin",
                "ablativus originis", (t.i, head.i), t.i,
                f"'{t.text}' is a bare ablative with '{head.text}', a participle of birth "
                f"or origin",
                f"Participles meaning *born* or *sprung* take a bare ablative of the parent "
                f"or stock: *Iove natus*, 'born of Jupiter'.",
                f"born of {t.text}", "A&G 403", 0.8))
            continue

        # --- degree of difference (A&G 414) ---
        if tl in DEGREE_WORDS and head.degree() == "Cmp":
            out.append(_make(
                "ablative_degree_of_difference", "Ablative of Degree of Difference",
                "ablativus mensurae", (t.i, head.i), t.i,
                f"'{t.text}' is a measure-word in the ablative beside the comparative "
                f"'{head.text}'",
                f"With comparatives, a bare ablative says *by how much*: *multo maior*, "
                f"'greater by much'. English usually drops the 'by' and says simply 'much "
                f"greater'.",
                f"by {t.text} / {t.text} more", "A&G 414", 0.8))
            continue

        # --- cause (A&G 404) ---
        if tl in CAUSE_NOUNS and head.pos in ("VERB", "AUX", "ADJ"):
            out.append(_make(
                "ablative_of_cause", "Ablative of Cause",
                "ablativus causae", (t.i, head.i), t.i,
                f"'{t.text}' is a bare ablative of an abstract noun of emotion or compulsion",
                f"A bare ablative can give the reason for an action, especially with nouns of "
                f"emotion: *timore fugit*, 'he fled out of fear'. It shades into the ablative "
                f"of means -- the fear is both why he ran and what drove him.",
                f"out of / because of {t.text}", "A&G 404", 0.65,
                caveat="Overlaps with the ablative of means; the two are not sharply distinct."))
            continue

        # --- specification / respect (A&G 418) ---
        if tl in RESPECT_NOUNS and head.pos in ("ADJ", "VERB", "NOUN"):
            out.append(_make(
                "ablative_of_specification", "Ablative of Specification (Respect)",
                "ablativus respectus", (t.i, head.i), t.i,
                f"'{t.text}' is a bare ablative naming the respect in which '{head.text}' "
                f"holds",
                f"A bare ablative can limit the application of an adjective or verb: *maior "
                f"natu*, 'greater in respect of birth', i.e. older. Ask 'in what way?' and "
                f"this ablative answers.",
                f"in respect of {t.text} / in {t.text}", "A&G 418", 0.7))
            continue

        # --- manner without cum, when the noun carries an adjective (A&G 412) ---
        if tl in MANNER_NOUNS and any(c.pos == "ADJ" and c.case() == "Abl"
                                      for c in _children(sent, t.i)):
            out.append(_make(
                "ablative_of_manner", "Ablative of Manner",
                "ablativus modi", (t.i,), t.i,
                f"'{t.text}' is a bare ablative of manner carrying its own adjective, which "
                f"is what licenses the omission of *cum*",
                f"*Cum* may be dropped when the noun of manner has an adjective: *magna "
                f"celeritate*, 'with great speed'. Without the adjective the preposition is "
                f"required.",
                f"with {t.text}", "A&G 412", 0.7))
            continue

        # --- route (A&G 429.a) ---
        if tl in ROUTE_NOUNS and head.pos == "VERB":
            out.append(_make(
                "ablative_of_route", "Ablative of the Way By Which",
                "ablativus viae", (t.i, head.i), t.i,
                f"'{t.text}' is a bare ablative of a route-word with the verb '{head.text}'",
                f"The road, river or gate by which one travels stands in a bare ablative -- "
                f"an instrumental use, the route being the means of the journey. *Terra "
                f"marique* is 'by land and sea'.",
                f"by way of {t.text} / by {t.text}", "A&G 429.a", 0.65))
            continue

        # --- quality / description (A&G 415) ---
        if head.pos in ("NOUN", "PROPN") and any(
                c.pos == "ADJ" and c.case() == "Abl" for c in _children(sent, t.i)):
            out.append(_make(
                "ablative_of_quality", "Ablative of Quality (Description)",
                "ablativus qualitatis", (t.i, head.i), t.i,
                f"'{t.text}' is an ablative with an adjective, describing '{head.text}'",
                f"An ablative with its own adjective describes a person or thing: *vir "
                f"summa virtute*, 'a man of the highest courage'. It competes with the "
                f"genitive of description; the ablative is preferred for physical and "
                f"temporary qualities, the genitive for permanent and measurable ones.",
                f"of {t.text}", "A&G 415", 0.65))
            continue

        # --- means / instrument (A&G 409) -- the residual reading ---
        if head.pos in ("VERB", "AUX") and t.pos in ("NOUN", "PROPN", "PRON"):
            out.append(_make(
                "ablative_of_means", "Ablative of Means (Instrument)",
                "ablativus instrumenti", (t.i, head.i), t.i,
                f"'{t.text}' is a bare ablative of a thing, under the verb '{head.text}', "
                f"with no preposition",
                f"The commonest use of the bare ablative: *{t.text}* is the instrument or "
                f"means by which the action is done. Note that a *person* cannot be a means "
                f"-- they would require *ab* -- so the absence of a preposition is itself "
                f"the evidence that {t.text} is being treated as a thing.",
                f"by/with {t.text}", "A&G 409", 0.6,
                caveat="The bare ablative also carries cause, manner, respect and price; "
                       "means is the default when no other trigger is present."))
    return out


# ======================================================================================
# GERUND AND GERUNDIVE -- A&G 500-507
# ======================================================================================


@detector("gerund_cases")
def _gerund_cases(sent: Sentence) -> list[Construction]:
    out: list[Construction] = []
    for t in sent:
        if not _looks_like_gerund(t):
            continue
        if any(c.lemma == "sum" and (c.head == t.i or t.head == c.i) for c in sent):
            continue
        case = t.case()
        if case is None or not t.is_gerundive():
            # Recover the case from the ending when the tagger has given up: *legendo* came
            # back as a proper noun, so nothing but the -nd- stem identifies it.
            form = t.text.lower().replace("v", "u").replace("j", "i")
            case = ("Gen" if form.endswith(("ndi", "ndorum", "ndarum"))
                    else "Acc" if form.endswith("ndum")
                    else "Abl" if form.endswith(("ndo", "ndis"))
                    else case)
        prep = _prep_lemma(sent, t)
        agreeing = [c for c in sent
                    if c.i != t.i and c.case() == case and c.pos in ("NOUN", "PROPN")
                    and abs(c.i - t.i) <= 2 and c.morph.get("Number") == t.morph.get("Number")]

        if agreeing:
            noun = agreeing[0]
            out.append(_make(
                "gerundive_construction", "Gerundive Construction (Attraction)",
                "constructio gerundivi", (t.i, noun.i), t.i,
                f"the gerundive '{t.text}' agrees with '{noun.text}' in case, number and "
                f"gender",
                f"Where English would use a verbal noun with an object -- 'for seeking "
                f"peace' -- Latin prefers to turn the object into the noun and make the "
                f"verb a *gerundive* agreeing with it: *pacis petendae*. Translate the noun "
                f"as the object and the gerundive as an active verbal noun; the passive form "
                f"is a grammatical device, not a passive meaning.",
                f"of/for {noun.lemma}-ing", "A&G 503", 0.75))

        if case == "Gen":
            causa = next((c for c in sent if c.lemma.lower() in ("causa", "gratia")), None)
            if causa is not None:
                out.append(_make(
                    "gerund_genitive_purpose", "Genitive of the Gerund with *causa*",
                    "genetivus gerundii cum 'causa'", (t.i, causa.i), t.i,
                    f"the genitive gerund '{t.text}' stands with *{causa.text}*",
                    f"A genitive gerund or gerundive with *causa* or *gratia* -- which "
                    f"follow it -- is one of the standard ways of expressing purpose in "
                    f"classical prose.",
                    f"for the sake of {t.lemma}-ing", "A&G 504.c", 0.8))
            else:
                out.append(_make(
                    "gerund_genitive", "Genitive of the Gerund",
                    "genetivus gerundii", (t.i,), t.i,
                    f"'{t.text}' is a gerund in the genitive",
                    f"The genitive gerund depends on a noun or an adjective that governs the "
                    f"genitive -- *ars scribendi*, 'the art of writing'; *cupidus "
                    f"videndi*, 'eager to see'.",
                    f"of {t.lemma}-ing", "A&G 504", 0.7))
        elif case == "Acc" and prep == "ad":
            out.append(_make(
                "gerund_accusative_purpose", "Accusative of the Gerund with *ad* (Purpose)",
                "accusativus gerundii cum 'ad'", (t.i,), t.i,
                f"'{t.text}' is a gerund in the accusative governed by *ad*",
                f"*Ad* + accusative gerund expresses purpose: *ad discendum*, 'for the "
                f"purpose of learning', 'in order to learn'. It is the commonest purpose "
                f"construction after the *ut*-clause.",
                f"in order to {t.lemma}", "A&G 506", 0.8))
        elif case == "Abl":
            out.append(_make(
                "gerund_ablative_means", "Ablative of the Gerund (Means)",
                "ablativus gerundii", (t.i,), t.i,
                f"'{t.text}' is a gerund in the ablative"
                + (f", governed by *{prep}*" if prep else ", with no preposition"),
                f"A bare ablative gerund expresses *means*: *legendo discimus*, 'we learn by "
                f"reading'. With *in* it means 'in the course of'; with *de* or *ex*, "
                f"'concerning'.",
                f"by {t.lemma}-ing", "A&G 507", 0.75))
        elif case == "Dat":
            out.append(_make(
                "gerund_dative", "Dative of the Gerund",
                "dativus gerundii", (t.i,), t.i,
                f"'{t.text}' is a gerund in the dative",
                f"The dative gerund is rare in classical prose, surviving chiefly in "
                f"official formulae of purpose -- *decemviri legibus scribundis*, 'the board "
                f"of ten for writing the laws'.",
                f"for {t.lemma}-ing", "A&G 505", 0.65))
    return out


#: Every case-use this module can report, for the reference index.
CASE_USE_INDEX = {
    "genitive_possessive": ("Possessive Genitive", "A&G 343"),
    "genitive_subjective": ("Subjective Genitive", "A&G 343.a"),
    "genitive_objective": ("Objective Genitive", "A&G 347"),
    "genitive_of_description": ("Genitive of Description", "A&G 345"),
    "genitive_with_adjective": ("Genitive with an Adjective", "A&G 349"),
    "genitive_of_charge": ("Genitive of the Charge", "A&G 352"),
    "genitive_of_value": ("Genitive of Indefinite Value", "A&G 417"),
    "genitive_with_interest": ("Genitive with interest/refert", "A&G 355"),
    "genitive_predicate": ("Predicate Genitive", "A&G 343.b"),
    "dative_indirect_object": ("Dative of the Indirect Object", "A&G 362"),
    "dative_with_compound": ("Dative with a Compound Verb", "A&G 370"),
    "dative_of_separation": ("Dative of Separation", "A&G 381"),
    "dative_of_purpose": ("Dative of Purpose", "A&G 382"),
    "dative_of_reference": ("Dative of Reference", "A&G 376"),
    "dative_ethical": ("Ethical Dative", "A&G 380"),
    "accusative_direct_object": ("Accusative of the Direct Object", "A&G 387"),
    "accusative_with_preposition": ("Accusative with a Preposition", "A&G 220"),
    "two_accusatives_person_thing": ("Two Accusatives (Person and Thing)", "A&G 396"),
    "two_accusatives_predicate": ("Object and Predicate Accusative", "A&G 393"),
    "cognate_accusative": ("Cognate Accusative", "A&G 390"),
    "adverbial_accusative": ("Adverbial Accusative", "A&G 397.a"),
    "accusative_subject_of_infinitive": ("Accusative Subject of an Infinitive", "A&G 397.e"),
    "ablative_of_agent": ("Ablative of Personal Agent", "A&G 405"),
    "ablative_of_means": ("Ablative of Means", "A&G 409"),
    "ablative_of_manner": ("Ablative of Manner", "A&G 412"),
    "ablative_of_accompaniment": ("Ablative of Accompaniment", "A&G 413"),
    "ablative_of_separation": ("Ablative of Separation", "A&G 401"),
    "ablative_of_origin": ("Ablative of Source or Origin", "A&G 403"),
    "ablative_of_cause": ("Ablative of Cause", "A&G 404"),
    "ablative_of_price": ("Ablative of Price", "A&G 416"),
    "ablative_of_specification": ("Ablative of Specification", "A&G 418"),
    "ablative_of_quality": ("Ablative of Quality", "A&G 415"),
    "ablative_degree_of_difference": ("Ablative of Degree of Difference", "A&G 414"),
    "ablative_of_place_where": ("Ablative of Place Where", "A&G 426"),
    "ablative_of_route": ("Ablative of the Way By Which", "A&G 429.a"),
    "ablative_with_preposition": ("Ablative with a Preposition", "A&G 220"),
    "gerundive_construction": ("Gerundive Construction", "A&G 503"),
    "gerund_genitive": ("Genitive of the Gerund", "A&G 504"),
    "gerund_genitive_purpose": ("Genitive of the Gerund with causa", "A&G 504.c"),
    "gerund_dative": ("Dative of the Gerund", "A&G 505"),
    "gerund_accusative_purpose": ("Accusative of the Gerund with ad", "A&G 506"),
    "gerund_ablative_means": ("Ablative of the Gerund", "A&G 507"),
}

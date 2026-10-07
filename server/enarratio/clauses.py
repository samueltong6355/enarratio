"""Conservative subordinate-clause rules; meanings are candidates, not proofs.

Allen & Greenough references and scope are recorded in docs/research/lightweight-clauses.md.
No network, generated translations, or additional model is required.
"""
from .constructions import Construction, Sentence, _children, _head_of, detector

CLAUSE_INDEX = {
    "hindering_clause": ("Clause of Hindering or Doubt", "A&G 558–559"),
    "substantive_purpose": ("Substantive Clause of Purpose", "A&G 563"),
    "substantive_result": ("Substantive Clause of Result", "A&G 567–571"),
    "causal_clause": ("Causal Clause", "A&G 540"),
    "concessive_clause": ("Concessive Clause", "A&G 527"),
    "proviso_clause": ("Clause of Proviso", "A&G 528"),
    "temporal_before": ("Temporal Clause: Before", "A&G 551"),
    "temporal_until": ("Temporal Clause: While or Until", "A&G 553–556"),
    "conditional_clause": ("Conditional Protasis and Apodosis", "A&G 513–517"),
    "relative_purpose": ("Possible Relative Clause of Purpose", "A&G 531.2"),
    "substantive_quod": ("Substantive Quod-clause", "A&G 572"),
    "dative_direction": ("Possible Poetic Dative of Direction", "A&G 428.h"),
}

COMMAND = {"impero", "persuadeo", "moneo", "rogo", "oro", "peto", "hortor", "curo", "suadeo", "postulo"}
RESULT = {"accido", "contingo", "euenio", "efficio", "perficio", "facio", "fio", "resto", "sequor", "impetro"}
HINDER = {"impedio", "prohibeo", "deterreo", "obsto", "recuso", "dubito"}
MOTION = {"eo", "uenio", "proficiscor", "contendo", "fero", "mitto", "tendo"}


def norm(value):
    return value.lower().replace("v", "u")


def make(key, mark, verb, governor, explanation, hint, confidence=.78):
    name, ref = CLAUSE_INDEX[key]
    participants = tuple(dict.fromkeys(t.i for t in (mark, verb, governor) if t is not None))
    return Construction(key=key, name=name, latin_name="", tokens=participants, anchor=verb.i,
        evidence=f"'{mark.text}' is attached to '{verb.text}' ({verb.morph.get('Mood', 'mood uncertain')}); governing word: '{governor.text if governor else 'unresolved'}'.",
        explanation=explanation, translation_hint=hint, grammar_ref=ref, confidence=confidence,
        caveat="A dependency-based candidate. Check the clause boundaries and surrounding sense; a parser can attach a conjunction incorrectly.")


@detector("subordinate_clauses")
def subordinate_clauses(sent: Sentence) -> list[Construction]:
    out = []
    for mark in sent:
        if mark.dep not in {"mark", "advmod"}:
            continue
        verb = _head_of(sent, mark)
        if verb is None:
            continue
        # Copular predicates carry their finite mood on a child, not the noun/adjective.
        finite = verb if verb.morph.get("Mood") in {"Ind", "Sub", "Imp"} else next(
            (c for c in _children(sent, verb.i) if c.dep in {"cop", "aux", "aux:pass"} and c.morph.get("Mood") in {"Ind", "Sub", "Imp"}), None)
        if finite is None:
            continue
        mood = finite.morph.get("Mood")
        governor = _head_of(sent, verb)
        lemma = norm(mark.lemma)
        head = norm(governor.lemma) if governor else ""
        relation = verb.dep.split(":")[0]
        if governor is None or relation not in {"advcl", "ccomp", "csubj", "acl", "xcomp"}:
            continue
        def add(key, explanation, hint, confidence=.78):
            out.append(make(key, mark, verb, governor, explanation, hint, confidence))

        if lemma in {"quin", "quominus", "ne"} and mood == "Sub" and head in HINDER:
            negative = any(norm(t.lemma) in {"non", "haud", "numquam", "nemo", "nihil"} for t in _children(sent, governor.i))
            if lemma != "quin" or negative:
                add("hindering_clause", "The clause supplies what is prevented or doubted, not a separate purpose. Quin normally requires a negative or virtually negative governing expression; quominus means 'from' doing something.", "prevent … from … / not doubt that …")
        elif lemma in {"ut", "ne"} and mood == "Sub" and head in COMMAND:
            add("substantive_purpose", "This clause supplies the content of a command, request, advice, or effort. It functions like the object of the governing verb, rather than an independent statement of purpose. Ne makes that content negative.", "ask/order/urge … to … (ne: not to …)")
        elif lemma == "ut" and mood == "Sub" and head in RESULT:
            add("substantive_result", "This clause states what happens or is brought about and fills a subject or object role. Its negative is ut non, unlike the ne of a negative command.", "it happens that … / bring it about that …")
        elif lemma == "quod" and mood == "Ind" and relation in {"ccomp", "csubj", "acl"}:
            add("substantive_quod", "Quod can introduce a fact treated as a noun: 'the fact that …'. Here the parser gives it a complement or explanatory role. A causal reading ('because') may also fit, especially after verbs of feeling.", "the fact that … / in that …", .65)
        elif lemma in {"quia", "quoniam", "quod"} and relation == "advcl":
            add("causal_clause", "This clause offers a reason. The indicative commonly presents the writer's own reason; a subjunctive may mark another person's alleged reason or indirect discourse, not necessarily an untrue reason.", "because … / since …")
        elif lemma in {"quamquam", "quamuis", "licet", "etsi", "etiamsi", "tametsi"}:
            add("concessive_clause", "This clause concedes a circumstance despite which the main statement holds. Quamquam usually has the indicative; quamvis and concessive licet usually have the subjunctive. Etsi can also mean 'even if'.", "although … / even if …", .72)
        elif lemma in {"dum", "modo", "dummodo"} and mood == "Sub":
            add("proviso_clause", "A subjunctive with this particle can set a stipulation; ne negates it. With dum, an anticipated temporal limit is also possible: mood alone cannot decide between 'provided that' and 'until'.", "provided that … / so long as …", .62 if lemma == "dum" else .8)
            if lemma == "dum":
                add("temporal_until", "Dum with a subjunctive can express an anticipated or intended limit. This competes with the proviso interpretation; choose from the surrounding sense.", "until …", .6)
        elif lemma in {"antequam", "priusquam"}:
            add("temporal_before", "This gives a time before which the main event occurs. The indicative commonly reports an event; the subjunctive can describe an anticipated or intended event.", "before …")
        elif lemma in {"dum", "donec", "quoad"}:
            add("temporal_until", "These particles express duration or a temporal limit. Dum with a present indicative commonly means 'while', even in past narrative; donec and quoad can mean 'as long as' or 'until'.", "while … / as long as … / until …", .73)
        elif lemma in {"si", "nisi", "sin"}:
            main_finite = governor if governor.morph.get("Mood") else next((c for c in _children(sent, governor.i) if c.dep == "cop"), governor)
            matching = main_finite.morph.get("Mood") == mood
            tense = finite.morph.get("Tense")
            if mood == "Sub" and matching and tense in {"Imp", "Pqp"} and main_finite.morph.get("Tense") in {"Imp", "Pqp"}:
                kind = "The two subjunctives suggest a contrary-to-fact condition (imperfect: present; pluperfect: past)."
            elif mood == "Sub":
                kind = "Subjunctive condition: less vivid, contrary-to-fact, and reported conditions must be distinguished from tense and context. Mood alone is insufficient."
            else:
                kind = "Indicative condition: the hypothesis is left open, not asserted to be true. Future and general conditions need context."
            add("conditional_clause", "The si/nisi clause is the protasis (condition); its governing clause is the apodosis (consequence). " + kind, "if …, then … / unless …", .76)
    return out


@detector("relative_purpose")
def relative_purpose(sent: Sentence) -> list[Construction]:
    out = []
    for verb in sent:
        if not verb.dep.startswith("acl") or not verb.is_(Mood="Sub"):
            continue
        antecedent = _head_of(sent, verb)
        governor = _head_of(sent, antecedent) if antecedent else None
        relative = next((t for t in _children(sent, verb.i) if t.morph.get("PronType") == "Rel"), None)
        if governor and norm(governor.lemma) in {"mitto", "deligo", "eligo"} and relative:
            out.append(make("relative_purpose", relative, verb, governor,
                "A relative subjunctive attached to someone sent or chosen may explain the task they are meant to perform. A clause of characteristic is an alternative; purpose is not proved by the subjunctive alone.", "someone to … / who should …", .65))
    return out


@detector("dative_direction")
def dative_direction(sent: Sentence) -> list[Construction]:
    out = []
    for token in sent:
        governor = _head_of(sent, token)
        if token.case() != "Dat" or not governor or norm(governor.lemma) not in MOTION:
            continue
        if token.dep.split(":")[0] not in {"obl", "iobj"} or any(t.dep == "case" for t in _children(sent, token.i)):
            continue
        if token.ent not in {"LOC", "GPE"} and norm(token.lemma) not in {"caelum", "terra", "pontus", "mare", "litus", "tartarus", "orcus"}:
            continue
        result = make("dative_direction", token, token, governor,
            "A place in the dative with motion can be a poetic destination, where prose normally uses ad/in with the accusative. This rare use is only a possibility here: compare a dative of reference, recipient, or a compound verb's complement.", "to / towards …", .55)
        result.caveat = "The rule does not establish that this is verse. Check genre, place sense, and competing dative uses."
        out.append(result)
    return out

"""Detection of literary and rhetorical figures.

The AP Latin examination does not ask a student to *name* a figure; it asks them to quote
the Latin that exemplifies it and say what it does. So every device here carries an
``effect`` -- what the figure achieves in this passage -- alongside the evidence that found
it. Naming alliteration is worthless; noticing that Vergil's *m* sounds in a line about the
sea imitate its swell is the actual skill.

The same discipline applies as in :mod:`enarratio.constructions`: a detector fires on
evidence from the text, reports that evidence, and carries a confidence. Figures differ
from constructions, though, in one important way -- many are matters of *degree* rather than
of kind. Two words beginning with the same letter is a coincidence; five is alliteration.
Thresholds are therefore explicit and stated in the evidence, so a reader can judge whether
the claim is worth making.

Some famous figures are deliberately **not** detected, because detecting them would require
knowing what words mean rather than how they behave: metaphor, oxymoron, transferred epithet
and true hendiadys all need semantics that a dependency parse does not supply. Claiming them
on structural grounds alone would produce confident nonsense, which is worse than silence.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Callable, Sequence

from .constructions import Tok

__all__ = ["Device", "detect_devices", "DEVICE_INDEX"]


@dataclass
class Device:
    key: str
    name: str
    latin_name: str
    tokens: tuple[int, ...]
    evidence: str
    #: What the figure *is*, in this instance.
    explanation: str
    #: What it does to the reader -- the half an examiner actually wants.
    effect: str
    confidence: float
    caveat: str = ""

    def as_dict(self) -> dict:
        return {
            "key": self.key, "name": self.name, "latinName": self.latin_name,
            "tokens": list(self.tokens), "evidence": self.evidence,
            "explanation": self.explanation, "effect": self.effect,
            "confidence": round(self.confidence, 2), "caveat": self.caveat,
        }


# --------------------------------------------------------------------------------------
# Sound
# --------------------------------------------------------------------------------------

VOWELS = set("aeiouy")

#: Words too common to count as alliteration when they merely happen to start with the
#: right letter -- a line is not alliterative because it contains *et* twice.
SOUND_STOPWORDS = {
    "et", "ac", "atque", "aut", "ad", "ab", "a", "in", "cum", "de", "e", "ex", "per",
    "sed", "si", "sic", "se", "sui", "sibi", "est", "sunt", "esse", "que", "ne", "nec",
    "non", "iam", "tam", "ut", "quam", "qui", "quae", "quod", "is", "ea", "id", "hic",
    "haec", "hoc", "ille", "illa", "illud", "te", "tu", "me", "ego", "nos", "vos",
}


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("j", "i").replace("v", "u")


def _initial(word: str) -> str:
    """The opening consonant sound, treating the usual digraphs as one."""
    w = _fold(word)
    if not w:
        return ""
    for dig in ("qu", "ch", "ph", "th", "gn", "sc", "sp", "st"):
        if w.startswith(dig):
            return dig
    return w[0]


def _alliteration(sent: Sequence[Tok], words: list[Tok]) -> list[Device]:
    """Three or more nearby words sharing an initial sound.

    The window matters: *arma* and *alto* eight words apart share a letter and nothing else.
    A span of five words is about the reach of the ear.
    """
    out: list[Device] = []
    used: set[int] = set()
    for i, t in enumerate(words):
        if t.i in used:
            continue
        sound = _initial(t.text)
        if not sound or sound[0] in VOWELS:
            continue
        group = [t]
        for u in words[i + 1 : i + 6]:
            if _initial(u.text) == sound and _fold(u.text) not in SOUND_STOPWORDS:
                group.append(u)
        if len(group) == 2 and group[1].i - group[0].i > 1:
            continue
        if len(group) < 2:
            continue
        used.update(g.i for g in group)
        quoted = " ".join(g.text for g in group)
        out.append(Device(
            key="alliteration", name="Alliteration", latin_name="allitteratio",
            tokens=tuple(g.i for g in group),
            evidence=f"{len(group)} words within six begin with '{sound}': {quoted}",
            explanation=(
                f"The repeated initial '{sound}' binds *{quoted}* into a single sound-unit, "
                f"so the ear hears the words as belonging together whatever the syntax does."
            ),
            effect=(
                "Latin poets use alliteration to enact meaning in sound. Ask what the "
                f"consonant itself suggests here: 's' can hiss or whisper, 'm' hum or moan, "
                f"'t' and 'c' strike hard and fast, 'l' flow. If the sense of the line matches "
                f"the sound of '{sound}', that correspondence is the point."
            ),
            confidence=(0.5 if len(group) == 2 else 0.6 + 0.1 * min(len(group) - 3, 3)),
            caveat=("Only two words, though they are adjacent -- weaker evidence than a run "
                    "of three." if len(group) == 2 else ""),
        ))
    return out


def _assonance(sent: Sequence[Tok], words: list[Tok]) -> list[Device]:
    """A vowel repeated in stressed positions across nearby words."""
    out: list[Device] = []
    for i in range(len(words) - 2):
        window = words[i : i + 4]
        counts: Counter[str] = Counter()
        totals: Counter[str] = Counter()
        for w in window:
            found = re.findall(r"[aeiou]", _fold(w.text))
            totals.update(found)
            for v in set(found):
                counts[v] += 1
        for vowel, n in counts.most_common(1):
            # Latin has five vowels and long words, so a vowel shared by four words proves
            # nothing on its own. Require it in every word AND six occurrences overall,
            # which is the difference between coincidence and a deliberate sound-effect.
            if n >= len(window) and totals[vowel] >= 6:
                quoted = " ".join(w.text for w in window)
                out.append(Device(
                    key="assonance", name="Assonance", latin_name="assonantia",
                    tokens=tuple(w.i for w in window),
                    evidence=f"the vowel '{vowel}' recurs in all {n} words of *{quoted}*",
                    explanation=(
                        f"The same vowel '{vowel}' sounds through *{quoted}*, colouring the "
                        f"phrase with one tone."
                    ),
                    effect=(
                        "Assonance slows a line and gives it a single mood; long open vowels "
                        "tend to broaden and sadden, short close ones to quicken it."
                    ),
                    confidence=0.5,
                    caveat="Latin's vowel inventory is small, so some repetition is inevitable.",
                ))
                break
    return out[:2]


def _homoeoteleuton(sent: Sequence[Tok], words: list[Tok]) -> list[Device]:
    """Nearby words with the same ending -- rhyme by inflection."""
    out: list[Device] = []
    for i in range(len(words) - 1):
        a = words[i]
        for b in words[i + 1 : i + 4]:
            ea, eb = _fold(a.text)[-3:], _fold(b.text)[-3:]
            if len(ea) < 3 or ea != eb or a.lemma == b.lemma:
                continue
            out.append(Device(
                key="homoeoteleuton", name="Homoeoteleuton", latin_name="homoeoteleuton",
                tokens=(a.i, b.i),
                evidence=f"'{a.text}' and '{b.text}' both end in '-{ea}'",
                explanation=(
                    f"*{a.text}* and *{b.text}* close on the same sound. In an inflected "
                    f"language this often follows from grammatical agreement, but poets "
                    f"exploit it deliberately."
                ),
                effect=(
                    "The echo links the two words in the ear, which usually reinforces a link "
                    "the grammar is already making -- or teases the reader with one it is not."
                ),
                confidence=0.45,
                caveat="Agreement produces matching endings by itself; this is only a figure "
                       "when the pairing seems chosen.",
            ))
            break
    return out[:3]


# --------------------------------------------------------------------------------------
# Word order
# --------------------------------------------------------------------------------------


def _agreeing_pairs(sent: Sequence[Tok]) -> list[tuple[Tok, Tok]]:
    """Modifier/head pairs that actually agree, whatever the parser attached them to."""
    pairs = []
    for t in sent:
        if t.pos not in ("ADJ", "DET", "NUM") or t.dep not in ("amod", "det", "nummod"):
            continue
        head = sent[t.head] if 0 <= t.head < len(sent) else None
        if head is None:
            continue
        pairs.append((t, head))
    return pairs


def _hyperbaton(sent: Sequence[Tok]) -> list[Device]:
    """An adjective torn away from its noun.

    This is the figure behind most of what a naive agreement check reports as an *error*.
    Separation of three or more words is not a mistake in verse; it is the single most
    characteristic feature of Latin poetic word order.
    """
    out = []
    for adj, noun in _agreeing_pairs(sent):
        gap = abs(adj.i - noun.i) - 1
        if gap < 3:
            continue
        between = [sent[k].text for k in range(min(adj.i, noun.i) + 1, max(adj.i, noun.i))]
        out.append(Device(
            key="hyperbaton", name="Hyperbaton", latin_name="hyperbaton",
            tokens=(adj.i, noun.i),
            evidence=(f"'{adj.text}' agrees with '{noun.text}' but {gap} words stand between "
                      f"them: {' '.join(between)}"),
            explanation=(
                f"*{adj.text}* belongs to *{noun.text}*, yet the poet has driven them apart. "
                f"Latin can do this because agreement, not position, shows what goes with "
                f"what -- English cannot, which is why translation has to reunite them."
            ),
            effect=(
                f"Displacement is emphasis: the reader holds *{adj.text}* in suspense until "
                f"*{noun.text}* resolves it. Ask what fills the gap -- the words the poet "
                f"chose to delay the resolution are usually the point of the line. Hyperbaton "
                f"can also enact its own sense, framing or separating in sound what is framed "
                f"or separated in the story."
            ),
            confidence=0.7,
        ))
    return out


def _chiasmus_and_synchysis(sent: Sequence[Tok]) -> list[Device]:
    """ABBA and ABAB patterns in two adjective/noun pairs.

    Both figures need the same evidence -- two agreeing pairs interleaved -- and differ only
    in the order, so they are found together and told apart by their arrangement.
    """
    out = []
    pairs = [(a, n) for a, n in _agreeing_pairs(sent) if abs(a.i - n.i) > 1]
    for i, (a1, n1) in enumerate(pairs):
        for a2, n2 in pairs[i + 1 :]:
            idx = sorted([(a1.i, "A"), (n1.i, "a"), (a2.i, "B"), (n2.i, "b")])
            span = idx[-1][0] - idx[0][0]
            if span > 8 or len({p[0] for p in idx}) < 4:
                continue
            shape = "".join(p[1] for p in idx)
            words = " ".join(sent[p[0]].text for p in idx)
            if shape in ("ABba", "BAab"):
                out.append(Device(
                    key="chiasmus", name="Chiasmus", latin_name="chiasmus",
                    tokens=tuple(p[0] for p in idx),
                    evidence=f"adjective-adjective-noun-noun in mirror order: {words}",
                    explanation=(
                        f"*{words}* is arranged ABBA: the two pairs mirror one another about "
                        f"the centre. The name is from the Greek letter chi (X), whose "
                        f"crossing strokes the pattern traces."
                    ),
                    effect=(
                        "Chiasmus encloses and balances. It can frame a scene, set two things "
                        "in symmetry to compare or contrast them, or wrap the centre of the "
                        "line in the words that matter -- look at what sits in the middle."
                    ),
                    confidence=0.65,
                ))
            elif shape in ("ABab", "BAba"):
                out.append(Device(
                    key="synchysis", name="Synchysis (interlocked word order)",
                    latin_name="synchysis",
                    tokens=tuple(p[0] for p in idx),
                    evidence=f"adjective-adjective-noun-noun interlocked ABAB: {words}",
                    explanation=(
                        f"*{words}* interlocks two pairs, ABAB, so neither adjective stands "
                        f"beside its own noun. Only the agreement tells the reader which "
                        f"belongs to which."
                    ),
                    effect=(
                        "Interlocking makes the two pairs inseparable on the page, and is "
                        "often used where the sense is of things intertwined, confused or "
                        "bound together."
                    ),
                    confidence=0.65,
                ))
    return out[:3]


def _golden_line(sent: Sequence[Tok]) -> list[Device]:
    """adj adj verb noun noun -- the most admired arrangement in Latin verse."""
    out = []
    words = [t for t in sent if t.pos not in ("PUNCT", "X")]
    if len(words) != 5:
        return out
    a1, a2, v, n1, n2 = words
    if a1.pos != "ADJ" or a2.pos != "ADJ" or v.pos not in ("VERB", "AUX"):
        return out
    if n1.pos not in ("NOUN", "PROPN") or n2.pos not in ("NOUN", "PROPN"):
        return out
    ok = (a1.morph.get("Case") == n2.morph.get("Case")
          and a2.morph.get("Case") == n1.morph.get("Case"))
    out.append(Device(
        key="golden_line", name="Golden Line", latin_name="versus aureus",
        tokens=tuple(t.i for t in words),
        evidence="two adjectives, a verb, then two nouns" + (
            ", each adjective agreeing with the far noun" if ok else ""),
        explanation=(
            "A golden line: two adjectives, a central verb, then the two nouns they modify, "
            "in the pattern aAVbB. The verb stands exactly at the centre with the epithets "
            "on one side and their nouns on the other."
        ),
        effect=(
            "The most self-consciously artificial arrangement in Latin verse, used to mark a "
            "line as finished and perfect -- often at the close of a description or a "
            "paragraph. Its balance is the point, and it should be noticed as ornament."
        ),
        confidence=0.8 if ok else 0.5,
    ))
    return out


def _anastrophe(sent: Sequence[Tok]) -> list[Device]:
    """A preposition standing after its object: *maria omnia circum*."""
    out = []
    for t in sent:
        if t.dep != "case" or t.pos != "ADP":
            continue
        head = sent[t.head] if 0 <= t.head < len(sent) else None
        # Genuine anastrophe puts the preposition immediately after its object
        # (*Italiam contra*). Anything looser is usually the parser attaching the
        # preposition to the wrong noun -- it made *per* govern *aestate* two words back
        # in "aestate nova per florea rura".
        if head is None or t.i != head.i + 1:
            continue
        out.append(Device(
            key="anastrophe", name="Anastrophe", latin_name="anastrophe",
            tokens=(head.i, t.i),
            evidence=f"the preposition '{t.text}' follows its object '{head.text}'",
            explanation=(
                f"*{t.text}* governs *{head.text}* but stands after it, reversing the normal "
                f"order. Prose would write *{t.text} {head.text}*."
            ),
            effect=(
                "Inverting preposition and object is a mark of elevated style, and it lets a "
                "poet put the noun where the metre or the emphasis needs it."
            ),
            confidence=0.75,
        ))
    return out


# --------------------------------------------------------------------------------------
# Repetition and omission
# --------------------------------------------------------------------------------------


def _polyptoton(sent: Sequence[Tok]) -> list[Device]:
    """The same word repeated in different cases: *manus manum lavat*."""
    out = []
    by_lemma: dict[str, list[Tok]] = defaultdict(list)
    for t in sent:
        if t.pos in ("NOUN", "PROPN", "ADJ", "PRON", "VERB") and len(t.lemma) > 2:
            by_lemma[t.lemma].append(t)
    for lemma, group in by_lemma.items():
        forms = {_fold(t.text) for t in group}
        if len(group) < 2 or len(forms) < 2:
            continue
        if max(t.i for t in group) - min(t.i for t in group) > 10:
            continue
        quoted = " … ".join(t.text for t in group)
        out.append(Device(
            key="polyptoton", name="Polyptoton", latin_name="polyptoton",
            tokens=tuple(t.i for t in group),
            evidence=f"*{lemma}* appears in {len(forms)} different forms: {quoted}",
            explanation=(
                f"The same word *{lemma}* recurs in different grammatical forms ({quoted}). "
                f"The repetition is of the word, the variation of its case or person."
            ),
            effect=(
                "Polyptoton insists on a single idea while turning it round to view from "
                "another grammatical angle -- often to show one thing acting on another of "
                "its own kind, as in man against man."
            ),
            confidence=0.7,
        ))
    return out[:3]


def _anaphora(sents: list[Sequence[Tok]]) -> list[Device]:
    """The same word opening successive clauses or lines."""
    out = []
    heads: list[Tok] = []
    for s in sents:
        words = [t for t in s if t.pos != "PUNCT"]
        if words:
            heads.append(words[0])
    for i in range(len(heads) - 1):
        run = [heads[i]]
        for j in range(i + 1, len(heads)):
            if _fold(heads[j].text) == _fold(heads[i].text):
                run.append(heads[j])
            else:
                break
        if len(run) >= 2:
            out.append(Device(
                key="anaphora", name="Anaphora", latin_name="anaphora",
                tokens=tuple(t.i for t in run),
                evidence=f"'{run[0].text}' opens {len(run)} successive sentences or clauses",
                explanation=(
                    f"*{run[0].text}* is repeated at the head of each successive unit. The "
                    f"repetition is positional, not merely lexical: it is where the word "
                    f"stands that makes the figure."
                ),
                effect=(
                    "Anaphora builds insistence and rhythm, hammering the same word until it "
                    "accumulates weight. It is the natural figure of oratory and of lament."
                ),
                confidence=0.75,
            ))
    return out


def _asyndeton_polysyndeton(sent: Sequence[Tok]) -> list[Device]:
    """Conjunctions conspicuously absent, or conspicuously multiplied."""
    out = []
    conj_children = [t for t in sent if t.dep == "conj"]
    coordinators = [t for t in sent if t.dep == "cc" or t.lemma in ("et", "que", "atque", "ac")]
    if len(conj_children) >= 2 and not coordinators:
        members = [sent[conj_children[0].head]] + conj_children if 0 <= conj_children[0].head < len(sent) else conj_children
        quoted = ", ".join(m.text for m in members)
        out.append(Device(
            key="asyndeton", name="Asyndeton", latin_name="asyndeton",
            tokens=tuple(m.i for m in members),
            evidence=f"{len(members)} coordinate members with no conjunction: {quoted}",
            explanation=(
                f"*{quoted}* are coordinate, yet no *et* or *-que* joins them. The omission "
                f"is deliberate: Latin normally supplies one."
            ),
            effect=(
                "Asyndeton hurries. Stripping the connectives makes the items tumble out at "
                "speed, suggesting urgency, breathlessness, or a list too long to finish -- "
                "Caesar's *veni, vidi, vici* is the standard example."
            ),
            confidence=0.65,
        ))
    # The parse is not always reliable on bare coordination: it read the first word of
    # *veni, vidi, vici* as a vocative proper noun, leaving only one conj and hiding the
    # most famous asyndeton in Latin. Commas between same-POS items, with no conjunction
    # anywhere in the sentence, are surface evidence that does not depend on the parse.
    if not out and not coordinators:
        # Split the sentence at its commas. Asyndeton proper is a run of parallel members,
        # so require at least three segments each carrying exactly one content word --
        # which "veni, vidi, vici" satisfies and "quo usque tandem abutere, Catilina,
        # patientia nostra" (a parenthetical vocative, not a list) does not.
        segments: list[list[Tok]] = [[]]
        for t in sent:
            if t.text == ",":
                segments.append([])
            elif t.pos in ("VERB", "NOUN", "ADJ", "PROPN", "ADV", "NUM"):
                segments[-1].append(t)
        segments = [seg for seg in segments if seg]
        if len(segments) >= 3 and all(len(seg) == 1 for seg in segments):
            members = [seg[0] for seg in segments]
            quoted = ", ".join(m.text for m in members)
            out.append(Device(
                key="asyndeton", name="Asyndeton", latin_name="asyndeton",
                tokens=tuple(m.i for m in members),
                evidence=(f"{len(members)} single-word members separated by commas, with no "
                          f"conjunction anywhere in the sentence: {quoted}"),
                explanation=(
                    f"*{quoted}* stand in parallel with nothing joining them. Latin would "
                    f"normally supply *et* or *-que*; the omission is the figure."
                ),
                effect=(
                    "Asyndeton hurries. Stripping the connectives makes the items tumble out "
                    "at speed -- Caesar's *veni, vidi, vici* compresses a whole campaign into "
                    "three words precisely by refusing to join them."
                ),
                confidence=0.65,
            ))

    if len(coordinators) >= 3:
        out.append(Device(
            key="polysyndeton", name="Polysyndeton", latin_name="polysyndeton",
            tokens=tuple(t.i for t in coordinators),
            evidence=f"{len(coordinators)} coordinating conjunctions in one sentence",
            explanation=(
                "Conjunctions are multiplied where one would do, joining every member "
                "explicitly to the next."
            ),
            effect=(
                "Polysyndeton is the opposite gesture to asyndeton: it slows the line and "
                "weighs each item equally, building an impression of accumulation, of one "
                "thing after another without end."
            ),
            confidence=0.6,
        ))
    return out


def _tricolon(sent: Sequence[Tok]) -> list[Device]:
    """Three parallel members, often each longer than the last."""
    out = []
    groups: dict[int, list[Tok]] = defaultdict(list)
    for t in sent:
        if t.dep == "conj" and 0 <= t.head < len(sent):
            groups[t.head].append(t)
    for head_i, members in groups.items():
        if len(members) < 2:
            continue
        all_members = [sent[head_i]] + members
        if len(all_members) != 3:
            continue
        quoted = ", ".join(m.text for m in all_members)
        out.append(Device(
            key="tricolon", name="Tricolon", latin_name="tricolon",
            tokens=tuple(m.i for m in all_members),
            evidence=f"three coordinate members: {quoted}",
            explanation=(
                f"Three parallel members -- *{quoted}* -- stand in the same construction. "
                f"Three is the rhetorically satisfying number: enough to establish a pattern "
                f"and complete it."
            ),
            effect=(
                "A tricolon gives a sentence shape and finality. If each member is longer "
                "than the one before, it is a *tricolon crescens*, and the growth drives "
                "towards a climax on the third."
            ),
            confidence=0.6,
        ))
    return out


# --------------------------------------------------------------------------------------
# Figures keyed to closed lexical sets
# --------------------------------------------------------------------------------------

#: Words whose negation produces litotes: *non ignarus*, "not unaware", i.e. well aware.
NEGATIVE_SENSE = {
    "ignarus", "inscius", "nescius", "indoctus", "invitus", "improbus", "iniustus",
    "infelix", "indignus", "impius", "ingratus", "inutilis", "nullus", "nemo", "nihil",
    "numquam", "haud", "parum", "vanus", "inanis", "mediocris",
}
NEGATORS = {"non", "haud", "nec", "neque", "ne", "nunquam", "numquam", "nullus"}

#: Words introducing an explicit comparison.
SIMILE_MARKERS = {"velut", "veluti", "sicut", "sicuti", "ceu", "qualis", "quasi",
                  "tamquam", "tanquam", "aeque", "instar", "similis", "haud secus"}


def _litotes(sent: Sequence[Tok]) -> list[Device]:
    out = []
    for t in sent:
        if _fold(t.lemma) not in NEGATORS:
            continue
        for u in sent[t.i + 1 : t.i + 3]:
            if _fold(u.lemma) in NEGATIVE_SENSE or _fold(u.text).startswith(("in", "ig", "ne")):
                if _fold(u.lemma) not in NEGATIVE_SENSE:
                    continue
                out.append(Device(
                    key="litotes", name="Litotes", latin_name="litotes",
                    tokens=(t.i, u.i),
                    evidence=f"the negative '{t.text}' applied to '{u.text}', itself negative in sense",
                    explanation=(
                        f"*{t.text} {u.text}* denies the opposite instead of asserting the "
                        f"thing: 'not un-{u.lemma}' rather than plainly '{u.lemma}'s opposite'."
                    ),
                    effect=(
                        "Litotes is understatement that intensifies. Saying a hero is 'not "
                        "unknown' claims more than calling him famous, because the reader "
                        "supplies the affirmation themselves."
                    ),
                    confidence=0.7,
                ))
                break
    return out


def _simile(sent: Sequence[Tok]) -> list[Device]:
    out = []
    for t in sent:
        if _fold(t.lemma) not in SIMILE_MARKERS:
            continue
        out.append(Device(
            key="simile", name="Simile", latin_name="similitudo",
            tokens=(t.i,),
            evidence=f"the comparison is marked explicitly by '{t.text}'",
            explanation=(
                f"*{t.text}* introduces an explicit comparison. Unlike a metaphor, a simile "
                f"announces itself as a comparison rather than asserting identity."
            ),
            effect=(
                "The epic simile is a set piece: it suspends the narrative, opens a window "
                "onto a wholly different world -- usually nature, farming or weather -- and "
                "returns. Ask which detail of the comparison is meant to carry over, and "
                "which is there only to fill the picture."
            ),
            confidence=0.7,
        ))
    return out


def _apostrophe(sent: Sequence[Tok]) -> list[Device]:
    out = []
    for t in sent:
        if t.morph.get("Case") != "Voc":
            continue
        # A word cannot be both addressed and the subject of the clause. The parser tags
        # *veni* (1st person perfect) as a vocative proper noun and makes it nsubj; the
        # contradiction is the tell.
        if t.dep in ("nsubj", "nsubj:pass") or t.pos not in ("NOUN", "PROPN", "PRON", "ADJ"):
            continue
        out.append(Device(
            key="apostrophe", name="Apostrophe / Direct Address",
            latin_name="apostrophe",
            tokens=(t.i,),
            evidence=f"'{t.text}' is vocative",
            explanation=(
                f"The passage turns to address *{t.text}* directly, in the vocative."
            ),
            effect=(
                "Breaking off to address someone -- especially someone absent, dead, or a "
                "thing that cannot answer -- raises the emotional pitch sharply and pulls the "
                "reader into the speaker's feeling."
            ),
            confidence=0.7,
        ))
    return out[:3]


def _ellipsis(sent: Sequence[Tok]) -> list[Device]:
    """A clause with no finite verb, *esse* being the usual omission."""
    words = [t for t in sent if t.pos not in ("PUNCT", "X")]
    if len(words) < 3:
        return []
    if any("Fin" in (t.morph.get("VerbForm") or "") for t in sent):
        return []
    return [Device(
        key="ellipsis", name="Ellipsis", latin_name="ellipsis",
        tokens=tuple(t.i for t in words[:6]),
        evidence="the clause has no finite verb",
        explanation=(
            "A verb is left to be understood -- almost always a part of *esse*, which Latin "
            "omits freely. *Omnia praeclara rara* means 'all excellent things [are] rare'."
        ),
        effect=(
            "Ellipsis compresses. Dropping the copula makes a statement terser and more "
            "sententious, which is why proverbs and epigrams so often lack a verb."
        ),
        confidence=0.6,
        caveat="Also produced by a sentence fragment, a heading, or a list.",
    )]


# --------------------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------------------

DEVICE_INDEX = {
    "alliteration": "Alliteration", "assonance": "Assonance",
    "homoeoteleuton": "Homoeoteleuton", "hyperbaton": "Hyperbaton",
    "chiasmus": "Chiasmus", "synchysis": "Synchysis", "golden_line": "Golden Line",
    "anastrophe": "Anastrophe", "polyptoton": "Polyptoton", "anaphora": "Anaphora",
    "asyndeton": "Asyndeton", "polysyndeton": "Polysyndeton", "tricolon": "Tricolon",
    "litotes": "Litotes", "simile": "Simile", "apostrophe": "Apostrophe",
    "ellipsis": "Ellipsis",
}

_PER_SENTENCE: list[Callable[[Sequence[Tok]], list[Device]]] = [
    _hyperbaton, _chiasmus_and_synchysis, _golden_line, _anastrophe, _polyptoton,
    _asyndeton_polysyndeton, _tricolon, _litotes, _simile, _apostrophe, _ellipsis,
]


def detect_devices(sentences: list[Sequence[Tok]]) -> list[Device]:
    """Find every figure in a parsed passage."""
    found: list[Device] = []
    for sent in sentences:
        words = [t for t in sent if t.pos not in ("PUNCT", "X") and t.text]
        for fn in _PER_SENTENCE:
            try:
                found.extend(fn(sent))
            except Exception:
                continue
        for fn in (_alliteration, _assonance, _homoeoteleuton):
            try:
                found.extend(fn(sent, words))
            except Exception:
                continue
    try:
        found.extend(_anaphora(sentences))
    except Exception:
        pass
    found.sort(key=lambda d: -d.confidence)
    return found

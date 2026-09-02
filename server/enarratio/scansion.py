"""Scansion of Latin verse.

The problem is one of constraint satisfaction, not of lookup. A Latin syllable is long by
*nature* (its vowel is long, or it is a diphthong) or by *position* (its vowel is followed
by two consonants), and neither fact is recoverable from ordinary spelling: *populus* is
"poplar" with a long o and "people" with a short one, and nothing on the page says which.

So the method is:

1. Establish what is *certain* -- diphthongs, positional length, and the quantities recorded
   in Morpheus for forms we can identify.
2. Leave everything else undetermined.
3. Fit the metre, which is a rigid template, and let it resolve the unknowns.

That last step is the interesting one, and it mirrors what a reader actually does. You do
not scan *arma virumque cano* by knowing every quantity in advance; you know the line is a
hexameter, and the metre tells you the first *a* must be long. When a line admits more than
one scansion the ambiguity is real and both are reported.

Quantities come from ``data/morpheus-quantities.db`` (812,318 forms from the Perseus
Morpheus analyser, marked ``_`` long and ``^`` short). The database is large and separately
licensed, so it is fetched at setup rather than vendored; scansion degrades to
position-and-diphthong evidence alone if it is absent, which still scans most hexameters
because the metre does so much of the work.
"""

from __future__ import annotations

import functools
import os
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Sequence

__all__ = ["scan_line", "scan_passage", "Scansion", "Foot", "Syllable", "quantity_db"]

# --------------------------------------------------------------------------------------
# Orthography
# --------------------------------------------------------------------------------------

LONG, SHORT, UNKNOWN = "long", "short", "unknown"

VOWELS = set("aeiouy")

#: Genuine diphthongs. *ui* is a diphthong only in a closed list of forms (*cui*, *huic*,
#: *hui*); elsewhere -- *fui*, *tenuis* -- the vowels are separate, so it is handled by
#: exception rather than listed here.
DIPHTHONGS = ("ae", "au", "oe", "eu", "ei")
UI_DIPHTHONG_WORDS = {"cui", "huic", "hui", "cuiquam", "cuius"}

#: Digraphs standing for a single consonant: Greek aspirates plus *qu* and *gu*. They never
#: make position, which is why *patris* can scan with a short first syllable but *pascit*
#: cannot.
CONSONANT_DIGRAPHS = ("ch", "ph", "th", "rh", "qu", "gu")

#: Mute + liquid. In Latin verse the group may be split (making the syllable heavy) or kept
#: together (leaving it light) at the poet's discretion -- *muta cum liquida*. Such syllables
#: are marked as genuinely ambiguous rather than guessed at.
MUTES = set("bcdgpt")
LIQUIDS = set("lr")

#: *x* and *z* are double consonants: they close the preceding syllable on their own.
DOUBLE_CONSONANTS = set("xz")

ENCLITICS = ("que", "ve", "ne", "cum")


def fold(word: str) -> str:
    """Normalise to the orthography the quantity tables use: lowercase, no macrons, u/i."""
    w = unicodedata.normalize("NFD", word.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return w.replace("v", "u").replace("j", "i")


def fold_syll(word: str) -> str:
    """Like :func:`fold`, but keeps *v* as a consonant.

    Both functions map one character to one character, so a character offset means the same
    thing in either -- which is what lets quantities from the database be matched to
    syllables by position.
    """
    w = unicodedata.normalize("NFD", word.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return w.replace("j", "i")


def _macron_hints(word: str) -> dict[int, str]:
    """Quantities the writer marked explicitly, by vowel index.

    A user who pastes a macronised text has told us the answer, and that evidence outranks
    anything inferred.
    """
    hints: dict[int, str] = {}
    decomposed = unicodedata.normalize("NFD", word.lower())
    offset = 0
    i = 0
    while i < len(decomposed):
        ch = decomposed[i]
        if unicodedata.category(ch) == "Mn":
            i += 1
            continue
        if ch in VOWELS:
            vowel_index = offset
            marks = ""
            j = i + 1
            while j < len(decomposed) and unicodedata.category(decomposed[j]) == "Mn":
                marks += decomposed[j]
                j += 1
            if "\u0304" in marks:      # macron
                hints[vowel_index] = LONG
            elif "\u0306" in marks:    # breve
                hints[vowel_index] = SHORT
            offset += 1
            i = j
        else:
            offset += 1
            i += 1
    return hints


# --------------------------------------------------------------------------------------
# Quantity database
# --------------------------------------------------------------------------------------


class QuantityDB:
    """Vowel quantities from Morpheus, keyed by surface form.

    A form usually has several analyses; where they disagree about a vowel's quantity the
    vowel is left unknown, since choosing arbitrarily would be worse than admitting the
    ambiguity and letting the metre decide.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self._conn: sqlite3.Connection | None = None
        if path and path.exists():
            self._conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)

    @property
    def available(self) -> bool:
        return self._conn is not None

    @functools.lru_cache(maxsize=50_000)
    def lookup(self, form: str) -> dict[int, str] | None:
        """Vowel-index -> quantity, or None if the form is unknown."""
        if self._conn is None:
            return None
        rows = self._conn.execute(
            "SELECT accented FROM morpheus WHERE wordform = ? LIMIT 40", (form,)
        ).fetchall()
        if not rows:
            # Enclitics are written solid but analysed separately.
            for enc in ENCLITICS:
                if form.endswith(enc) and len(form) > len(enc) + 1:
                    base = self.lookup(form[: -len(enc)])
                    if base is not None:
                        return base
            return None
        merged: dict[int, str] = {}
        conflict: set[int] = set()
        for (accented,) in rows:
            for idx, q in _parse_accented(accented).items():
                if idx in merged and merged[idx] != q:
                    conflict.add(idx)
                merged[idx] = q
        for idx in conflict:
            merged.pop(idx, None)
        return merged


def _parse_accented(accented: str) -> dict[int, str]:
    """Read Morpheus's marks into {character offset: quantity}.

    ``ca^no_`` -> {0: short, 2: long}. Offsets are into the mark-stripped form, which lines
    up with the wordform column (Morpheus writes *v* in the accented field and *u* in the
    wordform, but the two are the same length).

    An **unmarked vowel counts as short**. Morpheus marks length where it is lexically
    distinctive, so treating unmarked as "no information" let the imperative *armā* silently
    supply a long final vowel for the far commoner neuter plural *arma*. Counting unmarked as
    short turns that into a visible disagreement between analyses, and disagreements are
    discarded in favour of letting the metre decide.
    """
    out: dict[int, str] = {}
    offset = 0
    i = 0
    while i < len(accented):
        ch = accented[i].lower()
        if ch in "_^":
            i += 1
            continue
        if ch in VOWELS or ch == "v":
            mark = accented[i + 1] if i + 1 < len(accented) else ""
            if ch in VOWELS:
                out[offset] = LONG if mark == "_" else SHORT
        offset += 1
        i += 1
    return out


@functools.lru_cache(maxsize=1)
def quantity_db() -> QuantityDB:
    env = os.environ.get("ENARRATIO_QUANTITY_DB")
    path = Path(env) if env else Path(__file__).resolve().parents[2] / "data" / "morpheus-quantities.db"
    return QuantityDB(path)


# --------------------------------------------------------------------------------------
# Syllabification
# --------------------------------------------------------------------------------------


@dataclass
class Syllable:
    text: str
    #: Index of the word this syllable belongs to, for display.
    word: int
    onset: str
    nucleus: str
    coda: str
    #: Character offset of the nucleus within the folded word -- the key that matches a
    #: syllable to a recorded quantity, and immune to consonantal i/u shifting the count.
    offset: int = -1
    quantity: str = UNKNOWN
    #: Why we believe the quantity. Shown to the reader.
    reason: str = ""
    #: True when the syllable is elided away and does not count metrically.
    elided: bool = False
    #: True for *muta cum liquida*, where the poet may treat it either way.
    common: bool = False

    @property
    def is_last_of_word(self) -> bool:
        return self._last_of_word

    _last_of_word: bool = False


#: Words where *su-* is consonantal (*suadeo* scans as two syllables, not three).
SU_CONSONANTAL = ("suad", "suau", "suav", "suesc", "suet", "suau")


def _consonantal_u(word: str) -> set[int]:
    """Positions where *u* is part of a consonant digraph and forms no syllable.

    Always after *q* (*qui* is one syllable, not two -- this single omission made every
    hexameter containing *qui* or *quae* come out two syllables too long). After *g* the
    *u* is consonantal only when a nasal precedes, as in *lingua* and *sanguis*; *exiguus*
    keeps its vowel. *su-* is consonantal in a short closed list.
    """
    out: set[int] = set()
    for i, ch in enumerate(word):
        if ch != "u":
            continue
        nxt = word[i + 1] if i + 1 < len(word) else ""
        if nxt not in VOWELS:
            continue
        if i == 0:
            # Texts printed without *v* write *uirum* for *virum*; an initial u before a
            # vowel is the consonant.
            out.add(i)
            continue
        prv = word[i - 1]
        if prv == "q":
            out.add(i)
        elif prv == "g" and i >= 2 and word[i - 2] in "n":
            out.add(i)
        elif prv == "s" and any(word.startswith(p) for p in SU_CONSONANTAL):
            out.add(i)
    return out


def _split_nuclei(word: str) -> list[tuple[int, str]]:
    """Locate the vowel nuclei, treating diphthongs as one."""
    out: list[tuple[int, str]] = []
    i = 0
    while i < len(word):
        ch = word[i]
        if ch in VOWELS:
            pair = word[i : i + 2]
            if pair in DIPHTHONGS:
                # *ae*/*oe* are not diphthongs when the second vowel begins a new syllable,
                # but that only happens with a diaeresis in the source, which folding removes.
                out.append((i, pair))
                i += 2
                continue
            if pair == "ui" and word in UI_DIPHTHONG_WORDS:
                out.append((i, pair))
                i += 2
                continue
            out.append((i, ch))
            i += 1
        else:
            i += 1
    return out


def _consonantal_i(word: str) -> set[int]:
    """Positions where *i* is the consonant *j* and so forms no syllable.

    Word-initial *i* before a vowel (*iam*, *iuuenis*), and *i* between two vowels
    (*maior*, *Troia*), where it is doubled in pronunciation and makes position.
    """
    out: set[int] = set()
    for i, ch in enumerate(word):
        if ch != "i":
            continue
        nxt = word[i + 1] if i + 1 < len(word) else ""
        prv = word[i - 1] if i > 0 else ""
        if nxt in VOWELS and (i == 0 or prv in VOWELS):
            if i == 0 or (prv in VOWELS and nxt in VOWELS):
                out.add(i)
    return out


def syllabify(word: str, word_index: int = 0) -> list[Syllable]:
    """Split one word into syllables with onset, nucleus and coda."""
    w = fold_syll(word)
    if not w or not any(c in VOWELS for c in w):
        return []
    skip = _consonantal_i(w) | _consonantal_u(w)
    nuclei = [(i, v) for i, v in _split_nuclei(w) if i not in skip]
    if not nuclei:
        return []

    sylls: list[Syllable] = []
    for n, (pos, nucleus) in enumerate(nuclei):
        start = 0 if n == 0 else nuclei[n - 1][0] + len(nuclei[n - 1][1])
        end = nuclei[n + 1][0] if n + 1 < len(nuclei) else len(w)
        between = w[pos + len(nucleus) : end]  # consonants after this nucleus

        if n + 1 < len(nuclei):
            onset_next, coda = _divide(between)
        else:
            onset_next, coda = "", between

        onset = w[start:pos] if n == 0 else _pending
        sylls.append(
            Syllable(
                text=onset + nucleus + coda,
                word=word_index,
                onset=onset,
                nucleus=nucleus,
                coda=coda,
                offset=pos,
            )
        )
        _pending = onset_next  # noqa: F841  (assigned for the next iteration)
    if sylls:
        sylls[-1]._last_of_word = True
    return sylls


def _divide(cluster: str) -> tuple[str, str]:
    """Split an intervocalic consonant cluster into (onset of next, coda of this).

    Latin syllable division: a single consonant goes with the following vowel; of two or
    more, the first closes the syllable. Digraphs count as one consonant, *x* and *z* as
    two, and mute+liquid is left to the caller to treat as common.
    """
    if not cluster:
        return "", ""
    units = _consonant_units(cluster)
    if len(units) == 1:
        if units[0] in DOUBLE_CONSONANTS:
            return "", units[0]
        return units[0], ""
    if len(units) == 2 and units[0] in MUTES and units[1] in LIQUIDS:
        # Ambiguous by convention; treat as onset (light) and flag the syllable common.
        return "".join(units), ""
    return "".join(units[1:]), units[0]


def _consonant_units(cluster: str) -> list[str]:
    """Break a cluster into consonant units, keeping digraphs together."""
    units: list[str] = []
    i = 0
    # *h* is a breathing, not a consonant, and never makes position: *nihil* scans light.
    cluster = re.sub(r"(?<=.)h", "", cluster)
    while i < len(cluster):
        pair = cluster[i : i + 2]
        if pair in CONSONANT_DIGRAPHS:
            units.append(pair)
            i += 2
        else:
            units.append(cluster[i])
            i += 1
    return units


# --------------------------------------------------------------------------------------
# Quantity assignment
# --------------------------------------------------------------------------------------


def _assign_quantities(sylls: list[Syllable], words: list[str]) -> None:
    """Mark everything we can establish before the metre is consulted."""
    db = quantity_db()
    per_word_hints: dict[int, dict[int, str]] = {}
    per_word_db: dict[int, dict[int, str] | None] = {}
    for wi, raw in enumerate(words):
        per_word_hints[wi] = _macron_hints(raw)
        per_word_db[wi] = db.lookup(fold(raw))

    for i, syl in enumerate(sylls):
        vi = syl.offset

        # 1. Diphthongs are always long by nature.
        if len(syl.nucleus) == 2:
            syl.quantity, syl.reason = LONG, f"'{syl.nucleus}' is a diphthong, long by nature"
            continue

        # 2. An explicit macron or breve in the source settles it.
        hint = per_word_hints[syl.word].get(vi)
        if hint:
            syl.quantity = hint
            syl.reason = f"marked {hint} in the text"
            continue

        # 3. Position. What matters is the number of consonants between this vowel and the
        #    NEXT vowel, counted across the word boundary -- not whether this syllable has a
        #    coda. A single word-final consonant before a vowel-initial word attaches to that
        #    word instead: *primus ab* scans pri-mus-ab as a dactyl, with *-mus* light,
        #    because only one consonant separates the u from the a.
        cluster = _following_consonants(sylls, i)
        units = _consonant_units(cluster)
        if units and units[0] in DOUBLE_CONSONANTS:
            syl.quantity = LONG
            syl.reason = f"long by position: '{units[0]}' is a double consonant"
            continue
        if len(units) >= 2:
            if units[0] in MUTES and units[1] in LIQUIDS:
                syl.common = True
                syl.reason = (
                    f"'{units[0]}{units[1]}' is mute + liquid, so this syllable may be scanned "
                    f"either way (*muta cum liquida*)"
                )
            else:
                syl.quantity = LONG
                syl.reason = f"long by position: followed by '{cluster[:2]}'"
                continue

        # 4. Failing all that, the quantity recorded for the vowel itself.
        rec = per_word_db[syl.word]
        if rec and vi in rec:
            syl.quantity = rec[vi]
            recorded = f"vowel recorded {rec[vi]} in Morpheus"
            syl.reason = f"{syl.reason}; {recorded}" if syl.reason else recorded


def _following_consonants(sylls: list[Syllable], i: int) -> str:
    """Consonants standing between this syllable's vowel and the next vowel."""
    out = sylls[i].coda
    for nxt in sylls[i + 1 :]:
        if nxt.elided:
            # An elided syllable loses its vowel, not its consonants. *multum ille*
            # is spoken "mult' ille", so the t still stands between the u of *mul-* and
            # the i of *ille*, and *mul-* is heavy. Skipping the whole syllable here made
            # every elision before a consonant scan one syllable too light.
            out += nxt.onset + nxt.coda
            continue
        out += nxt.onset
        break
    # *h* never makes position.
    return out.replace("h", "")


# --------------------------------------------------------------------------------------
# Elision
# --------------------------------------------------------------------------------------


def _mark_elisions(sylls: list[Syllable], words: list[str]) -> list[str]:
    """Elide a final vowel (or vowel + m) before a word beginning with a vowel or h.

    Reported rather than silently applied: elision is one of the things a student most needs
    pointing out, because the elided syllable is still on the page.
    """
    notes: list[str] = []
    for i, s in enumerate(sylls):
        if not s._last_of_word:
            continue
        nxt = next((t for t in sylls[i + 1 :]), None)
        if nxt is None or nxt.word == s.word:
            continue
        ends_open = not s.coda or s.coda == "m"
        if not ends_open:
            continue
        starts_vowel = (not nxt.onset) or nxt.onset == "h"
        if not starts_vowel:
            continue
        s.elided = True
        w1, w2 = words[s.word], words[nxt.word]
        notes.append(
            f"{w1} ~ {w2}: the final "
            + ("'-" + s.nucleus + "m'" if s.coda == "m" else "'-" + s.nucleus + "'")
            + f" of *{w1}* elides before the "
            + ("'h'" if nxt.onset == "h" else "vowel")
            + f" of *{w2}* and is not counted."
        )
    return notes


# --------------------------------------------------------------------------------------
# Metrical fitting
# --------------------------------------------------------------------------------------

DACTYL = ("long", "short", "short")
SPONDEE = ("long", "long")


@dataclass
class Foot:
    n: int
    kind: str            # "dactyl" | "spondee" | "final"
    syllables: list[int]  # indices into the live (non-elided) syllable list


@dataclass
class Scansion:
    line: str
    metre: str
    ok: bool
    pattern: str = ""
    feet: list[Foot] = field(default_factory=list)
    syllables: list[Syllable] = field(default_factory=list)
    elisions: list[str] = field(default_factory=list)
    caesurae: list[dict] = field(default_factory=list)
    alternatives: int = 0
    note: str = ""

    def as_dict(self) -> dict:
        live = [s for s in self.syllables if not s.elided]
        return {
            "line": self.line,
            "metre": self.metre,
            "ok": self.ok,
            "pattern": self.pattern,
            "note": self.note,
            "alternatives": self.alternatives,
            "elisions": self.elisions,
            "caesurae": self.caesurae,
            "feet": [{"n": f.n, "kind": f.kind, "syllables": f.syllables} for f in self.feet],
            "syllables": [
                {
                    "text": s.text,
                    "word": s.word,
                    "quantity": s.quantity,
                    "reason": s.reason,
                    "elided": s.elided,
                    "common": s.common,
                }
                for s in self.syllables
            ],
            "liveCount": len(live),
        }


def _fit_hexameter(q: list[str]) -> list[list[str]]:
    """Every foot-sequence consistent with the known quantities.

    Feet 1-5 are dactyl or spondee; the sixth is two syllables whose second is anceps. The
    search is exhaustive because a hexameter has at most 2^5 shapes -- there is no need for
    anything cleverer, and exhaustiveness is what lets us report genuine ambiguity.
    """
    n = len(q)
    solutions: list[list[str]] = []

    def compatible(i: int, want: str) -> bool:
        if i >= n:
            return False
        have = q[i]
        return have == UNKNOWN or have == want

    def rec(foot: int, pos: int, acc: list[str]) -> None:
        if foot == 6:
            # Final foot: two syllables, the last anceps.
            if pos == n - 2 and compatible(pos, LONG):
                solutions.append(acc + ["final"])
            return
        if compatible(pos, LONG) and compatible(pos + 1, SHORT) and compatible(pos + 2, SHORT):
            rec(foot + 1, pos + 3, acc + ["dactyl"])
        if compatible(pos, LONG) and compatible(pos + 1, LONG):
            rec(foot + 1, pos + 2, acc + ["spondee"])

    rec(1, 0, [])
    return solutions


def _apply(solution: list[str], sylls: list[Syllable], live: list[int]) -> list[Foot]:
    feet: list[Foot] = []
    pos = 0
    for i, kind in enumerate(solution, start=1):
        size = 3 if kind == "dactyl" else 2
        idxs = live[pos : pos + size]
        feet.append(Foot(n=i, kind=kind, syllables=idxs))
        # Write the resolved quantities back so the reader sees a complete scansion.
        wanted = [LONG, SHORT, SHORT] if kind == "dactyl" else [LONG, LONG]
        for j, si in enumerate(idxs):
            if kind == "final":
                sylls[si].quantity = LONG if j == 0 else "anceps"
                if not sylls[si].reason:
                    sylls[si].reason = (
                        "final syllable of the line: anceps, counted long whatever its nature"
                        if j else "resolved by the metre"
                    )
            elif sylls[si].quantity == UNKNOWN:
                sylls[si].quantity = wanted[j]
                sylls[si].reason = sylls[si].reason or f"resolved by the metre ({kind})"
        pos += size
    return feet


#: Caesurae by half-foot, named as the grammars name them.
CAESURA_NAMES = {3: "trithemimeral", 5: "penthemimeral", 7: "hephthemimeral", 9: "enneemimeral"}


def _find_caesurae(feet: list[Foot], sylls: list[Syllable]) -> list[dict]:
    """Word-ends falling inside a foot, which is where the line breathes."""
    found: list[dict] = []
    half = 0
    for f in feet:
        for j, si in enumerate(f.syllables):
            half += 2 if j == 0 else 1
            if j == 0:
                continue
            if sylls[si - 1]._last_of_word if si else False:
                pass
        # A caesura falls after the long of the foot when a word ends there.
        first = f.syllables[0] if f.syllables else None
        if first is not None and sylls[first]._last_of_word and f.n <= 5:
            hf = 2 * f.n - 1
            if hf in CAESURA_NAMES:
                found.append({
                    "foot": f.n,
                    "halfFoot": hf,
                    "name": CAESURA_NAMES[hf],
                    "kind": "masculine",
                    "after": sylls[first].text,
                    "note": (
                        "The main caesura of the line: the sense pauses here, and a reader "
                        "should too." if hf == 5 else
                        "A secondary break, often paired with a caesura elsewhere."
                    ),
                })
        # Feminine caesura: word-end after the first short of a dactyl.
        if f.kind == "dactyl" and len(f.syllables) == 3 and sylls[f.syllables[1]]._last_of_word:
            found.append({
                "foot": f.n,
                "halfFoot": 2 * f.n,
                "name": "feminine" + (" (kata triton trochaion)" if f.n == 3 else ""),
                "kind": "feminine",
                "after": sylls[f.syllables[1]].text,
                "note": (
                    "A feminine caesura in the third foot -- the characteristic Greek break, "
                    "much rarer in Latin than the masculine." if f.n == 3 else
                    "Word-end after the first short of the dactyl."
                ),
            })
    # Bucolic diaeresis: word-end coinciding with the end of foot 4.
    if len(feet) >= 4 and feet[3].syllables:
        last = feet[3].syllables[-1]
        if sylls[last]._last_of_word:
            found.append({
                "foot": 4, "halfFoot": 8, "name": "bucolic diaeresis", "kind": "diaeresis",
                "after": sylls[last].text,
                "note": "Word-end at the close of the fourth foot, a pastoral mannerism.",
            })
    return found


def scan_line(line: str, metre: str = "hexameter") -> Scansion:
    """Scan a single verse."""
    words = [w for w in re.findall(r"[A-Za-zÀ-ɏ]+", line) if w]
    if not words:
        return Scansion(line=line, metre=metre, ok=False, note="No words to scan.")

    sylls: list[Syllable] = []
    for wi, w in enumerate(words):
        sylls.extend(syllabify(w, wi))
    if not sylls:
        return Scansion(line=line, metre=metre, ok=False, note="No syllables found.")

    elisions = _mark_elisions(sylls, words)
    _assign_quantities(sylls, words)

    live = [i for i, s in enumerate(sylls) if not s.elided]
    q = [sylls[i].quantity for i in live]

    if metre != "hexameter":
        return Scansion(line=line, metre=metre, ok=False, syllables=sylls, elisions=elisions,
                        note=f"Only hexameter is implemented; {metre} was requested.")

    solutions = _fit_hexameter(q)
    if not solutions:
        # Retry allowing every *muta cum liquida* syllable to go light, which is the usual
        # licence and the commonest reason a first pass fails.
        relaxed = list(q)
        for n, i in enumerate(live):
            if sylls[i].common and relaxed[n] == LONG:
                relaxed[n] = UNKNOWN
        solutions = _fit_hexameter(relaxed)
        if solutions:
            for n, i in enumerate(live):
                if sylls[i].common:
                    sylls[i].quantity = UNKNOWN

    if not solutions:
        return Scansion(
            line=line, metre=metre, ok=False, syllables=sylls, elisions=elisions,
            note=(
                f"No hexameter fits these {len(live)} syllables. Either the line is not a "
                f"hexameter, or a quantity here is not in the database -- proper names are "
                f"the usual culprit."
            ),
        )

    feet = _apply(solutions[0], sylls, live)
    pattern = " | ".join(
        "-uu" if f.kind == "dactyl" else "--" if f.kind == "spondee" else "-x" for f in feet
    )
    return Scansion(
        line=line, metre=metre, ok=True, pattern=pattern, feet=feet, syllables=sylls,
        elisions=elisions, caesurae=_find_caesurae(feet, sylls),
        alternatives=len(solutions) - 1,
        note=(
            "" if len(solutions) == 1 else
            f"{len(solutions)} scansions fit; the first is shown. Ambiguity usually means a "
            f"vowel quantity is unrecorded, not that the line is genuinely ambiguous."
        ),
    )


def scan_passage(text: str, metre: str = "hexameter") -> list[dict]:
    """Scan each line of a passage independently."""
    return [scan_line(ln, metre).as_dict() for ln in text.splitlines() if ln.strip()]

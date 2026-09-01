"""Orthographic normalisation for Latin, preserving offsets into the original text.

Latin reaches us in wildly inconsistent orthography. The same word appears as
``seruus``/``servus``, ``iam``/``jam``, ``coelum``/``caelum``/``celum``; editors add
macrons the manuscripts never had, and print editorial brackets around conjectures.
Lexica and corpus indexes need one canonical spelling, but the reader must keep seeing
exactly what they pasted -- and clicking a word on screen has to reach the right entry.

So every transformation here is *offset-preserving*: :class:`Normalized` carries a map
from each character of the normalised string back to its index in the original, and a
token found in normalised space can always be projected back onto the original text.

Two levels of folding are distinguished:

``fold_display``
    Reversible presentation tidying only -- ligatures expanded, long s regularised,
    editorial marks removed. Still recognisably what the editor printed.

``fold_index``
    Aggressive folding to a canonical lookup key: diacritics stripped, v/u and j/i
    merged, case flattened. Lossy on purpose; never shown to the reader.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

__all__ = [
    "Normalized",
    "fold_display",
    "fold_index",
    "strip_quantities",
    "split_enclitic",
    "Enclitic",
    "ENCLITICS",
]


# --------------------------------------------------------------------------------------
# Character tables
# --------------------------------------------------------------------------------------

#: Vowels carrying a macron (long) or breve (short). Editors mark quantity inconsistently,
#: so quantity is stripped for lookup -- but it is *kept* for scansion, which is why the
#: original string is never discarded.
_QUANTITY_MARKS = {
    "̄",  # combining macron
    "̆",  # combining breve
    "̈",  # combining diaeresis (aëris, poëta -- marks hiatus, not quantity)
    "̣",  # combining dot below (used in some editions for elision)
}

#: Precomposed forms that decomposition alone will not handle.
_LIGATURES = {
    "æ": "ae",
    "Æ": "Ae",
    "œ": "oe",
    "Œ": "Oe",
    "ﬁ": "fi",
    "ﬂ": "fl",
}

#: Long s and other archaic printing conventions.
_ARCHAIC_GLYPHS = {
    "ſ": "s",
    "’": "'",
    "‘": "'",
    "“": '"',
    "”": '"',
    "—": " -- ",
    "–": "-",
}

#: Editorial apparatus that should not reach the analyser as text. The *content* inside
#: brackets is kept (it is usually a supplement the editor is confident about); only the
#: bracket glyphs are dropped, so ``[C]aesar`` normalises to ``Caesar`` rather than to
#: ``aesar``. Daggers mark hopeless corruption and are simply removed.
_EDITORIAL_MARKS = "[]<>{}†‡*⟨⟩⌈⌉"


# --------------------------------------------------------------------------------------
# The offset-preserving result type
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Normalized:
    """A normalised string plus the map back to where each character came from.

    ``origin[i]`` is the index in :attr:`original` that produced ``text[i]``. When one
    source character expands to several (``æ`` -> ``ae``) every output character points
    at the same source index; when a character is deleted no output index points at it.
    """

    original: str
    text: str
    origin: Sequence[int]

    def to_original_span(self, start: int, end: int) -> tuple[int, int]:
        """Project a ``[start, end)`` span in normalised space back onto the original.

        Returns the tightest span of the original text covering those characters, so a
        token located in normalised space can be highlighted in what the user pasted.
        """
        if start >= end:
            raise ValueError(f"empty or inverted span: [{start}, {end})")
        if not self.origin:
            return (0, 0)
        lo = self.origin[start]
        hi = self.origin[min(end, len(self.origin)) - 1] + 1
        return (lo, hi)

    def original_slice(self, start: int, end: int) -> str:
        """The original text underlying a normalised span -- what the reader should see."""
        lo, hi = self.to_original_span(start, end)
        return self.original[lo:hi]


class _Builder:
    """Accumulates output characters alongside the source index each came from."""

    def __init__(self, original: str) -> None:
        self._original = original
        self._out: list[str] = []
        self._origin: list[int] = []

    def emit(self, chars: str, source_index: int) -> None:
        for ch in chars:
            self._out.append(ch)
            self._origin.append(source_index)

    def build(self) -> Normalized:
        return Normalized(
            original=self._original,
            text="".join(self._out),
            origin=tuple(self._origin),
        )


# --------------------------------------------------------------------------------------
# Folding
# --------------------------------------------------------------------------------------


def _decompose(ch: str) -> str:
    """NFD-decompose a single character, keeping it intact if decomposition is a no-op."""
    return unicodedata.normalize("NFD", ch)


def fold_display(text: str) -> Normalized:
    """Tidy presentation without changing what word the reader sees.

    Expands ligatures, regularises archaic glyphs and drops editorial brackets and
    daggers. Quantity marks, capitalisation and v/u distinctions are *preserved* -- an
    edition that prints ``Arma virumque canō`` should still read that way on screen.
    """
    b = _Builder(text)
    for i, ch in enumerate(text):
        if ch in _EDITORIAL_MARKS:
            continue
        if ch in _LIGATURES:
            b.emit(_LIGATURES[ch], i)
            continue
        if ch in _ARCHAIC_GLYPHS:
            b.emit(_ARCHAIC_GLYPHS[ch], i)
            continue
        b.emit(ch, i)
    return b.build()


def fold_index(text: str) -> Normalized:
    """Fold to a canonical lookup key: no quantity, no case, v=u and j=i.

    This is the form used for dictionary lookup and for matching a pasted excerpt against
    the corpus index. It deliberately destroys information:

    - ``ā ē ī ō ū ȳ ă ĕ ĭ ŏ ŭ ë`` collapse to plain vowels (editions disagree on marking,
      and macrons are a modern pedagogical convention absent from ancient texts);
    - ``v`` -> ``u`` and ``j`` -> ``i`` (the Romans wrote ``VOLVIT`` and ``IAM``; the
      distinction is a Renaissance printing convention);
    - everything is lowercased.

    Note the ordering: ligatures must expand *before* case folding so ``Æ`` becomes
    ``ae`` rather than ``Ae`` -> ``ae`` by a second pass.
    """
    b = _Builder(text)
    for i, ch in enumerate(text):
        if ch in _EDITORIAL_MARKS:
            continue
        expanded = _LIGATURES.get(ch) or _ARCHAIC_GLYPHS.get(ch) or ch
        out_chars: list[str] = []
        for piece in expanded:
            for sub in _decompose(piece):
                if sub in _QUANTITY_MARKS or unicodedata.combining(sub):
                    continue
                out_chars.append(sub)
        folded = "".join(out_chars).lower()
        folded = folded.replace("v", "u").replace("j", "i")
        b.emit(folded, i)
    return b.build()


def strip_quantities(text: str) -> str:
    """Remove macrons and breves, leaving case and v/u alone.

    Used when comparing a macronised edition against an unmacronised one, where folding
    all the way to index form would throw away distinctions still worth keeping.
    """
    out = []
    for ch in unicodedata.normalize("NFD", text):
        if ch in _QUANTITY_MARKS:
            continue
        out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


# --------------------------------------------------------------------------------------
# Enclitics
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Enclitic:
    """An enclitic particle and the words it must never be stripped from."""

    form: str
    gloss: str
    #: Words that merely *end* in this string. Splitting these is the classic tokeniser
    #: bug: ``quinque`` is not ``quin`` + ``-que``, and ``virgine`` is not ``virgi`` + ``-ne``.
    blocklist: frozenset[str] = field(default_factory=frozenset)
    #: Suffixes that make a split implausible even for words not individually listed.
    blocked_suffixes: tuple[str, ...] = ()


ENCLITICS: tuple[Enclitic, ...] = (
    Enclitic(
        form="que",
        gloss="and (joins this word to what precedes)",
        blocklist=frozenset(
            {
                # Lexicalised -que that is not the conjunction
                "absque", "atque", "cumque", "denique", "itaque", "namque", "neque",
                "plerumque", "quoque", "susque", "undique", "usque", "utique", "ubique",
                "quisque", "quidque", "quodque", "quemque", "quamque", "quosque",
                "quasque", "cuiusque", "cuique", "quoque", "quaque", "quibusque",
                "uterque", "utraque", "utrumque", "utriusque", "utrique", "utrumque",
                "plerique", "pleraque", "pleraeque", "plerosque", "plerasque",
                "quicumque", "quaecumque", "quodcumque", "quemcumque", "quocumque",
                "quacumque", "quotcumque", "ubicumque", "quandocumque", "utcumque",
                # Ordinary words that happen to end in -que
                "quinque", "torque", "coque", "cinque", "aeque", "abusque", "seque",
            }
        ),
        blocked_suffixes=("cumque",),
    ),
    Enclitic(
        form="ne",
        gloss="interrogative particle (marks this as a yes/no question)",
        blocklist=frozenset(
            {
                "bene", "sine", "paene", "pone", "omne", "plane", "superne", "inferne",
                "interne", "digne", "benigne", "maligne", "impune", "commune", "immune",
                "iuvene", "iuuene", "cane", "mane", "sane", "vane", "uane",
                "plene", "obscene", "serene", "amoene",
            }
        ),
        # Third-declension ablative singulars in -ine/-mine/-dine/-gine/-tudine are
        # extremely common (virgine, carmine, ordine, imagine, multitudine) and are the
        # dominant false-positive class for -ne. Consonant-stem ablatives generally.
        blocked_suffixes=(
            "ine", "mine", "dine", "gine", "tudine", "one", "ione", "gone", "rne",
            "sne", "cne", "gne", "pne", "tne",
        ),
    ),
    Enclitic(
        form="ve",
        gloss="or (inclusive alternative)",
        blocklist=frozenset(
            {
                "breve", "grave", "leve", "suave", "dulce", "nove", "noue", "prave",
                "praue", "salve", "salue", "cave", "caue", "solve", "solue", "volve",
                "uolue", "fave", "faue", "serve", "serue", "nerve", "nerue", "curve",
                "curue", "vive", "uiue", "move", "moue", "lave", "laue",
            }
        ),
    ),
)

#: ``cum`` attaches enclitically to personal and relative pronouns: ``mecum``, ``nobiscum``,
#: ``quibuscum``. This is a preposition in postposition, not a particle, so it is handled
#: separately -- the split yields a real word, not a clitic.
_CUM_HOSTS = {
    "mecum": "me", "tecum": "te", "secum": "se",
    "nobiscum": "nobis", "uobiscum": "uobis", "vobiscum": "vobis",
    "quocum": "quo", "quacum": "qua", "quicum": "qui", "quibuscum": "quibus",
}


def split_enclitic(
    word: str,
    is_known_word: Callable[[str], bool] | None = None,
) -> tuple[str, Enclitic | None]:
    """Split a trailing enclitic off a word, or return the word unchanged.

    Returns ``(stem, enclitic)`` where ``enclitic`` is ``None`` if nothing was split.

    Splitting Latin enclitics correctly *requires a lexicon*, and any rule that works
    without one will mangle real words. ``quinque`` is not ``quin``+``que``; ``virgine``
    is not ``virgi``+``ne``; ``breve`` is not ``bre``+``ve``. Pass ``is_known_word`` --
    a membership test against the lemma bank or a full-form lexicon -- and the split is
    refused whenever the intact word is itself attested. Without it, this falls back to
    hand-maintained blocklists, which catch the frequent traps but not the long tail.

    The input should already be :func:`fold_index`-folded (lowercase, v=u, j=i), since
    the blocklists are written in that form.
    """
    if is_known_word is not None and is_known_word(word):
        # The intact form is in the lexicon; prefer it. This is the single most effective
        # guard, and it is why the lexicon is threaded into tokenisation at all.
        if word not in {"multaque"}:  # (placeholder for forms attested both ways)
            return word, None

    if word in _CUM_HOSTS:
        return _CUM_HOSTS[word], Enclitic(form="cum", gloss="with (postposed preposition)")

    for enc in ENCLITICS:
        if not word.endswith(enc.form) or len(word) <= len(enc.form) + 1:
            continue
        if word in enc.blocklist:
            continue
        if any(word.endswith(suf) for suf in enc.blocked_suffixes):
            continue
        stem = word[: -len(enc.form)]
        if is_known_word is not None and not is_known_word(stem):
            # Splitting would produce a non-word; the enclitic reading is wrong.
            continue
        return stem, enc
    return word, None

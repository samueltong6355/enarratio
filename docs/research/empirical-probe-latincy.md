# Empirical probe: what LatinCy actually does

**Status:** primary evidence. Everything below was measured on this machine, not read about.
Where it contradicts a claim in the other research notes, this file wins.

**Setup:** macOS arm64 (Apple M5), Python 3.12.14 via `uv`, spaCy 3.8.16,
`la_core_web_lg==3.9.6` installed from
`https://huggingface.co/latincy/la_core_web_lg/resolve/main/la_core_web_lg-3.9.6-py3-none-any.whl`
(MIT). The wheel pulls in `la-latincy-lookups==1.0.0` and `latincy-preprocess==0.3.3`.

Note the version scheme: the model's `3.9.6` is LatinCy's own numbering, **not** a spaCy
version requirement. It installs and runs against spaCy 3.8.16, the current PyPI release.

## Pipeline

```
enclitic_splitter, tok2vec, senter, token_fix, normer, tagger, morphologizer,
trainable_lemmatizer, lookup_lemmatizer, uv_normalizer, harmonizer, remorpher, parser, ner
```

Self-reported accuracy from `nlp.meta["performance"]`:

| Metric | Score |
|---|---|
| UPOS accuracy | 96.48% |
| XPOS (tag) accuracy | 89.12% |
| Morphological analysis accuracy | 90.78% |
| Case precision / recall | 93.91% / 93.48% |
| Gender precision / recall | 91.99% / 91.58% |
| Sentence segmentation F | 93.00% |
| NER F | 88.36% |

**Read that morph figure carefully: roughly one token in eleven carries a wrong
morphological analysis.** For a tool whose entire premise is "fully explain this word",
that is the single most important number in this document. It is why the interface must
show competing readings with confidence rather than assert a single parse.

## Finding 1 — The parser gives no signal about whether the input is Latin

This is the most consequential finding, because it kills the obvious design for the
grammaticality gate.

Fed `The quick brown fox jumps over the lazy dog every single morning.`, the pipeline
returned a complete, confident parse:

```
The      PROPN  vocative  Case=Nom|Gender=Fem|Number=Sing
quick    DET    det       Case=Abl|Gender=Fem|Number=Sing
brown    NOUN   obj       Case=Abl|Number=Sing
fox      ADV    advmod    (lemma: fauces)
iumps    NOUN   amod      Case=Acc|Gender=Neut|Number=Sing
```

Lorem ipsum parsed just as happily. A statistical parser always emits its best guess; it
has no "this is not Latin" output and no calibrated confidence at the sentence level.

**Consequence:** the grammaticality gate must be built from evidence the parser does not
provide — lexicon coverage, character n-gram language identification, morphological
agreement checking, and finite-verb presence. It cannot be "did the parser succeed".

## Finding 2 — The bundled lookup table is not an OOV gate

> **Corrected.** An earlier revision of this note reported that `regis` and `bella` were
> absent from the table. That was a bug in the probe, not a fact about LatinCy: it queried
> the table through spaCy's string-hash interface, which does not do what I assumed. Read
> the raw `la_latincy_lookups/data/la_lemma_lookup.json` instead. The per-word claims below
> are the corrected ones; the conclusion happens to be unchanged, but it now rests on real
> evidence. The table is also stored **u-normalised** (`uirum` present, `virum` absent), so
> any query must fold v→u first.

`la_latincy_lookups` ships a `lemma_lookup` table with **909,669 entries**, which looks
like an offline full-form lexicon. It is not usable as a measure of Latinity.

Present: `regis`, `bella`, `amor`, `cano`, `carmine`, `quinque`, `uirum`.
Absent: **`arma`**, **`est`**, **`et`**, **`qui`**, **`quo`** — some of the commonest words
in the language. Also present: `consectetur`, a Lorem ipsum word.

Measured in-vocabulary rate (v→u folded, macrons stripped):

| Input | In-vocabulary | Words it fails to recognise |
|---|---|---|
| Cicero, *Cat.* 1.1 | 86% | `quo` |
| Vulgate, John 1.1 | 78% | `principio`, `et` |
| Lorem ipsum | **70%** | `lorem`, `adipiscing`, `elit` |
| Broken student Latin | 70% | `est`, `et`, `canis` |
| Caesar, *BG* 1.1 | 64% | `est`, `omnis`, `quarum`, `unam` |
| Vergil, *Aen.* 1.1 | **45%** | `arma`, `uirumque`, `troiae`, `qui`, `oris`, `fato` |
| Italian | 30% | — |
| English | 17% | — |
| Gibberish | 0% | — |

Lorem ipsum scores 70% and Vergil 45%. A gate built on this table would reject the *Aeneid*
and accept filler text. The table is evidently a lemma list from some particular corpus
rather than a coverage-complete form list, and it cannot separate Latin from non-Latin nor
serve as the `is_known_word` oracle that safe enclitic splitting needs.

**Consequence:** the vocabulary signal must come from a real morphological analyser. See
Finding 7 — `latincy-lexicon` supplies one.

## Finding 3 — Competing analyses ARE recoverable, with context-sensitive probabilities

The morphologizer is a classifier over 1,208 morphological tags. Its full distribution can
be read out, giving exactly the "here is the ambiguity, and here is why this reading wins"
display the project is built around.

The encoder must be run first — predicting on a bare `make_doc` yields a uniform
distribution (an easy mistake; it cost one probe iteration):

```python
doc = nlp.make_doc(text)
for name in ("enclitic_splitter", "tok2vec"):
    doc = nlp.get_pipe(name)(doc)
scores = nlp.get_pipe("morphologizer").model.predict([doc])
```

Results, and they are genuinely good:

| Input | Top readings |
|---|---|
| `regis` (alone) | 92.1% `Case=Gen\|Gender=Masc\|Number=Sing\|POS=NOUN`, 7.0% `Person=2\|Tense=Pres\|VerbForm=Fin\|POS=VERB` |
| `regis filia` | 100% genitive noun |
| `regis populum` | **69% 2sg present verb**, 30% genitive noun |
| `bella gerunt` | 100% `Case=Acc\|Gender=Neut\|Number=Plur\|POS=NOUN` (*wars*) |
| `bella puella` | **98% `Case=Nom\|Gender=Fem\|Number=Sing\|POS=ADJ`** (*beautiful*) |
| `cano` in *Arma virumque cano* | 65.5% 1sg pres. *canō*, 17.3% abl. sg. of *cānus* |

The model correctly flips `regis` between noun and verb, and `bella` between noun and
adjective, on the strength of one neighbouring word. The residual probability on `cano` is
not noise — that form really is ambiguous, and saying so is the pedagogically honest answer.

**Consequence:** this is a first-class feature, not a fallback. The token panel should show
the winning analysis, the runners-up with their probabilities, and — where the runner-up is
non-trivial — an explanation of what would have to be true for it to win instead.

## Finding 4 — Ablative absolutes are directly labelled, but only sometimes

LatinCy emits a non-standard dependency label **`advcl:abs`** for ablative absolutes.

| Sentence | Result |
|---|---|
| *His rebus gestis...* | `gestis` → `advcl:abs` ✓ |
| *Urbe capta cives fugerunt* | `capta` → `advcl:abs` ✓ |
| *Caesare duce milites pugnaverunt* | `duce` → `advcl:abs` ✓ |
| *Me duce tutus eris* | `duce` → `obl` ✗ |
| *Cicerone consule coniuratio detecta est* | `consule` → `obl` ✗ |

Participial ablative absolutes are caught reliably. **Nominal** ones (noun + noun with no
participle, the *Cicerone consule* / *me duce* type) are caught only sometimes.

**Consequence:** the construction detector cannot simply trust `advcl:abs`. It needs a
supplementary rule for the nominal type: two words in the ablative agreeing in case and
number, the second drawn from the closed class of role nouns that license the construction
(*dux, consul, rex, auctor, testis, iudex, praetor, puer, senex*) or the predicative
adjectives *vivo, invito, inscio, salvo*, with neither word governed by a preposition.

Other observed parse errors on this small sample: `Urbe` tagged `PROPN` (it is a common
noun); `duce` given `Gender=Fem`; `litora` in *Aen.* 1.2–3 labelled `nsubj` when it is the
accusative of the place to which; and `Os` in *Aen.* 1.589 (`Os umerosque deo similis`, the
canonical Greek accusative) assigned **no morphological features at all** — precisely the
construction a Latin reader most wants explained.

## Finding 5 — Enclitic splitting is correct on the traps

The `enclitic_splitter` component splits genuine enclitics and correctly leaves alone the
words that merely end in the same letters:

- Split: `virumque` → `uirum` + `que`; `populusque`, `senatusque`; `mecum` → `me` + `cum`.
- **Not** split (correct): `quinque, itaque, neque, namque, denique, uterque, quisque,
  torque, virgine, carmine, multitudine, bene, sine, paene, breve, grave, salve, suave,
  undique, usque, plerique`.

Gaps: interrogative `-ne` and disjunctive `-ve` are **not** split — `estne`, `videsne` and
`aliusve` come through whole. Since `-ne` is what marks a yes/no question, this matters for
explaining sentence force, and our own splitter must cover it.

The pipeline also folds `v` → `u` internally (`venit` → `uenit`, `virum` → `uirum`), which
matches the index-folding convention in `server/enarratio/normalize.py`.

## Finding 6 — CLTK conflicts with the pinned Python

`cltk 2.5.1` declares `requires_python >=3.13`, while the spaCy/LatinCy stack is pinned to
3.12. They cannot share one environment. CLTK should be treated as an optional, separately
installed tool rather than a core dependency.

## Finding 7 — `latincy-lexicon` supplies the complete candidate set and the paradigms

`pip install latincy-lexicon` (v0.11.1, MIT) adds `nlp.add_pipe("whitakers_words")`: Whitaker's
WORDS and Lewis & Short as spaCy components, with the data bundled — no download step.

`token._.ww` returns **every** analysis the stem+ending engine can produce, ranked using the
upstream tagger's output. Each entry is fully specified:

```json
{"form": "regis", "lemma": "rex", "pos": "N", "decl": "3.0", "meaning": "king;",
 "stem": "reg", "ending": "is", "case": "GEN", "number": "S", "age": "A", "freq": "A"}
```

For `regis` it yields four slots of *rēx* plus *regō* (V) and *regius* (ADJ) — and the ranking
flips to put *regō* first in `regis populum`. `token._.lexicon` gives dictionary entries with
principal parts, declension and frequency; `paradigm_generator` gives full paradigms and
reinflection (`scribit` → `scribunt`, `scribebat`, `scribitur`).

This is the missing layer from Finding 2, and it resolves the architecture: **LatinCy ranks,
Whitaker enumerates.** The candidate set is complete (so the reader sees every possible
reading) and the ranking is contextual (so the reader is told which one wins, and by how much).

## Finding 8 — The gate can test for Latin, but not for grammaticality

Measured across genuine prose, verse, late and Neo-Latin, deliberately broken student Latin,
and five other languages:

| Signal | Real Latin | Not Latin | Broken Latin |
|---|---|---|---|
| Whitaker analysability | 86–100% | 0–58% | ~100% |
| `lingua` Latin confidence | 0.83–1.00 | 0.002–0.04 | 0.45–0.99 |

**The two signals are complementary and should be combined.** `lingua` cleanly rejects English
(0.020), Italian (0.039), Spanish (0.002) and Romanian (0.003), but rates Lorem ipsum 0.996 —
which Whitaker catches at 58%. Conversely `lingua` collapses on short input (*Carpe diem.* =
0.338) where Whitaker gives 100%. Neither alone is sufficient; together they separate cleanly.

**Grammaticality is a different matter, and the obvious test fails badly.** Checking
adjective/determiner agreement against its head:

| Text | Agreement violations | |
|---|---|---|
| Vergil, *Aen.* 1.1–3 | **5 / 6** | false positive |
| Horace, *C.* 1.5 | **5 / 12** | false positive |
| Broken student Latin | 2 / 3 | true positive |
| Word salad (*Rosa mensa dominus…*) | 0 / 0 | **missed** |

Poetic hyperbaton separates adjective from noun by whole lines, the parser mis-attaches the
modifier, and the checker reports a violation. Vergil and Horace — precisely the authors a
student most needs help with — score *worse* than deliberately broken Latin. Meanwhile a list
of unconnected nouns passes cleanly, since it violates no agreement rule at all. Requiring a
finite verb does not rescue this either: the word salad has none, but neither does the genuine
Latin *Omnia praeclara rara* (ellipsis of *esse*).

**Consequence — a deliberate departure from the original specification.** The brief asked the
program to verify the passage is grammatically sound and to proceed only if it is. Implemented
literally, that gate would refuse the *Aeneid*. So the gate is split:

- **Language identity** (*is this Latin?*) — gated, using the two complementary signals. This
  is reliable, and refusing non-Latin input is correct behaviour.
- **Grammaticality** (*is this well-formed Latin?*) — **never** blocks analysis. Anomalies are
  surfaced as flagged observations on the affected tokens, with the caveat that poetic word
  order is the likeliest explanation. The reader decides.

This fails soft on purpose. A tool that silently refuses hard passages is worse than useless to
someone translating hard passages.

## What this means for the build

1. Adopt LatinCy `la_core_web_lg` as the contextual disambiguator and dependency parser.
2. Do **not** rely on it for the "is this Latin?" gate; build that from independent signals.
3. Do **not** rely on it as the enumerator of possible analyses either — it is trained on
   what is *likely*, not what is *possible*. Pair it with a real morphological analyser so
   the candidate set is complete, and use LatinCy's distribution to rank that set.
4. Surface the probability distribution in the UI. It is the honest representation of Latin
   morphology and the app's best pedagogical asset.
5. Treat every displayed analysis as defeasible: ~9% of morphological analyses are wrong,
   so the interface must never present a parse as settled fact.

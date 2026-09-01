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

## Finding 2 — The bundled lookup table is not a lexicon, and not an OOV gate

`la_latincy_lookups` ships a `lemma_lookup` table with **909,669 entries**, which looks
like an offline full-form lexicon. It is not usable as one.

```
known('arma')        = False      # first word of the Aeneid
known('regis')       = False
known('uirum')       = True
known('quinque')     = True
known('consectetur') = True       # ...a Lorem ipsum word
```

Measured in-vocabulary rate by input type:

| Input | In-vocabulary |
|---|---|
| Caesar, *BG* 1.1 | 64% |
| Vergil, *Aen.* 1.1–2 | 38% |
| Lorem ipsum | 55% |
| Italian (Dante) | 23% |
| English | 18% |

Real Vergil scores *below* Lorem ipsum. The table is skewed (the sample entries are
biblical proper nouns like `Aaron`) and cannot separate Latin from non-Latin, nor serve as
the `is_known_word` oracle that safe enclitic splitting needs.

**Consequence:** a genuine full-form lexicon must come from elsewhere — Whitaker's WORDS
`DICTLINE`, Morpheus, LEMLAT, or paradigm expansion over Lewis & Short headwords. This is
now a hard requirement of the data-acquisition plan, not a nice-to-have.

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

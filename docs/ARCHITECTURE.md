# Architecture

Enarratio turns a pasted Latin excerpt into a fully annotated reading. This document
explains how, and — more usefully — *why each choice was made*, since several of them were
forced by measurements that contradicted the obvious design.

The measurements are in [`research/empirical-probe-latincy.md`](research/empirical-probe-latincy.md).
Where this document asserts a number, that file is the evidence.

## The governing principle

> The deterministic layers state facts. Any generative layer may only phrase them.

Morphology, syntax, lexicon and metre come from real parsers and real dictionaries. A
language model, when one is added, is confined to putting that analysis into prose, and
every grammatical claim it makes is checked against the parser's output before display.
This is the difference between a research tool and a plausible-sounding guess.

## Pipeline

```
pasted text
    │
    ├─1─ normalise ................ server/enarratio/normalize.py
    │      offset-preserving folding; v/u, i/j, ligatures, macrons, editorial brackets
    │
    ├─2─ parse .................... LatinCy la_core_web_lg
    │      lemma, UPOS, morphology, dependencies, NER
    │
    ├─3─ enumerate ................ latincy-lexicon (Whitaker's WORDS)
    │      EVERY morphologically possible reading, not just the likely one
    │
    ├─4─ rank ..................... morphologizer probability distribution
    │      contextual probabilities over the candidate set
    │
    ├─5─ gate ..................... server/enarratio/gate.py
    │      "is this Latin?" only — never "is this good Latin?"
    │
    ├─6─ detect constructions ..... server/enarratio/constructions.py
    │      28 named constructions over morphology + dependencies
    │
    ├─6b─ classify case usage ..... server/enarratio/cases.py
    │      42 uses of the genitive, dative, accusative, ablative, gerund/gerundive
    │
    ├─6c─ detect literary figures . server/enarratio/devices.py
    │      17 figures, each explaining its effect rather than just its name
    │
    ├─6d─ identify the passage .... server/enarratio/identify.py + corpus.py
    │      hashed 5-gram shingle index; Perseus citations, Latin Library for breadth
    │
    ├─6e─ attach commentary ....... server/enarratio/commentary.py
    │      28,747 notes keyed by (work, reference, line)
    │
    ├─6f─ scan the metre .......... server/enarratio/scansion.py
    │      hexameter, solving quantity and metre as one constraint problem
    │
    └─7─ assemble ................. server/enarratio/pipeline.py
           dictionary entries, paradigm data, human-readable parse
```

### Why steps 3 and 4 are separate

This is the central design decision. LatinCy is a statistical model trained on what is
*likely*; Whitaker's WORDS is a rule engine describing what is *possible*. Neither alone is
adequate:

- Ask only LatinCy and you get one reading, sometimes an incoherent one. For `regis` it
  returned lemma `regō` (the verb) combined with `Case=Gen|Number=Sing` (the noun *rēx*) —
  a parse that cannot exist.
- Ask only Whitaker and you get six readings with no way to choose between them.

Together they give what a student actually needs: the complete space of possibilities, and
an argued ranking within it. `regis` alone ranks 92.1% genitive noun / 7.0% second-person
verb; before `populum` that flips to 69% verb; before `filia` it goes to 100% noun. The
interface shows this, because Latin morphology *is* ambiguous and concealing that teaches
students to trust the tool instead of to read.

Note the implementation trap in step 4: the morphologizer's distribution is only meaningful
if the encoder has been run first. Calling `predict()` on a bare `make_doc` returns a
uniform distribution over all 1,208 tags.

### Why the gate does what it does

The brief asked the program to verify that the passage is grammatically sound and to
proceed only if it is. Measurement showed that requirement cannot be met as stated, and
that meeting it literally would make the tool useless:

- **The parser cannot detect non-Latin.** Fed English, it returns a confident full parse
  with morphology. It has no failure mode to observe.
- **Agreement checking rejects the best Latin.** It flags 5 of 6 modifiers in *Aeneid*
  1.1–3 and 5 of 12 in Horace *C.* 1.5, because hyperbaton separates adjective from noun by
  whole lines and the parser reattaches them wrongly. Deliberately broken student Latin
  scores *better*.
- **Requiring a finite verb rejects real Latin too**, since *esse* is routinely elided
  (*omnia praeclara rara*).

So the gate was split. **Language identity** is gated, using two complementary signals that
separate cleanly (Whitaker analysability ≥86% for genuine Latin vs ≤58% for everything
else; `lingua` confidence for the Romance languages and English below 0.05). **Grammaticality
is never gated** — irregularities are attached to the affected tokens as observations, each
noting that displaced word order is the likelier explanation than faulty Latin.

A tool that silently refuses hard passages is worthless to someone translating hard passages.

### Why the case system needs its own module

Naming constructions and classifying case usage are different problems. A construction like
the ablative absolute is a *shape* — two ablatives, a participle, no preposition — and
either the shape is there or it is not. A case *use* is a question about function that has
to be answered for every oblique noun in the passage, and the answer is rarely structural.

The ablative is the reason. Latin merged three Indo-European cases into one form — the
ablative proper (*from*), the instrumental (*with*), and the locative (*in*) — so a single
ending carries separation, means, manner, accompaniment, price, respect, cause, origin,
degree of difference, route, place and time. No amount of morphology distinguishes them.
What distinguishes them is the governing word, the presence or absence of a preposition,
and the semantic class of the noun. That is why `cases.py` is mostly closed lexical lists:
a bare ablative is ambiguous between a dozen readings, but a bare ablative governed by
*emo* is a price, and one governed by *careo* is separation.

Where two readings genuinely compete the module reports both. Subjective and objective
genitives are formally identical — *amor patris* is the father's love or love for the
father — so offering one and suppressing the other would be a false precision.

### Why the parse needs surface fallbacks

Rules keyed on the dependency parse keep failing in the same few ways, and each failure is
now worked around rather than tolerated:

| What the parser does | Consequence | Fallback |
|---|---|---|
| Attaches an oblique noun to the neighbouring noun, not the verb | verb-keyed rules never fire | climb to the nearest governing verb |
| Picks one case for an ambiguous form (`gloriae` → dative) | genitive rules blocked | consult Whitaker's candidate list when a governing word demands a case |
| Tags `multo` as an adverb with no case | ablative of measure invisible | match on form before the case filter |
| Tags `legendo` as a proper noun | gerund invisible | recognise the `-nd-` stem |
| Reads `veni` as a vocative proper noun | asyndeton hidden, apostrophe invented | comma-delimited members; reject vocatives that are also subjects |

The general principle: **a detector that depends on the parse should carry independent
evidence for the cases where the parse is weakest**, and should say in its caveat when it
has overridden the parser.

### Why constructions are allowed to overlap

Several detectors may fire on one word, and that is intended. *Carthago delenda est nobis*
yields both a dative of agent and a passive periphrastic — correctly, they are the same
construction seen from two angles. Where readings genuinely compete, showing both with
their confidences is more honest, and more useful, than silent arbitration.

Every detector reports the evidence that fired it, so a wrong detection is visibly wrong
rather than authoritative.

## Known limits

| Limit | Consequence |
|---|---|
| Morphological accuracy is ~91% (`la_core_web_lg`) | Roughly one token in eleven is misparsed. Never present a parse as settled. |
| LatinCy emits no `Degree` feature | Comparatives and superlatives are recovered from the form. |
| Gerunds arrive tagged as participles | `Tok.is_gerundive()` accepts both spellings of the analysis. |
| `advcl:abs` misses nominal ablative absolutes | A supplementary rule keys on role-nouns; confidence 0.7, with a caveat. |
| The bare ablative is ambiguous between a dozen uses | Means is the residual reading, at 0.6 and with an explicit caveat. |
| Subjective and objective genitives are formally identical | Both are reported; the reader decides from sense. |
| Dependency errors propagate into rules | Every construction carries evidence so the reader can audit it. |

`la_core_web_trf` roughly halves the morphological error rate (94.63% vs 90.78%) at the cost
of speed and size; it is the intended upgrade for interactive single-passage use.

## What is not built yet

The intertext and cultural-background layers are designed but not implemented. The research phase downloaded much of the data they need
(Perseus `canonical-latinLit`, the Latin Library and Tesserae corpora, Lewis & Short,
Morpheus, UD treebanks, Allen & Greenough). See [`../CHANGELOG.md`](../CHANGELOG.md) and the
project README for current status.

## Layout

```
server/enarratio/
    normalize.py       offset-preserving orthographic folding
    gate.py            language identification; anomaly reporting
    constructions.py   28 named constructions + the lexical classes that license them
    cases.py           42 uses of the oblique cases and the gerund/gerundive
    devices.py         17 literary figures, each with its rhetorical effect
    corpus.py          per-work specs for reading Perseus's many markup shapes
    identify.py        shingle index; passage identification and canonical text
    latinlibrary.py    optional breadth: ~600 more classical texts, no commentary
    commentary.py      Servius, Conington, Shorey, Merrill, Allen & Greenough
    scansion.py        hexameter, quantity and metre solved jointly
    pipeline.py        stage orchestration, morphology rendered into English
    app.py             FastAPI, localhost only
server/tests/          regression tests, each case verified against A&G by hand
web/src/
    api.ts             typed client
    App.tsx            reading interface
    App.css            styling, light and dark
```

Nothing leaves the machine. The server binds to localhost and the analysis is entirely local.

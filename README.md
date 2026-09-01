# Enarratio

A local-first Latin reading environment that explains everything.

> *enarratio poetarum* — in Roman grammatical education, the detailed exposition of a text:
> the grammarian's line-by-line unfolding of morphology, syntax, allusion and realia.
> That is exactly what this program does.

Paste a Latin excerpt. Enarratio first checks that it is well-formed Latin, then lets you
click any token to get a complete account of it **in this specific context**:

- **Morphology** — lemma, part of speech, and full parse (case, number, gender, person, tense, voice, mood, degree), with every *competing* reading shown and the reason this one wins.
- **Syntax** — the named construction the word participates in: ablative absolute, partitive genitive, dative with a special verb, accusative of respect (the "Greek accusative"), passive periphrastic with dative of agent, relative clause of characteristic, and so on — cross-referenced to Allen & Greenough.
- **Paradigm** — the complete declension or conjugation table the form belongs to.
- **Dictionary** — the full lexicon entry, not a gloss.
- **Metre** — scansion of the line, with elision, hiatus, synizesis, caesura and correption marked.
- **Commentary** — real editorial notes and footnotes when the passage is a known text.
- **Allusion** — intertextual echoes of earlier authors.
- **Background** — the cultural, historical, religious, legal and scientific context a Roman reader would have taken for granted.

## Status

**Early construction.** The research phase is complete and documented in [`docs/`](docs/);
implementation is in progress. See [CHANGELOG.md](CHANGELOG.md) for what has landed so far.

## Design principles

1. **Local-first.** Lexica, corpora, commentaries and models live on disk. The app works
   offline. Network calls are an enrichment layer whose results are cached permanently.
2. **Deterministic core, generative shell.** Morphology, syntax and scansion come from real
   parsers and real lexica — never from a language model's memory. A model may only put the
   deterministic analysis into prose, and every grammatical claim it makes is validated
   against the parser's output before it reaches the screen.
3. **Show the ambiguity.** Latin forms are systematically ambiguous. A tool that hides this
   teaches students to trust it instead of to read. Enarratio shows the competing analyses
   and argues for the winner.
4. **Cite everything.** Every grammatical claim points at a grammar section; every note
   points at its edition; every background claim points at its source.

## Repository layout

```
server/    Python analysis backend (FastAPI) — the pipeline and all linguistic logic
web/       Frontend reading interface
data/      Downloaded lexica, corpora, treebanks, models (git-ignored; fetched by script)
docs/      Architecture, the research dossier, and per-domain research notes
```

## Setup

Requires `uv` and Node. Python is pinned to 3.12 (the NLP stack has no 3.14 wheels yet).

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r server/requirements.txt
```

Full data-acquisition instructions live in [`docs/RESEARCH-DOSSIER.md`](docs/RESEARCH-DOSSIER.md).

## Licensing

The code in this repository is MIT-licensed. The linguistic **data** it downloads is not:
lexica, treebanks, corpora and commentaries each carry their own terms, which are recorded
per-resource in the research notes under [`docs/research/`](docs/research/). Nothing with
restrictive terms is vendored into this repository — it is fetched at setup time instead.

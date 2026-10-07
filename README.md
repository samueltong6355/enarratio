# Enarratio

A local-first Latin reading companion with evidence-based, explicitly uncertain analysis.

> *enarratio poetarum* — in Roman grammatical education, the detailed exposition of a text:
> the grammarian's line-by-line unfolding of morphology, syntax, allusion and realia.
> This is the project's ambition, not a claim that every interpretive problem is solved.

Paste a Latin excerpt. Enarratio checks whether it appears to be Latin, then lets you
click any token for a contextual analysis. It cannot certify grammatical correctness;
agreement warnings and parser confidence should be checked by the reader.

- **Morphology** — lemma, part of speech, and full parse (case, number, gender, person, tense, voice, mood, degree), with every *competing* reading shown and the reason this one wins.
- **Syntax** — the named construction the word participates in: ablative absolute, partitive genitive, dative with a special verb, accusative of respect (the "Greek accusative"), passive periphrastic with dative of agent, relative clause of characteristic, and so on — cross-referenced to Allen & Greenough.
- **Dictionary** — local entries, principal parts and competing morphological readings; complete generated paradigm tables are not implemented.
- **Metre** — hexameter candidates, elision and caesura; synizesis and non-hexameter metres remain unimplemented.
- **Commentary** — imported editorial notes for recognized texts, when optional local databases are installed.
- **Literary devices** — rule-based candidates with explanations and caveats, not proof of authorial intent.
- **Offline study** — save up to 20 analyses in your browser, export JSON, or print. New analysis requires the local server, not the internet.
- **Remaining research layers** — allusion search and comprehensive cultural background are not yet implemented.

## Status

**Working, partial.** Morphology, syntax, lexical lookup, hexameter, literary devices and
optional imported commentary are implemented. Eleven additional clause families and a
tentative directional dative are included. See [CHANGELOG.md](CHANGELOG.md) and
[docs/STATE.md](docs/STATE.md) for verification and remaining work, and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how it works and why.

```bash
./run.sh --setup  # once, online: install/repair dependencies and build the reader
./run.sh          # everyday use, offline: http://127.0.0.1:8000
```

What works today: paste a passage, and every token can be clicked for its full parse,
dictionary entry with principal parts, the syntactic construction it belongs to (with an
Allen & Greenough citation and the evidence for the identification), the competing readings
with their probabilities, and every form the word could possibly be.

## Design principles

1. **Local-first.** Lexica and models live on disk. Analysis makes no external requests.
   Optional corpora and commentaries are separately installed, not shipped in Git.
2. **Evidence-based core.** A statistical parser, local lexica and explicit rules supply
   the analysis. There is no generative-model explanation layer in the current app.
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
./run.sh --setup
./run.sh
```

Setup creates or repairs the environment. Normal startup serves both API and reader on
port 8000 and never installs packages. See [the startup and troubleshooting guide](docs/STARTUP.md)
for missing dependencies, occupied ports, optional data, and saved-reading limitations.
To run the tests:

```bash
PYTHONPATH=server .venv/bin/python -m pytest server/tests -q
```

## AP Latin benchmark

This is **not yet a complete AP course replacement**. The previous 897/897-unit report was
a legacy Caesar/Vergil corpus-presence check from a different data installation, not a
learning-quality assessment. The [current College Board course](https://apcentral.collegeboard.org/courses/ap-latin)
uses Pliny's *Letters* and revised *Aeneid* selections, plus teacher-selected texts.
`scripts/ap_coverage.py` is explicitly labeled as the legacy benchmark; current coverage
still needs a new manifest and verified commentary.

## Licensing

The code in this repository is MIT-licensed. The linguistic **data** it downloads is not:
lexica, treebanks, corpora and commentaries each carry their own terms, which are recorded
per-resource in the research notes under [`docs/research/`](docs/research/). Nothing with
restrictive terms is vendored into this repository — it is fetched at setup time instead.

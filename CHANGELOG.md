# Changelog

All notable changes to Enarratio are documented here. Each entry records what changed and
*why*, so the reasoning behind the build is recoverable later.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added — analysis core and reading interface

- **Working end-to-end path.** Paste Latin, get every token analysed and every syntactic
  construction named. `./run.sh` starts both servers.
- **28 construction detectors** (`server/enarratio/constructions.py`) — ablative absolute
  (participial and nominal), partitive genitive, dative with special verbs, dative of agent,
  passive periphrastic, Greek accusative, ablative with the five deponents, ablative of
  comparison, dative of possession, dative with adjectives, indirect statement, purpose and
  result clauses, *cum*-clauses, indirect question, clauses of fearing, relative clause of
  characteristic, gerund, supine, independent subjunctives, and more. Each reports the
  evidence that fired it, a confidence, an Allen & Greenough citation, and a translation hint.
- **Language gate** (`gate.py`) combining Whitaker analysability with `lingua`.
- **Analysis pipeline** (`pipeline.py`) rendering morphology as a grammar book would recite
  it — "perfect passive participle feminine ablative plural", not `Case=Abl|Gender=Fem`.
- **Reading interface** (`web/`): click any token for its parse, dictionary entry with
  principal parts, case force, constructions in context, competing readings with
  probabilities, and every form the word could possibly be.
- **27 regression tests**, each case verified by hand against Allen & Greenough.
- `latincy-lexicon` adopted for Whitaker's WORDS and Lewis & Short as spaCy components —
  the complete candidate-analysis set, dictionary entries and paradigm generation.

### Changed — decisions forced by measurement

- **Grammaticality is no longer gated, contrary to the original specification.** Agreement
  checking flags 5 of 6 modifiers in *Aeneid* 1.1–3 and 5 of 12 in Horace *C.* 1.5, because
  hyperbaton separates adjective from noun and the parser reattaches them wrongly — worse
  than deliberately broken student Latin scores. A literal "reject unless grammatically
  sound" gate would refuse the *Aeneid*. Only language identity is gated; irregularities are
  reported on the token as observations that never block analysis.

### Fixed

- Corrected a **wrong finding** published in the previous commit: `regis` and `bella` are in
  the bundled lemma table after all. The probe had queried it through spaCy's string-hash
  interface instead of reading the raw JSON, and the table is u-normalised. The conclusion
  (unusable as an OOV gate) survives on better evidence — it omits `est`, `et`, `qui` and
  `arma`, so Vergil scores 45% against Lorem ipsum's 70%.
- LatinCy emits no `Degree` feature, so comparatives are recovered from the form.
- Gerunds arrive tagged `VerbForm=Part|Voice=Pass|Aspect=Prosp`, not `Ger`.
- A dative in a copular clause hangs off the predicate, not off *sum*.
- *dicit Caesarem venire* reported `Caesarem` as a destination; place-to-which now requires
  a verb of motion and the NER `LOC` label.
- *Italiam … profugus* (*Aen.* 1.2) reported a Greek accusative; without a body-part noun the
  rule now requires a participial head.
- Explanations no longer fabricate English inflections ("gero-ed"); they name the dictionary
  sense instead.

### Added — scaffold
- Project scaffold: repository layout, README stating the design principles, MIT licence for
  the code, and a `.gitignore` that keeps downloaded linguistic data out of version control
  (it is large and separately licensed).
- Python 3.12 virtual environment pinned via `uv`. The system Python is 3.14, which is ahead
  of the Latin NLP stack — spaCy, Stanza and the LatinCy pipelines have no 3.14 wheels yet.
- Research phase: an eleven-domain survey of the digital-classics landscape, each domain
  independently fact-checked against live sources (PyPI, the GitHub API, HuggingFace, and
  HTTP liveness checks) to eliminate invented package names and dead links. Notes land in
  `docs/research/`, consolidated into `docs/RESEARCH-DOSSIER.md`.

# State of play

**Updated:** 2026-09-02, after commentary and passage identification landed.
**Read this first; update it before you stop.** `./scripts/status.sh` prints a live readout.

---

## Where we are in one paragraph

The analysis core is built, tested and working end to end: paste Latin, click any word, get
its full parse, dictionary entry, the syntactic construction it belongs to with an Allen &
Greenough citation, competing readings with probabilities, and every form it could possibly
be. A scansion engine now scans hexameter correctly (6 of 7 test lines, the seventh needing
synizesis). Two research sweeps were killed by the usage ceiling but their findings were
recovered from disk, and six dossiers in `docs/research/` now say precisely how to build the
remaining layers. **The next big win is commentary**, because Servius and Conington turn out
to be sitting on local disk already keyed by `(book, line)`.

---

## Built and verified

| Layer | Status | How it was verified |
|---|---|---|
| Orthographic normalisation | done | offset-preserving; round-trip tested |
| Parsing (LatinCy `la_core_web_lg`) | done | probed empirically; limits documented |
| Candidate enumeration (Whitaker's WORDS) | done | `regis` → *rēx* ×4, *regō*, *regius* |
| Language gate | done | genuine Latin ≥86% analysable vs ≤58% for everything else |
| Construction detection | 28 rules | 27 passing regression tests, each hand-checked against A&G |
| Reading interface | done | driven with a real browser; no console errors |
| **Scansion (hexameter)** | done, wired in | 6/7 lines correct incl. *Aen.* 1.1, 1.3, 1.5, *Ecl.* 1.1; verified in browser |
| **Passage identification** | **done, wired in** | exact, macronised and `VIRVMQVE` orthography all resolve to *Aen.* 1.1; non-Vergil correctly declined |
| **Commentary (Servius, Conington)** | **done, wired in** | 18,611 notes ingested; Servius on *arma* renders in the browser |

Everything above is reachable from the interface. Verse is detected rather than declared:
each line is offered to the hexameter fitter and the passage counts as verse if a majority
fit, which prose never does.

---

## Next actions

1. **Extend the corpus beyond Vergil.** Identification and commentary work, but only for
   the *Aeneid*, *Eclogues* and *Georgics*, because that is where line-keyed commentary
   exists. Indexing Perseus `canonical-latinLit` (1,078 TEI files, already downloaded) would
   let Caesar, Cicero, Ovid and Horace be identified even where no commentary follows.
   The index cost is trivial — all of Vergil is 83k tokens.
2. **The eleven missing clause detectors.** We cover ~12% of A&G's ~230 named constructions,
   and the gap is almost entirely the subordinate-clause and mood system — where students
   actually get stuck. All eleven are closed-conjunction-list + mood rules, the same shape as
   the detectors that already work: `quin`/`quominus` (558–9), substantive purpose after
   verbs of commanding (563), substantive result (568–71), causal `quod`/`quia`/`quoniam`
   (540), concessive `quamquam`/`quamvis`/`licet` (527), proviso `dum`/`modo` (528),
   `antequam`/`priusquam` (551), `dum`/`donec`/`quoad` (553–6), conditional protasis/apodosis
   (513–17), relative clause of purpose (531.2), noun-clause `quod` of fact (572). See
   `docs/research/syntax-taxonomy.md`.
3. **Allusion.** Tesserae bigram index over the local `.tess` corpus with Tesserae's published
   scoring formula. `knauer.json` gives verified Vergil↔Homer pairs as ground truth.
4. **Cultural background.** Hardest, least settled. Note the negative finding: the Perseus
   hopper dump does **not** contain Smith's dictionaries — the empty directories are a
   deliberate rights carve-out, not a failed download.

---

## Settled decisions — do not relitigate

- **Grammaticality is never gated.** Measured: agreement checking flags 5 of 6 modifiers in
  *Aen.* 1.1–3 and 5 of 12 in Horace *C.* 1.5, worse than deliberately broken student Latin
  scores. A literal reading of the brief would refuse the *Aeneid*. Only language identity is
  gated. (`empirical-probe-latincy.md` Finding 8.)
- **LatinCy ranks, Whitaker enumerates.** A statistical model says what is likely; a rule
  engine says what is possible. The reader needs the whole space plus an argued ranking.
- **Constructions may overlap.** Two competing readings with confidences beat silent
  arbitration.
- **Quantity and metre are solved jointly, not sequentially.** Independently confirmed by the
  research: this is exactly how Winge's `latin-macronizer` works.
- **`data/` is gitignored.** Large, separately licensed. Fetched at setup, never vendored.

---

## Known bugs and limitations

- `scripts/build-data.sh` rebuilds `commentary.db` and `passages.db` from the Perseus dump,
  but `morpheus-quantities.db` must still be copied by hand from Winge's latin-macronizer;
  without it scansion degrades to position-and-diphthong evidence.
- Commentary and identification cover **Vergil only**. Anything else analyses fully but
  receives no citation and no notes.
- **Synizesis is not implemented**, so *Aen.* 1.2 (`Laviniaque` → *Lāvīnjă-que*) does not
  scan. Only hexameter is implemented; elegiac couplet, hendecasyllable and the lyric
  strophes are not.
- Morphological accuracy is ~91% (`la_core_web_lg`). Roughly one token in eleven is
  misparsed, and rules built on the parse inherit that. `la_core_web_trf` roughly halves the
  error rate (94.63% vs 90.78%) and is the intended upgrade for interactive use.
- LatinCy emits no `Degree` feature; comparatives are recovered from the form.
- Gerunds arrive tagged `VerbForm=Part|Voice=Pass|Aspect=Prosp`, not `Ger`.
- Nominal ablative absolutes are detected by a role-noun list at confidence 0.7, because
  `advcl:abs` misses them.

---

## Scars — mistakes already made, don't repeat them

- **A published finding was wrong.** I reported `regis` as missing from LatinCy's lemma table;
  the bug was in my probe (spaCy's hash-keyed interface, and the table is u-normalised).
  Corrected in place. *Read raw data files rather than trusting a convenience API.*
- **Two research sweeps died on the usage ceiling**, 1.36M subagent tokens total. The first
  returned nothing at all. The second recovered everything, because agents were told to write
  notes to disk incrementally. *Never hold research in context until the end.*
- **Scansion had four bugs found only by testing against real verse**: `qu` counted as a
  vowel (every line with `qui` came out two syllables long), `v` folded to a vowel, vowel
  indices misaligned between database and syllabifier, and elided syllables not making
  position (`multum ille` — the `-um` elides but the `t` still closes `mul-`). *Invented
  examples would have caught none of these.*

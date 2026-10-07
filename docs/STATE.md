# State of play

**Updated:** 2026-10-07, offline startup and lightweight feature revision.
**Read this first; update it before you stop.** `./scripts/status.sh` prints a live readout.

## Current checkpoint — supersedes historical claims below

- Working checkout: `/Users/samueltong/enarratio`, linked to `samueltong6355/enarratio`.
  The downloaded Documents copy was identical on arrival and has not been modified.
- Start with `./run.sh`; use `--setup` only for online dependency repair/installation.
  The built reader and API share port 8000. Use `--port` if an old server occupies it.
  See [STARTUP.md](STARTUP.md). New analyses need a running local server.
- Added model warm-up/error reporting, optional-data diagnostics, corrupt-enrichment
  isolation, configurable data directory, browser-saved readings, JSON export and print.
- Added eleven clause families and tentative directional dative. The construction API
  now includes the case and clause catalogues. Source notes and limits:
  [research/lightweight-clauses.md](research/lightweight-clauses.md).
- Fixed offline hexameter preference when absent quantities leave multiple fits. All
  alternatives remain counted; fifth-foot dactyl preference is disclosed.
- This fresh checkout has **no optional research databases**. Historical corpus counts
  below describe a former installation, not assets shipped with the repository.
- The historical AP benchmark is NOT current coverage. Current AP uses Pliny and revised
  Vergil selections; README and benchmark now state this explicitly.
- Git history backup before removing Claude co-author trailers:
  `/Users/samueltong/enarratio-before-credit-cleanup-20261007.bundle` (verified).
  Samuel Tong remains the author and committer of historical commits. The history rewrite
  changes commit IDs; other clones must reconcile with the rewritten main before pushing.

### Resume here

1. Read this checkpoint; run `git status`, `./run.sh --check`, and the tests before edits.
2. Optional corpus-dependent tests skip on this checkout. Restore/import independently
   licensed data before claiming passage/commentary coverage; do not invent notes.
3. Resolve Cicero Select Orations heading-to-work mapping against real source XML.
4. Build a current Pliny/Vergil AP manifest and verify commentary and teaching coverage.
5. Remaining substantial work: allusion index, cultural database, full paradigms,
   additional metres and synizesis. Current rules remain partial, not all Latin syntax.

### Verification for this checkpoint

- `PYTHONPATH=server .venv/bin/python -m pytest server/tests -q`: **133 passed,
  28 skipped** (optional corpus databases absent). One upstream Starlette/httpx
  deprecation warning; no test failures.
- `npm --prefix web run build` and `npm --prefix web run lint`: passed.
- `node web/scripts/smoke.mjs http://127.0.0.1:8001`: passed with external requests
  blocked; checked live analysis, new clause display, browser save/reload, JSON download,
  disconnected API error, preserved saved analysis, and zero browser page errors.
- `./run.sh --check`: passed. Occupied-port startup returns an actionable error without
  killing another server. `git diff --check`: passed.
- Test server was started on port 8001 because port 8000 was occupied by a pre-existing
  process; that existing process was left untouched.

## Historical record (September installation)

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
| **Passage identification** | done, wired in | 15 works, 376k tokens; macronised and `VIRVMQVE` orthography both resolve; unindexed authors correctly declined |
| **Commentary** | done, wired in | 28,747 notes from 5 commentators; Allen & Greenough's Caesar notes are word-level |
| **Literary figures** | done, wired in | 17 figures, each explaining its *effect* |
| **Case usage** | **done, wired in** | 42 uses of gen./dat./acc./abl./gerund; 70 constructions in all; 128 tests |
| Legacy Caesar/Vergil corpus | historical presence check only | 897/897 units in the former installation; not current AP or comprehensive teaching coverage |

Everything above is reachable from the interface. Verse is detected rather than declared:
each line is offered to the hexameter fitter and the passage counts as verse if a majority
fit, which prose never does.

---

## Next actions

1. **Cicero commentary.** The *texts* are now indexed (*In Catilinam*, *Philippics*, *De
   Lege Agraria*) and cite correctly, but Allen & Greenough's *Select Orations* is not
   ingested. Its `<div1 type="speech">` keys are a mix of abbreviations (`S. Rosc.`, `Man.`,
   `Arch.`) and bare numbers that **repeat across different orations** (`1` appears twice,
   `2` three times), so there is no unambiguous mapping to a work. Resolving it means
   reading each speech's `<head>` and matching by title. Until then a wrong mapping would
   file a *Pro Milone* note under *In Catilinam*, which is worse than no note at all.
2. **Eleven clause families now implemented (October revision).** The original backlog was:
   We cover ~12% of A&G's ~230 named constructions,
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
- Identification covers fifteen Perseus works with real citations, plus ~600 Latin Library
  texts (Livy, Tacitus, Sallust, Juvenal, Lucretius, Seneca, Martial, Plautus and the rest
  of the classical canon). **The Latin Library carries no commentary of any kind** — it is a
  bare text archive — so those works get a citation but no notes.
- Latin Library verse citations count lines from the top of the file, since the archive
  marks no line numbers. Accurate for a complete book, but reported at lower confidence
  than the Perseus citations, which come from real `<l n=…>` anchors.
- The medieval and neo-Latin two-thirds of The Latin Library is deliberately not indexed:
  13.7M words would cost several GB for material a student is rarely translating.
- Commentary for AP Caesar *BG* 4.24–36 covers 10 of 13 chapters; the other three have no
  Allen & Greenough note.
- Metaphor, oxymoron, transferred epithet and true hendiadys are **deliberately not
  detected**: they need semantics a dependency parse cannot supply, and guessing them
  structurally would produce confident nonsense.
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

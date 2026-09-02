# Intertextuality and Allusion — research notes

*Research file for Enarratio. Written incrementally; sections appended as verified.*
*Date: 2026-09-01. All claims marked VERIFIED were checked against local data or a live URL;
claims marked RECALL are from memory and should be re-checked before implementation.*

## Most actionable finding (read this first)

**Build the intertext engine as a Tesserae-style bigram (two-lemma) index over the local
Tesserae `.tess` corpus, scored with Tesserae's published formula
`score = ln( (1/f_target(a) + 1/f_target(b) + 1/f_source(a) + 1/f_source(b)) / (d_target + d_source) )`,
and *do not* ship raw ranked lists to the student.** The formula is the whole trick: it is a
single-line computation over two things you already have (a lemma-frequency table and word
positions), it needs no training, it runs in milliseconds against a pre-built inverted index,
and it is the only allusion-detection method in Classics with a published human-annotated
benchmark (the Lucan–Vergil "Tesserae benchmark", Forstall et al.). Everything else — Knauer,
the commentaries, the LLM — is a *curation layer* on top of that recall engine. Concretely:
the local `lat_text_tesserae/texts/*.tess` corpus (784 files, already in Tesserae's own
`<ref>\ttext` line format, so no parsing work at all) plus a lemma table derived from
`macrons.db` (812k Morpheus form→lemma rows) is everything needed to build the index offline.
The single highest-leverage design decision on the *presentation* side: an allusion must be
shown as a **side-by-side diff with the shared lemmata highlighted and the student asked what
changed**, never as a prose assertion that "X alludes to Y" — the pedagogy lives in the
*delta*, not in the identification.

---

## 1. knauer.json — structure and coverage (VERIFIED, inspected locally)

Path: `/private/tmp/claude-501/-Users-samueltong/c1f16a5b-019c-4034-b903-a79279f6a3e8/scratchpad/knauer.json`
Size: 134,300 bytes. Format: a single JSON **array** of flat objects (not JSONL, not nested).

Record schema — exactly 9 keys, all present on every record, all strings:

```json
{
  "source_ref":      "hom. il. 5.892",
  "target_ref":      "verg. aen. 1.4",
  "source_work":     "homer.iliad.part.5",
  "target_work":     "vergil.aeneid.part.1",
  "source_language": "grc",
  "target_language": "la",
  "source_text":     "μένος ... Ἥρης",
  "target_text":     "Iunonis ob iram",
  "authority":       "Knauer"
}
```

### Measured coverage

| property | value |
|---|---|
| total records | **412** |
| `authority` | `"Knauer"` for all 412 |
| `source_language` | `grc` × 412 |
| `target_language` | `la` × 412 |
| distinct `target_work` | **1** — `vergil.aeneid.part.1` only |
| distinct `source_work` | 24 — `homer.iliad.part.1` … `part.24` (**Iliad only; no Odyssey**) |
| target line range | Aen. 1.1 – 1.754 |
| distinct target lines cited | **226 of 756** = **29.9%** of Aeneid 1 |
| mean pairs per cited line | 1.82 |
| max pairs on one line | 7 (Aen. 1.65, 1.97, 1.212) |
| records with **empty** `source_text`/`target_text` | **156 (37.9%)** — the two fields are empty together, never one alone |

Source-book distribution is not uniform: Iliad 1, 2 and 7 supply 33 pairs each; Iliad 17
supplies only 2. That reflects Knauer's own book-by-book density, not a sampling artefact.

### Implications for Enarratio

1. **This is a book-1-only demo slice, not Knauer's full index.** Knauer's *Die Aeneis und
   Homer* (1964) contains the complete Aeneid↔Homer concordance for all 12 books and both
   Homeric epics. What is on disk covers ~1/12 of the Aeneid and half the Homeric corpus.
   Do not advertise "Knauer coverage" to a student reading Aeneid 4.
2. **The 38% of records with empty text fields are still usable as citations** — the refs are
   intact, so the passage text can be re-fetched from the corpus (`vergil.aeneid.part.1.tess`
   locally for the Latin; Greek would need a Perseus/First1KGreek fetch). Build a resolution
   step that fills `source_text`/`target_text` from corpus lookups rather than treating an
   empty string as "no parallel".
3. **`source_text`/`target_text` use `...` and `…` as elision markers** — note the file mixes
   ASCII `...` and U+2026 `…` (both observed, e.g. `"Musa … mihi memora"` vs
   `"μένος ... Ἥρης"`). Normalise both to a single ellipsis token before display or matching.
4. **Refs are Tesserae-style, and they match the local corpus exactly.** `verg. aen. 1.4` is
   literally the ref string in `lat_text_tesserae/texts/vergil.aeneid.part.1.tess`. So a join
   from a Knauer record to the Latin line is a plain string lookup, zero normalisation:
   ```
   grep -F '<verg. aen. 1.4>' lat_text_tesserae/texts/vergil.aeneid.part.1.tess
   ```
5. **No ranged refs.** Checked for `-`, `,`, `ff` in either ref field: zero hits. Every ref is
   a single `author. work. book.line` point. Parsing is a fixed regex:
   `^(?P<auth>\w+)\.\s*(?P<work>\w+)\.\s*(?P<book>\d+)\.(?P<line>\d+)$`.
6. **Directionality is encoded and correct**: source = the alluded-to (Homer, earlier),
   target = the alluding (Vergil, later). Preserve that; a student needs to know which way the
   arrow points.
7. Recommended storage: a SQLite table `attested_parallel(target_work, target_book,
   target_line, source_ref, source_text, target_text, authority)` with an index on
   `(target_work, target_book, target_line)`. Lookup for a displayed line is then O(log n),
   and the `authority` column lets you add other indices (Pease on Aen. 4, Nisbet–Hubbard on
   Horace) under the same schema.

## 2. The local Tesserae corpus (VERIFIED, inspected locally)

Path: `.../scratchpad/lat_text_tesserae/` — the CLTK repackaging of the Tesserae Project texts.
- 784 files under `texts/`, all `.tess`.
- Licence: **UB Public License 1.0** (University at Buffalo), stated in `README.md` and
  `LICENSE.md`, full text at <https://cse.buffalo.edu/sneps/ubpl.pdf>. This is an
  MPL-1.1-derived licence: it permits redistribution and modification but is *not* CC0 —
  attribution and licence propagation for the corpus files are required. Upstream:
  <https://github.com/cltk/latin_text_tesserae>; original texts at
  <https://github.com/tesserae/tesserae/tree/master/texts>.
- File format is trivially parseable and **identical to Knauer's ref convention**:
  `<ref>\t<text>\n`, one unit per line. Verse texts use one line per verse
  (`<verg. aen. 1.1>\tArma virumque cano...`); prose texts use one paragraph/section per line
  (`<cic. mur. 1> quae precatus a dis immortalibus sum, iudices, ...`).
  **Edge case: prose files separate ref and text with a single space, not a tab** — observed in
  `cicero.pro_murena.tess`. Parse with `^<([^>]+)>\s+(.*)$`, not `split('\t')`.
- Naming convention: `author.work[.part.N][.subtitle].tess`, e.g.
  `jerome.vulgate.part.54.2_corinthians.tess`, `ovid.fasti.part.1.tess`,
  `propertius.elegies.tess` (no part when the work is single-file).

---

## 3. The Tesserae matching algorithm, in implementable detail (VERIFIED against source)

Sources verified this session:
- **v3 Perl reference implementation**, `cgi-bin/read_table.pl` and
  `scripts/TessPerl/score/plugins/Default.pm` in <https://github.com/tesserae/tesserae>
  (fetched via `gh api repos/tesserae/tesserae/contents/<path>`). Licence: **UB Public
  License 1.0**, tri-licensed UBPL / GPL-2 / LGPL-2.1 — the file headers state that a
  recipient may use any one of the three, so **you can take the algorithm under GPL-2/LGPL-2.1
  if that suits Enarratio better.** (Verified: copyright block in `scripts/benchmark/knauer.pl`
  and every other script.)
- **v5 Python reimplementation**, `tesserae/matchers/sparse_encoding.py` and
  `tesserae/utils/stopwords.py` in <https://github.com/tesserae/tesserae-v5>.
- **The paper**: Coffee, Forstall, Buck, Roache, Jacobson, "Modeling the Scholars: Detecting
  Intertextuality through Enhanced Word-Level N-Gram Matching," *DSH* 30.4 (2015) 503–515.
  Preprint PDF:
  <https://tesserae.caset.buffalo.edu/blog/wp-content/uploads/2012/10/Modeling-the-Scholars-2013-11-6LLC-preprint.pdf>
  (I extracted the text with `pypdf`; the equation itself is a raster figure in the PDF, so
  the formula below is taken from the **code**, which is authoritative, and cross-checked
  against the paper's prose definition of the variables.)

### 3.1 The scoring formula (from `Default.pm::score` + `read_table.pl::score_default`)

```
score = ln( ( Σ_{i ∈ M_t} 1/f_t(form_i)  +  Σ_{j ∈ M_s} 1/f_s(form_j) ) / (d_t + d_s) )
```

where
- `M_t` = the set of **token positions in the target unit** that participated in the match
  (distinct positions, not distinct lemmata — a repeated lemma at two positions contributes
  twice); `M_s` likewise for the source unit.
- `f_t(w)` = frequency of the **inflected form** `w` **in the target text**, i.e.
  `count(w in target text) / total_words(target text)`. `f_s` likewise, in the source text.
  Two things are easy to get wrong here and both are verified in the code:
  1. **Frequency is looked up by inflected FORM even when matching is by LEMMA.** The Perl is
     literally `$freq = 1/$freq_target{$token_target[$token_id_target]{FORM}};`. Matching uses
     the lemma index; scoring uses form frequency. (Exception below.)
  2. **Frequency is per-text by default** (`--freq_basis text`), not corpus-wide, so the same
     word has different `f` in the source and in the target. `--freq_basis corpus` switches to
     corpus-wide stats, and *only then* does `stem_frequency()` kick in: for an ambiguous form
     it averages the corpus frequency over **all** candidate lemmata
     (`$average = Σ freq[stem_k] / n_stems`). Note this is a mean of frequencies, not of
     inverse frequencies — a common reimplementation bug.
- `d_t` = distance in the target unit, `d_s` = distance in the source unit, added together
  (`--dibasis freq`, the default). Definition per unit:
  - sort the matched positions by the frequency of their forms, ascending (rarest first);
  - take the **two rarest** matched positions `p0` and `p1`;
  - `d = |p0 − p1| + 1`.

  **Inclusive**, so adjacent matched words give `d = 2`, one intervening word gives `d = 3`.
  The v5 source explicitly flags this: *"Contrary to the v3 help documentation on `--dist` in
  `read_table.pl`, v3 behavior is that distance is inclusive of both matched words."* The
  prose docs saying "adjacent words have a distance of 1" are **wrong**; follow the code.
  Alternative `--dibasis span` uses first-to-last matched position instead of the two rarest.
- v3 `span`/`freq` count only tokens of `TYPE eq 'WORD'` between the endpoints, i.e.
  punctuation does not inflate the distance. The paper's footnote 6 notes that the *original*
  metric counted word and non-word tokens alike, so a published `--dist 50` corresponds to a
  modern word-only `--dist 23`. **If you replicate a published Tesserae search, halve the
  distance cap.**

Range: the paper says the output "generally falls between 2 and 10". A cutoff of 6 is where
the useful signal starts (see 3.5).

### 3.2 Stage 1 — what counts as a candidate parallel

From the matching loop in `read_table.pl` (lines ~676–830), a target unit *T* and source unit
*S* form a candidate parallel iff **all** of:

1. They share at least one non-stoplisted **feature key** (lemma, or exact form, or trigram,
   or synonym-set, depending on `--feature`). Matching is done through an inverted index
   `index_<feature>: key → [token_ids]`, and *every* occurrence in T is linked to *every*
   occurrence in S — the pairing is a cross-product, not a one-to-one alignment.
2. **T has ≥ 2 distinct matched token positions**, and **S has ≥ 2 distinct matched token
   positions.** (Two separate checks — a match where one target word aligns with two source
   words is rejected.)
3. **T has ≥ 2 distinct inflected FORMS among its matched tokens**, and S likewise. This is
   the anti-polyptoton guard: `arma … armis` matching `arma … arma` would otherwise score as
   a two-word parallel on a single lemma. Verified in code via the `%seen_forms` hashes.
4. `d_t + d_s ≤ max_dist` (v3 default 999 ≈ off; v5 default **10**, which is very tight —
   effectively "both pairs adjacent or nearly so").
5. `score ≥ cutoff` (v3 default 0; v5 default `min_score=6`).
6. Self-match guard: if source text == target text, skip `unit_id_source == unit_id_target`.

**Units** are either `line` (one verse) or `phrase` (sentence, or text delimited by `;` / `:`).
The paper's benchmark used **phrase**, because phrases are longer and catch more. For a
student-facing tool, `line` gives tighter, more quotable parallels for verse and `phrase`
is the only sane choice for prose.

**Features** available: `word` (exact form), `stem`/`lemmata` (dictionary headword — the
default for Latin, and what the paper used), `3gr` (character trigram, catches sound-play),
`syn` (lemma + synonym expansion), `g_l` (Greek→Latin cross-language via a bilingual lexicon —
this is how Tesserae does Homer↔Vergil; see `tesserae/matchers/greek_to_latin.py` and
`data/synonymy/g_l.csv`). For `3gr` only, each token's inverse frequency is **multiplied by
the number of distinct features it matched on**, so a word sharing three trigrams counts triple.

**Lemmatisation is unsupervised and deliberately permissive**: paper footnote 5 — "In cases
where an inflected form is ambiguous (e.g. Latin *bello* could mean 'war' or 'handsome'), it
is allowed to match on any of the possible lemmata." **Do not disambiguate before indexing.**
This is a recall-first design and it matters: the LatinCy tagger Enarratio already runs would
*reduce* recall if you indexed only its single best lemma. Index the full candidate lemma set
(which Enarratio already has, from Whitaker's WORDS enumeration + `macrons.db`), and let the
score and the human sort it out.

### 3.3 The stoplist (from `read_table.pl::load_stoplist` and v5 `create_stoplist`)

The stoplist is **not** a hand-curated function-word list by default. It is:
> rank all features in the *stoplist basis* by frequency, descending; take the top *N*.

- `--stop N`: default **10**. Yes, ten. Tesserae is deliberately shallow here.
- `--stbasis`: `corpus` (default), `target`, `source`, or `both`. For `both`, the two texts'
  frequency tables are **averaged** (`($f_target + $f_source)/2`, with a missing key treated
  as 0 before averaging — verified in code).
- A stoplisted key is skipped at index-lookup time (`next if grep { $_ eq $key } @stoplist`),
  so it can neither trigger a parallel nor contribute to the score.
- The paper's benchmark used `--stop 10 --stbasis both` on Aeneid + Bellum Civile 1, giving
  exactly: **et, qui, quis, in, hic, sum, tu, per, neque, fero**. (Note `fero` — a lexical verb
  that is stoplisted purely because it is frequent. That is the whole philosophy.)
- There is also an optional hand-made function-word list, `data/common/la.function`
  (**105 Latin function words**, fetched and verified: `quodsi, enimvero, penes, nedum,
  propter, …`), selected with `--stop function`. Use this if you want linguistic rather than
  statistical stopping.
- Separately, `texts/lsa/stoplist_250.txt` and `data/common/la.lsa.stop` exist for the LSA
  experiments — not part of the default pipeline.

**Recommendation for Enarratio**: N=10 corpus-basis is too permissive for a student tool,
because a student sees a *ranked list of ten*, not a spreadsheet of 23,617. Use N ≈ 50 on a
corpus basis, *plus* the `la.function` list, and rely on the score for the rest. Do not go much
above ~100: rare-but-real allusions turn on words like *arma*, *fata*, *umbra*, *sanguis*,
which are corpus-frequent but allusively loaded, and a big stoplist deletes exactly those.

### 3.4 Reference implementation sketch (offline, over the local corpus)

Index build (one pass, ~7.7M words — measured: `cat lat_text_tesserae/texts/*.tess | wc -lw`
gives **351,731 units / 7,748,160 words** across **784 files / 72 authors**):

```python
# 1. parse: every .tess line is  <ref>\t text   (prose files: <ref> SPACE text)
UNIT_RE = re.compile(r'^<([^>]+)>\s+(.*)$')

# 2. tokenise + normalise: lowercase; j->i, v->u, strip macrons and non-letters;
#    keep token order and position index within the unit.
# 3. lemmatise permissively: form -> SET of lemmas.
#    Source: macrons.db (Morpheus, 812k form|morphtag|lemma rows) -- one SELECT DISTINCT
#    lemma FROM entries WHERE form=? gives the candidate set for free.
#    Fall back to the form itself when unknown (this is what stem_frequency() does).
# 4. tables:
#    unit(unit_id, work_id, ref, text)
#    token(unit_id, pos, form)                     # pos = word index within unit
#    postings(lemma, unit_id, pos)                 # THE inverted index
#    form_freq(work_id, form, count), work_total(work_id, n_words)
#    lemma_df(lemma, n_units)                      # for the corpus-frequency stoplist
```

Query time, for a target unit `T` (the student's pasted line):

```python
def candidates(T_lemmas_by_pos, stoplist, max_dist=None, min_score=6.0):
    # a) gather postings for each non-stoplisted lemma of T, bucket by source unit
    hits = defaultdict(list)                     # unit_id -> [(t_pos, s_pos, lemma)]
    for t_pos, lemset in T_lemmas_by_pos.items():
        for lem in lemset - stoplist:
            for (s_unit, s_pos) in postings[lem]:
                hits[s_unit].append((t_pos, s_pos, lem))
    # b) filter: >=2 distinct t_pos AND >=2 distinct s_pos AND >=2 distinct forms each side
    # c) distance: d_t = |p0-p1|+1 over the two RAREST matched t_pos (rarity by form freq
    #    in the target text); d_s likewise; reject if d_t + d_s > max_dist
    # d) score = log(sum(1/f) over distinct matched positions both sides) - log(d_t + d_s)
```

**Edge cases you must handle (all of them bite):**

| case | correct behaviour |
|---|---|
| a matched form does not occur in the frequency table (OOV, or the pasted passage is not in the corpus) | you cannot use per-text frequency for a *pasted* target. Use **corpus-wide** frequency for the target side. This is `--freq_basis corpus`, a supported mode. Do not silently divide by zero. |
| ambiguous form → *n* lemmas | index under **all** *n*. For corpus-frequency scoring, average the *n* lemma frequencies (Tesserae's `stem_frequency`), not the inverse frequencies. |
| `d = 0` | happens when all matched positions collapse to one token. v5 returns 0 and the match is **discarded** (`if source_distance <= 0 ... continue`), because `log(x/0)` is undefined. Guard explicitly. |
| repeated lemma in one unit (polyptoton, anaphora) | the ≥2-distinct-**forms** rule (3.2.3) is what stops `arma…armis` from being a "match". Implement it; it is the single highest-precision filter in the whole pipeline. |
| the pasted passage *is* in the corpus | the top hit will be the passage itself. Suppress exact self-matches by ref, and warn the student that the passage was identified (that is a feature — it doubles as passage ID). |
| `.part.` files | Tesserae's `select_file_freq()` collapses `ovid.fasti.part.1` → `ovid.fasti` for frequency purposes: **frequency stats belong to the whole work, not the book.** Replicate this or short books will produce inflated scores. |
| prose vs verse units | the same `.tess` corpus mixes them. Never compare a 200-word Ciceronian period against a hexameter line without normalising, or the prose distance term will swamp the score. Either restrict the source corpus by genre, or use `phrase` units on both sides. |
| Greek sources | the Latin-only local corpus cannot produce Homer parallels. Use `g_l` cross-language matching (bilingual lexicon `data/synonymy/g_l.csv` in the Tesserae repo) or fall back to the curated Knauer table. For Enarratio, **the curated table is the right answer** — cross-language Tesserae is low-precision and hard to explain to a student. |

### 3.5 What accuracy to expect (measured numbers from the paper, Tables 2–4)

Benchmark: Vergil *Aeneid* (9,896 lines) vs Lucan *Bellum Civile* 1 (695 lines), phrase units,
lemma feature, stop 10 (basis both), max distance 50 (old metric), no score cutoff.
Ground truth: parallels from the commentaries of Heitland–Haskins 1887, Thompson–Bruère 1968,
Viansino 1995, Roche 2009.

- **Recall of scholarly parallels: 62%** with the stoplist and distance restrictions;
  **~72%** without them, at much worse precision.
- **23,617 candidate parallels** produced, of which a 5% stratified hand-ranked sample
  (n=1,194) graded: type 5 (high formal similarity, analogous context) **1%**; type 4 **3%**;
  type 3 **12%**; type 2 (ordinary language) **74%**; type 1 (algorithm error) **10%**.
- So **raw precision before scoring is 17% for "meaningful" (3–5) and 5% for "interpretable"
  (4–5)** (Table 3). Commentators, by comparison, run 86% / 41%. **The unscored output is
  unusable in front of a student.**
- Score distribution over the 23,617 (Table 2): score 10 → 1 parallel; 9 → 32; 8 → 342;
  7 → 1,721; 6 → 6,314; 5 → 10,004; 4 → 4,942; 3 → 259; 2 → 2.
- Score-vs-hand-rank (Table 4) is the number that should drive Enarratio's threshold:

  | auto score | n sampled | type 5 | type 4 | type 3 | type 2 | type 1 | P(type ≥ 4) |
  |---|---|---|---|---|---|---|---|
  | 10 | 1 | 0 | 1 | 0 | 0 | 0 | 100% |
  | 9 | 3 | 0 | 1 | 2 | 0 | 0 | 33% |
  | 8 | 19 | 2 | 3 | 6 | 8 | 0 | **26%** |
  | 7 | 86 | 5 | 10 | 20 | 44 | 7 | **17%** |
  | 6 | 316 | 0 | 20 | 79 | 184 | 33 | **6%** |
  | 5 | 507 | 0 | 4 | 31 | 412 | 60 | 0.8% |
  | 4 | 243 | 0 | 0 | 7 | 214 | 22 | 0% |
  | 3 | 17 | 0 | 0 | 0 | 15 | 2 | 0% |

  The paper's own recommendation: **investigate score ≥ 6 for "meaningful", ≥ 7 for
  "interpretable"**, based on F-measure.

**The blunt consequence for Enarratio: even at the best threshold, roughly 3 out of 4
top-scoring hits are not interpretable allusions.** A student-facing tool must therefore
either (a) show only curated parallels by default and put Tesserae hits behind an explicitly
labelled "possible echoes — most of these are coincidence" affordance, or (b) put an LLM
re-ranker between the recall engine and the student. Both, ideally. **Never present a raw
Tesserae hit in the same visual register as a Knauer parallel.**

Tesserae's 5-point hand-rank scale (Table 1) is worth adopting verbatim as Enarratio's own
internal confidence label, because it is the only published rubric for this:
- **5** — high formal similarity in analogous context. *(meaningful, interpretable)*
- **4** — moderate formal similarity in analogous context; **or** high formal similarity in
  moderately analogous context. *(meaningful, interpretable)*
- **3** — high/moderate formal similarity but with very common words; **or** high/moderate
  formal similarity with **no** analogous context; **or** moderate formal similarity with
  analogous context. *(meaningful, not interpretable)*
- **2** — very common words in a very common phrase; or matched words too far apart to form a
  phrase. *(not meaningful)*
- **1** — algorithm error; the words should not have matched.

## 4. Other allusion datasets (VERIFIED — fetched this session)

All of the following are in the `tesserae/tesserae` repo under `data/bench/` and
`scripts/benchmark/`, under the same UBPL-1.0 / GPL-2 / LGPL-2.1 tri-licence, and all are
plain TSV/CSV that you can vendor directly.

| file | rows | content |
|---|---|---|
| `data/bench/aeneid1-iliad.txt` | 290 | Knauer, Aen. 1 ↔ Iliad. Columns `TARGET_BOOK TARGET_LINE TARGET_TEXT SOURCE_BOOK SOURCE_LINE SOURCE_TEXT TYPE AUTH` (TAB). Covers **183** distinct Aen. 1 lines. `TYPE` is empty in every row. |
| `data/bench/aeneid1-iliad_include_uni_blank.txt` | 283 | Same schema; covers 134 distinct target lines; **entirely contained in the local `knauer.json`** (283/283 overlap, verified). |
| `data/bench/aeneid1-iliad_bigrams_only.txt` | 282 | Same + a `NOTES` column; header has a leading space in `TARGET_BOOK` (parser trap). |
| `data/bench/aeneid1-iliad_backup_first_94.txt` | 94 | Earlier partial pass. |
| **`data/bench/all_lucan.txt`** | **816** | **The Lucan benchmark. Lucan *BC* books 2–10 ↔ Vergil.** Columns `TARGET_BOOK TARGET_LINE TARGET_TEXT SOURCE_BOOK SOURCE_LINE SOURCE_TEXT AUTH`. Authorities: **Viansino 594, Fantham 223**. Target-book distribution: bk 2: 273, bk 3: 91, bk 4: 50, bk 5: 102, bk 6: 64, bk 7: 92, bk 8: 52, bk 9: 51, bk 10: 42. |
| `data/bench/bench3.csv` / `bench4.txt` | 3,411 | **The hand-ranked Lucan BC 1 ↔ Aeneid set.** Columns `BC_BOOK BC_LINE BC_TXT AEN_BOOK AEN_LINE AEN_TXT SCORE AUTH` — `SCORE` here is the **human 1–5 rank**, not the automatic score. This is the labelled training/eval set: 3,411 rows with human labels. **This is the most valuable file in the whole set for Enarratio**, because it lets you calibrate any re-ranker (including an LLM one) against human judgement. |
| `scripts/benchmark/synonyms_in_knauer.cache` | — | cached synonym expansion used in the Greek↔Latin Knauer replication. |
| `data/common/la.function` | 105 | hand-made Latin function-word stoplist. |
| `data/common/lexica/` | — | `DICTPAGE.RAW` (Whitaker), `elementary_lewis.xml`, `middle_liddell.xml`, `autenrieth.xml`. |
| `data/synonymy/g_l.csv` | — | Greek→Latin bilingual mapping used for cross-language matching. |

**Important provenance finding about the local `knauer.json`:** it is a **superset** of the
upstream Tesserae benchmark. Set-comparing (verified):
`knauer.json` (412 pairs) ⊇ `aeneid1-iliad_include_uni_blank.txt` (283/283), but only 161 of
the 290 pairs in `aeneid1-iliad.txt` appear in it, and **129 pairs in `knauer.json` appear in
none of the four upstream files.** So `knauer.json` came from a later or enriched upstream, and
the two upstream variants **disagree with each other on line references** — a live warning that
Knauer line numbers are not stable across editions. If you display a Homeric line number to a
student, display the *edition* too, and be prepared for an off-by-one or two against
Perseus's text.

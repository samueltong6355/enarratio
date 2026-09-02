# Scansion and Prosody — implementation notes for Enarratio

**Status:** research notes, written incrementally. Last verified 2026-09-01 against local data in
`/private/tmp/claude-501/-Users-samueltong/c1f16a5b-019c-4034-b903-a79279f6a3e8/scratchpad/`.

## Most actionable finding (read this first)

**Do not write a scanner from scratch, and do not treat "get vowel quantities" and "scan the
line" as two separate stages.** The single best-engineered open-source Latin scansion system is
Johan Winge's `latin-macronizer` (GPL-3.0), and it is *already cloned locally* at
`…/scratchpad/lm/` with its lexicon already built into `…/scratchpad/macrons.db` (812,318 Morpheus
rows, verified). Its key architectural insight — which any reimplementation must copy — is that
lexical quantity and metre are solved **jointly**, not sequentially: every word is expanded into a
*set* of candidate syllable-weight strings (each with a penalty for how marked its assumptions
are: muta-cum-liquida, diaeresis, synizesis, hiatus…), the metre is expressed as a **finite-state
automaton over `L`/`S` syllables**, and the line is scanned by a recursive minimum-penalty search
over the product of the two. That falls straight out of `scansion.py:possiblescans` +
`scansion.py:scanverse` + `meters.py`. This design is exactly what a *teaching* tool needs, because
the penalty on the winning path is a machine-readable statement of *which prosodic licence the
poet took* — "this line only scans if you allow muta cum liquida in `patris`" is precisely the
commentary note a student wants. Enarratio should reuse this engine (GPL-3.0 is compatible with a
local-first app; see licensing section) and add on top of it: caesura/diaeresis detection, ictus
display, and per-syllable explanation strings, none of which the macronizer provides.

---

## 1. `macrons.db` — format, coverage, and the exact gotchas

Verified by direct query.

### Schema

```sql
CREATE TABLE morpheus(
    id INTEGER PRIMARY KEY,
    wordform TEXT NOT NULL,   -- lowercase surface form
    morphtag TEXT,            -- 9-char Perseus/AGDT positional tag
    lemma TEXT,               -- Morpheus lemma, may carry a homograph digit (e.g. "litus3")
    accented TEXT,            -- quantity-marked form: _ = long, ^ = short, + = diaeresis marker
    UNIQUE(wordform, morphtag, lemma, accented)
);
CREATE INDEX morpheus_wordform_index ON morpheus (wordform);
```

`select count(*) from morpheus` → **812,318** rows.

### The `accented` mini-language (character inventory verified by full scan)

| mark | count | meaning |
|---|---|---|
| `_` | 1,028,563 | preceding vowel is **long by nature** |
| `^` | 629,708 | preceding vowel is **short by nature** |
| `+` | 235 | preceding vowel is a **diaeresis**: the two vowels do *not* form a diphthong (`A^e+llo_` = Aëllō, `co^e+rci^ti^o_` = coërcitiō) |
| (none) | — | quantity **not determined / not relevant** — see below |

**Critical gotcha #1 — unmarked ≠ short.** `arma` (noun) is stored as `arma`: neither `a` carries a
mark. The first is unmarked because the syllable `ar-` is heavy *by position* regardless, so
Morpheus never had to decide; the second is unmarked because Morpheus's convention leaves the
short final unmarked. Winge's `possiblescans` handles this by the rule **`if "_" in segment: heavy,
else treat as light and let positional lengthening decide`** — i.e. `^` and *unmarked* are
operationally identical, and only `_` is load-bearing. Any reimplementation must not read unmarked
as "unknown, bail out". Contrast `arma_` = `armā`, the imperative of `armō` — this is the *whole
reason* the lookup must be tag-aware and not lemma-blind.

**Critical gotcha #2 — `wordform` carries both orthographies, `accented` only one.** The
`wordform` column is indexed under *both* `u/v` and `i/j` spellings (`venit` → 2 rows, `uenit` → 2
rows; `iam` → 1, `jam` → 1), so surface lookup is orthography-tolerant and you should **not**
normalise before querying. But the `accented` column is written in the `v`/`j` orthography
(150,862 `v`, 23,863 `j`), which matters because `j` is what triggers the
double-consonant/`maius`-lengthening rule in `possiblescans`.

**Critical gotcha #3 — enclitics are inconsistently present.** `que` exists as a row with NULL
morphtag/lemma/accented (`que|||`); only 579 wordforms end in `que` at all, and the accented value
of the ones that do *excludes* the enclitic (`virumque|n-p---mg-|vir|vi^rum`). Meanwhile common
verse forms `armaque`, `litoraque`, `Laviniaque`, `studiisque` are **absent**. So the pipeline must
split `-que / -ve / -ne` itself before lookup (this is what `Tokenization.splittokens` does) and
re-attach `que` as a separately-scanned light syllable.

### Verified: coverage of Aeneid 1.1–10

Test performed (`enar_scan.py`, see §5) against the Perseus TEI text
`canonical-latinLit/data/phi0690/phi003/phi0690.phi003.perseus-lat2.xml` (verified identical to the
Latin Library copy `lat_text_latin_library/vergil/aen1.txt`):

```
tokens=68   direct hits=64   found after enclitic split=4   missing=0   coverage = 100.0%
```

The four that needed splitting: `Laviniaque`, `Albanique`, `inferretque`, `quidve`. Nothing in the
first ten lines of the *Aeneid* is unknown to `macrons.db`. **Lexical coverage is not the
bottleneck for canonical hexameter verse — disambiguation is.**

Ambiguity is the real cost. Example from line 1, tag-blind candidate sets:

| word | candidate `accented` values |
|---|---|
| `Arma` | `arma`, `arma_` (noun vs. imperative of `armō`) |
| `cano` | `ca_no_`, `ca^no_` (`cānō` abl. of `cānus` vs. `canō` "I sing") |
| `Troiae` | `Tro_iae`, `Trojae` |
| `primus` | `pri_mus`, `Pri_mus` |
| `oris` | `O^ri_s`, `o_ri_s`, `o_ris` (`ōs/ōris` vs. `ōra/ōrīs` vs. proper name) |

### **BUG FOUND — Morpheus silently swallows enclitics, and the cache DB persists the damage**

This one will bite anybody who reuses `macrons.db`, and it is verified end-to-end.

`macrons.db` is **not** a static asset. It is a *mutable cache*: `Wordlist.crunchwords`
(`lm/latin_macronizer/wordlist.py`) shells out to the Morpheus `cruncher` binary for any word not
already present and `INSERT`s the result. The shipped seed file `macrons.txt` has 812,588 lines;
the DB has 812,318 rows, and rows **812308–812318 are live-crunch additions from a previous
session** (`virumque`×8, `laviniaque`, `que`, `violentaque` — i.e. somebody ran the macronizer on
*Aeneid* 1.1–2 on this machine).

Run the cruncher directly and the cause is plain:

```
$ MORPHLIB=…/morpheus/stemlib …/morpheus/bin/cruncher -L <<< "virumque"
virumque
<NL>N vi^rum,vir  masc acc sg   0_i</NL><NL>N vi^rum,vir  masc gen pl  poetic  0_i</NL>…
```

**Morpheus strips `-que` and returns the accented form of the *stem only*.** `crunchwords` stores
that verbatim, so the DB now claims `virumque` → `vi^rum`. And the enclitic splitter is then
disarmed, because `Tokenization.splittokens` only splits a word that is in
`wordlist.unknownwords` — and `virumque` is now "known". Net effect: the `-que` syllable vanishes.

Measured consequence: my scanner produced `DSSSDS` for *Aeneid* 1.1 (14 syllables) instead of the
correct `DDSSDS` (15). Confirmed `virumque` is the **only** wordform in this DB whose stripped
`accented` is shorter than its `wordform` — but that is luck, not safety: `armaque` crunches to
`arma`/`arma_` too, and would be cached wrong the moment it is seen.

**Fix Enarratio must apply (verified to work):**

1. Reject any lexicon row whose `accented`, stripped of `_ ^ +`, is materially shorter than the
   surface `wordform`. One-char slack tolerates `x`→`cs`-style rewrites; be stricter if you can.
2. Do **not** gate enclitic splitting on "the whole form is unknown". *Always* additionally try
   `stem + enclitic` and let the metre arbitrate:

   ```python
   for enc in ("que", "ve", "ne"):
       if lc.endswith(enc) and len(lc) > len(enc) + 1:
           for a in accents_for(lc[:-len(enc)]):
               candidates.append(a + enc)   # "que" needs no marks: qu = 1 consonant, e short
   ```
   This is strictly better than a hand-maintained stoplist of genuine words in `-que/-ne/-ve`
   (`atque, neque, quoque, itaque, denique, undique, plerumque, quisque, uterque, namque, usque,
   bene, sine, omne, paene, mane, breve, salve, ave, …`), because ambiguous cases
   (`quoque` = `quŏque` vs. `quōque`) are resolved by the metre rather than by a lexicographer's
   guess. Append `que` to the *accented* string, not the surface one, so `segmentaccented` sees it.

With both fixes, all ten lines scan correctly:

```
  1 DDSSDS  Arma virumque cano, Troiae qui primus ab oris
  2 DSDSDT  Italiam, fato profugus, Laviniaque venit
  3 DSSSDS  litora, multum ille et terris iactatus et alto
  4 DSDSDS  vi superum saevae memorem Iunonis ob iram;
  5 DSSSDS  multa quoque et bello passus, dum conderet urbem,
  6 SDDDDS  inferretque deos Latio, genus unde Latinum,
  7 SDSSDS  Albanique patres, atque altae moenia Romae.
  8 DSDSDS  Musa, mihi causas memora, quo numine laeso,
  9 DSDSDS  quidve dolens, regina deum tot volvere casus
 10 SDDDDS  insignem pietate virum, tot adire labores
```
(hand-checked against the standard scansions; `T` = final-foot trochee, i.e. `vēnĭt`.)

**Operational recommendation:** ship `macrons.db` **read-only** and route Morpheus crunching into a
*separate* writable overlay table, so a bad crunch can be invalidated without rebuilding 812k rows.

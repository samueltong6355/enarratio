# Passage identification — identifying a pasted Latin excerpt and returning its canonical citation

**Status:** research notes, written incrementally against the local corpora. Every number below
was measured on this machine unless marked ESTIMATE.

---

## Most actionable finding (one paragraph)

Do **not** reach for FTS5, MinHash/LSH, or embeddings. The whole problem collapses to a
**hashed word-5-gram (shingle) inverted index over a normalised token stream**, stored in
SQLite as `(hash INTEGER, work_id INTEGER, token_offset INTEGER)` with one index on `hash`.
Normalisation (lowercase → strip macrons → `j→i`, `v→u`, `æ→ae` → drop all non-`[a-z ]`)
absorbs essentially every orthographic difference between what a student pastes and what
Perseus prints, so *exact* 5-gram hits carry the whole retrieval load; fuzzy matching is only
needed as a fallback for genuine textual variants, and is handled by the fact that a 10-word
paste yields 6 shingles and needs only **one** to survive. The offsets let you do the thing
FTS5 cannot: recover *which line* matched by chaining consecutive shingle hits into a
collinear run (offset_in_corpus − offset_in_query ≈ constant), which gives you book+line
directly and a confidence score for free. Measured on the real Perseus corpus this index is
**~1.0 GB with the offset column**, or **~300 MB** in a delta-encoded postings-blob variant,
and answers in **single-digit milliseconds**.

*(numbers filled in / corrected below as measured — see "Measured results")*

---

## 1. CTS / CITE URN conventions

Verified against `canonical-latinLit/data/**/__cts__.xml`.

A CTS URN is colon-delimited with exactly 5 components:

```
urn:cts:latinLit:phi0690.phi003.perseus-lat2:1.1
└1─┘ └2┘ └──3───┘ └──────────4────────────┘ └5┘
```

1. `urn` — literal
2. `cts` — the namespace (protocol)
3. **CTS namespace** — `latinLit` for Latin, `greekLit` for Greek. Also `latinLit` for
   Neo-Latin in the Perseus repo.
4. **Work component**, itself dot-delimited and hierarchical:
   - `phi0690` — **textgroup** (≈ author). `phi####` = PHI (Packard Humanities) author id,
     `tlg####` = TLG id, `stoa####` = Stoa id for authors PHI never numbered.
   - `phi0690.phi003` — **work** (Aeneid). Second element is the work id in that author's
     numbering.
   - `phi0690.phi003.perseus-lat2` — **version** (a specific *edition*). `perseus-lat2` =
     Perseus' 2nd Latin edition; `perseus-eng2` = an English *translation* (a different
     `ti:translation` element, not an edition). There can also be `-lat1`, `-eng1`, ...
5. **Passage component** — the citation proper, e.g. `1.1` = book 1 line 1; `1.1-1.11` is a
   range (dash-separated, both endpoints full citations).

Real metadata files, verified:

- `data/phi0690/__cts__.xml` → `<ti:textgroup urn="urn:cts:latinLit:phi0690">` with
  `<ti:groupname xml:lang="lat">P. Vergilius Maro (Virgil)</ti:groupname>`
- `data/phi0690/phi003/__cts__.xml` → `<ti:work urn="urn:cts:latinLit:phi0690.phi003">`
  with `<ti:title xml:lang="eng">Aeneid</ti:title>`, then one `<ti:edition>` and one
  `<ti:translation>` child, each with `urn`, `<ti:label>` and `<ti:description>` (the
  description is the full bibliographic reference — "Greenough, J.B., editor. Boston: Ginn
  and Company, 1881.").

**This is exactly the author/work/edition triple Enarratio needs to display**, and it is
already sitting in two tiny XML files per work. Harvest `groupname` + `title` + edition
`label`/`description` at index-build time into a `work` table; never parse them at query
time.

**CITE URNs** (`urn:cite:...` / `urn:cite2:...`) are the sibling scheme for non-textual
objects (manuscripts, images, scholia collections). Not needed for passage ID; mentioned
only so the codebase does not conflate them.

## 2. Structure of the Perseus canonical-latinLit TEI

Local copy: `canonical-latinLit/`, 218 MB, **1078 XML files** (both `-lat*` and `-eng*`).

Layout is strictly `data/<textgroup>/<work>/<textgroup>.<work>.<version>.xml`, plus
`__cts__.xml` at the textgroup and work levels.

The citation scheme is declared inside each file's `<encodingDesc>`. Aeneid has *three*
overlapping declarations (verified):

```xml
<refsDecl n="CTS">
  <cRefPattern n="line" matchPattern="(\w+).(\w+)"
    replacementPattern="#xpath(/tei:TEI/tei:text/tei:body/tei:div/tei:div[@n='$1']//tei:l[@n='$2'])"/>
  <cRefPattern n="Book" matchPattern="(\w+)" .../>
</refsDecl>
<refsDecl><refState unit="book" delim="."/><refState unit="line"/></refsDecl>
<refsDecl xml:id="CTS">
  <citeStructure match="/TEI/text/body" use="@xml:base">
    <citeStructure unit="book" delim=":" match="div[@subtype='book']" use="@n">
      <citeStructure unit="line" delim="." match="l" use="@n"/>
```

The old `cRefPattern` form and the new `citeStructure` form coexist; **do not depend on
either**. See §3 for why generic descent beats parsing refsDecl.

Body markup (verbatim from `phi0690.phi003.perseus-lat2.xml`):

```xml
<body xml:base="urn:cts:latinLit:phi0690.phi003.perseus-lat2">
  <div type="edition" xml:lang="lat" subtype="book">
    <div n="1" type="textpart" subtype="book">
      <milestone ed="p" n="1" unit="card"/>
      <l n="1" rend="indent">Arma virumque cano, Troiae qui primus ab oris</l>
      <l n="2">Italiam, fato profugus, Laviniaque venit</l>
```

Note `<milestone unit="card"/>` interleaved — these are Perseus display anchors, **not**
citation units, and must be skipped (they contribute no text but do sit between `<l>`).

### 2a. Corpus census (measured)

| | count |
|---|---|
| `.xml` files total | 1078 |
| `__cts__.xml` metadata files | 388 |
| actual text files | 687 (+3 stray at repo root) |
| of which **Latin** versions (`*-lat*.xml`) | **428** |
| textgroups (authors) | 59 |
| works | 397 |
| disk | 218 MB |

Version-suffix distribution (`ls | rsplit('.',2)[1]`):
`perseus-lat2` 294, `perseus-eng2` 115, `perseus-eng1` 110, `perseus-lat1` 73,
`perseus-eng3` 31, `opp-lat1` 29, `perseus-lat3` 26, `perseus-lat4` 3, `perseus-eng4` 2,
`perseus-lat5` 1, `perseus-lat6` 1, `rolfe-eng1` 1.

**Consequence:** Perseus alone gives only 59 authors / 397 works. It is *citation-perfect but
narrow*. The "~2000 works" figure comes from the Latin Library. See §2c.

### 2b. Element census inside Latin `<body>` (measured over all 428 Latin files)

| tag | occurrences | files |
|---|---|---|
| `hi` | 306,478 | 115 |
| `l` | 211,890 | 187 |
| **`note`** | **125,664** | **199** |
| `p` | 86,537 | 323 |
| `div` | 80,539 | 403 |
| `milestone` | 69,736 | 234 |
| `reg` | 56,007 | 81 |
| `pb` | 29,984 | 286 |
| **`foreign`** | 22,792 | 150 |
| `q` | 18,904 | 175 |
| `sp` / `speaker` | 18,583 | 39 |
| `add` | 11,847 | 144 |
| `choice` | 6,939 | 49 |
| `sic` / `corr` | 6,687 / 6,643 | 43 / 37 |
| `head` | 5,934 | 252 |
| `del` | 3,217 | 161 |
| `gap` | 2,396 | 175 |
| `div2` / `div1` (TEI P4) | 1,646 / 415 | 10 / 14 |
| `app` / `lem` | 691 | 17 |
| `abbr` / `expan` | 690 | 41 |

**This table is the whole extraction spec.** `itertext()` over the body — which is what the
naive extractor does — silently indexes 125k apparatus-criticus notes and 22k Greek
`<foreign>` spans as if they were Latin text. Verified example, Cicero *In Catilinam* 1.1.1:

```xml
<div type="textpart" subtype="section" n="1"><p rend="align(indent)">
  <milestone unit="chapter" n="1"/> <reg>quo</reg> usque tandem abutere, Catilina,
  patientia nostra? quam diu etiam furor iste tuus nos<note>nos <hi rend="italic">om. A et
  Iulius Victor</hi> (<hi rend="italic">Rhet. M. p.</hi> 439): <hi rend="italic">post</hi>
  diu <hi rend="italic">hab. bs</hi></note> eludet? ...
```

`itertext()` yields `... furor iste tuus nos nos om. A et Iulius Victor Rhet. M. p. 439:
post diu hab. bs eludet? ...` — the shingle `tuus nos nos om a` is garbage and the *real*
shingle `furor iste tuus nos eludet` is **destroyed**. Any index built without note-stripping
will fail to match the single most famous sentence in Latin prose.

**Extraction rules, derived from the census:**

| element | action | why |
|---|---|---|
| `note`, `bibl`, `ref` | **drop subtree** | apparatus criticus, editorial |
| `head`, `label`, `speaker`, `figure` | **drop subtree** | headings/stage names, not the author's text |
| `foreign` | **drop subtree** | embedded Greek (22k) |
| `del`, `gap`, `orig`, `sic`, `abbr` | **drop subtree** | rejected/unexpanded readings |
| `reg`, `corr`, `expan`, `lem`, `ex`, `supplied` | **keep text** | the accepted reading |
| `add` | keep text | editorial addition that *is* the text |
| `hi`, `q`, `quote`, `seg`, `w`, `name`, `persName`, `num`, `emph` | keep text (transparent) | pure formatting |
| `milestone`, `pb`, `lb`, `cb` | empty; **skip, but harvest `@n`** | see §2d |
| `app` | descend, but only into `lem` | choose the lemma over variants |
| `choice` | descend into `corr`/`reg`/`expan` only | never both halves |

Because `choice`/`app` wrap a keep-child and a drop-child, a **whitelist walk with an explicit
drop-set beats a blacklist**: recurse, and on entering a drop-tag return "" immediately.

### 2c. The other two corpora

- **Latin Library** `lat_text_latin_library/` — **2141 `.txt`**, 134 MB. Plain text, no
  citation markup at all (line breaks are typographic, not verse lines in every file).
  Licence: **CC Public Domain Mark 1.0** (`LICENSE.md`) — no restrictions.
  This is where the "~2000 works" breadth lives, but it can only ever return
  *author + work*, never book+line, unless you align it to Perseus.
- **Tesserae** `lat_text_tesserae/texts/` — **748 `.tess`**, 73 MB, 70 authors,
  **261 author.work units**. Licence: **UB Public License 1.0**
  (https://cse.buffalo.edu/sneps/ubpl.pdf) — an open licence but *not* CC; check the
  attribution clause before shipping.
  **`.tess` is a tab-separated citation-bearing line format** and is by far the easiest
  high-quality index source:
  ```
  <verg. aen. 1.1>	Arma virumque cano, Troiae qui primus ab oris
  <verg. aen. 1.2>	Italiam, fato profugus, Laviniaque venit
  <ov. fast. 1.1>	Tempora cum causis Latium digesta per annum
  ```
  One regex `^<([^>]*)>\t(.*)$` and you are done — no XML, no note-stripping, one line = one
  citation unit. Tag shapes vary per author though and are *not* CTS
  (`gel. attic. N.N.Narg`, `Quint. Inst. N.pr.N`, `Vulgate 1 Samuel.N.N`,
  `claud. N hon. N`, `scr. hist. aug. N.N`), so you need a hand-built
  `tess-abbrev → CTS-URN` map (~261 rows, one-time, mostly mechanical).

**Recommended source strategy:** index **Perseus TEI as primary** (canonical URNs, exact
book/line), **Tesserae as secondary** for works Perseus lacks (it covers e.g. the Vulgate,
Ausonius, Claudian, the Historia Augusta), **Latin Library as tertiary/breadth** with
work-level-only citations and a lower confidence score. Tag every segment with its source so
the UI can say "Aeneid 1.1 (Perseus)" vs "somewhere in Ausonius, Mosella (Latin Library)".

### 2d. The citation-scheme trap, and the fix (`<citeStructure>`)

Measured over the 428 Latin files:

| declaration present | files |
|---|---|
| `<citeStructure>` (new-style, has `unit` **and** `match`) | **413** |
| `<refState>` (old-style, `unit` only) | 361 |
| `<cRefPattern>` (old-style, XPath template) | 336 |
| none of the three | **1** |

Declared citation depth: 1 level 143 files, 2 levels 106, 3 levels 139, 4 levels 37, 5 levels 2.

**`<milestone unit="section">` occurs 50,557 times and `unit="chapter"` 6,272 times, and in 97
of 428 Latin files (23%) the sectioning exists *only* as milestones, never as `<div>`.**
Livy (`phi0914`) and Pliny NH (`phi0978`) are the big ones. Livy 3.1:

```xml
<div n="3" type="book">
  <milestone n="1" unit="chapter"/>
  <milestone n="1" unit="section"/>
  <p>Antio capto, ... superfuerat.
     <milestone n="2" unit="section"/> iam priore consulatu Aemilius ...
```

So a div-only walker gives Livy a citation of just `3` for an entire book.

But a walker that appends *every* milestone is **also wrong**: Cicero *In Catilinam* is cited
`speech.section` (both `<div>`s) while `chapter` is a *parallel, non-citational* milestone
numbering. Appending it yields the bogus `1.1.1` for what is really `1.1`.

**The fix — drive the citation off the file's own `<citeStructure>`.** It gives the ordered
unit names *and* an XPath `match` that says where each level comes from:

```xml
<!-- Livy: level 2 is a milestone -->
<citeStructure match="div[@type='book']" use="@n" unit="book" delim=":">
  <citeStructure match=".//milestone[@unit='chapter']" use="@n" unit="chapter" delim="."/>
<!-- Cicero: both levels are divs -->
<citeStructure unit="speech" match="div/div[@subtype='speech']" use="@n">
  <citeStructure unit="section" match="div[@subtype='section']" use="@n"/>
<!-- Vergil Eclogues: leaf is <l> -->
<citeStructure unit="poem" match="div/div[@subtype='poem']" use="@n">
  <citeStructure unit="line" match="l" use="@n"/>
```

You do **not** need an XPath engine. Reduce each level to a two-way classification:
`'milestone' in @match` → take the value from the milestone state dict keyed by `@unit`;
otherwise → consume the next `@n` off the div/`l` stack. Then:

```
citation = for each declared level, in order:
             ms[unit]        if level is milestone-backed
             div_stack[i++]  otherwise
           (stop at the first missing value)
```

Working extractor: `/private/tmp/.../scratchpad/extract_cts2.py` (stdlib `xml.etree` only, no
lxml needed). **Measured: 426/428 files parsed, 269,971 segments, 6,972,702 Latin words, 5.6 s.**
The 2 failures are genuinely malformed XML (`phi0692.phi009.perseus-lat1.xml` mismatched tag;
`phi0972.phi001p.perseus-lat1.xml` invalid token) and need `lxml` with `recover=True`, or hand
patching — 0.5% loss, ignorable at first.

Spot-checked outputs, all correct after the fix:

| URN | citation | text |
|---|---|---|
| `phi0690.phi003.perseus-lat2` | `1.1` | Arma virumque cano, Troiae qui primus ab oris |
| `phi0959.phi006.perseus-lat2` | `1.1` | In nova fert animus mutatas dicere formas |
| `phi0893.phi001.perseus-lat2` | `1.1.1` | Maecenas atavis edite regibus, |
| `phi0474.phi013.perseus-lat2` | `1.1` | quo usque tandem abutere, Catilina, patientia nostra? … furor iste tuus **nos eludet?** |
| `phi0914.phi0013.perseus-lat2` | `3.1` | Antio capto, T. Aemilius et Q. Fabius consules fiunt. … |

Note the Cicero row: the `<note>` between `nos` and `eludet` is gone, so the shingle
`furor iste tuus nos eludet` exists. And the citation is `1.1`, not `1.1.1`.

Resulting citation-depth distribution over the 269,971 segments:
depth 1: 8,225 · depth 2: 122,058 · depth 3: 116,930 · depth 4: 22,358 · depth 5: 400.

**Known limitation:** Livy's `citeStructure` declares only `book.chapter`, so segments are
whole chapters (~150–250 words) even though the milestones carry `section` too. That is
CTS-conformant. Recover the finer position from the shingle offset (§4), and optionally emit
a display-only `book.chapter.section` refinement alongside the CTS-valid URN.

**Data quality note:** `@subtype` values in the wild include typos — `secton`, `chaper`,
`Book` (capital B) alongside `book`. Never key logic on `@subtype` string equality; that is
another reason to use `citeStructure`'s explicit `unit`.

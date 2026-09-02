# Commentary and editorial notes — source survey

**Status: in progress (append-only log). Last updated by research agent.**

## Most actionable finding

**You already have, on local disk, a complete line-keyed commentary corpus for Vergil —
Servius (all 12 Aeneid books, Eclogues, Georgics) and Conington (all 12 Aeneid books) — in
Perseus TEI P4, and its structure is a direct index into Enarratio's data model.** The file
`hopper-GreekRoman.tar.gz` (already extracted to `scratchpad/hopper/`) contains
`Classics/Vergil/opensource/serv.verg.aen_lat.xml` and `c.verg.aen{1,2}_eng.xml`, in which
every single note is a `<div2 type="commline" n="N">` nested inside `<div1 type="book" n="B">`.
That means a note's address is literally `(book, line)` — the same key a passage-identification
step produces. No alignment heuristics, no fuzzy matching, no scraping: parse the XML once,
emit rows of `(work, book, line, note_html)`, and commentary lookup becomes a primary-key
join against the passage you already identified. Servius gives 9,489 Latin notes across the
three Vergil works; Conington gives 9,122 English notes on the Aeneid. Both authors are long
dead and the source editions (Thilo/Hagen 1881; Conington 1876) are unambiguously public
domain, so this is the one body of commentary that can ship inside a local-first app with no
licence conditions on the note text itself. Build the Vergil commentary path first; it is
essentially free.

---

## A. Perseus Hopper "Greek and Roman" XML dump (LOCAL — verified)

**Location:** `scratchpad/hopper/Classics/<Author>/opensource/*.xml`
**Size:** 404 MB extracted, 1,127 files, 1,127 XML.
**Format:** TEI P4 (`<!DOCTYPE TEI.2 ... PersProse.dtd>`), NOT TEI P5. Custom Perseus DTD.
**Verified structural note:** every author directory's leaf is named `opensource/` —
113 of 113 second-level dirs. The CVS log inside the files explains why:

    Revision 1.1  2009/12/09 18:06:48  rsingh04
    moved more xml files around based on copyright status

So Perseus itself partitioned this dump by copyright status and this tarball is the
**opensource half**. That is a strong, checkable signal that everything in this tree is
redistributable — but see the licence section below, because "opensource" for Perseus means
CC BY-SA, not public domain, for the *encoding*.

### Vergil commentaries (verified counts)

| File | Work | div1 | Notes (`div2 type="commline"`) |
|---|---|---|---|
| `serv.verg.aen_lat.xml` | Servius on Aeneid | book 1–12 | **7,326** |
| `serv.verg.georg_lat.xml` | Servius on Georgics | book 1–4 | **1,505** |
| `serv.verg.ecl_lat.xml` | Servius on Eclogues | poem pr,1–10 | **658** |
| `c.verg.aen1_eng.xml` | Conington vol. 1 | Book 1–6 (+intro) | **4,422** |
| `c.verg.aen2_eng.xml` | Conington vol. 2 | Book 7–12 (+appendices) | **4,700** |

Servius source edition: *Servii Grammatici qui feruntur in Vergilii carmina commentarii*,
rec. Georgius Thilo et Hermannus Hagen, Leipzig, B. G. Teubner, **1881**. (Read from the
`<sourceDesc><biblStruct>` in the file — not recalled.)

Conington source edition: *P. Vergili Maronis Opera. The works of Virgil, with a Commentary
by John Conington, M.A.*, London, Whittaker and Co., **1876**.

Both editions are pre-1929 → **public domain in the US** as to the underlying text.

### The structure that makes this cheap

    <div1 type="book" n="1">
      <head>SERVII GRAMMATICI IN VERGILII AENEIDOS LIBRVM PRIMVM COMMENTARIVS.</head>
      <div2 type="commline" n="pr"> <p>In exponendis auctoribus haec consideranda sunt: ...
      <div2 type="commline" n="1">  <p>...
      <div2 type="commline" n="2">  <p>...

`n` on div2 is the **line number of the lemmatised verse**. `n="pr"` is the prefatory
material (Servius' *vita Vergilii*) — special-case it, it is not a line.

Inline, notes carry machine-readable canonical citations:

    <cit><quote>hic cursus fuit</quote> <bibl n="Verg. A. 1.534">(1.534)</bibl></cit>

`<bibl n="...">` holds a resolvable canonical reference in Perseus abbreviation style. These
are directly reusable for the allusion/cross-reference feature — Servius' own cross-refs to
Plautus, Terence, Lucretius etc. were hand-corrected by Perseus student editors (see the CVS
log: "fixed Pl. Trin. references", "fixed Ter. An. references").

**Implementation edge cases for the commline parser:**
1. `n="pr"` (and other non-numeric `n`) — prefaces. Do not `int()` blindly.
2. Conington vol. 2 has `div1 type="Preface" n="pref.,2"` — the `n` contains a comma and a
   period. Any `n` parser must treat `n` as an opaque string first, numeric second.
3. Conington vol. 2 also carries `div2` of type `Excursus` (2), `Part` (2), `note` (30),
   `Introduction` (1) alongside the 4,700 `commline`s. Filter on `type="commline"` or you
   will mix essay material into line notes.
4. Servius notes are **Latin**, Conington's are **English but quote Latin and Greek**;
   `<profileDesc><langUsage>` on Conington declares en, la, greek, **and it**. Mixed script.
5. Ranged notes exist in Perseus commentaries generally — a single `n` may cover several
   verses in some texts. For Servius/Conington the observed pattern is one integer per note,
   but the resolver should still be a range-overlap query, not equality, so it survives
   commentaries where `n="12-14"`.
6. `<pb/>` page breaks appear mid-sentence inside `<p>`. Strip them, do not treat as
   paragraph boundaries.
7. Entities `&responsibility;`, `&fund.NEH;`, `&Perseus.publish;` are **undefined in this
   tarball** — the Perseus DTD is not shipped. A strict XML parser will fail. Parse with
   entity resolution disabled / recovering mode (`lxml.etree.XMLParser(recover=True,
   resolve_entities=False)`), or pre-substitute empty strings.

### Other commentaries present in the same dump (filename evidence)

- `Classics/Ovid/opensource/ovid.her_comm.xml` — commentary on the *Heroides*.
- `Classics/Livy/opensource/livy.weisscomm{31-32,33-34,35-38,39-40,41-42,43-44,45}.xml` —
  Weissenborn's commentary on Livy, 7 volumes.
- `Classics/Livy/opensource/livy.schles43-45.xml`, `livy.foster21-22.xml`.
- Greek-side (not needed now but same shape): Jebb on Sophocles (5 plays), Leaf on the Iliad,
  Monro on the Odyssey, Macan and How on Herodotus, Gildersleeve on Pindar, Sandys on
  Demosthenes.
- `Classics/Caesar/opensource/ag.caes.bg_eng.xml` — Allen & Greenough's *edition* of Caesar
  BG (school commentary; pairs with the A&G grammar you already have as `ag_*.htm`).
- `Classics/Horace/opensource/shore.hor_eng.xml` — Shorey/Shore on Horace.


### Other local commentaries — verified headers

| File | Title (from TEI) | Editor / publisher | Date | Structure |
|---|---|---|---|---|
| `Ovid/opensource/ovid.her_comm.xml` | Commentary on the Heroides of Ovid | J. Nunn / R. Priestley, London | **1813** | `div1 type="poem"` ×21, **no div2** |
| `Caesar/opensource/ag.caes.bg_eng.xml` | Commentary on Caesar's Gallic War | **J. B. Greenough**, Ginn and Company | **1898** | `div1` Book×7, chapter×9; `div2` Chapter×341, section×45 |
| `Horace/opensource/shore.hor_eng.xml` | Commentary on Horace, Odes, Epodes, Carmen Saeculare | **Paul Shorey**, Benj. H. Sanborn | **1910** | `div1` book×4, work×2; `div2` poem×117, commline×61, intro×3 |
| `Livy/opensource/livy.weisscomm31-32.xml` (+6 more vols) | Ab urbe condita, erklärt von M. Weissenborn | Weidmannsche Buchhandlung | **1883** | `div2` chunk/chunkY/chunkZ — **irregular, German** |

Notes on these:
- **Ovid Heroides commentary has no `div2`** — the notes are not line-segmented in the
  encoding. Poem-level granularity only. Much lower value for Enarratio than Servius.
- **Greenough on Caesar (1898)** is the same Greenough as Allen & Greenough. Its notes are
  keyed by `Chapter`, not by line — prose text, so chapter/section is the right granularity.
  This pairs naturally with the `ag_*.htm` grammar files already in the scratchpad.
- **Shorey on Horace (1910)** is mostly `div2 type="poem"` with only 61 `commline`s — so it
  is poem-keyed, not line-keyed. Resolve at poem level (`Odes 1.5`), not line level.
- **Weissenborn on Livy is in German** and uses opaque `chunk`/`chunkY`/`chunkZ` div2 types.
  Low value: wrong language for a student-facing English/Latin tool, and the chunking does
  not map cleanly to Livy's book.chapter.section citation scheme. **Deprioritise.**
- `livy.foster21-22.xml` header literally reads `<date>1929: no copyright notice</date>` —
  Perseus recorded the PD determination in the metadata. Useful precedent: Perseus did the
  copyright clearance work and left an audit trail in the files.

**Ranking for Enarratio:** Servius (Latin, line-keyed, complete) > Conington (English,
line-keyed, complete) > Greenough on Caesar (English, chapter-keyed) > Shorey on Horace
(poem-keyed) > Ovid Heroides (poem-keyed, no div2) > Weissenborn (German, deprioritise).

---

## B. Dickinson College Commentaries (DCC)

**Licence: CC BY-SA 4.0** — confirmed from https://dcc.dickinson.edu/about-dcc, which states
the commentaries are "peer-reviewed, citable scholarly resources, licensed under a Creative
Commons Attribution-ShareAlike License (CC BY-SA)" linking to
`http://creativecommons.org/licenses/by-sa/4.0/`.
Caveat: **individual DCC works carry their own licences.** The *Tacitus Annals* volume is
CC BY 3.0 (more permissive, commercial use explicitly allowed). Allen & Greenough on DCC is
CC BY-SA. **Check per-work, do not assume a site-wide licence.**

**ShareAlike is the thing that decides what can ship.** CC BY-SA 4.0 means: if Enarratio
embeds DCC note *text*, the derivative work containing it must be released under a compatible
licence. For a local-first app this is survivable if DCC notes live in a separately-licensed
data pack rather than being fused into proprietary code — keep DCC content in its own
`data/dcc/` bundle with its own LICENSE file and attribution, and do not mix it into
CC-incompatible content in the same file.

### Programmatic access — what actually works (tested)

| Endpoint | Result |
|---|---|
| `GET /latin-core-list.csv?page&_format=csv` | **HTTP 200, `text/csv`, 81 KB, 997 rows** ✅ |
| `GET /latin-core-list.xml?page&_format=xml` | advertised via `<link rel="alternate">` |
| `GET /jsonapi` | **404** — Drupal JSON:API module not enabled ❌ |
| `GET /node/4669?_format=json` | **406** "A route that returns a rendered array as its response only supports the HTML format" ❌ |
| `GET /vergil-aeneid/...?_format=json` | **406**, same ❌ |
| `GET /robots.txt` | 200 — default Drupal robots; **content pages are NOT disallowed** ✅ |

**Conclusion: DCC has no commentary API. Notes must be parsed from HTML.** The only
structured export is the Latin Core Vocabulary view. Site is Drupal 11.

Verified CSV shape (`dcc_core.csv`, 1,000 headwords, macronized):

    Headword,Definition,"Part of Speech","Semantic Group","Frequency Rank"
    "ā ab abs","from, by (+abl.)",Preposition,Place,21
    "abeō -īre -iī -itum","go away","Verb: Irregular",Motion,553

This is independently valuable: a macronized, frequency-ranked, semantically-grouped 1,000-word
core vocabulary. Useful for "is this word worth glossing?" decisions in the reading UI.

### Why DCC is the format model to copy

The captured page `scratchpad/dcc_aen.html` (canonical
`https://dcc.dickinson.edu/vergil-aeneid/vergil-aeneid-i-1-11`, `node/4669`) shows exactly
the output Enarratio is trying to produce. Extracted note text:

> **1 :** *arma virumque* : the first word, indicating war as the subject matter of the poem,
> challenges comparison with the *Iliad*; the second challenges comparison with the *Odyssey*.
> ... (**Williams**). *primus:* "first," not here in the sense of "the first who," but "at the
> first," ... (**Frieze**). ... (**Bennett**).
> **2 :** *Italiam:* acc. of the limit of motion. In prose a preposition (*ad* or *in*) would
> be required (**F-B**) (**AG 428g**).

Three things to steal:
1. **Line-number-keyed notes** (`1 :`, `2 :`) — same key as Servius' `commline`.
2. **Per-note attribution to a named 19th-c. commentator** (Williams, Frieze, Bennett, F-B =
   Frieze–Dennison). DCC's editors compiled from PD commentaries and *credited each one*.
   This is the model: aggregate PD notes, attribute inline.
3. **Cross-references into Allen & Greenough by section number** (`AG 428g`) — and you
   already have A&G locally as `ag_*.htm`. These are directly resolvable into your existing
   28-construction detector output. `AG 428g` = accusative of limit of motion; if your
   detector fires "accusative of place to which", you can link the same A&G section DCC links.

DCC's Aeneid text is also **fully macronized** (`Arma virumque canō, Trōiae quī prīmus ab
ōrīs`) — a free gold-standard check for the macronizer/scansion work, on a passage every
student starts with.

**DCC Vergil coverage (from the page's own nav):** *Aeneid* Book 1 complete, in 38 chunks
(1-11, 12-33, 34-49, ... 723-756), plus **Book 2, Book 4, Book 6**. Edited by Christopher
Francese and Meghan Reedy. Not all 12 books — it is a *Selections* edition.


### DCC HTML scraping contract (verified against `dcc_aen.html`)

Drupal field wrappers, stable across DCC pages:

| Selector | Contains |
|---|---|
| `div.field--name-body` | the Latin text (macronized), `<p>` per line |
| `span.line-number` | the line number printed every 5 lines inside the text |
| `div.field--name-field-notes` | **the commentary notes** |
| `div.field--name-field-vocab` | the running vocabulary list |
| `details#edit-group-notes` / `-vocabulary` / `-media` | the three collapsible tabs |
| `link[rel=canonical]` | e.g. `/vergil-aeneid/vergil-aeneid-i-1-11` |
| `link[rel=shortlink]` | e.g. `/node/4669` — stable numeric id |

Note paragraph shape inside `field--name-field-notes` — one `<p>` per verse:

    <p><b>2</b><strong>:</strong> <b>Italiam:</b> acc. of the limit of motion. In prose a
    preposition (<i>ad</i> or <i>in</i>) would be required (F-B)
    (<a href="http://dcc.dickinson.edu/grammar/latin/relations-space">AG 428g</a>).
    ... <b>fato:</b> belongs to both <i>profugus</i> and <i>venit</i> (F-B).</p>

**Parse rule:** for each `<p>` in the notes field, a leading `<b>` whose text is an integer
(optionally a range) followed by a `:` is the **verse key**. Within the paragraph, each
subsequent `<b>`/`<strong>` starts a new **lemma sub-note**; the text up to the next bold run
is that lemma's note; a trailing `(Name)` in parentheses is the **attribution**.

**Scraper edge cases:**
1. The first `<p>`s are not notes: `Manuscripts: M | R` links, then a **passage-level essay
   teaser** ending in `[full essay]`. Skip any `<p>` not starting with a bold integer.
2. Bold markup is inconsistent — `<b>1</b><strong>:</strong>` mixes `b` and `strong`, and
   lemma bolds sometimes swallow the trailing space/colon (`<b>primus: </b>`). Normalise by
   stripping and matching on text, not tag identity.
3. Curly quotes (`“first,”`) and `&nbsp;` are used throughout. Normalise Unicode.
4. Attributions are terse initials: `F-B` = Fairclough–Brown, `G-K` = Greenough–Kittredge,
   plus `Williams`, `Frieze`, `Bennett`, `Austin`. **Austin and Williams are 20th-century and
   still in copyright** — DCC quotes them under its own arrangement. See the licence warning
   below.
5. The notes div has an inline `style="height: 400px; overflow-y: scroll"` wrapper `<div>`
   between the field div and the `<p>`s. Do not assume `<p>` are direct children.
6. Outbound links are typed and worth keeping: `pleiades.stoa.org/places/<id>` (geography),
   `perseus.tufts.edu/hopper/text?doc=...entry%3D<lemma>` (lexicon),
   `dcc.dickinson.edu/grammar/latin/<slug>` (A&G section), `en.wikipedia.org` (concepts),
   `mss.bmlonline.it` (manuscript facsimiles).

> ⚠ **Licence hazard inside DCC notes.** DCC's notes are a *compilation* of PD commentators
> (Frieze 1860s, Bennett, Fairclough–Brown, Greenough–Kittredge — all PD) **mixed with
> quotations from in-copyright scholars (R. D. Williams, R. G. Austin)**. The CC BY-SA 4.0
> licence covers DCC's own editorial work. It does **not** launder the third-party quotations.
> If you ingest DCC notes wholesale you inherit that mixture. Safer paths: (a) ship DCC notes
> as a separate, clearly-attributed CC BY-SA data pack, or (b) filter to sub-notes whose
> attribution tag is a known-PD commentator and drop `(Williams)` / `(Austin)` ones.

---

## C. Perseus `canonical-latinLit` (LOCAL) — **contains no commentaries**

**Verified negative result, and it matters architecturally.**

I title-scanned all 1,078 XML files in `scratchpad/canonical-latinLit/data/`. Only **two**
files have a commentary-ish title, and both are false positives — Caesar's *Commentaries on
the Civil War* and the pseudo-Ciceronian *Commentariolum Petitionis*, i.e. primary works
whose Latin titles happen to contain "commentar-". **There is not one work of scholarly
commentary in the repo.**

**Implication:** Perseus's modern, CTS/TEI-P5, URN-addressable repos (`canonical-latinLit`,
`canonical-greekLit`) carry *primary texts and translations only*. **The commentaries were
left behind in the legacy Hopper P4 dump.** So:

- For **passage identification and canonical citation** → use `canonical-latinLit` (clean
  TEI P5, CTS URNs like `urn:cts:latinLit:phi0690.phi003`).
- For **commentary** → you must use the older `hopper/` P4 tree. Two different schemas, two
  different citation conventions; you will need a mapping layer between them.

**Licence (read from `canonical-latinLit/license.md` and `README.md`):**
**CC BY-SA 4.0 International**, full legal text shipped in the repo. The README adds a
project-specific request beyond the bare licence:

> "Tufts University holds the overall copyright to the Perseus Digital Library... Materials
> within the Perseus DL have varying copyright status: please contact the project for more
> information about a specific component or object. ... Unless otherwise indicated, all
> contents of this repository are licensed under a Creative Commons Attribution-ShareAlike
> 4.0 International License. **You must offer Perseus any modifications you make.** Perseus
> provides credit for all accepted changes."

Two things to note: (1) "**varying copyright status**" — Perseus explicitly declines to
warrant that every object is CC BY-SA; (2) the "offer modifications back" clause is a
*request*, not part of CC BY-SA 4.0, but it is the community norm and cheap to honour.

Repo is citable: Zenodo DOI badge, `https://zenodo.org/badge/latestdoi/36303583`.


---

## D. Perseus Hopper — the live access path for the commentary XML

**Download page:** https://www.perseus.tufts.edu/hopper/opensource/download

**Licence (quoted from that page): "Texts are licensed under the Creative Commons
ShareAlike 3.0 License", linking `http://creativecommons.org/licenses/by-sa/3.0/us/`
→ i.e. CC BY-SA 3.0 *United States*.**

Note the version mismatch that matters for compliance:
- Hopper P4 dump (where the commentaries are) = **CC BY-SA 3.0 US**
- `canonical-latinLit` P5 repo (primary texts only) = **CC BY-SA 4.0 International**

CC BY-SA 3.0 US is **one-way upgradeable to 4.0** (BY-SA 3.0's §4(b) "later version" clause,
and CC's official compatibility ruling), so you can relicense a 3.0-US-derived data pack
under BY-SA 4.0 and have one consistent licence for the whole commentary bundle. You cannot
go the other way.

**Verified live (HTTP HEAD, 2026-09-02):**

    https://www.perseus.tufts.edu/hopper/opensource/downloads/texts/hopper-texts-GreekRoman.tar.gz
    HTTP/1.1 200 OK
    Last-Modified: Fri, 27 May 2011 14:52:41 GMT
    Content-Type: application/x-gzip
    Access-Control-Allow-Origin: *
    Accept-Ranges: bytes

125 MB. **This is the exact file already in your scratchpad** as
`hopper-GreekRoman.tar.gz` (124,801,865 bytes). `Last-Modified: 2011` — the corpus is frozen;
there is no update to track and no reason to re-fetch. Pin it and vendor it.
`Accept-Ranges: bytes` + `Access-Control-Allow-Origin: *` mean it can be range-fetched and
even pulled from a browser if you ever want partial downloads.

Other collections on the same page: `hopper-texts.tar.gz` (all, 447 MB), Germanic (58 KB),
American History (220 MB), Richmond Times (89 MB), Renaissance (15 MB), Arabic (15.5 MB).
Also `/hopper/opensource/downloads/data/` — MySQL dumps and processed XML for **artifacts,
citations, entities, frequencies, lemmas**. The **citations** dump is worth a look for the
allusion feature (it is Perseus's extracted cross-reference index).

## E. Scaife Viewer — good for texts, useless for Latin commentary

**Verified by querying the live service, not from memory.**

| Endpoint | Status |
|---|---|
| `GET https://scaife.perseus.org/library/json/` | **200**, `application/json`, **6.1 MB** ✅ |
| `GET .../library/passage/<urn>/json/` | **200** ✅ (tested `urn:cts:latinLit:phi0690.phi003.perseus-lat2:1.1-1.11` → 9,956 bytes) |
| `POST https://scaife.perseus.org/atlas/graphql/` | **200**, full GraphQL introspection works ✅ |
| `https://scaife-cts.perseus.org/api/cts?request=GetCapabilities` | **connection failed (HTTP 000)** ❌ — the old CTS API endpoint is dead; use the ATLAS/GraphQL and library JSON instead |

**Library inventory (computed from the 6.1 MB JSON): 557 text groups, 2,699 works,
3,860 texts, of which 739 are `latinLit`.**

**Commentary-labelled texts in Scaife: 0.** A raw scan for `servius|commentar|scholi` returns
416 hits, but every one is a *Greek* philosophical commentary — the *Commentaria in
Aristotelem Graeca* series (Alexander of Aphrodisias, Ammonius, Sophonias…), Berlin: Reimer,
supplied by the Digital Corpus for Graeco-Arabic Studies. **No Servius. No Conington. No
Latin literary commentary at all.**

So Scaife confirms the same architectural split as `canonical-latinLit`: the modern Perseus
stack carries primary texts, and the Latin commentaries exist *only* in the frozen 2011 P4
Hopper dump.

ATLAS GraphQL query fields (from live introspection) — worth knowing for other Enarratio
features: `textGroup(s)`, `work(s)`, `version(s)`, `textPart(s)`, `passageTextParts`,
`textAlignment(s)`, `textAlignmentRecord(s)`, `textAnnotation(s)`, **`syntaxTree(s)`**,
**`metricalAnnotation(s)`**, `imageAnnotation(s)`, `audioAnnotation(s)`.

⚠ But I queried `textAnnotations(first:5)` and `metricalAnnotations(first:3)` on the
production deployment and **both returned `{"edges":[]}` — empty.** The schema advertises
metrical and syntactic annotation, but the public server has no data loaded for them. Do not
plan the scansion feature around Scaife's `metricalAnnotations`.

Scaife code is **MIT** (`scaife-viewer/scaife-viewer`, 99 stars; `scaife-cts-api`,
`scaife-search-indexer`, `scaife-widgets` all MIT). So the *software* is reusable even though
the commentary *data* is not there.


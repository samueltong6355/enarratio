# Cultural and realia background — sourcing the "humoral theory / Roman triumph" layer

*Research notes for Enarratio. Written incrementally; every claim marked VERIFIED was
checked against local data or a live URL during this session. Claims marked RECALL are
from model memory and must be re-checked before implementation.*

---

## Most actionable finding (read this first)

**Do not plan on the Perseus "hopper" open-source dump for Smith's dictionaries or
Harper's — it does not contain them, and the empty directories in the tarball are a
deliberate rights carve-out, not a download error.** VERIFIED locally: the 124 MB
`hopper-GreekRoman.tar.gz` in the scratchpad expands to 1374 entries in which
`Classics/Smith/`, `Classics/Harper/`, `Classics/Encyclopedia/`, `Classics/ArchDB/`,
`Classics/Vase_Painters/`, `Classics/Boegehold/`, `Classics/Stewart/` and
`Classics/Reisner/` are **bare directory stubs with zero files**. The realistic plan is
therefore a *two-tier* one: (tier 1) build the entity-linking index out of things that
really are openly licensed and machine-tractable — **Pleiades** (CC-BY, daily JSON/CSV
dumps, ~40k ancient places with coordinates and time-spans), **Wikidata** (CC0, SPARQL +
dumps, the glue that joins Pleiades ↔ ToposText ↔ VIAF ↔ Wikipedia), **ToposText**
(CC-BY-NC-SA, one downloadable place-list, 6k+ places keyed to Pleiades), and **the
encyclopedic material already sitting inside Lewis & Short**, which is public-domain,
already in the repo as `ls_corpus.parquet`, and already keyed by the exact lemma strings
the parser emits; and (tier 2) treat Smith's *Antiquities* / *Biography and Mythology* /
*Geography* and Harper's as PD-but-must-be-acquired-elsewhere (Perseus website scrape
under its CC-BY-SA terms, LacusCurtius, Wikisource, or Internet Archive OCR), scheduled
after tier 1 rather than as a dependency of it. Tier 1 alone already covers the two
canonical demo cases: a *place* token like `Cannas` links by gazetteer, and a *realia*
token like `triumphus` or `bilis` links by lemma into L&S's own encyclopedic note.

---

## Verified inventory of what is on disk

### `hopper-GreekRoman.tar.gz` — Perseus Hopper open-source text dump
- **Location:** `/private/tmp/claude-501/-Users-samueltong/c1f16a5b-019c-4034-b903-a79279f6a3e8/scratchpad/hopper-GreekRoman.tar.gz` (124,801,865 bytes), expanded at `.../scratchpad/hopper/`.
- **Shape:** `Classics/<Author>/opensource/<file>.xml`, TEI P4 with the Perseus
  `PersDict.dtd` / `Perseus.publish` entity set.
- **VERIFIED — reference works absent.** `tar tzf hopper-GreekRoman.tar.gz | grep -Ei 'smith|harper|encyclo|archdb'`
  returns only the empty directory entries plus three *unrelated* files that merely have
  "smith" in the filename because of a translator's surname:
  `Classics/Thucydides/opensource/smith.thuc{3,6,7}_eng.xml`,
  `Classics/Xenophon/opensource/smith.mem_eng.xml`,
  `Classics/Catullus/opensource/cat.smithers_eng.xml`. Those are translations by William
  Smith and Leonard Smithers, **not** the dictionaries.
- **VERIFIED — the `Lewis` directory is a false friend.** `hopper/Classics/Lewis/opensource/lewis.xml`
  (14,535,857 bytes) is *An Elementary Latin Dictionary*, Charlton T. Lewis alone,
  American Book Company 1890 — confirmed from its own `<sourceDesc>`. It is **not**
  Lewis & Short. It also uses `<entry>` not `<entryFree>` (`grep -c '<entryFree'` = 0),
  so any extractor written against L&S's element names will silently produce nothing.
- **Consequence for planning:** the Hopper dump is still useful (it is the source for
  Celsus, Galen, Hippocrates, Aretaeus — i.e. the *primary* medical texts that underpin
  the humoral-theory layer) but it is not a shortcut to the encyclopedias.

*(notes continue below; appended as research proceeds)*

### CORRECTION to the project brief: `ls_corpus.parquet` is **not** Lewis & Short
VERIFIED by reading the files. The three `ls_*.parquet` files are a **Latin
intertextuality / text-reuse benchmark**, not a lexicon:

| file | rows | schema |
|---|---|---|
| `ls_corpus.parquet` | 90,546 | `id, work, author, citation, text_original, text` |
| `ls_queries.parquet` | 85,254 | same schema |
| `ls_labels.parquet` | 1,490 | `query_*` ↔ `corpus_*` pairs + `reference_type`, `fold`, `provenance_*` |

`ls_corpus` row 0 is `<cat. 1.1.1>` "Cui dono lepidum novum libellum…". Author
distribution: `cic` 54,331, `ov` 14,096, `verg` 4,861, `mart` 4,114, `lucan` 2,952,
`stat` 2,527, `hor` 2,353, `prop` 1,889, `lucr` 1,826, `cat` 809, `tib` 788.
`ls_labels.reference_type` ∈ {`cit.` 858, `cf.` 632}; `provenance_dataset` ∈
{`burns` 945 (https://doi.org/10.18653/v1/2021.naacl-main.389), `ngram_pipeline` 287
(http://www.digitalhumanities.org/dhq/vol/18/3/000716/000716.html),
`schropp_goldstandard` 258 (https://journals.ub.uni-heidelberg.de/index.php/dco/article/view/104963)}.
**This belongs to the allusion-detection topic, not to cultural background.** Whoever
wrote the brief conflated it with L&S because of the `ls` prefix.

Also VERIFIED: none of the local sqlite DBs is a lexicon either. `idx.db`, `sh5.db` and
`win.db` all carry a `seg(id, u, c, t)` table (urn / citation / text) plus FTS5 or
shingle-hash indexes — they are **passage-identification** indexes over the corpus.
`macrons.db` is `morpheus(id, wordform, morphtag, lemma, accented)`.

**Net: there is no Lewis & Short on disk.** `ls_head.xml` is only the 9 kB TEI header of
it, and `hopper/Classics/Lewis/opensource/lewis.xml` is Elementary Lewis.

### Where Lewis & Short actually lives — VERIFIED
`https://github.com/PerseusDL/lexica`, licence **CC BY-SA 4.0** (stated in the repo
README). Full file tree fetched via
`curl -s "https://api.github.com/repos/PerseusDL/lexica/git/trees/master?recursive=1"`
(43 entries, not truncated). The Latin files:

```
CTS_XML_TEI/perseus/pdllex/lat/ls/lat.ls.perseus-eng1.xml            77,248,803 B
CTS_XML_TEI/perseus/pdllex/lat/ls/lat.ls.perseus-eng2.xml            77,414,731 B
CTS_XML_TEI/perseus/pdllex/lat/viaf2845558/viaf001/viaf2845558.viaf001.xml  14,536,947 B  (= Elementary Lewis)
```
Raw fetch path:
`https://raw.githubusercontent.com/PerseusDL/lexica/master/CTS_XML_TEI/perseus/pdllex/lat/ls/lat.ls.perseus-eng1.xml`

**The repo contains no Smith and no Harper** — only `grc/lsj/*` (27 files) and the three
Latin files above. So the "Perseus has it on GitHub" assumption fails for the
encyclopedias exactly as it fails for the Hopper dump.

### Pleiades — VERIFIED (https://pleiades.stoa.org/downloads)
- **Licence: CC BY 3.0** — "Sharing and remixing permitted under terms of the Creative
  Commons Attribution 3.0 License (cc-by)." No NC, no SA. This is the cleanest licence
  of anything in this survey and the reason Pleiades should be tier 1.
- **Daily single-format snapshots** (regenerated nightly, RDF weekly on Sundays):
  - JSON "Preferred Export" (complete: places, names, locations, connections) — `https://atlantides.org/downloads/pleiades/json/`
  - CSV "Legacy Export" (places / names / locations tables) — `https://atlantides.org/downloads/pleiades/dumps/`
  - CSV GIS-ready — `https://atlantides.org/downloads/pleiades/gis/`
  - KML/KMZ — `https://atlantides.org/downloads/pleiades/kml/`
  - RDF/Turtle (places, errata, authors, types, periods) — `https://atlantides.org/downloads/pleiades/rdf/`
- **Quarterly citable releases** (use these for reproducibility): GitHub
  `https://github.com/isawnyu/pleiades.datasets/releases`, Zenodo
  `https://doi.org/10.5281/zenodo.1193921`, NYU FDA `http://hdl.handle.net/2451/34305`.
  Current at time of writing: **v4.1, 28 May 2025**.

### ToposText — VERIFIED (https://topostext.org/TT-downloads)
Downloadable files, all under `https://topostext.org/downloads/`:

| file | format | size | contents |
|---|---|---|---|
| `ToposText_places_2025-11-20.geojson` | GeoJSON | 5.6 MB | all mapped places |
| `ToposTextGazetteer.jsonld` | JSON-LD | 9 MB | places **with ancient text citations** — the useful one |
| `pelagios.ttl` | RDF Turtle | 5.4 MB | **place data with Pleiades and DARE equivalences** — the alignment file |
| `ToposTextWorkTurtles.ttl` | Turtle | 1.1 MB | text library, Dublin Core metadata |
| `ToposText_Ancient_PlacesbyRegions2025-11-14.kmz` | KMZ | 1.4 MB | places by region |
| `ToposText_GoogleEarth_places_by_featuretype2025-11-19.kmz` | KMZ | 1.4 MB | places by feature type |
| `topostext.void.ttl` | VoID | 2 KB | dataset metadata |

Scale (from the site's own front page): 886 texts, **8,150 places**, **22,003 proper
names** (people, gods, festivals), 279,191 ancient references. The 22k proper-name index
is the part that matters for entity linking — it covers *people and gods and festivals*,
not just places, which is precisely the gap Pleiades leaves.
Licence caveat: the downloads page only says data is shared "with appropriate
attribution to ToposText" and does not name a licence on that page; ToposText is
generally published **CC BY-NC-SA** (the NC clause is the constraint to check before
shipping). **Treat the licence as unresolved and verify with the site owner before
redistribution**; using `pelagios.ttl` purely as an *alignment table* to Pleiades IDs is
the low-risk use.

---

## ★ THE ANSWER: `PerseusDL/canonical-pdlrefwk` — all three Smith dictionaries, CC BY-SA 4.0

This supersedes the pessimism above. The reference works *are* on GitHub, just not in the
repo everybody names. VERIFIED by downloading all three files during this session.

**Repo:** `https://github.com/PerseusDL/canonical-pdlrefwk` (branch `master`; there is no
`main` — the API returns "Not Found" for it). Full tree fetched, 30 entries, not truncated.
**Licence: CC BY-SA 4.0** — VERIFIED by downloading `license.md` (18,625 B), which is the
verbatim "Attribution-ShareAlike 4.0 International" deed. The GitHub API also reports
`spdx_id: CC-BY-SA-4.0` for the repo.

Base URL for raw fetches:
`https://raw.githubusercontent.com/PerseusDL/canonical-pdlrefwk/master/data/`

| path under `data/` | bytes | **what it actually is** (read from its own `<teiHeader>`) |
|---|---:|---|
| `viaf88890045/001/viaf88890045.001.xml` | 24,375,971 | **Smith, A Dictionary of Greek and Roman Antiquities (1890)**, John Murray = Perseus `1999.04.0063` |
| `viaf88890045/002/viaf88890045.002.xml` | 30,544,537 | **Smith, Dictionary of Greek and Roman Geography (1854)**, Walton & Maberly |
| `viaf88890045/003/viaf88890045.003.perseus-eng1.xml` | 36,481,106 | **Smith, A Dictionary of Greek and Roman Biography and Mythology** (1848, 1873 printing), John Murray = Perseus `1999.04.0104` |
| `viaf66541464/001/viaf66541464.001.perseus-eng1.xml` | 20,190,148 | Liddell–Scott, *An Intermediate Greek-English Lexicon* (1889) — **not** Harper's |
| `viaf39744457/001/viaf39744457.001.perseus-eng1.xml` | 3,565,857 | **Allen & Greenough's New Latin Grammar** in canonical TEI — better than the scraped `ag_*.htm` files already in the scratchpad |
| `viaf32364342/001/viaf32364342.001.xml` | 10,588,415 | Zoega's Old Icelandic dictionary (irrelevant) |

CTS URNs, from `data/viaf88890045/003/__cts__.xml`:
`urn:cts:pdlrefwk:viaf88890045.003` (work) / `urn:cts:pdlrefwk:viaf88890045.003.perseus-eng1` (edition),
`groupUrn="urn:cts:pdlrefwk:viaf88890045"` (= William Smith). By the same scheme,
Antiquities is `.001` and Geography is `.002`.

**Harper's is NOT in this repo, nor anywhere in the PerseusDL org** (all 47 org repos
listed and checked). See the Harper's section below for the fallback.

### Entry structure of Smith's Antiquities — VERIFIED by parsing the downloaded file
TEI P5, **not** the `<entryFree>` shape of L&S. The whole dictionary is:

```xml
<div type="entry" xml:id="triumphus-cn">
  <head>TRIUMPHUS</head>
  <byline>…author initials…</byline>
  <p>… prose, with <foreign xml:lang="la">…</foreign>, <foreign xml:lang="greek">…</foreign>,
     <bibl n="Hom. Od. 2.37">Od. 2.37</bibl>,
     <ref target="ricinium-cn" n="U">RICINIUM</ref> …</p>
</div>
```

Counts in `smith_antiq.xml`: `div type="entry"` = **3,409**; divs carrying both `xml:id`
and `<head>` = 3,772; `div type="alphabetic letter"` = 22, `"section"` = 12, `"preface"` = 1.
Element frequencies: `foreign` 48,195, `bibl` 29,545, `title` 25,585, `p` 13,655,
`ref` 7,235, `figure` 1,057 (illustrations), `row`/`cell` (tables) 1,411/7,417.

**The `xml:id` is the linking key and it is a slugified headword plus `-cn`.** Confirmed by
direct lookup: `triumphus-cn` → `TRIUMPHUS`, `toga-cn` → `TOGA`, `lictor-cn` → `LICTOR`,
`pontifex-cn` → `PO&acute;NTIFEX`, `funus-cn` → `FUNUS`, `medicina-cn` → `MEDICI&acute;NA`,
`haruspices-cn` → `HARU&acute;SPICES`.

Two edge cases already visible in that list:
1. **`<head>` text still contains SGML accent entities** (`&acute;`, and by inspection also
   `&grave;`) marking the printed Latin accentuation: `HARU&acute;SPICES`, `MEDICI&acute;NA`.
   Any headword normaliser must strip `&[a-z]+;` before matching, or every polysyllable
   with a printed accent will silently fail to match.
2. **The headword is not always the lemma LatinCy will emit.** `gladiator-cn` does **not**
   exist (the article is under the plural), while `haruspices-cn` is plural where the lemma
   is `haruspex`. So naive `lemma + "-cn"` is necessary but not sufficient — see the
   entity-linking algorithm section.

The `-cn` suffix is also what the live Perseus site uses, so an `xml:id` doubles as a
citable public URL with zero extra mapping:
`https://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.04.0063:entry%3Dtriumphus-cn`
(VERIFIED pattern: search results return live pages for `argentum-cn`, `gens-cn`,
`domus-cn`, `mimus-cn`, `ludus-litterarius-cn`.)

### `smith_bio.xml` carries real named-entity markup
Element counts: **`persName` 25,676**, `surname` 25,599, `addName` 5,994, `forename` 3,601,
`date` 17,444, `div` 29,870 / `head` 29,871 (i.e. ~29.8k entries), `bibl` 50,166.
The `persName`/`surname`/`addName` markup is the reason Biography is the *easiest* of the
three to link automatically: Roman names are already decomposed into praenomen / nomen /
cognomen rather than sitting in undifferentiated head text.

### `smith_geog.xml`
`div`/`head` 12,215/12,778 entries, `title` 47,327, `bibl` 32,889, `ref` 13,640,
`label` 22,697, `figure` 535. This is the one to **join to Pleiades** rather than use alone.

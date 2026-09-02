# Complete Latin Syntax Taxonomy — coverage checklist for Enarratio

**Most actionable finding.** Our 28 detectors cover roughly **12% of the ~230 named
constructions** Allen & Greenough actually labels, and the gap is not evenly distributed:
we have decent case coverage but we are missing *almost the entire subordinate-clause and
mood system*, which is where a student translating actually gets stuck. Concretely, the
highest-value missing block is **eleven clause detectors that are pure morphology+dependency
rules with a closed conjunction list** — `quin`/`quominus` clauses (A&G 558–559), substantive
clauses of purpose after verbs of commanding (563), substantive clauses of result (568–571),
causal `quod`/`quia`/`quoniam`/`quandō` (540), concessive `quamquam`/`quamvis`/`licet`/`etsī`
(527), proviso `dum`/`modo`/`dummodo` (528), `antequam`/`priusquam` (551), `dum`/`dōnec`/`quoad`
(553–556), conditional protasis/apodosis classification (513–517), relative clause of purpose
(531.2), and the noun-clause `quod` of fact (572). Every one of these fires on
`mark`/`advmod` lemma ∈ closed-set **plus** the subordinate verb's `VerbForm=Fin` mood — i.e.
they need no lexicon beyond a ~40-word conjunction table and no semantics. Ship that table
first: it roughly doubles construction coverage for about a day of work, and it lights up
the parts of a sentence the reader most needs explained. The single **hardest** gap, by
contrast, is the ablative: A&G distinguishes 16 adverbal ablative uses (means, manner, cause,
respect, source, separation, degree of difference, quality, price, place where, time…) that
are morphologically **identical**; these need a lexical trigger table keyed on the governing
verb/adjective lemma plus a noun semantic class, and even then §418's own note admits cases
where "it is impossible to tell."

**Sources used.** All section numbers verified by extracting from the local DCC copies of
Allen & Greenough at `scratchpad/ag_*.htm` (syntax §§268–435, moods/tenses §§436–512,
subordinate clauses §§513–593, conditionals, indirect discourse, participles). The extraction
is contiguous and complete: §§268–593 with **zero missing section numbers**. Woodcock (*A New
Latin Syntax*, 1959) and Gildersleeve–Lodge (*Latin Grammar*, 3rd ed. 1895) are cited where
they name a construction A&G does not.

**Legend for detectability class:**

| Class | Meaning | Implementation cost |
|---|---|---|
| **M** | Morphology + dependency only. Deterministic, no word lists. | rule, ~10 lines |
| **L** | Needs a closed lexical trigger list (verb/adj/noun/conjunction lemmas). | rule + table |
| **L+** | Needs a trigger list *and* a semantic noun class (person/place/time/abstract). | rule + 2 tables |
| **S** | Genuinely ambiguous; surface-identical to a sibling construction. Report as a ranked set, never a single answer. | rule + confidence |

**Status column:** ✅ = one of our 28. ⬜ = missing.

---

## 1. Nominative and Vocative (A&G §§339–340)

| # | Construction | A&G | Status | Class | Detection recipe |
|---|---|---|---|---|---|
| 1 | Subject nominative | 339 | ⬜ | M | `Case=Nom` and `dep ∈ {nsubj, nsubj:pass, csubj}`. Trivial; worth emitting only as a hover-label, not a "construction". |
| 2 | Predicate nominative | 284 | ⬜ | M | `Case=Nom`, `dep ∈ {xcomp, ROOT-child}`, and a `cop` child on the head, **or** head lemma ∈ {sum, fio, videor, maneo, evado, exsisto, appareo, nascor, creor, deligor, habeor, putor, dicor, vocor, nominor, appellor}. Edge case: LatinCy attaches the predicate noun as `ROOT` and `sum` as `cop`, so look **down** from the copula's head, not up. |
| 3 | Nominative in exclamation | 339.a | ⬜ | S | `Case=Nom` in a sentence with no finite verb and terminal `!`. Confusable with an elliptical predicate nominative; low value. |
| 4 | Vocative of address | 340 | ⬜ | M | `Case=Voc` **or** `dep=vocative`. **Important edge case:** 2nd-decl. voc. sg. in *-e* is homographic with nothing else, but 1st-decl. voc. = nom., and LatinCy under-tags `Voc`. Fall back to: `dep=vocative` OR (`Case=Nom` AND a 2sg/2pl imperative or 2nd-person finite verb in the same clause AND the noun is not that verb's `nsubj`). |
| 5 | Nominative for vocative (appositive w/ imperative) | 340.a | ⬜ | S | Same trigger as #4 but tagged `Case=Nom`; report as a note on #4, not a separate card. |
| 6 | Vocative adjective for nominative (poetic) | 340.b | ⬜ | S | ADJ with `Case=Voc` whose head verb is 2nd person. Rare; poetry only. |

## 2. Genitive (A&G §§341–359)

| # | Construction | A&G | Status | Class | Detection recipe |
|---|---|---|---|---|---|
| 7 | Possessive genitive | 343 | ⬜ | S | `Case=Gen`, `dep=nmod`, head is NOUN. This is the **default** genitive: emit it only when no more specific genitive rule fires, at reduced confidence. Positive signal: head noun is concrete and the genitive is animate/proper (`ent=PERSON`). |
| 8 | Predicate genitive | 343.b | ⬜ | M | `Case=Gen` + `dep` attaches to a clause with `cop`/lemma `sum` and there is **no** nominal head for it to modify. e.g. *hominis est errāre*. Strong signal: infinitive subject + `sum` + bare genitive. |
| 9 | Appositional genitive | 343.d | ⬜ | L | `Case=Gen`, head noun lemma ∈ {nomen, vox, verbum, urbs, oppidum, flumen, arbor, virtus, genus, res}. e.g. *nōmen Mercuriī*. |
| 10 | Genitive of material | 344 | ⬜ | L+ | Head noun is a container/quantity (*acervus, pōculum, mōns, flūmen*) and dependent is a mass noun. Overlaps #11. |
| 11 | Genitive of quality / description | 345 | ⬜ | M | `Case=Gen` **with an `amod`/`nummod` child of its own**, modifying a noun. The obligatory adjective is the discriminator against possessive genitive — A&G 345 says quality genitive occurs "only when the quality is modified by an adjective." High precision. |
| 12 | Genitive of measure | 345.b | ⬜ | M | Special case of #11 where the modifier is `nummod` and head noun ∈ {longitudo, latitudo, altitudo, crassitudo, spatium} or the noun is *pedum/passuum/dierum/annorum*. |
| 13 | **Partitive genitive (genitive of the whole)** | 346 | ✅ | L | Have it. Extend: A&G 346.a lists the partitive words — {pars, nemo, nihil, quid, aliquid, satis, parum, plus, minus, multum, tantum, quantum, amplius} + neuter comparatives + `nummod`s + `mille/milia` + superlatives + {uterque, quisque, uter, nullus, solus} with pronouns (346.d). |
| 14 | Partitive after adjectives (poetic) | 346.b | ⬜ | S | ADJ head + `Case=Gen` dependent, poetry. e.g. *sancte deōrum*. |
| 15 | Objective genitive (with nouns) | 347–348 | ⬜ | L | Head noun is a **noun of action, agency, or feeling** — derivationally: `-tio/-sio/-tus/-or/-ntia/-ium` deverbals, plus {amor, metus, timor, spes, cupiditas, memoria, oblivio, studium, odium, cura, fuga, adventus, occasio}. Discriminates from #7 only lexically. |
| 16 | Subjective genitive | 343/347 | ⬜ | S | Same surface as #15. **Genuinely ambiguous**: *amor patris* = "father's love" or "love of the father". Emit both readings with equal confidence — this is exactly the kind of thing a reader tool should *show*, not resolve. |
| 17 | Genitive with adjectives (desire, knowledge, fullness, guilt…) | 349, 349.a | ⬜ | L | ADJ head with `Case=Gen` dependent, ADJ lemma ∈ closed list: {cupidus, avidus, studiosus, peritus, imperitus, gnarus, ignarus, memor, immemor, plenus, inops, particeps, expers, potens, impotens, similis, dissimilis, conscius, insons, reus, consultus, prudens, rudis, dives, egenus, fertilis, ferax, refertus}. |
| 18 | Genitive with participles in *-ns* used adjectivally | 349.b | ⬜ | M+L | `VerbForm=Part Tense=Pres` + `Case=Gen` dependent + the participle has no `obj`. e.g. *amāns patriae*. |
| 19 | Genitive of specification (poetic) | 349.d | ⬜ | S | Any ADJ + Gen not in list #17. Poetry only; low confidence. |
| 20 | **Genitive with verbs of remembering/forgetting** | 350 | ✅ | L | Have it (memini, obliviscor, reminiscor, recordor). Note 350.a–d: **acc. vs gen. is a sense distinction**, not a rule — flag both. |
| 21 | Genitive of the thing with verbs of reminding | 351 | ⬜ | L | Verb lemma ∈ {admoneo, commoneo, commonefacio, moneo} + `Case=Acc` (person) + `Case=Gen` (thing) both dependent on it. Edge case: a neuter pronoun goes in the accusative instead (351). |
| 22 | Genitive of the charge or penalty | 352 | ⬜ | L | Verb lemma ∈ {accuso, arguo, incuso, insimulo, damno, condemno, convinco, absolvo, libero, arcesso, postulo, defero} + `Case=Gen`. Common charges: {furtum, proditio, ambitus, maiestas, repetundae, capitis, pecuniae, sceleris, parricidii}. Note §353: `dē` + abl. is the competing construction. |
| 23 | **Genitive with impersonals of feeling** | 354.b | ✅ | L | Have it (miseret, paenitet, piget, pudet, taedet). |
| 24 | Genitive with verbs of pity | 354.a | ⬜ | L | Lemma ∈ {misereor, miseresco}. Small but distinct from #23 — personal, not impersonal. |
| 25 | Genitive with *interest* / *rēfert* | 355 | ⬜ | L | Verb lemma ∈ {interest, refert} + `Case=Gen` person. Edge case §355.a: with personal pronouns the **ablative fem. sg. possessive** (*meā, tuā, suā, nostrā, vestrā*) is used, not the genitive — a distinctive, teachable trap that our tool should catch explicitly. |
| 26 | Genitive with verbs of plenty and want | 356 | ⬜ | L | Lemma ∈ {egeo, indigeo, impleo, compleo, repleo, satio, abundo}. Note these usually take the **ablative** (§409.a) — flag the alternation. |
| 27 | Genitive with *potior* etc. | 357, 357.a | ⬜ | L | *potīrī rērum* is effectively a fixed phrase. Match lemma `potior` + lemma `res` in `Case=Gen`. |
| 28 | Genitive of indefinite value | 417 | ⬜ | L | `Case=Gen` of {magnus, parvus, tantus, quantus, plus, minor, nihilum, as, floccus, pilus, nauci} with a verb of valuing {aestimo, facio, habeo, duco, puto, sum}. Closed list; high precision. |
| 29 | Genitive of exclamation | 359.a | ⬜ | S | Bare `Case=Gen` in a verbless exclamation. Very rare (Graecism). |
| 30 | Genitive with *causā*, *grātiā*, *ergō*, *īnstar*, *tenus* | 359.b | ⬜ | M | `Case=Gen` immediately **preceding** lemma ∈ {causa, gratia, ergo, instar, tenus} in the ablative. Word order is part of the rule: *causā* and *grātiā* are postpositive. **This is also purpose** when the genitive is a gerund/gerundive (§504.b) — see #163. |
| 31 | Locative *animī* with verbs of feeling | 358 | ⬜ | L | Fixed: form `animi` + verb/adj of feeling. Looks like a genitive, **is** a locative — a good "gotcha" card. |

## 3. Dative (A&G §§360–385)

| # | Construction | A&G | Status | Class | Detection recipe |
|---|---|---|---|---|---|
| 32 | Dative of indirect object (transitive) | 361–362 | ⬜ | M | `Case=Dat`, `dep ∈ {obl:arg, iobj, obl}`, head is a verb that also has an `obj` in `Case=Acc`. The **presence of a direct object** is the discriminator against #34. |
| 33 | Dative retained with passive | 365, 369.a, 372 | ⬜ | M | `Case=Dat` + head verb `Voice=Pass`. §372: intransitives governing the dative go **impersonal** in the passive (*mihi persuādētur*) — detect as `Voice=Pass` + 3sg + no `nsubj`. |
| 34 | **Dative with special (intransitive) verbs** | 366–367 | ✅ | L | Have it. A&G 367's list: favor/help/please/trust + believe, persuade, command, obey, serve, resist, envy, threaten, pardon, spare. Verify our list includes: {faveo, studeo, indulgeo, ignosco, parco, placeo, displiceo, credo, confido, diffido, fido, noceo, obsum, prosum, servio, pareo, oboedio, obtempero, resisto, invideo, minor, irascor, suadeo, persuadeo, impero, medeor, nubo, supplico, satisfacio, gratulor, blandior, adulor}. §367.a is the trap list — {iuvo, adiuvo, laedo, iubeo, deficio, delecto} take the **accusative** despite meaning the same. |
| 35 | **Dative with compound verbs** | 370 | ⬜ | M+L | Verb lemma **prefixed** by {ad-, ante-, circum-, con-/com-, in-, inter-, ob-, post-, prae-, pro-, sub-, super-} AND has a `Case=Dat` dependent. This is near-**M**: the prefix is recoverable from the lemma string, so you need only a prefix table, not a verb list. Edge case §370.b: {adeo, aggredior, antecedo, antecello, obeo, oppugno, praecedo, convenio} became transitive → accusative. §371: when literal motion is meant, a preposition returns. |
| 36 | *Obvius* / *obviam* + dative | 370.c | ⬜ | L | Two lemmas; trivial. |
| 37 | **Dative of possession** | 373 | ✅ | M | Have it. `Case=Dat` + lemma `sum` + nominative subject. Edge case §373.a: *nōmen est* takes the name in the dative **by attraction** (*mihi nōmen est Gāiō*) — a distinct sub-card worth adding. §373.b: *dēsum/absum*. |
| 38 | **Dative of agent (with gerundive)** | 374 | ✅ | M | Have it. |
| 39 | Dative of agent with perfect participle | 375 | ⬜ | M | `Case=Dat` (usually animate/pronoun) + head is `VerbForm=Part Tense=Past Voice=Pass`, **not** a gerundive. Distinct from #38 and currently missed. |
| 40 | Dative with *videor* | 375.b | ⬜ | L | Lemma `videor` + `Case=Dat`. Very common in Cicero; one-line rule. |
| 41 | Dative of reference / advantage / disadvantage | 376–377 | ⬜ | S | `Case=Dat` attached to a clause with **no** governing verb from list #34 and **no** direct object relation. This is the residual dative. Report at ~0.5 confidence with the *dativus commodi/incommodi* gloss. |
| 42 | Dative of the person judging | 378 | ⬜ | L+ | `Case=Dat` animate (pronoun or `ent=PERSON`) + head is a predicate adjective of evaluation. e.g. *Quintiā fōrmōsa multīs*. |
| 43 | **Ethical dative** | 380 | ⬜ | M | `Case=Dat` **and** lemma ∈ {ego, tu, nos, vos} (personal pronouns only, per A&G 380) **and** the pronoun is not required by the verb's valency. Near-deterministic and a classic student stumbling-block: *quid mihi Celsus agit?* Cheap win. |
| 44 | Dative in colloquial exclamation / after interjections | 379, 379.a | ⬜ | M | `Case=Dat` in a verbless clause, or governed by an INTJ (*vae, ei, heu*). |
| 45 | Dative of separation | 381 | ⬜ | L | Verb of taking away {eripio, adimo, aufero, detraho, demo, subtraho, surripio, excutio} + `Case=Dat` of person. Distinctive because English and the ablative both push you the wrong way. |
| 46 | **Dative of purpose / end (*dativus finalis*)** | 382 | ✅ (as part of double dative) | M | We detect the **double** dative. Add the **single** purpose dative: `Case=Dat` of an abstract noun ∈ {auxilium, praesidium, subsidium, usus, cura, dolor, honor, odium, exemplum, argumentum, impedimentum, detrimentum, saluti, receptui, laudi, crimini, vitio} without a second dative. |
| 47 | **Double dative** | 382 | ✅ | M | Have it. |
| 48 | **Dative with adjectives** | 383–384 | ✅ | L | Have it. A&G 384: fitness, nearness, likeness, service, inclination + opposites. §385.a–c gives the competing constructions (`ad` + acc.; `in`/`ergā` + acc.; possessive genitive) — worth surfacing as "expected dative, got X". |
| 49 | Dative of direction (poetic) | 428.h | ⬜ | S | `Case=Dat` of a place noun + verb of motion, in verse. e.g. *it clāmor caelō*. Genuinely ambiguous with #41. |

## 4. Accusative (A&G §§386–397)

| # | Construction | A&G | Status | Class | Detection recipe |
|---|---|---|---|---|---|
| 50 | Direct object | 387 | ⬜ | M | `Case=Acc` + `dep=obj`. Hover-label only. |
| 51 | Accusative with verbs of feeling (*doleo, queror, horreo, maereo, lugeo, gemo, rideo, fleo*) | 388.a | ⬜ | L | Small closed list; teaches "apparently intransitive". |
| 52 | Accusative with compounds of *circum-, trāns-, praeter-* | 388.b | ⬜ | M | Prefix match on lemma + `obj`. Same prefix table as #35. |
| 53 | Accusative with impersonals *decet, dēdecet, dēlectat, iuvat, oportet, fallit, fugit, praeterit* | 388.c | ⬜ | L | 8 lemmas. The accusative here is the **logical subject** — a real comprehension trap. |
| 54 | Cognate accusative | 390 | ⬜ | M+L | `Case=Acc` + `dep=obj` where the object's lemma **shares a stem** with the verb lemma (*vītam vīvere, servitūtem servīre, pugnam pugnāre*). Implement as: strip verb lemma to first 4 chars of stem, compare with noun stem. Plus §390.a: verbs of taste/smell {oleo, sapio, redoleo} + acc. of quality. Plus §390.c: a neuter pronoun/indef. adj. as object of an intransitive (*id gaudeo, hoc te moneo*). |
| 55 | Predicate accusative (verbs of naming, making, esteeming) | 392–393 | ⬜ | L | Verb lemma ∈ {appello, voco, nomino, dico, creo, facio, reddo, habeo, duco, puto, existimo, iudico, declaro, designo, eligo, praesto, praebe​o, se praebere} + **two** `Case=Acc` dependents that agree in number/gender. Detection edge case: the pair test is `agrees(a, b, ("Case","Number"))` and one of them is the `obj`, the other an `xcomp`. §393.a: in the passive, both go nominative → link to #2. |
| 56 | Secondary object with compounded verbs | 394–395 | ⬜ | M | Two `Case=Acc` dependents that **do not** agree, head verb prefixed by trāns-/circum-/trā-. e.g. *Caesar cōpiās flūmen trādūxit*. |
| 57 | Double accusative with verbs of asking and teaching | 396 | ⬜ | L | Lemma ∈ {rogo, oro, posco, reposco, flagito, interrogo, doceo, edoceo, celo}. §396.a: {peto, quaero} instead take `ab/ex/dē` + abl. of person — a very common student error, worth an explicit "expected accusative, got prepositional phrase" card. §396.c: *cēlō* takes two accusatives. |
| 58 | Adverbial accusative | 397.a | ⬜ | L | Closed list of frozen forms: {multum, plus, plurimum, plerumque, ceterum, cetera, primum, postremum, id genus, quod si, nihil, aliquid, quid, magnam partem, maximam partem, vicem, partim, id temporis, secus, dulce, acerba}. Pure lookup. |
| 59 | **Greek / synecdochical accusative of respect** | 397.b | ✅ | M | Have it. |
| 60 | Middle-voice accusative | 397.c | ⬜ | S | `VerbForm=Part Voice=Pass` (or a passive verb) + `Case=Acc` object. e.g. *inūtile ferrum cīngitur*. Surface-identical to #59; A&G itself says the two analyses compete. **Report both.** |
| 61 | Accusative of exclamation | 397.d | ⬜ | M | `Case=Acc` in a verbless clause, often with *ō*, *ēn*, *ecce*, *prō*, or `!`. |
| 62 | Subject accusative of the infinitive | 397.e | ⬜ | M | `Case=Acc` whose head is `VerbForm=Inf` and which fills that infinitive's `nsubj` slot. Foundational to #180ff. |
| 63 | Accusative in apposition to a clause | 397.f | ⬜ | S | Rare, late. |
| 64 | **Accusative of extent (duration of time / space)** | 423, 425 | ✅ | L+ | Have it. Needs the time-noun class {annus, mensis, dies, hora, nox, aetas, hiems, aestas, biennium, triennium…} vs space nouns {pes, passus, milia, stadium, iugerum}. |
| 65 | **Accusative of place to which (no preposition)** | 427 | ✅ | L+ | Have it — names of towns/small islands + *domum, rūs*. Needs a toponym gazetteer; `ent=LOC` from LatinCy is a usable proxy but **under-recalls** on Perseus-era text. Recommend a static list from the Pleiades gazetteer (CC-BY, https://pleiades.stoa.org/downloads) intersected with the corpus. |
| 66 | Accusative of the end of motion in poetry (preposition omitted) | 428.g | ⬜ | S | `Case=Acc` + motion verb + no `case` child, where the noun is **not** a town name. Poetry-only; competes with #50. |
| 67 | *Ante diem* date formula | 424.g | ⬜ | M | Fixed pattern: `ante` + `diem` + ordinal + month name in acc. Deterministic and genuinely opaque to students. High teaching value, tiny rule. |
| 68 | Accusative of anticipation (prolepsis) | 576 | ⬜ | S | Object accusative of the matrix verb that is semantically the subject of a following indirect question. e.g. *nōstī Mārcellum quam tardus sit*. |

## 5. Ablative (A&G §§398–420) — the hard case

A&G groups 16 adverbal ablatives under three historical cases (ablative proper "from",
locative "in", instrumental "with/by", §398). **They are morphologically indistinguishable.**
Every rule below is therefore a *lexical trigger + noun-class* rule, and several are marked
**S** because A&G's own notes concede indeterminacy (see §418.a Note: "it is impossible to
tell whether *vīribus* is the means of the superiority or that in respect to which").

| # | Construction | A&G | Status | Class | Detection recipe |
|---|---|---|---|---|---|
| 69 | Ablative of separation | 400–402 | ⬜ | L | Verb/adj of separation, freeing, want: {libero, solvo, absolvo, levo, exonero, privo, spolio, nudo, orbo, fraudo, expello, pello, moveo, deicio, cedo, abstineo, desisto, careo, egeo, vaco} + `Case=Abl` with **no** `case` child, or with `ab/ex/dē`. §402.a: adjectives {liber, vacuus, nudus, orbus, inanis, expers, immunis, purus}. |
| 70 | Ablative of source | 403, 403.a | ⬜ | L | Participles of birth/origin {natus, ortus, genitus, editus, satus, cretus, prognatus, oriundus} + `Case=Abl`. Very high precision — a one-list rule. |
| 71 | Ablative of material | 403.b–d | ⬜ | L | Verb lemma ∈ {consto, consisto, contineo, facio, fio} + `Case=Abl` (usually with `ex`). |
| 72 | Ablative of cause | 404 | ⬜ | S | `Case=Abl` abstract noun (emotion/reason: {ira, metus, timor, amor, odium, dolor, gaudium, spes, desperatio, cupiditas, inopia, necessitas, casus, iussu, rogatu, permissu, natura, consuetudine}) with no preposition. Overlaps #77 (means) irreducibly. §404.a lists verbs that take bare causal abl.: {laboro, exsilio, exsulto, triumpho, lacrimo, ardeo}. |
| 73 | *causā* / *grātiā* of cause & purpose | 404.c | ⬜ | M | See #30 — same surface rule, different label depending on whether the genitive is a gerund(ive). |
| 74 | Ablative of agent (`ā`/`ab` + abl.) | 405 | ⬜ | M | `dep=obl:agent`, or `Case=Abl` + `case` child lemma ∈ {a, ab, abs} + head `Voice=Pass`. **Deterministic.** Should be trivially added; it is the natural partner of our existing dative-of-agent detector and students constantly confuse the two. §405.b: *per* + acc. = intermediary, not agent — flag the contrast. |
| 75 | **Ablative of comparison** | 406 | ✅ | M | Have it. Check we implement §407.b: with a general negative, the ablative rather than *quam* is regular; and §407.c: after *plūs/minus/amplius/longius* the measure word keeps its own case with no *quam*. |
| 76 | Comparison with *quam* | 407 | ⬜ | M | `quam` + the two compared items in the same case. Worth detecting as the *sibling* of #75 so the tool can say "this could have been an ablative of comparison". |
| 77 | Ablative of means / instrument | 409 | ⬜ | S | `Case=Abl` inanimate, no preposition, head is a verb. **The residual instrumental.** Emit at ~0.45 when no other ablative rule fires and the noun is inanimate. §409.a: verbs/adjs of filling {compleo, impleo, repleo, abundo, affluo, plenus, refertus, onustus} take the ablative of means. |
| 78 | **Ablative with the five deponents (*ūtor, fruor, fungor, potior, vescor*)** | 410 | ✅ | L | Have it. Add their compounds: {abutor, deutor, perfruor, defungor, perfungor}. |
| 79 | Ablative with *opus est* / *ūsus est* | 411 | ⬜ | M | Lemma ∈ {opus, usus} + `sum` + `Case=Abl`. §411.a: abl. of a perfect participle (*mātūrātō opus est*). §411.b: *opus* can also take a nominative subject — flag the alternation. |
| 80 | Ablative of manner | 412 | ⬜ | M+L | `Case=Abl` + `case` child `cum`, **or** bare abl. when the noun carries an `amod` (§412: *cum* is dropped when an adjective modifies), **or** the noun ∈ frozen set {modo, pacto, ratione, ritu, vi, via, silentio, iure, iniuria, casu, consilio, ordine, more}. |
| 81 | Ablative of accompaniment | 413 | ⬜ | M | `Case=Abl` **animate** + `case` child `cum`. The animacy test (`ent=PERSON`/`NORP`, or a human-noun list) is the only thing separating this from #80. §413.a: military phrases drop *cum* (*omnibus cōpiīs*) — detect via head verb of motion + `copiis/exercitu/legionibus`. |
| 82 | Ablative of degree of difference | 414 | ⬜ | M | `Case=Abl` + head is a comparative (use our existing `Tok.degree()` heuristic) or a word implying comparison {ante, post, supra, infra, plus, minus, prior, superior}. Very common with {multo, paulo, aliquanto, tanto, quanto, nihilo, quo…eo}. **Near-deterministic and currently missing.** |
| 83 | Correlative *quō … eō / quantō … tantō* | 414.a | ⬜ | M | Both ablatives present, both heads comparative. Distinct card; explains "the more … the more". |
| 84 | Ablative of quality / description | 415 | ⬜ | M | `Case=Abl` with an obligatory `amod`/`nmod` modifier, modifying a **noun** (not a verb). Same shape as the genitive of quality #11 — the tool should say "abl. or gen. of quality both possible here" per §415.a. |
| 85 | Ablative of price | 416 | ⬜ | L | Verb of buying/selling/valuing {emo, vendo, veneo, sto, consto, conduco, loco, muto, commuto, permuto, verto, aestimo, liceor} + `Case=Abl`. §417.c: *tantī/quantī/plūris/minōris* stay genitive → link #28. |
| 86 | **Ablative of specification / respect** | 418 | ⬜ | M+S | `Case=Abl` inanimate + head is an ADJ or a verb of excelling/differing {praesto, praecedo, supero, differo, disto, antecedo, valeo}. Also *nātū* (fixed), and §418.b **{dīgnus, indīgnus}** take the ablative — a one-line rule with high student value. Currently missing entirely, and it is one of the most frequent ablatives in Cicero. |
| 87 | **Ablative absolute (participial)** | 419 | ✅ | M | Have it (`advcl:abs`). |
| 88 | **Ablative absolute (nominal / adjectival)** | 419.a | ✅ | M | Have it — *Cicerōne cōnsule*, *mē vīvō*. |
| 89 | Ablative absolute with clause as subject | 419.b | ⬜ | M | Participle in abl. with a `ccomp`/`csubj` child rather than a nominal. e.g. *audītō eum vēnisse*. |
| 90 | Impersonal ablative absolute (no substantive) | 419.c | ⬜ | M | A lone `Case=Abl` participle/adjective, neuter sg., `dep=advcl:abs` with no nominal sibling: {auspicātō, sortītō, cōnsultō, explōrātō, serēnō, nūbilō}. Closed list; add to our existing detector. |
| 91 | Ablative absolute replacing a subordinate clause (temporal/causal/concessive/conditional) | 420 | ⬜ | S | Our detector fires but does not **classify** the relation. A&G 420 enumerates four readings. Recommend emitting all four as ranked interpretations rather than picking one — this is a genuine ambiguity and exactly the kind of thing a reading tool should teach. |
| 92 | **Ablative of time when / within which** | 423 | ✅ | L+ | Have it. Note `dep=obl:tmod` / `advmod:tmod` exists in the Latin UD treebanks and is a strong extra signal. |
| 93 | Ablative of duration (rare) | 424.b | ⬜ | S | Competes with #64. |
| 94 | Ablative of place where (no preposition) | 429 | ⬜ | L+ | Bare `Case=Abl` place noun. §429: restricted to (a) nouns modified by *tōtus/omnis/medius*, (b) *locō/locīs/parte/partibus*, (c) *terrā marīque*, (d) poetry. Encode the four sub-rules; otherwise the preposition (`in`) is required. |
| 95 | Ablative of the way by which | 429.a | ⬜ | L | Nouns {via, iter, porta, ponte, flumine, mari, terra} + motion verb. |
| 96 | Ablative of place from which | 426.1, 428.f | ⬜ | M | `case` child ∈ {a, ab, de, ex, e} + `Case=Abl`; or the bare-abl. idioms of §428.f. |
| 97 | Ablative with *frētus, contentus, laetus* | 431.a | ⬜ | L | Three lemmas. |
| 98 | Ablative with *acquiēscō, dēlector, laetor, gaudeō, glōrior, nītor, stō, maneō, fīdō, cōnfīdō, cōnsistō, contineor* | 431 | ⬜ | L | Twelve lemmas; A&G calls it "locative ablative". |
| 99 | **Locative case** | 427, 427.a | ✅ | M+L | Have it. §427.a extras: {domi, humi, ruri, belli, militiae, vesperi, animi, foris, temperi}. |

---

## 6. Moods — independent uses (A&G §§437–450)

Our single `subjunctive_independent` detector collapses this whole block into a
**person-based guess** (`Person=1 & Plur` → hortatory, `Person=3` → jussive, else
"optative or potential"). Two concrete defects, both confirmed by reading
`server/enarratio/constructions.py:1224–1258`:

1. It requires `t.dep == "ROOT"`, so a main-clause subjunctive in a **coordinated** clause
   (`dep == "conj"`) is silently dropped. Fix: `t.dep in ("ROOT", "conj")` **and** the head
   chain contains no `mark`.
2. It never checks for `utinam`, which is the *decisive* optative marker (§442). Adding a
   `utinam / utinam nē / ō sī / velim / vellem` child test would turn the weakest branch
   ("Optative or Potential", conf. 0.7) into a near-certain classification.

| # | Construction | A&G | Status | Class | Detection recipe |
|---|---|---|---|---|---|
| 100 | Hortatory subjunctive (1pl) | 439 | ✅ (partial) | M | `Mood=Sub Tense=Pres Person=1 Number=Plur`, main clause, negative `nē`. |
| 101 | Jussive subjunctive (3rd person) | 439 | ✅ (partial) | M | `Mood=Sub Person=3`, main clause, negative `nē`. |
| 102 | Hortatory of indefinite 2nd person | 439.a | ⬜ | S | `Person=2 Number=Sing` generic. Ambiguous with potential #106. |
| 103 | Subjunctive of unfulfilled past obligation | 439.b | ⬜ | M | `Mood=Sub Tense=Imp/Pqp` in a main clause with `nē` or in a *why-didn't-you* context. |
| 104 | Concessive subjunctive | 440 | ⬜ | M | `Mood=Sub Tense=Pres/Perf`, main clause, often with *sānē*, *licet*, followed by a *sed/tamen/at* clause. The `sed`/`tamen` continuation is the reliable signal. |
| 105 | Optative subjunctive (wish) | 441–442 | ⬜ | M | **Decisive rule:** `Mood=Sub` + a child or preceding token with lemma ∈ {utinam, uti, ut, o, si} in a main clause. Tense carries the meaning: Pres = possible wish, Imp = unaccomplished in present, Pqp = unaccomplished in past (§441). Negative `nē`. Also §442.b: *velim/vellem* + subjunctive. This is a **one-token lookup** and should be added immediately. |
| 106 | Potential subjunctive | 445–447 | ⬜ | M | `Mood=Sub`, main clause, negative **`nōn`** (not `nē`) — the negative is the discriminator against #100/#101/#105. Also §447.a: `forsitan` + subjunctive is regularly potential; `fortasse` (§447.b) takes the **indicative**. Common frozen forms: *velim, nōlim, mālim, dīxerit quis, crēdās, putēs, cernerēs, vidērēs*. |
| 107 | Deliberative subjunctive | 443–444 | ✅ (partial) | M | `Mood=Sub` in an interrogative main clause; negative **`nōn`**. Our rule fires only on `Person=1 Number=Sing` and does **not** check for a question — add `?` / `-ne` / interrogative-word test, and allow 2nd person (*quid facerēs?*). §485.g: the deliberative is **exempt from sequence of tenses**. |
| 108 | Imperative (present) | 448 | ⬜ | M | `Mood=Imp`. Trivial; hover-label. |
| 109 | Future imperative in *-tō/-tōte* | 449 | ⬜ | M | `Mood=Imp Tense=Fut`. §449.a: {scio, memini, habeo} regularly use it. Legal/formulaic register — good commentary hook. |
| 110 | Prohibition: *nōlī* + inf. | 450.1 | ⬜ | M | lemma `nolo` `Mood=Imp` + `xcomp` infinitive. |
| 111 | Prohibition: *cavē* + pres. subj. | 450.2 | ⬜ | M | lemma `caveo` + `Mood=Sub`. |
| 112 | Prohibition: *nē* + perf. subj. | 450.3 | ⬜ | M | `ne` + `Mood=Sub Tense=Perf` in a main clause. Distinct from #101 by tense + person. |
| 113 | Prohibition: *nē* + pres. imperative (poetic/early) | 450.a | ⬜ | M | `ne` + `Mood=Imp`. Register marker worth flagging in verse. |

## 7. The infinitive (A&G §§451–463)

| # | Construction | A&G | Status | Class | Detection recipe |
|---|---|---|---|---|---|
| 114 | Infinitive as subject | 452 | ⬜ | M | `VerbForm=Inf` + `dep=csubj` (or `nsubj` of `sum`). |
| 115 | Infinitive as predicate nominative / in apposition | 452 | ⬜ | M | Two infinitives joined by `sum`. e.g. *docto homini vivere est cogitare*. |
| 116 | Infinitive with impersonals (*libet, licet, oportet, decet, placet, necesse est, opus est*) | 454–455 | ⬜ | L | ~15 lemmas + `xcomp/csubj` infinitive. §455.a: predicate noun/adj goes **accusative**, except with *licet* where it goes **dative** — a lovely, teachable, purely lexical exception. |
| 117 | Complementary infinitive | 456 | ⬜ | L | `VerbForm=Inf` + `dep=xcomp` + head lemma ∈ {possum, debeo, audeo, coepi, incipio, desino, soleo, conor, statuo, constituo, decerno, cupio, volo, nolo, malo, paro, disco, scio, nescio, memini, obliviscor, pergo, contendo, studeo, dubito, veror}. **No subject accusative** — that is the discriminator against #118. |
| 118 | Predicate noun/adj after complementary inf. takes the case of the main subject | 458 | ⬜ | M | `Case=Nom` predicate under an `xcomp` infinitive. A precise, checkable rule. |
| 119 | Infinitive of purpose (poetic / with *habeō, dō, ministrō*) | 460, 460.a, 460.c | ⬜ | S | `VerbForm=Inf` + motion verb, no complementary-verb lemma. In classical prose this is *ungrammatical*, so detecting it is a genre marker: flag "poetic infinitive of purpose". |
| 120 | Infinitive with adjectives (Graecism) | 461 | ⬜ | S | ADJ + `xcomp` infinitive. Poetry (*audāx omnia perpetī*). |
| 121 | Infinitive of result (poetic) | 461.a | ⬜ | S | Rare. |
| 122 | Infinitive of exclamation | 462 | ⬜ | M | `VerbForm=Inf` + subject accusative, no governing verb, `!` or *-ne*. e.g. *tē in tantās aerumnās incidere!* |
| 123 | **Historical infinitive** | 463 | ⬜ | M | `VerbForm=Inf Tense=Pres` + a **nominative** subject + `dep=ROOT/conj`. The nominative subject is decisive: everywhere else an independent infinitive takes an accusative subject. Very common in Sallust/Tacitus narrative and a guaranteed student stumble. §485.f: it takes **secondary** sequence. **Cheap, deterministic, high value — add it.** |

## 8. Tense usage and sequence (A&G §§464–486)

These are not "constructions" a detector highlights so much as **notes attached to a verb**,
but they are exactly what a reading tool should whisper.

| # | Phenomenon | A&G | Status | Class | Detection recipe |
|---|---|---|---|---|---|
| 124 | Present of general truth (gnomic) | 465 | ⬜ | S | Semantic. |
| 125 | Present for continued past action with *iam diū / iam dūdum / iam prīdem* | 466 | ⬜ | M | `Tense=Pres` + adverb ∈ {diu, dudum, pridem} preceded by `iam`. Deterministic, and the English requires a **perfect** — a real translation trap. |
| 126 | Conative present | 467 | ⬜ | S | Semantic. |
| 127 | Historical present | 469 | ⬜ | S | `Tense=Pres` in a narrative context with past-tense neighbours. Heuristic: a `Tense=Pres Mood=Ind` verb in a sentence/paragraph whose other main verbs are `Tense=Perf`. §485.e: sequence can go either way after it. |
| 128 | Annalistic present | 469.a | ⬜ | S | Sub-type of #127. |
| 129 | Inceptive / conative imperfect | 471.c | ⬜ | S | Semantic. |
| 130 | Imperfect of surprise ("so you were…!") | 471.d | ⬜ | S | Needs discourse context. |
| 131 | Perfect definite vs historical (aoristic) perfect | 473 | ⬜ | S | **Genuinely ambiguous by design** — the same form. Report both English renderings. This is one of the highest-value "explain, don't decide" cards in the whole taxonomy. |
| 132 | Gnomic perfect | 475 | ⬜ | S | Semantic. |
| 133 | Preteritive verbs (*ōdī, meminī, nōvī, cōnsuēvī*) — perfect form, present meaning | 476 | ⬜ | L | Four lemmas + {coepi, didici, consuevi}. Pure lookup, and a guaranteed misreading otherwise. **Add it.** |
| 134 | Epistolary tenses | 479 | ⬜ | S | Genre-conditioned (letters). |
| 135 | Sequence of tenses (primary vs secondary) | 482–485 | ⬜ | M | Fully computable: classify the matrix verb's tense as primary {Pres, Fut, FutPerf, Perf-definite} or secondary {Imp, Pqp, Perf-historical}, then check the subordinate subjunctive is Pres/Perf (primary) or Imp/Pqp (secondary). **This is a validator, not a detector** — its value is flagging *violations* (§485.a–j lists the licensed exceptions). Worth building because a violation is almost always a signal the parse is wrong. |
| 136 | Periphrastic future subjunctive (*-ūrus sim / essem*) in indirect question | 575.a | ⬜ | M | `VerbForm=Part Tense=Fut` + `sum` in `Mood=Sub`. Fills the gap where Latin has no future subjunctive. Deterministic. |
| 137 | Present infinitive with *dēbuī, oportuit, potuī* where English wants a perfect | 486.a | ⬜ | L | Matrix lemma ∈ {debeo, oportet, possum, licet, decet} in `Tense=Perf/Imp` + present infinitive. Deterministic given the lemma list, and the mistranslation is near-universal among students. |


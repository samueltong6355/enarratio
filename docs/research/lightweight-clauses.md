# Lightweight clause rules — 2026-10-07

`server/enarratio/clauses.py` implements the eleven priority clause families from the
earlier syntax survey, plus a tentative poetic dative of direction. Rules require a
dependency relationship and a finite predicate (including a copular child), not merely
the presence of a conjunction anywhere in the sentence. They operate entirely offline.

Sources: Allen & Greenough, as edited by Meagan Ayer at Dickinson College Commentaries.
Primary pages checked for this revision include:

- [Substantive purpose, §563](https://dcc.dickinson.edu/grammar/latin/substantive-clauses-purpose)
- [Substantive result, §§567–571](https://dcc.dickinson.edu/grammar/latin/substantive-clauses-result)
- [Causal clauses, §540](https://dcc.dickinson.edu/grammar/latin/causal-clauses)
- [Concessive clauses, §527](https://dcc.dickinson.edu/grammar/latin/concessive-clauses)
- [Proviso, §528](https://dcc.dickinson.edu/grammar/latin/clauses-proviso)
- [Temporal clauses](https://dcc.dickinson.edu/grammar/latin/temporal-clauses)
- [Conditional sentences, §§513 onward](https://dcc.dickinson.edu/grammar/latin/conditional-sentences)
- [Substantive quod, §572](https://dcc.dickinson.edu/grammar/latin/indicative-quod)

Hindering/doubt (§§558–559), relative purpose (§531.2), and directional dative (§428.h)
also use the section mapping in [the prior survey](syntax-taxonomy.md). These are bounded
heuristics, not exhaustive grammar coverage. Explanations are original summaries, not
copied commentary.

Important limits:

- `dum` + subjunctive keeps both proviso and anticipated temporal interpretations.
- A relative subjunctive after sending/choosing can be purpose or characteristic.
- A directional dative requires a place candidate and motion governor, but verse is not
  established by the detector; it is explicitly tentative.
- `quod` must be a clause marker, not a relative pronoun object. Complement vs causal
  readings still inherit parser uncertainty.
- `quin` is restricted to negatively marked governing expressions here; rhetorical
  questions and other virtually negative expressions are not yet covered.
- Split `prius … quam`, unmarked complements, richer conditional tense classification,
  and exhaustive governor lists remain future extensions.
- Specialized complement readings suppress a generic purpose/result label at the same
  anchor. Other genuine competing interpretations remain visible.

Tests include controlled positive/negative syntax fixtures and live LatinCy examples.
Passing fixtures proves implementation behavior, not accuracy over all Latin literature.

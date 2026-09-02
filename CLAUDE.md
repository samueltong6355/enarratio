# Enarratio — working agreement

A local-first Latin reading environment that fully explains a pasted passage.

## Read this first

**[`docs/STATE.md`](docs/STATE.md) is the pickup point.** It records what is built, what is
half-built, what is next, and which decisions are already settled. Read it before planning
anything. Update it before you stop.

Run `./scripts/status.sh` for a live status readout (git log, tests, data files, servers).

## Session-limit protocol — this project keeps hitting one

Two research sweeps have been killed mid-flight by the usage ceiling, losing 1.36M tokens of
subagent work between them. The lesson is now a rule:

1. **Write to disk as you discover, never at the end.** A subagent's return value is the
   least durable thing it produces — a killed agent returns nothing, but its files survive.
   The second sweep recovered 1,710 lines of research this way from a run that reported
   total failure.
2. **Commit early and often.** Every meaningful increment gets its own commit and push.
   Samuel asked for this explicitly; it is also what makes a hard stop survivable.
3. **Update `docs/STATE.md` before the context runs out**, not after. Treat it as the
   handoff you would want if you were shut off mid-sentence.
4. Prefer several small workflows over one large fan-out. Six agents was still too many.

## Invariants — do not violate without saying so

- **Deterministic layers state facts; generative layers only phrase them.** Morphology,
  syntax, scansion and lexicon come from real parsers and real dictionaries. A language
  model may put that analysis into prose; it may not invent a grammatical claim.
- **Never gate on grammaticality.** Agreement checking flags 5 of 6 modifiers in the opening
  of the *Aeneid*. Anomalies are reported on the token, never as a refusal. This is a
  deliberate, measured departure from the original brief — see `docs/research/empirical-probe-latincy.md`
  Finding 8 before revisiting it.
- **Every grammatical claim cites Allen & Greenough** and reports the evidence that produced
  it, so a wrong detection is visibly wrong rather than authoritative.
- **Show ambiguity, don't hide it.** Latin morphology is genuinely ambiguous; the interface
  shows competing readings with probabilities.
- Nothing leaves the machine. The server binds to localhost.

## Environment

- Python **3.12** in `.venv` (not 3.13+; the spaCy stack has no wheels). `uv` manages it.
- `data/` holds large, separately licensed corpora and is **gitignored** — never vendor it.
  `data/morpheus-quantities.db` (94 MB) supplies vowel quantities for scansion.
- Tests: `PYTHONPATH=server .venv/bin/python -m pytest server/tests -q`
- Run both servers: `./run.sh`

## Style

Prose in explanations is for a student translating a hard passage: precise, unhedged, and
never fabricating English inflections ("gero-ed" helps nobody — name the dictionary sense).
Commit messages explain *why*, and record measurements that forced a decision.

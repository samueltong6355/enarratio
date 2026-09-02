import { useMemo, useState } from "react";
import { analyse, type Analysis, type Construction, type ScanLine, type Token } from "./api";
import "./App.css";

const SAMPLES: { label: string; text: string }[] = [
  {
    label: "Caesar, BG 1.1",
    text: "Gallia est omnis divisa in partes tres, quarum unam incolunt Belgae, aliam Aquitani, tertiam qui ipsorum lingua Celtae, nostra Galli appellantur.",
  },
  {
    label: "Vergil, Aeneid 1.1",
    text: "Arma virumque cano, Troiae qui primus ab oris Italiam fato profugus Laviniaque venit litora.",
  },
  {
    label: "Caesar, ablative absolute",
    text: "His rebus gestis Caesar in citeriorem Galliam profectus est.",
  },
  {
    label: "Cicero, Catiline",
    text: "Quo usque tandem abutere, Catilina, patientia nostra?",
  },
];

function confidenceLabel(c: number): string {
  if (c >= 0.85) return "high";
  if (c >= 0.7) return "moderate";
  return "tentative";
}

export default function App() {
  const [text, setText] = useState(SAMPLES[2].text);
  const [data, setData] = useState<Analysis | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    setSelected(null);
    try {
      setData(await analyse(text));
    } catch (e) {
      setError(
        e instanceof Error
          ? `${e.message}. Is the server running? \`uvicorn enarratio.app:app\``
          : String(e),
      );
    } finally {
      setBusy(false);
    }
  }

  const token = selected !== null ? data?.tokens[selected] : null;
  const tokenConstructions = useMemo(
    () =>
      token
        ? (data?.constructions ?? []).filter((c) => c.tokens.includes(token.i))
        : [],
    [token, data],
  );

  return (
    <div className="app">
      <header>
        <h1>
          Enarratio<span className="sub">Latin, fully explained</span>
        </h1>
      </header>

      <section className="input">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          spellCheck={false}
          placeholder="Paste a Latin excerpt…"
          rows={4}
        />
        <div className="controls">
          <button onClick={run} disabled={busy || !text.trim()}>
            {busy ? "Analysing…" : "Analyse"}
          </button>
          <div className="samples">
            {SAMPLES.map((s) => (
              <button
                key={s.label}
                className="link"
                onClick={() => {
                  setText(s.text);
                  setData(null);
                }}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
        {error && <p className="error">{error}</p>}
      </section>

      {data && !data.gate.isLatin && (
        <section className="reject">
          <h2>This does not appear to be Latin</h2>
          <p>{data.gate.message}</p>
          <dl className="signals">
            <div>
              <dt>Morphologically analysable</dt>
              <dd>{(data.gate.analysableRate * 100).toFixed(0)}%</dd>
              <small>genuine Latin scores at least 86%</small>
            </div>
            {data.gate.linguaLatin !== null && (
              <div>
                <dt>Language identification</dt>
                <dd>{(data.gate.linguaLatin * 100).toFixed(1)}% Latin</dd>
                {data.gate.competingLanguage && (
                  <small>reads as {data.gate.competingLanguage}</small>
                )}
              </div>
            )}
          </dl>
          {data.gate.unrecognised.length > 0 && (
            <p className="muted">
              Unrecognised: {data.gate.unrecognised.slice(0, 12).join(", ")}
            </p>
          )}
        </section>
      )}

      {data && data.gate.isLatin && (
        <div className="workspace">
          <main>
            {data.gate.message && (
              <p className="notice">{data.gate.message}</p>
            )}
            <div className="passage">
              {data.tokens.map((t) => (
                <TokenSpan
                  key={t.i}
                  token={t}
                  selected={selected === t.i}
                  highlighted={
                    hovered !== null && t.constructions.includes(hovered)
                  }
                  onClick={() => setSelected(t.i === selected ? null : t.i)}
                />
              ))}
            </div>

            {data.scansion && <ScansionPanel lines={data.scansion} />}

            {data.constructions.length > 0 && (
              <section className="constructions">
                <h2>Constructions in this passage</h2>
                <ul>
                  {data.constructions.map((c, idx) => (
                    <li
                      key={`${c.key}-${idx}`}
                      onMouseEnter={() => setHovered(c.key)}
                      onMouseLeave={() => setHovered(null)}
                      onClick={() => setSelected(c.anchor)}
                    >
                      <div className="crow">
                        <strong>{c.name}</strong>
                        <span className={`conf ${confidenceLabel(c.confidence)}`}>
                          {confidenceLabel(c.confidence)}
                        </span>
                        <cite>{c.grammarRef}</cite>
                      </div>
                      <div className="cwords">
                        {c.tokens.map((i) => data.tokens[i]?.text).join(" ")}
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {data.gate.anomalies.length > 0 && (
              <section className="anomalies">
                <h2>Irregularities noted</h2>
                <p className="muted">
                  These do not block analysis. In verse they usually mean the
                  parser attached a word to the wrong head, not that the Latin is
                  faulty.
                </p>
                <ul>
                  {data.gate.anomalies.map((a, i) => (
                    <li key={i}>
                      <strong>{a.message}</strong>
                      {a.likelyBenign && <p>{a.likelyBenign}</p>}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </main>

          <aside>
            {!token && (
              <div className="placeholder">
                <p>Click any word to see its full analysis.</p>
                <p className="muted">
                  Words with a coloured underline take part in a syntactic
                  construction.
                </p>
              </div>
            )}
            {token && (
              <TokenPanel token={token} constructions={tokenConstructions} />
            )}
          </aside>
        </div>
      )}
    </div>
  );
}

function TokenSpan({
  token,
  selected,
  highlighted,
  onClick,
}: {
  token: Token;
  selected: boolean;
  highlighted: boolean;
  onClick: () => void;
}) {
  if (!token.isWord) {
    return <span className="punct">{token.text + token.whitespace}</span>;
  }
  const cls = [
    "tok",
    selected ? "sel" : "",
    highlighted ? "hl" : "",
    token.constructions.length ? "inconstr" : "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <>
      <button className={cls} onClick={onClick} title={token.description}>
        {token.text}
      </button>
      {token.whitespace}
    </>
  );
}

function TokenPanel({
  token,
  constructions,
}: {
  token: Token;
  constructions: Construction[];
}) {
  const entry = token.lexicon[0];
  const alternatives = token.rankedReadings.filter((r) => r.probability < 0.9);
  const top = token.rankedReadings[0];

  return (
    <div className="panel">
      <h2 className="word">{token.text}</h2>
      <p className="parse">{token.description}</p>
      {token.gloss && <p className="gloss">{token.gloss}</p>}

      {entry && (
        <section>
          <h3>Dictionary</h3>
          <p className="headword">
            <strong>{entry.headword}</strong>
            {entry.principalParts.length > 0 && (
              <span className="pp">
                {" "}
                ({entry.principalParts.filter(Boolean).join(", ")})
              </span>
            )}
          </p>
          {entry.glosses.length > 0 && (
            <p>{entry.glosses.join("; ")}</p>
          )}
          <ul className="meta">
            {entry.declension && <li>{entry.declension}</li>}
            {entry.gender && <li>{entry.gender}</li>}
            {entry.frequency && <li>{entry.frequency}</li>}
            {entry.age && <li>{entry.age}</li>}
          </ul>
        </section>
      )}

      {token.caseForce && (
        <section>
          <h3>What this case does</h3>
          <p>{token.caseForce}</p>
        </section>
      )}

      {constructions.length > 0 && (
        <section>
          <h3>Syntax in this context</h3>
          {constructions.map((c, i) => (
            <div className="constr" key={i}>
              <div className="crow">
                <strong>{c.name}</strong>
                <cite>{c.grammarRef}</cite>
              </div>
              <p className="latin-name">{c.latinName}</p>
              <p>{c.explanation}</p>
              <p className="hint">
                <em>Translate:</em> {c.translationHint}
              </p>
              <details>
                <summary>Why this was identified ({confidenceLabel(c.confidence)} confidence)</summary>
                <p>{c.evidence}</p>
                {c.caveat && <p className="caveat">{c.caveat}</p>}
              </details>
            </div>
          ))}
        </section>
      )}

      {alternatives.length > 0 && top && (
        <section>
          <h3>Competing readings</h3>
          <p className="muted">
            This form is ambiguous. The parser weighs the context as follows.
          </p>
          <ul className="readings">
            {token.rankedReadings.map((r, i) => (
              <li key={i} className={i === 0 ? "win" : ""}>
                <span className="bar" style={{ width: `${r.probability * 100}%` }} />
                <span className="pct">{(r.probability * 100).toFixed(0)}%</span>
                <span className="desc">{r.description}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {token.possibleReadings.length > 1 && (
        <section>
          <h3>Every form this could be</h3>
          <p className="muted">
            All analyses the morphological engine allows, regardless of context.
          </p>
          <ul className="ww">
            {token.possibleReadings.map((p, i) => (
              <li key={i}>
                <strong>{p.headword ?? p.lemma}</strong>
                {p.case && <span> · {p.case}</span>}
                {p.number && <span> {p.number}</span>}
                {p.stem && p.ending && (
                  <span className="split">
                    {" "}
                    ({p.stem}<b>{p.ending}</b>)
                  </span>
                )}
                {p.meaning && <div className="mean">{p.meaning}</div>}
              </li>
            ))}
          </ul>
        </section>
      )}

      <details className="raw">
        <summary>Parser detail</summary>
        <dl>
          <dt>lemma</dt><dd>{token.lemma}</dd>
          <dt>part of speech</dt><dd>{token.posName}</dd>
          <dt>dependency</dt><dd>{token.dep}</dd>
          <dt>features</dt>
          <dd>
            {Object.entries(token.morph)
              .map(([k, v]) => `${k}=${v}`)
              .join(" | ") || "—"}
          </dd>
        </dl>
      </details>
    </div>
  );
}


function ScansionPanel({ lines }: { lines: ScanLine[] }) {
  const scanned = lines.filter((l) => l.ok);
  if (!scanned.length) return null;
  return (
    <section className="scansion">
      <h2>Metre</h2>
      {lines.map((l, i) => (
        <div className="scanline" key={i}>
          {!l.ok ? (
            <>
              <div className="verse plain">{l.line}</div>
              <p className="muted">{l.note}</p>
            </>
          ) : (
            <>
              <div className="verse">
                {(() => {
                  // Walk the syllables in their original order so an elided syllable stays
                  // where it was written -- it is still on the page, and the reader needs to
                  // see which one vanished. Grouping by foot alone would move them all to
                  // the end of the line.
                  const footOf = new Map<number, number>();
                  l.feet.forEach((f) => f.syllables.forEach((si) => footOf.set(si, f.n)));
                  const groups: { foot: number | null; idx: number[] }[] = [];
                  l.syllables.forEach((_s, si) => {
                    const f = footOf.get(si) ?? null;
                    const last = groups[groups.length - 1];
                    if (last && (f === null || last.foot === f)) last.idx.push(si);
                    else groups.push({ foot: f, idx: [si] });
                  });
                  return groups.map((g, gi) => (
                    <span className={`foot ${g.foot ? "in" : "out"}`} key={gi}>
                      {g.idx.map((si) => {
                        const s = l.syllables[si];
                        const mark =
                          s.elided ? "" :
                          s.quantity === "anceps" ? "\u00D7" :
                          s.quantity === "long" ? "\u00AF" :
                          s.quantity === "short" ? "\u02D8" : "";
                        return (
                          <span
                            className={`syl${s.elided ? " elided" : ""}`}
                            key={si}
                            title={s.elided ? "elided — not counted in the metre" : s.reason}
                          >
                            <span className="mark">{mark}</span>
                            <span className="syltext">{s.text}</span>
                          </span>
                        );
                      })}
                    </span>
                  ));
                })()}
              </div>
              <div className="metrics">
                <code>{l.pattern}</code>
                {l.caesurae
                  .filter((c) => c.name === "penthemimeral" || c.kind === "diaeresis")
                  .slice(0, 1)
                  .map((c, k) => (
                    <span key={k} className="cae" title={c.note}>
                      {c.name} caesura after &lsquo;{c.after}&rsquo;
                    </span>
                  ))}
              </div>
              {l.elisions.map((e, k) => (
                <p className="elision" key={k}>
                  {e}
                </p>
              ))}
            </>
          )}
        </div>
      ))}
    </section>
  );
}

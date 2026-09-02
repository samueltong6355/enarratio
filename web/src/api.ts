export interface Reading {
  probability: number;
  features: Record<string, string>;
  pos: string;
  description: string;
}

export interface WhitakerParse {
  lemma: string | null;
  headword: string | null;
  pos: string | null;
  stem: string | null;
  ending: string | null;
  case: string | null;
  number: string | null;
  declension: string | null;
  meaning: string;
}

export interface LexEntry {
  headword: string | null;
  pos: string;
  glosses: string[];
  principalParts: string[];
  gender: string | null;
  declension: string | null;
  frequency: string | null;
  age: string | null;
  sourceRefs: string[];
}

export interface Token {
  i: number;
  text: string;
  whitespace: string;
  start: number;
  end: number;
  isWord: boolean;
  lemma: string;
  pos: string;
  posName: string;
  tag: string;
  dep: string;
  head: number;
  morph: Record<string, string>;
  description: string;
  caseForce: string | null;
  gloss: string | null;
  lexicon: LexEntry[];
  possibleReadings: WhitakerParse[];
  rankedReadings: Reading[];
  constructions: string[];
  sentence: number;
}

export interface Construction {
  key: string;
  name: string;
  latinName: string;
  tokens: number[];
  anchor: number;
  evidence: string;
  explanation: string;
  translationHint: string;
  grammarRef: string;
  confidence: number;
  caveat: string;
}

export interface Anomaly {
  token: number;
  kind: string;
  message: string;
  likelyBenign: string;
}

export interface Gate {
  isLatin: boolean;
  confidence: number;
  analysableRate: number;
  linguaLatin: number | null;
  competingLanguage: string | null;
  unrecognised: string[];
  anomalies: Anomaly[];
  message: string;
}

export interface ScanSyllable {
  text: string;
  word: number;
  quantity: "long" | "short" | "anceps" | "unknown";
  reason: string;
  elided: boolean;
  common: boolean;
}

export interface ScanLine {
  line: string;
  metre: string;
  ok: boolean;
  pattern: string;
  note: string;
  alternatives: number;
  elisions: string[];
  caesurae: { foot: number; name: string; kind: string; after: string; note: string }[];
  feet: { n: number; kind: string; syllables: number[] }[];
  syllables: ScanSyllable[];
  liveCount: number;
}

export interface Passage {
  work: string; author: string; title: string; unit: string;
  book: number; lineStart: number; lineEnd: number;
  confidence: number; matchedShingles: number; possibleShingles: number;
  citation: string;
}

export interface Note {
  author: string; source: string; language: string;
  book: number; lineStart: number; lineEnd: number;
  lemma: string; text: string; line: number;
}

export interface Analysis {
  text: string;
  gate: Gate;
  tokens: Token[];
  constructions: Construction[];
  sentences: { i: number; start: number; end: number; text: string }[];
  scansion: ScanLine[] | null;
  passage: Passage | null;
  commentary: Note[];
  model: string;
}

const BASE = import.meta.env.VITE_API ?? "http://127.0.0.1:8000";

export async function analyse(text: string): Promise<Analysis> {
  const res = await fetch(`${BASE}/api/analyse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`Analysis failed (${res.status})`);
  return res.json();
}

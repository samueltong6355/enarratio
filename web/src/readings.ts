import type { Analysis } from "./api";

export interface SavedReading { id: string; savedAt: string; analysis: Analysis }
const KEY = "enarratio.readings.v1";
export function readSaved(): SavedReading[] {
  try {
    const entries: unknown = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    if (!Array.isArray(entries)) return [];
    return entries.filter((x): x is SavedReading => typeof x?.id === "string" && typeof x?.savedAt === "string"
      && typeof x?.analysis?.text === "string" && Array.isArray(x?.analysis?.tokens)
      && Array.isArray(x?.analysis?.constructions) && Array.isArray(x?.analysis?.devices)
      && Array.isArray(x?.analysis?.commentary) && typeof x?.analysis?.gate?.isLatin === "boolean");
  } catch { return []; }
}
export function writeSaved(entries: SavedReading[]) {
  localStorage.setItem(KEY, JSON.stringify(entries));
}
export function exportReading(analysis: Analysis) {
  const url = URL.createObjectURL(new Blob([JSON.stringify({ format: "enarratio-reading-v1", exportedAt: new Date().toISOString(), analysis }, null, 2)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "enarratio-reading.json";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

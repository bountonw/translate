/* Proofreading site: the words of the interface (web/core/words.js).

   Every word the page shows comes from ui-strings.json: {"key": {"en": "...", "th": "..."}}. A key
   whose Thai is empty shows its English. {name} in a string takes the value of that name; a number of
   1,000 or more is written with commas, in Western digits. */

import { K } from "./store.js";
import { S, store, emit } from "./state.js";
import { getFile } from "./net.js";

let STR = {};

/* 8000 -> "8,000". */
export const groupDigits = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");

export function t(id, vars) {
  const s = STR[id];
  let out = s ? s[S.lang] || s.en || s.th || id : id;
  if (vars) out = out.replace(/\{(\w+)\}/g, (m, k) => (!(k in vars) ? m : typeof vars[k] === "number" ? groupDigits(vars[k]) : String(vars[k])));
  return out;
}

/* A time the server sent ("2026-10-22T16:45:24Z") as a date in the reader's own time zone, in the words of
   the keys date ("{d} {month} {y}"; {be} is the year of the Buddhist era) and months (the twelve names,
   separated by commas). "" when the time cannot be read. */
export function dateText(iso) {
  const d = new Date(String(iso || ""));
  if (isNaN(d.getTime())) return "";
  const names = t("months").split(",").map(x => x.trim());
  const y = d.getFullYear();
  return t("date", { d: String(d.getDate()), month: names[d.getMonth()] || String(d.getMonth() + 1), y: String(y), be: String(y + 543) });
}

/* A wait of {h, m} (refusals.js, untilReset) in words: "5 hours 12 minutes", "40 minutes" or "2 hours"; ""
   for none. */
export function durationText(d) {
  if (!d) return "";
  const parts = [];
  if (d.h) parts.push(plural(d.h, "hours_one", "hours_many"));
  if (d.m || !d.h) parts.push(plural(d.m, "minutes_one", "minutes_many"));
  return parts.join(" ");
}

/* A word in a given language, for the language switch, which names each language in itself. */
export const tIn = (l, id) => { const s = STR[id]; return s ? s[l] || s.en || id : id; };
export const plural = (n, one, many) => t(n === 1 ? one : many, { n });

export const hasWords = () => Object.keys(STR).length > 0;

export function useKeptWords() {
  STR = store.get(K.strings) || {};
}

/* Fetch ui-strings.json; true when the words changed. */
export async function loadWords() {
  const d = await getFile("ui-strings.json");
  if (!d) return false;
  const changed = JSON.stringify(d) !== JSON.stringify(STR);
  STR = d;
  store.set(K.strings, d);
  return changed;
}

/* The interface languages, the first being the default. Each needs its value in every string of
   ui-strings.json (an empty one shows the English) and a key lang_<code> naming it in itself. */
export const UI_LANGS = ["th", "en"];

export function keptLang() {
  const l = store.get(K.lang);
  return UI_LANGS.indexOf(l) >= 0 ? l : UI_LANGS[0];
}

export function setLang(l) {
  S.lang = l;
  store.set(K.lang, l);
  emit("lang");
}

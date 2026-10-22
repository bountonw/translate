/* Proofreading site: the words of the interface (web/core/words.js).

   Every word the page shows comes from ui-strings.json: {"key": {"en": "...", "th": "..."}}. A key
   whose Thai is empty shows its English. {name} in a string takes the value of that name. */

import { K } from "./store.js";
import { S, store, emit } from "./state.js";
import { getFile } from "./net.js";

let STR = {};

export function t(id, vars) {
  const s = STR[id];
  let out = s ? s[S.lang] || s.en || s.th || id : id;
  if (vars) out = out.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
  return out;
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

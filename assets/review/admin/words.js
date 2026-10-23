// The admin page's words. Every word the page shows comes from strings.json, as {"key": {"en": "...", "th": ""}},
// so that a Thai, Lao or Mien admin page needs only that file filled in, with no change to the code. {name} in a
// string takes the value of that name. LANGS lists the languages the page can show, the first being the one it
// shows; a key whose value is empty in that language shows its English. The lines and messages of the commands
// stay as review.py prints them.
export const LANGS = ["en"];

let STR = {};
let lang = LANGS[0];

// Take the words of strings.json; false when there are none.
export function setWords(data) {
  STR = data && typeof data === "object" && !Array.isArray(data) ? data : {};
  lang = LANGS[0];
  return Object.keys(STR).length > 0;
}

export function language() {
  return lang;
}

export function t(key, vars) {
  const s = STR[key];
  let out = s ? s[lang] || s.en || key : key;
  if (vars) out = out.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
  return out;
}

// A count and its word, as "1 reader" or "2 readers": the keys WORD_1 and WORD_n of strings.json.
export function plural(n, word) {
  return t(word + (n === 1 ? "_1" : "_n"), { n: n });
}

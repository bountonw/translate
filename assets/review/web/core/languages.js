/* Proofreading site: languages and their fonts (web/core/languages.js).

   web/languages.json, the registry the server also reads, names each language's font: its family,
   fallback families and files. For each language the page shows (the interface language and the
   language of each of the reader's books), the page registers the font files with the FontFace API
   and adds two rules to app.css through the CSS object model, which the CSP allows:

     :lang(th) { --f-book: "Sarabun", "Noto Sans Thai", ...; }        the book text in that language
     :root:lang(th) { --f-ui: "Sarabun", "Noto Sans Thai", ...; }     the interface in that language

   A language missing from the registry gets the system fonts and still gets its lang attribute. A
   font file is downloaded only when text in its language, weight and style is on the screen, except
   the regular face of each language shown, which starts at once. */

import { K } from "./store.js";
import { LANG_RE } from "./model.js";
import { S, store } from "./state.js";
import { getFile } from "./net.js";

const SYSTEM = ["system-ui", "-apple-system", "Segoe UI", "sans-serif"];
const GENERIC = new Set(["serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "-apple-system",
  "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded", "emoji", "math"]);
const FAMILY_RE = /^[A-Za-z0-9 _-]{1,64}$/;
const SRC_RE = /^fonts\/[A-Za-z0-9._-]{1,100}$/;
const RANGE_RE = /^[Uu+0-9A-Fa-f?, -]{1,200}$/;

let REG = null;
const wanted = new Set();
const done = new Set();
const faces = [];   // [FontFace, src]: every font file registered on this visit

const valid = d => !!d && typeof d === "object" && !!d.languages && typeof d.languages === "object";

/* The language of a book's text, for its lang attribute, or null when the server did not say. */
export function bookLang(book) {
  const l = S.me && S.me.langs ? S.me.langs[book] : null;
  return typeof l === "string" && LANG_RE.test(l) ? l : null;
}

/* A family list for CSS: names quoted, generic families as they are, anything odd left out. */
function stack(families) {
  return families.filter(f => typeof f === "string" && FAMILY_RE.test(f))
    .map(f => (GENERIC.has(f) ? f : '"' + f + '"')).join(", ");
}

function addRule(rule) {
  const sheet = Array.from(document.styleSheets).find(s => /(^|\/)app\.css(\?|$)/.test(s.href || ""));
  if (!sheet) return;
  try { sheet.insertRule(rule, sheet.cssRules.length); } catch (e) { /* this browser cannot read the rule */ }
}

function apply(code) {
  const entry = REG && REG.languages[code];
  const font = entry && entry.font && typeof entry.font === "object" ? entry.font : null;
  const family = font && typeof font.family === "string" && FAMILY_RE.test(font.family) ? font.family : null;
  const list = family ? stack([family].concat(Array.isArray(font.fallback) ? font.fallback : [])) : stack(SYSTEM);
  if (family && Array.isArray(font.files) && typeof FontFace === "function" && document.fonts) {
    for (const f of font.files) {
      if (!f || !SRC_RE.test(f.src || "")) continue;
      const desc = { weight: String(f.weight || 400), style: f.style === "italic" ? "italic" : "normal", display: "swap" };
      if (typeof font.unicode_range === "string" && RANGE_RE.test(font.unicode_range)) desc.unicodeRange = font.unicode_range;
      try {
        const face = new FontFace(family, 'url("' + f.src + '")', desc);
        document.fonts.add(face);
        faces.push([face, f.src]);
        if (desc.weight === "400" && desc.style === "normal") face.load().catch(() => { /* the fallback shows */ });
      } catch (e) { /* a font this browser cannot read: the fallback shows */ }
    }
  }
  addRule(":lang(" + code + ") { --f-book: " + list + "; }");
  addRule(":root:lang(" + code + ") { --f-ui: " + list + "; }");
}

/* Register the fonts of these languages, once each. Before the registry is known, the languages wait. */
export function showLanguages(codes) {
  for (const c of codes) if (typeof c === "string" && LANG_RE.test(c)) wanted.add(c);
  if (!REG) return;
  for (const c of wanted) {
    if (done.has(c)) continue;
    done.add(c);
    apply(c);
  }
}

export function useKeptLanguages() {
  const d = store.get(K.langs);
  if (valid(d)) REG = d;
}

/* Fetch languages.json. A first registry is applied at once; a changed one shows on the next visit,
   because a font already registered stays for this visit. */
export async function loadLanguages() {
  const d = await getFile("languages.json");
  if (!valid(d)) return;
  store.set(K.langs, d);
  if (!REG) {
    REG = d;
    showLanguages([]);
  }
}

/* The font files this visit has loaded, as "fonts/Sarabun-Regular.ttf", for the service worker to keep. */
export function loadedFontFiles() {
  return faces.filter(x => x[0].status === "loaded").map(x => x[1]);
}

/* The languages on the screen now: the interface's and those of the reader's books. */
export function shownLanguages() {
  const out = [S.lang];
  if (S.me && S.me.langs) for (const b of Object.keys(S.me.langs)) out.push(S.me.langs[b]);
  return out;
}

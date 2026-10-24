/* Proofreading site: the places where features plug into the page (web/core/ext.js).

   A feature's page part is one module in web/features/. It calls feature() once with its name, the
   same name as its module in server/features/, then adds itself to any of these places:

     panelSection   a section of a paragraph's panel; the English leads its first face (core/panel.js)
     spanMark       what a marked span in the book text does: <span data-kind="bible" data-value="...">
     chapterSection a section at the end of a chapter, before the "finished" box
     settingsItem   an item in the settings, beside the language switch
     titleLine      a line under a chapter's title, in the chapter list and at the head of the chapter
     bookText       a change to book text once it is drawn, such as the sentence spans of features/sentences.js

   Each entry is an object {name, order, feature, ...}. The page uses an entry only while its feature
   is on for this reader (GET /api/me, features); an entry without `feature` belongs to the core and is
   always used. Entries are used in rising `order`. This module holds no DOM, so tests/core_test.js can
   run it with node. EXTENDING.md, "The page side", says what each place passes and expects. */

const FEATURES = {};
const PLACES = { panels: [], marks: [], sections: [], settings: [], titles: [], texts: [] };

/* def = {name, enabled(settings)?, variant?}. `enabled` decides from the feature's settings whether it
   is on; without it the feature is on when settings.on is true. `variant` is a word for a feature that
   changes the chapter text the server sends (English adds "en"), so a chapter kept on the device is
   fetched again when the feature is switched on or off. */
export function feature(def) {
  FEATURES[def.name] = def;
  return def;
}

/* Whether a feature is on for this reader. A feature the page does not know, or one missing from
   /api/me, is off. An entry without a feature is always on. */
export function isOn(me, name) {
  if (!name) return true;
  const def = FEATURES[name];
  const settings = me && me.features && me.features[name];
  if (!def || !settings || typeof settings !== "object") return false;
  return def.enabled ? !!def.enabled(settings) : settings.on === true;
}

function add(place, def) {
  const list = PLACES[place];
  const i = list.findIndex(x => x.name === def.name);
  if (i >= 0) list.splice(i, 1);
  list.push(def);
  list.sort((x, y) => (x.order || 0) - (y.order || 0));
  return def;
}

/* def.render(ctx) returns an element or null: a section of the paragraph's panel (core/panel.js). ctx: {p, art,
   chapter, me, book, lang, span, show, beside, face}; span is the marked span the reader tapped, or null;
   show(a, span) shows paragraph a in the panel with span lit (null for none), as Next sentence does; face is "en"
   when the section stands on the lead's face and "note" when it stands under the comment form. The entry with lead: true,
   the English, leads the panel's first face, whose button says the key `label`; the other sections follow it there,
   or stand under the comment form when no lead section draws anything. With beside: true the lead section is
   drawn beside the paragraph instead, when the reader shows it side by side on a wide screen. def.hint names a key
   of ui-strings.json for the line under a chapter title that says what a tap shows. */
export const panelSection = def => add("panels", def);
/* def.kind is the data-kind it handles. def.decorate(span, ctx) changes the span once it is drawn;
   def.tap(span, ctx) runs when the reader taps it and returns true to keep the panel from opening or closing. */
export const spanMark = def => add("marks", def);
/* def.render(ctx) returns an element or null. ctx: {chapter, comments, me, book}. With refresh: true
   the section is drawn again whenever the reader's comments change. */
export const chapterSection = def => add("sections", def);
/* def.render(ctx) returns an element or null. ctx: {me, screen}; me is null on the link and offline
   screens, so only core items show there. */
export const settingsItem = def => add("settings", def);
/* def.render(ctx) returns an element or null. ctx: {chapter, me, where: "list" or "head"}. */
export const titleLine = def => add("titles", def);
/* def.decorate(el, ctx) changes book text once it is drawn, without changing its words: it may wrap words in
   spans. ctx is that of panelSection plus `where`: "para" (a paragraph's text in the book's language, with
   p.al its sentence pairs), "fn" (a footnote), "en" (the English in the panel), "side" (the English beside the
   paragraph) or "earlier" (the earlier wording). */
export const bookText = def => add("texts", def);

/* The entries of a place that are on for this reader, in order. */
export function active(place, me) {
  return PLACES[place].filter(d => isOn(me, d.feature));
}

/* The entry that handles spans of this data-kind, or null. */
export function markFor(kind, me) {
  return active("marks", me).find(d => d.kind === kind) || null;
}

/* The words that tell a chapter kept on the device which features shaped it: "" or "en". */
export function variantOf(me) {
  return Object.keys(FEATURES).sort()
    .filter(n => FEATURES[n].variant && isOn(me, n))
    .map(n => FEATURES[n].variant).join(".");
}

/* The key of the hint under a chapter title: the first panel section on that names one, else "hint". */
export function hintKey(me) {
  const p = active("panels", me).find(d => d.hint);
  return p ? p.hint : "hint";
}

/* Run a feature's function so that its fault never stops the page: the fault is logged and the
   entry is left out. */
export function safely(def, fn, fallback) {
  try { return fn(); } catch (e) { console.error("feature " + (def.feature || def.name), e); return fallback; }
}


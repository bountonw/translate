/* Proofreading site: the server's answers in the shape the page uses (web/core/model.js).

   Plain functions with no DOM: tests/core_test.js runs them with node. */

/* The limits the server applied before /api/me carried them (README.md, "Limits"). */
export const DEFAULT_LIMITS = { quote: 500, text: 4000, comments: 5000, writes_per_minute: 60 };

const count = x => Number(x) || 0;
const isObj = x => !!x && typeof x === "object" && !Array.isArray(x);

/* A language code as a lang attribute and a CSS selector may hold it: th, lo, pt-BR. */
export const LANG_RE = /^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$/;

/* features maps each feature to its settings for this reader, as {"english": {"on": true}}. An answer
   without features (the server before groups) has only `english`. */
function normFeatures(d) {
  if (isObj(d.features)) {
    const out = {};
    for (const k of Object.keys(d.features)) if (isObj(d.features[k])) out[k] = Object.assign({}, d.features[k]);
    return out;
  }
  return { english: { on: !!d.english } };
}

function normLimits(x) {
  const out = Object.assign({}, DEFAULT_LIMITS);
  if (isObj(x)) {
    for (const k of Object.keys(DEFAULT_LIMITS)) {
      const n = Math.floor(Number(x[k]));
      if (n > 0) out[k] = n;
    }
  }
  return out;
}

/* GET /api/me in the shape the page uses. A book's heading is its title in its own language (title_th),
   or its English title. `total` is every comment of the reader, in closed chapters too, or null when the
   server did not say. */
export function normMe(d) {
  d = d || {};
  const books = {}, langs = {};
  for (const b of Array.isArray(d.books) ? d.books : []) {
    if (!isObj(b)) continue;
    books[b.id] = b.title_th || b.title_en || b.id;
    if (typeof b.language === "string" && LANG_RE.test(b.language)) langs[b.id] = b.language;
  }
  const chapters = (Array.isArray(d.chapters) ? d.chapters : []).map(c => ({
    book: c.book, id: c.id, n: Number(c.n) || 0,
    title_th: c.title_th || "", title_en: c.title_en || "", version: c.version,
    count: count(c.paragraphs),
    comments: count(c.comments),
    finished: !!c.finished,
    place: c.place || null,
  }));
  const total = typeof d.comments_total === "number" && isFinite(d.comments_total) ? d.comments_total : null;
  return { name: d.name || "", books, langs, chapters, features: normFeatures(d), limits: normLimits(d.limits), total };
}

/* A chapter list saved on the device by an older page lacks features, limits and total. */
export function upgradeMe(m) {
  if (!isObj(m) || !Array.isArray(m.chapters)) return null;
  if (!isObj(m.features)) m.features = { english: { on: !!m.english } };
  m.limits = normLimits(m.limits);
  if (m.total === undefined) m.total = null;
  if (!isObj(m.langs)) m.langs = {};
  if (!isObj(m.books)) m.books = {};
  return m;
}

/* GET /api/chapter/<book>/<id> in the shape the page uses. */
export function normChapter(d) {
  const c = d || {};
  const paras = c.paragraphs;
  return {
    book: c.book, id: c.id, n: Number(c.n) || 0,
    title_th: c.title_th || "", title_en: c.title_en || "", version: c.version,
    paras: (Array.isArray(paras) ? paras : []).map(p => ({ a: p.a, th: p.th || "", fn: Array.isArray(p.fn) ? p.fn : [], en: p.en || "" })),
  };
}

/* A comment list from the server; a comment without a client_id is keyed by its id. */
export function normComments(d) {
  const list = Array.isArray(d) ? d : d && Array.isArray(d.comments) ? d.comments : [];
  return list.filter(c => c && typeof c === "object").map(c => (c.client_id ? c : Object.assign({ client_id: "id:" + c.id }, c)));
}

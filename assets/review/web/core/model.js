/* Proofreading site: the server's answers in the shape the page uses (web/core/model.js).

   Plain functions with no DOM: tests/core_test.js runs them with node. */

/* The limits the page uses until /api/me carries the server's own (README.md, "Limits"): quoted words and
   a comment in characters, new comments in a minute and in a day, other changes in a minute, and the devices
   a link works on without the translator's approval. There is no limit on the comments a reader keeps. */
export const DEFAULT_LIMITS = { quote: 4000, text: 8000, comments_per_minute: 10, comments_per_day: 1000, writes_per_minute: 60, devices_per_link: 2 };

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

/* What changed in a chapter since the version the reader last opened: {since, since_at, at, paragraphs:
   [{a, at, new}], removed: [{a, at}]}, or null when there is nothing to show (README.md, GET /api/me). */
function normChanged(x) {
  if (!isObj(x) || typeof x.since !== "string" || !x.since) return null;
  const str = v => (typeof v === "string" ? v : "");
  const paras = (Array.isArray(x.paragraphs) ? x.paragraphs : [])
    .filter(p => isObj(p) && typeof p.a === "string" && p.a)
    .map(p => ({ a: p.a, at: str(p.at), new: p.new === true }));
  const removed = (Array.isArray(x.removed) ? x.removed : [])
    .filter(p => isObj(p) && typeof p.a === "string" && p.a)
    .map(p => ({ a: p.a, at: str(p.at) }));
  if (!paras.length && !removed.length) return null;
  return { since: x.since, since_at: str(x.since_at), at: str(x.at), paragraphs: paras, removed };
}

/* A title in the book's own language: `title`, or `title_th` in an answer of a server before round 3b. */
const titleOf = x => (typeof x.title === "string" ? x.title : "") || (typeof x.title_th === "string" ? x.title_th : "");

/* A book's current review round, {name, started}, or null. */
function normRound(r) {
  return isObj(r) && typeof r.name === "string" && r.name ? { name: r.name, started: typeof r.started === "string" ? r.started : "" } : null;
}

/* GET /api/me in the shape the page uses. `id` is the reader's fixed number, which a new link keeps, or null
   when the server did not say. A book's heading is its title in its own language, or its English title.
   `rounds` gives each book's current review round, {name, started} or null, and `earlier` the count of the
   reader's comments of earlier rounds on chapters open now. `total` counts the reader's comments of the
   current rounds on chapters open now, or is null when the server did not say. Each chapter's `title` is
   in the book's language; its `opened` is the version the reader last opened, or null, and `changed` what
   changed since then, or null. */
export function normMe(d) {
  d = d || {};
  const books = {}, langs = {}, rounds = {}, earlier = {};
  for (const b of Array.isArray(d.books) ? d.books : []) {
    if (!isObj(b)) continue;
    books[b.id] = titleOf(b) || b.title_en || b.id;
    if (typeof b.language === "string" && LANG_RE.test(b.language)) langs[b.id] = b.language;
    rounds[b.id] = normRound(b.round);
    earlier[b.id] = count(b.earlier);
  }
  const chapters = (Array.isArray(d.chapters) ? d.chapters : []).map(c => ({
    book: c.book, id: c.id, n: Number(c.n) || 0,
    title: titleOf(c), title_en: c.title_en || "", version: c.version,
    count: count(c.paragraphs),
    comments: count(c.comments),
    finished: !!c.finished,
    place: c.place || null,
    opened: typeof c.opened === "string" && c.opened ? c.opened : null,
    changed: normChanged(c.changed),
  }));
  const total = typeof d.comments_total === "number" && isFinite(d.comments_total) ? d.comments_total : null;
  const id = Number.isInteger(d.id) ? d.id : null;
  return { id, name: d.name || "", books, langs, rounds, earlier, chapters, features: normFeatures(d), limits: normLimits(d.limits), total };
}

/* A chapter list saved on the device by an older page lacks some of these: features, limits, total, the
   reader's number, the rounds, and each chapter's neutral `title` (title_th before round 3b). `rounds` stays
   missing when the page did not keep it, so that the comment lists kept with it are fetched again. */
export function upgradeMe(m) {
  if (!isObj(m) || !Array.isArray(m.chapters)) return null;
  if (!isObj(m.features)) m.features = { english: { on: !!m.english } };
  m.limits = normLimits(m.limits);
  if (m.total === undefined) m.total = null;
  if (!Number.isInteger(m.id)) m.id = null;
  if (!isObj(m.langs)) m.langs = {};
  if (!isObj(m.books)) m.books = {};
  if (!isObj(m.earlier)) m.earlier = {};
  for (const c of m.chapters) {
    if (!isObj(c)) continue;
    if (typeof c.title !== "string") c.title = typeof c.title_th === "string" ? c.title_th : "";
    if (typeof c.opened !== "string") c.opened = null;
    c.changed = normChanged(c.changed);
  }
  return m;
}

const isRange = r => Array.isArray(r) && r.length === 2 && r.every(n => Number.isInteger(n) && n >= 0) && r[0] < r[1];

/* A paragraph's sentence pairs, [{text: [start, end], en: [[start, end], ...]}], each range counting code
   points of the text the page shows (EXTENDING.md, "Sentence alignment"); a pair that does not have this
   shape is left out. A server or a kept chapter from before round 3b names the text's range `th`. */
export function normPairs(al) {
  if (!Array.isArray(al)) return [];
  const textOf = x => (isRange(x.text) ? x.text : x.th);
  return al.filter(x => isObj(x) && isRange(textOf(x)) && Array.isArray(x.en) && x.en.length && x.en.every(isRange))
    .map(x => ({ text: textOf(x).slice(), en: x.en.map(r => r.slice()) }));
}

/* A paragraph in the shape the page uses: {a, text, fn, en, al?}. `text` is in the book's own language; a
   server or a kept chapter from before round 3b names it `th`. */
function normPara(p) {
  p = isObj(p) ? p : {};
  const text = typeof p.text === "string" ? p.text : typeof p.th === "string" ? p.th : "";
  const out = { a: p.a, text, fn: Array.isArray(p.fn) ? p.fn : [], en: p.en || "" };
  const al = normPairs(p.al);
  if (al.length) out.al = al;
  return out;
}

/* GET /api/chapter/<book>/<id> in the shape the page uses. `title` and each paragraph's `text` are in the
   book's language, `language` names it when the server says, and `at` is when the version was published. A
   paragraph has `al`, its sentence pairs, only when the server sent some. */
export function normChapter(d) {
  const c = d || {};
  const paras = c.paragraphs;
  return {
    book: c.book, id: c.id, n: Number(c.n) || 0, language: typeof c.language === "string" && LANG_RE.test(c.language) ? c.language : "",
    title: titleOf(c), title_en: c.title_en || "", version: c.version, at: typeof c.at === "string" ? c.at : "",
    paras: (Array.isArray(paras) ? paras : []).map(normPara),
  };
}

/* A chapter kept on the device by a page before round 3b, in its own shape (title_th, and `th` for each
   paragraph and each pair's range), brought to the shape of normChapter. The server answers 304 for such a
   chapter, since its version did not change, so the page keeps using it. A chapter already in the new shape
   comes back as it is. */
export function upgradeChapter(data) {
  if (!isObj(data) || !Array.isArray(data.paras)) return data;
  if (typeof data.title !== "string") data.title = typeof data.title_th === "string" ? data.title_th : "";
  if (typeof data.language !== "string") data.language = "";
  if (data.paras.some(p => !isObj(p) || typeof p.text !== "string" || (Array.isArray(p.al) && p.al.some(x => !isObj(x) || !isRange(x.text))))) {
    data.paras = data.paras.map(normPara);
  }
  return data;
}

/* A comment list from the server; a comment without a client_id is keyed by its id. */
export function normComments(d) {
  const list = Array.isArray(d) ? d : d && Array.isArray(d.comments) ? d.comments : [];
  return list.filter(c => c && typeof c === "object").map(c => (c.client_id ? c : Object.assign({ client_id: "id:" + c.id }, c)));
}

/* The numbers in a paragraph's tag, for sorting: "SC 23.2" -> [23, 2]. */
const tagNumbers = a => (String(a || "").match(/\d+/g) || []).map(Number);
function byTag(x, y) {
  const p = tagNumbers(x), q = tagNumbers(y);
  for (let i = 0; i < Math.max(p.length, q.length); i++) {
    const d = (p[i] || 0) - (q[i] || 0);
    if (d) return d;
  }
  return String(x).localeCompare(String(y));
}

/* The reader's comments of earlier review rounds (GET /api/comments?earlier=1), grouped for "My earlier
   comments": by book, then by round, newest round first and the comments written before the book's first
   round last, then by chapter, then by paragraph and time. rounds is the answer's `rounds`; a round it does
   not name stands with its name only. Returns [{book, rounds: [{round: {name, started} or null, chapters:
   [{ch, comments}]}]}]. */
export function groupEarlier(comments, rounds) {
  const known = {};
  for (const r of Array.isArray(rounds) ? rounds : []) {
    if (isObj(r) && typeof r.book === "string" && typeof r.name === "string") known[r.book + "\n" + r.name] = { name: r.name, started: typeof r.started === "string" ? r.started : "" };
  }
  const books = new Map();
  for (const c of Array.isArray(comments) ? comments : []) {
    if (!isObj(c) || typeof c.book !== "string" || typeof c.ch !== "string") continue;
    const name = typeof c.round === "string" && c.round ? c.round : null;
    if (!books.has(c.book)) books.set(c.book, new Map());
    const byRound = books.get(c.book);
    const key = name === null ? "" : name;
    if (!byRound.has(key)) byRound.set(key, { round: name === null ? null : known[c.book + "\n" + name] || { name, started: "" }, chapters: new Map() });
    const chs = byRound.get(key).chapters;
    if (!chs.has(c.ch)) chs.set(c.ch, []);
    chs.get(c.ch).push(c);
  }
  const newestFirst = (x, y) => {
    if (!x.round || !y.round) return x.round ? -1 : y.round ? 1 : 0;
    return y.round.started.localeCompare(x.round.started) || y.round.name.localeCompare(x.round.name);
  };
  return [...books.keys()].sort().map(book => ({
    book,
    rounds: [...books.get(book).values()].sort(newestFirst).map(r => ({
      round: r.round,
      chapters: [...r.chapters.keys()].sort().map(ch => ({
        ch,
        comments: r.chapters.get(ch).slice().sort((x, y) => byTag(x.a, y.a) || String(x.created || "").localeCompare(String(y.created || ""))),
      })),
    })),
  }));
}

/* Proofreading site: what changed in a chapter since the reader last opened it (web/core/changes.js).

   GET /api/me gives each chapter `opened`, the version the reader last opened, and `changed`, the paragraphs
   whose words changed since then or are new, with `since`, the version opened. The page marks each such
   paragraph until the reader opens it (taps it open), and keeps on the device which marked paragraphs the
   reader has opened: the record of one chapter, under openedKey() of store.js. When every marked paragraph
   is opened, the page sends the chapter's version with PUT /api/opened (core/updates.js); the server then
   has nothing more to show, and the record stays so that "Show the earlier wording" can still fetch the
   version the reader saw before (`since`).

   record = {since, version, at, paras: [{a, at, new}], removed, opened: {a: at}, done}
     since    the version the reader had opened before the change
     version  the chapter's version that the marks belong to
     paras    the changed and new paragraphs, each with the time of the version that last changed it
     removed  how many paragraphs the change took out
     opened   the marked paragraphs the reader has opened, each with the `at` of the change seen
     done     true once every marked paragraph is opened, or once the server has nothing to show

   Plain functions with no DOM: tests/core_test.js runs them with node. */

/* The record brought up to date with one chapter of /api/me (c = {version, opened, changed}). A new change
   starts a new record; a paragraph opened before keeps its mark cleared when its change is the same. With
   nothing to show, a record stays, done, for the earlier wording. Returns the record, or null. */
export function syncRecord(rec, c) {
  const ch = c && c.changed;
  if (ch && ch.since) {
    if (rec && rec.since === ch.since && rec.version === c.version && sameParas(rec.paras, ch.paragraphs)) return rec;
    const before = (rec && rec.opened) || {};
    const opened = {};
    for (const p of ch.paragraphs) if (before[p.a] && before[p.a] === p.at) opened[p.a] = p.at;
    const out = {
      since: ch.since, version: c.version, at: ch.at || "",
      paras: ch.paragraphs.map(p => ({ a: p.a, at: p.at || "", new: !!p.new })),
      removed: (ch.removed || []).length, opened, done: false,
    };
    return out;
  }
  if (!rec || rec.done) return rec || null;
  return Object.assign({}, rec, { done: true });
}

function sameParas(x, y) {
  if (!Array.isArray(x) || !Array.isArray(y) || x.length !== y.length) return false;
  return x.every((p, i) => p.a === y[i].a && p.at === (y[i].at || "") && !!p.new === !!y[i].new);
}

/* The marks of a chapter drawn at `version`: {a: "new" or "changed"} for each changed paragraph the reader
   has not opened yet. None when the record is done or belongs to another version. */
export function marksOf(rec, version) {
  const out = {};
  if (!rec || rec.done || rec.version !== version) return out;
  for (const p of rec.paras) if (!rec.opened[p.a]) out[p.a] = p.new ? "new" : "changed";
  return out;
}

/* The reader opened paragraph a. Returns the record with its mark cleared, or the same record when a was not
   marked. */
export function openPara(rec, a) {
  if (!rec || rec.done || rec.opened[a]) return rec;
  const p = rec.paras.find(x => x.a === a);
  if (!p) return rec;
  const opened = Object.assign({}, rec.opened);
  opened[a] = p.at || "1";
  return Object.assign({}, rec, { opened });
}

/* Whether the reader has opened every marked paragraph (true when none is marked). */
export function allOpened(rec) {
  return !!rec && rec.paras.every(p => !!rec.opened[p.a]);
}

/* What the page should send now for a chapter drawn at `version`, given its entry c of /api/me and its
   record: "send" the version with PUT /api/opened, or "" for nothing. The page sends it when the chapter
   has nothing marked and the server does not yet hold this version as opened, or when the reader has
   opened every marked paragraph. */
export function openedToSend(c, rec, version) {
  if (!c || c.version !== version) return "";
  if (!c.changed) return c.opened === version ? "" : "send";
  return rec && rec.version === version && allOpened(rec) ? "send" : "";
}

/* The paragraph's change in the record, for "Show the earlier wording": {a, at, new}, or null. */
export function changeOf(rec, a) {
  return (rec && rec.paras.find(p => p.a === a)) || null;
}

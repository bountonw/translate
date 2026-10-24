/* Proofreading site: a new version of a chapter, as the reader sees it (web/core/updates.js).

   The translator's ruling: a new version of a chapter shows the reader a line saying when it changed and how
   many paragraphs changed, marks each changed paragraph until the reader opens it, and offers "Show the
   earlier wording" in the paragraph's panel. core/changes.js holds the rules; this module draws them:

     - the line at the head of the chapter (updateLine, called by chapter.js);
     - the mark "Changed" or "New" at the start of a paragraph (paintMark, called by para.js);
     - "Show the earlier wording", a core section of the panel (ext.js, panelSection, order 20, under the
       English), which fetches the paragraph as the reader last saw it with GET /api/earlier;
     - PUT /api/opened through the outbox, once the reader has opened every marked paragraph, or at once
       when nothing is marked.

   The line on a reader's own comment whose paragraph changed is drawn by notes.js. */

import { syncRecord, marksOf, openPara, openedToSend, changeOf } from "./changes.js";
import { queueSet } from "./outbox.js";
import { S, store } from "./state.js";
import { K, openedKey } from "./store.js";
import { t, plural, dateText } from "./words.js";
import { h, bookHtml, applyMarks, decorateText } from "./dom.js";
import { panelSection } from "./ext.js";
import { api, mutateOb, flush, authFailed, isDeviceWaiting, deviceWaiting, who } from "./net.js";
import { bookLang } from "./languages.js";

const enc = encodeURIComponent;

const meChapterOf = (book, ch) => (S.me ? S.me.chapters.find(c => c.book === book && c.id === ch) || null : null);

/* The device's record of a chapter, brought up to date with the chapter list. */
export function recordOf(book, ch) {
  const key = openedKey(book, ch);
  const old = store.get(key);
  const c = meChapterOf(book, ch);
  if (!c) return old;
  const rec = syncRecord(old, c);
  if (rec !== old) {
    if (rec) store.set(key, rec);
    else store.del(key);
  }
  return rec;
}

/* The marks of the chapter on the screen: {a: "new" or "changed"}. */
let marks = {};
let marksFor = { book: null, ch: null };

function computeMarks(data) {
  marks = marksOf(recordOf(data.book, data.id), data.version);
  marksFor = { book: data.book, ch: data.id };
}

/* Send the version of the chapter on the screen as opened, through the outbox, when changes.js says so. The
   chapter list on the device takes it at once, so the page sends it once. */
function sendOpenedIfDue(data) {
  const c = meChapterOf(data.book, data.id);
  const rec = recordOf(data.book, data.id);
  if (openedToSend(c, rec, data.version) !== "send") return;
  if (rec && !rec.done) store.set(openedKey(data.book, data.id), Object.assign({}, rec, { done: true }));
  c.opened = data.version;
  c.changed = null;
  store.set(K.me, S.me);
  mutateOb(ob => queueSet(ob, "opened", { book: data.book, ch: data.id, version: data.version }, who(), Date.now(), 0));
  flush();
}

/* The chapter `data` is on the screen now: work out its marks and send its version as opened if due.
   chapter.js calls it before it draws the paragraphs, and again when a new chapter list arrives. */
export function chapterShown(data) {
  computeMarks(data);
  sendOpenedIfDue(data);
}

/* The mark at the start of a paragraph: "Changed" or "New", until the reader opens the paragraph. */
export function paintMark(art) {
  const el = art.querySelector(".upd");
  if (!el) return;
  const m = S.chapter && marksFor.book === S.book && marksFor.ch === S.ch ? marks[art.dataset.a] || "" : "";
  el.hidden = !m;
  el.textContent = m === "new" ? t("mark_new") : m ? t("mark_changed") : "";
  art.classList.toggle("is-changed", !!m);
}

/* The reader opened paragraph a of the chapter on the screen: its mark goes, and when no mark is left the
   page sends the chapter's version as opened. */
export function paraOpened(art) {
  if (!S.chapter) return;
  const data = S.chapter;
  const key = openedKey(data.book, data.id);
  const rec = recordOf(data.book, data.id);
  const next = openPara(rec, art.dataset.a);
  if (next === rec) return;
  store.set(key, next);
  computeMarks(data);
  paintMark(art);
  sendOpenedIfDue(data);
}

/* All marks and the line again, as after a new chapter list. */
export function repaintUpdates() {
  if (S.view !== "chapter" || !S.chapter) return;
  chapterShown(S.chapter);
  for (const art of document.querySelectorAll("#main .para")) paintMark(art);
}

/* The line at the head of the chapter: when it changed, how many paragraphs changed, and how many were taken
   out. Shown while the chapter list says that something changed since the version the reader opened. */
export function updateLine(data) {
  const c = meChapterOf(data.book, data.id);
  const ch = c && c.version === data.version ? c.changed : null;
  if (!ch) return null;
  const parts = [];
  const date = dateText(ch.at);
  parts.push(date ? t("upd_on", { date }) : t("upd_changed"));
  if (ch.paragraphs.length) parts.push(plural(ch.paragraphs.length, "upd_paras_one", "upd_paras_many"));
  if (ch.removed.length) parts.push(plural(ch.removed.length, "upd_removed_one", "upd_removed_many"));
  return h("p", { class: "upd-line", id: "upd-line", role: "status", text: parts.join(" ") });
}

/* ---- "Show the earlier wording": a core section of the panel ---- */

const fetched = new Map();   // "book/ch/a/version" -> the answer of GET /api/earlier, for this visit
/* The keys of fetched whose earlier wording the reader opened and has not folded again, for this visit: the panel
   draws its sections anew at every Next sentence and every tap on another sentence, and the earlier wording stays
   open through those, so a reader can compare it sentence by sentence. */
const unfolded = new Set();

/* The earlier wording's text in the book's language: `text`, or `th` from a server before round 3b. */
const earlierText = d => (typeof d.text === "string" ? d.text : d.th);

function earlierBlock(ctx, change, rec) {
  const box = h("section", { class: "earlier-block" });
  const out = h("div", { class: "earlier-out" });
  const status = h("p", { class: "status", "aria-live": "polite" });
  let shown = false;
  const btn = h("button", { type: "button", class: "link earlier-btn", text: t("earlier_show"), "aria-expanded": "false" });
  const show = d => {
    const lg = bookLang(ctx.book);
    const text = h("div", { class: "earlier-text bt", lang: lg }, bookHtml(earlierText(d)));
    const fns = Array.isArray(d.fn) && d.fn.length ? h("ol", { class: "fns", lang: lg }, d.fn.map(f => h("li", { class: "bt" }, bookHtml(f)))) : null;
    const date = dateText(change.at);
    out.textContent = "";
    // append() would write a missing footnote list as the word "null", so the list goes in only when there is one.
    out.append(h("p", { class: "label", text: date ? t("earlier_title", { date }) : t("earlier_label") }), text);
    if (fns) out.append(fns);
    applyMarks(out, ctx);
    decorateText(text, ctx, "earlier");
    if (fns) for (const li of fns.children) decorateText(li, ctx, "earlier");
  };
  const key = [ctx.book, ctx.chapter.id, ctx.p.a, rec.since].join("/");
  const open = d => {
    status.textContent = "";
    shown = true;
    show(d);
    btn.textContent = t("earlier_hide");
    btn.setAttribute("aria-expanded", "true");
  };
  const toggle = async () => {
    if (shown) {
      shown = false;
      unfolded.delete(key);
      out.textContent = "";
      status.textContent = "";
      btn.textContent = t("earlier_show");
      btn.setAttribute("aria-expanded", "false");
      return;
    }
    let d = fetched.get(key);
    if (!d) {
      btn.disabled = true;
      status.textContent = t("loading");
      const r = await api("GET", "api/earlier/" + enc(ctx.book) + "/" + enc(ctx.chapter.id) + "?a=" + enc(ctx.p.a) + "&version=" + enc(rec.since));
      btn.disabled = false;
      if (r.status === 401) { authFailed(r.data && r.data.error); return; }
      if (isDeviceWaiting(r)) { deviceWaiting(r.data); return; }
      if (r.status !== 200 || !r.data || typeof earlierText(r.data) !== "string") {
        const code = r.data && r.data.error;
        status.textContent = r.status === 0 ? t("cannot_connect") : code === "no_chapter" ? t("chapter_closed") : t("no_earlier");
        return;
      }
      d = r.data;
      fetched.set(key, d);
    }
    unfolded.add(key);
    open(d);
  };
  btn.addEventListener("click", toggle);
  box.append(btn, status, out);
  if (unfolded.has(key) && fetched.has(key)) open(fetched.get(key));
  return box;
}

panelSection({
  name: "earlier",
  order: 20,
  render(ctx) {
    const rec = recordOf(ctx.book, ctx.chapter.id);
    const change = changeOf(rec, ctx.p.a);
    if (!change || change.new || !rec.since) return null;
    return earlierBlock(ctx, change, rec);
  },
});

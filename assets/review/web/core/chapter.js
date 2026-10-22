/* Proofreading site: an open chapter (web/core/chapter.js).

   The chapter's head, its paragraphs (para.js), the sections at its end (the chapterSection place of
   ext.js), the "finished" box with the way to the next chapter, and the reader's place, which is
   recorded only after the reader scrolls, never after a jump. */

import { overlay, queueSet } from "./outbox.js";
import { S, store, on } from "./state.js";
import { K } from "./store.js";
import { t } from "./words.js";
import { h, $, shortA, paraId, drawn } from "./dom.js";
import { active, hintKey, variantOf } from "./ext.js";
import { loadOb, mutateOb, flush, schedule, PLACE_DELAY_MS, keptChapter, keptComments, revalidateChapter, loadComments } from "./net.js";
import { bookLang } from "./languages.js";
import { setHash, setBar, goHome } from "./screens.js";
import { showHome, titleLines } from "./home.js";
import { renderPara, paintPara, openDrawer } from "./para.js";
import { editNote } from "./notes.js";

const enc = encodeURIComponent;

export const meChapter = () => (S.me ? S.me.chapters.find(c => c.book === S.book && c.id === S.ch) : null);

export function leaveChapter() {
  if (S.view !== "chapter") return;
  stopTracking();
  S.book = S.ch = S.chapter = S.waiting = null;
  S.openNote = null;
}

export function openChapter(book, id, opts) {
  const meCh = S.me && S.me.chapters.find(c => c.book === book && c.id === id);
  if (!meCh) { setHash("", false); return showHome(); }
  leaveChapter();
  S.view = "chapter";
  S.book = book;
  S.ch = id;
  setHash("#" + enc(book) + "/" + enc(id), !!opts.push);
  setBar(meCh);
  const data = keptChapter(book, id);
  if (data) renderChapter(data, opts.resume);
  else {
    const main = $("main");
    main.textContent = "";
    main.append(h("p", { class: "lead loading", text: t("loading") }));
    window.scrollTo(0, 0);
  }
  revalidateChapter(book, id);
  loadComments(book, id);
}

/* Open a chapter at one paragraph with one of the reader's comments ready to change. */
export function openComment(book, id, a, cid) {
  openChapter(book, id, { resume: false });
  if (S.view !== "chapter") return;
  S.openNote = { a, cid };
  if (S.chapter) applyOpenNote();
}

function applyOpenNote() {
  const want = S.openNote;
  S.openNote = null;
  const p = want && S.chapter && S.chapter.paras.find(x => x.a === want.a);
  const art = p && document.getElementById(paraId(p.a));
  if (!art) return;
  jumpTo(p.a, false);
  openDrawer(art, p, null);
  editNote(art, p, want.cid);
}

export function showChapterMessage(text, canRetry) {
  if (S.view !== "chapter") return;
  stopTracking();
  S.chapter = null;
  const book = S.book, id = S.ch;
  const main = $("main");
  main.textContent = "";
  main.append(h("section", { class: "message" },
    h("p", { class: "lead", text }),
    h("div", { class: "row" },
      canRetry ? h("button", { type: "button", class: "btn", text: t("retry_load"), onclick: () => openChapter(book, id, { resume: true }) }) : null,
      h("button", { type: "button", class: "btn ghost", text: t("all_chapters"), onclick: goHome }))));
  window.scrollTo(0, 0);
}

/* A chapter text arrived for the open chapter. Draw it if nothing is drawn yet; redraw only when
   it differs from what is on screen, and not while a comment drawer is open. */
export function offerChapter(data) {
  if (!S.chapter) return renderChapter(data, true);
  if (data.version === S.chapter.version && data.variant === S.chapter.variant) return;
  if (document.querySelector("#main .para.open")) { S.waiting = data; return; }
  keepPosition(() => renderChapter(data, false));
}

/* Draw the open chapter again in place, as after a change of language; not while a drawer is open. */
export function redrawChapter() {
  if (!S.chapter || document.querySelector("#main .para.open")) return;
  const data = S.chapter;
  keepPosition(() => renderChapter(data, false));
}

/* Redraw without moving the paragraph at the top of the screen. */
export function keepPosition(fn) {
  const barBottom = $("bar").getBoundingClientRect().bottom;
  const top = [...document.querySelectorAll("#main .para")].find(x => x.getBoundingClientRect().bottom > barBottom + 1);
  const a = top && top.dataset.a;
  const off = top ? top.getBoundingClientRect().top : 0;
  fn();
  const el = a && document.getElementById(paraId(a));
  if (el) { markJump(); window.scrollBy(0, el.getBoundingClientRect().top - off); }
}

export function renderChapter(data, resume) {
  stopTracking();
  S.chapter = data;
  S.waiting = null;
  setBar(meChapter() || data);
  const main = $("main");
  main.textContent = "";
  main.append(h("header", { class: "ch-head" },
    h("p", { class: "eyebrow", text: t("chapter_n", { n: data.n }) }),
    h("h1", { lang: bookLang(data.book), text: data.title_th }),
    titleLines(data, "head"),
    h("p", { class: "hint", text: t(hintKey(S.me)) })));
  const list = currentComments();
  for (const p of data.paras) main.append(renderPara(p, list));
  main.append(renderSections(list), renderFinish());
  const c = meChapter();
  $("bar-place").textContent = c && c.place ? shortA(c.place) : "";
  if (resume) resumePlace();
  startTracking();
  if (S.openNote) applyOpenNote();
}

function resumePlace() {
  const c = meChapter();
  const first = S.chapter.paras[0];
  const target = c && c.place && first && c.place !== first.a ? c.place : null;
  if (!(target && jumpTo(target, true))) { markJump(); window.scrollTo(0, 0); }
  // The font may arrive after the jump and move the text; jump again unless the reader has scrolled.
  if (target && document.fonts && document.fonts.ready) {
    const ch = S.ch;
    document.fonts.ready.then(() => { if (!armed && S.ch === ch) jumpTo(target, false); });
  }
}

export function jumpTo(a, withFlash) {
  const el = document.getElementById(paraId(a));
  if (!el) return false;
  markJump();
  el.scrollIntoView({ block: "start" });
  if (withFlash) {
    el.classList.remove("flash");
    void el.offsetWidth;
    el.classList.add("flash");
  }
  return true;
}

export function currentComments() {
  return overlay(keptComments(S.book, S.ch) || [], loadOb(), S.book, S.ch, S.code);
}

export function repaintComments() {
  if (S.view !== "chapter" || !S.chapter) return;
  const list = currentComments();
  for (const art of document.querySelectorAll("#main .para")) paintPara(art, list);
  const box = $("ch-sections");
  if (!box) return;
  const ctx = sectionCtx(list);
  for (const d of active("sections", S.me)) {
    if (!d.refresh) continue;
    const old = Array.from(box.children).find(x => x.getAttribute("data-section") === d.name);
    if (old) old.replaceWith(drawSection(d, ctx));
  }
}

/* ---- sections at the end of the chapter (ext.js, chapterSection) ---- */

const sectionCtx = list => ({ chapter: S.chapter, comments: list, me: S.me, book: S.book });

function drawSection(d, ctx) {
  const el = drawn(d, ctx) || h("div", { hidden: true });
  el.setAttribute("data-section", d.name);
  return el;
}

function renderSections(list) {
  const ctx = sectionCtx(list);
  return h("div", { class: "ch-sections", id: "ch-sections" }, active("sections", S.me).map(d => drawSection(d, ctx)));
}

/* ---- the end of the chapter ---- */

function renderFinish() {
  const c = meChapter();
  const done = !!(c && c.finished);
  const sibs = S.me.chapters.filter(x => x.book === S.book).sort((x, y) => x.n - y.n);
  const i = sibs.findIndex(x => x.id === S.ch);
  const prev = i > 0 ? sibs[i - 1] : null, next = i >= 0 ? sibs[i + 1] : null;
  const pageBtn = (x, cls, label) => h("button", { type: "button", class: "pager-btn " + cls, onclick: () => openChapter(x.book, x.id, { resume: true }) },
    h("span", { class: "page-dir", text: label }), h("span", { class: "page-title", lang: bookLang(x.book), text: x.title_th }));
  return h("section", { class: "finish" + (done ? " is-done" : ""), id: "finish" },
    h("h2", { text: done ? t("finish_done") : t("finish_q") }),
    h("div", { class: "row" },
      h("button", { type: "button", class: done ? "btn ghost" : "btn done", text: done ? t("finish_undo") : t("finish_btn"), onclick: () => setFinished(!done) })),
    h("nav", { class: "pager" },
      prev ? pageBtn(prev, "prev", t("prev")) : null,
      next ? pageBtn(next, "next", t("next")) : null),
    h("button", { type: "button", class: "btn ghost wide", text: t("all_chapters"), onclick: goHome }));
}

function setFinished(v) {
  const c = meChapter();
  if (!c) return;
  c.finished = v;
  store.set(K.me, S.me);
  mutateOb(ob => queueSet(ob, "finished", { book: S.book, ch: S.ch, finished: v }, S.code, Date.now(), 0));
  $("finish").replaceWith(renderFinish());
  flush();
}

/* ---- the reader's place: recorded only after the reader scrolls, never after a jump ---- */

let armed = false, jumpedAt = 0, observer = null, placeTimer = 0, pendingPlace = null;
export function markJump() { jumpedAt = Date.now(); armed = false; }
export function onScroll() { if (Date.now() - jumpedAt > 800) armed = true; }

function startTracking() {
  stopTracking();
  if (!("IntersectionObserver" in window)) return;
  observer = new IntersectionObserver(entries => {
    for (const e of entries) {
      if (!e.isIntersecting || !armed || S.view !== "chapter") continue;
      const a = e.target.dataset.a;
      $("bar-place").textContent = shortA(a);
      pendingPlace = { book: S.book, ch: S.ch, a };
      clearTimeout(placeTimer);
      placeTimer = setTimeout(savePlace, 2500);
    }
  }, { rootMargin: "-25% 0px -65% 0px" });
  for (const p of document.querySelectorAll("#main .para")) observer.observe(p);
}

function stopTracking() {
  if (observer) observer.disconnect();
  observer = null;
  savePlace();
}

export function savePlace() {
  clearTimeout(placeTimer);
  const p = pendingPlace;
  pendingPlace = null;
  if (!p || !S.me) return;
  const c = S.me.chapters.find(x => x.book === p.book && x.id === p.ch);
  if (!c || c.place === p.a) return;
  c.place = p.a;
  store.set(K.me, S.me);
  mutateOb(ob => queueSet(ob, "place", { book: p.book, ch: p.ch, a: p.a }, S.code, Date.now(), PLACE_DELAY_MS));
  schedule(0);
}

/* The page is being hidden: send the place now rather than after the usual wait. */
export function sendPlaceNow() {
  savePlace();
  mutateOb(ob => { for (const o of ob) if (o.type === "place" && !o.tries) o.next = 0; return ob; });
  flush();
}

/* ---- news from net.js ---- */

on("chapter", ev => {
  if (S.view !== "chapter" || S.book !== ev.book || S.ch !== ev.id) return;
  if (ev.gone) showChapterMessage(t("chapter_closed"), false);
  else if (ev.data) offerChapter(ev.data);
  else if (!S.chapter) showChapterMessage(t("not_on_device"), true);
});

/* A new chapter list: the open chapter is fetched again when its version, or the features that shape
   its text, changed; otherwise only the bar and the "finished" box are drawn again. */
export function onMeInChapter() {
  const c = meChapter();
  if (!c || !S.chapter || c.version !== S.chapter.version || variantOf(S.me) !== S.chapter.variant) revalidateChapter(S.book, S.ch);
  else {
    setBar(c);
    $("bar-place").textContent = c.place ? shortA(c.place) : "";
    const f = $("finish");
    if (f) f.replaceWith(renderFinish());
  }
}

/* Proofreading site: the router and the plain screens (web/core/screens.js).

   The address holds the open chapter as #SC/SC03, "My earlier comments" as #earlier, and "Your devices" as
   #account; an empty hash is the chapter list. This module also draws the link, offline, loading and device
   screens, the list of comments the server refused (with the unsaved drafts whose paragraph is no longer
   open), the note at the foot of the screen, the bar with its "Show spaces" button, and the settings. The
   screens of signing in are core/signin.js's, and "Your devices" is core/account.js's. */

import { ownerOf } from "./outbox.js";
import { S, store } from "./state.js";
import { ownerTag, parseDraftKey } from "./store.js";
import { t, tIn, plural, hasWords, loadWords, setLang, UI_LANGS } from "./words.js";
import { h, $, shortA, copyButton, twoTapButton, drawn, spacesOn } from "./dom.js";
import { active, settingsItem } from "./ext.js";
import { loadOb, mutateOb, refreshMe, keptChapter, who } from "./net.js";
import { explain } from "./refusals.js";
import { bookLang, showLanguages, shownLanguages } from "./languages.js";
import { leaveChapter, openChapter, openComment, redrawChapter } from "./chapter.js";
import { showHome, renderHome } from "./home.js";
import { failText } from "./notes.js";
import { showEarlier } from "./earlier.js";
import { showAuthAgain, redrawAuth, showBlocked } from "./signin.js";
import { showAccount, redrawAccount } from "./account.js";

export function setHash(hash, push) {
  const url = location.pathname + location.search + hash;
  try {
    if (push) history.pushState({ list: true }, "", url);
    else history.replaceState(hash ? history.state : null, "", url);
  } catch (e) { /* history is not available here */ }
}

export function route() {
  if (store.blocked) return showBlocked();
  if (!S.mode || S.authBlocked) return showAuthAgain();
  if (S.deviceWaiting) return showDeviceWaiting();
  if (!S.me) return showBoot();
  if (location.hash === "#earlier") {
    if (S.view !== "earlier") showEarlier(false);
    return;
  }
  if (location.hash === "#account") {
    if (S.mode !== "session") { setHash("", false); return showHome(); }
    if (S.view !== "account") showAccount(false, null);
    return;
  }
  const m = /^#([^/=&]+)\/([^/=&]+)$/.exec(location.hash);
  if (m) {
    let book, id;
    try { book = decodeURIComponent(m[1]); id = decodeURIComponent(m[2]); } catch (e) { return showHome(); }
    if (S.view === "chapter" && S.book === book && S.ch === id) return;
    return openChapter(book, id, { resume: true });
  }
  if (S.view !== "home") showHome();
}

export function goHome() {
  if (history.state && history.state.list) { history.back(); return; }   // popstate draws the list
  setHash("", false);
  showHome();
}

export function applyLang() {
  document.documentElement.lang = S.lang;
  document.title = t("app_title");
  $("back").textContent = t("back");
  paintSpaces();
  showLanguages(shownLanguages());
}

/* Draw the screen again in the language now chosen, or with new words. */
export function rerender() {
  applyLang();
  if (S.view === "home") renderHome(true);
  else if (S.view === "link") showLink();
  else if (S.view === "signin" || S.view === "blocked") redrawAuth();
  else if (S.view === "account") redrawAccount();
  else if (S.view === "offline") showOffline();
  else if (S.view === "unsaved") showUnsaved();
  else if (S.view === "device") showDeviceWaiting();
  else if (S.view === "earlier") showEarlier(false);
  else if (S.view === "chapter") redrawChapter();
  paintSync();
}

/* The bar shows inside a chapter: the way back, the chapter, the reader's place and the "Show spaces"
   button. Given a title instead of a chapter, as on "My earlier comments", it shows the way back and that
   title only. */
export function setBar(c, title) {
  $("bar").hidden = !c && !title;
  $("bar-title").textContent = c ? c.n + " · " + c.title : title || t("app_title");
  const lg = c ? bookLang(c.book) : null;
  if (lg) $("bar-title").lang = lg; else $("bar-title").removeAttribute("lang");
  $("bar-place").textContent = "";
  $("bar-spaces").hidden = !c;
}

/* The "Show spaces" button in the bar: a faint dot on every space of the book text, a choice kept on this
   device (dom.js, setSpaces). */
export function paintSpaces() {
  const b = $("bar-spaces");
  if (!b) return;
  b.textContent = t("show_spaces");
  b.setAttribute("aria-pressed", String(spacesOn()));
}

let devicePoll = 0;

export function showScreen(view, ...kids) {
  leaveChapter();
  if (view !== "device") { clearInterval(devicePoll); devicePoll = 0; }
  S.view = view;
  setBar(null);
  const main = $("main");
  main.textContent = "";
  main.append(...kids);
  window.scrollTo(0, 0);
}

/* ---- settings: the language switch is the first item; features add theirs (ext.js) ---- */

function langSwitch() {
  return h("div", { class: "lang", role: "group", "aria-label": t("language") },
    UI_LANGS.map(l => h("button", { type: "button", class: "lang-btn", lang: l, "aria-pressed": String(S.lang === l),
      text: tIn(l, "lang_" + l), onclick: () => setLang(l) })));
}
settingsItem({ name: "language", order: 0, render: () => langSwitch() });

/* The settings of a screen. On the link, offline and sign-in screens there is no chapter list, so only the
   language switch shows. */
export function settingsBar(screen) {
  const me = screen === "home" ? S.me : null;
  return h("div", { class: "settings" }, active("settings", me).map(d => drawn(d, { me, screen })));
}

/* ---- plain screens ---- */

export function showBoot() {
  showScreen("boot", h("div", { class: "boot", "aria-hidden": "true" }));
}

export function showLink() {
  showScreen("link", h("section", { class: "message" },
    h("div", { class: "home-top" }, h("h1", { text: t("link_title") }), settingsBar("link")),
    h("p", { class: "lead", text: t("link_body") })));
}

/* The link already works on other devices, and this one waits until the translator lets it in (403
   device_waiting). The page keeps everything on the device, asks the site again every two minutes while
   the screen shows, and draws the chapter list once the site answers (main.js, on "me"). */
export function showDeviceWaiting() {
  const status = h("p", { class: "status", "aria-live": "polite" });
  const btn = h("button", { type: "button", class: "btn", text: t("device_check") });
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    status.textContent = t("device_checking");
    await refreshMe();
    if (S.view !== "device") return;   // let in: the chapter list is drawn
    btn.disabled = false;
    status.textContent = S.meStatus === 0 ? t("cannot_connect") : t("device_still");
  });
  const unsent = loadOb().some(o => ownerOf(o) === who()) || ownDrafts().length > 0;
  // The device's number, as the translator's lists show it, so the reader can say which device to let in.
  const number = typeof S.deviceNumber === "number" ? h("p", { class: "lead device-number", text: t("device_number", { n: String(S.deviceNumber) }) }) : null;
  showScreen("device", h("section", { class: "message" },
    h("div", { class: "home-top" }, h("h1", { text: t("device_title") }), settingsBar("device")),
    h("p", { class: "lead", text: t("device_body") }),
    h("p", { class: "lead", text: t("device_todo") }),
    number,
    unsent ? h("p", { class: "lead", text: t("device_kept") }) : null,
    h("div", { class: "row" }, btn),
    status));
  if (!devicePoll) {
    devicePoll = setInterval(() => {
      // The chapter list or a chapter took the screen's place: the device was let in.
      if (S.view !== "device" || !S.deviceWaiting) { clearInterval(devicePoll); devicePoll = 0; return; }
      if (document.visibilityState !== "hidden") refreshMe();
    }, 120000);
  }
}

/* The site cannot be reached and nothing is on the device to show. again, when given, is what Try again
   does, as asking a link's claim again; it is kept for the redraw after a change of language. */
let offlineAgain = null;
export function showOffline(again) {
  if (typeof again === "function") offlineAgain = again;
  else if (S.view !== "offline") offlineAgain = null;
  const then = offlineAgain;
  const retry = async () => {
    showBoot();
    if (!hasWords() && (await loadWords())) applyLang();
    if (then) then();
    else refreshMe();
  };
  showScreen("offline", h("section", { class: "message" },
    h("div", { class: "home-top" }, h("h1", { text: t("app_title") }), settingsBar("offline")),
    h("p", { class: "lead", text: t("cannot_connect") }),
    h("button", { type: "button", class: "btn", text: t("retry_load"), onclick: retry })));
}

/* ---- the note at the foot of the screen ----
   Comments the server refused make it a button that lists them; changes that wait because the
   reader is offline, or because the server asked to try later, show as a count. */

/* The screens on which the note shows nothing: before a reader is signed in, no reader's words are shown. */
const QUIET = ["signin", "blocked", "link", "boot"];

export function paintSync() {
  const el = $("sync");
  if (!el) return;
  if (QUIET.indexOf(S.view) >= 0) { el.textContent = ""; el.hidden = true; return; }
  const ob = loadOb().filter(o => ownerOf(o) === who());
  const waiting = ob.filter(o => !o.failed).length;
  const failed = ob.length - waiting + goneDrafts().length + orphanOps().length;
  const offline = S.netFails > 0 || navigator.onLine === false;
  const retrying = ob.some(o => !o.failed && o.tries > 0);
  el.textContent = "";
  el.classList.toggle("bad", failed > 0);
  el.classList.toggle("has-btn", failed > 0);
  if (failed) {
    if (S.view !== "unsaved") el.append(h("button", { type: "button", class: "sync-btn", text: plural(failed, "failed_one", "failed_many"), onclick: showUnsaved }));
  } else if (waiting && offline) el.textContent = t("offline") + " · " + plural(waiting, "waiting_one", "waiting_many");
  else if (waiting && retrying) el.textContent = plural(waiting, "waiting_one", "waiting_many");
  el.hidden = !el.textContent;
}

/* ---- comments the server refused ---- */

const failedOps = () => loadOb().filter(o => ownerOf(o) === who() && o.failed);

/* Comments written under a link whose reader number this device never learnt, other than the link open now: a
   page of round 3b wrote them under a link that no chapter list answered on this device. They stay in the
   outbox, never deleted unasked, and go out if that link opens here again; meanwhile the list of comments not
   saved shows their words. */
export function orphanOps() {
  const now = who();
  return loadOb().filter(o => {
    const w = ownerOf(o);
    return typeof w === "string" && w !== now && !!o.cid && (o.type === "create" || o.type === "update") && !!o.body;
  });
}

/* The drafts of the reader signed in now: [{tag, book, ch, a, key}]. Drafts of other readers stay on the
   device, unseen, until their reader signs in on this browser again (net.js). */
export function ownDrafts() {
  const tag = ownerTag(who());
  if (!tag) return [];
  const out = [];
  for (const key of store.keys()) {
    const d = parseDraftKey(key);
    if (d && d.tag === tag) out.push(Object.assign(d, { key }));
  }
  return out;
}

/* The reader's unsaved drafts that no drawer shows any more: their chapter is closed now, or the chapter
   kept on the device no longer has their paragraph. A chapter not kept yet is not judged. */
export function goneDrafts() {
  if (!S.me) return [];
  const anchors = {};
  const has = (book, ch, a) => {
    const key = book + "/" + ch;
    if (!(key in anchors)) {
      const kept = S.chapter && S.book === book && S.ch === ch ? S.chapter : keptChapter(book, ch);
      anchors[key] = kept ? new Set(kept.paras.map(p => p.a)) : null;
    }
    return !anchors[key] || anchors[key].has(a);
  };
  const out = [];
  for (const d of ownDrafts()) {
    const open = S.me.chapters.some(x => x.book === d.book && x.id === d.ch);
    if (open && has(d.book, d.ch, d.a)) continue;
    const body = store.get(d.key);
    if (!body || (!body.text && !body.quote)) continue;
    out.push(Object.assign(d, { body }));
  }
  return out;
}

/* A card for a draft whose paragraph is gone: its words, why it cannot be saved, Copy and Remove. */
function draftCard(d) {
  const c = S.me && S.me.chapters.find(x => x.book === d.book && x.id === d.ch);
  const where = (c ? t("chapter_n", { n: c.n }) : d.ch) + " · " + t("para_n", { a: shortA(d.a) });
  const words = h("div", { class: "note-words", lang: bookLang(d.book) },
    d.body.quote ? h("p", { class: "note-quote", text: "“" + d.body.quote + "”" }) : null,
    h("p", { class: "note-text", text: d.body.text || "" }));
  const all = (d.body.quote ? "“" + d.body.quote + "”\n" : "") + (d.body.text || "");
  const remove = () => {
    store.del(d.key);
    showUnsaved();
  };
  return h("div", { class: "note failed" },
    h("p", { class: "note-where", text: where }),
    words,
    h("p", { class: "note-why", text: t("draft_gone") }),
    h("div", { class: "note-acts" }, copyButton(all, words), twoTapButton(t("remove"), t("remove_confirm"), remove)));
}

/* A card for a comment of orphanOps(): its words, where it was written, Copy and Remove. */
function orphanCard(o) {
  const where = o.ch + " · " + t("para_n", { a: shortA(o.a) });
  const body = o.body || {};
  const words = h("div", { class: "note-words", lang: bookLang(o.book) },
    body.quote ? h("p", { class: "note-quote", text: "“" + body.quote + "”" }) : null,
    h("p", { class: "note-text", text: body.text || "" }));
  const all = (body.quote ? "“" + body.quote + "”\n" : "") + (body.text || "");
  const remove = () => {
    mutateOb(ob => ob.filter(x => x.cid !== o.cid));
    showUnsaved();
  };
  return h("div", { class: "note failed" },
    h("p", { class: "note-where", text: where }),
    words,
    h("p", { class: "note-why", text: t("orphan_op") }),
    h("div", { class: "note-acts" }, copyButton(all, words), twoTapButton(t("remove"), t("remove_confirm"), remove)));
}

/* Whether the comment of a refused op can be opened for a change: its chapter is open to the reader
   and its paragraph is in the chapter as kept on the device (or the chapter is not kept yet). */
function canOpen(o) {
  if (!o.cid || !o.a || !S.me || !S.me.chapters.some(x => x.book === o.book && x.id === o.ch)) return false;
  const kept = keptChapter(o.book, o.ch);
  return !kept || kept.paras.some(p => p.a === o.a);
}

function unsavedCard(o) {
  const c = S.me && S.me.chapters.find(x => x.book === o.book && x.id === o.ch);
  const where = (c ? t("chapter_n", { n: c.n }) : o.ch) + " · " + t("para_n", { a: shortA(o.a) });
  const body = o.body || {};
  const words = h("div", { class: "note-words", lang: bookLang(o.book) },
    body.quote ? h("p", { class: "note-quote", text: "“" + body.quote + "”" }) : null,
    h("p", { class: "note-text", text: body.text || "" }));
  const all = (body.quote ? "“" + body.quote + "”\n" : "") + (body.text || "");
  const why = explain(o.failed, S.me && S.me.limits);
  const remove = () => {
    mutateOb(ob => ob.filter(x => (o.type === "create" ? x.cid !== o.cid : x.op !== o.op)));
    showUnsaved();
  };
  const change = why.change && canOpen(o)
    ? h("button", { type: "button", class: "link", text: t("edit"), onclick: () => openComment(o.book, o.ch, o.a, o.cid) }) : null;
  return h("div", { class: "note failed" },
    h("p", { class: "note-where", text: where }),
    words,
    h("p", { class: "note-why", text: failText(why) }),
    h("div", { class: "note-acts" }, change, copyButton(all, words), twoTapButton(t("remove"), t("remove_confirm"), remove)));
}

/* Every comment the server refused, from any chapter, even one that is closed now, then every unsaved
   draft whose paragraph is no longer open. */
export function showUnsaved() {
  if (S.view !== "unsaved") S.from = S.view === "chapter" ? { book: S.book, ch: S.ch } : null;
  const from = S.from;
  const close = () => {
    if (from) openChapter(from.book, from.ch, { resume: true });
    else { setHash("", false); showHome(); }
  };
  const list = failedOps();
  const drafts = goneDrafts();
  const orphans = orphanOps();
  showScreen("unsaved", h("section", { class: "message" },
    h("h1", { text: t("unsaved_title") }),
    list.length || !(drafts.length || orphans.length) ? h("p", { class: "lead", text: list.length ? t("unsaved_lead") : t("unsaved_none") }) : null,
    h("div", { class: "notes" }, list.map(unsavedCard), drafts.map(draftCard), orphans.map(orphanCard)),
    h("div", { class: "row" }, h("button", { type: "button", class: "btn ghost", text: t("close"), onclick: close }))));
  paintSync();
}

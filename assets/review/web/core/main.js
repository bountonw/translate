/* Proofreading site: the start of the page (web/core/main.js).

   web/app.js loads this module and calls boot(). It reads the link, loads the words, the languages
   and the chapter list, wires the page's events, and loads the features. Each feature's page part is
   one module in web/features/, named only by its modulepreload line in web/index.html: boot() loads
   every such module with its own import() before the page starts, so a feature that fails as it
   loads is logged and left out, and the page works without it. The same line makes the browser fetch
   the file at once and the service worker keep it for offline use. */

// Every core module is named here, so that each one runs before the page starts, whichever module
// first needs it.
import "./ext.js";
import "./refusals.js";
import "./notes.js";
import "./changes.js";
import "./updates.js";
import "./earlier.js";

import { applyPending } from "./outbox.js";
import { upgradeMe } from "./model.js";
import { K } from "./store.js";
import { S, store, on } from "./state.js";
import { t, useKeptWords, loadWords, hasWords, keptLang } from "./words.js";
import { showNotice, spacesOn, setSpaces } from "./dom.js";
import { loadOb, flush, refreshMe, startMe, forgetReader, schedulePrefetch, adoptOldDrafts } from "./net.js";
import { useKeptLanguages, loadLanguages, showLanguages, shownLanguages, loadedFontFiles } from "./languages.js";
import { route, rerender, applyLang, paintSync, paintSpaces, showLink, showOffline, showDeviceWaiting, goHome, setHash } from "./screens.js";
import { renderHome } from "./home.js";
import { repaintComments, onScroll, onMeInChapter, savePlace, sendPlaceNow } from "./chapter.js";
import { onSelection } from "./para.js";

/* ---- news from net.js ---- */

on("sync", paintSync);
on("auth", showLink);
on("offline", showOffline);
on("device", () => { if (S.view !== "device") showDeviceWaiting(); });
on("lang", rerender);
on("me", () => {
  showLanguages(shownLanguages());
  if (S.view === "boot" || S.view === "offline" || S.view === "device") route();
  else if (S.view === "home") renderHome(false);
  else if (S.view === "chapter") {
    onMeInChapter();
    repaintComments();    // a refusal's message names the site's limits, which may have changed (48 UX3-5)
  }
  paintSync();          // a draft whose chapter closed now counts as unsaved
  schedulePrefetch();
});
on("chapter", () => paintSync());   // so does a draft whose paragraph a new version dropped
const onCommentsOf = (book, ch) => {
  if (S.view === "chapter" && book === S.book && ch === S.ch) repaintComments();
  else if (S.view === "home") renderHome(false);
};
on("result", r => onCommentsOf(r.op.book, r.op.ch));
on("comments", ev => onCommentsOf(ev.book, ev.id));

/* ---- events of the browser ---- */

function onStorage(ev) {
  if (!ev.key) return;
  if (ev.key === K.code && store.get(K.code) !== S.code) { location.reload(); return; }
  if (ev.key === K.outbox || ev.key.startsWith("rv.cm:")) { repaintComments(); paintSync(); }
  if (ev.key === K.me && S.view === "home") {
    const me = upgradeMe(store.get(K.me));
    if (me) { S.me = me; renderHome(false); }
  }
}

/* A fault in the page's own code shows the general error notice. */
const OWN_CODE = /\/(app|core\/\w+|features\/\w+)\.js(\?|$)/;

/* A link opened in a tab that shows the page already changes only the address's #k=...; the page starts
   again so that boot() reads the new link. */
function onHash() {
  if (/^#(?:.*&)?k=/.test(location.hash)) location.reload();
}

function wireEvents() {
  document.getElementById("back").addEventListener("click", goHome);
  document.getElementById("bar-spaces").addEventListener("click", () => {
    setSpaces(!spacesOn());
    paintSpaces();
  });
  window.addEventListener("popstate", route);
  window.addEventListener("hashchange", onHash);
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("online", () => {
    S.netFails = 0;
    flush();
    if (!S.me || Date.now() - S.meAt > 60000) refreshMe();
  });
  window.addEventListener("offline", paintSync);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") sendPlaceNow();
    else {
      flush();
      if (Date.now() - S.meAt > 60000) refreshMe();
    }
  });
  window.addEventListener("pagehide", savePlace);
  window.addEventListener("storage", onStorage);
  document.addEventListener("selectionchange", onSelection);
  window.addEventListener("error", ev => { if (ev.filename && OWN_CODE.test(ev.filename)) showNotice(t("error_generic")); });
}

/* The service worker keeps the page's files on the device; it needs https. Once the page has
   started, it asks the worker to fetch the newest files for the next visit, all together, so a visit
   never mixes files of two versions, and names the font files loaded so far, which the worker keeps
   if it does not hold them yet (a browser may reuse a font it loaded before the worker took over). */
function registerWorker() {
  if (!("serviceWorker" in navigator) || location.protocol !== "https:") return;
  navigator.serviceWorker.register("sw.js").catch(() => { /* the page works without it */ });
  setTimeout(() => {
    const w = navigator.serviceWorker.controller;
    if (!w) return;
    w.postMessage("refresh");
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => w.postMessage({ fonts: loadedFontFiles() }));
  }, 3000);
}

function start() {
  applyLang();
  registerWorker();
  if (!S.code) return showLink();
  S.me = upgradeMe(store.get(K.me));
  if (S.me) S.me = applyPending(S.me, loadOb(), S.code);
  showLanguages(shownLanguages());
  route();
  refreshMe();
  flush();
}

/* The page parts of the features: every module index.html names under features/ in a modulepreload line,
   each loaded with its own catch. Resolves when every one has loaded or failed. doc is the document. */
const FEATURE_HREF = /^features\/[a-z0-9_-]+\.js$/;
export function loadFeatures(doc) {
  const hrefs = Array.from(doc.querySelectorAll('link[rel="modulepreload"]'))
    .map(l => l.getAttribute("href"))
    .filter(href => FEATURE_HREF.test(href || ""));
  return Promise.all(hrefs.map(href => import("../" + href)
    .then(() => true, err => { console.error("feature " + href + " did not load", err); return false; })));
}

export function boot() {
  S.lang = keptLang();
  // The link is https://<host>/#k=<code>. The fragment never reaches the server; it is kept here
  // and taken out of the address bar.
  // Codes hold only A-Z, a-z, 0-9, _ and -, so a full stop or bracket after the link is left out.
  const m = /^#(?:.*&)?k=([A-Za-z0-9_-]+)/.exec(location.hash);
  // Drafts kept by a page before round 3b belong to the link the device held then (net.js, adoptOldDrafts).
  adoptOldDrafts(store.get(K.code) || (m && m[1]));
  if (m) {
    let code = m[1];
    try { code = decodeURIComponent(code); } catch (e) { /* keep it as it is */ }
    if (code !== store.get(K.code)) forgetReader();
    store.set(K.code, code);
    setHash("", false);
  }
  S.code = store.get(K.code);
  useKeptWords();
  useKeptLanguages();
  wireEvents();
  // Ask for the chapter list at the same time as the words, so a first visit waits for one fetch at most.
  startMe();
  loadLanguages();
  // The features register their entries in ext.js as they load, so the page starts once they have.
  const features = loadFeatures(document);
  const fresh = loadWords();
  if (hasWords()) {
    features.then(start);
    fresh.then(changed => { if (changed) rerender(); });
  } else {
    Promise.all([fresh, features]).then(start);
  }
}

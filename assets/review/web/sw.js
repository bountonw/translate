/* Proofreading site: service worker (web/sw.js).

   Keeps the page's own files on the device, so the site opens at once and opens offline. The files
   are BASE below and every module that index.html names in a <link rel="modulepreload"> line: that
   list in index.html is the one list of the page's modules, which the browser also uses to fetch them
   all at once. tests/test_web.py checks that it names every module of web/core/ and web/features/.
   A new module therefore needs no change here.

   A visit is served from the device. Once the page has started, it asks this worker to fetch the
   newest index.html and every file it lists; only when all of them arrive does the worker keep them,
   all together, in place of the old ones, so the next visit shows the new version and never mixes
   files of two versions. A change to this file itself needs a new CACHE name.

   Fonts are kept the first time the page loads each one, in a cache of their own that survives a new
   CACHE name, so a reader downloads only the fonts of the languages they read, and only once. The page
   also names the font files it has loaded, and the worker keeps any it does not hold yet: a browser
   may reuse a font it loaded before this worker took over, and then never asks for it here. API
   calls are never touched here: the page keeps its own copy of chapters and comments. app.js registers
   this file only over https. To retire it, replace this file with one that calls
   self.registration.unregister(). */
"use strict";

const CACHE = "review-shell-2";
const FONTS = "review-fonts-1";
const BASE = ["./", "app.css", "app.js", "ui-strings.json", "languages.json"];
const MODULE_LINK = /<link rel="modulepreload" href="((?:core|features)\/[a-z0-9_-]+\.js)">/g;
const ROOT = new URL("./", self.location).pathname;
const FONT_DIR = ROOT + "fonts/";
const API_DIR = ROOT + "api/";

/* The page's files: BASE and the modules index.html lists. */
function shellOf(html) {
  const out = BASE.slice();
  let m;
  MODULE_LINK.lastIndex = 0;
  while ((m = MODULE_LINK.exec(html))) out.push(m[1]);
  return out;
}

/* Fetch the newest index.html and every file it lists. Resolves to [[path, response]]; rejects when
   any file cannot be had. */
function fetchShell() {
  const get = p => fetch(p, { cache: "no-cache" }).then(res => {
    if (!res.ok) throw new Error(p + ": " + res.status);
    return [p, res];
  });
  return get("./").then(page => page[1].clone().text()
    .then(html => Promise.all(shellOf(html).slice(1).map(get)))
    .then(rest => [page].concat(rest)));
}

/* Keep a fetched set of files in place of the old set. */
function keep(pairs) {
  return caches.open(CACHE).then(c => c.keys().then(old => {
    const wanted = new Set(pairs.map(x => new URL(x[0], self.location).href));
    return Promise.all(pairs.map(x => c.put(x[0], x[1])))
      .then(() => Promise.all(old.filter(req => !wanted.has(req.url)).map(req => c.delete(req))));
  }));
}

self.addEventListener("install", event => {
  event.waitUntil(fetchShell().then(keep).then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE && k !== FONTS).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

/* Keep the font files the page names that the font cache does not hold yet. */
function keepFonts(files) {
  const wanted = files.filter(f => typeof f === "string" && /^fonts\/[A-Za-z0-9._-]+$/.test(f));
  return caches.open(FONTS).then(c => Promise.all(wanted.map(f => c.match(f).then(hit => hit || fetch(f).then(res => {
    if (res.ok) return c.put(f, res);
    return null;
  }))))).catch(() => null);
}

self.addEventListener("message", event => {
  const d = event.data;
  if (d === "refresh") event.waitUntil(fetchShell().then(keep).catch(() => null));   // offline: keep what is here
  else if (d && Array.isArray(d.fonts)) event.waitUntil(keepFonts(d.fonts.slice(0, 50)));
});

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || !url.pathname.startsWith(ROOT) || url.pathname.startsWith(API_DIR)) return;
  if (url.pathname.startsWith(FONT_DIR) && req.mode !== "navigate") {
    event.respondWith(caches.open(FONTS).then(c => c.match(req, { ignoreSearch: true }).then(hit => hit || fetch(req).then(res => {
      if (res.ok) c.put(req, res.clone());
      return res;
    }))));
    return;
  }
  const isPage = req.mode === "navigate" && (url.pathname === ROOT || url.pathname === ROOT + "index.html");
  if (req.mode === "navigate" && !isPage) return;
  const key = isPage ? "./" : req;
  event.respondWith(caches.match(key, { cacheName: CACHE, ignoreSearch: true })
    .then(hit => hit || fetch(isPage ? "./" : req)));
});

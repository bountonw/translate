/* Proofreading site: service worker (web/sw.js).

   Keeps the page's own files (page, script, style, words, fonts) on the device, so the site opens
   at once and opens offline. Each file is served from the device first and refreshed from the
   server in the background, so a new version shows on the next visit. API calls are never touched
   here: app.js keeps its own cache of chapters and comments. app.js registers this file only over
   https. To retire it, replace this file with one that calls self.registration.unregister(). */
"use strict";

const CACHE = "review-shell-1";
const SHELL = [
  "./", "app.css", "app.js", "ui-strings.json",
  "fonts/Sarabun-Regular.ttf", "fonts/Sarabun-Italic.ttf", "fonts/Sarabun-Medium.ttf", "fonts/Sarabun-SemiBold.ttf",
];
const ROOT = new URL("./", self.location).pathname;
const SHELL_PATHS = new Set(SHELL.map(p => new URL(p, self.location).pathname));

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  const isPage = req.mode === "navigate" && (url.pathname === ROOT || url.pathname === ROOT + "index.html");
  if (!isPage && (req.mode === "navigate" || !SHELL_PATHS.has(url.pathname))) return;
  const key = isPage ? "./" : req;
  const net = fetch(isPage ? "./" : req, { cache: "no-cache" })
    .then(res => ({ res, copy: res.ok ? res.clone() : null }));
  event.waitUntil(net
    .then(({ copy }) => copy && caches.open(CACHE).then(c => c.put(key, copy)))
    .catch(() => null));
  event.respondWith(caches.match(key, { cacheName: CACHE, ignoreSearch: true })
    .then(hit => hit || net.then(x => x.res)));
});

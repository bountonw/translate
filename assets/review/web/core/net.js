/* Proofreading site: talking to the server (web/core/net.js).

   The API calls, the outbox runner, and the chapter list, chapters and comment lists kept on the
   device. The page draws from the device first and checks the server in the background (chapters by
   ETag). This module draws nothing: it tells the drawing modules what changed through emit() in
   state.js. */

import { TIMEOUT_MS, PLACE_DELAY_MS, backoff, flushOnce, nextWake, applyPending, pendingCreates } from "./outbox.js";
import { normMe, normChapter, normComments } from "./model.js";
import { variantOf } from "./ext.js";
import { K, chKey, cmKey, parseDraftKey } from "./store.js";
import { S, store, emit } from "./state.js";

export { PLACE_DELAY_MS };
const enc = encodeURIComponent;

/* A file of the page itself, such as ui-strings.json, as JSON; null when it cannot be had. */
export async function getFile(path) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(path, { cache: "no-cache", credentials: "omit", signal: ctl.signal });
    if (!r.ok) return null;
    const d = await r.json();
    return d && typeof d === "object" ? d : null;
  } catch (e) {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/* Retry-After in ms: whole seconds only, at most ten minutes. */
function retryAfter(r) {
  const s = Number(r.headers.get("Retry-After"));
  return s > 0 ? Math.min(600, s) * 1000 : 0;
}

/* One API call. Returns {status, data, etag, wait}; status 0 means offline or timed out. */
export async function api(method, path, opts) {
  opts = opts || {};
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  const headers = { Authorization: "Bearer " + (opts.code || S.code) };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.etag) headers["If-None-Match"] = opts.etag;
  try {
    const r = await fetch(path, {
      method, headers, signal: ctl.signal, cache: "no-store", credentials: "omit", keepalive: !!opts.keepalive,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
    });
    const text = r.status === 204 || r.status === 304 ? "" : await r.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }   // Apache answers some errors in HTML
    return { status: r.status, data, etag: r.headers.get("ETag"), wait: r.status === 429 || r.status === 503 ? retryAfter(r) : 0 };
  } catch (e) {
    return { status: 0, data: null, etag: null, wait: 0 };
  } finally {
    clearTimeout(timer);
  }
}

/* ---- the outbox ---- */

export const loadOb = () => { const v = store.get(K.outbox); return Array.isArray(v) ? v : []; };
const saveOb = ob => store.set(K.outbox, ob);
export function mutateOb(fn) {
  const ob = fn(loadOb());
  saveOb(ob);
  emit("sync");
  return ob;
}
const io = {
  load: loadOb, save: saveOb, now: () => Date.now(),
  send: (method, path, body, code) => api(method, path, { body, code, keepalive: true }),
};

/* The reader's comments as the server will count them: its last count, plus new ones on their way. */
export function commentTotal() {
  if (!S.me || typeof S.me.total !== "number") return null;
  return S.me.total + pendingCreates(loadOb(), S.code);
}

/* Send the outbox one op at a time, in the background. One tab sends at a time. */
let flushing = false, wakeTimer = 0;
export function flush() {
  if (flushing || S.authBlocked) return;
  flushing = true;
  const run = async () => {
    for (;;) {
      const r = await flushOnce(io);
      if (!r) return "idle";
      handleResult(r);
      if (r.verdict === "net") { S.netFails++; return "net"; }
      if (r.verdict === "auth") return "auth";
      if (r.verdict !== "dropped") S.netFails = 0;
    }
  };
  const job = navigator.locks
    ? navigator.locks.request("rv-outbox", { ifAvailable: true }, lock => (lock ? run() : "busy"))
    : run();
  Promise.resolve(job)
    .catch(err => { console.error(err); return "error"; })
    .then(how => { flushing = false; schedule(how === "busy" || how === "error" ? 1000 : 0); });
}

export function schedule(minDelay) {
  clearTimeout(wakeTimer);
  emit("sync");
  if (S.authBlocked) return;
  const now = Date.now();
  let at = nextWake(loadOb(), now);
  if (at === Infinity) return;
  if (S.netFails) at = Math.max(at, now + backoff(S.netFails));
  wakeTimer = setTimeout(flush, Math.max(minDelay || 0, at - now));
}

const cmWrites = new Map();   // writes confirmed per chapter, so a comment list fetched meanwhile is not trusted

function handleResult(r) {
  const o = r.op;
  if (r.verdict === "auth") {
    if (o.code === S.code) authFailed();
    else mutateOb(ob => ob.filter(x => x.op !== o.op));   // a change from an old link can no longer go
    return;
  }
  if (!o.cid) return;
  if (r.verdict === "ok") {
    const key = cmKey(o.book, o.ch);
    const rec = store.get(key);
    if (rec && Array.isArray(rec.list)) {
      const list = rec.list.filter(x => x.client_id !== o.cid);
      if (o.type !== "delete" && r.data && r.data.id != null) {
        const i = rec.list.findIndex(x => x.client_id === o.cid);
        const c = Object.assign({ client_id: o.cid }, r.data);
        if (i >= 0) list.splice(i, 0, c); else list.push(c);
      }
      store.set(key, { list });
    }
    cmWrites.set(key, (cmWrites.get(key) || 0) + 1);
    if (S.me && typeof S.me.total === "number") {
      if (o.type === "create" && r.status === 201) S.me.total++;
      else if (o.type === "delete" && r.status === 200) S.me.total = Math.max(0, S.me.total - 1);
    }
    if (o.type !== "delete") {
      S.saved.set(o.cid, Date.now());
      setTimeout(() => emit("result", { verdict: "faded", op: o }), 4200);
    }
  }
  emit("result", r);
}

/* ---- the chapter list, chapters and comments ---- */

let firstMe = null;   // the first /api/me request, started by boot() alongside the words
export function startMe() {
  if (S.code) firstMe = api("GET", "api/me");
}

export async function refreshMe() {
  if (!S.code || S.authBlocked) return false;
  const pending = firstMe;
  firstMe = null;
  const r = await (pending || api("GET", "api/me"));
  if (r.status === 401) { authFailed(); return false; }
  if (r.status === 200 && r.data) {
    S.me = applyPending(normMe(r.data), loadOb(), S.code);
    S.meAt = Date.now();
    store.set(K.me, S.me);
    keepDraftsOf(S.me.name);
    emit("me");
    return true;
  }
  if (!S.me) emit("offline");
  return false;
}

/* A kept chapter's variant; a chapter kept by an older page says only whether it has English. */
const keptVariant = rec => (typeof rec.variant === "string" ? rec.variant : rec.english ? "en" : "");

/* Whether a chapter on the device is missing, old, or shaped by other features than the reader's. */
export function keptIsStale(c) {
  const rec = store.get(chKey(c.book, c.id));
  return !rec || !rec.data || rec.data.version !== c.version || keptVariant(rec) !== variantOf(S.me);
}

/* The chapter kept on the device, with its variant, or null. */
export function keptChapter(book, id) {
  const rec = store.get(chKey(book, id));
  if (!rec || !rec.data) return null;
  rec.data.variant = keptVariant(rec);
  return rec.data;
}

/* Returns {data, changed}, "gone" (withdrawn or not granted), or null (offline or a server fault). */
export async function fetchChapter(book, id) {
  const key = chKey(book, id);
  const rec = store.get(key);
  const variant = variantOf(S.me);
  const etag = rec && rec.data && keptVariant(rec) === variant ? rec.etag : null;
  const r = await api("GET", "api/chapter/" + enc(book) + "/" + enc(id), { etag });
  if (r.status === 304 && rec && rec.data) {
    rec.data.variant = variant;
    return { data: rec.data, changed: false };
  }
  if (r.status === 200 && r.data) {
    const data = normChapter(r.data);
    const changed = !rec || !rec.data || rec.data.version !== data.version || keptVariant(rec) !== variant;
    store.set(key, { etag: r.etag, variant, data });
    data.variant = variant;
    return { data, changed };
  }
  if (r.status === 401) { authFailed(); return null; }
  if (r.status === 403 || r.status === 404) {
    store.del(key);
    store.del(cmKey(book, id));
    return "gone";
  }
  return null;
}

/* Fetch the open chapter again and say what came back. */
export async function revalidateChapter(book, id) {
  const r = await fetchChapter(book, id);
  if (r === "gone") emit("chapter", { book, id, gone: true });
  else if (r) emit("chapter", { book, id, data: r.data });
  else emit("chapter", { book, id, missing: true });
}

export const keptComments = (book, id) => {
  const rec = store.get(cmKey(book, id));
  return rec && Array.isArray(rec.list) ? rec.list : null;
};

export async function loadComments(book, id) {
  const key = cmKey(book, id);
  for (let i = 0; i < 3; i++) {
    const before = cmWrites.get(key) || 0;
    const r = await api("GET", "api/comments?book=" + enc(book) + "&ch=" + enc(id));
    if (r.status === 401) { authFailed(); return false; }
    if (r.status !== 200 || !r.data) return false;
    if ((cmWrites.get(key) || 0) !== before) continue;   // a write landed meanwhile: ask again
    store.set(key, { list: normComments(r.data) });
    emit("comments", { book, id });
    return true;
  }
  return false;
}

/* After the chapter list arrives, fetch every chapter and comment list that is missing or old,
   one at a time, so each chapter opens at once and can be read offline. */
let prefetchTimer = 0;
export function schedulePrefetch() {
  clearTimeout(prefetchTimer);
  prefetchTimer = setTimeout(prefetch, 1500);
}
async function prefetch() {
  if (!S.me || S.authBlocked) return;
  const chapters = S.me.chapters.slice();
  for (const c of chapters) {
    if (keptIsStale(c)) {
      const r = await fetchChapter(c.book, c.id);
      if (r === null || !S.me) return;   // offline: stop here and try on the next visit
      if (r !== "gone") emit("chapter", { book: c.book, id: c.id, data: r.data, background: true });
    }
    if (!store.get(cmKey(c.book, c.id)) && !(await loadComments(c.book, c.id))) return;
    if (!S.me) return;
  }
  const keep = new Set(S.me.chapters.map(c => c.book + "/" + c.id));
  for (const k of store.keys()) {
    const m = /^rv\.(?:ch|cm):(.+)$/.exec(k);
    if (m && !keep.has(m[1])) store.del(k);
  }
}

const draftKeys = () => store.keys().filter(k => parseDraftKey(k));

/* The drafts on the device belong to the reader named in rv.draftOwner. When the chapter list of a reader
   with another name arrives, they are deleted, so no reader sees another reader's words; a new link of the
   same reader keeps them. */
function keepDraftsOf(name) {
  if (!name) return;
  const owner = store.get(K.draftOwner);
  if (owner && owner !== name) for (const k of draftKeys()) store.del(k);
  store.set(K.draftOwner, name);
}

/* Drop what the device keeps for one reader: the chapter list, chapters, comment lists, and what features
   keep for the reader under "rv.f:<feature>:" keys. The outbox stays: each op names the link that made
   it. The drafts stay with the name of their reader (keepDraftsOf), or go when that name is not known. */
export function forgetReader() {
  for (const k of store.keys()) if (/^rv\.(ch|cm|f):/.test(k)) store.del(k);
  const me = store.get(K.me);
  if (!store.get(K.draftOwner) && me && me.name) store.set(K.draftOwner, me.name);
  if (!store.get(K.draftOwner)) for (const k of draftKeys()) store.del(k);
  store.del(K.me);
}

export function authFailed() {
  S.authBlocked = true;
  forgetReader();
  S.me = null;
  emit("auth");
}

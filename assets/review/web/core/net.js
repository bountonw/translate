/* Proofreading site: talking to the server (web/core/net.js).

   The API calls, the outbox runner, and the chapter list, chapters and comment lists kept on the
   device. The page draws from the device first and checks the server in the background (chapters by
   ETag). This module draws nothing: it tells the drawing modules what changed through emit() in
   state.js.

   Every request carries this device's key in X-Review-Device (README.md, "One person per link"). A link
   works on the first devices that open it; on a further device every route answers 403 device_waiting
   until the translator approves it. The page then waits: it keeps everything on the device, sends nothing,
   and asks /api/me again until it answers.

   Each link's waiting comments, refused comments and drafts are kept apart on the device, and the page
   shows and sends only those of the link open now. When /api/me answers, the page notes the reader number
   of the link (rv.links); the waiting comments and drafts of another link of the same reader number then
   move to the link open now and go out under it. Those of another reader wait untouched until that
   reader's link opens again on this device. */

import { TIMEOUT_MS, LEASE_MS, PLACE_DELAY_MS, backoff, flushOnce, nextWake, applyPending, adoptOps, randomId } from "./outbox.js";
import { normMe, normChapter, upgradeChapter, normComments } from "./model.js";
import { variantOf } from "./ext.js";
import { K, chKey, cmKey, linkTag, draftMoves } from "./store.js";
import { S, store, emit } from "./state.js";

export { PLACE_DELAY_MS };
const enc = encodeURIComponent;

/* A controller that gives up a fetch after TIMEOUT_MS: {signal, done()}. Safari before iOS 12.2 has no
   AbortController; there a fetch runs without a timeout, as the network allows. */
function deadline() {
  if (typeof AbortController !== "function") return { signal: undefined, done() {} };
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  return { signal: ctl.signal, done() { clearTimeout(timer); } };
}

/* A file of the page itself, such as ui-strings.json, as JSON; null when it cannot be had. */
export async function getFile(path) {
  const limit = deadline();
  try {
    const r = await fetch(path, { cache: "no-cache", credentials: "omit", signal: limit.signal });
    if (!r.ok) return null;
    const d = await r.json();
    return d && typeof d === "object" ? d : null;
  } catch (e) {
    return null;
  } finally {
    limit.done();
  }
}

/* Retry-After in ms: whole seconds only, at most ten minutes, or at most a day for the daily limit of new
   comments, whose wait runs until the next midnight, Thailand time. */
function retryAfter(r, data) {
  const s = Number(r.headers.get("Retry-After"));
  const most = data && data.error === "daily_limit" ? 86400 : 600;
  return s > 0 ? Math.min(most, s) * 1000 : 0;
}

/* This device's key: made once, at random, and kept on the device under rv.device, which a new link does
   not clear. Once read or made, it stays in a variable for the visit, so storage that is full or blocked
   (store.js) never gives each request a new key, which the site would count as a new device. */
const DEVICE_RE = /^[A-Za-z0-9_-]{16,128}$/;
let thisDevice = "";
export function deviceKey() {
  if (thisDevice) return thisDevice;
  let k = store.get(K.device);
  if (typeof k !== "string" || !DEVICE_RE.test(k)) {
    k = randomId();
    store.set(K.device, k);
  }
  thisDevice = k;
  return k;
}

/* Whether an answer says that the link does not work on this device until the translator approves it. */
export const isDeviceWaiting = r => r.status === 403 && !!r.data && r.data.error === "device_waiting";

/* One API call. Returns {status, data, etag, wait}; status 0 means offline or timed out. */
export async function api(method, path, opts) {
  opts = opts || {};
  const limit = deadline();
  const headers = { Authorization: "Bearer " + (opts.code || S.code), "X-Review-Device": deviceKey() };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.etag) headers["If-None-Match"] = opts.etag;
  try {
    const r = await fetch(path, {
      method, headers, signal: limit.signal, cache: "no-store", credentials: "omit", keepalive: !!opts.keepalive,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
    });
    const text = r.status === 204 || r.status === 304 ? "" : await r.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }   // Apache answers some errors in HTML
    return { status: r.status, data, etag: r.headers.get("ETag"), wait: r.status === 429 || r.status === 503 ? retryAfter(r, data) : 0 };
  } catch (e) {
    return { status: 0, data: null, etag: null, wait: 0 };
  } finally {
    limit.done();
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
/* Only the ops of the link open now go out (outbox.js). */
const io = {
  load: loadOb, save: saveOb, now: () => Date.now(),
  send: (method, path, body, code) => api(method, path, { body, code, keepalive: true }),
  get code() { return S.code; },
};

/* Send the outbox one op at a time, in the background. One tab sends at a time, under the lock rv-outbox.
   Nothing goes while the link does not work, or while this device waits for the translator's approval.
   A page that holds the lock may be frozen with it: Firefox keeps a page left in the same tab in its
   back-forward cache, stopped in the middle of a request. So a page that has found the lock taken for longer
   than an op's lease (LEASE_MS) takes it over ({steal: true}); each op's own lease (outbox.js) and the site's
   check of client_id keep two pages from sending one comment twice. */
let flushing = false, wakeTimer = 0, busySince = 0;
export function flush() {
  if (flushing || S.authBlocked || S.deviceWaiting) return;
  flushing = true;
  const run = async () => {
    for (;;) {
      const r = await flushOnce(io);
      if (!r) return "idle";
      handleResult(r);
      if (r.verdict === "net") { S.netFails++; return "net"; }
      if (r.verdict === "auth" || r.verdict === "device") return r.verdict;
      if (r.verdict !== "dropped") S.netFails = 0;
    }
  };
  let ran = null;
  const go = () => (ran = run());
  const steal = busySince > 0 && Date.now() - busySince > LEASE_MS;
  const job = navigator.locks
    ? navigator.locks.request("rv-outbox", steal ? { steal: true } : { ifAvailable: true }, lock => (lock ? go() : "busy"))
    : go();
  Promise.resolve(job)
    // A page that takes the lock over ends this page's hold on it, not its run, which ends by itself.
    .catch(err => (ran ? ran.catch(() => "error") : (console.error(err), "error")))
    .then(how => {
      flushing = false;
      if (how === "busy") { if (!busySince) busySince = Date.now(); } else busySince = 0;
      schedule(how === "busy" || how === "error" ? 1000 : 0);
    });
}

export function schedule(minDelay) {
  clearTimeout(wakeTimer);
  emit("sync");
  if (S.authBlocked || S.deviceWaiting) return;
  const now = Date.now();
  let at = nextWake(loadOb(), now, S.code);
  if (at === Infinity) return;
  if (S.netFails) at = Math.max(at, now + backoff(S.netFails));
  wakeTimer = setTimeout(flush, Math.max(minDelay || 0, at - now));
}

const cmWrites = new Map();   // writes confirmed per chapter, so a comment list fetched meanwhile is not trusted
const STALE = ["no_chapter", "text_too_long", "quote_too_long"];   // refusals after which /api/me is asked again

function handleResult(r) {
  const o = r.op;
  // The op stays in the outbox in both cases: a new link of the reader, or the translator's approval of
  // this device, lets it go later.
  if (r.verdict === "auth") {
    if (o.code === S.code) authFailed();
    return;
  }
  if (r.verdict === "device") { deviceWaiting(r.data); return; }
  // A refusal that a newer chapter list explains: the chapter is closed now, or the site's limits changed. The
  // list is asked for at once, so the page shows "This chapter is closed now" and names the site's own limit.
  if (r.verdict === "fail" && r.data && STALE.indexOf(r.data.error) >= 0) refreshMe();
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
  S.meStatus = r.status;
  if (r.status === 401) { authFailed(); return false; }
  if (isDeviceWaiting(r)) { deviceWaiting(r.data); return false; }
  if (r.status === 200 && r.data) {
    const me = normMe(r.data);
    const before = S.me;
    const wasWaiting = S.deviceWaiting;
    S.deviceWaiting = false;
    const taken = takeOverLinks(me);
    dropStale(before, me);
    S.me = applyPending(me, loadOb(), S.code);
    S.meAt = Date.now();
    store.set(K.me, S.me);
    emit("me");
    // Ops that waited for the device, or that the link open now just took over, go at once.
    if (wasWaiting || taken) flush();
    return true;
  }
  if (!S.me && !S.deviceWaiting) emit("offline");
  return false;
}

/* The link does not work on this device until the translator approves it. Nothing is sent meanwhile, and
   nothing the device keeps is dropped. data is the site's answer, which names the device's number, so the
   reader can tell the translator which device to approve; a number already known stays. */
export function deviceWaiting(data) {
  S.deviceWaiting = true;
  if (data && typeof data.device === "number") S.deviceNumber = data.device;
  clearTimeout(wakeTimer);
  emit("device");
  emit("sync");
}

/* Note which reader the link open now belongs to, and move to it the waiting comments and drafts of the
   reader's other links on this device (README.md, "One person per link"). The match is by the reader's
   fixed number from /api/me, never by name, because two readers may share a name. Returns how many ops
   moved. */
function takeOverLinks(me) {
  if (me.id === null || !S.code) return 0;
  const links = store.get(K.links) || {};
  const tag = linkTag(S.code);
  if (links[tag] !== me.id) {
    links[tag] = me.id;
    store.set(K.links, links);
  }
  const sameReader = code => code !== S.code && links[linkTag(code)] === me.id;
  let moved = 0;
  if (loadOb().some(o => sameReader(o.code))) mutateOb(ob => { moved = adoptOps(ob, S.code, sameReader, Date.now()); return ob; });
  moveDrafts(tag, t => t !== tag && links[t] === me.id);
  return moved;
}

/* Move drafts under the link whose tag is `to` (store.js, draftMoves). */
function moveDrafts(to, sameReader) {
  for (const [from, dest] of draftMoves(store.keys(), to, sameReader)) {
    const body = store.get(from);
    if (body && store.set(dest, body)) store.del(from);
  }
}

/* A page before round 3b kept the drafts without the tag of their link, and deleted them when a reader of
   another name opened the page. They belong to the link the device held then: code, the link of rv.code
   before a new link replaces it. */
export function adoptOldDrafts(code) {
  if (!code) return;
  moveDrafts(linkTag(code), t => t === "");
  store.del(K.draftOwner);
}

/* What the device keeps that a new chapter list makes stale: each chapter that is no longer open to the
   reader, with its comment list and its record of changes, and the comment lists of a book whose review
   round changed, since a reader's page shows only the current round's comments. A chapter list kept by a
   page before round 3b names no rounds, so every comment list is fetched again once. Drafts and the outbox
   stay: an unsent comment of a closed chapter shows in the list of comments not saved, with its words. */
function dropStale(before, me) {
  const open = new Set(me.chapters.map(c => c.book + "/" + c.id));
  const roundsKnown = !!before && !!before.rounds && typeof before.rounds === "object";
  const name = r => (r && r.name) || "";
  const newRound = book => !roundsKnown || name(before.rounds[book]) !== name(me.rounds[book]);
  let openDropped = false;
  for (const k of store.keys()) {
    const m = /^rv\.(ch|cm|opened):([^/]+)\/(.+)$/.exec(k);
    if (!m) continue;
    const gone = !open.has(m[2] + "/" + m[3]);
    if (gone || (m[1] === "cm" && newRound(m[2]))) {
      store.del(k);
      if (m[1] === "cm" && S.view === "chapter" && S.book === m[2] && S.ch === m[3]) openDropped = !gone;
    }
  }
  if (openDropped) loadComments(S.book, S.ch);
}

/* A kept chapter's variant; a chapter kept by an older page says only whether it has English. */
const keptVariant = rec => (typeof rec.variant === "string" ? rec.variant : rec.english ? "en" : "");

/* Whether a chapter on the device is missing, old, or shaped by other features than the reader's. */
export function keptIsStale(c) {
  const rec = store.get(chKey(c.book, c.id));
  return !rec || !rec.data || rec.data.version !== c.version || keptVariant(rec) !== variantOf(S.me);
}

/* The chapter kept on the device, with its variant, or null. A chapter kept by a page before round 3b is
   brought to the shape of now (model.js, upgradeChapter). */
export function keptChapter(book, id) {
  const rec = store.get(chKey(book, id));
  if (!rec || !rec.data) return null;
  upgradeChapter(rec.data);
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
    upgradeChapter(rec.data);
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
  if (isDeviceWaiting(r)) { deviceWaiting(r.data); return null; }
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
    if (isDeviceWaiting(r)) { deviceWaiting(r.data); return false; }
    if (r.status !== 200 || !r.data) return false;
    if ((cmWrites.get(key) || 0) !== before) continue;   // a write landed meanwhile: ask again
    store.set(key, { list: normComments(r.data) });
    emit("comments", { book, id });
    return true;
  }
  return false;
}

/* The reader's comments of earlier review rounds, for "My earlier comments": {comments, rounds}, or
   {error: "offline"} or {error: "fault"}, or null when the link or the device stopped working (the page
   then shows that instead). */
export async function fetchEarlier() {
  const r = await api("GET", "api/comments?earlier=1");
  if (r.status === 401) { authFailed(); return null; }
  if (isDeviceWaiting(r)) { deviceWaiting(r.data); return null; }
  if (r.status === 200 && r.data) return { comments: normComments(r.data), rounds: Array.isArray(r.data.rounds) ? r.data.rounds : [] };
  return { error: r.status === 0 ? "offline" : "fault" };
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
}

/* Drop what the device keeps for one reader to read: the chapter list, chapters, comment lists, the changed
   paragraphs the reader has opened, and what features keep for the reader under "rv.f:<feature>:" keys.
   What the reader wrote stays: each op of the outbox names the link that made it, and each draft carries
   its link's tag in its key. The device key and the reader numbers of links (rv.links) stay too. */
export function forgetReader() {
  for (const k of store.keys()) if (/^rv\.(ch|cm|opened|f):/.test(k)) store.del(k);
  store.del(K.me);
}

export function authFailed() {
  S.authBlocked = true;
  forgetReader();
  S.me = null;
  emit("auth");
}

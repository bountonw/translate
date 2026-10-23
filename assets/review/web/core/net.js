/* Proofreading site: talking to the server (web/core/net.js).

   The API calls, the outbox runner, and the chapter list, chapters and comment lists kept on the
   device. The page draws from the device first and checks the server in the background (chapters by
   ETag). This module draws nothing: it tells the drawing modules what changed through emit() in
   state.js.

   Every request carries the header X-Review-Page: 1, which tells the site that its own page sent it
   (README.md, "One person per account"). A reader signed in (S.mode "session") is known by the session
   cookie, which the page never sees: those requests go with credentials "same-origin" and no code. In link
   mode (S.mode "link", README.md, "Link signs in") a request carries the link's code and this device's key in
   X-Review-Device, as before accounts, and goes with credentials "omit", so a session of another reader on
   this browser never answers for the link. A link works on the first devices that open it; on a further
   device every route answers 403 device_waiting until the translator approves it. The page then waits: it
   keeps everything on the device, sends nothing, and asks /api/me again until it answers.

   Each reader's waiting comments, refused comments and drafts are kept apart on the device by the reader's
   fixed number (who()), and the page shows and sends only those of the reader signed in now. When /api/me
   answers, or a link's claim names its reader, the page notes the number of the link (rv.links); the waiting
   comments and drafts written under that link then become the reader's, and go out once that reader is
   signed in on this browser. Those of another reader wait untouched until that reader signs in here again. */

import { TIMEOUT_MS, LEASE_MS, PLACE_DELAY_MS, backoff, flushOnce, nextWake, applyPending, renumber, randomId } from "./outbox.js";
import { normMe, normChapter, upgradeChapter, normComments } from "./model.js";
import { variantOf } from "./ext.js";
import { K, chKey, cmKey, linkTag, ownerTag, draftMoves } from "./store.js";
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

/* Whether a request of a reader route goes in link mode: with the link's code and the device key. */
const linkMode = () => S.mode === "link" && !!S.code;

/* One API call. Returns {status, data, etag, wait}; status 0 means offline or timed out. opts.page is true for
   the sign-in routes (/api/auth/, /api/dev/), which always go with the cookies and never with a link's code. */
export async function api(method, path, opts) {
  opts = opts || {};
  const limit = deadline();
  const link = !opts.page && linkMode();
  const headers = { "X-Review-Page": "1" };
  if (link) Object.assign(headers, { Authorization: "Bearer " + S.code, "X-Review-Device": deviceKey() });
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.etag) headers["If-None-Match"] = opts.etag;
  try {
    const r = await fetch(path, {
      method, headers, signal: limit.signal, cache: "no-store", credentials: link ? "omit" : "same-origin", keepalive: !!opts.keepalive,
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
/* The reader whose words the page shows and sends now: the reader's fixed number, or, in link mode before the
   device knows the link's number, "link:" and the link's code (outbox.js, ownerOf); null when nobody is signed
   in. */
export function who() {
  if (typeof S.reader === "number") return S.reader;
  return linkMode() ? "link:" + S.code : null;
}

/* Only the ops of the reader signed in now go out (outbox.js). */
const io = {
  load: loadOb, save: saveOb, now: () => Date.now(),
  send: (method, path, body) => api(method, path, { body, keepalive: true }),
  get who() { return who(); },
};

/* Send the outbox one op at a time, in the background. One tab sends at a time, under the lock rv-outbox.
   Nothing goes while nobody is signed in, while a reader route answers 401, or while this device waits for the
   translator's approval.
   A page that holds the lock may be frozen with it: Firefox keeps a page left in the same tab in its
   back-forward cache, stopped in the middle of a request. So a page that has found the lock taken for longer
   than an op's lease (LEASE_MS) takes it over ({steal: true}); each op's own lease (outbox.js) and the site's
   check of client_id keep two pages from sending one comment twice. */
let flushing = false, wakeTimer = 0, busySince = 0;
export function flush() {
  if (flushing || S.authBlocked || S.deviceWaiting || who() === null) return;
  flushing = true;
  const run = async () => {
    for (;;) {
      const r = await flushOnce(io);
      if (!r) return "idle";
      handleResult(r);
      if (r.verdict === "net") { S.netFails++; return "net"; }
      if (r.verdict === "auth" || r.verdict === "device" || r.verdict === "page") return r.verdict;
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
  if (S.authBlocked || S.deviceWaiting || who() === null) return;
  const now = Date.now();
  let at = nextWake(loadOb(), now, who());
  if (at === Infinity) return;
  if (S.netFails) at = Math.max(at, now + backoff(S.netFails));
  wakeTimer = setTimeout(flush, Math.max(minDelay || 0, at - now));
}

const cmWrites = new Map();   // writes confirmed per chapter, so a comment list fetched meanwhile is not trusted
const STALE = ["no_chapter", "text_too_long", "quote_too_long"];   // refusals after which /api/me is asked again

function handleResult(r) {
  const o = r.op;
  // The op stays in the outbox in these cases: the reader's sign-in, the translator's approval of this device,
  // or the page loaded again lets it go later.
  if (r.verdict === "auth") { authFailed(r.data && r.data.error); return; }
  if (r.verdict === "device") { deviceWaiting(r.data); return; }
  if (r.verdict === "page") { emit("fault"); return; }
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
  if (S.mode) firstMe = api("GET", "api/me");
}

export async function refreshMe() {
  if (!S.mode || S.authBlocked) return false;
  const pending = firstMe;
  firstMe = null;
  const r = await (pending || api("GET", "api/me"));
  if (!S.mode || S.authBlocked) return false;   // signed out meanwhile
  S.meStatus = r.status;
  if (r.status === 401) { authFailed(r.data && r.data.error); return false; }
  if (isDeviceWaiting(r)) { deviceWaiting(r.data); return false; }
  if (r.status === 200 && r.data) {
    const me = normMe(r.data);
    S.deviceWaiting = false;
    S.justSignedIn = false;
    if (me.id !== null) adoptReader(me.id);
    const before = S.me;
    dropStale(before, me);
    S.me = applyPending(me, loadOb(), who());
    S.meAt = Date.now();
    store.set(K.me, S.me);
    emit("me");
    // Every answer of 200 sends what waits: ops that waited for the device, for the reader's number or for a
    // sign-in (a reader in link mode who signs in, on a device that already knew the number, 66-adversarial.md
    // ADV4-01), and ops written under the reader's earlier links. flush() returns at once when nothing of the
    // reader's is due, and sends only the ops of the reader signed in now.
    flush();
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

/* The reader signed in now is reader `id`, as /api/me or a sign-in says. In link mode the page notes the link's
   number (rv.links). When the device kept the chapter list of another reader, what it keeps for reading goes
   (forgetReader); what any reader wrote stays. The ops and drafts written under the reader's links become the
   reader's (noteLink). Returns how many ops became the reader's, or 1 when the reader changed, so that the
   caller sends them at once. */
export function adoptReader(id) {
  const kept = store.get(K.reader);
  const keptMe = store.get(K.me);
  let changed = 0;
  if ((typeof kept === "number" && kept !== id) || (!!keptMe && Number.isInteger(keptMe.id) && keptMe.id !== id)) {
    forgetReader();
    S.me = null;
  }
  if (kept !== id) {
    store.set(K.reader, id);
    changed = 1;
  }
  S.reader = id;
  return Math.max(changed, linkMode() ? noteLink(S.code, id) : ownWords(id));
}

/* Note that the link `code` belongs to reader `id` (rv.links: the link's tag, never its code), and give the
   reader every op and draft written under the reader's links on this device. The match is by the reader's
   fixed number, never by name, because two readers may share a name. Returns how many ops changed. */
export function noteLink(code, id) {
  if (!code || typeof id !== "number") return 0;
  const links = store.get(K.links) || {};
  const tag = linkTag(code);
  if (links[tag] !== id) {
    links[tag] = id;
    store.set(K.links, links);
  }
  return ownWords(id);
}

/* Give reader `id` the ops and drafts written under the reader's links (rv.links), and those written before
   the device knew the number of the link open now. Returns how many ops changed. */
function ownWords(id) {
  const links = store.get(K.links) || {};
  const numberOf = code => links[linkTag(code)];
  const ob = loadOb();
  const moved = renumber(ob, numberOf, Date.now());
  if (moved) {
    saveOb(ob);
    emit("sync");
  }
  const to = ownerTag(id);
  moveDrafts(to, t => t !== to && /^[0-9a-f]{8}$/.test(t) && links[t] === id);
  return moved;
}

/* Move drafts under the tag `to` (store.js, draftMoves). */
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
  if (r.status === 401) { authFailed(r.data && r.data.error); return null; }
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
    if (r.status === 401) { authFailed(r.data && r.data.error); return false; }
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
  if (r.status === 401) { authFailed(r.data && r.data.error); return null; }
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
   What the reader wrote stays: each op of the outbox names its reader, and each draft carries its reader's
   tag in its key. The device key and the reader numbers of links (rv.links) stay too. */
export function forgetReader() {
  for (const k of store.keys()) if (/^rv\.(ch|cm|opened|f):/.test(k)) store.del(k);
  store.del(K.me);
}

/* A reader route answered 401 with the error `code`: nothing more goes out, the page forgets what it keeps for
   reading, and the screen that the code calls for shows (core/signin.js). The outbox and the drafts stay. */
export function authFailed(code) {
  S.authBlocked = true;
  clearTimeout(wakeTimer);
  forgetReader();
  S.me = null;
  emit("auth", typeof code === "string" ? code : "");
}

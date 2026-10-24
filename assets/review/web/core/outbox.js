/* Proofreading site: the outbox (web/core/outbox.js).

   Every write the reader makes (a comment, a change, a delete, a place, a finished mark, the version of a
   chapter the reader opened) becomes an op
   in an array that net.js keeps in localStorage and sends in the background, retried with backoff, so
   reading and typing never wait for the network. Plain functions with no DOM: tests/core_test.js
   runs them with node.

   op = {op, type: create|update|delete|place|finished|opened, reader, cid?, id?, key?, book, ch, a?, body,
         t, rev, tries, sent, next, sending, failed, why}
   Ops of one comment (same cid) or one setting (same key and reader) go out in order; others never wait.
   `failed` holds {status, error, message, type} when the server refused the op for good; `why` holds the
   error code of the last answer that asked the page to try again later, such as slow_down. A delete keeps
   the comment's words in its body, so a delete the server refuses can still show them.

   `reader` is the fixed number of the reader who wrote the op (README.md, "Link signs in"): the page sends
   only the ops of the reader signed in now on this browser, with the session cookie or, in link mode, with the
   link's code. The ops of another reader wait, untouched, until that reader signs in on this browser again.
   An op made by a page of round 3b names its link in `code` instead, and so does an op written in link mode
   before the device knew the link's reader number; its owner is then "link:" and the code (ownerOf), until
   renumber() gives it the number the device learnt for that link. Nothing in the outbox is ever deleted
   unsent unless the reader asks. */

export const TIMEOUT_MS = 8000;    // a fetch is given up after this long and tried again later
export const LEASE_MS = 20000;     // an op marked "sending" longer ago than this was lost with its tab
export const PLACE_DELAY_MS = 5000;   // places reported within this time go out as one write
/* What a comment says, and `at`, where its quoted words start in the paragraph's reading text (core/quotes.js),
   a number or null. */
const FIELDS = ["kind", "quote", "text", "at"];
const atOf = v => (typeof v === "number" ? v : null);
const sameField = (f, x, y) => (f === "at" ? atOf(x) === atOf(y) : (x || "") === (y || ""));

export function randomId() {
  const b = new Uint8Array(16);
  crypto.getRandomValues(b);
  return Array.from(b, x => x.toString(16).padStart(2, "0")).join("");
}

/* The wait before retry number `tries`: 2 s, doubling up to 60 s, give or take 20%. */
export function backoff(tries, rand) {
  const base = Math.min(60000, 2000 * 2 ** Math.max(0, tries - 1));
  return Math.round(base * (0.8 + 0.4 * (rand === undefined ? Math.random() : rand)));
}

const isSending = (o, now) => !!o.sending && now - o.sending < LEASE_MS;

/* Whose an op is: the reader's number, or "link:" and the code of the link it was made under while its reader
   number was not known (a page of round 3b kept that code in `code`). */
export function ownerOf(o) {
  if (typeof o.reader === "number" || typeof o.reader === "string") return o.reader;
  return typeof o.code === "string" && o.code ? "link:" + o.code : null;
}
const chainOf = o => (o.cid ? "c:" + o.cid : "k:" + ownerOf(o) + ":" + o.key);
/* Whether op o is of the reader `who` (a number, or "link:" and a code); with no reader given, every op is. */
const mine = (o, who) => who === undefined || ownerOf(o) === who;

function newOp(type, who, now, extra) {
  return Object.assign({ op: randomId(), type, reader: who, t: now, rev: 0, tries: 0, sent: 0, next: 0, sending: 0, failed: null, why: "" }, extra);
}

/* A refused op that the reader changes is tried again from the start. */
function revive(o) {
  if (o.failed) { o.failed = null; o.tries = 0; o.next = 0; }
}

export function queueCreate(ob, c, who, now) {
  const body = { client_id: c.client_id, book: c.book, ch: c.ch, a: c.a, kind: c.kind, quote: c.quote || "", text: c.text,
    at: c.quote ? atOf(c.at) : null };
  ob.push(newOp("create", who, now, { cid: c.client_id, book: c.book, ch: c.ch, a: c.a, body }));
  return ob;
}

/* An edit joins a create or update still in the outbox; otherwise it becomes a new update. */
export function queueEdit(ob, c, fields, who, now) {
  const mine = ob.filter(o => o.cid === c.client_id && o.type !== "delete");
  const target = mine.find(o => o.type === "create") || mine.find(o => o.type === "update");
  if (target) {
    Object.assign(target.body, fields);
    target.rev++;
    revive(target);
    return ob;
  }
  ob.push(newOp("update", who, now, { cid: c.client_id, id: c.id, book: c.book, ch: c.ch, a: c.a, body: Object.assign({}, fields) }));
  return ob;
}

/* A comment the server cannot have seen is simply dropped; otherwise a delete goes out, with the comment's
   words, which the page shows if the server refuses the delete. */
export function queueDelete(ob, c, who, now) {
  const cid = c.client_id;
  const create = ob.find(o => o.cid === cid && o.type === "create");
  const onServer = c.id != null || (!!create && !create.failed && (isSending(create, now) || create.sent > 0));
  ob = ob.filter(o => o.cid !== cid || isSending(o, now) || (o === create && onServer));
  const body = { kind: c.kind, quote: c.quote || "", text: c.text || "" };
  if (onServer) ob.push(newOp("delete", who, now, { cid, id: c.id, book: c.book, ch: c.ch, a: c.a, body }));
  return ob;
}

/* Place, finished and opened: the newest value replaces an older one of the same chapter that is still
   waiting. */
export function queueSet(ob, type, body, who, now, delay) {
  const key = type + ":" + body.book + "/" + body.ch;
  const old = ob.find(o => o.key === key && ownerOf(o) === who);
  if (old) {
    old.body = Object.assign({}, body);
    old.rev++;
    revive(old);
    return ob;
  }
  ob.push(newOp(type, who, now, { key, book: body.book, ch: body.ch, body: Object.assign({}, body), next: now + (delay || 0) }));
  return ob;
}

/* Clear the refusal of every op of one comment, so they go out again. */
export function queueRetry(ob, cid) {
  for (const o of ob) if (o.cid === cid) revive(o);
  return ob;
}

/* The first op of the reader `who` that may go now: the head of its chain, not failed, not sending, not
   waiting. */
export function pickNext(ob, now, who) {
  const seen = new Set();
  for (const o of ob) {
    if (!mine(o, who)) continue;
    const chain = chainOf(o);
    if (seen.has(chain)) continue;
    seen.add(chain);
    if (!o.failed && !isSending(o, now) && o.next <= now) return o;
  }
  return null;
}

/* When the next op of the reader `who` falls due: a time in ms, or Infinity when nothing can go. */
export function nextWake(ob, now, who) {
  const seen = new Set();
  let at = Infinity;
  for (const o of ob) {
    if (!mine(o, who)) continue;
    const chain = chainOf(o);
    if (seen.has(chain)) continue;
    seen.add(chain);
    if (!o.failed) at = Math.min(at, isSending(o, now) ? o.sending + LEASE_MS : o.next);
  }
  return at;
}

/* The server's answer to an op, as what the page does next. error is the answer's error code, if any.
   "auth": the browser is not signed in as this reader now (every 401: no_code, signed_out, stopped, bad_code,
   link_used, sign_in_required); "device": the link does not work on this device until the translator
   approves it (403 device_waiting). In both the op stays as it is, and nothing more goes out until the reader
   signs in or the device is let in. "page": the site took the request for one another site made (403
   bad_page), a fault of the page; the op waits, as after a "retry", and is never refused for it. */
export function classify(type, status, error) {
  if (status >= 200 && status < 300) return "ok";
  // Already gone; any other refusal of a delete, as no_chapter for a closed chapter, leaves the comment.
  if (status === 404 && type === "delete" && error === "no_comment") return "ok";
  if (status === 0) return "net";                          // offline or timed out
  if (status === 401) return "auth";
  if (status === 403 && error === "device_waiting") return "device";
  if (status === 403 && error === "bad_page") return "page";
  if (status === 408 || status === 425 || status === 429 || status >= 500) return "retry";
  return "fail";                                           // the server refused this op
}

export function requestFor(o) {
  const path = o.id == null ? null : "api/comments/" + encodeURIComponent(o.id);
  switch (o.type) {
    case "create": return ["POST", "api/comments", o.body];
    case "update": return path && ["PATCH", path, o.body];
    case "delete": return path && ["DELETE", path, undefined];   // the body holds only the words, kept for the page
    case "place": return ["PUT", "api/place", o.body];
    case "finished": return ["PUT", "api/finished", o.body];
    case "opened": return ["PUT", "api/opened", o.body];
    default: return null;
  }
}

/* Apply the server's answer to the op that was sent. `ob` is the outbox as it is now; it may have
   changed while the request was out. `wait` is the server's Retry-After in ms, or 0. */
export function settle(ob, opid, sentRev, verdict, data, status, now, wait) {
  const o = ob.find(x => x.op === opid);
  if (!o) return ob;
  o.sending = 0;
  if (verdict === "ok") {
    if (o.type === "create" && data && data.id != null) {
      for (const x of ob) if (x.cid === o.cid) x.id = data.id;
      // The server keeps the first copy of a client_id, so an edit made meanwhile goes out as an update.
      if (FIELDS.some(f => !sameField(f, data[f], o.body[f]))) {
        o.type = "update";
        o.body = { kind: o.body.kind, quote: o.body.quote, text: o.body.text, at: atOf(o.body.at) };
        o.tries = 0;
        o.next = 0;
        o.why = "";
        return ob;
      }
      return ob.filter(x => x !== o);
    }
    if (o.rev !== sentRev) { o.tries = 0; o.next = 0; o.why = ""; return ob; }   // changed while out: send again
    return ob.filter(x => x !== o);
  }
  if (verdict === "retry" || verdict === "page") {
    o.tries++;
    o.next = now + Math.max(backoff(o.tries), wait || 0);
    o.why = verdict === "page" ? "" : (data && typeof data.error === "string" && data.error) || (status === 429 ? "slow_down" : "");
    return ob;
  }
  if (verdict === "fail") {
    if (o.type === "create" || o.type === "update" || o.type === "delete") {
      // A refused delete stays too: the reader learns that the comment was not deleted and the translator
      // still receives it.
      o.failed = { status, error: (data && typeof data.error === "string" && data.error) || "", message: (data && data.message) || "" };
      if (o.type === "delete") o.failed.type = "delete";
      o.why = "";
      return ob;
    }
    return ob.filter(x => x !== o);   // a refused place, finished or opened is dropped
  }
  return ob;   // "net", "auth" and "device": the op stays as it is, and the caller decides
}

/* Send one op. io = {load(), save(ob), send(method, path, body) -> {status, data, wait}, now(), who};
   io.who, when given, is the reader signed in now, and only that reader's ops go out. Returns {verdict, op,
   data, status}, or null when nothing is due. */
export async function flushOnce(io) {
  const ob = io.load();
  const o = pickNext(ob, io.now(), io.who);
  if (!o) return null;
  const req = requestFor(o);
  if (!req) {
    io.save(ob.filter(x => x !== o));
    return { verdict: "dropped", op: o, data: null, status: 0 };
  }
  o.sending = io.now();
  o.sent = (o.sent || 0) + 1;
  const opid = o.op, rev = o.rev;
  io.save(ob);
  const r = await io.send(req[0], req[1], req[2]);
  const verdict = classify(o.type, r.status, r.data && typeof r.data === "object" ? r.data.error : "");
  const data = r.data && typeof r.data === "object" && r.data.comment ? r.data.comment : r.data;
  io.save(settle(io.load(), opid, rev, verdict, data, r.status, io.now(), r.wait || 0));
  return { verdict, op: o, data, status: r.status };
}

/* The reader's comments on one chapter as they should look now: the server's list with the
   outbox laid over it. Each comment gets a state: saved, saving or failed. A comment that waits
   because the server asked the page to try later carries the reason in `why`. */
export function overlay(list, ob, book, ch, who) {
  const map = new Map();
  // Every comment carries its chapter, so an edit or delete made from this list finds its way back.
  for (const c of list || []) map.set(c.client_id, Object.assign({}, c, { book, ch, state: "saved", why: "" }));
  for (const o of ob) {
    if (!o.cid || o.book !== book || o.ch !== ch || ownerOf(o) !== who) continue;
    const cur = map.get(o.cid);
    const mark = { state: o.failed ? "failed" : "saving", failure: o.failed || null, why: o.failed ? "" : o.why || "" };
    // A comment held back by the daily limit carries when it goes again: the next midnight in Thailand.
    mark.until = mark.why === "daily_limit" ? o.next || 0 : 0;
    if (o.type === "create") map.set(o.cid, Object.assign({ processed: false }, cur, o.body, { client_id: o.cid }, mark));
    else if (o.type === "update" && cur) map.set(o.cid, Object.assign({}, cur, o.body, mark));
    else if (o.type === "delete" && o.failed && cur) map.set(o.cid, Object.assign({}, cur, mark));   // not deleted
    else if (o.type === "delete") map.delete(o.cid);
  }
  return [...map.values()];
}

/* Lay waiting place, finished and opened writes over a chapter list from the server. A waiting opened
   version of the chapter's current version leaves nothing to show as changed. */
export function applyPending(me, ob, who) {
  for (const o of ob) {
    if (ownerOf(o) !== who || (o.type !== "place" && o.type !== "finished" && o.type !== "opened")) continue;
    const c = me.chapters.find(x => x.book === o.book && x.id === o.ch);
    if (!c) continue;
    if (o.type === "place") c.place = o.body.a;
    else if (o.type === "finished") c.finished = !!o.body.finished;
    else if (o.body.version === c.version) { c.opened = c.version; c.changed = null; }
  }
  return me;
}

/* Give each op whose owner is a link (ownerOf: "link:" and a code) the number of that link's reader, once the
   device knows it: numberOf(code) returns the number, or anything else when it is not known. An op being sent
   by another tab is left as it is. The ops of a reader's earlier links thus go out once the reader signs in,
   matched by the reader's fixed number, never by name. Returns how many ops were given a number. */
export function renumber(ob, numberOf, now) {
  let n = 0;
  for (const o of ob) {
    const who = ownerOf(o);
    if (typeof who !== "string" || who.indexOf("link:") !== 0 || isSending(o, now)) continue;
    const id = numberOf(who.slice(5));
    if (typeof id !== "number") continue;
    o.reader = id;
    delete o.code;
    n++;
  }
  return n;
}

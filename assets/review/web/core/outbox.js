/* Proofreading site: the outbox (web/core/outbox.js).

   Every write the reader makes (a comment, a change, a delete, a place, a finished mark) becomes an op
   in an array that net.js keeps in localStorage and sends in the background, retried with backoff, so
   reading and typing never wait for the network. Plain functions with no DOM: tests/core_test.js
   runs them with node.

   op = {op, type: create|update|delete|place|finished, code, cid?, id?, key?, book, ch, a?, body,
         t, rev, tries, sent, next, sending, failed, why}
   Ops of one comment (same cid) or one setting (same key) go out in order; others never wait.
   `failed` holds {status, error, message} when the server refused the op for good; `why` holds the
   error code of the last answer that asked the page to try again later, such as slow_down. */

export const TIMEOUT_MS = 8000;    // a fetch is given up after this long and tried again later
export const LEASE_MS = 20000;     // an op marked "sending" longer ago than this was lost with its tab
export const PLACE_DELAY_MS = 5000;   // places reported within this time go out as one write
const FIELDS = ["kind", "quote", "text"];

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
const chainOf = o => (o.cid ? "c:" + o.cid : "k:" + o.key);

function newOp(type, code, now, extra) {
  return Object.assign({ op: randomId(), type, code, t: now, rev: 0, tries: 0, sent: 0, next: 0, sending: 0, failed: null, why: "" }, extra);
}

/* A refused op that the reader changes is tried again from the start. */
function revive(o) {
  if (o.failed) { o.failed = null; o.tries = 0; o.next = 0; }
}

export function queueCreate(ob, c, code, now) {
  const body = { client_id: c.client_id, book: c.book, ch: c.ch, a: c.a, kind: c.kind, quote: c.quote || "", text: c.text };
  ob.push(newOp("create", code, now, { cid: c.client_id, book: c.book, ch: c.ch, a: c.a, body }));
  return ob;
}

/* An edit joins a create or update still in the outbox; otherwise it becomes a new update. */
export function queueEdit(ob, c, fields, code, now) {
  const mine = ob.filter(o => o.cid === c.client_id && o.type !== "delete");
  const target = mine.find(o => o.type === "create") || mine.find(o => o.type === "update");
  if (target) {
    Object.assign(target.body, fields);
    target.rev++;
    revive(target);
    return ob;
  }
  ob.push(newOp("update", code, now, { cid: c.client_id, id: c.id, book: c.book, ch: c.ch, a: c.a, body: Object.assign({}, fields) }));
  return ob;
}

/* A comment the server cannot have seen is simply dropped; otherwise a delete goes out. */
export function queueDelete(ob, c, code, now) {
  const cid = c.client_id;
  const create = ob.find(o => o.cid === cid && o.type === "create");
  const onServer = c.id != null || (!!create && !create.failed && (isSending(create, now) || create.sent > 0));
  ob = ob.filter(o => o.cid !== cid || isSending(o, now) || (o === create && onServer));
  if (onServer) ob.push(newOp("delete", code, now, { cid, id: c.id, book: c.book, ch: c.ch, a: c.a }));
  return ob;
}

/* Place and finished: the newest value replaces an older one that is still waiting. */
export function queueSet(ob, type, body, code, now, delay) {
  const key = type + ":" + body.book + "/" + body.ch;
  const old = ob.find(o => o.key === key && o.code === code);
  if (old) {
    old.body = Object.assign({}, body);
    old.rev++;
    revive(old);
    return ob;
  }
  ob.push(newOp(type, code, now, { key, book: body.book, ch: body.ch, body: Object.assign({}, body), next: now + (delay || 0) }));
  return ob;
}

/* Clear the refusal of every op of one comment, so they go out again. */
export function queueRetry(ob, cid) {
  for (const o of ob) if (o.cid === cid) revive(o);
  return ob;
}

/* The first op that may go now: the head of its chain, not failed, not sending, not waiting. */
export function pickNext(ob, now) {
  const seen = new Set();
  for (const o of ob) {
    const chain = chainOf(o);
    if (seen.has(chain)) continue;
    seen.add(chain);
    if (!o.failed && !isSending(o, now) && o.next <= now) return o;
  }
  return null;
}

/* When the next op falls due: a time in ms, or Infinity when nothing can go. */
export function nextWake(ob, now) {
  const seen = new Set();
  let at = Infinity;
  for (const o of ob) {
    const chain = chainOf(o);
    if (seen.has(chain)) continue;
    seen.add(chain);
    if (!o.failed) at = Math.min(at, isSending(o, now) ? o.sending + LEASE_MS : o.next);
  }
  return at;
}

export function classify(type, status) {
  if (status >= 200 && status < 300) return "ok";
  if (status === 404 && type === "delete") return "ok";     // already gone
  if (status === 0) return "net";                          // offline or timed out
  if (status === 401) return "auth";
  if (status === 408 || status === 425 || status === 429 || status >= 500) return "retry";
  return "fail";                                           // the server refused this op
}

export function requestFor(o) {
  const path = o.id == null ? null : "api/comments/" + encodeURIComponent(o.id);
  switch (o.type) {
    case "create": return ["POST", "api/comments", o.body];
    case "update": return path && ["PATCH", path, o.body];
    case "delete": return path && ["DELETE", path, undefined];
    case "place": return ["PUT", "api/place", o.body];
    case "finished": return ["PUT", "api/finished", o.body];
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
      if (FIELDS.some(f => (data[f] || "") !== (o.body[f] || ""))) {
        o.type = "update";
        o.body = { kind: o.body.kind, quote: o.body.quote, text: o.body.text };
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
  if (verdict === "retry") {
    o.tries++;
    o.next = now + Math.max(backoff(o.tries), wait || 0);
    o.why = (data && typeof data.error === "string" && data.error) || (status === 429 ? "slow_down" : "");
    return ob;
  }
  if (verdict === "fail") {
    if (o.type === "create" || o.type === "update") {
      o.failed = { status, error: (data && typeof data.error === "string" && data.error) || "", message: (data && data.message) || "" };
      o.why = "";
      return ob;
    }
    return ob.filter(x => x !== o);   // a refused delete, place or finished is dropped
  }
  return ob;   // "net" and "auth": the caller decides
}

/* Send one op. io = {load(), save(ob), send(method, path, body, code) -> {status, data, wait}, now()}.
   Returns {verdict, op, data, status}, or null when nothing is due. */
export async function flushOnce(io) {
  const ob = io.load();
  const o = pickNext(ob, io.now());
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
  const r = await io.send(req[0], req[1], req[2], o.code);
  const verdict = classify(o.type, r.status);
  const data = r.data && typeof r.data === "object" && r.data.comment ? r.data.comment : r.data;
  io.save(settle(io.load(), opid, rev, verdict, data, r.status, io.now(), r.wait || 0));
  return { verdict, op: o, data, status: r.status };
}

/* The reader's comments on one chapter as they should look now: the server's list with the
   outbox laid over it. Each comment gets a state: saved, saving or failed. A comment that waits
   because the server asked the page to try later carries the reason in `why`. */
export function overlay(list, ob, book, ch, code) {
  const map = new Map();
  // Every comment carries its chapter, so an edit or delete made from this list finds its way back.
  for (const c of list || []) map.set(c.client_id, Object.assign({}, c, { book, ch, state: "saved", why: "" }));
  for (const o of ob) {
    if (!o.cid || o.book !== book || o.ch !== ch || o.code !== code) continue;
    const cur = map.get(o.cid);
    const mark = { state: o.failed ? "failed" : "saving", failure: o.failed || null, why: o.failed ? "" : o.why || "" };
    if (o.type === "create") map.set(o.cid, Object.assign({ processed: false }, cur, o.body, { client_id: o.cid }, mark));
    else if (o.type === "update" && cur) map.set(o.cid, Object.assign({}, cur, o.body, mark));
    else if (o.type === "delete") map.delete(o.cid);
  }
  return [...map.values()];
}

/* Lay waiting place and finished writes over a chapter list from the server. */
export function applyPending(me, ob, code) {
  for (const o of ob) {
    if (o.code !== code || (o.type !== "place" && o.type !== "finished")) continue;
    const c = me.chapters.find(x => x.book === o.book && x.id === o.ch);
    if (!c) continue;
    if (o.type === "place") c.place = o.body.a;
    else c.finished = !!o.body.finished;
  }
  return me;
}

/* New comments still in the outbox and not refused: they will count against the reader's limit. */
export function pendingCreates(ob, code) {
  return ob.filter(o => o.code === code && o.type === "create" && !o.failed).length;
}

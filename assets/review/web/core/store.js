/* Proofreading site: what the page keeps on the device (web/core/store.js).

   JSON in localStorage behind try/catch. Blocked storage falls back to memory for this visit, and the store
   says so (`blocked`), since the page then shows the screen for a browser that keeps no site data. A write
   that meets the quota drops the cached chapters and comment lists and tries once more. Plain functions:
   tests/core_test.js can run makeStore with a stand-in for localStorage. */

export const K = {
  code: "rv.code", lang: "rv.lang", strings: "rv.strings", langs: "rv.langs", me: "rv.me", outbox: "rv.outbox",
  draftOwner: "rv.draftOwner",   // a page before round 3b: the name of the reader whose drafts the device kept
  spaces: "rv.spaces",           // true when the book text shows a dot on every space
  device: "rv.device",           // this device's random key, sent in X-Review-Device; a new link keeps it
  links: "rv.links",             // {tag of a link: the reader number /api/me or the link's claim gave for it}
  reader: "rv.reader",           // the number of the reader whose chapter list the device keeps: the reader signed in last
  flow: "rv.flow",               // the sign-in screen the reader is on, {kind, code, at}, for the way back from LINE
  homeHint: "rv.homeHint",       // true once the reader hid the hint on adding the site to the Home Screen
};
export const chKey = (b, c) => "rv.ch:" + b + "/" + c;
export const cmKey = (b, c) => "rv.cm:" + b + "/" + c;
/* What changed in a chapter since the reader last opened it, and which changed paragraphs the reader has
   opened since (core/changes.js). */
export const openedKey = (b, c) => "rv.opened:" + b + "/" + c;

/* A short tag of a link's code: eight hexadecimal digits (FNV-1a), so that what the device keeps for each
   link, such as the drafts, is kept apart without writing the code itself into the name of a key. */
export function linkTag(code) {
  let x = 0x811c9dc5;
  const s = String(code || "");
  for (let i = 0; i < s.length; i++) {
    x ^= s.charCodeAt(i);
    x = Math.imul(x, 0x01000193) >>> 0;
  }
  return ("0000000" + x.toString(16)).slice(-8);
}

/* The tag of the reader `who` in the name of a draft's key, which is the letter R and the reader's fixed number,
   as R7; or, for a link whose reader number the device does not know yet ("link:" and its code, net.js, who),
   the link's tag. */
export function ownerTag(who) {
  if (typeof who === "number") return "R" + who;
  return typeof who === "string" && who.indexOf("link:") === 0 ? linkTag(who.slice(5)) : "";
}

/* One unsent comment per paragraph and per reader: rv.draft:<tag>:BOOK/CH/A, where the tag is the reader's
   (ownerTag). A page of round 3b used the tag of the link instead, and a page before round 3b no tag. */
export const draftKey = (tag, b, c, a) => "rv.draft:" + tag + ":" + b + "/" + c + "/" + a;

/* The tag ("" for a key without one), book, chapter and paragraph of a draft's key, or null for any other key. */
export function parseDraftKey(k) {
  const m = /^rv\.draft:(?:([0-9a-f]{8}|R\d+):)?([^/:]+)\/([^/]+)\/([^/]+)$/.exec(String(k));
  return m ? { tag: m[1] || "", book: m[2], ch: m[3], a: m[4] } : null;
}

/* The drafts to move under the tag `to`: each draft kept under another tag for which sameReader(tag) is true. A draft whose paragraph already has one under `to` stays where it is, so no words
   are written over. Returns [[from key, to key], ...]. */
export function draftMoves(keys, to, sameReader) {
  const list = keys.map(k => [k, parseDraftKey(k)]).filter(x => x[1]);
  const where = d => d.book + "/" + d.ch + "/" + d.a;
  const have = new Set(list.filter(x => x[1].tag === to).map(x => where(x[1])));
  const out = [];
  for (const [k, d] of list) {
    if (d.tag === to || !sameReader(d.tag) || have.has(where(d))) continue;
    have.add(where(d));
    out.push([k, draftKey(to, d.book, d.ch, d.a)]);
  }
  return out;
}

export function makeStore(ls) {
  let mem = null;
  try { ls.setItem("rv.probe", "1"); ls.removeItem("rv.probe"); } catch (e) { mem = new Map(); }
  const blocked = !!mem;
  const raw = mem ? {
    get: k => (mem.has(k) ? mem.get(k) : null),
    set: (k, v) => { mem.set(k, v); },
    del: k => { mem.delete(k); },
    keys: () => [...mem.keys()],
  } : {
    get: k => ls.getItem(k),
    set: (k, v) => ls.setItem(k, v),
    del: k => ls.removeItem(k),
    keys: () => Array.from({ length: ls.length }, (_, i) => ls.key(i)),
  };
  const keys = () => { try { return raw.keys(); } catch (e) { return []; } };
  const del = k => { try { raw.del(k); } catch (e) { /* nothing to do */ } };
  return {
    blocked,
    keys,
    del,
    get(k) {
      try { const v = raw.get(k); return v == null ? null : JSON.parse(v); } catch (e) { return null; }
    },
    set(k, v) {
      const s = JSON.stringify(v);
      try { raw.set(k, s); return true; } catch (e) { /* full: make room below */ }
      for (const x of keys()) if (x !== k && /^rv\.(ch|cm):/.test(x)) del(x);
      try { raw.set(k, s); return true; } catch (e) { return false; }
    },
  };
}

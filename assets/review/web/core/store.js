/* Proofreading site: what the page keeps on the device (web/core/store.js).

   JSON in localStorage behind try/catch. Blocked storage falls back to memory for this visit. A write
   that meets the quota drops the cached chapters and comment lists and tries once more. Plain
   functions: tests/core_test.js can run makeStore with a stand-in for localStorage. */

export const K = {
  code: "rv.code", lang: "rv.lang", strings: "rv.strings", langs: "rv.langs", me: "rv.me", outbox: "rv.outbox",
  draftOwner: "rv.draftOwner",   // the name of the reader whose drafts the device keeps
};
export const chKey = (b, c) => "rv.ch:" + b + "/" + c;
export const cmKey = (b, c) => "rv.cm:" + b + "/" + c;
export const draftKey = (b, c, a) => "rv.draft:" + b + "/" + c + "/" + a;   // one unsent comment per paragraph

/* The book, chapter and paragraph of a draft's key, or null for any other key. */
export function parseDraftKey(k) {
  const m = /^rv\.draft:([^/]+)\/([^/]+)\/([^/]+)$/.exec(String(k));
  return m ? { book: m[1], ch: m[2], a: m[3] } : null;
}

export function makeStore(ls) {
  let mem = null;
  try { ls.setItem("rv.probe", "1"); ls.removeItem("rv.probe"); } catch (e) { mem = new Map(); }
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

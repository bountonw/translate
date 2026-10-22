/* Proofreading site: the reader's page (web/app.js).

   Shows the chapters a reader may open, the chapter text, and the reader's own comments.
   The page draws from the localStorage cache first and checks the server in the background
   (chapters by ETag). Every write goes into an outbox in localStorage, keyed by client_id, and is
   sent, retried with backoff and confirmed in the background, so reading and typing never wait
   for the network. Every word of the interface comes from ui-strings.json.

   Part one ("core") holds plain functions with no DOM, so a node script can load this file and
   test them. Part two draws the page. */
(function () {
  "use strict";

  /* ================================ core ================================ */

  const TIMEOUT_MS = 8000;   // a fetch is given up after this long and tried again later
  const LEASE_MS = 20000;    // an op marked "sending" longer ago than this was lost with its tab
  const PLACE_DELAY_MS = 5000;  // places reported within this time go out as one write
  const FIELDS = ["kind", "quote", "text"];

  function randomId() {
    const b = new Uint8Array(16);
    crypto.getRandomValues(b);
    return Array.from(b, x => x.toString(16).padStart(2, "0")).join("");
  }

  /* The wait before retry number `tries`: 2 s, doubling up to 60 s, give or take 20%. */
  function backoff(tries, rand) {
    const base = Math.min(60000, 2000 * 2 ** Math.max(0, tries - 1));
    return Math.round(base * (0.8 + 0.4 * (rand === undefined ? Math.random() : rand)));
  }

  /* JSON in localStorage behind try/catch. Blocked storage falls back to memory for this visit.
     A write that meets the quota drops the cached chapters and comment lists and tries once more. */
  function makeStore(ls) {
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

  /* ---- The outbox: an array of ops, saved to localStorage after every change.
     op = {op, type: create|update|delete|place|finished, code, cid?, id?, key?, book, ch, a?, body,
           t, rev, tries, sent, next, sending, failed}
     Ops of one comment (same cid) or one setting (same key) go out in order; others never wait. */

  const isSending = (o, now) => !!o.sending && now - o.sending < LEASE_MS;
  const chainOf = o => (o.cid ? "c:" + o.cid : "k:" + o.key);

  function newOp(type, code, now, extra) {
    return Object.assign({ op: randomId(), type, code, t: now, rev: 0, tries: 0, sent: 0, next: 0, sending: 0, failed: null }, extra);
  }

  function queueCreate(ob, c, code, now) {
    const body = { client_id: c.client_id, book: c.book, ch: c.ch, a: c.a, kind: c.kind, quote: c.quote || "", text: c.text };
    ob.push(newOp("create", code, now, { cid: c.client_id, book: c.book, ch: c.ch, a: c.a, body }));
    return ob;
  }

  /* An edit joins a create or update still in the outbox; otherwise it becomes a new update. */
  function queueEdit(ob, c, fields, code, now) {
    const mine = ob.filter(o => o.cid === c.client_id && o.type !== "delete");
    const target = mine.find(o => o.type === "create") || mine.find(o => o.type === "update");
    if (target) {
      Object.assign(target.body, fields);
      target.rev++;
      if (target.failed) { target.failed = null; target.tries = 0; target.next = 0; }
      return ob;
    }
    ob.push(newOp("update", code, now, { cid: c.client_id, id: c.id, book: c.book, ch: c.ch, a: c.a, body: Object.assign({}, fields) }));
    return ob;
  }

  /* A comment the server cannot have seen is simply dropped; otherwise a delete goes out. */
  function queueDelete(ob, c, code, now) {
    const cid = c.client_id;
    const create = ob.find(o => o.cid === cid && o.type === "create");
    const onServer = c.id != null || (!!create && !create.failed && (isSending(create, now) || create.sent > 0));
    ob = ob.filter(o => o.cid !== cid || isSending(o, now) || (o === create && onServer));
    if (onServer) ob.push(newOp("delete", code, now, { cid, id: c.id, book: c.book, ch: c.ch, a: c.a }));
    return ob;
  }

  /* Place and finished: the newest value replaces an older one that is still waiting. */
  function queueSet(ob, type, body, code, now, delay) {
    const key = type + ":" + body.book + "/" + body.ch;
    const old = ob.find(o => o.key === key && o.code === code);
    if (old) {
      old.body = Object.assign({}, body);
      old.rev++;
      if (old.failed) { old.failed = null; old.tries = 0; old.next = 0; }
      return ob;
    }
    ob.push(newOp(type, code, now, { key, book: body.book, ch: body.ch, body: Object.assign({}, body), next: now + (delay || 0) }));
    return ob;
  }

  /* The first op that may go now: the head of its chain, not failed, not sending, not waiting. */
  function pickNext(ob, now) {
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
  function nextWake(ob, now) {
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

  function classify(type, status) {
    if (status >= 200 && status < 300) return "ok";
    if (status === 404 && type === "delete") return "ok";     // already gone
    if (status === 0) return "net";                          // offline or timed out
    if (status === 401) return "auth";
    if (status === 408 || status === 425 || status === 429 || status >= 500) return "retry";
    return "fail";                                           // the server refused this op
  }

  function requestFor(o) {
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
     changed while the request was out. */
  function settle(ob, opid, sentRev, verdict, data, status, now) {
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
          return ob;
        }
        return ob.filter(x => x !== o);
      }
      if (o.rev !== sentRev) { o.tries = 0; o.next = 0; return ob; }   // changed while out: send again
      return ob.filter(x => x !== o);
    }
    if (verdict === "retry") { o.tries++; o.next = now + backoff(o.tries); return ob; }
    if (verdict === "fail") {
      if (o.type === "create" || o.type === "update") {
        o.failed = { status, error: (data && data.error) || "", message: (data && data.message) || "" };
        return ob;
      }
      return ob.filter(x => x !== o);   // a refused delete, place or finished is dropped
    }
    return ob;   // "net" and "auth": the caller decides
  }

  /* Send one op. io = {load(), save(ob), send(method, path, body, code) -> {status, data}, now()}.
     Returns {verdict, op, data}, or null when nothing is due. */
  async function flushOnce(io) {
    const ob = io.load();
    const o = pickNext(ob, io.now());
    if (!o) return null;
    const req = requestFor(o);
    if (!req) {
      io.save(ob.filter(x => x !== o));
      return { verdict: "dropped", op: o, data: null };
    }
    o.sending = io.now();
    o.sent = (o.sent || 0) + 1;
    const opid = o.op, rev = o.rev;
    io.save(ob);
    const r = await io.send(req[0], req[1], req[2], o.code);
    const verdict = classify(o.type, r.status);
    const data = r.data && typeof r.data === "object" && r.data.comment ? r.data.comment : r.data;
    io.save(settle(io.load(), opid, rev, verdict, data, r.status, io.now()));
    return { verdict, op: o, data };
  }

  /* The reader's comments on one chapter as they should look now: the server's list with the
     outbox laid over it. Each comment gets a state: saved, saving or failed. */
  function overlay(list, ob, book, ch, code) {
    const map = new Map();
    // Every comment carries its chapter, so an edit or delete made from this list finds its way back.
    for (const c of list || []) map.set(c.client_id, Object.assign({}, c, { book, ch, state: "saved" }));
    for (const o of ob) {
      if (!o.cid || o.book !== book || o.ch !== ch || o.code !== code) continue;
      const cur = map.get(o.cid);
      const state = o.failed ? "failed" : "saving";
      const failure = o.failed || null;
      if (o.type === "create") map.set(o.cid, Object.assign({ processed: false }, cur, o.body, { client_id: o.cid, state, failure }));
      else if (o.type === "update" && cur) map.set(o.cid, Object.assign({}, cur, o.body, { state, failure }));
      else if (o.type === "delete") map.delete(o.cid);
    }
    return [...map.values()];
  }

  /* Lay waiting place and finished writes over a chapter list from the server. */
  function applyPending(me, ob, code) {
    for (const o of ob) {
      if (o.code !== code || (o.type !== "place" && o.type !== "finished")) continue;
      const c = me.chapters.find(x => x.book === o.book && x.id === o.ch);
      if (!c) continue;
      if (o.type === "place") c.place = o.body.a;
      else c.finished = !!o.body.finished;
    }
    return me;
  }

  /* A comment list from the server; a comment without a client_id is keyed by its id. */
  function normComments(d) {
    const list = Array.isArray(d) ? d : d && Array.isArray(d.comments) ? d.comments : [];
    return list.filter(c => c && typeof c === "object").map(c => (c.client_id ? c : Object.assign({ client_id: "id:" + c.id }, c)));
  }

  const count = x => (Array.isArray(x) ? x.length : Number(x) || 0);
  const first = (...xs) => xs.find(x => x !== undefined && x !== null);   // like ??, which older Safari cannot read

  /* GET /api/me in the shape the page uses. */
  function normMe(d) {
    d = d || {};
    const r = d.reader && typeof d.reader === "object" ? d.reader : d;
    const books = {}, langs = {};
    if (Array.isArray(d.books)) {
      for (const b of d.books) { books[b.id] = b.title_th || b.title_en || b.title || b.id; langs[b.id] = b.language || "th"; }
    } else if (d.books && typeof d.books === "object") {
      for (const [k, v] of Object.entries(d.books)) books[k] = typeof v === "string" ? v : v.title_th || v.title_en || v.title || k;
    }
    const chapters = (Array.isArray(d.chapters) ? d.chapters : []).map(c => ({
      book: c.book, id: c.id, n: Number(c.n) || 0,
      title_th: c.title_th || "", title_en: c.title_en || "", version: c.version,
      count: count(first(c.paragraphs, c.paragraph_count, c.n_paragraphs, c.count)),
      comments: count(first(c.comments, c.comment_count, c.comments_count, c.own_comments)),
      finished: c.finished && typeof c.finished === "object" ? !!c.finished.finished : !!c.finished,
      place: c.place && typeof c.place === "object" ? c.place.a || null : c.place || null,
    }));
    return { name: r.name || "", english: !!first(r.english, d.english), books, langs, chapters };
  }

  /* GET /api/chapter/<book>/<id> in the shape the page uses. */
  function normChapter(d) {
    d = d || {};
    const c = d.chapter && typeof d.chapter === "object" ? Object.assign({}, d, d.chapter) : d;
    let paras = first(c.paragraphs, c.paras, []);
    if (typeof paras === "string") { try { paras = JSON.parse(paras); } catch (e) { paras = []; } }
    return {
      book: c.book, id: c.id, n: Number(c.n) || 0,
      title_th: c.title_th || "", title_en: c.title_en || "", version: c.version,
      paras: (Array.isArray(paras) ? paras : []).map(p => ({ a: p.a, th: p.th || "", fn: Array.isArray(p.fn) ? p.fn : [], en: p.en || "" })),
    };
  }

  const core = {
    TIMEOUT_MS, LEASE_MS, randomId, backoff, makeStore, queueCreate, queueEdit, queueDelete, queueSet,
    pickNext, nextWake, classify, requestFor, settle, flushOnce, overlay, applyPending, normMe, normChapter, normComments,
  };
  if (typeof document === "undefined") {
    if (typeof module === "object" && module.exports) module.exports = core;
    return;
  }

  /* ================================ page ================================ */

  let lsRef = null;
  try { lsRef = window.localStorage; } catch (e) { lsRef = null; }
  const store = makeStore(lsRef);
  const K = { code: "rv.code", lang: "rv.lang", strings: "rv.strings", me: "rv.me", outbox: "rv.outbox" };
  const chKey = (b, c) => "rv.ch:" + b + "/" + c;
  const cmKey = (b, c) => "rv.cm:" + b + "/" + c;
  const draftKey = (b, c, a) => "rv.draft:" + b + "/" + c + "/" + a;   // one unsent comment per paragraph
  const enc = encodeURIComponent;
  const $ = id => document.getElementById(id);
  const shortA = a => String(a || "").replace(/^\S+\s+/, "");          // "SC 9.1" -> "9.1"
  const paraId = a => "p-" + String(a).replace(/[^A-Za-z0-9]/g, "-");

  const S = {
    code: null, me: null, meAt: 0, view: "boot", authBlocked: false,
    book: null, ch: null, chapter: null, waiting: null,   // the open chapter; a newer text held back
    lastSel: null, saved: new Map(), homeY: 0, homeSig: "",
    from: null,   // the chapter the list of unsaved comments was opened from
  };
  let firstMe = null;   // the first /api/me request, started in boot() alongside the words

  /* The language of a book's text, th or lo, for the lang attribute and the font. */
  const bookLang = book => (S.me && S.me.langs && S.me.langs[book]) || "th";
  let STR = {};
  let lang = "th";
  let netFails = 0;

  /* ---- words ---- */

  function t(id, vars) {
    const s = STR[id];
    let out = s ? (lang === "th" && s.th) || s.en || s.th || id : id;
    if (vars) out = out.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
    return out;
  }
  const tIn = (l, id) => { const s = STR[id]; return s ? (l === "th" && s.th) || s.en || id : id; };
  const plural = (n, one, many) => t(n === 1 ? one : many, { n });

  async function loadStrings() {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
    try {
      const r = await fetch("ui-strings.json", { cache: "no-cache", credentials: "omit", signal: ctl.signal });
      if (!r.ok) return false;
      const d = await r.json();
      if (!d || typeof d !== "object") return false;
      const changed = JSON.stringify(d) !== JSON.stringify(STR);
      STR = d;
      store.set(K.strings, d);
      return changed;
    } catch (e) {
      return false;
    } finally {
      clearTimeout(timer);
    }
  }

  function applyLang() {
    document.documentElement.lang = lang;
    document.title = t("app_title");
    $("back").textContent = t("back");
  }

  function setLang(l) {
    lang = l;
    store.set(K.lang, l);
    rerender();
  }

  /* ---- building the page ---- */

  function h(tag, props, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v == null || v === false) continue;
      if (k === "class") e.className = v;
      else if (k === "text") e.textContent = v;
      else if (k === "value" || k === "checked") e[k] = v;
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v === true ? "" : String(v));
    }
    for (const c of kids.flat()) if (c != null && c !== false) e.append(c);
    return e;
  }

  /* Book text arrives as HTML made by the server's parser. It is parsed in an inert template and
     rebuilt with a short list of tags and only the class attribute. Reader text never comes here. */
  const BOOK_TAGS = new Set(["EM", "I", "STRONG", "B", "SUP", "SUB", "SMALL", "SPAN", "P", "BR"]);
  function bookHtml(html) {
    const tpl = document.createElement("template");
    tpl.innerHTML = String(html || "");
    const out = document.createDocumentFragment();
    (function copy(from, to) {
      for (const n of from.childNodes) {
        if (n.nodeType === 3) to.append(n.data);
        if (n.nodeType !== 1 || n.tagName === "SCRIPT" || n.tagName === "STYLE") continue;
        let into = to;
        if (BOOK_TAGS.has(n.tagName)) {
          into = document.createElement(n.tagName.toLowerCase());
          const cls = n.getAttribute("class");
          if (cls) into.className = cls;
          to.append(into);
        }
        copy(n, into);
      }
    })(tpl.content, out);
    return out;
  }

  function showNotice(text) {
    const n = $("notice");
    n.textContent = text;
    n.hidden = false;
  }

  function setHash(hash, push) {
    const url = location.pathname + location.search + hash;
    try {
      if (push) history.pushState({ list: true }, "", url);
      else history.replaceState(hash ? history.state : null, "", url);
    } catch (e) { /* history is not available here */ }
  }

  function langSwitch() {
    return h("div", { class: "lang", role: "group", "aria-label": t("language") },
      h("button", { type: "button", class: "lang-btn", lang: "th", "aria-pressed": String(lang === "th"), text: tIn("th", "lang_th"), onclick: () => setLang("th") }),
      h("button", { type: "button", class: "lang-btn", lang: "en", "aria-pressed": String(lang === "en"), text: tIn("en", "lang_en"), onclick: () => setLang("en") }));
  }

  /* The bar shows only inside a chapter: the way back, the chapter, and the reader's place. */
  function setBar(c) {
    $("bar").hidden = !c;
    $("bar-title").textContent = c ? c.n + " · " + c.title_th : t("app_title");
    $("bar-title").lang = c ? bookLang(c.book) : "";
    $("bar-place").textContent = "";
  }

  function rerender() {
    applyLang();
    if (S.view === "home") renderHome(true);
    else if (S.view === "link") showLink();
    else if (S.view === "offline") showOffline();
    else if (S.view === "unsaved") showUnsaved();
    else if (S.view === "chapter" && S.chapter && !document.querySelector("#main .para.open")) {
      const data = S.chapter;
      keepPosition(() => renderChapter(data, false));
    }
    paintSync();
  }

  /* ---- talking to the server ---- */

  async function api(method, path, opts) {
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
      try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
      return { status: r.status, data, etag: r.headers.get("ETag") };
    } catch (e) {
      return { status: 0, data: null, etag: null };
    } finally {
      clearTimeout(timer);
    }
  }

  const loadOb = () => { const v = store.get(K.outbox); return Array.isArray(v) ? v : []; };
  const saveOb = ob => store.set(K.outbox, ob);
  function mutateOb(fn) {
    const ob = fn(loadOb());
    saveOb(ob);
    paintSync();
    return ob;
  }
  const io = {
    load: loadOb, save: saveOb, now: () => Date.now(),
    send: (method, path, body, code) => api(method, path, { body, code, keepalive: true }),
  };

  /* Send the outbox one op at a time, in the background. One tab sends at a time. */
  let flushing = false, wakeTimer = 0;
  function flush() {
    if (flushing || S.authBlocked) return;
    flushing = true;
    const run = async () => {
      for (;;) {
        const r = await flushOnce(io);
        if (!r) return "idle";
        handleResult(r);
        if (r.verdict === "net") { netFails++; return "net"; }
        if (r.verdict === "auth") return "auth";
        if (r.verdict !== "dropped") netFails = 0;
      }
    };
    const job = navigator.locks
      ? navigator.locks.request("rv-outbox", { ifAvailable: true }, lock => (lock ? run() : "busy"))
      : run();
    Promise.resolve(job)
      .catch(err => { console.error(err); return "error"; })
      .then(how => { flushing = false; schedule(how === "busy" || how === "error" ? 1000 : 0); });
  }

  function schedule(minDelay) {
    clearTimeout(wakeTimer);
    paintSync();
    if (S.authBlocked) return;
    const now = Date.now();
    let at = nextWake(loadOb(), now);
    if (at === Infinity) return;
    if (netFails) at = Math.max(at, now + backoff(netFails));
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
      if (o.type !== "delete") {
        S.saved.set(o.cid, Date.now());
        setTimeout(repaintComments, 4200);
      }
    }
    if (S.view === "chapter" && o.book === S.book && o.ch === S.ch) repaintComments();
    else if (S.view === "home") renderHome(false);
  }

  /* The note at the foot of the screen. Comments the server refused make it a button that lists them;
     changes that wait because the reader is offline, or because the server asked to try later, show
     as a count. */
  function paintSync() {
    const el = $("sync");
    if (!el) return;
    const ob = loadOb().filter(o => o.code === S.code);
    const failed = ob.filter(o => o.failed).length;
    const waiting = ob.length - failed;
    const offline = netFails > 0 || navigator.onLine === false;
    const retrying = ob.some(o => !o.failed && o.tries > 0);
    el.textContent = "";
    el.classList.toggle("bad", failed > 0);
    el.classList.toggle("has-btn", failed > 0);
    if (failed) {
      if (S.view !== "unsaved") el.append(h("button", { type: "button", class: "sync-btn", text: plural(failed, "failed_one", "failed_many"), onclick: showUnsaved }));
    } else if (waiting && offline) el.textContent = t("offline") + " · " + plural(waiting, "waiting_one", "waiting_many");
    else if (waiting && retrying) el.textContent = plural(waiting, "waiting_one", "waiting_many");
    el.hidden = !el.textContent;
  }

  async function refreshMe() {
    if (!S.code || S.authBlocked) return false;
    const pending = firstMe;
    firstMe = null;
    const r = await (pending || api("GET", "api/me"));
    if (r.status === 401) { authFailed(); return false; }
    if (r.status === 200 && r.data) {
      S.me = applyPending(normMe(r.data), loadOb(), S.code);
      S.meAt = Date.now();
      store.set(K.me, S.me);
      onMe();
      return true;
    }
    if (!S.me) showOffline();
    return false;
  }

  function onMe() {
    if (S.view === "boot" || S.view === "offline") route();
    else if (S.view === "home") renderHome(false);
    else if (S.view === "chapter") {
      const c = meChapter();
      if (!c || !S.chapter || c.version !== S.chapter.version) revalidateChapter(S.book, S.ch);
      else {
        setBar(c);
        $("bar-place").textContent = c.place ? shortA(c.place) : "";
        const f = $("finish");
        if (f) f.replaceWith(renderFinish());
      }
    }
    schedulePrefetch();
  }

  /* Returns {data, changed}, "gone" (withdrawn or not granted), or null (offline or a server fault). */
  async function fetchChapter(book, id) {
    const key = chKey(book, id);
    const rec = store.get(key);
    const english = !!(S.me && S.me.english);
    const etag = rec && rec.data && rec.english === english ? rec.etag : null;
    const r = await api("GET", "api/chapter/" + enc(book) + "/" + enc(id), { etag });
    if (r.status === 304 && rec && rec.data) return { data: rec.data, changed: false };
    if (r.status === 200 && r.data) {
      const data = normChapter(r.data);
      const changed = !rec || !rec.data || rec.data.version !== data.version || rec.english !== english;
      store.set(key, { etag: r.etag, english, data });
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

  async function revalidateChapter(book, id) {
    const r = await fetchChapter(book, id);
    if (S.view !== "chapter" || S.book !== book || S.ch !== id) return;
    if (r === "gone") return showChapterMessage(t("chapter_closed"), false);
    if (r) offerChapter(r.data);
    else if (!S.chapter) showChapterMessage(t("not_on_device"), true);
  }

  async function loadComments(book, id) {
    const key = cmKey(book, id);
    for (let i = 0; i < 3; i++) {
      const before = cmWrites.get(key) || 0;
      const r = await api("GET", "api/comments?book=" + enc(book) + "&ch=" + enc(id));
      if (r.status === 401) { authFailed(); return false; }
      if (r.status !== 200 || !r.data) return false;
      if ((cmWrites.get(key) || 0) !== before) continue;   // a write landed meanwhile: ask again
      store.set(key, { list: normComments(r.data) });
      if (S.view === "chapter" && S.book === book && S.ch === id) repaintComments();
      else if (S.view === "home") renderHome(false);
      return true;
    }
    return false;
  }

  /* After the chapter list arrives, fetch every chapter and comment list that is missing or old,
     one at a time, so each chapter opens at once and can be read offline. */
  let prefetchTimer = 0;
  function schedulePrefetch() {
    clearTimeout(prefetchTimer);
    prefetchTimer = setTimeout(prefetch, 1500);
  }
  async function prefetch() {
    if (!S.me || S.authBlocked) return;
    const chapters = S.me.chapters.slice();
    for (const c of chapters) {
      const rec = store.get(chKey(c.book, c.id));
      if (!rec || !rec.data || rec.data.version !== c.version || rec.english !== !!S.me.english) {
        const r = await fetchChapter(c.book, c.id);
        if (r === null || !S.me) return;   // offline: stop here and try on the next visit
        if (r !== "gone" && S.view === "chapter" && S.book === c.book && S.ch === c.id) offerChapter(r.data);
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

  function forgetReader() {
    for (const k of store.keys()) if (/^rv\.(ch|cm|draft):/.test(k)) store.del(k);
    store.del(K.me);
  }

  function authFailed() {
    S.authBlocked = true;
    forgetReader();
    S.me = null;
    showLink();
  }

  /* ---- screens ---- */

  function route() {
    if (!S.code || S.authBlocked) return showLink();
    if (!S.me) return showBoot();
    const m = /^#([^/=&]+)\/([^/=&]+)$/.exec(location.hash);
    if (m) {
      let book, id;
      try { book = decodeURIComponent(m[1]); id = decodeURIComponent(m[2]); } catch (e) { return showHome(); }
      if (S.view === "chapter" && S.book === book && S.ch === id) return;
      return openChapter(book, id, { resume: true });
    }
    if (S.view !== "home") showHome();
  }

  function leaveChapter() {
    if (S.view !== "chapter") return;
    stopTracking();
    S.book = S.ch = S.chapter = S.waiting = null;
  }

  function showScreen(view, ...kids) {
    leaveChapter();
    S.view = view;
    setBar(null);
    const main = $("main");
    main.textContent = "";
    main.append(...kids);
    window.scrollTo(0, 0);
  }

  function showBoot() {
    showScreen("boot", h("div", { class: "boot", "aria-hidden": "true" }));
  }

  function showLink() {
    showScreen("link", h("section", { class: "message" },
      h("div", { class: "home-top" }, h("h1", { text: t("link_title") }), langSwitch()),
      h("p", { class: "lead", text: t("link_body") })));
  }

  function showOffline() {
    const retry = async () => {
      showBoot();
      if (!Object.keys(STR).length && (await loadStrings())) applyLang();
      refreshMe();
    };
    showScreen("offline", h("section", { class: "message" },
      h("div", { class: "home-top" }, h("h1", { text: t("app_title") }), langSwitch()),
      h("p", { class: "lead", text: t("cannot_connect") }),
      h("button", { type: "button", class: "btn", text: t("retry_load"), onclick: retry })));
  }

  /* ---- comments the server refused ---- */

  const failedOps = () => loadOb().filter(o => o.code === S.code && o.failed);

  /* Why a comment was refused, in the reader's words. */
  function failNote(f) {
    const closed = f && (f.error === "no_chapter" || (!f.error && f.status === 404));
    return closed ? t("failed_closed") : t("failed_refused");
  }

  /* A button that copies text; where the clipboard is blocked it selects the text for the reader instead. */
  function copyButton(text, target) {
    const b = h("button", { type: "button", class: "link", text: t("copy") });
    b.addEventListener("click", () => {
      const select = () => {
        const r = document.createRange();
        r.selectNodeContents(target);
        const s = window.getSelection();
        s.removeAllRanges();
        s.addRange(r);
      };
      const done = () => {
        b.textContent = t("copied");
        setTimeout(() => { if (b.isConnected) b.textContent = t("copy"); }, 2500);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, select);
      else select();
    });
    return b;
  }

  /* A button that acts on the second tap within 4 seconds. */
  function twoTapButton(label, confirmLabel, action) {
    const b = h("button", { type: "button", class: "link danger", text: label });
    let armedAt = 0;
    b.addEventListener("click", () => {
      if (Date.now() - armedAt > 4000) {
        armedAt = Date.now();
        b.textContent = confirmLabel;
        setTimeout(() => { if (b.isConnected) b.textContent = label; }, 4000);
        return;
      }
      action();
    });
    return b;
  }

  function unsavedCard(o) {
    const c = S.me && S.me.chapters.find(x => x.book === o.book && x.id === o.ch);
    const where = (c ? t("chapter_n", { n: c.n }) : o.ch) + " · " + t("para_n", { a: shortA(o.a) });
    const body = o.body || {};
    const words = h("div", { class: "note-words", lang: bookLang(o.book) },
      body.quote ? h("p", { class: "note-quote", text: "“" + body.quote + "”" }) : null,
      h("p", { class: "note-text", text: body.text || "" }));
    const all = (body.quote ? "“" + body.quote + "”\n" : "") + (body.text || "");
    const remove = () => {
      mutateOb(ob => ob.filter(x => (o.type === "create" ? x.cid !== o.cid : x.op !== o.op)));
      showUnsaved();
    };
    return h("div", { class: "note failed" },
      h("p", { class: "note-where", text: where }),
      words,
      h("p", { class: "note-why", text: failNote(o.failed) }),
      h("div", { class: "note-acts" }, copyButton(all, words), twoTapButton(t("remove"), t("remove_confirm"), remove)));
  }

  /* Every comment the server refused, from any chapter, even one that is closed now. */
  function showUnsaved() {
    if (S.view !== "unsaved") S.from = S.view === "chapter" ? { book: S.book, ch: S.ch } : null;
    const from = S.from;
    const close = () => {
      if (from) openChapter(from.book, from.ch, { resume: true });
      else { setHash("", false); showHome(); }
    };
    const list = failedOps();
    showScreen("unsaved", h("section", { class: "message" },
      h("h1", { text: t("unsaved_title") }),
      h("p", { class: "lead", text: list.length ? t("unsaved_lead") : t("unsaved_none") }),
      h("div", { class: "notes" }, list.map(unsavedCard)),
      h("div", { class: "row" }, h("button", { type: "button", class: "btn ghost", text: t("close"), onclick: close }))));
    paintSync();
  }

  function showHome() {
    leaveChapter();
    S.view = "home";
    setBar(null);
    renderHome(true);
    window.scrollTo(0, S.homeY || 0);
  }

  function countComments(c, ob) {
    const rec = store.get(cmKey(c.book, c.id));
    if (rec && Array.isArray(rec.list)) return overlay(rec.list, ob, c.book, c.id, S.code).length;
    let n = c.comments;
    for (const o of ob) {
      if (o.code !== S.code || o.book !== c.book || o.ch !== c.id) continue;
      if (o.type === "create") n++;
      else if (o.type === "delete") n--;
    }
    return Math.max(0, n);
  }

  function renderHome(force) {
    const me = S.me;
    if (!me) return;
    const ob = loadOb();
    const rows = me.chapters.slice().sort((x, y) => x.n - y.n).map(c => {
      const status = c.finished ? "done" : c.place ? "reading" : "todo";
      const bits = [];
      if (c.place && !c.finished) bits.push(t("place", { a: shortA(c.place) }));
      if (c.count) bits.push(plural(c.count, "paras_one", "paras_many"));
      const n = countComments(c, ob);
      if (n) bits.push(plural(n, "comments_one", "comments_many"));
      return { c, status, meta: bits.join(" · ") };
    });
    const sig = JSON.stringify([lang, me.name, me.english, rows.map(r => [r.c.book, r.c.id, r.c.title_th, r.status, r.meta])]);
    if (!force && sig === S.homeSig) return;
    S.homeSig = sig;
    const statusText = { done: t("status_done"), reading: t("status_reading"), todo: t("status_new") };
    const main = $("main");
    main.textContent = "";
    main.append(h("header", { class: "home-head" },
      h("div", { class: "home-top" }, h("h1", { text: t("app_title") }), langSwitch()),
      me.name ? h("p", { class: "hello", text: t("hello", { name: me.name }) }) : null,
      h("p", { class: "lead", text: me.english ? t("hint_english") : t("hint") })));
    if (!rows.length) {
      main.append(h("p", { class: "lead empty", text: t("no_chapters") }));
      return;
    }
    const books = [...new Set(rows.map(r => r.c.book))];
    for (const book of books) {
      if (books.length > 1) main.append(h("h2", { class: "book", text: me.books[book] || book }));
      main.append(h("ul", { class: "shelf" }, rows.filter(r => r.c.book === book).map(r => h("li", null,
        h("button", { type: "button", class: "ch-row", onclick: () => { S.homeY = window.scrollY; openChapter(r.c.book, r.c.id, { resume: true, push: true }); } },
          h("span", { class: "ch-num", text: String(r.c.n) }),
          h("span", { class: "ch-names" },
            h("span", { class: "ch-th", lang: bookLang(r.c.book), text: r.c.title_th }),
            me.english && r.c.title_en ? h("span", { class: "ch-en", lang: "en", text: r.c.title_en }) : null),
          h("span", { class: "chip " + r.status, text: statusText[r.status] }),
          r.meta ? h("span", { class: "ch-meta", text: r.meta }) : null)))));
    }
  }

  const meChapter = () => (S.me ? S.me.chapters.find(c => c.book === S.book && c.id === S.ch) : null);

  function openChapter(book, id, opts) {
    const meCh = S.me && S.me.chapters.find(c => c.book === book && c.id === id);
    if (!meCh) { setHash("", false); return showHome(); }
    leaveChapter();
    S.view = "chapter";
    S.book = book;
    S.ch = id;
    setHash("#" + enc(book) + "/" + enc(id), !!opts.push);
    setBar(meCh);
    const rec = store.get(chKey(book, id));
    if (rec && rec.data) renderChapter(rec.data, opts.resume);
    else {
      const main = $("main");
      main.textContent = "";
      main.append(h("p", { class: "lead loading", text: t("loading") }));
      window.scrollTo(0, 0);
    }
    revalidateChapter(book, id);
    loadComments(book, id);
  }

  function showChapterMessage(text, canRetry) {
    if (S.view !== "chapter") return;
    stopTracking();
    S.chapter = null;
    const book = S.book, id = S.ch;
    const main = $("main");
    main.textContent = "";
    main.append(h("section", { class: "message" },
      h("p", { class: "lead", text }),
      h("div", { class: "row" },
        canRetry ? h("button", { type: "button", class: "btn", text: t("retry_load"), onclick: () => openChapter(book, id, { resume: true }) }) : null,
        h("button", { type: "button", class: "btn ghost", text: t("all_chapters"), onclick: goHome }))));
    window.scrollTo(0, 0);
  }

  function goHome() {
    if (history.state && history.state.list) { history.back(); return; }   // popstate draws the list
    setHash("", false);
    showHome();
  }

  /* A chapter text arrived for the open chapter. Draw it if nothing is drawn yet; redraw only when
     it differs from what is on screen, and not while a comment drawer is open. */
  function offerChapter(data) {
    if (!S.chapter) return renderChapter(data, true);
    const hasEn = d => d.paras.some(p => p.en);
    if (data.version === S.chapter.version && hasEn(data) === hasEn(S.chapter)) return;
    if (document.querySelector("#main .para.open")) { S.waiting = data; return; }
    keepPosition(() => renderChapter(data, false));
  }

  /* Redraw without moving the paragraph at the top of the screen. */
  function keepPosition(fn) {
    const barBottom = $("bar").getBoundingClientRect().bottom;
    const top = [...document.querySelectorAll("#main .para")].find(x => x.getBoundingClientRect().bottom > barBottom + 1);
    const a = top && top.dataset.a;
    const off = top ? top.getBoundingClientRect().top : 0;
    fn();
    const el = a && document.getElementById(paraId(a));
    if (el) { markJump(); window.scrollBy(0, el.getBoundingClientRect().top - off); }
  }

  function renderChapter(data, resume) {
    stopTracking();
    S.chapter = data;
    S.waiting = null;
    setBar(meChapter() || data);
    const main = $("main");
    main.textContent = "";
    main.append(h("header", { class: "ch-head" },
      h("p", { class: "eyebrow", text: t("chapter_n", { n: data.n }) }),
      h("h1", { lang: bookLang(data.book), text: data.title_th }),
      S.me.english && data.title_en ? h("p", { class: "ch-en", lang: "en", text: data.title_en }) : null,
      h("p", { class: "hint", text: S.me.english ? t("hint_english") : t("hint") })));
    const list = currentComments();
    for (const p of data.paras) main.append(renderPara(p, list));
    main.append(renderGone(list), renderFinish());
    const c = meChapter();
    $("bar-place").textContent = c && c.place ? shortA(c.place) : "";
    if (resume) resumePlace();
    startTracking();
  }

  function resumePlace() {
    const c = meChapter();
    const first = S.chapter.paras[0];
    const target = c && c.place && first && c.place !== first.a ? c.place : null;
    if (!(target && jumpTo(target, true))) { markJump(); window.scrollTo(0, 0); }
    // The font may arrive after the jump and move the text; jump again unless the reader has scrolled.
    if (target && document.fonts && document.fonts.ready) {
      const ch = S.ch;
      document.fonts.ready.then(() => { if (!armed && S.ch === ch) jumpTo(target, false); });
    }
  }

  function jumpTo(a, withFlash) {
    const el = document.getElementById(paraId(a));
    if (!el) return false;
    markJump();
    el.scrollIntoView({ block: "start" });
    if (withFlash) {
      el.classList.remove("flash");
      void el.offsetWidth;
      el.classList.add("flash");
    }
    return true;
  }

  function currentComments() {
    const rec = store.get(cmKey(S.book, S.ch));
    return overlay(rec && Array.isArray(rec.list) ? rec.list : [], loadOb(), S.book, S.ch, S.code);
  }

  function repaintComments() {
    if (S.view !== "chapter" || !S.chapter) return;
    const list = currentComments();
    for (const art of document.querySelectorAll("#main .para")) paintPara(art, list);
    const gone = $("gone");
    if (gone) gone.replaceWith(renderGone(list));
  }

  /* The reader's comments on paragraphs that a newer version of the chapter no longer has. */
  function renderGone(list) {
    const known = new Set(S.chapter.paras.map(p => p.a));
    const gone = list.filter(c => !known.has(c.a));
    const box = h("div", { class: "notes" });
    renderNotes(null, box, gone);
    return h("section", { class: "gone", id: "gone", hidden: !gone.length },
      h("h2", { text: t("gone_title") }),
      h("p", { class: "hint", text: t("gone_lead") }),
      box);
  }

  /* ---- paragraphs ---- */

  function renderPara(p, list) {
    const lg = bookLang(S.book);
    const art = h("article", { class: "para", id: paraId(p.a), "data-a": p.a, tabindex: "0", "aria-expanded": "false" },
      h("p", { class: "th", lang: lg }, bookHtml(p.th), h("span", { class: "tag", text: shortA(p.a) }), h("span", { class: "badge" })),
      p.fn.length ? h("ol", { class: "fns", lang: lg }, p.fn.map(f => h("li", null, bookHtml(f)))) : null);
    art.addEventListener("click", ev => {
      // A button inside the drawer may redraw itself during its own click; once detached it is no longer inside art.
      if (!art.contains(ev.target) || ev.target.closest(".drawer")) return;
      const sel = selectionIn(art);
      if (!art.classList.contains("open")) openDrawer(art, p, sel);
      else if (sel) fillQuote(art, sel);
      else closeDrawer(art);
    });
    art.addEventListener("keydown", ev => {
      if (ev.target === art && (ev.key === "Enter" || ev.key === " ")) {
        ev.preventDefault();
        if (art.classList.contains("open")) closeDrawer(art); else openDrawer(art, p, null);
      } else if (ev.key === "Escape" && art.classList.contains("open")) {
        closeDrawer(art);
        art.focus();
      }
    });
    paintPara(art, list);
    return art;
  }

  function paintPara(art, list) {
    const mine = list.filter(c => c.a === art.dataset.a);
    art.classList.toggle("has-notes", mine.length > 0);
    art.classList.toggle("has-failed", mine.some(c => c.state === "failed"));
    art.querySelector(".badge").textContent = mine.length ? plural(mine.length, "comments_one", "comments_many") : "";
    const box = art.querySelector(".drawer .notes");
    if (box) renderNotes(art, box, mine);
  }

  /* The words the reader selected inside this paragraph, without the paragraph number,
     the comment count and the footnote numbers. */
  function quoteFromSelection(art) {
    const s = window.getSelection && window.getSelection();
    if (!s || s.isCollapsed || !s.rangeCount) return null;
    const inText = node => {
      const el = node && (node.nodeType === 1 ? node : node.parentElement);
      return !!el && art.contains(el) && !el.closest(".drawer");
    };
    if (!inText(s.anchorNode) || !inText(s.focusNode)) return null;
    const frag = s.getRangeAt(0).cloneContents();
    for (const x of frag.querySelectorAll(".tag, .badge, sup.fn")) x.remove();
    return frag.textContent.replace(/\s+/g, " ").trim().slice(0, 500) || null;
  }

  function selectionIn(art) {
    const q = quoteFromSelection(art);
    if (q) return q;
    // On a phone the selection is often gone by the time the paragraph is tapped.
    const last = S.lastSel;
    return last && last.a === art.dataset.a && Date.now() - last.t < 90000 ? last.text : null;
  }

  function onSelection() {
    if (S.view !== "chapter") return;
    const s = window.getSelection();
    if (!s || s.isCollapsed || !s.anchorNode) return;
    const el = s.anchorNode.nodeType === 1 ? s.anchorNode : s.anchorNode.parentElement;
    const art = el && el.closest(".para");
    if (!art) return;
    const text = quoteFromSelection(art);
    if (!text) return;
    S.lastSel = { a: art.dataset.a, text, t: Date.now() };
    if (art.classList.contains("open")) fillQuote(art, text);
  }

  /* Put selected words in the quote box unless the reader typed something there. */
  function fillQuote(art, text) {
    const q = art.querySelector(".drawer input[name=quote]");
    if (!q || (q.value && q.dataset.auto !== "1")) return;
    q.value = text;
    q.dataset.auto = "1";
    q.dispatchEvent(new Event("input", { bubbles: true }));
  }

  /* Open the comment drawer under a paragraph. The tapped paragraph stays where it was on the screen,
     even when an open drawer above it closes. When the new drawer would start low on the screen, the
     page scrolls so that it starts about a third of the way down; when the comment box would end below
     the screen, the page scrolls just enough to show it, and never moves the drawer above that third. */
  function openDrawer(art, p, quote) {
    const before = art.getBoundingClientRect().top;
    art.classList.add("open");
    art.setAttribute("aria-expanded", "true");
    for (const o of document.querySelectorAll("#main .para.open")) if (o !== art) closeDrawer(o);
    art.append(h("div", { class: "drawer" },
      S.me.english && p.en ? h("section", { class: "en-block" },
        h("p", { class: "label", text: t("english") }),
        h("div", { class: "en", lang: "en" }, bookHtml(p.en))) : null,
      h("section", { class: "notes-block" },
        h("p", { class: "label", text: t("your_comments") }),
        h("div", { class: "notes" })),
      commentForm(art, p, null, quote)));
    paintPara(art, currentComments());
    S.lastSel = null;
    let by = art.getBoundingClientRect().top - before;
    const drawer = art.querySelector(".drawer");
    const top = drawer.getBoundingClientRect().top - by;
    const box = drawer.querySelector("textarea").getBoundingClientRect().bottom - by;
    const want = Math.max($("bar").getBoundingClientRect().bottom + 8, window.innerHeight * 0.35);
    const low = window.innerHeight - 8;
    if (top > window.innerHeight - 160) by += top - want;
    else if (top > want && box > low) by += Math.min(top - want, box - low);
    if (by) { markJump(); window.scrollBy(0, by); }
  }

  function closeDrawer(art) {
    art.classList.remove("open");
    art.setAttribute("aria-expanded", "false");
    const d = art.querySelector(".drawer");
    if (d) d.remove();
    if (S.waiting && !document.querySelector("#main .para.open")) {
      const data = S.waiting;
      keepPosition(() => renderChapter(data, false));
    }
  }

  let formSeq = 0;
  /* The form for a new comment (c null) or for changing comment c. */
  function commentForm(art, p, c, quote) {
    const seq = ++formSeq;
    const dKey = draftKey(S.book, S.ch, p.a);
    const draft = c ? null : store.get(dKey);
    const kindNow = c ? c.kind : draft ? draft.kind : "flag";

    const kinds = h("fieldset", { class: "kinds" }, h("legend", { class: "label", text: c ? t("edit_comment") : t("new_comment") }));
    for (const [value, name, hint] of [["flag", t("kind_flag"), t("kind_flag_hint")], ["wording", t("kind_wording"), t("kind_wording_hint")]]) {
      const id = "kind-" + seq + "-" + value;
      kinds.append(h("label", { class: "kind", for: id },
        h("input", { type: "radio", name: "kind", value, id, checked: kindNow === value }),
        h("span", { class: "kind-text" }, h("span", { class: "kind-name", text: name }), h("span", { class: "kind-hint", text: hint }))));
    }
    const quoteLabel = h("span");
    const lg = bookLang(S.book);
    const quoteBox = h("input", { name: "quote", type: "text", maxlength: "500", autocomplete: "off", lang: lg, value: c ? c.quote || "" : quote || (draft && draft.quote) || "" });
    if (!c && quote) quoteBox.dataset.auto = "1";
    const textLabel = h("span");
    const textBox = h("textarea", { name: "text", maxlength: "4000", rows: "4", lang: lg, value: c ? c.text || "" : (draft && draft.text) || "" });
    const status = h("span", { class: "status", "aria-live": "polite" });
    const f = h("form", { class: "note-form", novalidate: true },
      kinds,
      h("label", { class: "field" }, quoteLabel, quoteBox),
      h("label", { class: "field" }, textLabel, textBox),
      h("div", { class: "row" },
        h("button", { type: "submit", class: "btn", text: t("save") }),
        h("button", { type: "button", class: "btn ghost", text: c ? t("cancel") : t("close"),
          onclick: () => (c ? f.replaceWith(commentForm(art, p, null, null)) : closeDrawer(art)) }),
        status));

    const kind = () => (f.querySelector("input[name=kind]:checked") || {}).value || "flag";
    const relabel = () => {
      const w = kind() === "wording";
      quoteLabel.textContent = w ? t("quote_label_wording") : t("quote_label_flag");
      textLabel.textContent = w ? t("text_label_wording") : t("text_label_flag");
    };
    const keepDraft = () => {
      if (c) return;
      if (quoteBox.value || textBox.value) store.set(dKey, { kind: kind(), quote: quoteBox.value, text: textBox.value });
      else store.del(dKey);
    };
    relabel();
    f.addEventListener("change", () => { relabel(); keepDraft(); });
    f.addEventListener("input", keepDraft);
    quoteBox.addEventListener("input", ev => { if (ev.isTrusted) delete quoteBox.dataset.auto; });

    f.addEventListener("submit", ev => {
      ev.preventDefault();
      const k = kind();
      const text = textBox.value.trim();
      const q = quoteBox.value.trim().slice(0, 500);
      if (!text) { status.textContent = k === "wording" ? t("need_text_wording") : t("need_text_flag"); textBox.focus(); return; }
      if (k === "wording" && !q) { status.textContent = t("need_quote"); quoteBox.focus(); return; }
      const now = Date.now();
      if (c) mutateOb(ob => queueEdit(ob, c, { kind: k, quote: q, text }, S.code, now));
      else {
        mutateOb(ob => queueCreate(ob, { client_id: randomId(), book: S.book, ch: S.ch, a: p.a, kind: k, quote: q, text }, S.code, now));
        store.del(dKey);
      }
      f.replaceWith(commentForm(art, p, null, null));
      repaintComments();
      flush();
    });
    return f;
  }

  /* The reader's comments in a drawer (art is the paragraph), or at the chapter's end for paragraphs
     that are gone (art is null: no Change button, and each comment names its paragraph). */
  function renderNotes(art, box, list) {
    box.textContent = "";
    if (!list.length) { box.append(h("p", { class: "status", text: t("no_comments") })); return; }
    const p = art && S.chapter && S.chapter.paras.find(x => x.a === art.dataset.a);
    for (const c of list) {
      const recent = c.state === "saved" && Date.now() - (S.saved.get(c.client_id) || 0) < 4000;
      const stateText = c.state === "saving" ? t("st_saving") : c.state === "failed" ? t("st_failed") : recent ? t("st_saved") : "";
      const words = h("div", { class: "note-words", lang: bookLang(S.book) },
        c.quote ? h("p", { class: "note-quote", text: "“" + c.quote + "”" }) : null,
        h("p", { class: "note-text", text: c.text || "" }));
      const all = (c.quote ? "“" + c.quote + "”\n" : "") + (c.text || "");
      const failed = c.state === "failed";
      const edit = () => {
        const f = art.querySelector(".drawer form.note-form");
        if (f) { f.replaceWith(commentForm(art, p, c, null)); art.querySelector(".drawer form.note-form textarea").focus(); }
      };
      const acts = h("span", { class: "note-acts" },
        failed ? h("button", { type: "button", class: "link", text: t("retry"), onclick: () => retryComment(c) })
          : p ? h("button", { type: "button", class: "link", text: t("edit"), onclick: edit }) : null,
        failed || !p ? copyButton(all, words) : null,
        deleteButton(c));
      box.append(h("div", { class: "note " + c.state },
        h("div", { class: "note-top" },
          h("span", { class: "chip " + (c.kind === "wording" ? "mine" : "flag"), text: c.kind === "wording" ? t("kind_wording") : t("kind_flag") }),
          c.processed ? h("span", { class: "chip done", text: t("processed") }) : null,
          stateText ? h("span", { class: "note-state", text: stateText }) : null,
          acts),
        art ? null : h("p", { class: "note-where", text: t("para_n", { a: shortA(c.a) }) }),
        words,
        c.state === "failed" ? h("p", { class: "note-why", text: failNote(c.failure) }) : null));
    }
  }

  function deleteButton(c) {
    return twoTapButton(t("delete"), t("delete_confirm"), () => {
      mutateOb(ob => queueDelete(ob, c, S.code, Date.now()));
      repaintComments();
      flush();
    });
  }

  function retryComment(c) {
    mutateOb(ob => {
      for (const o of ob) if (o.cid === c.client_id && o.failed) { o.failed = null; o.tries = 0; o.next = 0; }
      return ob;
    });
    repaintComments();
    flush();
  }

  /* ---- end of chapter ---- */

  function renderFinish() {
    const c = meChapter();
    const done = !!(c && c.finished);
    const sibs = S.me.chapters.filter(x => x.book === S.book).sort((x, y) => x.n - y.n);
    const i = sibs.findIndex(x => x.id === S.ch);
    const prev = i > 0 ? sibs[i - 1] : null, next = i >= 0 ? sibs[i + 1] : null;
    const pageBtn = (x, cls, label) => h("button", { type: "button", class: "pager-btn " + cls, onclick: () => openChapter(x.book, x.id, { resume: true }) },
      h("span", { class: "page-dir", text: label }), h("span", { class: "page-title", lang: bookLang(x.book), text: x.title_th }));
    return h("section", { class: "finish" + (done ? " is-done" : ""), id: "finish" },
      h("h2", { text: done ? t("finish_done") : t("finish_q") }),
      h("div", { class: "row" },
        h("button", { type: "button", class: done ? "btn ghost" : "btn done", text: done ? t("finish_undo") : t("finish_btn"), onclick: () => setFinished(!done) })),
      h("nav", { class: "pager" },
        prev ? pageBtn(prev, "prev", t("prev")) : null,
        next ? pageBtn(next, "next", t("next")) : null),
      h("button", { type: "button", class: "btn ghost wide", text: t("all_chapters"), onclick: goHome }));
  }

  function setFinished(v) {
    const c = meChapter();
    if (!c) return;
    c.finished = v;
    store.set(K.me, S.me);
    mutateOb(ob => queueSet(ob, "finished", { book: S.book, ch: S.ch, finished: v }, S.code, Date.now(), 0));
    $("finish").replaceWith(renderFinish());
    flush();
  }

  /* ---- the reader's place: recorded only after the reader scrolls, never after a jump ---- */

  let armed = false, jumpedAt = 0, observer = null, placeTimer = 0, pendingPlace = null;
  function markJump() { jumpedAt = Date.now(); armed = false; }

  function startTracking() {
    stopTracking();
    if (!("IntersectionObserver" in window)) return;
    observer = new IntersectionObserver(entries => {
      for (const e of entries) {
        if (!e.isIntersecting || !armed || S.view !== "chapter") continue;
        const a = e.target.dataset.a;
        $("bar-place").textContent = shortA(a);
        pendingPlace = { book: S.book, ch: S.ch, a };
        clearTimeout(placeTimer);
        placeTimer = setTimeout(savePlace, 2500);
      }
    }, { rootMargin: "-25% 0px -65% 0px" });
    for (const p of document.querySelectorAll("#main .para")) observer.observe(p);
  }

  function stopTracking() {
    if (observer) observer.disconnect();
    observer = null;
    savePlace();
  }

  function savePlace() {
    clearTimeout(placeTimer);
    const p = pendingPlace;
    pendingPlace = null;
    if (!p || !S.me) return;
    const c = S.me.chapters.find(x => x.book === p.book && x.id === p.ch);
    if (!c || c.place === p.a) return;
    c.place = p.a;
    store.set(K.me, S.me);
    mutateOb(ob => queueSet(ob, "place", { book: p.book, ch: p.ch, a: p.a }, S.code, Date.now(), PLACE_DELAY_MS));
    schedule(0);
  }

  /* The page is being hidden: send the place now rather than after the usual wait. */
  function sendPlaceNow() {
    savePlace();
    mutateOb(ob => { for (const o of ob) if (o.type === "place" && !o.tries) o.next = 0; return ob; });
    flush();
  }

  /* ---- start ---- */

  function onStorage(ev) {
    if (!ev.key) return;
    if (ev.key === K.code && store.get(K.code) !== S.code) { location.reload(); return; }
    if (ev.key === K.outbox || ev.key.startsWith("rv.cm:")) { repaintComments(); paintSync(); }
    if (ev.key === K.me && S.view === "home") {
      const me = store.get(K.me);
      if (me) { S.me = me; renderHome(false); }
    }
  }

  function wireEvents() {
    $("back").addEventListener("click", goHome);
    window.addEventListener("popstate", route);
    window.addEventListener("scroll", () => { if (Date.now() - jumpedAt > 800) armed = true; }, { passive: true });
    window.addEventListener("online", () => {
      netFails = 0;
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
    window.addEventListener("error", ev => { if (ev.filename && /app\.js/.test(ev.filename)) showNotice(t("error_generic")); });
  }

  function registerWorker() {
    // The service worker keeps the page's own files on the device; it needs https.
    if (!("serviceWorker" in navigator) || location.protocol !== "https:") return;
    navigator.serviceWorker.register("sw.js").catch(() => { /* the page works without it */ });
  }

  function start() {
    applyLang();
    registerWorker();
    if (!S.code) return showLink();
    S.me = store.get(K.me);
    if (S.me && Array.isArray(S.me.chapters)) S.me = applyPending(S.me, loadOb(), S.code);
    else S.me = null;
    route();
    refreshMe();
    flush();
  }

  function boot() {
    lang = store.get(K.lang) === "en" ? "en" : "th";
    // The link is https://<host>/#k=<code>. The fragment never reaches the server; it is kept here
    // and taken out of the address bar.
    // Codes hold only A-Z, a-z, 0-9, _ and -, so a full stop or bracket after the link is left out.
    const m = /^#(?:.*&)?k=([A-Za-z0-9_-]+)/.exec(location.hash);
    if (m) {
      let code = m[1];
      try { code = decodeURIComponent(code); } catch (e) { /* keep it as it is */ }
      if (code !== store.get(K.code)) forgetReader();
      store.set(K.code, code);
      setHash("", false);
    }
    S.code = store.get(K.code);
    STR = store.get(K.strings) || {};
    wireEvents();
    // Ask for the chapter list at the same time as the words, so a first visit waits for one fetch at most.
    if (S.code) firstMe = api("GET", "api/me");
    const fresh = loadStrings();
    if (Object.keys(STR).length) {
      start();
      fresh.then(changed => { if (changed) rerender(); });
    } else {
      fresh.then(start);
    }
  }

  boot();
})();

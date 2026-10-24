/* Checks of the page's plain modules in web/core/ (the outbox, the server's answers, the refusals, the
   feature places, what changed since the reader last opened a chapter, the words, the rules of signing in, and
   the quoted words, picked words and sentence steps of quotes.js), of web/core/net.js with a stand-in for fetch,
   and of the entries of web/features/sentences.js, run by test_core.py with node. Prints "ok" and exits 0 when
   every check passes. */
"use strict";
const assert = require("assert");
const path = require("path");
const { pathToFileURL } = require("url");

const load = name => import(pathToFileURL(path.join(__dirname, "..", "web", "core", name)).href);

(async () => {
  const core = await load("outbox.js");
  const model = await load("model.js");
  const ref = await load("refusals.js");
  const ext = await load("ext.js");
  const store = await load("store.js");
  const changes = await load("changes.js");

  // The reader whose ops these are: the outbox keys each op by the reader's fixed number (README.md, "Link signs in").
  const code = 7;
  const c = { client_id: "c1", book: "SC", ch: "SC03", a: "SC 23.3", kind: "flag", quote: "", text: "words" };

  // A comment the server refuses for good stays in the outbox as failed, with the server's error code.
  let ob = core.queueCreate([], c, code, 0);
  const op = ob[0].op;
  ob = core.settle(ob, op, 0, core.classify("create", 404), { error: "no_chapter", message: "x" }, 404, 1);
  assert.deepStrictEqual(ob[0].failed, { status: 404, error: "no_chapter", message: "x" });
  assert.strictEqual(core.pickNext(ob, 2), null);

  // The chapter view shows it as failed and carries the reason, so the page can explain it.
  const shown = core.overlay([], ob, "SC", "SC03", code);
  assert.strictEqual(shown.length, 1);
  assert.strictEqual(shown[0].state, "failed");
  assert.strictEqual(shown[0].failure.error, "no_chapter");

  // A 409 for a paragraph that is gone is final; so was the old 400 bad_anchor. A 503 is tried again later.
  for (const [status, error] of [[409, "no_paragraph"], [400, "bad_anchor"]]) {
    let o2 = core.queueCreate([], c, code, 0);
    o2 = core.settle(o2, o2[0].op, 0, core.classify("create", status), { error }, status, 1);
    assert.strictEqual(o2[0].failed.error, error);
    assert.strictEqual(ref.explain(o2[0].failed).key, "failed_paragraph");
  }
  let ob3 = core.queueCreate([], c, code, 0);
  ob3 = core.settle(ob3, ob3[0].op, 0, core.classify("create", 503), null, 503, 1);
  assert.strictEqual(ob3[0].failed, null);
  assert.strictEqual(ob3[0].tries, 1);

  // Deleting a refused comment that never reached the server just drops it.
  assert.deepStrictEqual(core.queueDelete(ob, Object.assign({}, c, { id: null }), code, 5), []);

  // Every refusal code of the server has its own message; each says which buttons help.
  const limits = { quote: 500, text: 4000, comments: 5000, writes_per_minute: 60 };
  const why = (status, error) => ref.explain({ status, error: error || "", message: "" }, limits);
  const cases = [
    [404, "no_chapter", "failed_closed", {}, true, false],
    [409, "no_paragraph", "failed_paragraph", {}, false, false],
    [400, "quote_required", "failed_quote_required", {}, false, true],
    [400, "quote_too_long", "failed_quote_long", { n: 500 }, false, true],
    [400, "text_required", "failed_text_required", {}, false, true],
    [400, "text_too_long", "failed_text_long", { n: 4000 }, false, true],
    [413, "too_large", "failed_text_long", { n: 4000 }, false, true],
    [413, "", "failed_text_long", { n: 4000 }, false, true],      // Apache's own HTML answer
    [403, "comment_limit", "failed_limit", { n: 5000 }, true, false],
    [404, "no_comment", "failed_deleted", {}, false, false],
    [404, "", "failed_closed", {}, true, false],                   // a 404 without a code
    [400, "bad_json", "failed_refused", {}, true, false],
    [400, "bad_kind", "failed_refused", {}, true, false],
    [400, "bad_field", "failed_refused", {}, true, false],
    [403, "", "failed_refused", {}, true, false],
  ];
  for (const [status, error, key, vars, retry, change] of cases) {
    assert.deepStrictEqual(why(status, error), { key, vars, retry, change }, status + " " + error);
  }
  // The limit in a message is the server's, from /api/me.
  assert.deepStrictEqual(ref.explain({ status: 400, error: "quote_too_long" }, { quote: 120 }).vars, { n: 120 });
  assert.strictEqual(ref.explain(null).key, "failed_refused");

  // slow_down is never final: the op waits at least as long as Retry-After and shows why it waits.
  let ob4 = core.queueCreate([], c, code, 0);
  ob4 = core.settle(ob4, ob4[0].op, 0, core.classify("create", 429), { error: "slow_down" }, 429, 1000, 37000);
  assert.strictEqual(ob4[0].failed, null);
  assert.ok(ob4[0].next >= 38000, "waits for Retry-After");
  assert.strictEqual(ob4[0].why, "slow_down");
  assert.strictEqual(core.pickNext(ob4, 30000), null);
  assert.strictEqual(core.overlay([], ob4, "SC", "SC03", code)[0].why, "slow_down");
  assert.strictEqual(ref.waitNote("slow_down"), "wait_slow");
  assert.strictEqual(ref.waitNote(""), "");
  // A 429 from Apache without a body is the same.
  let ob5 = core.queueCreate([], c, code, 0);
  ob5 = core.settle(ob5, ob5[0].op, 0, "retry", null, 429, 0, 0);
  assert.strictEqual(ob5[0].why, "slow_down");

  // A refused comment that the reader changes goes out again from the start.
  let ob6 = core.queueCreate([], c, code, 0);
  ob6 = core.settle(ob6, ob6[0].op, 0, "fail", { error: "text_too_long" }, 400, 1);
  ob6 = core.queueEdit(ob6, c, { kind: "flag", quote: "", text: "shorter" }, code, 2);
  assert.strictEqual(ob6[0].failed, null);
  assert.strictEqual(ob6[0].body.text, "shorter");
  assert.strictEqual(core.pickNext(ob6, 3), ob6[0]);
  // Try again clears the refusal of every op of the comment.
  ob6 = core.settle(ob6, ob6[0].op, 1, "fail", { error: "comment_limit" }, 403, 4);
  assert.ok(ob6[0].failed);
  assert.strictEqual(core.queueRetry(ob6, "c1")[0].failed, null);

  // Save checks the comment first and names the box to fix.
  const check = (kind, quote, text) => ref.checkComment({ kind, quote, text }, limits);
  assert.deepStrictEqual(check("flag", "", "", true, 0), { key: "need_text_flag", vars: {}, field: "text" });
  assert.strictEqual(check("wording", "", "x", true, 0).key, "need_quote");
  assert.strictEqual(check("flag", "", "\u200b\ufeff", true, 0).key, "need_text_flag");   // only invisible characters
  assert.deepStrictEqual(check("flag", "q".repeat(501), "x", true, 0), { key: "long_quote", vars: { n: 500 }, field: "quote" });
  assert.strictEqual(check("flag", "q".repeat(500), "x", true, 0), null);
  assert.deepStrictEqual(check("flag", "", "ก".repeat(4001), true, 0), { key: "long_text", vars: { n: 4000 }, field: "text" });
  assert.strictEqual(check("flag", "", "ก".repeat(4000), true, 0), null);
  assert.strictEqual(check("flag", "", "😀".repeat(4000), true, 0), null);   // characters, not UTF-16 units
  // There is no limit on the comments a reader keeps: Save never counts them (the lifetime limit is gone).
  assert.strictEqual(ref.checkComment({ kind: "flag", quote: "", text: "x" }, { comments: 1 }, true, 5000), null);
  assert.strictEqual(ref.counter("x".repeat(399), 500), null);
  assert.deepStrictEqual(ref.counter("x".repeat(400), 500), { n: 400, max: 500, over: false });
  assert.deepStrictEqual(ref.counter("x".repeat(501), 500), { n: 501, max: 500, over: true });

  // normMe keeps each book's language, the features, the limits and the reader's comment total.
  const me = model.normMe({ name: "R", books: [{ id: "GC", title_en: "G", language: "lo" }], chapters: [],
    features: { english: { on: true }, later: { on: false } }, limits: { quote: 100, text: 2000, comments: 9, writes_per_minute: 5 },
    comments_total: 4 });
  assert.deepStrictEqual(me.langs, { GC: "lo" });
  assert.deepStrictEqual(me.features, { english: { on: true }, later: { on: false } });
  // The retired lifetime limit `comments` is not kept; devices_per_link is.
  assert.deepStrictEqual(me.limits, { quote: 100, text: 2000, comments_per_minute: 10, comments_per_day: 1000, writes_per_minute: 5, devices_per_link: 2 });
  // The page's own limits are the ruled defaults until /api/me carries the server's.
  assert.deepStrictEqual(model.DEFAULT_LIMITS, { quote: 4000, text: 8000, comments_per_minute: 10, comments_per_day: 1000, writes_per_minute: 60, devices_per_link: 2 });
  assert.deepStrictEqual(model.normMe({ chapters: [], limits: { comments_per_day: 3, comments_per_minute: 0 } }).limits,
    Object.assign({}, model.DEFAULT_LIMITS, { comments_per_day: 3 }));
  assert.strictEqual(me.total, 4);
  // A book without a language has none; a language code that is not one is left out.
  assert.deepStrictEqual(model.normMe({ books: [{ id: "SC" }, { id: "X", language: "th) {}" }], chapters: [] }).langs, {});
  // An answer without features (an older server) has only english; without limits, the defaults.
  const old = model.normMe({ name: "R", english: true, chapters: [] });
  assert.deepStrictEqual(old.features, { english: { on: true } });
  assert.deepStrictEqual(old.limits, model.DEFAULT_LIMITS);
  assert.strictEqual(old.total, null);
  // A chapter list saved by the older page is brought up to date.
  const kept = model.upgradeMe({ name: "R", english: true, books: {}, langs: { SC: "th" }, chapters: [] });
  assert.deepStrictEqual(kept.features, { english: { on: true } });
  assert.strictEqual(model.upgradeMe({ name: "R" }), null);
  // The server's own shapes: a book's heading is its title in its own language, else its English title.
  const two = model.normMe({ name: "R", books: [{ id: "SC", title_en: "Steps", title_th: "", language: "th" },
    { id: "GC", title_en: "Controversy", title_th: "T", language: "th" }],
    chapters: [{ book: "SC", id: "SC01", n: 1, title_th: "a", title_en: "b", version: "v", paragraphs: 17, comments: 2,
      finished: true, finished_at: "x", place: "SC 9.1" }] });
  assert.deepStrictEqual(two.books, { SC: "Steps", GC: "T" });
  assert.deepStrictEqual(two.chapters[0], { book: "SC", id: "SC01", n: 1, title: "a", title_en: "b", version: "v",
    count: 17, comments: 2, finished: true, place: "SC 9.1", opened: null, changed: null });
  // opened and changed pass through; a change with nothing in it is no change.
  const changedMe = model.normMe({ chapters: [{ book: "SC", id: "SC01", version: "v2", opened: "v1",
    changed: { since: "v1", since_at: "t1", at: "t2", paragraphs: [{ a: "SC 9.1", at: "t2", new: false }, { a: "SC 9.4", at: "t2", new: true }, { x: 1 }],
      removed: [{ a: "SC 9.9", at: "t2" }] } }, { book: "SC", id: "SC02", version: "v", opened: "v", changed: { since: "v", paragraphs: [], removed: [] } }] });
  assert.deepStrictEqual(changedMe.chapters[0].changed, { since: "v1", since_at: "t1", at: "t2",
    paragraphs: [{ a: "SC 9.1", at: "t2", new: false }, { a: "SC 9.4", at: "t2", new: true }], removed: [{ a: "SC 9.9", at: "t2" }] });
  assert.strictEqual(changedMe.chapters[0].opened, "v1");
  assert.strictEqual(changedMe.chapters[1].changed, null);
  // A chapter list kept by the page before this round gains opened and changed.
  const keptOld = model.upgradeMe({ name: "R", features: {}, books: {}, langs: {}, chapters: [{ book: "SC", id: "SC01", version: "v" }] });
  assert.strictEqual(keptOld.chapters[0].opened, null);
  assert.strictEqual(keptOld.chapters[0].changed, null);
  // A chapter from a server before round 3b (title_th, th) takes the neutral names of the page's shape.
  assert.deepStrictEqual(model.normChapter({ book: "SC", id: "SC01", n: 1, title_th: "t", title_en: "e", version: "v",
    paragraphs: [{ a: "SC 9.1", th: "x" }] }).paras, [{ a: "SC 9.1", text: "x", fn: [], en: "" }]);
  assert.strictEqual(model.normChapter({ title_th: "t", paragraphs: [] }).title, "t");
  // A chapter keeps when its version was published, its language, and each paragraph's sentence pairs of the right shape.
  const withPairs = model.normChapter({ book: "SC", id: "SC01", version: "v", language: "th", title: "T", at: "2026-10-22T16:45:24Z", paragraphs: [
    { a: "SC 9.1", text: "x", en: "e", al: [{ text: [0, 11], en: [[0, 9]] }, { text: [5, 2], en: [[0, 1]] }, { text: [11, 20], en: [] }, "bad"] },
    { a: "SC 9.2", text: "y", al: "nonsense" }] });
  assert.strictEqual(withPairs.at, "2026-10-22T16:45:24Z");
  assert.strictEqual(withPairs.title, "T");
  assert.strictEqual(withPairs.language, "th");
  assert.deepStrictEqual(withPairs.paras[0].al, [{ text: [0, 11], en: [[0, 9]] }]);
  assert.strictEqual("al" in withPairs.paras[1], false);
  // A pair from a server before round 3b names its range th.
  assert.deepStrictEqual(model.normPairs([{ th: [2, 5], en: [[0, 3]] }]), [{ text: [2, 5], en: [[0, 3]] }]);

  // The version of a chapter the reader opened goes out through the outbox as PUT /api/opened; a newer one
  // replaces one still waiting, a refused one is dropped, and one still waiting leaves nothing shown as changed.
  let obo = core.queueSet([], "opened", { book: "SC", ch: "SC01", version: "v1" }, code, 0, 0);
  obo = core.queueSet(obo, "opened", { book: "SC", ch: "SC01", version: "v2" }, code, 1, 0);
  assert.strictEqual(obo.length, 1);
  assert.deepStrictEqual(core.requestFor(obo[0]), ["PUT", "api/opened", { book: "SC", ch: "SC01", version: "v2" }]);
  const meOpened = { chapters: [{ book: "SC", id: "SC01", version: "v2", opened: "v1", changed: { since: "v1", paragraphs: [{ a: "SC 9.1" }], removed: [] } },
    { book: "SC", id: "SC02", version: "w", opened: null, changed: null }] };
  core.applyPending(meOpened, obo, code);
  assert.strictEqual(meOpened.chapters[0].opened, "v2");
  assert.strictEqual(meOpened.chapters[0].changed, null);
  assert.deepStrictEqual(core.settle(obo, obo[0].op, obo[0].rev, core.classify("opened", 404), { error: "no_chapter" }, 404, 2), []);
  assert.strictEqual(core.settle(obo, obo[0].op, obo[0].rev, core.classify("opened", 200), {}, 200, 2).length, 0);

  // The daily limit is never final: the comment waits on the device, says why, and goes by itself.
  let obd = core.queueCreate([], c, code, 0);
  obd = core.settle(obd, obd[0].op, 0, core.classify("create", 429), { error: "daily_limit", limit: 1000, retry_at: "x" }, 429, 1000, 86400000);
  assert.strictEqual(obd[0].failed, null);
  assert.strictEqual(obd[0].why, "daily_limit");
  assert.ok(obd[0].next >= 86401000, "waits a day");
  assert.strictEqual(core.overlay([], obd, "SC", "SC03", code)[0].why, "daily_limit");
  assert.strictEqual(ref.waitNote("daily_limit"), "wait_daily");

  // What changed since the reader last opened a chapter: the device's record, the marks, and when to send.
  const meCh = { version: "v2", opened: "v1", changed: { since: "v1", at: "t3", paragraphs: [
    { a: "SC 9.1", at: "t2", new: false }, { a: "SC 9.4", at: "t3", new: true }], removed: [{ a: "SC 9.9", at: "t2" }] } };
  let rec = changes.syncRecord(null, meCh);
  assert.deepStrictEqual(rec, { since: "v1", version: "v2", at: "t3", paras: [{ a: "SC 9.1", at: "t2", new: false }, { a: "SC 9.4", at: "t3", new: true }],
    removed: 1, opened: {}, done: false });
  assert.strictEqual(changes.syncRecord(rec, meCh), rec);                       // nothing new: the same record
  assert.deepStrictEqual(changes.marksOf(rec, "v2"), { "SC 9.1": "changed", "SC 9.4": "new" });
  assert.deepStrictEqual(changes.marksOf(rec, "v1"), {});                       // a chapter drawn at another version
  assert.strictEqual(changes.openedToSend(meCh, rec, "v2"), "");               // marks are left
  rec = changes.openPara(rec, "SC 9.1");
  assert.deepStrictEqual(changes.marksOf(rec, "v2"), { "SC 9.4": "new" });
  assert.strictEqual(changes.openPara(rec, "SC 9.2"), rec);                    // not marked: nothing to clear
  assert.strictEqual(changes.allOpened(rec), false);
  rec = changes.openPara(rec, "SC 9.4");
  assert.strictEqual(changes.allOpened(rec), true);
  assert.strictEqual(changes.openedToSend(meCh, rec, "v2"), "send");           // every mark opened: send v2
  assert.strictEqual(changes.openedToSend(meCh, rec, "v1"), "");               // never for a chapter drawn at another version
  assert.deepStrictEqual(changes.changeOf(rec, "SC 9.1"), { a: "SC 9.1", at: "t2", new: false });
  // A later change of the same paragraph marks it again; a paragraph whose change is the same stays opened.
  const meCh3 = { version: "v3", opened: "v1", changed: { since: "v1", at: "t4", paragraphs: [
    { a: "SC 9.1", at: "t4", new: false }, { a: "SC 9.4", at: "t3", new: true }], removed: [] } };
  const rec3 = changes.syncRecord(rec, meCh3);
  assert.deepStrictEqual(changes.marksOf(rec3, "v3"), { "SC 9.1": "changed" });
  // Once the server has nothing to show, the record stays, done, for the earlier wording; no marks.
  const recDone = changes.syncRecord(rec3, { version: "v3", opened: "v3", changed: null });
  assert.strictEqual(recDone.done, true);
  assert.strictEqual(recDone.since, "v1");
  assert.deepStrictEqual(changes.marksOf(recDone, "v3"), {});
  assert.strictEqual(changes.syncRecord(null, { version: "v", opened: "v", changed: null }), null);
  // Nothing marked: send the version at once when the server does not hold it as opened yet.
  assert.strictEqual(changes.openedToSend({ version: "v", opened: null, changed: null }, null, "v"), "send");
  assert.strictEqual(changes.openedToSend({ version: "v", opened: "v", changed: null }, null, "v"), "");
  // Only paragraphs taken out: nothing to mark, so the version goes at once.
  const meGone = { version: "v2", opened: "v1", changed: { since: "v1", at: "t", paragraphs: [], removed: [{ a: "SC 9.9", at: "t" }] } };
  assert.strictEqual(changes.openedToSend(meGone, changes.syncRecord(null, meGone), "v2"), "send");

  // Numbers in messages are written with commas; a date takes the words of the keys date and months.
  const words = await load("words.js");
  const st = await load("state.js");
  assert.strictEqual(words.groupDigits(1000), "1,000");
  assert.strictEqual(words.groupDigits(8000), "8,000");
  assert.strictEqual(words.groupDigits(500), "500");
  st.store.set("rv.strings", { wait_daily: { en: "limit of {n} comments", th: "" }, date: { en: "{d} {month} {y}", th: "{d} {month} {be}" },
    months: { en: "January,February,March,April,May,June,July,August,September,October,November,December", th: "" } });
  words.useKeptWords();
  st.S.lang = "en";
  assert.strictEqual(words.t("wait_daily", { n: 1000 }), "limit of 1,000 comments");
  assert.strictEqual(words.dateText("2026-10-22T12:00:00Z"), "22 October 2026");
  st.S.lang = "th";
  assert.strictEqual(words.t("wait_daily", { n: 1000 }), "limit of 1,000 comments");   // an empty Thai shows the English
  assert.strictEqual(words.dateText("2026-10-22T12:00:00Z"), "22 October 2569");
  assert.strictEqual(words.dateText("not a time"), "");

  // A draft's key names its link's tag, book, chapter and paragraph; a page before round 3b wrote no tag.
  const tagA = store.linkTag("code-of-link-A"), tagB = store.linkTag("code-of-link-B");
  assert.match(tagA, /^[0-9a-f]{8}$/);
  assert.strictEqual(store.linkTag("code-of-link-A"), tagA);
  assert.notStrictEqual(tagA, tagB);
  assert.deepStrictEqual(store.parseDraftKey(store.draftKey(tagA, "SC", "SC03", "SC 35.4")), { tag: tagA, book: "SC", ch: "SC03", a: "SC 35.4" });
  assert.deepStrictEqual(store.parseDraftKey("rv.draft:SC/SC03/SC 35.4"), { tag: "", book: "SC", ch: "SC03", a: "SC 35.4" });
  assert.strictEqual(store.parseDraftKey("rv.cm:SC/SC03"), null);
  // Drafts move to the link open now from the reader's other links, never over a draft already there, and
  // never from another reader's link.
  const dk = (tag, a) => store.draftKey(tag, "SC", "SC03", a);
  const tagC = store.linkTag("code-of-another-reader");
  const moves = store.draftMoves([dk(tagA, "SC 1.1"), dk(tagA, "SC 1.2"), dk(tagB, "SC 1.2"), dk(tagC, "SC 1.3"), "rv.me"], tagB, t => t === tagA);
  assert.deepStrictEqual(moves, [[dk(tagA, "SC 1.1"), dk(tagB, "SC 1.1")]]);
  assert.deepStrictEqual(store.draftMoves(["rv.draft:SC/SC03/SC 1.1"], tagA, t => t === ""), [["rv.draft:SC/SC03/SC 1.1", dk(tagA, "SC 1.1")]]);
  // A draft is kept per reader, under R and the reader's fixed number; in link mode before the device knows the link's
  // number, under the link's tag, from which it moves to the reader's.
  assert.strictEqual(store.ownerTag(7), "R7");
  assert.strictEqual(store.ownerTag("link:code-of-link-A"), tagA);
  assert.strictEqual(store.ownerTag(null), "");
  assert.deepStrictEqual(store.parseDraftKey(dk("R12", "SC 1.1")), { tag: "R12", book: "SC", ch: "SC03", a: "SC 1.1" });
  assert.deepStrictEqual(store.draftMoves([dk(tagA, "SC 1.1"), dk("R7", "SC 1.2"), dk(tagC, "SC 1.3")], "R7", t => t === tagA),
    [[dk(tagA, "SC 1.1"), dk("R7", "SC 1.1")]]);
  // A browser that refuses storage outright is named, so the page shows the plain screen for it.
  assert.strictEqual(store.makeStore({ setItem() { throw new Error("SecurityError"); } }).blocked, true);
  assert.strictEqual(store.makeStore(null).blocked, true);
  const okStore = new Map();
  assert.strictEqual(store.makeStore({ setItem: (k, v) => okStore.set(k, v), removeItem: k => okStore.delete(k), getItem: k => okStore.get(k) }).blocked, false);

  // ---- One person per link: the device key and the wait for the translator's approval ----
  // 403 device_waiting keeps the op as it is and stops the sending; any other 403 refuses it as before.
  assert.strictEqual(core.classify("create", 403, "device_waiting"), "device");
  assert.strictEqual(core.classify("place", 403, "device_waiting"), "device");
  assert.strictEqual(core.classify("create", 403, ""), "fail");
  let obw = core.queueCreate([], c, code, 0);
  obw = core.settle(obw, obw[0].op, 0, "device", { error: "device_waiting" }, 403, 1);
  assert.strictEqual(obw.length, 1);
  assert.strictEqual(obw[0].failed, null);
  assert.strictEqual(obw[0].tries, 0);
  let obp = core.queueSet([], "place", { book: "SC", ch: "SC03", a: "SC 23.3" }, code, 0, 0);
  obp = core.settle(obp, obp[0].op, 0, "device", { error: "device_waiting" }, 403, 1);
  assert.strictEqual(obp.length, 1, "a place waits too");

  // ---- Each reader's ops are kept apart: only the reader signed in now sends ----
  const other = 8;
  let obl = core.queueCreate([], Object.assign({}, c, { client_id: "x1" }), other, 0);
  obl = core.queueCreate(obl, Object.assign({}, c, { client_id: "x2" }), code, 0);
  obl = core.queueSet(obl, "place", { book: "SC", ch: "SC03", a: "SC 23.3" }, other, 0, 0);
  obl = core.queueSet(obl, "place", { book: "SC", ch: "SC03", a: "SC 23.4" }, code, 0, 0);
  assert.strictEqual(obl.length, 4, "two readers' places of one chapter stay apart");
  assert.strictEqual(core.pickNext(obl, 1, code).cid, "x2");
  assert.strictEqual(core.pickNext(obl, 1, other).cid, "x1");
  assert.strictEqual(core.pickNext(obl, 1).cid, "x1");                 // no reader given: any op, as before
  const afterX2 = obl.filter(o => o.cid !== "x2");
  assert.strictEqual(core.pickNext(afterX2, 1, code).body.a, "SC 23.4");  // another reader's place does not block this one
  assert.strictEqual(core.nextWake(obl.filter(o => core.ownerOf(o) === other), 1, code), Infinity);
  assert.deepStrictEqual(core.overlay([], obl, "SC", "SC03", code).map(x => x.client_id), ["x2"]);
  assert.deepStrictEqual(obl.map(o => o.reader), [8, 7, 8, 7], "each op names its reader's number");
  // flushOnce sends only io.who's ops.
  const sent = [];
  let box = obl.map(o => Object.assign({}, o));
  const io2 = { load: () => box, save: x => { box = x; }, now: () => 5, who: code,
    send: async (m, pth) => { sent.push([m, pth]); return { status: 201, data: { id: 9, client_id: "x2", kind: "flag", quote: "", text: "words" } }; } };
  await core.flushOnce(io2);
  assert.deepStrictEqual(sent, [["POST", "api/comments"]]);
  assert.deepStrictEqual(box.map(o => o.cid || o.key), ["x1", "place:SC/SC03", "place:SC/SC03"]);
  // An op of a page of round 3b names its link in `code`, and so does one written in link mode before the device
  // knew the link's number ("link:" and the code). Once the device knows the number of the link, the op becomes
  // that reader's; the op of a link the device never tied to a number stays as it is.
  const legacy = (cid, link) => ({ op: "o-" + cid, type: "create", code: link, cid, book: "SC", ch: "SC03", a: "SC 23.3",
    body: { client_id: cid, book: "SC", ch: "SC03", a: "SC 23.3", kind: "flag", quote: "", text: "words" },
    t: 0, rev: 0, tries: 0, sent: 0, next: 0, sending: 0, failed: null, why: "" });
  let oba = [legacy("y1", "old-link"), legacy("y2", "someone-else"), legacy("y3", "old-link"), legacy("y4", "never-known")];
  oba = core.queueCreate(oba, Object.assign({}, c, { client_id: "y5" }), "link:new-link", 0);
  assert.deepStrictEqual(oba.map(core.ownerOf), ["link:old-link", "link:someone-else", "link:old-link", "link:never-known", "link:new-link"]);
  assert.strictEqual(core.pickNext(oba, 1, "link:new-link").cid, "y5", "an op of a link whose number is not known yet goes in link mode");
  oba[2].sending = 10;   // being sent by another tab: left alone
  const numbers = { "old-link": 7, "new-link": 7, "someone-else": 8 };
  assert.strictEqual(core.renumber(oba, cd => numbers[cd], 11), 3);
  assert.deepStrictEqual(oba.map(core.ownerOf), [7, 8, "link:old-link", "link:never-known", 7]);
  assert.ok(!("code" in oba[0]), "a numbered op keeps no link code");
  assert.deepStrictEqual(core.overlay([], oba, "SC", "SC03", 7).map(x => x.client_id), ["y1", "y5"]);

  // ---- The daily limit: how long until it resets, in hours and minutes ----
  let obt = core.queueCreate([], c, code, 0);
  obt = core.settle(obt, obt[0].op, 0, "retry", { error: "daily_limit" }, 429, 1000, 5 * 3600000 + 12 * 60000);
  const held = core.overlay([], obt, "SC", "SC03", code)[0];
  assert.strictEqual(held.why, "daily_limit");
  assert.ok(held.until >= 1000 + 5 * 3600000 + 12 * 60000);
  assert.deepStrictEqual(ref.untilReset(1000 + 5 * 3600000 + 12 * 60000, 1000), { h: 5, m: 12 });
  assert.deepStrictEqual(ref.untilReset(90001, 0), { h: 0, m: 2 });       // rounded up: never "0 minutes"
  assert.deepStrictEqual(ref.untilReset(3600000, 0), { h: 1, m: 0 });
  assert.strictEqual(ref.untilReset(5, 10), null);
  assert.strictEqual(ref.untilReset(0, 10), null);
  assert.strictEqual(core.overlay([], core.queueCreate([], c, code, 0), "SC", "SC03", code)[0].until, 0);
  st.S.lang = "en";
  st.store.set("rv.strings", { hours_one: { en: "{n} hour", th: "" }, hours_many: { en: "{n} hours", th: "" },
    minutes_one: { en: "{n} minute", th: "" }, minutes_many: { en: "{n} minutes", th: "" } });
  words.useKeptWords();
  assert.strictEqual(words.durationText({ h: 5, m: 12 }), "5 hours 12 minutes");
  assert.strictEqual(words.durationText({ h: 1, m: 1 }), "1 hour 1 minute");
  assert.strictEqual(words.durationText({ h: 0, m: 40 }), "40 minutes");
  assert.strictEqual(words.durationText({ h: 2, m: 0 }), "2 hours");
  assert.strictEqual(words.durationText(null), "");

  // ---- The reader number, rounds and earlier comments in /api/me ----
  const me3 = model.normMe({ id: 7, name: "Anan", books: [{ id: "SC", title: "", title_en: "Steps", language: "th",
    round: { name: "first", started: "2026-10-22T18:56:15Z" }, earlier: 3 }, { id: "GC", title: "G", round: null, earlier: 0 }],
    chapters: [{ book: "SC", id: "SC01", n: 1, title: "ชื่อ", title_en: "Name", version: "v" }] });
  assert.strictEqual(me3.id, 7);
  assert.deepStrictEqual(me3.rounds, { SC: { name: "first", started: "2026-10-22T18:56:15Z" }, GC: null });
  assert.deepStrictEqual(me3.earlier, { SC: 3, GC: 0 });
  assert.deepStrictEqual(me3.books, { SC: "Steps", GC: "G" });
  assert.strictEqual(me3.chapters[0].title, "ชื่อ");
  assert.strictEqual(model.normMe({ id: "7", chapters: [] }).id, null);
  // A chapter list kept by a page before round 3b: title_th becomes title, and the number and rounds are unknown.
  const kept3 = model.upgradeMe({ name: "R", chapters: [{ book: "SC", id: "SC01", title_th: "เก่า", version: "v" }] });
  assert.strictEqual(kept3.chapters[0].title, "เก่า");
  assert.strictEqual(kept3.id, null);
  assert.strictEqual(kept3.rounds, undefined);
  assert.deepStrictEqual(kept3.earlier, {});
  // A chapter kept on the device by a page before round 3b is brought to the new shape, once.
  const oldKept = { book: "SC", id: "SC01", n: 1, title_th: "เก่า", title_en: "Old", version: "v",
    paras: [{ a: "SC 9.1", th: "ข้อความ", fn: [], en: "e", al: [{ th: [0, 3], en: [[0, 1]] }] }] };
  const up = model.upgradeChapter(oldKept);
  assert.strictEqual(up.title, "เก่า");
  assert.deepStrictEqual(up.paras[0], { a: "SC 9.1", text: "ข้อความ", fn: [], en: "e", al: [{ text: [0, 3], en: [[0, 1]] }] });
  const again = up.paras;
  assert.strictEqual(model.upgradeChapter(up).paras, again, "a chapter in the new shape stays as it is");

  // The refusals of round 3b: a comment of an earlier round cannot be changed; an older server's lifetime limit.
  assert.deepStrictEqual(ref.explain({ status: 409, error: "round_closed" }, {}), { key: "failed_round", vars: {}, retry: false, change: false });
  assert.deepStrictEqual(ref.explain({ status: 403, error: "comment_limit" }, model.DEFAULT_LIMITS).vars, { n: 5000 });
  assert.strictEqual(core.classify("update", 409), "fail");
  let obr = core.queueEdit([], Object.assign({}, c, { id: 4 }), { kind: "flag", quote: "", text: "new words" }, code, 0);
  obr = core.settle(obr, obr[0].op, 0, "fail", { error: "round_closed", message: "x" }, 409, 1);
  assert.strictEqual(obr[0].failed.error, "round_closed", "an edit refused for its round keeps the reader's words");
  // A delete the site refuses stays, with the comment's words, and says that the comment was not deleted and the
  // translator still receives it; only no_comment means the comment is already gone.
  let obrd = core.queueDelete([], Object.assign({}, c, { id: 4 }), code, 0);
  assert.deepStrictEqual(obrd[0].body, { kind: "flag", quote: "", text: "words" });
  assert.strictEqual(core.requestFor(obrd[0])[2], undefined, "a delete sends no body");
  obrd = core.settle(obrd, obrd[0].op, 0, core.classify("delete", 409, "round_closed"), { error: "round_closed", message: "x" }, 409, 1);
  assert.deepStrictEqual(obrd[0].failed, { status: 409, error: "round_closed", message: "x", type: "delete" });
  assert.strictEqual(ref.explain(obrd[0].failed, {}).key, "failed_delete_round");
  const keptCard = core.overlay([Object.assign({}, c, { id: 4 })], obrd, "SC", "SC03", code);
  assert.deepStrictEqual(keptCard.map(x => [x.client_id, x.state, x.failure.type]), [["c1", "failed", "delete"]]);
  assert.deepStrictEqual(core.overlay([], obrd, "SC", "SC03", code), [], "a refused delete adds no comment the list lacks");
  assert.strictEqual(core.classify("delete", 404, "no_comment"), "ok");
  assert.strictEqual(core.classify("delete", 404, "no_chapter"), "fail");
  assert.strictEqual(core.classify("delete", 404, ""), "fail");
  assert.deepStrictEqual(ref.explain({ status: 404, error: "no_chapter", type: "delete" }, {}),
    { key: "failed_delete_closed", vars: {}, retry: false, change: false });
  assert.strictEqual(ref.explain({ status: 404, error: "no_chapter" }, {}).key, "failed_closed", "a create keeps its message");
  // A place refused for good is still dropped.
  const obpl = core.queueSet([], "place", { book: "SC", ch: "SC03", a: "SC 23.3" }, code, 0, 0);
  assert.deepStrictEqual(core.settle(obpl, obpl[0].op, 0, "fail", { error: "no_chapter" }, 404, 1), []);

  // "My earlier comments": by book, then round (newest first, before the first round last), chapter and paragraph.
  const groups = model.groupEarlier([
    { id: 1, book: "SC", ch: "SC03", a: "SC 23.10", round: "first", created: "2026-10-01" },
    { id: 2, book: "SC", ch: "SC03", a: "SC 23.2", round: "first", created: "2026-10-02" },
    { id: 3, book: "SC", ch: "SC01", a: "SC 9.1", round: null, created: "2026-09-01" },
    { id: 4, book: "SC", ch: "SC01", a: "SC 9.1", round: "second", created: "2026-11-02" },
    { id: 5, book: "SC", ch: "SC01", a: "SC 9.1", round: "first", created: "2026-10-03" },
    { id: 6, book: "GC", ch: "GC01", a: "GC 1.1", round: "gone", created: "2026-10-03" },
  ], [{ book: "SC", name: "first", started: "2026-10-01T00:00:00Z", current: false },
      { book: "SC", name: "second", started: "2026-11-01T00:00:00Z", current: false },
      { book: "SC", name: "third", started: "2026-12-01T00:00:00Z", current: true }]);
  assert.deepStrictEqual(groups.map(g => g.book), ["GC", "SC"]);
  const sc = groups[1].rounds;
  assert.deepStrictEqual(sc.map(r => r.round && r.round.name), ["second", "first", null]);
  assert.deepStrictEqual(sc[1].chapters.map(x => x.ch), ["SC01", "SC03"]);
  assert.deepStrictEqual(sc[1].chapters[1].comments.map(x => x.id), [2, 1], "paragraphs in the order of their numbers");
  assert.deepStrictEqual(groups[0].rounds[0].round, { name: "gone", started: "" });
  assert.deepStrictEqual(model.groupEarlier([], []), []);

  // ---- The network module: session mode, link mode, the device key, the wait, and each reader's words ----
  const net = await load("net.js");
  const outbox = () => st.store.get("rv.outbox") || [];
  // Storage that passed the start check of store.js and then refuses every write, as a full one does: the page
  // keeps one key for the whole visit, never a new one per request, which the site would count as a new device.
  const realGet = st.store.get, realSet = st.store.set;
  st.store.get = () => null;
  st.store.set = () => false;
  const key1 = net.deviceKey();
  assert.strictEqual(net.deviceKey(), key1);
  assert.strictEqual(net.deviceKey(), key1);
  st.store.get = realGet;
  st.store.set = realSet;
  assert.match(key1, /^[A-Za-z0-9_-]{16,128}$/);
  assert.strictEqual(net.deviceKey(), key1, "the device key is made once");
  let answers = [];
  const calls = [];
  const events = [];
  st.on("auth", code => events.push(["auth", code]));
  st.on("fault", () => events.push(["fault"]));
  globalThis.fetch = async (url, init) => {
    calls.push({ url, method: init.method, headers: init.headers, body: init.body, credentials: init.credentials });
    const [status, body] = answers.length ? answers.shift() : [500, { error: "server_error" }];
    return { status, headers: { get: () => null }, text: async () => JSON.stringify(body) };
  };
  const meAnswer = (id, extra) => [200, Object.assign({ id, name: "R" + id, books: [{ id: "SC", title: "", round: null, earlier: 0 }],
    chapters: [{ book: "SC", id: "SC03", n: 3, title: "t", version: "v" }] }, extra || {})];
  const pause = ms => new Promise(r => setTimeout(r, ms));
  const created = (id, cid) => [201, { id, client_id: cid, kind: "flag", quote: "", text: "words" }];

  // Signed in (session mode): the session cookie, which the page never sees, and X-Review-Page: 1; never a link's
  // code or the device key.
  Object.assign(st.S, { mode: "session", code: null, reader: 7 });
  answers = [[200, { ok: true }]];
  await net.api("GET", "api/me");
  assert.deepStrictEqual(calls[0].headers, { "X-Review-Page": "1" });
  assert.strictEqual(calls[0].credentials, "same-origin");
  assert.strictEqual(net.who(), 7);
  // Link mode: the link's code and the device key, without the cookies, so that a session of another reader on this
  // browser never answers for the link.
  Object.assign(st.S, { mode: "link", code: "new-link", reader: null });
  answers = [[200, { ok: true }], [200, { ok: true }]];
  await net.api("GET", "api/me");
  assert.deepStrictEqual(calls[1].headers, { "X-Review-Page": "1", Authorization: "Bearer new-link", "X-Review-Device": key1 });
  assert.strictEqual(calls[1].credentials, "omit");
  // The sign-in routes go with the cookies and never with the link's code.
  await net.api("POST", "api/auth/claim", { page: true, body: { link: "new-link" } });
  assert.deepStrictEqual(calls[2].headers, { "X-Review-Page": "1", "Content-Type": "application/json" });
  assert.strictEqual(calls[2].credentials, "same-origin");
  assert.strictEqual(net.who(), "link:new-link", "before the device knows the link's number, the link stands for its reader");
  calls.length = 0;

  // The device waits: /api/me answers 403 device_waiting; the page stops sending and keeps everything.
  st.store.set("rv.outbox", core.queueCreate([], Object.assign({}, c, { client_id: "w1" }), net.who(), 0));
  answers = [[403, { error: "device_waiting", message: "x", device: 12 }]];
  assert.strictEqual(await net.refreshMe(), false);
  assert.strictEqual(st.S.deviceWaiting, true);
  assert.strictEqual(st.S.deviceNumber, 12, "the waiting screen names the device's number");
  assert.strictEqual(calls[0].headers["X-Review-Device"], key1, "every request in link mode carries the device key");
  net.flush();
  await pause(20);
  assert.strictEqual(calls.length, 1, "nothing is sent while the device waits");
  assert.strictEqual(outbox().length, 1);
  // /api/me names the link's reader, 7, whose earlier link is known on this device: the ops and drafts of the earlier
  // link, and those of the link open now, become reader 7's and go; another reader's wait untouched.
  st.store.set("rv.links", { [store.linkTag("old-link")]: 7, [store.linkTag("someone-else")]: 8 });
  st.store.set("rv.outbox", outbox().concat([legacy("o1", "old-link"), legacy("s1", "someone-else")]));
  st.store.set(store.draftKey(store.linkTag("old-link"), "SC", "SC03", "SC 23.3"), { kind: "flag", quote: "", text: "draft of the old link" });
  st.store.set(store.draftKey(store.linkTag("someone-else"), "SC", "SC03", "SC 23.3"), { kind: "flag", quote: "", text: "another reader's draft" });
  st.store.set("rv.cm:SC/SC09", { list: [] });   // a chapter no longer open
  answers = [meAnswer(7)];
  for (let i = 0; i < 4; i++) answers.push(created(100 + i, "?"));
  calls.length = 0;
  assert.strictEqual(await net.refreshMe(), true);
  assert.strictEqual(st.S.deviceWaiting, false, "an answer of /api/me means the device was let in");
  assert.strictEqual(st.S.me.id, 7);
  assert.strictEqual(st.S.reader, 7);
  assert.strictEqual(net.who(), 7);
  assert.strictEqual(st.store.get("rv.reader"), 7);
  assert.strictEqual(st.store.get("rv.links")[store.linkTag("new-link")], 7);
  assert.deepStrictEqual(outbox().filter(o => o.cid === "s1").map(core.ownerOf), [8], "another reader's op waits untouched");
  assert.strictEqual(st.store.get(store.draftKey("R7", "SC", "SC03", "SC 23.3")).text, "draft of the old link");
  assert.strictEqual(st.store.get(store.draftKey(store.linkTag("old-link"), "SC", "SC03", "SC 23.3")), null);
  assert.strictEqual(st.store.get(store.draftKey(store.linkTag("someone-else"), "SC", "SC03", "SC 23.3")).text, "another reader's draft");
  assert.strictEqual(st.store.get("rv.cm:SC/SC09"), null, "a closed chapter's comment list leaves the device");
  // The flush that follows the wait sends reader 7's ops, in link mode with the link open now.
  await pause(50);
  const posts = calls.filter(x => x.method === "POST");
  assert.deepStrictEqual(posts.map(x => JSON.parse(x.body).client_id).sort(), ["o1", "w1"]);
  assert.ok(posts.every(x => x.headers.Authorization === "Bearer new-link" && x.credentials === "omit"));
  assert.deepStrictEqual(outbox().map(o => o.cid), ["s1"]);
  // A link the device learns belongs to reader 7 sends its ops at once, without waiting for another write.
  st.store.set("rv.links", Object.assign(st.store.get("rv.links"), { [store.linkTag("older-link")]: 7 }));
  st.store.set("rv.outbox", outbox().concat([legacy("o2", "older-link")]));
  answers = [meAnswer(7), created(120, "o2")];
  calls.length = 0;
  assert.strictEqual(await net.refreshMe(), true);
  await pause(50);
  assert.deepStrictEqual(calls.filter(x => x.method === "POST").map(x => [JSON.parse(x.body).client_id, x.headers.Authorization]), [["o2", "Bearer new-link"]]);
  assert.deepStrictEqual(outbox().map(o => o.cid), ["s1"]);
  // Forgetting what the device keeps for reading keeps the device key, the link numbers, the outbox and the drafts.
  net.forgetReader();
  assert.strictEqual(net.deviceKey(), key1);
  assert.ok(st.store.get("rv.links"));
  assert.strictEqual(outbox().length, 1);
  assert.ok(st.store.get(store.draftKey("R7", "SC", "SC03", "SC 23.3")));
  // Drafts kept by a page before round 3b go to the link the device held then, and from there to its reader.
  st.store.set("rv.draft:SC/SC03/SC 23.4", { kind: "flag", quote: "", text: "old page's draft" });
  st.store.set("rv.draftOwner", "Anan");
  net.adoptOldDrafts("new-link");
  assert.strictEqual(st.store.get(store.draftKey(store.linkTag("new-link"), "SC", "SC03", "SC 23.4")).text, "old page's draft");
  assert.strictEqual(st.store.get("rv.draft:SC/SC03/SC 23.4"), null);
  assert.strictEqual(st.store.get("rv.draftOwner"), null);
  // A new round of a book makes its kept comment lists stale; another book's stay.
  st.store.set("rv.cm:SC/SC03", { list: [{ client_id: "old-round" }] });
  answers = [meAnswer(7, { books: [{ id: "SC", title: "", round: { name: "second", started: "2026-11-01T00:00:00Z" }, earlier: 1 }] })];
  await net.refreshMe();
  assert.strictEqual(st.store.get("rv.cm:SC/SC03"), null);
  assert.strictEqual(st.store.get(store.draftKey("R7", "SC", "SC03", "SC 23.4")).text, "old page's draft");
  // An earlier wording or a comment list refused for the device leaves the kept chapter where it is.
  st.store.set("rv.ch:SC/SC03", { etag: '"v"', variant: "", data: { book: "SC", id: "SC03", version: "v", title: "t", paras: [] } });
  answers = [[403, { error: "device_waiting" }]];
  assert.strictEqual(await net.fetchChapter("SC", "SC03"), null);
  assert.ok(st.store.get("rv.ch:SC/SC03"), "a device that waits keeps its chapters");
  assert.strictEqual(st.S.deviceWaiting, true);
  answers = [[403, { error: "device_waiting" }]];
  assert.strictEqual(await net.fetchEarlier(), null);
  assert.strictEqual(st.S.deviceNumber, 12, "an answer without a number keeps the one known");

  // Safari before iOS 12.2 has no AbortController: a request still goes, without a timeout.
  const realAbort = globalThis.AbortController;
  globalThis.AbortController = undefined;
  answers = [[200, { ok: true }]];
  assert.strictEqual((await net.api("GET", "api/health")).status, 200);
  globalThis.AbortController = realAbort;

  // A page frozen while it held the outbox lock, as Firefox keeps a page left in the same tab: the page open now
  // finds the lock taken, and once it has been taken for longer than an op's lease, takes it over.
  st.S.deviceWaiting = false;
  let frozen = null;
  navigator.locks.request("rv-outbox", () => new Promise(() => {})).catch(e => { frozen = e.name; });
  await pause(10);
  st.store.set("rv.outbox", core.queueCreate([], Object.assign({}, c, { client_id: "z1" }), net.who(), 0));
  answers = [created(300, "z1")];
  calls.length = 0;
  net.flush();
  await pause(30);
  assert.strictEqual(calls.length, 0, "the lock is taken: nothing goes yet");
  const realNow = Date.now;
  Date.now = () => realNow() + core.LEASE_MS + 1000;
  net.flush();
  await pause(50);
  Date.now = realNow;
  assert.deepStrictEqual(calls.map(x => x.method === "POST" && JSON.parse(x.body).client_id), ["z1"]);
  assert.strictEqual(frozen, "AbortError", "the frozen page's hold ended");
  assert.deepStrictEqual(outbox().filter(o => o.cid === "z1"), []);

  // A refusal that a newer chapter list explains asks for /api/me at once: a chapter closed meanwhile then leaves
  // the page, and a lowered limit is named rightly.
  st.store.set("rv.outbox", core.queueCreate([], Object.assign({}, c, { client_id: "z2" }), net.who(), 0));
  answers = [[404, { error: "no_chapter", message: "x" }], [200, { id: 7, name: "Anan", limits: { text: 40 },
    books: [], chapters: [] }]];
  calls.length = 0;
  net.flush();
  await pause(50);
  assert.deepStrictEqual(calls.map(x => x.method + " " + x.url), ["POST api/comments", "GET api/me"]);
  assert.strictEqual(st.S.me.limits.text, 40);
  assert.strictEqual(outbox()[0].failed.error, "no_chapter");
  st.store.set("rv.outbox", []);

  // ---- Signed in (session mode): a 401 pauses the outbox and keeps every op; each reader's ops wait for that reader ----
  Object.assign(st.S, { mode: "session", code: null, reader: 7, authBlocked: false, deviceWaiting: false });
  st.store.set("rv.outbox", core.queueCreate(core.queueCreate([], Object.assign({}, c, { client_id: "q7" }), 7, 0),
    Object.assign({}, c, { client_id: "q8" }), 8, 0));
  answers = [[401, { error: "signed_out", message: "x" }]];
  calls.length = 0;
  events.length = 0;
  net.flush();
  await pause(50);
  assert.deepStrictEqual(calls.map(x => [x.method, JSON.parse(x.body).client_id, x.credentials, x.headers.Authorization]),
    [["POST", "q7", "same-origin", undefined]], "reader 7's op goes with the cookie; reader 8's waits");
  assert.deepStrictEqual(events, [["auth", "signed_out"]], "the page learns why: the sign-in screen says the browser was signed out");
  assert.strictEqual(st.S.authBlocked, true);
  assert.deepStrictEqual(outbox().map(o => [o.cid, o.failed, o.sending]), [["q7", null, 0], ["q8", null, 0]],
    "a 401 never marks a comment failed or drops it");
  net.flush();
  await pause(20);
  assert.strictEqual(calls.length, 1, "nothing goes while the browser is not signed in");
  for (const [status, error] of [[401, "no_code"], [401, "stopped"], [401, "link_used"], [401, "sign_in_required"], [401, ""]]) {
    assert.strictEqual(core.classify("create", status, error), "auth", error);
  }
  // Signed in again: reader 7's op goes; reader 8's waits.
  st.S.authBlocked = false;
  answers = [created(400, "q7")];
  calls.length = 0;
  net.flush();
  await pause(50);
  assert.deepStrictEqual(calls.map(x => JSON.parse(x.body).client_id), ["q7"]);
  assert.deepStrictEqual(outbox().map(o => o.cid), ["q8"]);
  // A 403 bad_page is a fault of the page: the op waits, nothing more goes at once, and the general notice shows.
  assert.strictEqual(core.classify("create", 403, "bad_page"), "page");
  st.store.set("rv.outbox", core.queueCreate([], Object.assign({}, c, { client_id: "q9" }), 7, 0).concat(outbox()));
  answers = [[403, { error: "bad_page", message: "x" }]];
  events.length = 0;
  calls.length = 0;
  net.flush();
  await pause(50);
  assert.deepStrictEqual(events, [["fault"]]);
  assert.strictEqual(calls.length, 1);
  assert.deepStrictEqual(outbox().filter(o => o.cid === "q9").map(o => [o.failed, o.sending, o.tries > 0]), [[null, 0, true]],
    "the op waits and goes again later, never refused for a fault of the page");
  st.store.set("rv.outbox", outbox().filter(o => o.cid !== "q9"));
  // /api/me names another reader, 8 (the browser was signed in as reader 8 in another tab): what the device kept for
  // reading goes, the device notes reader 8, and reader 8's waiting op goes at once.
  st.store.set("rv.ch:SC/SC03", { etag: '"v"', variant: "", data: { book: "SC", id: "SC03", version: "v", title: "t", paras: [] } });
  st.store.set(store.draftKey("R7", "SC", "SC03", "SC 1.1"), { kind: "flag", quote: "", text: "reader 7's draft" });
  answers = [meAnswer(8), created(401, "q8")];
  calls.length = 0;
  assert.strictEqual(await net.refreshMe(), true);
  await pause(50);
  assert.strictEqual(st.S.reader, 8);
  assert.strictEqual(st.store.get("rv.reader"), 8);
  assert.strictEqual(st.store.get("rv.ch:SC/SC03"), null, "the other reader's kept chapters leave the device");
  assert.strictEqual(st.store.get(store.draftKey("R7", "SC", "SC03", "SC 1.1")).text, "reader 7's draft", "what reader 7 wrote stays");
  assert.deepStrictEqual(calls.filter(x => x.method === "POST").map(x => JSON.parse(x.body).client_id), ["q8"]);
  assert.deepStrictEqual(outbox(), []);
  // A reader in link mode signs in, on a device that already knew the reader's number: the op written in link
  // mode waited for the sign-in, and the first answer of /api/me sends it, with nothing new to adopt.
  st.store.set("rv.reader", 8);
  Object.assign(st.S, { mode: "session", code: null, reader: 8, authBlocked: true, deviceWaiting: false });
  st.store.set("rv.outbox", core.queueCreate([], Object.assign({}, c, { client_id: "s8" }), 8, 0));
  st.S.authBlocked = false;
  answers = [meAnswer(8), created(402, "s8")];
  calls.length = 0;
  assert.strictEqual(await net.refreshMe(), true);
  await pause(50);
  assert.deepStrictEqual(calls.map(x => x.method + " " + x.url), ["GET api/me", "POST api/comments"]);
  assert.deepStrictEqual(outbox(), [], "the waiting comment went with the sign-in, without a reload");
  // Nobody signed in: nothing is sent and /api/me is not asked.
  Object.assign(st.S, { mode: null, code: null, reader: null });
  st.store.set("rv.outbox", core.queueCreate([], Object.assign({}, c, { client_id: "n1" }), 8, 0));
  calls.length = 0;
  net.flush();
  assert.strictEqual(await net.refreshMe(), false);
  await pause(20);
  assert.strictEqual(calls.length, 0);
  assert.strictEqual(outbox().length, 1);
  st.store.set("rv.outbox", []);

  // ---- The rules of signing in (core/auth.js) ----
  const auth = await load("auth.js");
  // The code: six digits, with spaces between them, Thai or Lao digits read as Western ones; anything else is refused
  // on the page before it is sent.
  assert.strictEqual(auth.sixDigits("123456"), "123456");
  assert.strictEqual(auth.sixDigits(" 123 456 "), "123456");
  const digitsIn = (base, s) => s.replace(/[0-9]/g, d => String.fromCharCode(base + Number(d)));   // Thai 0x0E50, Lao 0x0ED0
  assert.strictEqual(auth.sixDigits(digitsIn(0x0E50, "123456")), "123456");
  assert.strictEqual(auth.sixDigits(digitsIn(0x0ED0, "09") + " 1234"), "091234");
  for (const bad of ["12345", "1234567", "12a456", "", null]) assert.strictEqual(auth.sixDigits(bad), null, String(bad));
  // An email address by the server's own pattern.
  assert.ok(auth.isAddress("Mali@Example.org"));
  assert.ok(auth.isAddress("  pim@example.co.th "));
  for (const bad of ["mali", "mali@example", "@example.org", "a b@example.org", "mali@exa mple.org"]) assert.ok(!auth.isAddress(bad), bad);
  // Before the @ only A to Z, digits and . _ % + -, as the server takes it.
  assert.ok(auth.isAddress("a.b-c_d+e%f@example.org"));
  for (const bad of ["x\u001b@evil.example", "group:x@evil.example", "a(b)c@evil.example", "\u202ex@evil.example",
    "x\u200b@evil.example", "\uff58@evil.example"]) assert.ok(!auth.isAddress(bad), JSON.stringify(bad));
  // Each sign-in route takes the code of the screen it starts from in its body, never in an address.
  assert.deepStrictEqual(auth.startBody("link", "C"), { link: "C" });
  assert.deepStrictEqual(auth.startBody("join", "C"), { join: "C" });
  assert.deepStrictEqual(auth.startBody("add", "C"), { add: true });
  assert.deepStrictEqual(auth.startBody("signin", "C"), {});
  // Every result of server/auth.py has a screen.
  const results = { signed_in: "list", added: "account", request_sent: "request", request_waiting: "request",
    request_declined: "request", no_account: "signin", identity_taken: "start", link_used: "signin", link_signs_in: "claim", stopped: "stopped",
    join_closed: "closed", join_busy: "start", cancelled: "start", expired: "start", other_browser: "start", failed: "start" };
  for (const [result, screen] of Object.entries(results)) assert.strictEqual(auth.afterSignIn(result).screen, screen, result);
  assert.strictEqual(auth.afterSignIn("cancelled").key, "", "a cancel shows the screen as it was");
  assert.strictEqual(auth.afterSignIn("expired").key, "line_expired");
  assert.deepStrictEqual(auth.afterSignIn("nonsense"), { screen: "signin", key: "" });
  assert.deepStrictEqual(auth.afterSignIn("constructor"), { screen: "signin", key: "" });
  // Every 401 of a reader route has a screen; no_code right after a sign-in means the browser refused the cookie.
  assert.deepStrictEqual(auth.afterRefusal("no_code", false), { screen: "signin", key: "" });
  assert.deepStrictEqual(auth.afterRefusal("no_code", true), { screen: "blocked", key: "" });
  assert.deepStrictEqual(auth.afterRefusal("signed_out", false), { screen: "signin", key: "line_signed_out" });
  assert.deepStrictEqual(auth.afterRefusal("link_used", false), { screen: "signin", key: "line_link_used" });
  assert.strictEqual(auth.afterRefusal("stopped", false).screen, "stopped");
  assert.strictEqual(auth.afterRefusal("bad_code", false).screen, "link");
  assert.strictEqual(auth.afterRefusal("sign_in_required", false).screen, "claim");
  assert.strictEqual(auth.afterRefusal("", false), null);
  // A refusal of a start or of the code is a line under the field, or another screen.
  const said = (status, data, wait) => auth.startRefusal({ status, data, wait: wait || 0 });
  assert.deepStrictEqual(said(400, { error: "wrong_code", tries_left: 2 }), { key: "wrong_code_many", vars: { n: 2 }, screen: "" });
  assert.deepStrictEqual(said(400, { error: "wrong_code", tries_left: 1 }), { key: "wrong_code_one", vars: { n: 1 }, screen: "" });
  assert.strictEqual(said(400, { error: "code_used_up" }).key, "code_used_up");
  assert.strictEqual(said(400, { error: "code_expired" }).key, "code_expired");
  assert.strictEqual(said(400, { error: "bad_email" }).key, "bad_email");
  assert.strictEqual(said(503, { error: "mail_failed" }, 60000).key, "mail_failed");
  assert.strictEqual(said(429, { error: "slow_down" }, 60000).key, "too_many");
  assert.strictEqual(said(429, { error: "slow_down" }, 600000).key, "too_many_hour", "an hourly limit");
  // A limit that names itself: the codes of a day, of an hour, and the wrong codes of an hour.
  assert.strictEqual(said(429, { error: "slow_down", limit: "day" }, 3600000).key, "too_many_day");
  assert.strictEqual(said(429, { error: "slow_down" }, 80000000).key, "too_many_day", "a wait of a day without a name");
  assert.strictEqual(said(429, { error: "slow_down", limit: "hour" }, 60000).key, "too_many_hour");
  assert.strictEqual(said(429, { error: "slow_down", limit: "wrong" }, 3000000).key, "too_many_wrong");
  // "Link signs in" came on: the link's claim says the screen again.
  assert.deepStrictEqual(said(409, { error: "link_signs_in" }), { key: "", vars: {}, screen: "claim" });
  assert.strictEqual(said(429, null, 0).key, "too_many");
  assert.deepStrictEqual(said(409, { error: "link_used" }), { key: "line_link_used", vars: {}, screen: "signin" });
  assert.strictEqual(said(410, { error: "join_closed" }).screen, "closed");
  assert.strictEqual(said(401, { error: "signed_out" }).screen, "signin");
  assert.strictEqual(said(0, null).key, "cannot_connect");
  assert.strictEqual(said(404, { error: "route_off" }).key, "error_generic");
  // The screen kept for the way back from LINE counts for half an hour.
  assert.ok(auth.flowFresh({ kind: "link", code: "C", at: 1000 }, 1000 + 29 * 60000));
  assert.ok(!auth.flowFresh({ kind: "link", code: "C", at: 1000 }, 1000 + 31 * 60000));
  assert.ok(!auth.flowFresh(null, 1000));
  // The hint on adding the site to the Home Screen: Safari on an iPhone or iPad only, and not once the site runs from
  // the Home Screen, since the reader has added it then.
  const ua = {
    iphone: "Mozilla/5.0 (iPhone; CPU iPhone OS 12_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1.2 Mobile/15E148 Safari/604.1",
    ipad: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    chrome: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/118.0 Mobile/15E148 Safari/604.1",
    line: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Safari Line/13.17.0",
    android: "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Mobile Safari/537.36",
  };
  assert.ok(auth.wantsHomeHint({ userAgent: ua.iphone, platform: "iPhone", maxTouchPoints: 5 }));
  assert.ok(auth.wantsHomeHint({ userAgent: ua.ipad, platform: "MacIntel", maxTouchPoints: 5 }), "an iPad names itself a Mac");
  assert.ok(!auth.wantsHomeHint({ userAgent: ua.ipad, platform: "MacIntel", maxTouchPoints: 0 }), "Safari on a Mac");
  assert.ok(!auth.wantsHomeHint({ userAgent: ua.iphone, platform: "iPhone", maxTouchPoints: 5, standalone: true }), "already on the Home Screen");
  assert.ok(!auth.wantsHomeHint({ userAgent: ua.chrome, platform: "iPhone", maxTouchPoints: 5 }));
  assert.ok(!auth.wantsHomeHint({ userAgent: ua.line, platform: "iPhone", maxTouchPoints: 5 }));
  assert.ok(!auth.wantsHomeHint({ userAgent: ua.android, platform: "Linux armv8l", maxTouchPoints: 5 }));
  assert.ok(!auth.wantsHomeHint(undefined));

  // Features: a place's entry shows only while its feature is on; an unknown feature is off.
  ext.feature({ name: "probe", variant: "pr" });
  ext.panelSection({ name: "probe-panel", feature: "probe", order: 5, hint: "hint_probe", render: () => null });
  ext.chapterSection({ name: "core-section", order: 1, render: () => null });
  const on = { features: { probe: { on: true } } };
  const off = { features: { probe: { on: false } } };
  assert.strictEqual(ext.isOn(on, "probe"), true);
  assert.strictEqual(ext.isOn(off, "probe"), false);
  assert.strictEqual(ext.isOn({ features: {} }, "probe"), false);
  assert.strictEqual(ext.isOn({ features: { nobody: { on: true } } }, "nobody"), false);
  assert.strictEqual(ext.isOn(null, undefined), true);
  assert.deepStrictEqual(ext.active("panels", on).map(d => d.name), ["probe-panel"]);
  assert.deepStrictEqual(ext.active("panels", off).map(d => d.name), []);
  assert.deepStrictEqual(ext.active("sections", off).map(d => d.name), ["core-section"]);
  assert.strictEqual(ext.hintKey(on), "hint_probe");
  assert.strictEqual(ext.hintKey(off), "hint");
  assert.strictEqual(ext.variantOf(on), "pr");
  assert.strictEqual(ext.variantOf(off), "");
  // A feature may decide from settings other than "on".
  ext.feature({ name: "bible", enabled: s => typeof s.version === "string" && s.version !== "" });
  assert.strictEqual(ext.isOn({ features: { bible: { version: "THSV11" } } }, "bible"), true);
  assert.strictEqual(ext.isOn({ features: { bible: { version: "" } } }, "bible"), false);
  // A feature's fault is logged and left out; it never stops the page.
  const quiet = console.error;
  console.error = () => {};
  assert.strictEqual(ext.safely({ name: "x" }, () => { throw new Error("boom"); }, "fallback"), "fallback");
  console.error = quiet;
  ext.spanMark({ name: "probe-mark", feature: "probe", kind: "bible" });
  assert.strictEqual(ext.markFor("bible", on).name, "probe-mark");
  assert.strictEqual(ext.markFor("bible", off), null);

  // The page loads each feature named in index.html under features/ on its own: one that fails is logged
  // and left out, the others load, and nothing outside features/ is loaded.
  const main = await load("main.js");
  const links = ["core/main.js", "features/english.js", "features/no-such-feature.js", "https://elsewhere.example/x.js"];
  const doc = { querySelectorAll: () => links.map(href => ({ getAttribute: () => href })) };
  const logged = [];
  console.error = m => logged.push(String(m));
  const loaded = await main.loadFeatures(doc);
  console.error = quiet;
  assert.deepStrictEqual(loaded, [true, false]);
  assert.deepStrictEqual(logged, ["feature features/no-such-feature.js did not load"]);
  assert.strictEqual(ext.isOn({ features: { english: { on: true } } }, "english"), true);
  // The address at the start: a personal link, a general link, or the result of a sign-in with LINE.
  assert.deepStrictEqual(main.readHash("#k=Abc_123-x"), { link: "Abc_123-x", join: null, result: null });
  assert.deepStrictEqual(main.readHash("#k=Abc_123-x."), { link: "Abc_123-x", join: null, result: null }, "a full stop after the link");
  assert.deepStrictEqual(main.readHash("#join=Gen_1"), { link: null, join: "Gen_1", result: null });
  assert.deepStrictEqual(main.readHash("#auth=request_sent"), { link: null, join: null, result: "request_sent" });
  assert.deepStrictEqual(main.readHash("#SC/SC03"), { link: null, join: null, result: null });
  assert.deepStrictEqual(main.readHash(""), { link: null, join: null, result: null });

  // Ranges over a text's nodes: how they cut the nodes. Two nodes of 5 and 6 code points; pair 0 covers
  // [0, 3), pair 1 covers [4, 9), which crosses from the first node into the second.
  const quotes = await load("quotes.js");
  assert.deepStrictEqual(quotes.pieces([5, 6], [[0, 3, 0], [4, 9, 1]]),
    [[[0, 3, 0], [3, 4, -1], [4, 5, 1]], [[0, 4, 1], [4, 6, -1]]]);
  assert.deepStrictEqual(quotes.pieces([4], []), [[[0, 4, -1]]]);
  assert.deepStrictEqual(quotes.pieces([2, 0, 2], [[0, 4, 0]]), [[[0, 2, 0]], [], [[0, 2, 0]]]);
  // The sentence module adds to english: on with English, off without it, and a sentence span is its mark; the
  // English leads the panel's first face, and Previous and Next sentence follow it.
  await import(pathToFileURL(path.join(__dirname, "..", "web", "features", "sentences.js")).href);
  const english = { features: { english: { on: true } } };
  assert.strictEqual(ext.markFor("sentence", english).name, "sentences");
  assert.strictEqual(ext.markFor("sentence", { features: { english: { on: false } } }), null);
  assert.deepStrictEqual(ext.active("texts", english).map(d => d.name), ["sentences"]);
  assert.deepStrictEqual(ext.active("panels", english).map(d => [d.name, !!d.lead]),
    [["english", true], ["steps", false], ["earlier", false]]);
  assert.deepStrictEqual(ext.active("panels", { features: {} }).map(d => d.name), ["earlier"]);

  // Words: with a segmenter, Thai splits into its words; without one, a word runs between white space.
  const run1 = "เมื่อพระเจ้าทรงสร้างมนุษย์", run2 = "ขึ้นมา", thai = run1 + " " + run2;
  const n1 = Array.from(run1).length, n2 = Array.from(run2).length;
  assert.deepStrictEqual(quotes.wordRanges("ab  cd e", null), [[0, 2], [4, 6], [7, 8]]);
  assert.deepStrictEqual(quotes.wordRanges(thai, null), [[0, n1], [n1 + 1, n1 + 1 + n2]]);
  if (typeof Intl === "object" && Intl.Segmenter) {
    const words = quotes.wordRanges(thai, new Intl.Segmenter("th", { granularity: "word" }));
    assert.ok(words.length > 3, "the segmenter splits a Thai run into words");
    assert.deepStrictEqual(words[0], [0, 5]);   // เมื่อ
  }
  // A segment with a letter or a digit is a word even when the segmenter calls it not word-like, as Firefox does
  // with โรม; spaces and punctuation are no words.
  const like = { segment: () => [["(", false], ["โรม", false], [" ", false], ["7", true], [":", false], ["24", true], [")", false]]
    .map(x => ({ segment: x[0], isWordLike: x[1] })) };
  assert.deepStrictEqual(quotes.wordRanges("(โรม 7:24)", like), [[1, 4], [5, 6], [7, 9]]);
  // The word under a tap: the one holding the offset, the one ending there (a tap on its last letter), the nearest.
  const ws = [[0, 2], [4, 6], [7, 8]];
  assert.deepStrictEqual(quotes.wordAt(ws, 1), [0, 2]);
  assert.deepStrictEqual(quotes.wordAt(ws, 6), [4, 6]);
  assert.deepStrictEqual(quotes.wordAt(ws, 3), [0, 2]);
  assert.strictEqual(quotes.wordAt([], 3), null);
  // Clusters: a letter with the marks drawn on it, the vowel AM among them, as the browser measures them.
  assert.deepStrictEqual(quotes.clusters("สร้าง"), [[0, 1], [1, 3], [3, 4], [4, 5]]);
  assert.deepStrictEqual(quotes.clusters("กำลัง"), [[0, 2], [2, 4], [4, 5]]);
  assert.deepStrictEqual(quotes.clusters("น้ำ"), [[0, 3]]);
  assert.deepStrictEqual(quotes.clusters("ab c"), [[0, 1], [1, 2], [2, 3], [3, 4]]);
  // The character under a tap. On a made-up line each cluster of "สร้างมนุษย์ขึ้น" is a box 10 pixels wide and
  // 20 high, side by side. A tap on the right half of ง, the last letter of สร้าง, gets the caret after it, at 5,
  // where มนุษย์ starts; the boxes give ง, so the word is สร้าง, not the next one.
  const line = "สร้างมนุษย์ขึ้น", cls = quotes.clusters(line);
  const boxesOf = (s, e) => {
    const j0 = cls.findIndex(c => c[0] === s), j1 = cls.findIndex(c => c[1] === e);
    return j0 < 0 || j1 < 0 ? [] : [{ left: 10 * j0, right: 10 * j1 + 10, top: 0, bottom: 20 }];
  };
  const lineWords = [[0, 5], [5, 11], [11, 15]];   // สร้าง, มนุษย์, ขึ้น
  assert.strictEqual(quotes.charUnder(line, 5, boxesOf, 38, 10), 4);
  assert.deepStrictEqual(quotes.wordAt(lineWords, quotes.charUnder(line, 5, boxesOf, 38, 10)), [0, 5]);
  assert.deepStrictEqual(quotes.wordAt(lineWords, 5), [5, 11], "the word at the caret would be the next one");
  // A tap on the tone mark above ขึ้ (high in its box) gives the cluster's letter, so the word ขึ้น.
  assert.strictEqual(quotes.charUnder(line, 14, boxesOf, 85, 2), 11);
  assert.deepStrictEqual(quotes.wordAt(lineWords, quotes.charUnder(line, 14, boxesOf, 85, 2)), [11, 15]);
  // A caret one cluster away from the letter tapped still finds it; a tap under the line takes the nearest box.
  assert.strictEqual(quotes.charUnder(line, 3, boxesOf, 35, 10), 4);
  assert.strictEqual(quotes.charUnder(line, 5, boxesOf, 38, 30), 4);
  // Without any box, as where the browser measures nothing, the caret stands; a box without width counts for nothing.
  assert.strictEqual(quotes.charUnder(line, 5, () => [], 38, 10), 5);
  assert.strictEqual(quotes.charUnder(line, 5, (s, e) => s === 4 ? [{ left: 40, right: 40, top: 0, bottom: 20 }] : boxesOf(s, e), 40, 10), 5);
  // The words between two picks: trimmed, white space as one space, and where they start and end.
  assert.deepStrictEqual(quotes.quoteBetween("ab  cd\ne", 0, 9), { at: 0, end: 8, text: "ab cd e" });
  assert.deepStrictEqual(quotes.quoteBetween(" ab ", 0, 4), { at: 1, end: 3, text: "ab" });
  assert.strictEqual(quotes.quoteBetween("a   b", 1, 4), null);
  assert.deepStrictEqual(quotes.quoteBetween("abcdef", 0, 6, 3), { at: 0, end: 6, text: "abc" }, "cut to the longest quote");
  // Where a quote stands: at its place when it stands there, else the first place, else nowhere; white space
  // counts as one space either way.
  const para = "the word and the word again";
  assert.deepStrictEqual(quotes.locate(para, "the word", 13), [13, 21]);
  assert.deepStrictEqual(quotes.locate(para, "the word", 5), [0, 8], "at does not fit: the first place");
  assert.deepStrictEqual(quotes.locate(para, "the word", null), [0, 8]);
  assert.deepStrictEqual(quotes.locate("a  b c", "a b", 0), [0, 4]);
  assert.strictEqual(quotes.locate(para, "absent", 0), null);
  assert.strictEqual(quotes.locate(para, "  ", 0), null);
  // The backgrounds: soft for one comment, deeper for two or more, and the picked words over both.
  assert.deepStrictEqual(quotes.marks([[0, 8], [4, 12]], null), [[0, 4, "q1"], [4, 8, "q2"], [8, 12, "q1"]]);
  assert.deepStrictEqual(quotes.marks([[0, 8]], [2, 4]), [[0, 2, "q1"], [2, 4, "pk"], [4, 8, "q1"]]);
  assert.deepStrictEqual(quotes.marks([], null), []);
  assert.deepStrictEqual(quotes.marks([[0, 4], [0, 4]], null), [[0, 4, "q2"]]);
  // Previous and Next sentence: every pair of each paragraph with English, a paragraph without pairs as one stop,
  // into the next paragraph after the last pair, and nothing past either end.
  const stops = quotes.stepList([{ a: "A", en: "x", al: [{}, {}] }, { a: "B", en: "" }, { a: "C", en: "y" }, { a: "D", en: "z", al: [{}] }]);
  assert.deepStrictEqual(stops, [{ a: "A", s: 0 }, { a: "A", s: 1 }, { a: "C", s: -1 }, { a: "D", s: 0 }]);
  assert.deepStrictEqual(quotes.stepFrom(stops, "A", 1, 1), { a: "C", s: -1 });
  assert.deepStrictEqual(quotes.stepFrom(stops, "C", -1, 1), { a: "D", s: 0 });
  assert.deepStrictEqual(quotes.stepFrom(stops, "D", 0, -1), { a: "C", s: -1 });
  assert.strictEqual(quotes.stepFrom(stops, "A", 0, -1), null);
  assert.strictEqual(quotes.stepFrom(stops, "D", 0, 1), null);
  // A paragraph opened without a sentence: Next goes to its first pair, Previous to the stop before it.
  assert.deepStrictEqual(quotes.stepFrom(stops, "D", -1, 1), { a: "D", s: 0 });
  assert.deepStrictEqual(quotes.stepFrom(stops, "A", -1, 1), { a: "A", s: 0 });
  assert.deepStrictEqual(quotes.stepFrom(stops, "D", -1, -1), { a: "C", s: -1 });
  assert.strictEqual(quotes.stepFrom(stops, "B", -1, 1), null);

  // The English ranges of the pairs: a range two pairs share, as in {SC 18.2} where one English sentence is rendered
  // by two Thai sentences around a Bible reference, is wrapped once and names both pairs, so either lights it.
  const shared = [{ text: [0, 5], en: [[0, 184]] }, { text: [5, 9], en: [[185, 200]] }, { text: [9, 12], en: [[0, 184]] },
    { text: [12, 15], en: [[201, 210], [211, 220]] }];
  assert.deepStrictEqual(quotes.englishRanges(shared), [[0, 184, "0 2"], [185, 200, "1"], [201, 210, "3"], [211, 220, "3"]]);
  assert.deepStrictEqual(quotes.englishRanges([]), []);
  assert.strictEqual(quotes.holdsPair("0 2", "2"), true);
  assert.strictEqual(quotes.holdsPair("0 2", "0"), true);
  assert.strictEqual(quotes.holdsPair("12", "1"), false);
  assert.strictEqual(quotes.holdsPair("0 2", null), false);

  // A draft is kept only while it holds words the reader wrote: words a selection or a pick put in the quote box
  // alone are not the reader's comment, so they never come back as a draft or count as not saved.
  assert.strictEqual(store.draftHolds({ kind: "flag", quote: "ครทูตเปาโลเข", text: "", auto: true, at: 322 }), false);
  assert.strictEqual(store.draftHolds({ kind: "flag", quote: "ครทูตเปาโลเข", text: "  ", auto: true, at: 322 }), false);
  assert.strictEqual(store.draftHolds({ kind: "flag", quote: "ครทูตเปาโลเข", text: "why?", auto: true, at: 322 }), true);
  assert.strictEqual(store.draftHolds({ kind: "wording", quote: "typed", text: "", auto: false, at: null }), true);
  assert.strictEqual(store.draftHolds({ kind: "flag", quote: "", text: "" }), false);
  assert.strictEqual(store.draftHolds(null), false);

  // A comment keeps where its quoted words start (`at`) through the outbox; a comment without quoted words keeps no
  // place. An answer that gives the same place settles the op; one that lacks it, from a server before version 9,
  // sends the place again as a change.
  let obAt = core.queueCreate([], Object.assign({}, c, { quote: "words", at: 0 }), code, 0);
  assert.strictEqual(obAt[0].body.at, 0);
  assert.strictEqual(core.queueCreate([], Object.assign({}, c, { at: 4 }), code, 0)[0].body.at, null);
  const same = core.settle(obAt.slice(), obAt[0].op, 0, "ok", { id: 9, kind: "flag", quote: "words", text: "words", at: 0 }, 201, 1);
  assert.deepStrictEqual(same, []);
  const older = core.settle(obAt, obAt[0].op, 0, "ok", { id: 9, kind: "flag", quote: "words", text: "words" }, 201, 1);
  assert.strictEqual(older[0].type, "update");
  assert.deepStrictEqual(older[0].body, { kind: "flag", quote: "words", text: "words", at: 0 });
  let obEdit = core.queueEdit([], Object.assign({ id: 3 }, c), { kind: "flag", quote: "new", text: "t", at: 7 }, code, 0);
  assert.deepStrictEqual(core.requestFor(obEdit[0]), ["PATCH", "api/comments/3", { kind: "flag", quote: "new", text: "t", at: 7 }]);

  console.log("ok");
})().catch(err => { console.error(err); process.exit(1); });

/* Checks of the page's plain modules in web/core/ (the outbox, the server's answers, the refusals, the
   feature places, what changed since the reader last opened a chapter, and the words), and of the plain
   part of web/features/sentences.js, run by test_core.py with node. Prints "ok" and exits 0 when every
   check passes. */
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

  const code = "reader-code";
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

  // ---- Each link's ops are kept apart: only the link open now sends ----
  const other = "code-of-another-link";
  let obl = core.queueCreate([], Object.assign({}, c, { client_id: "x1" }), other, 0);
  obl = core.queueCreate(obl, Object.assign({}, c, { client_id: "x2" }), code, 0);
  obl = core.queueSet(obl, "place", { book: "SC", ch: "SC03", a: "SC 23.3" }, other, 0, 0);
  obl = core.queueSet(obl, "place", { book: "SC", ch: "SC03", a: "SC 23.4" }, code, 0, 0);
  assert.strictEqual(obl.length, 4, "two links' places of one chapter stay apart");
  assert.strictEqual(core.pickNext(obl, 1, code).cid, "x2");
  assert.strictEqual(core.pickNext(obl, 1, other).cid, "x1");
  assert.strictEqual(core.pickNext(obl, 1).cid, "x1");                 // no link given: any op, as before
  const afterX2 = obl.filter(o => o.cid !== "x2");
  assert.strictEqual(core.pickNext(afterX2, 1, code).body.a, "SC 23.4");  // another link's place does not block this one
  assert.strictEqual(core.nextWake(obl.filter(o => o.code === other), 1, code), Infinity);
  assert.deepStrictEqual(core.overlay([], obl, "SC", "SC03", code).map(x => x.client_id), ["x2"]);
  // flushOnce sends only io.code's ops, under their own link.
  const sent = [];
  let box = obl.map(o => Object.assign({}, o));
  const io2 = { load: () => box, save: x => { box = x; }, now: () => 5, code,
    send: async (m, pth, body, cd) => { sent.push([m, pth, cd]); return { status: 201, data: { id: 9, client_id: "x2", kind: "flag", quote: "", text: "words" } }; } };
  await core.flushOnce(io2);
  assert.deepStrictEqual(sent, [["POST", "api/comments", code]]);
  // A new link of the same reader takes over the reader's ops; another reader's stay as they are.
  let oba = core.queueCreate([], Object.assign({}, c, { client_id: "y1" }), "old-link", 0);
  oba = core.queueCreate(oba, Object.assign({}, c, { client_id: "y2" }), "someone-else", 0);
  oba = core.queueCreate(oba, Object.assign({}, c, { client_id: "y3" }), "old-link", 0);
  oba[2].sending = 10;   // being sent by another tab: left alone
  assert.strictEqual(core.adoptOps(oba, "new-link", cd => cd === "old-link", 11), 1);
  assert.deepStrictEqual(oba.map(o => o.code), ["new-link", "someone-else", "old-link"]);

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
  // translator still receives it (46 ADV3-03, 48 UX3-4); only no_comment means the comment is already gone.
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

  // ---- The network module: the device key, the wait, and a new link of the same reader ----
  const net = await load("net.js");
  const outbox = () => st.store.get("rv.outbox") || [];
  // Storage that passed the start check of store.js and then refuses every write, as a full one does: the page
  // keeps one key for the whole visit, never a new one per request (45 SEC3-9).
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
  globalThis.fetch = async (url, init) => {
    calls.push({ url, method: init.method, headers: init.headers, body: init.body });
    const [status, body] = answers.length ? answers.shift() : [500, { error: "server_error" }];
    return { status, headers: { get: () => null }, text: async () => JSON.stringify(body) };
  };
  st.S.code = "new-link";
  // The device waits: /api/me answers 403 device_waiting; the page stops sending and keeps everything.
  st.store.set("rv.outbox", core.queueCreate([], Object.assign({}, c, { client_id: "w1" }), "new-link", 0));
  answers = [[403, { error: "device_waiting", message: "x", device: 12 }]];
  assert.strictEqual(await net.refreshMe(), false);
  assert.strictEqual(st.S.deviceWaiting, true);
  assert.strictEqual(st.S.deviceNumber, 12, "the waiting screen names the device's number (45 SEC3-5)");
  assert.strictEqual(calls[0].headers["X-Review-Device"], key1, "every request carries the device key");
  net.flush();
  await new Promise(r => setTimeout(r, 20));
  assert.strictEqual(calls.length, 1, "nothing is sent while the device waits");
  assert.strictEqual(outbox().length, 1);
  // A new link of reader 7, whose old link is known on this device: the old link's ops and drafts move to it.
  st.store.set("rv.links", { [store.linkTag("old-link")]: 7, [store.linkTag("someone-else")]: 8 });
  st.store.set("rv.outbox", outbox().concat(core.queueCreate([], Object.assign({}, c, { client_id: "o1" }), "old-link", 0),
    core.queueCreate([], Object.assign({}, c, { client_id: "s1" }), "someone-else", 0)));
  st.store.set(store.draftKey(store.linkTag("old-link"), "SC", "SC03", "SC 23.3"), { kind: "flag", quote: "", text: "draft of the old link" });
  st.store.set(store.draftKey(store.linkTag("someone-else"), "SC", "SC03", "SC 23.3"), { kind: "flag", quote: "", text: "another reader's draft" });
  st.store.set("rv.cm:SC/SC09", { list: [] });   // a chapter no longer open
  answers = [[200, { id: 7, name: "Anan", books: [{ id: "SC", title: "", round: null, earlier: 0 }],
    chapters: [{ book: "SC", id: "SC03", n: 3, title: "t", version: "v" }] }]];
  for (let i = 0; i < 4; i++) answers.push([201, { id: 100 + i, client_id: "?", kind: "flag", quote: "", text: "words" }]);
  calls.length = 0;
  assert.strictEqual(await net.refreshMe(), true);
  assert.strictEqual(st.S.deviceWaiting, false, "an answer of /api/me means the device was let in");
  assert.strictEqual(st.S.me.id, 7);
  assert.strictEqual(st.store.get("rv.links")[store.linkTag("new-link")], 7);
  assert.deepStrictEqual(outbox().filter(o => o.cid === "o1").map(o => o.code), ["new-link"], "the old link's op goes under the new link");
  assert.deepStrictEqual(outbox().filter(o => o.cid === "s1").map(o => o.code), ["someone-else"], "another reader's op waits untouched");
  assert.strictEqual(st.store.get(store.draftKey(store.linkTag("new-link"), "SC", "SC03", "SC 23.3")).text, "draft of the old link");
  assert.strictEqual(st.store.get(store.draftKey(store.linkTag("old-link"), "SC", "SC03", "SC 23.3")), null);
  assert.strictEqual(st.store.get(store.draftKey(store.linkTag("someone-else"), "SC", "SC03", "SC 23.3")).text, "another reader's draft");
  assert.strictEqual(st.store.get("rv.cm:SC/SC09"), null, "a closed chapter's comment list leaves the device");
  // The flush that follows the wait sends this link's ops only, each under the new link.
  await new Promise(r => setTimeout(r, 50));
  const posts = calls.filter(x => x.method === "POST");
  assert.deepStrictEqual(posts.map(x => JSON.parse(x.body).client_id).sort(), ["o1", "w1"]);
  assert.ok(posts.every(x => x.headers.Authorization === "Bearer new-link"));
  assert.deepStrictEqual(outbox().map(o => o.cid), ["s1"]);
  // A link that takes over another link's ops sends them at once, without waiting for another write.
  st.store.set("rv.links", Object.assign(st.store.get("rv.links"), { [store.linkTag("older-link")]: 7 }));
  st.store.set("rv.outbox", outbox().concat(core.queueCreate([], Object.assign({}, c, { client_id: "o2" }), "older-link", 0)));
  answers = [[200, { id: 7, name: "Anan", books: [{ id: "SC", title: "", round: null, earlier: 0 }],
    chapters: [{ book: "SC", id: "SC03", n: 3, title: "t", version: "v" }] }], [201, { id: 120, client_id: "o2", kind: "flag", quote: "", text: "words" }]];
  calls.length = 0;
  assert.strictEqual(await net.refreshMe(), true);
  await new Promise(r => setTimeout(r, 50));
  assert.deepStrictEqual(calls.filter(x => x.method === "POST").map(x => [JSON.parse(x.body).client_id, x.headers.Authorization]), [["o2", "Bearer new-link"]]);
  assert.deepStrictEqual(outbox().map(o => o.cid), ["s1"]);
  // A new link keeps the device key, the link numbers, the outbox and the drafts.
  net.forgetReader();
  assert.strictEqual(net.deviceKey(), key1);
  assert.ok(st.store.get("rv.links"));
  assert.strictEqual(outbox().length, 1);
  assert.ok(st.store.get(store.draftKey(store.linkTag("new-link"), "SC", "SC03", "SC 23.3")));
  // Drafts kept by a page before round 3b go to the link the device held then.
  st.store.set("rv.draft:SC/SC03/SC 23.4", { kind: "flag", quote: "", text: "old page's draft" });
  st.store.set("rv.draftOwner", "Anan");
  net.adoptOldDrafts("new-link");
  assert.strictEqual(st.store.get(store.draftKey(store.linkTag("new-link"), "SC", "SC03", "SC 23.4")).text, "old page's draft");
  assert.strictEqual(st.store.get("rv.draft:SC/SC03/SC 23.4"), null);
  assert.strictEqual(st.store.get("rv.draftOwner"), null);
  // A new round of a book makes its kept comment lists stale; another book's stay.
  st.store.set("rv.cm:SC/SC03", { list: [{ client_id: "old-round" }] });
  answers = [[200, { id: 7, name: "Anan", books: [{ id: "SC", title: "", round: { name: "second", started: "2026-11-01T00:00:00Z" }, earlier: 1 }],
    chapters: [{ book: "SC", id: "SC03", n: 3, title: "t", version: "v" }] }]];
  await net.refreshMe();
  assert.strictEqual(st.store.get("rv.cm:SC/SC03"), null);
  // An earlier wording or a comment list refused for the device leaves the kept chapter where it is.
  st.store.set("rv.ch:SC/SC03", { etag: '"v"', variant: "", data: { book: "SC", id: "SC03", version: "v", title: "t", paras: [] } });
  answers = [[403, { error: "device_waiting" }]];
  assert.strictEqual(await net.fetchChapter("SC", "SC03"), null);
  assert.ok(st.store.get("rv.ch:SC/SC03"), "a device that waits keeps its chapters");
  assert.strictEqual(st.S.deviceWaiting, true);
  answers = [[403, { error: "device_waiting" }]];
  assert.strictEqual(await net.fetchEarlier(), null);
  assert.strictEqual(st.S.deviceNumber, 12, "an answer without a number keeps the one known");

  // Safari before iOS 12.2 has no AbortController: a request still goes, without a timeout (48 UX3-9).
  const realAbort = globalThis.AbortController;
  globalThis.AbortController = undefined;
  answers = [[200, { ok: true }]];
  assert.strictEqual((await net.api("GET", "api/health")).status, 200);
  globalThis.AbortController = realAbort;

  // A page frozen while it held the outbox lock, as Firefox keeps a page left in the same tab: the page open now
  // finds the lock taken, and once it has been taken for longer than an op's lease, takes it over (48 UX3-1).
  st.S.deviceWaiting = false;
  let frozen = null;
  navigator.locks.request("rv-outbox", () => new Promise(() => {})).catch(e => { frozen = e.name; });
  await new Promise(r => setTimeout(r, 10));
  st.store.set("rv.outbox", core.queueCreate([], Object.assign({}, c, { client_id: "z1" }), st.S.code, 0));
  answers = [[201, { id: 300, client_id: "z1", kind: "flag", quote: "", text: "words" }]];
  calls.length = 0;
  net.flush();
  await new Promise(r => setTimeout(r, 30));
  assert.strictEqual(calls.length, 0, "the lock is taken: nothing goes yet");
  const realNow = Date.now;
  Date.now = () => realNow() + core.LEASE_MS + 1000;
  net.flush();
  await new Promise(r => setTimeout(r, 50));
  Date.now = realNow;
  assert.deepStrictEqual(calls.map(x => x.method === "POST" && JSON.parse(x.body).client_id), ["z1"]);
  assert.strictEqual(frozen, "AbortError", "the frozen page's hold ended");
  assert.deepStrictEqual(outbox(), []);

  // A refusal that a newer chapter list explains asks for /api/me at once: a chapter closed meanwhile then leaves
  // the page, and a lowered limit is named rightly (48 UX3-5, UX3-6).
  st.store.set("rv.outbox", core.queueCreate([], Object.assign({}, c, { client_id: "z2" }), st.S.code, 0));
  answers = [[404, { error: "no_chapter", message: "x" }], [200, { id: 7, name: "Anan", limits: { text: 40 },
    books: [], chapters: [] }]];
  calls.length = 0;
  net.flush();
  await new Promise(r => setTimeout(r, 50));
  assert.deepStrictEqual(calls.map(x => x.method + " " + x.url), ["POST api/comments", "GET api/me"]);
  assert.strictEqual(st.S.me.limits.text, 40);
  assert.strictEqual(outbox()[0].failed.error, "no_chapter");
  st.store.set("rv.outbox", []);

  // Features: a place's entry shows only while its feature is on; an unknown feature is off.
  ext.feature({ name: "probe", variant: "pr" });
  ext.drawerPanel({ name: "probe-panel", feature: "probe", order: 5, hint: "hint_probe", render: () => null });
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

  // Sentence pairs: how the ranges cut a text's nodes. Two nodes of 5 and 6 code points; pair 0 covers
  // [0, 3), pair 1 covers [4, 9), which crosses from the first node into the second.
  const sentences = await import(pathToFileURL(path.join(__dirname, "..", "web", "features", "sentences.js")).href);
  assert.deepStrictEqual(sentences.pieces([5, 6], [[0, 3, 0], [4, 9, 1]]),
    [[[0, 3, 0], [3, 4, -1], [4, 5, 1]], [[0, 4, 1], [4, 6, -1]]]);
  assert.deepStrictEqual(sentences.pieces([4], []), [[[0, 4, -1]]]);
  assert.deepStrictEqual(sentences.pieces([2, 0, 2], [[0, 4, 0]]), [[[0, 2, 0]], [], [[0, 2, 0]]]);
  // The sentence module adds to english: on with English, off without it, and a sentence span is its mark.
  assert.strictEqual(ext.markFor("sentence", { features: { english: { on: true } } }).name, "sentences");
  assert.strictEqual(ext.markFor("sentence", { features: { english: { on: false } } }), null);
  assert.deepStrictEqual(ext.active("texts", { features: { english: { on: true } } }).map(d => d.name), ["sentences"]);

  console.log("ok");
})().catch(err => { console.error(err); process.exit(1); });

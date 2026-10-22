/* Checks of the page's plain modules in web/core/ (the outbox, the server's answers, the refusals and
   the feature places), run by test_core.py with node. Prints "ok" and exits 0 when every check passes. */
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

  // New comments on their way count against the limit; refused ones do not.
  assert.strictEqual(core.pendingCreates(core.queueCreate(core.queueCreate([], c, code, 0), Object.assign({}, c, { client_id: "c2" }), code, 0), code), 2);
  assert.strictEqual(core.pendingCreates(ob, code), 0);

  // Save checks the comment first and names the box to fix.
  const check = (kind, quote, text, isNew, total) => ref.checkComment({ kind, quote, text }, limits, isNew, total);
  assert.deepStrictEqual(check("flag", "", "", true, 0), { key: "need_text_flag", vars: {}, field: "text" });
  assert.strictEqual(check("wording", "", "x", true, 0).key, "need_quote");
  assert.strictEqual(check("flag", "", "\u200b\ufeff", true, 0).key, "need_text_flag");   // only invisible characters
  assert.deepStrictEqual(check("flag", "q".repeat(501), "x", true, 0), { key: "long_quote", vars: { n: 500 }, field: "quote" });
  assert.strictEqual(check("flag", "q".repeat(500), "x", true, 0), null);
  assert.deepStrictEqual(check("flag", "", "ก".repeat(4001), true, 0), { key: "long_text", vars: { n: 4000 }, field: "text" });
  assert.strictEqual(check("flag", "", "ก".repeat(4000), true, 0), null);
  assert.strictEqual(check("flag", "", "😀".repeat(4000), true, 0), null);   // characters, not UTF-16 units
  assert.deepStrictEqual(check("flag", "", "x", true, 5000), { key: "limit_reached", vars: { n: 5000 }, field: "" });
  assert.strictEqual(check("flag", "", "x", false, 5000), null);   // a change adds no comment
  assert.strictEqual(check("flag", "", "x", true, null), null);    // total unknown: the server decides
  assert.strictEqual(ref.counter("x".repeat(399), 500), null);
  assert.deepStrictEqual(ref.counter("x".repeat(400), 500), { n: 400, max: 500, over: false });
  assert.deepStrictEqual(ref.counter("x".repeat(501), 500), { n: 501, max: 500, over: true });

  // normMe keeps each book's language, the features, the limits and the reader's comment total.
  const me = model.normMe({ name: "R", books: [{ id: "GC", title_en: "G", language: "lo" }], chapters: [],
    features: { english: { on: true }, later: { on: false } }, limits: { quote: 100, text: 2000, comments: 9, writes_per_minute: 5 },
    comments_total: 4 });
  assert.deepStrictEqual(me.langs, { GC: "lo" });
  assert.deepStrictEqual(me.features, { english: { on: true }, later: { on: false } });
  assert.deepStrictEqual(me.limits, { quote: 100, text: 2000, comments: 9, writes_per_minute: 5 });
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
  assert.deepStrictEqual(two.chapters[0], { book: "SC", id: "SC01", n: 1, title_th: "a", title_en: "b", version: "v",
    count: 17, comments: 2, finished: true, place: "SC 9.1" });
  assert.deepStrictEqual(model.normChapter({ book: "SC", id: "SC01", n: 1, title_th: "t", title_en: "e", version: "v",
    paragraphs: [{ a: "SC 9.1", th: "x" }] }).paras, [{ a: "SC 9.1", th: "x", fn: [], en: "" }]);

  // A draft's key names its book, chapter and paragraph.
  assert.deepStrictEqual(store.parseDraftKey(store.draftKey("SC", "SC03", "SC 35.4")), { book: "SC", ch: "SC03", a: "SC 35.4" });
  assert.strictEqual(store.parseDraftKey("rv.cm:SC/SC03"), null);

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

  console.log("ok");
})().catch(err => { console.error(err); process.exit(1); });

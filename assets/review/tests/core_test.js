/* Checks of the plain functions at the top of web/app.js, run by test_core.py with node.
   Prints "ok" and exits 0 when every check passes. */
"use strict";
const assert = require("assert");
const path = require("path");
const core = require(path.join(__dirname, "..", "web", "app.js"));

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

// A 400 for a paragraph that is gone is also final; a 503 is tried again later.
let ob2 = core.queueCreate([], c, code, 0);
ob2 = core.settle(ob2, ob2[0].op, 0, core.classify("create", 400), { error: "bad_anchor" }, 400, 1);
assert.strictEqual(ob2[0].failed.error, "bad_anchor");
let ob3 = core.queueCreate([], c, code, 0);
ob3 = core.settle(ob3, ob3[0].op, 0, core.classify("create", 503), null, 503, 1);
assert.strictEqual(ob3[0].failed, null);
assert.strictEqual(ob3[0].tries, 1);

// Deleting a refused comment that never reached the server just drops it.
assert.deepStrictEqual(core.queueDelete(ob2, Object.assign({}, c, { id: null }), code, 5), []);

// normMe keeps each book's language.
const me = core.normMe({ name: "R", books: [{ id: "GC", title_en: "G", language: "lo" }], chapters: [] });
assert.deepStrictEqual(me.langs, { GC: "lo" });

console.log("ok");

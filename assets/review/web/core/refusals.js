/* Proofreading site: why a comment was not saved, in the reader's words (web/core/refusals.js).

   explain() turns the server's refusal of a comment into a message key of ui-strings.json and says
   which buttons help: Try again (retry) or Change (change). checkComment() catches the same problems
   before the comment is sent. Plain functions with no DOM: tests/core_test.js runs them with node.
   The codes are those of WRITE_ERRORS in server/app.py and README.md, "Why the server refuses". */

import { DEFAULT_LIMITS } from "./model.js";

/* A count is shown under a text box from this share of its limit on. */
export const NEAR = 0.8;

/* Characters as the server counts them (Unicode code points). The server also drops invisible
   characters first, so this count is the same or a little more, never less. */
export const chars = s => Array.from(String(s || "").trim()).length;

/* Characters the server removes from what readers type, among those a phone may insert. A box
   holding only these is empty to the server. The full list is in server/text.py. */
const INVISIBLE = /[\u00AD\u034F\u061C\u115F\u1160\u17B4\u17B5\u180B-\u180F\u200B-\u200F\u202A-\u202E\u2060-\u206F\u3164\uFE00-\uFE0F\uFEFF\uFFA0]/g;
export const blank = s => !String(s || "").replace(INVISIBLE, "").trim();

const lim = limits => Object.assign({}, DEFAULT_LIMITS, limits || {});

/* f is the `failed` record of an op: {status, error, message}. Returns {key, vars, retry, change}.
   A 413 without a code comes from Apache, which answers a body over 64 KiB itself. */
export function explain(f, limits) {
  const L = lim(limits);
  const code = (f && f.error) || "";
  const status = (f && f.status) || 0;
  if (code === "no_chapter" || (!code && status === 404)) return { key: "failed_closed", vars: {}, retry: true, change: false };
  if (code === "no_paragraph" || code === "bad_anchor" || (!code && status === 409)) return { key: "failed_paragraph", vars: {}, retry: false, change: false };
  if (code === "quote_required") return { key: "failed_quote_required", vars: {}, retry: false, change: true };
  if (code === "quote_too_long") return { key: "failed_quote_long", vars: { n: L.quote }, retry: false, change: true };
  if (code === "text_required") return { key: "failed_text_required", vars: {}, retry: false, change: true };
  if (code === "text_too_long" || code === "too_large" || (!code && status === 413)) return { key: "failed_text_long", vars: { n: L.text }, retry: false, change: true };
  if (code === "comment_limit") return { key: "failed_limit", vars: { n: L.comments }, retry: true, change: false };
  if (code === "no_comment") return { key: "failed_deleted", vars: {}, retry: false, change: false };
  return { key: "failed_refused", vars: {}, retry: true, change: false };   // a fault in the site or the page
}

/* What a waiting comment shows while the page tries again by itself, or "" for nothing. */
export function waitNote(why) {
  return why === "slow_down" ? "wait_slow" : "";
}

/* The check made when the reader taps Save. c = {kind, quote, text}; isNew is true for a new comment;
   total is the reader's comments counted so far, or null when unknown. Returns null when the comment
   may go, or {key, vars, field} naming the message and the box to fix ("quote", "text" or ""). */
export function checkComment(c, limits, isNew, total) {
  const L = lim(limits);
  if (blank(c.text)) return { key: c.kind === "wording" ? "need_text_wording" : "need_text_flag", vars: {}, field: "text" };
  if (c.kind === "wording" && blank(c.quote)) return { key: "need_quote", vars: {}, field: "quote" };
  if (chars(c.quote) > L.quote) return { key: "long_quote", vars: { n: L.quote }, field: "quote" };
  if (chars(c.text) > L.text) return { key: "long_text", vars: { n: L.text }, field: "text" };
  if (isNew && typeof total === "number" && total >= L.comments) return { key: "limit_reached", vars: { n: L.comments }, field: "" };
  return null;
}

/* The count under a text box: null while the text is short, else {n, max, over}. */
export function counter(text, max) {
  const n = chars(text);
  return n >= Math.floor(max * NEAR) ? { n, max, over: n > max } : null;
}

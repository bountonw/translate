/* Proofreading site: why a comment was not saved, in the reader's words (web/core/refusals.js).

   explain() turns the server's refusal of a comment into a message key of ui-strings.json and says
   which buttons help: Try again (retry) or Change (change). checkComment() catches the same problems
   before the comment is sent. Plain functions with no DOM: tests/core_test.js runs them with node.
   The codes are those of WRITE_ERRORS in server/app.py and README.md, "Reader routes"; slow_down
   and daily_limit (429) never refuse a comment for good, so waitNote() explains them instead. The page
   checks no count of the reader's comments: there is no limit on the comments a reader keeps, and the
   server alone counts the new comments of a day. */

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

/* f is the `failed` record of an op: {status, error, message, type}. Returns {key, vars, retry, change}.
   A 413 without a code comes from Apache, which answers a body over 64 KiB itself. A delete the server
   refused (type "delete") leaves the comment on the site, for the translator. */
export function explain(f, limits) {
  const L = lim(limits);
  const code = (f && f.error) || "";
  const status = (f && f.status) || 0;
  if (f && f.type === "delete") {
    if (code === "no_chapter" || (!code && status === 404)) return { key: "failed_delete_closed", vars: {}, retry: false, change: false };
    if (code === "round_closed") return { key: "failed_delete_round", vars: {}, retry: false, change: false };
  }
  if (code === "no_chapter" || (!code && status === 404)) return { key: "failed_closed", vars: {}, retry: true, change: false };
  if (code === "no_paragraph" || code === "bad_anchor" || (!code && status === 409)) return { key: "failed_paragraph", vars: {}, retry: false, change: false };
  if (code === "quote_required") return { key: "failed_quote_required", vars: {}, retry: false, change: true };
  if (code === "quote_too_long") return { key: "failed_quote_long", vars: { n: L.quote }, retry: false, change: true };
  if (code === "text_required") return { key: "failed_text_required", vars: {}, retry: false, change: true };
  if (code === "text_too_long" || code === "too_large" || (!code && status === 413)) return { key: "failed_text_long", vars: { n: L.text }, retry: false, change: true };
  // A server before round 3b refused the 5,001st comment of a reader with comment_limit.
  if (code === "comment_limit") return { key: "failed_limit", vars: { n: Number(L.comments) || 5000 }, retry: true, change: false };
  if (code === "no_comment") return { key: "failed_deleted", vars: {}, retry: false, change: false };
  if (code === "round_closed") return { key: "failed_round", vars: {}, retry: false, change: false };
  return { key: "failed_refused", vars: {}, retry: true, change: false };   // a fault in the site or the page
}

/* What a waiting comment shows while the page tries again by itself, as a key of ui-strings.json, or ""
   for nothing. daily_limit (429): the reader wrote limits.comments_per_day new comments today, a day that
   runs from midnight to midnight Thailand time; the comment waits on the device and goes by itself once the
   server takes it. The message shows only on a comment the server held back this way. */
export function waitNote(why) {
  if (why === "daily_limit") return "wait_daily";
  return why === "slow_down" ? "wait_slow" : "";
}

/* How long until the daily limit resets, from `now` to `until` (both in ms), in whole hours and minutes,
   the minutes rounded up so that the wait never shows as nothing: {h, m}, or null when the time is past or
   unknown. */
export function untilReset(until, now) {
  const left = Number(until) - Number(now);
  if (!(left > 0)) return null;
  const minutes = Math.ceil(left / 60000);
  return { h: Math.floor(minutes / 60), m: minutes % 60 };
}

/* The check made when the reader taps Save. c = {kind, quote, text}. Returns null when the comment may
   go, or {key, vars, field} naming the message and the box to fix ("quote" or "text"). */
export function checkComment(c, limits) {
  const L = lim(limits);
  if (blank(c.text)) return { key: c.kind === "wording" ? "need_text_wording" : "need_text_flag", vars: {}, field: "text" };
  if (c.kind === "wording" && blank(c.quote)) return { key: "need_quote", vars: {}, field: "quote" };
  if (chars(c.quote) > L.quote) return { key: "long_quote", vars: { n: L.quote }, field: "quote" };
  if (chars(c.text) > L.text) return { key: "long_text", vars: { n: L.text }, field: "text" };
  return null;
}

/* The count under a text box: null while the text is short, else {n, max, over}. */
export function counter(text, max) {
  const n = chars(text);
  return n >= Math.floor(max * NEAR) ? { n, max, over: n > max } : null;
}

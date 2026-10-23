/* Proofreading site: the plain rules of signing in (web/core/auth.js).

   What the page shows after each answer of the sign-in routes of server/auth.py (README.md, "Sign-in
   routes"), the checks it makes before it sends an email address or a code, and whether it shows the hint on
   adding the site to the Home Screen. Plain functions with no DOM: tests/core_test.js runs them with node.
   core/signin.js and core/account.js draw what these functions decide.

   A screen of signing in is one of these kinds, kept as `kind` in the context of core/signin.js:

     link    the welcome screen of a personal link (#k=), which ties the link to LINE or an address
     join    the request screen of a general link (#join=), which asks the translator for access
     signin  the sign-in screen, with no link
     add     a second way to sign in, from "Your devices" (core/account.js) */

/* The body of POST /api/auth/line/start and email/start for a screen of signing in. */
export function startBody(kind, code) {
  if (kind === "link") return { link: code };
  if (kind === "join") return { join: code };
  if (kind === "add") return { add: true };
  return {};
}

/* The six digits of the email code as six Western digits, or null. Spaces may stand between them, and Thai or
   Lao digits, typed on a Thai or Lao keyboard, count as the Western digits they stand for, as the server reads
   them. */
export function sixDigits(text) {
  const western = ch => {
    const n = ch.charCodeAt(0);
    if (n >= 0x0E50 && n <= 0x0E59) return String(n - 0x0E50);   // a Thai digit
    if (n >= 0x0ED0 && n <= 0x0ED9) return String(n - 0x0ED0);   // a Lao digit
    return ch;
  };
  const s = String(text || "").replace(/\s+/g, "").split("").map(western).join("");
  return /^[0-9]{6}$/.test(s) ? s : null;
}

/* Whether text is a whole email address, by the server's own pattern (server/mail.py, EMAIL_RE): before the @
   only A to Z, digits and . _ % + -. */
export function isAddress(text) {
  const s = String(text || "").trim();
  return s.length <= 254 && /^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,252}\.[A-Za-z]{2,63}$/.test(s);
}

/* What the page shows after a sign-in ends, for each result of server/auth.py (RESULTS): {screen, key}.
   screen is "list" (the chapter list), "account" (the settings' "Your devices"), "request" (the request
   screen of a general link, once the request is made), "signin" (the sign-in screen), "start" (the screen
   that started the sign-in, as it was when key is ""), "claim" (the claim of the personal link it started
   from says the screen again: the link signs in by itself now), "stopped" or "closed" (a general link that
   takes no more requests). key names the line of ui-strings.json the screen shows, or is "". */
const RESULTS = {
  signed_in: { screen: "list", key: "" },
  added: { screen: "account", key: "added" },
  request_sent: { screen: "request", key: "request_sent" },
  request_waiting: { screen: "request", key: "request_waiting" },
  request_declined: { screen: "request", key: "request_declined" },
  no_account: { screen: "signin", key: "line_no_account" },
  identity_taken: { screen: "start", key: "line_identity_taken" },
  link_used: { screen: "signin", key: "line_link_used" },
  link_signs_in: { screen: "claim", key: "" },
  stopped: { screen: "stopped", key: "" },
  join_closed: { screen: "closed", key: "" },
  join_busy: { screen: "start", key: "line_join_busy" },
  cancelled: { screen: "start", key: "" },
  expired: { screen: "start", key: "line_expired" },
  other_browser: { screen: "start", key: "line_other_browser" },
  failed: { screen: "start", key: "line_failed" },
};
export function afterSignIn(result) {
  return Object.prototype.hasOwnProperty.call(RESULTS, result) ? RESULTS[result] : { screen: "signin", key: "" };
}

/* What the page shows when a reader route answers 401 (server/app.py, ACCESS_ERRORS): {screen, key}, or null
   for a code the page does not know, which shows the screen of the mode (the link screen in link mode, else
   the sign-in screen). screen "claim" asks the claim route about the link kept on the device: its welcome
   screen while it still welcomes, else the sign-in screen. no_code right after a sign-in means the browser
   refused the cookie it was just given: the screen for blocked site data. */
const REFUSALS = {
  no_code: { screen: "signin", key: "" },
  signed_out: { screen: "signin", key: "line_signed_out" },
  stopped: { screen: "stopped", key: "" },
  bad_code: { screen: "link", key: "" },
  link_used: { screen: "signin", key: "line_link_used" },
  sign_in_required: { screen: "claim", key: "" },
};
export function afterRefusal(code, justSignedIn) {
  if (code === "no_code" && justSignedIn) return { screen: "blocked", key: "" };
  return Object.prototype.hasOwnProperty.call(REFUSALS, code) ? REFUSALS[code] : null;
}

/* The line for a refusal of a start or of the code (POST /api/auth/line/start, email/start, email/finish):
   {key, vars, screen}. screen is "" to stay on the screen, or "signin" (the link was used meanwhile, or the
   reader adding a way to sign in is signed out), "claim" (the link signs in by itself: its claim says the
   screen again), or "closed" (the general link takes no more requests). r = {status, data, wait} as api() of
   net.js gives it. A refusal of a limit names it ({limit: "day", "hour" or "wrong"}); otherwise a wait of more
   than two hours (Retry-After) is a daily limit and one of more than two minutes an hourly one. */
export function startRefusal(r) {
  const code = (r && r.data && typeof r.data.error === "string" && r.data.error) || "";
  const line = (key, vars, screen) => ({ key, vars: vars || {}, screen: screen || "" });
  if (!r || r.status === 0) return line("cannot_connect");
  if (code === "wrong_code") {
    const n = Number(r.data.tries_left) || 0;
    return line(n === 1 ? "wrong_code_one" : "wrong_code_many", { n });
  }
  if (code === "code_used_up") return line("code_used_up");
  if (code === "code_expired") return line("code_expired");
  if (code === "bad_email") return line("bad_email");
  if (code === "mail_failed") return line("mail_failed");
  if (code === "link_used") return line("line_link_used", {}, "signin");
  if (code === "link_signs_in") return line("", {}, "claim");
  if (code === "signed_out") return line("line_signed_out", {}, "signin");
  if (code === "join_closed") return line("", {}, "closed");
  if (code === "slow_down" || r.status === 429) {
    const limit = r.data && r.data.limit;
    if (limit === "wrong") return line("too_many_wrong");
    if (limit === "day" || (!limit && r.wait > 7200000)) return line("too_many_day");
    return line(limit === "hour" || r.wait > 120000 ? "too_many_hour" : "too_many");
  }
  return line("error_generic");
}

/* Whether the sign-in kept on the device (rv.flow, {kind, code, at}) is recent enough to be the one a LINE
   sign-in comes back from: LINE gives ten minutes, and the page allows a little more. */
export const FLOW_MS = 30 * 60000;
export const flowFresh = (flow, now) => !!flow && typeof flow.at === "number" && now - flow.at >= 0 && now - flow.at < FLOW_MS;

/* Whether the page shows the hint on adding the site to the Home Screen: in Safari on an iPhone or iPad, not
   in another browser there, such as Chrome or LINE's own, and not when the site already runs from the Home
   Screen (navigator.standalone). nav = {userAgent, platform, maxTouchPoints, standalone}. An iPad since iPadOS
   13 names itself a Mac, with a touch screen. */
export function wantsHomeHint(nav) {
  nav = nav || {};
  const ua = String(nav.userAgent || "");
  const apple = /iPhone|iPad|iPod/.test(ua) || (nav.platform === "MacIntel" && Number(nav.maxTouchPoints) > 1);
  const safari = /Version\/[\d.]+.*Safari\//.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS|OPT\/|GSA\/|Line\/|FBAN|FBAV|Instagram|YaBrowser|DuckDuckGo/.test(ua);
  return apple && safari && nav.standalone !== true;
}

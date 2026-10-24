/* Proofreading site: signing in (web/core/signin.js).

   The screens before a reader is signed in (README.md, "One person per account"), drawn from the answers of
   the sign-in routes of server/auth.py; core/auth.js holds the rules that decide which screen and which line:

     - the welcome screen of a personal link (#k=): "Continue with LINE", the smaller "Use your email instead",
       and "Continue without signing in" while the link alone still works for the reader. In a browser signed in
       as another reader it comes in two steps: first "Continue as" the reader signed in, or "Sign in as" the
       link's reader, each button naming its person; then the welcome screen, which says that the reader signed
       in is signed out on this browser, with "Continue as" that reader as its small button;
     - the sign-in screen, for a browser that is not signed in, a link that was used, a browser signed out, or
       a LINE account or address that no reader uses;
     - the request screen of a general link (#join=), which asks the translator for access, and the screens
       after it: the request went, it still waits, or it was declined; a link that takes no more requests shows
       the sign-in screen with a line that says so;
     - the email form: the address, then the six-digit code, with the refusals under the field;
     - the screens of a reader whose access is stopped, and of a browser that blocks the site's data;
     - on the dev server alone, "Enter as <reader>".

   A sign-in with LINE leaves the page for LINE and comes back as /#auth=RESULT. Before it leaves, the page
   keeps the screen it started from in rv.flow ({kind, code, at}), so that a sign-in that was cancelled or
   failed comes back to that screen. The link's code goes to the site in a request's body, never in an
   address. After a sign-in the page forgets the link (rv.code): it was used, and the session cookie, which
   the page never sees, signs the browser in from then on. */

import { upgradeMe } from "./model.js";
import { applyPending } from "./outbox.js";
import { S, store } from "./state.js";
import { K, linkTag } from "./store.js";
import { t } from "./words.js";
import { h, $ } from "./dom.js";
import { api, refreshMe, flush, forgetReader, adoptReader, noteLink, loadOb, who, authFailed } from "./net.js";
import { startBody, sixDigits, isAddress, afterSignIn, afterRefusal, startRefusal, flowFresh } from "./auth.js";
import { route, showScreen, settingsBar, setHash, showLink, showOffline, showBoot } from "./screens.js";
import { showAccount } from "./account.js";

/* The screen of signing in shown now: {kind, code, id, name, skip, routes, signedIn, chosen, line, email, draw},
   where kind is link, join, signin or add (core/auth.js), chosen is true once the reader chose "Sign in as" the
   link's reader (or the screen came back from LINE with a line), line is {key, vars, bad} or null, and email is the
   state of the email form, {stage: "address" or "code", address, code, error}, or null; address and code keep
   what the reader typed, so that a change of language keeps it. draw() draws the screen again. */
let ctx = null;
/* A function that draws the screen of signing in shown now again, as after a change of language. */
let shown = null;

/* ---- what the site says before signing in ---- */

/* GET /api/auth/state, kept in S.auth: whether the browser is signed in, the routes switched on, dev, and the
   reader's identities. Returns the answer, or null when the site cannot be reached. */
export async function loadAuthState() {
  const r = await api("GET", "api/auth/state", { page: true });
  if (r.status === 200 && r.data && r.data.routes) {
    S.auth = r.data;
    return r.data;
  }
  return null;
}

/* How the device was used last: in link mode with the link it keeps (rv.code), or signed in as the reader whose
   chapter list it keeps (rv.reader). boot() calls it when the address holds no link and no sign-in result, so
   that the chapter list kept on the device shows at once, also offline. */
export function keptMode() {
  const code = store.get(K.code);
  const links = store.get(K.links) || {};
  if (typeof code === "string" && code) {
    S.mode = "link";
    S.code = code;
    const n = links[linkTag(code)];
    S.reader = typeof n === "number" ? n : null;
  } else if (typeof store.get(K.reader) === "number") {
    S.mode = "session";
    S.reader = store.get(K.reader);
  }
}

/* ---- the start ---- */

/* What the page shows first, after boot() in core/main.js. hash = {link, join, result}, read from the address
   (#k=, #join=, #auth=). */
export function startAuth(hash) {
  if (store.blocked) return showBlocked();
  if (hash.result) return comeBack(hash.result);
  if (hash.link) return openLink(hash.link, null);
  if (hash.join) return openJoin(hash.join, null);
  if (S.mode) return resumeKept();
  // Nobody signed in on this device: the screen of a link or a general link the reader had open, or sign in.
  const flow = store.get(K.flow);
  if (flow && flow.kind === "link" && flow.code) return openLink(flow.code, null);
  if (flow && flow.kind === "join" && flow.code) return openJoin(flow.code, null);
  return signInScreen(null);
}

/* The device was signed in, or in link mode: draw the chapter list it keeps, and ask the site in the
   background. */
function resumeKept() {
  store.del(K.flow);
  // The ops and drafts written under the reader's links become the reader's before anything is drawn.
  if (typeof S.reader === "number") adoptReader(S.reader);
  const me = upgradeMe(store.get(K.me));
  S.me = me && (me.id === null || S.reader === null || me.id === S.reader) ? applyPending(me, loadOb(), who()) : null;
  route();
  refreshMe();
  flush();
  if (S.mode === "session") loadAuthState();
}

/* A personal link: what its claim says. line, when given, is the line to show on its welcome screen, as after
   a LINE sign-in that came back without signing in. */
export async function openLink(code, line) {
  showBoot();
  const r = await api("POST", "api/auth/claim", { page: true, body: { link: code } });
  if (r.status === 0) return showOffline(() => openLink(code, line));
  if (r.status === 401 || r.status === 400) {
    // An old link, as one kept in a LINE chat after a new link came: a browser signed in goes to its chapter
    // list, and any other shows the sign-in screen with the line "This link does not work";
    // with no sign-in route on, the link screen shows as before accounts.
    forgetLink(code);
    return signInScreen({ key: "link_title", vars: {}, bad: false });
  }
  if (r.status !== 200 || !r.data) return showProblem(r.status === 429 ? "too_many" : "error_generic", () => openLink(code, line));
  const d = r.data;
  if (typeof d.id === "number") noteLink(code, d.id);
  // This browser is signed in as the link's reader already.
  if (d.signed_in && d.signed_in.id === d.id) return enterSession(d.id, false);
  if (d.state === "link") return enterLink(code, d.id);
  if (d.state === "used") {
    forgetLink(code);
    return signInScreen({ key: "line_link_used" });
  }
  store.set(K.flow, { kind: "link", code, at: Date.now() });
  showAuth({ kind: "link", code, id: d.id, name: d.name || "", skip: d.skip === true, routes: d.routes || {},
    signedIn: d.signed_in || null, chosen: !!line, line });
}

/* A general link: whether it still takes requests. */
export async function openJoin(code, line) {
  showBoot();
  const r = await api("POST", "api/auth/join", { page: true, body: { join: code } });
  if (r.status === 0) return showOffline(() => openJoin(code, line));
  if (r.status !== 200 || !r.data) return showProblem(r.status === 429 ? "too_many" : "error_generic", () => openJoin(code, line));
  const d = r.data;
  if (d.signed_in && typeof d.signed_in.id === "number") return enterSession(d.signed_in.id, false);
  if (d.state !== "open") {
    forgetLink(code);
    return showClosed();
  }
  store.set(K.flow, { kind: "join", code, at: Date.now() });
  showAuth({ kind: "join", code, routes: d.routes || {}, line });
}

/* The sign-in screen. line is {key, vars, bad} or null. A browser that is signed in after all goes to its
   chapter list; with no sign-in route switched on, the site works as before accounts and shows the link screen. */
export async function signInScreen(line) {
  S.mode = null;
  S.code = null;
  S.reader = null;
  S.authBlocked = false;
  showBoot();
  const st = await loadAuthState();
  if (!st) return showOffline(() => signInScreen(line));
  if (st.signed_in && st.account && typeof st.account.id === "number") return enterSession(st.account.id, false);
  if (!st.routes.line && !st.routes.email) return showLink();
  showAuth({ kind: "signin", routes: st.routes, line });
}

/* Back from LINE with /#auth=RESULT. The screen the sign-in started from is the one kept in rv.flow. */
function comeBack(result) {
  const flow = store.get(K.flow);
  const from = flowFresh(flow, Date.now()) ? flow : null;
  const what = afterSignIn(result);
  const line = what.key ? { key: what.key, vars: {}, bad: what.screen === "start" || what.screen === "signin" } : null;
  if (what.screen === "list") return enterSession(null, true);
  if (what.screen === "claim") return from && from.kind === "link" ? openLink(from.code, null) : signInScreen(null);
  if (what.screen === "start" && from && from.kind === "link") return openLink(from.code, line);
  if (what.screen === "start" && from && from.kind === "join") return openJoin(from.code, line);
  if ((what.screen === "start" || what.screen === "account") && from && from.kind === "add") return backToAccount(line);
  if (what.screen === "account") return backToAccount(line);
  store.del(K.flow);
  if (what.screen === "signin" && from && from.kind === "link" && result === "link_used") forgetLink(from.code);
  if (what.screen === "request") return showRequestDone(what.key);
  if (what.screen === "stopped") return showStopped();
  if (what.screen === "closed") return showClosed();
  return signInScreen(line);
}

/* The reader added a way to sign in, or tried to: "Your devices", with the chapter list of the session behind. */
function backToAccount(line) {
  store.del(K.flow);
  keptMode();
  if (S.mode !== "session") return signInScreen(line);
  const me = upgradeMe(store.get(K.me));
  S.me = me && me.id === S.reader ? me : null;
  refreshMe();
  flush();
  showAccount(false, line);
}

/* ---- signed in ---- */

/* This browser is signed in, as reader `id` (null when only /api/me will say, as after LINE or the email code).
   fresh is true right after a sign-in: a 401 no_code from /api/me then means the browser refused the cookie. */
export function enterSession(id, fresh) {
  S.mode = "session";
  S.code = null;
  store.del(K.code);
  store.del(K.flow);
  S.authBlocked = false;
  S.deviceWaiting = false;
  S.justSignedIn = !!fresh;
  ctx = null;
  shown = null;
  setHash("", false);
  S.reader = null;
  S.me = null;
  if (typeof id === "number") {
    adoptReader(id);
    const me = upgradeMe(store.get(K.me));
    if (me && me.id === id) S.me = applyPending(me, loadOb(), who());
  }
  route();
  refreshMe();
  flush();
  loadAuthState();
}

/* Link mode, as before accounts: the link signs in by itself, with the two-device lock (README.md, "Link signs
   in"). id is the link's reader number from its claim. */
export function enterLink(code, id) {
  const before = store.get(K.code);
  S.mode = "link";
  S.code = code;
  S.authBlocked = false;
  S.justSignedIn = false;
  ctx = null;
  shown = null;
  store.del(K.flow);
  if (code !== before) {
    // A new link: what the device keeps for reading goes, unless it is the same reader's.
    if (!(typeof id === "number" && store.get(K.reader) === id)) forgetReader();
    store.set(K.code, code);
  }
  S.reader = null;
  S.me = null;
  if (typeof id === "number") adoptReader(id);
  const me = upgradeMe(store.get(K.me));
  if (me && (me.id === null || me.id === S.reader)) S.me = applyPending(me, loadOb(), who());
  route();
  refreshMe();
  flush();
}

/* The device forgets a link that does not sign in any more: as rv.code, and as the screen kept in rv.flow. */
function forgetLink(code) {
  if (store.get(K.code) === code) store.del(K.code);
  const flow = store.get(K.flow);
  if (flow && flow.code === code) store.del(K.flow);
}

/* A reader route answered 401 (net.js, authFailed): the screen the code calls for (core/auth.js,
   afterRefusal). The outbox and the drafts stay on the device. */
export function onRefused(code) {
  const what = afterRefusal(code, S.justSignedIn);
  S.justSignedIn = false;
  if (!what) return S.mode === "link" ? showLink() : signInScreen(null);
  if (what.screen === "blocked") return showBlocked();
  if (what.screen === "link") return showLink();
  if (what.screen === "stopped") return showStopped();
  // The link kept for link mode no longer signs in by itself: its claim says which screen comes now (its welcome
  // screen, or the sign-in screen with the line that the link was used), and names the link's reader, so that the
  // comments written under the link stay that reader's.
  if ((what.screen === "claim" || code === "link_used") && S.mode === "link" && S.code) return openLink(S.code, null);
  if (S.mode === "session") store.del(K.reader);
  return signInScreen(what.key ? { key: what.key, vars: {}, bad: false } : null);
}

/* The screen of signing in again, as when the address changes while it shows. */
export function showAuthAgain() {
  if (shown) shown();
  else signInScreen(null);
}

/* Draw the screen of signing in again in the language now chosen. */
export function redrawAuth() {
  if (shown) shown();
}

/* ---- the screens ---- */

function showAuth(c) {
  ctx = c;
  c.draw = drawAuth;
  shown = drawAuth;
  drawAuth();
}

/* Lines that say on their own what to do, so the sign-in screen leaves out its lead under them: after a used link
   the lead, which says to open the personal link, would send the reader in a circle, and a
   person who asked through a general link has no personal link. */
const SELF_SAID = ["line_link_used", "join_closed_signin"];

/* A line under the title: why the screen shows, or what a sign-in ended in. */
const lineOf = line => (line && line.key ? h("p", { class: "lead auth-line" + (line.bad ? " bad" : ""), role: "status", text: t(line.key, line.vars) }) : null);

/* Whether the browser is signed in as another reader than the one of the link on the screen. */
const otherReader = c => c.kind === "link" && !!c.signedIn && typeof c.signedIn.id === "number" && c.signedIn.id !== c.id;

function drawAuth() {
  const c = ctx;
  if (!c) return;
  const other = otherReader(c);
  const otherName = other ? c.signedIn.name || "" : "";
  // Another reader is signed in: first ask who is reading, each button naming its person, so that nobody signs the
  // other reader out by mistake.
  if (other && !c.chosen && !c.email) {
    showScreen("signin", h("section", { class: "message auth" },
      h("div", { class: "home-top" }, h("h1", { text: t("link_for", { name: c.name }) }), settingsBar("signin")),
      h("p", { class: "lead", text: t("signed_in_as", { name: otherName }) }),
      h("div", { class: "auth-choices" },
        h("button", { type: "button", class: "btn", text: t("continue_as", { name: otherName }),
          onclick: () => enterSession(c.signedIn.id, false) }),
        h("button", { type: "button", class: "btn ghost", text: t("signin_as", { name: c.name }),
          onclick: () => { c.chosen = true; c.draw(); } })),
      devBox()));
  } else {
    const title = c.kind === "link" ? t("welcome_title", { name: c.name }) : c.kind === "join" ? t("request_title") : t("signin_title");
    const lead = c.kind === "link" ? t("welcome_text") : c.kind === "join" ? t("request_text") : t("signin_text");
    showScreen("signin", h("section", { class: "message auth" },
      h("div", { class: "home-top" }, h("h1", { text: title }), settingsBar("signin")),
      lineOf(c.line),
      // In the email form the welcome stays, while the sign-in screen's and the request screen's own words give way.
      (!c.email || c.kind === "link") && !(c.line && SELF_SAID.indexOf(c.line.key) >= 0) ? h("p", { class: "lead", text: lead }) : null,
      other ? h("p", { class: "lead", text: t("signs_out_other", { name: otherName }) }) : null,
      c.email ? emailForm(c) : choices(c),
      devBox()));
  }
  if (!S.auth) loadAuthState().then(st => { if (st && st.dev && shown === drawAuth && ctx === c && !c.email) drawAuth(); });
}

/* "Continue with LINE", "Use your email instead", and the small button of the welcome screen: "Continue as" the
   reader signed in on this browser, or "Continue without signing in" while the link alone still works. */
function choices(c) {
  const box = h("div", { class: "auth-choices" });
  if (c.routes.line) {
    const btn = h("button", { type: "button", class: "btn line-btn", text: t("line_continue") });
    btn.addEventListener("click", () => startLine(c, btn));
    box.append(btn);
  }
  if (c.routes.email) {
    // Under the LINE button the email is the other way; with LINE switched off it is the only one.
    const only = !c.routes.line;
    box.append(h("button", { type: "button", class: only ? "btn" : "btn ghost", text: only ? t("email_continue") : t("email_use"), onclick: () => {
      c.email = { stage: "address", address: "", error: null };
      c.draw();
      focusField();
    } }));
  }
  // The browser is signed in as another reader: "Continue as" that reader keeps it so and opens that reader's
  // chapter list. Otherwise "Continue without signing in" goes on
  // in link mode while the link alone still works.
  if (otherReader(c)) {
    box.append(h("button", { type: "button", class: "link skip-btn", text: t("continue_as", { name: c.signedIn.name || "" }),
      onclick: () => enterSession(c.signedIn.id, false) }));
  } else if (c.kind === "link" && c.skip) {
    box.append(h("button", { type: "button", class: "link skip-btn", text: t("skip_now"), onclick: () => enterLink(c.code, c.id) }));
  }
  return box;
}

const focusField = () => {
  const f = document.querySelector("#main .auth-field");
  if (f) f.focus();
};

/* Start a sign-in with LINE from the screen of c: the site gives LINE's address, and the page goes there. The
   screen is kept in rv.flow for the way back. A refusal shows on the screen (c.line), or on "Your devices" for
   a way added there. */
export async function startLine(c, btn) {
  if (btn) btn.disabled = true;
  const r = await api("POST", "api/auth/line/start", { page: true, body: startBody(c.kind, c.code) });
  if (r.status === 200 && r.data && typeof r.data.url === "string") {
    store.set(K.flow, { kind: c.kind, code: c.code || "", at: Date.now() });
    location.href = r.data.url;
    return;
  }
  if (btn) btn.disabled = false;
  refused(c, startRefusal(r));
}

/* A refusal of a start or of the code (core/auth.js, startRefusal). */
function refused(c, ref) {
  if (ref.screen === "closed") return showClosed();
  if (ref.screen === "claim") return c.kind === "link" ? openLink(c.code, null) : signInScreen(null);
  if (ref.screen === "signin") {
    if (c.kind === "link") forgetLink(c.code);
    if (c.kind === "add") authFailed("signed_out");
    else signInScreen({ key: ref.key, vars: ref.vars, bad: false });
    return;
  }
  if (c.email) c.email.error = { key: ref.key, vars: ref.vars };
  else c.line = { key: ref.key, vars: ref.vars, bad: true };
  c.draw();
  if (c.email) focusField();
}

/* The email form of the screen of c: the address, then the code. */
export function emailForm(c) {
  const e = c.email;
  const error = e.error ? h("p", { class: "status bad auth-error", role: "alert", text: t(e.error.key, e.error.vars) }) : null;
  if (e.stage === "address") {
    const input = h("input", { class: "auth-field", type: "email", name: "email", autocomplete: "email", inputmode: "email",
      autocapitalize: "off", spellcheck: "false", value: e.address || "" });
    input.addEventListener("input", () => { e.address = input.value; });
    const send = h("button", { type: "submit", class: "btn", text: t("email_send") });
    const f = h("form", { class: "auth-form", novalidate: true },
      h("label", { class: "field" }, h("span", { text: t("email_label") }), input),
      error,
      h("div", { class: "row" }, send,
        h("button", { type: "button", class: "btn ghost", text: t("cancel"), onclick: () => { c.email = null; c.draw(); } })));
    f.addEventListener("submit", ev => {
      ev.preventDefault();
      const address = input.value.trim();
      if (!isAddress(address)) {
        e.address = input.value;
        e.error = { key: "bad_email", vars: {} };
        c.draw();
        focusField();
        return;
      }
      sendCode(c, address, send);
    });
    return f;
  }
  const input = h("input", { class: "auth-field code-field", type: "text", name: "code", autocomplete: "one-time-code",
    inputmode: "numeric", maxlength: "20", spellcheck: "false", value: e.code || "" });
  input.addEventListener("input", () => { e.code = input.value; });
  const go = h("button", { type: "submit", class: "btn", text: c.kind === "add" ? t("email_add") : t("email_signin") });
  const again = h("button", { type: "button", class: "link", text: t("email_new_code") });
  again.addEventListener("click", () => sendCode(c, e.address, again));
  const f = h("form", { class: "auth-form", novalidate: true },
    h("p", { class: "lead", text: c.kind === "signin" ? t("email_sent_signin", { address: e.address }) : t("email_sent", { address: e.address }) }),
    h("p", { class: "hint", text: t("email_spam") }),
    h("label", { class: "field" }, h("span", { text: t("code_label") }), input),
    error,
    // Cancel closes the form, as on the address step, since the browser's Back leaves the site.
    h("div", { class: "row" }, go,
      h("button", { type: "button", class: "btn ghost", text: t("cancel"), onclick: () => { c.email = null; c.draw(); } })),
    h("div", { class: "row" }, again,
      h("button", { type: "button", class: "link", text: t("email_other"), onclick: () => {
        c.email = { stage: "address", address: e.address, error: null };
        c.draw();
        focusField();
      } })));
  f.addEventListener("submit", ev => {
    ev.preventDefault();
    const digits = sixDigits(input.value);
    if (!digits) {
      e.error = { key: "code_six", vars: {} };
      c.draw();
      focusField();
      return;
    }
    finishCode(c, digits, go);
  });
  return f;
}

/* Ask the site to send a code to `address`. The button waits while the request is out, so one tap sends one
   code: each code counts toward the codes one address may receive in a day (server/auth.py, CODES_PER_CLIENT_DAY
   and CODES_PER_DAY). */
async function sendCode(c, address, btn) {
  if (c.email.busy) return;
  c.email.busy = true;
  if (btn) btn.disabled = true;
  const r = await api("POST", "api/auth/email/start", { page: true, body: Object.assign({ email: address }, startBody(c.kind, c.code)) });
  c.email.busy = false;
  if (btn) btn.disabled = false;
  if (r.status === 200) {
    c.email = { stage: "code", address, error: null };
    c.line = null;
    c.draw();
    focusField();
    return;
  }
  c.email.address = address;
  refused(c, startRefusal(r));
}

/* Send the six digits. */
async function finishCode(c, digits, btn) {
  if (c.email.busy) return;
  c.email.busy = true;
  if (btn) btn.disabled = true;
  const r = await api("POST", "api/auth/email/finish", { page: true, body: { code: digits } });
  c.email.busy = false;
  if (btn) btn.disabled = false;
  if (r.status === 200 && r.data && typeof r.data.result === "string") return finished(c, r.data.result);
  refused(c, startRefusal(r));
}

/* A sign-in with the email code ended in `result` (core/auth.js, afterSignIn). */
function finished(c, result) {
  const what = afterSignIn(result);
  const line = what.key ? { key: what.key, vars: {}, bad: what.screen === "start" || what.screen === "signin" } : null;
  if (what.screen === "list") return enterSession(null, true);
  if (what.screen === "claim") return c.kind === "link" ? openLink(c.code, null) : signInScreen(null);
  if (c.kind === "add" && (what.screen === "account" || what.screen === "start")) return showAccount(false, line);
  if (what.screen === "request") return showRequestDone(what.key);
  if (what.screen === "stopped") return showStopped();
  if (what.screen === "closed") return showClosed();
  if (what.screen === "signin") {
    if (c.kind === "link" && result === "link_used") forgetLink(c.code);
    return signInScreen(line);
  }
  c.email = null;
  c.line = line;
  c.draw();
}

/* After a request through a general link: it went to the translator, it still waits, or it was declined. */
function showRequestDone(key) {
  store.del(K.flow);
  ctx = null;
  shown = () => showRequestDone(key);
  showScreen("signin", h("section", { class: "message auth" },
    h("div", { class: "home-top" }, h("h1", { text: t("request_title") }), settingsBar("signin")),
    h("p", { class: "lead", text: t(key) }),
    key === "request_declined" ? null : h("p", { class: "lead", text: t("request_later") }),
    h("div", { class: "row" }, h("button", { type: "button", class: "btn ghost", text: t("signin_title"), onclick: () => signInScreen(null) }))));
}

/* A general link that takes no more requests: the sign-in screen, with a line that says so. A person who asked
   through it already signs in there and sees the chapters once approved, or that the request still waits, or
   that it was declined. */
function showClosed() {
  store.del(K.flow);
  return signInScreen({ key: "join_closed_signin", vars: {}, bad: false });
}

/* The reader's access is stopped. The reader's waiting comments stay on the device. "Try again" asks the site
   again, so that a reader let back in reaches the chapter list without reloading the page, which a site opened
   from the Home Screen cannot do: signed in or in link mode, /api/me answers; with no mode,
   as after a LINE sign-in that ended in stopped, the sign-in screen shows. */
function showStopped() {
  ctx = null;
  shown = showStopped;
  showScreen("signin", h("section", { class: "message auth" },
    h("div", { class: "home-top" }, h("h1", { text: t("app_title") }), settingsBar("signin")),
    h("p", { class: "lead", text: t("stopped") }),
    h("div", { class: "row" }, h("button", { type: "button", class: "btn ghost", text: t("retry_load"), onclick: tryStoppedAgain }))));
}

function tryStoppedAgain() {
  if (!S.mode) return signInScreen(null);
  S.authBlocked = false;
  showBoot();
  refreshMe();
}

/* The browser refuses the site's data: the page sends nothing, since it could keep no comment waiting, and a link
   would count this browser as a new device on every visit. */
export function showBlocked() {
  ctx = null;
  shown = showBlocked;
  showScreen("blocked", h("section", { class: "message auth" },
    h("div", { class: "home-top" }, h("h1", { text: t("app_title") }), settingsBar("blocked")),
    h("p", { class: "lead", text: t("blocked") }),
    // After the reader allows the site's data in the browser's settings, the page starts again.
    h("div", { class: "row" }, h("button", { type: "button", class: "btn ghost", text: t("retry_load"), onclick: () => location.reload() }))));
}

/* A refusal before any screen of signing in could show, with Try again. */
function showProblem(key, again) {
  ctx = null;
  shown = () => showProblem(key, again);
  showScreen("signin", h("section", { class: "message auth" },
    h("div", { class: "home-top" }, h("h1", { text: t("app_title") }), settingsBar("signin")),
    h("p", { class: "lead", text: t(key) }),
    h("button", { type: "button", class: "btn", text: t("retry_load"), onclick: again })));
}

/* ---- the dev server alone: "Enter as <reader>" ---- */

let devReaders = null;

/* The readers of the dev server, each a button that signs this browser in as that reader. /api/auth/state says
   dev: true on the dev server alone, and the live site answers /api/dev/ with 404, so this never shows there. */
function devBox() {
  if (!S.auth || S.auth.dev !== true) return null;
  const box = h("div", { class: "dev-box" });
  const fill = list => {
    box.textContent = "";
    for (const r of list) {
      if (!r || typeof r.id !== "number") continue;
      box.append(h("button", { type: "button", class: "link", text: t("dev_enter", { name: r.name || String(r.id) }), onclick: () => devEnter(r.id) }));
    }
  };
  if (devReaders) fill(devReaders);
  else {
    api("GET", "api/dev/readers", { page: true }).then(r => {
      if (r.status === 200 && r.data && Array.isArray(r.data.readers)) {
        devReaders = r.data.readers;
        if (box.isConnected) fill(devReaders);
      }
    });
  }
  return box;
}

async function devEnter(id) {
  const r = await api("POST", "api/dev/enter", { page: true, body: { reader: id } });
  if (r.status === 200 && r.data && typeof r.data.id === "number") return enterSession(r.data.id, true);
  const box = $("main").querySelector(".dev-box");
  if (box) box.append(h("p", { class: "status bad", text: t("error_generic") }));
}

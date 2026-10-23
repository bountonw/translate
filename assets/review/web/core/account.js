/* Proofreading site: "Your devices" (web/core/account.js).

   For a reader signed in with LINE or an email code (S.mode "session"), the settings at the top of the chapter
   list offer "Your devices", a screen at the address #account:

     - the browsers where the reader is signed in now (GET /api/auth/sessions), newest visit first, each with
       the browser, the day it was last used, and "Sign out", or "This browser" for this one;
     - the ways the reader signs in ("LINE: <name>", "Email: <address>"), with "Add LINE" or "Add an email
       address" for a kind the reader lacks, which ties one more way to the reader (`add: true`);
     - "Sign out" of this browser (POST /api/auth/logout). The reader's waiting comments stay on the device
       and go once the reader signs in on this browser again.

   In link mode there are no sessions, and the item does not show. */

import { ownerOf } from "./outbox.js";
import { S, store } from "./state.js";
import { K } from "./store.js";
import { t, dateText } from "./words.js";
import { h, twoTapButton } from "./dom.js";
import { settingsItem } from "./ext.js";
import { api, loadOb, forgetReader, authFailed, who } from "./net.js";
import { setHash, setBar, showScreen, goHome } from "./screens.js";
import { loadAuthState, signInScreen, startLine, emailForm } from "./signin.js";

settingsItem({
  name: "account",
  order: 5,
  render: ctx => (ctx.screen === "home" && S.mode === "session"
    ? h("button", { type: "button", class: "tool-btn", id: "devices-btn", text: t("devices_title"), onclick: () => showAccount(true, null) })
    : null),
});

/* What the screen shows: {sessions, failed, line, add}. sessions is the list of GET /api/auth/sessions, or null
   while it loads; failed is a key of ui-strings.json when it could not be had; line is {key, vars, bad} or
   null; add is the context of the email form for adding an address (core/signin.js), or null. */
let view = null;

/* Show "Your devices". push is true when the reader opened it from the chapter list, so that the browser's back
   button returns there. line, when given, says what a way of signing in just added ended in. */
export function showAccount(push, line) {
  if (push) setHash("#account", true);
  else if (location.hash !== "#account") setHash("#account", false);
  view = { sessions: null, failed: "", line: line || null, add: null };
  draw();
  load();
}

/* Draw the screen again in the language now chosen. */
export function redrawAccount() {
  if (view) draw();
}

async function load() {
  const mine = view;
  const [r] = await Promise.all([api("GET", "api/auth/sessions", { page: true }), loadAuthState()]);
  if (view !== mine || S.view !== "account") return;
  if (r.status === 401) return authFailed(r.data && r.data.error);
  if (r.status === 200 && r.data && Array.isArray(r.data.sessions)) {
    mine.sessions = r.data.sessions;
    mine.failed = "";
  } else mine.failed = r.status === 0 ? "cannot_connect" : "error_generic";
  draw();
}

function draw() {
  const v = view;
  showScreen("account", h("section", { class: "message account" },
    h("h1", { text: t("devices_title") }),
    v.line && v.line.key ? h("p", { class: "lead auth-line" + (v.line.bad ? " bad" : ""), role: "status", text: t(v.line.key, v.line.vars) }) : null,
    devices(v),
    ways(v),
    signOutBlock(),
    h("div", { class: "row" }, h("button", { type: "button", class: "btn ghost", text: t("all_chapters"), onclick: goHome }))));
  setBar(null, t("devices_title"));
}

/* The browsers signed in now. */
function devices(v) {
  if (v.failed) {
    return h("div", { class: "devices" }, h("p", { class: "lead", text: t(v.failed) }),
      h("div", { class: "row" }, h("button", { type: "button", class: "btn", text: t("retry_load"), onclick: () => { v.failed = ""; draw(); load(); } })));
  }
  if (!v.sessions) return h("p", { class: "lead loading", text: t("loading") });
  return h("ul", { class: "devices" }, v.sessions.map(s => {
    const date = dateText(s.last_seen);
    return h("li", { class: "device" + (s.current ? " current" : "") },
      h("span", { class: "device-name", text: typeof s.agent === "string" && s.agent ? s.agent : t("device_unknown") }),
      h("span", { class: "device-when", text: date ? t("last_used", { date }) : "" }),
      s.current
        ? h("span", { class: "chip reading", text: t("this_browser") })
        : twoTapButton(t("sign_out"), t("sign_out_confirm"), () => endOne(s.id)));
  }));
}

/* Sign out another browser of the reader's. */
async function endOne(id) {
  const r = await api("DELETE", "api/auth/sessions/" + encodeURIComponent(id), { page: true });
  if (r.status === 401) return authFailed(r.data && r.data.error);
  if (r.status !== 200 && r.status !== 404) {
    view.line = { key: r.status === 0 ? "cannot_connect" : "error_generic", vars: {}, bad: true };
    return draw();
  }
  view.line = null;
  view.sessions = null;
  draw();
  load();
}

/* The ways the reader signs in, and the buttons that add one of a kind the reader lacks. */
function ways(v) {
  const st = S.auth || {};
  const list = Array.isArray(st.identities) ? st.identities : [];
  const has = kind => list.some(x => x && x.provider === kind);
  const routes = st.routes || {};
  const add = h("div", { class: "row" });
  if (routes.line && !has("line")) {
    const btn = h("button", { type: "button", class: "btn ghost", text: t("add_line") });
    btn.addEventListener("click", () => startLine(addContext(v), btn));
    add.append(btn);
  }
  if (routes.email && !has("email") && !v.add) {
    add.append(h("button", { type: "button", class: "btn ghost", text: t("add_email"), onclick: () => {
      const c = addContext(v);
      c.email = { stage: "address", address: "", error: null };
      draw();
      const f = document.querySelector("#main .auth-field");
      if (f) f.focus();
    } }));
  }
  return h("section", { class: "ways" },
    h("h2", { text: t("ways_title") }),
    list.length ? h("ul", { class: "devices" }, list.map(x => h("li", { class: "device" },
      h("span", { class: "device-name", text: t(x.provider === "line" ? "way_line" : "way_email", { name: x.display || "" }) })))) : null,
    v.add && v.add.email ? emailForm(v.add) : null,
    add.childNodes.length ? add : null);
}

/* The context of the email form or the LINE sign-in that adds a way to sign in (core/signin.js). A refusal it
   meets shows as the screen's line. */
function addContext(v) {
  if (!v.add) {
    v.add = { kind: "add", code: "", email: null, line: null, draw: () => {
      if (v.add && v.add.line) { v.line = v.add.line; v.add.line = null; }
      if (v.add && !v.add.email) v.add = null;
      draw();
    } };
  }
  return v.add;
}

/* "Sign out" of this browser, with a line when the reader has comments not sent yet. */
function signOutBlock() {
  const me = who();
  const unsent = loadOb().some(o => ownerOf(o) === me && !o.failed);
  return h("section", { class: "ways" },
    unsent ? h("p", { class: "lead", text: t("signout_kept") }) : null,
    h("div", { class: "row" }, h("button", { type: "button", class: "btn ghost", text: t("sign_out_here"), onclick: signOut })));
}

async function signOut() {
  const r = await api("POST", "api/auth/logout", { page: true });
  if (r.status === 0) {
    view.line = { key: "cannot_connect", vars: {}, bad: true };
    return draw();
  }
  forgetReader();
  store.del(K.reader);
  S.me = null;
  S.auth = null;
  view = null;
  setHash("", false);
  signInScreen({ key: "signed_out_here", vars: {}, bad: false });
}

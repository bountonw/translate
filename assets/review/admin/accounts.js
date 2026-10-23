// Sign-in and browsers, in the Readers section (README.md, "One person per account"): the LINE accounts and email
// addresses each reader signs in with, as review.py identities lists them, and the browsers signed in, as review.py
// sessions lists them, of every reader or of one, with "also those signed out" (sessions --all). Remove a LINE
// account or address (unbind NUMBER), let a reader sign in with a code sent to an address (identity add NAME
// ADDRESS), sign out one browser or the browsers ticked in one request (session end NUMBER ...), or every browser of
// the reader (signout NAME).
import { get, post, busy } from "./api.js";
import { h, clear, button, field, fill, td, answer, ask, refuse, working, stamp } from "./ui.js";
import { t, plural } from "./words.js";
import { state, loadAuth } from "./shared.js";

const a = {};
let ids = [];
let sessions = [];
let who = "";          // the reader shown, or "" for every reader
let failed = "";
let selected = {};
let after = null;
let seq = 0;

// The panel, under the devices; done() runs after a change, so the reader list shows the new state.
export function build(root, done) {
  after = done;
  a.name = h("input", { type: "text", id: "a-name", list: "r-names", autocomplete: "off", placeholder: t("whole_name") });
  a.all = h("input", { type: "checkbox", id: "a-all" });
  a.count = h("p", { class: "count", id: "a-count", "aria-live": "polite" });
  a.ids = h("table", { class: "list", id: "a-ids" });
  a.sessions = h("table", { class: "list", id: "a-sessions" });
  a.address = h("input", { type: "text", id: "a-address", autocomplete: "off", spellcheck: "false",
    placeholder: t("a_address_placeholder") });
  a.box = h("div", { class: "answer", id: "a-answer", hidden: true, "aria-live": "polite" });
  a.end = button(t("a_end_selected"), () => endSessions(picked()), { id: "a-end", class: "act danger" });
  a.signout = button(t("a_signout"), signout, { id: "a-signout", class: "act danger" });
  a.add = button(t("a_add"), addAddress, { id: "a-add" });
  a.all.addEventListener("change", load);
  a.name.addEventListener("keydown", e => { if (e.key === "Enter") ofReader(a.name.value.trim()); });
  // The hint names the days a browser stays signed in, auth.session_days of the site (66-adversarial.md ADV4-08).
  a.hint = h("p", { class: "hint", id: "a-hint", hidden: true });
  (state.auth ? Promise.resolve({ ok: true, result: state.auth }) : loadAuth()).then(res => {
    if (!res.ok || typeof res.result.session_days !== "number") return;
    a.hint.textContent = t("a_hint", { days: plural(res.result.session_days, "day") });
    a.hint.hidden = false;
  });
  a.panel = h("div", { id: "a-panel" },
    h("h3", null, t("a_title")),
    a.hint,
    h("div", { class: "row" },
      button(t("a_every"), () => { who = ""; a.name.value = ""; load(); }, { id: "a-every", class: "plain" }),
      h("span", { class: "gap" }),
      field(t("reader"), a.name),
      button(t("a_show"), () => ofReader(a.name.value.trim()), { id: "a-show" }),
      h("label", { class: "check" }, a.all, " " + t("a_all"))),
    a.count,
    h("h4", null, t("a_ids_title")),
    h("div", { class: "scroll short" }, a.ids),
    h("div", { class: "row" }, field(t("a_address"), a.address, t("a_address_hint")), a.add),
    h("h4", null, t("a_sessions_title")),
    h("div", { class: "scroll short" }, a.sessions),
    h("div", { class: "row" }, a.end, a.signout),
    a.box);
  root.append(a.panel);
}

// Show one reader's LINE accounts, addresses and browsers, as review.py identities NAME and sessions NAME do.
export function ofReader(name) {
  if (!name) {
    a.name.focus();
    return;
  }
  a.name.value = name;
  who = name;
  load();
  if (a.panel.scrollIntoView) a.panel.scrollIntoView({ block: "start" });
}

export async function load() {
  if (!a.panel) return;
  const mine = ++seq;
  const q = who ? { name: who } : {};
  const both = await Promise.all([get("identities", q), get("sessions", Object.assign({ all: a.all.checked }, q))]);
  if (mine !== seq) return;
  failed = both[0].ok ? (both[1].ok ? "" : both[1].error) : both[0].error;
  ids = both[0].ok ? both[0].result.identities : [];
  sessions = both[1].ok ? both[1].result.sessions : [];
  render();
}

function picked() {
  return sessions.filter(s => selected[s.id] && s.active).map(s => s.id);
}

function way(i) {
  return i.provider === "line" ? t("r_signin_line", { name: i.display }) : i.display;
}

function how(s) {
  const id = s.identity;
  if (s.via === "line") return id ? t("a_via_line_as", { name: id.display }) : t("a_via_line");
  if (s.via === "email") return id ? t("a_via_email_to", { address: id.display }) : t("a_via_email");
  return t("a_via_dev");
}

// Who or what ended a browser's session (ended_by of the server).
const ENDED = { reader: "a_state_ended_reader", translator: "a_state_ended_translator", unbind: "a_state_ended_unbind",
  relink: "a_state_ended_relink", signin: "a_state_ended_signin" };

function stateText(s) {
  if (s.active) return t("a_state_active", { time: stamp(s.expires) });
  if (s.ended) return t(ENDED[s.ended_by] || "a_state_ended_translator", { time: stamp(s.ended) });
  // The days the session lasted after its last visit: the site's auth.session_days when it was last seen.
  const days = Math.max(0, Math.round((Date.parse(s.expires) - Date.parse(s.last_seen)) / 86400000)) || 0;
  return t("a_state_ran_out", { time: stamp(s.expires), days: plural(days, "day") });
}

function render() {
  fill(a.ids, [t("a_col_number"), t("a_col_reader"), t("a_col_way"), t("a_col_added"), t("a_col_used"),
    t("a_col_browsers"), ""], ids.map(i => h("tr", { "data-identity": String(i.id) },
    td(String(i.id), "num"), td(i.name, "name"), td(way(i)), td(stamp(i.created), "nowrap"),
    td(i.last_used ? stamp(i.last_used) : t("a_not_used"), "nowrap"), td(String(i.sessions), "num"),
    td(button(t("a_remove"), () => unbind(i), { class: "act small danger", "data-unbind": String(i.id) }), "nowrap"))));
  a.ids.hidden = ids.length === 0;
  const keep = {};
  sessions.forEach(s => { if (selected[s.id] && s.active) keep[s.id] = true; });
  selected = keep;
  const live = sessions.filter(s => s.active);
  const all = h("input", { type: "checkbox", id: "a-select-all", "aria-label": t("a_select_all") });
  all.checked = live.length > 0 && live.every(s => selected[s.id]);
  all.addEventListener("change", () => {
    selected = {};
    if (all.checked) live.forEach(s => { selected[s.id] = true; });
    render();
  });
  fill(a.sessions, [all, t("a_col_number"), t("a_col_reader"), t("a_col_browser"), t("a_col_how"), t("a_col_since"),
    t("a_col_seen"), t("a_col_state"), ""], sessions.map(s => {
    const box = s.active ? h("input", { type: "checkbox", "aria-label": t("select_one", { name: String(s.id) }),
      "data-session": String(s.id) }) : null;
    if (box) {
      box.checked = !!selected[s.id];
      box.addEventListener("change", () => {
        if (box.checked) selected[s.id] = true;
        else delete selected[s.id];
        render();
      });
    }
    return h("tr", { class: s.active ? "" : "off", "data-session": String(s.id) }, td(box, "pick"),
      td(String(s.id), "num"), td(s.name, "name"), td(s.agent), td(how(s)), td(stamp(s.created), "nowrap"),
      td(stamp(s.last_seen), "nowrap"), td(stateText(s)),
      td(s.active ? button(t("a_end"), () => endSessions([s.id]), { class: "act small danger", "data-end": String(s.id) })
        : null, "nowrap"));
  }));
  a.sessions.hidden = sessions.length === 0;
  const n = picked().length;
  if (failed) {
    clear(a.count).append(h("span", { class: "error" }, failed));
  } else {
    const vars = { ways: plural(ids.length, "way"), browsers: plural(live.length, "browser"), name: who };
    a.count.textContent = (who ? t("a_count_reader", vars) : t("a_count_every", vars)) + (n ? " " + t("n_selected", { n: n }) : "");
  }
  a.end.disabled = n === 0;
  a.signout.disabled = !who;
  a.add.disabled = !who;
}

async function changed(res, title) {
  answer(a.box, res, { title: title });
  selected = {};
  await load();
  if (after) await after();
}

// Remove one LINE account or address: it no longer signs in, and the browsers it signed in are signed out.
async function unbind(i) {
  if (busy()) return;
  const vars = { way: way(i), name: i.name, browsers: plural(i.sessions, "browser") };
  if (!(await ask(t("a_remove_q", vars), { note: t("a_remove_note", vars), go: t("a_remove") }))) return;
  working(a.box);
  await changed(await post("unbind", { ids: [i.id] }), t("a_remove_title", vars));
}

// Sign out one browser, or the browsers ticked, in one request.
async function endSessions(list) {
  if (busy() || !list.length) return;
  const n = plural(list.length, "browser");
  if (list.length > 1) {
    const names = sessions.filter(s => list.indexOf(s.id) >= 0).map(s => s.id + ". " + s.name + ": " + s.agent);
    if (!(await ask(t("a_end_q", { browsers: n }), { list: names, note: t("a_end_note"), go: t("a_end") }))) return;
  }
  working(a.box);
  await changed(await post("session", { action: "end", ids: list }), t("a_end_title", { browsers: n }));
}

// Sign the reader shown out on every browser.
async function signout() {
  if (busy() || !who) return;
  const n = sessions.filter(s => s.active).length;
  const vars = { name: who, browsers: plural(n, "browser") };
  if (!(await ask(t("a_signout_q", vars), { note: t("a_signout_note"), go: t("a_signout") }))) return;
  working(a.box);
  await changed(await post("signout", { names: [who] }), t("a_signout_title", vars));
}

// Let the reader shown sign in with a code sent to an address, without the link.
async function addAddress() {
  if (busy()) return;
  const address = a.address.value.trim();
  if (!who || !address) {
    refuse(a.box, t("a_add_need"));
    a.address.focus();
    return;
  }
  working(a.box);
  const res = await post("identity", { action: "add", name: who, address: address });
  if (res.ok) a.address.value = "";
  await changed(res, t("a_add_title", { name: who, address: address }));
}

// Readers: find readers by any part of the name, by group, book, inactivity, revoked links, links used on more
// than two devices, how they sign in, or a link; act on the readers ticked, all in one request, as the commands do
// with several names; stop or restore one reader's link, and switch "Link signs in", from its row; the devices of
// each link (devices.js); each reader's LINE accounts, addresses and browsers signed in (accounts.js); delete one
// reader's comments between two dates; invite one reader, or many from a CSV file.
import { get, post, busy } from "./api.js";
import { h, clear, button, field, fill, td, answer, ask, refuse, working, stamp, compact, csvRows, readFile, names,
  thaiTime } from "./ui.js";
import { t, plural } from "./words.js";
import { bookIds, featureSelect } from "./shared.js";
import * as devices from "./devices.js";
import * as accounts from "./accounts.js";

const f = {};
const invite = {};
const dc = {};
let built = false;
let rows = [];
let lines = [];
let total = 0;
let failed = "";
let selected = {};
let groups = [];
let seq = 0;
let timer = 0;
let wantGroup = "";
let perLink = 2;       // the devices a link works on without approval: limits.devices_per_link of the server

export async function show(root) {
  if (!built) {
    build(root);
    built = true;
  }
  if (wantGroup) {
    // The Groups section asked for one group's members: its option may not be in the list yet.
    if (!Array.from(f.group.options).some(o => o.value === wantGroup)) f.group.append(h("option", { value: wantGroup }, wantGroup));
    f.group.value = wantGroup;
    wantGroup = "";
  }
  const mine = ++seq;
  const both = await Promise.all([get("groups"), get("readers", params())]);
  takeGroups(both[0]);
  if (mine === seq) take(both[1]);
  render();
  await Promise.all([devices.load(), accounts.load()]);
}

// Open this section with the members of one group listed, from the Groups section.
export function showGroup(name) {
  wantGroup = name;
  if (location.hash === "#readers" && built) show(null);
  else location.hash = "#readers";
}

function build(root) {
  f.name = h("input", { type: "search", id: "r-name", placeholder: t("r_name_placeholder"), autocomplete: "off" });
  f.group = h("select", { id: "r-group" }, h("option", { value: "" }, t("r_any_group")));
  f.book = h("select", { id: "r-book" }, h("option", { value: "" }, t("r_any_book")),
    bookIds().map(id => h("option", { value: id }, id)));
  f.inactive = h("input", { type: "number", id: "r-inactive", min: "0", step: "1", placeholder: t("r_any"), class: "short" });
  f.revoked = h("input", { type: "checkbox", id: "r-revoked" });
  f.devices = h("input", { type: "checkbox", id: "r-devices" });
  f.identity = h("select", { id: "r-identity" }, [["", "r_identity_all"], ["none", "r_identity_none"],
    ["line", "r_identity_line"], ["email", "r_identity_email"], ["any", "r_identity_any"]].map(v =>
    h("option", { value: v[0] }, t(v[1]))));
  f.link = h("input", { type: "text", id: "r-link", placeholder: t("r_link_placeholder"), autocomplete: "off",
    spellcheck: "false" });
  f.count = h("p", { class: "count", id: "r-count", "aria-live": "polite" });
  f.table = h("table", { class: "list", id: "r-table" });
  f.names = h("datalist", { id: "r-names" });
  f.chosen = h("p", { id: "r-selected", class: "chosen" });
  f.spec = h("input", { type: "text", id: "r-spec", placeholder: t("spec_placeholder"), autocomplete: "off",
    spellcheck: "false" });
  f.feature = featureSelect("r-feature");
  f.unbind = h("input", { type: "checkbox", id: "r-unbind" });
  f.box = h("div", { class: "answer", id: "r-answer", hidden: true, "aria-live": "polite" });
  f.buttons = [
    button(t("r_open"), () => act("open"), { id: "r-open" }),
    button(t("r_close"), () => act("close"), { id: "r-close" }),
    button(t("r_revoke"), () => act("revoke"), { id: "r-revoke" }),
    button(t("r_restore"), () => act("restore"), { id: "r-restore" }),
    button(t("r_relink"), () => act("relink"), { id: "r-relink" }),
    button(t("english_on"), () => act("english", "on"), { id: "r-english-on" }),
    button(t("english_off"), () => act("english", "off"), { id: "r-english-off" }),
    button(t("on"), () => act("feature", "on"), { id: "r-feature-on" }),
    button(t("off"), () => act("feature", "off"), { id: "r-feature-off" }),
    button(t("r_lsi_on"), () => act("link-signs-in", "on"), { id: "r-lsi-on", title: t("r_lsi_hint") }),
    button(t("r_lsi_off"), () => act("link-signs-in", "off"), { id: "r-lsi-off", title: t("r_lsi_hint") })
  ];
  [f.name, f.link, f.inactive].forEach(input => input.addEventListener("input", later));
  [f.group, f.book, f.revoked, f.devices, f.identity].forEach(input => input.addEventListener("change", search));
  const b = f.buttons;
  root.append(h("h2", null, t("r_title")),
    h("div", { class: "filters" },
      field(t("r_f_name"), f.name),
      field(t("r_f_group"), f.group),
      field(t("r_f_book"), f.book, t("r_f_book_hint")),
      field(t("r_f_inactive"), f.inactive, t("r_f_inactive_hint")),
      h("label", { class: "check" }, f.revoked, " " + t("r_f_revoked")),
      h("label", { class: "check" }, f.devices, " " + t("r_f_devices")),
      field(t("r_f_identity"), f.identity),
      field(t("r_f_link"), f.link, t("r_f_link_hint")),
      button(t("r_clear"), clearFilters, { id: "r-clear", class: "plain" })),
    f.count,
    h("div", { class: "scroll tall" }, f.table),
    f.names,
    h("div", { class: "actions", id: "r-actions" },
      f.chosen,
      h("div", { class: "row" }, field(t("chapters"), f.spec), b[0], b[1]),
      h("div", { class: "row" }, b[2], b[3], b[4], h("label", { class: "check" }, f.unbind, " " + t("r_unbind"))),
      h("div", { class: "row" }, b[5], b[6], h("span", { class: "gap" }), field(t("feature"), f.feature), b[7], b[8],
        h("span", { class: "gap" }), b[9], b[10]),
      f.box));
  devices.build(root, search);
  accounts.build(root, search);
  buildDelete(root);
  buildInvite(root);
}

function buildDelete(root) {
  dc.name = h("input", { type: "text", id: "dc-name", list: "r-names", autocomplete: "off", placeholder: t("whole_name") });
  dc.from = h("input", { type: "date", id: "dc-from" });
  dc.fromTime = h("input", { type: "time", id: "dc-from-time", "aria-label": t("dc_from_time") });
  dc.to = h("input", { type: "date", id: "dc-to" });
  dc.toTime = h("input", { type: "time", id: "dc-to-time", "aria-label": t("dc_to_time") });
  dc.box = h("div", { class: "answer", id: "dc-answer", hidden: true, "aria-live": "polite" });
  root.append(h("h3", null, t("dc_title")),
    h("p", { class: "hint" }, t("dc_hint")),
    h("div", { class: "row" },
      field(t("reader"), dc.name),
      field(t("dc_from"), h("span", { class: "pair" }, dc.from, dc.fromTime), t("dc_time_hint")),
      field(t("dc_to"), h("span", { class: "pair" }, dc.to, dc.toTime), t("dc_time_hint")),
      button(t("dc_go"), deleteComments, { id: "dc-go", class: "act danger" })),
    dc.box);
}

function buildInvite(root) {
  invite.name = h("input", { type: "text", id: "i-name", autocomplete: "off" });
  invite.grant = h("input", { type: "text", id: "i-grant", placeholder: t("spec_placeholder_book"), autocomplete: "off",
    spellcheck: "false" });
  invite.groups = h("div", { class: "choices", id: "i-groups" });
  invite.english = h("input", { type: "checkbox", id: "i-english" });
  invite.lsi = h("input", { type: "checkbox", id: "i-link-signs-in" });
  invite.box = h("div", { class: "answer", id: "i-answer", hidden: true, "aria-live": "polite" });
  invite.file = h("input", { type: "file", id: "m-file", accept: ".csv,text/csv" });
  invite.many = h("div", { class: "answer", id: "m-answer", hidden: true, "aria-live": "polite" });
  root.append(h("h3", null, t("i_title")),
    h("div", { class: "row" },
      field(t("name"), invite.name),
      field(t("chapters"), invite.grant, t("i_chapters_hint")),
      h("label", { class: "check" }, invite.english, " " + t("english")),
      h("label", { class: "check", title: t("i_lsi_hint") }, invite.lsi, " " + t("i_lsi"))),
    h("div", { class: "row" }, h("span", { class: "label" }, t("groups")), invite.groups),
    h("div", { class: "bar" }, button(t("i_go"), inviteOne, { id: "i-go" })),
    invite.box,
    h("h3", null, t("m_title")),
    h("p", { class: "hint" }, t("m_hint")),
    h("div", { class: "row" }, field(t("m_file"), invite.file), button(t("m_go"), inviteMany, { id: "m-go" })),
    invite.many);
}

function params() {
  return { name: f.name.value.trim(), group: f.group.value, book: f.book.value, inactive: f.inactive.value.trim(),
    revoked: f.revoked.checked, devices: f.devices.checked, identity: f.identity.value, link: f.link.value.trim() };
}

function filtered() {
  const p = params();
  return Object.keys(p).some(k => p[k] !== "" && p[k] !== false);
}

function later() {
  clearTimeout(timer);
  timer = setTimeout(search, 200);
}

function clearFilters() {
  f.name.value = "";
  f.group.value = "";
  f.book.value = "";
  f.inactive.value = "";
  f.revoked.checked = false;
  f.devices.checked = false;
  f.identity.value = "";
  f.link.value = "";
  search();
}

async function search() {
  clearTimeout(timer);
  const mine = ++seq;
  const res = await get("readers", params());
  if (mine !== seq) return;
  take(res);
  render();
}

function take(res) {
  if (res.ok) {
    rows = res.result.readers;
    total = res.result.total;
    lines = res.lines;
    failed = "";
    if (res.result.devices_per_link > 0) perLink = res.result.devices_per_link;
  } else {
    rows = [];
    lines = [];
    failed = res.error;
  }
}

function takeGroups(res) {
  if (!res.ok) return;
  groups = res.result.groups;
  const keep = f.group.value;
  clear(f.group).append(h("option", { value: "" }, t("r_any_group")));
  groups.forEach(g => f.group.append(h("option", { value: g.name }, g.active ? g.name : t("group_off", { name: g.name }))));
  f.group.value = groups.some(g => g.name === keep) ? keep : "";
  const ticked = {};
  invite.groups.querySelectorAll("input:checked").forEach(c => { ticked[c.value] = true; });
  clear(invite.groups);
  if (!groups.length) invite.groups.append(h("span", { class: "muted" }, t("i_no_groups")));
  groups.forEach(g => {
    const c = h("input", { type: "checkbox", value: g.name, "data-group": g.name });
    c.checked = !!ticked[g.name];
    invite.groups.append(h("label", { class: "check" }, c, " " + (g.active ? g.name : t("group_off", { name: g.name }))));
  });
}

function englishText(r) {
  if (r.english && !r.settings["english.on"]) return t("r_english_group");
  return r.english ? t("is_on") : t("is_off");
}

// The devices of the reader's current link, flagged when the link was opened on more devices than it works on
// without approval (devices_per_link) or a device waits for approval. A link with too many devices waiting refuses
// further ones unlisted (full), and the row says the reader needs a new link.
function deviceCell(r) {
  const d = r.devices || { total: 0, waiting: 0 };
  const flagged = d.total > perLink || d.waiting > 0 || !!d.full;
  const text = (d.total ? plural(d.total, "device") + (d.waiting ? t("r_devices_waiting", { n: d.waiting }) : "")
    : t("r_devices_none")) + (d.full ? t("r_devices_full") : "");
  return [h("span", { class: flagged ? "flag" : null, title: flagged ? t("r_flag", { n: perLink }) : null,
    "data-flag": flagged ? r.name : null }, text),
    " ", button(t("r_devices_show"), () => devices.ofReader(r.name), { class: "plain small", "data-devices": r.name })];
}

// How the reader signs in: "Link signs in", the LINE accounts and addresses with the browsers signed in, a link
// used whose LINE accounts and addresses were all removed (flagged: the reader needs a new link), none now for a
// reader who signed in before and has an unused link, with the next sign-in through the link only for an active
// reader, since a revoked reader's link opens nothing, or not yet.
function signinCell(r) {
  const ids = r.identities || [];
  let text;
  let flagged = false;
  if (r.link_signs_in) {
    text = t("r_signin_link");
  } else if (ids.length) {
    text = ids.map(i => i.provider === "line" ? t("r_signin_line", { name: i.display }) : i.display).join(", ") +
      (r.sessions ? t("r_signin_browsers", { browsers: plural(r.sessions, "browser") }) : t("r_signin_no_browser"));
  } else if (r.link_used) {
    text = t("r_signin_used");
    flagged = true;
  } else if (r.first_signin) {
    // The reader signed in before, and every LINE account and address was removed since, as relink --unbind does.
    text = r.active ? t("r_signin_none_now") : t("r_signin_none_stopped");
  } else {
    text = t("r_signin_not_yet");
  }
  // The switch "Link signs in", for this reader alone; and the reader's sign-in and browsers below the list.
  const sw = button(r.link_signs_in ? t("r_lsi_switch_off") : t("r_lsi_switch_on"), () => switchLsi(r),
    { class: "plain small", "data-link-signs-in": r.name,
      "aria-label": t(r.link_signs_in ? "r_lsi_switch_off_aria" : "r_lsi_switch_on_aria", { name: r.name }) });
  return [h("span", { class: flagged ? "flag" : null, "data-signin-of": r.name }, text), " ", sw, " ",
    button(t("r_signin_show"), () => accounts.ofReader(r.name), { class: "plain small", "data-signin": r.name })];
}

function render() {
  const keep = {};
  rows.forEach(r => { if (selected[r.id]) keep[r.id] = r; });
  selected = keep;
  const byName = {};
  groups.forEach(g => { byName[g.name.toLowerCase()] = g; });
  const all = h("input", { type: "checkbox", id: "r-all", "aria-label": t("r_select_all") });
  all.checked = rows.length > 0 && rows.every(r => selected[r.id]);
  all.addEventListener("change", () => {
    selected = {};
    if (all.checked) rows.forEach(r => { selected[r.id] = r; });
    render();
  });
  fill(f.table, [all, t("r_col_name"), t("r_col_link"), t("r_col_own"), t("r_col_groups"), t("r_col_english"),
    t("r_col_signin"), t("r_col_devices"), t("r_col_comments"), t("r_col_last")],
    rows.map((r, i) => {
      const box = h("input", { type: "checkbox", value: String(r.id), "aria-label": t("select_one", { name: r.name }),
        "data-reader": r.name });
      box.checked = !!selected[r.id];
      box.addEventListener("change", () => {
        if (box.checked) selected[r.id] = r;
        else delete selected[r.id];
        render();
      });
      const marked = (r.groups || []).map(n => {
        const g = byName[n.toLowerCase()];
        return g && !g.active ? t("group_off", { name: n }) : n;
      });
      // The stop switch of the reader's link: revoke or restore, for this reader alone.
      const sw = button(r.active ? t("r_stop_one") : t("r_restore_one"), () => switchOne(r),
        { class: r.active ? "plain small" : "act small", "data-switch": r.name,
          "aria-label": t(r.active ? "r_stop_one_aria" : "r_restore_one_aria", { name: r.name }) });
      return h("tr", { class: r.active ? "" : "revoked", title: lines[i] || "", "data-reader": r.name },
        td(box, "pick"), td(r.name, "name"), td([r.active ? t("r_works") : t("r_stopped"), " ", sw], "nowrap"),
        td(compact(r.grants) || t("nothing")), td(marked.join(", ")), td(englishText(r)), td(signinCell(r)),
        td(deviceCell(r), "nowrap"),
        td(String(r.comments), "num"), td(r.last_active ? stamp(r.last_active) : t("never"), "nowrap"));
    }));
  clear(f.names);
  rows.slice(0, 2000).forEach(r => f.names.append(h("option", { value: r.name })));
  if (failed) {
    clear(f.count).append(h("span", { class: "error" }, failed));
  } else if (!total) {
    f.count.textContent = t("r_none");
  } else {
    f.count.textContent = filtered() ? t("r_count_of", { n: rows.length, readers: plural(total, "reader") })
      : t("r_count", { readers: plural(total, "reader") });
  }
  const picked = chosen().map(r => r.name);
  f.chosen.textContent = picked.length ? t("r_selected", { readers: plural(picked.length, "reader"), names: names(picked, 8) })
    : t("r_selected_none");
  f.buttons.forEach(btn => { btn.disabled = picked.length === 0; });
}

function chosen() {
  return rows.filter(r => selected[r.id]);
}

// What each button asks and sends: one request for every reader ticked, as review.py takes several names.
function plan(kind, spec, state, feature) {
  const p = {
    open: { q: "r_open_q", note: "r_open_note", go: "r_open", title: "r_open_title",
      send: list => post("open", { names: list, spec: spec }) },
    close: { q: "r_close_q", note: "r_close_note", go: "r_close", title: "r_close_title",
      send: list => post("close", { names: list, spec: spec }) },
    revoke: { q: "r_revoke_q", note: "r_revoke_note", go: "r_revoke", title: "r_revoke_title",
      send: list => post("revoke", { names: list }) },
    restore: { q: "r_restore_q", note: "r_restore_note", go: "r_restore", title: "r_restore_title",
      send: list => post("restore", { names: list }) },
    relink: { q: f.unbind.checked ? "r_relink_unbind_q" : "r_relink_q",
      note: f.unbind.checked ? "r_relink_unbind_note" : "r_relink_note", go: "r_relink_go", title: "r_relink_title",
      send: list => post("relink", { names: list, unbind: f.unbind.checked }) },
    "link-signs-in": { q: state === "on" ? "r_lsi_on_q" : "r_lsi_off_q", note: state === "on" ? "r_lsi_on_note" : "r_lsi_off_note",
      go: state === "on" ? "r_lsi_on" : "r_lsi_off", title: state === "on" ? "r_lsi_on_title" : "r_lsi_off_title",
      send: list => post("link-signs-in", { names: list, state: state }) },
    english: { q: state === "on" ? "r_english_on_q" : "r_english_off_q", note: "r_english_note",
      go: state === "on" ? "english_on" : "english_off", title: state === "on" ? "r_english_on_title" : "r_english_off_title",
      send: list => post("english", { names: list, state: state }) },
    feature: { q: state === "on" ? "r_feature_on_q" : "r_feature_off_q", note: "r_feature_note",
      go: state === "on" ? "on" : "off", title: state === "on" ? "r_feature_on_title" : "r_feature_off_title",
      send: list => post("feature", { names: list, feature: feature, state: state }) }
  };
  return p[kind];
}

async function act(kind, state) {
  if (busy()) return;
  const list = chosen();
  if (!list.length) return;
  const spec = f.spec.value.trim();
  if ((kind === "open" || kind === "close") && !spec) {
    refuse(f.box, t("need_spec"));
    f.spec.focus();
    return;
  }
  const feature = f.feature.value;
  if (kind === "feature" && !feature) return;
  const p = plan(kind, spec, state, feature);
  const vars = { spec: spec, feature: feature, readers: plural(list.length, "reader"), name: list[0].name };
  if (list.length > 1 || kind === "relink") {
    const q = kind === "relink" && list.length === 1 ? (f.unbind.checked ? "r_relink_unbind_one_q" : "r_relink_one_q") : p.q;
    if (!(await ask(t(q, vars), { list: list.map(r => r.name), note: t(p.note), go: t(p.go) }))) return;
  }
  working(f.box);
  const res = await p.send(list.map(r => r.name));
  const links = res.ok && res.result && res.result.readers
    ? res.result.readers.map(r => ({ name: r.name, link: r.link, note: r.stopped || "" })) : [];
  answer(f.box, res, { title: t(p.title, vars), links: links, after: search });
  if (kind === "relink") f.unbind.checked = false;
  await search();
  if (kind === "relink") await accounts.load();
}

// The switch "Link signs in" on a reader's row, for that reader alone.
async function switchLsi(r) {
  if (busy()) return;
  working(f.box);
  const p = plan("link-signs-in", "", r.link_signs_in ? "off" : "on");
  const res = await p.send([r.name]);
  answer(f.box, res, { title: t(p.title, { readers: r.name }) });
  await search();
}

// The stop switch on a reader's row: one reader's link stopped (revoke) or working again (restore).
async function switchOne(r) {
  if (busy()) return;
  working(f.box);
  const p = plan(r.active ? "revoke" : "restore");
  const res = await p.send([r.name]);
  answer(f.box, res, { title: t(p.title, { readers: r.name }), after: search });
  await search();
}

// A date of a date field and a time of a time field, as the command reads them: "2026-10-22" or
// "2026-10-22 14:30", in Thailand time.
function when(day, time) {
  const d = day.value.trim();
  return d ? d + (time.value ? " " + time.value.slice(0, 5) : "") : "";
}

async function deleteComments() {
  if (busy()) return;
  const name = dc.name.value.trim();
  const from = when(dc.from, dc.fromTime);
  const to = when(dc.to, dc.toTime);
  if (!name || !from || !to) {
    refuse(dc.box, t("dc_need"));
    return;
  }
  working(dc.box);
  // First the count, which deletes nothing; then the same with yes, once you agree.
  const res = await post("delete-comments", { name: name, from: from, to: to });
  const r = res.result;
  if (!res.ok || !r || !r.comments) {
    answer(dc.box, res, { title: t("dc_answer_title", { name: name }) });
    return;
  }
  const where = Object.keys(r.chapters).sort().map(ch => t("dc_where", { chapter: ch, n: r.chapters[ch] })).join(", ");
  const vars = { comments: plural(r.comments, "comment"), name: r.name, from: thaiTime(r.from), to: thaiTime(r.to),
    where: where };
  if (!(await ask(t("dc_q", vars), { note: t("dc_note", vars), go: t("dc_go_yes") }))) {
    answer(dc.box, { ok: true, lines: [t("dc_kept", vars)], error: "" }, { title: t("dc_answer_title", { name: r.name }) });
    return;
  }
  working(dc.box);
  // upto: the last comment counted, so a comment the reader writes meanwhile is not deleted with them.
  const done = await post("delete-comments", { name: name, from: from, to: to, yes: true, upto: r.last });
  answer(dc.box, done, { title: t("dc_answer_title", { name: r.name }) });
  await search();
}

async function inviteOne() {
  if (busy()) return;
  const name = invite.name.value.trim();
  if (!name) {
    refuse(invite.box, t("i_need_name"));
    invite.name.focus();
    return;
  }
  const groupNames = Array.from(invite.groups.querySelectorAll("input:checked")).map(c => c.value);
  working(invite.box);
  const res = await post("invite", { name: name, grant: invite.grant.value.trim(), group: groupNames,
    english: invite.english.checked, link_signs_in: invite.lsi.checked });
  const links = res.ok && res.result ? [{ name: res.result.name, link: res.result.link }] : [];
  answer(invite.box, res, { title: t("i_answer_title", { name: name }), links: links, after: search });
  if (res.ok) {
    invite.name.value = "";
    invite.lsi.checked = false;
    await search();
  }
}

async function inviteMany() {
  if (busy()) return;
  const file = await readFile(invite.file);
  if (!file) {
    refuse(invite.many, t("m_need_file"));
    return;
  }
  const n = csvRows(file.text);
  if (!(await ask(t("m_q", { readers: plural(n, "reader"), file: file.name }), { go: t("m_go_yes"), note: t("m_note") }))) return;
  working(invite.many);
  const res = await post("invite", { csv: file.text, filename: file.name });
  answer(invite.many, res, { title: t("m_answer_title", { file: file.name }), after: search });
  if (res.ok) {
    invite.file.value = "";
    await search();
  }
}

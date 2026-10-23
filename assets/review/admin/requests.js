// Requests: the requests to read that people make through a group's general link, as review.py requests lists them
// (waiting, approved, declined or all), and the general links themselves (review.py general-link [G]). Approve a
// request as a new reader, with a name, chapters, groups and English, or for a reader who exists (request approve
// NUMBER --name --grant --group --english, or --reader NAME); decline it (request decline); forget it (request
// forget). Make a new general link of a group, shown once with a Copy button (general-link G --new --days --uses),
// or switch a group's link off (general-link G --off). The menu counts the requests waiting.
import { get, post, busy } from "./api.js";
import { h, clear, button, field, fill, td, answer, ask, refuse, working, stamp } from "./ui.js";
import { t, plural } from "./words.js";
import { showRequests } from "./shared.js";

const q = {};
let built = false;
let rows = [];
let links = [];
let groups = [];
let failed = "";
let current = null;     // the request being approved
let defaults = { general_days: 90, general_uses: 100 };   // invite.general_days and general_uses of config.json

export async function show(root) {
  if (!built) {
    build(root);
    built = true;
  }
  await load();
}

function build(root) {
  q.state = h("select", { id: "q-state" }, [["open", "q_state_open"], ["approved", "q_state_approved"],
    ["declined", "q_state_declined"], ["all", "q_state_all"]].map(v => h("option", { value: v[0] }, t(v[1]))));
  q.count = h("p", { class: "count", id: "q-count", "aria-live": "polite" });
  q.table = h("table", { class: "list", id: "q-table" });
  q.box = h("div", { class: "answer", id: "q-answer", hidden: true, "aria-live": "polite" });
  q.state.addEventListener("change", loadRequests);
  root.append(h("h2", null, t("q_title")),
    h("p", { class: "hint" }, t("q_hint")),
    h("div", { class: "row" }, field(t("q_show"), q.state)),
    q.count,
    h("div", { class: "scroll" }, q.table),
    q.box,
    buildApprove(),
    buildLinks());
}

// The approval of one request: as a new reader, or for a reader who exists.
function buildApprove() {
  q.panel = h("div", { class: "panel", id: "q-panel", hidden: true });
  q.panelTitle = h("h3", { id: "q-panel-title" });
  q.name = h("input", { type: "text", id: "q-name", autocomplete: "off" });
  q.nameHint = h("span", { class: "hint", id: "q-name-hint" });
  q.grant = h("input", { type: "text", id: "q-grant", placeholder: t("spec_placeholder_book"), autocomplete: "off",
    spellcheck: "false" });
  q.groups = h("div", { class: "choices", id: "q-groups" });
  q.english = h("input", { type: "checkbox", id: "q-english" });
  q.reader = h("input", { type: "text", id: "q-reader", list: "r-names", autocomplete: "off", placeholder: t("whole_name") });
  q.panel.append(q.panelTitle,
    h("h4", null, t("q_new_title")),
    h("div", { class: "row" },
      h("label", { class: "field" }, h("span", { class: "label" }, t("name")), q.name, q.nameHint),
      field(t("chapters"), q.grant, t("q_chapters_hint")),
      h("label", { class: "check" }, q.english, " " + t("english"))),
    h("div", { class: "row" }, h("span", { class: "label" }, t("groups")), q.groups),
    h("div", { class: "bar" }, button(t("q_approve_new"), () => approve(false), { id: "q-approve-new" })),
    h("h4", null, t("q_reader_title")),
    h("div", { class: "row" }, field(t("reader"), q.reader, t("q_reader_hint")),
      button(t("q_approve_reader"), () => approve(true), { id: "q-approve-reader" })),
    h("div", { class: "bar" }, button(t("cancel"), closeApprove, { id: "q-cancel", class: "plain" })));
  return q.panel;
}

// The general links of the groups, and a new one.
function buildLinks() {
  q.lGroup = h("select", { id: "gl-group" });
  q.lCount = h("p", { class: "count", id: "gl-count" });
  q.lTable = h("table", { class: "list", id: "gl-table" });
  q.newGroup = h("select", { id: "gl-new-group" });
  q.days = h("input", { type: "number", id: "gl-days", min: "1", step: "1", class: "short" });
  q.uses = h("input", { type: "number", id: "gl-uses", min: "1", step: "1", class: "short" });
  q.lBox = h("div", { class: "answer", id: "gl-answer", hidden: true, "aria-live": "polite" });
  q.daysHint = h("span", { id: "gl-days-hint" });
  q.usesHint = h("span", { id: "gl-uses-hint" });
  q.lGroup.addEventListener("change", loadLinks);
  return h("div", { id: "gl-panel" },
    h("h3", null, t("gl_title")),
    h("p", { class: "hint" }, t("gl_hint")),
    h("div", { class: "row" }, field(t("gl_of_group"), q.lGroup)),
    q.lCount,
    h("div", { class: "scroll short" }, q.lTable),
    h("div", { class: "row" }, field(t("gl_new_group"), q.newGroup), field(t("gl_days"), q.days, q.daysHint),
      field(t("gl_uses"), q.uses, q.usesHint), button(t("gl_new"), makeLink, { id: "gl-new" })),
    q.lBox);
}

async function load() {
  const both = await Promise.all([get("groups"), get("auth")]);
  const res = both[0];
  if (res.ok) groups = res.result.groups;
  if (both[1].ok && both[1].result.invite) defaults = both[1].result.invite;
  q.days.placeholder = String(defaults.general_days);
  q.uses.placeholder = String(defaults.general_uses);
  q.daysHint.textContent = t("gl_days_hint", { days: defaults.general_days });
  q.usesHint.textContent = t("gl_uses_hint", { uses: defaults.general_uses });
  [q.lGroup, q.newGroup].forEach((select, i) => {
    const keep = select.value;
    clear(select);
    if (i === 0) select.append(h("option", { value: "" }, t("gl_every_group")));
    groups.forEach(g => select.append(h("option", { value: g.name }, g.active ? g.name : t("group_off", { name: g.name }))));
    if (groups.some(g => g.name === keep)) select.value = keep;
  });
  await Promise.all([loadRequests(), loadLinks()]);
}

async function loadRequests() {
  const res = await get("requests", { state: q.state.value });
  if (res.ok) {
    rows = res.result.requests;
    failed = "";
    showRequests(res.result.open);
  } else {
    rows = [];
    failed = res.error;
  }
  render(res.ok ? res.result.open : 0);
}

function stateText(r) {
  if (r.decision === "approved") return r.name ? t("q_approved_as", { time: stamp(r.decided), name: r.name }) : t("q_approved", { time: stamp(r.decided) });
  if (r.decision === "declined") return t("q_declined", { time: stamp(r.decided) });
  return t("q_waiting");
}

function render(open) {
  fill(q.table, [t("q_col_number"), t("q_col_who"), t("q_col_by"), t("q_col_group"), t("q_col_asked"), t("q_col_state"), ""],
    rows.map(r => {
      const acts = [];
      if (!r.decided) {
        acts.push(button(t("q_approve"), () => openApprove(r), { class: "act small", "data-approve-request": String(r.id) }),
          button(t("q_decline"), () => decline(r), { class: "act small danger", "data-decline": String(r.id) }));
      }
      acts.push(button(t("q_forget"), () => forget(r), { class: "plain small", "data-forget": String(r.id) }));
      // A LINE display name comes from the person's LINE account: it goes in as text, never as HTML.
      return h("tr", { class: r.decided ? "off" : "waiting", "data-request": String(r.id) },
        td(String(r.id), "num"), td(r.display, "name"), td(r.provider === "line" ? t("q_by_line") : t("q_by_email")),
        td(r.group || t("q_group_gone")), td(stamp(r.created), "nowrap"), td(stateText(r)), td(acts, "nowrap"));
    }));
  q.table.hidden = rows.length === 0;
  if (failed) {
    clear(q.count).append(h("span", { class: "error" }, failed));
  } else if (q.state.value === "open") {
    q.count.textContent = rows.length ? t("q_count_open", { requests: plural(rows.length, "request") }) : t("q_none_open");
  } else {
    q.count.textContent = t("q_count", { requests: plural(rows.length, "request"), open: open });
  }
}

async function reload() {
  await loadRequests();
  await loadLinks();
}

// An answer, then the lists again; a step the answer offers, such as forgetting a declined request, reloads them too.
async function changed(res, title, box) {
  answer(box || q.box, res, { title: title, after: reload });
  await reload();
}

function openApprove(r) {
  current = r;
  q.panelTitle.textContent = t("q_panel_title", { id: r.id, who: r.display });
  // The name starts as the display name; an address is offered too, but asked for, since it would become the name.
  q.name.value = r.display;
  q.nameHint.textContent = r.provider === "email" ? t("q_name_hint_email") : t("q_name_hint_line");
  q.grant.value = "";
  q.english.checked = false;
  q.reader.value = "";
  clear(q.groups);
  if (!groups.length) q.groups.append(h("span", { class: "muted" }, t("i_no_groups")));
  groups.forEach(g => {
    const c = h("input", { type: "checkbox", value: g.name, "data-group": g.name });
    c.checked = g.name === r.group;
    q.groups.append(h("label", { class: "check" }, c, " " + (g.active ? g.name : t("group_off", { name: g.name }))));
  });
  q.panel.hidden = false;
  if (q.panel.scrollIntoView) q.panel.scrollIntoView({ block: "start" });
  q.name.focus();
}

function closeApprove() {
  current = null;
  q.panel.hidden = true;
}

async function approve(toReader) {
  if (busy() || !current) return;
  const r = current;
  let body;
  let title;
  if (toReader) {
    const reader = q.reader.value.trim();
    if (!reader) {
      refuse(q.box, t("q_need_reader"));
      q.reader.focus();
      return;
    }
    body = { action: "approve", id: r.id, reader: reader };
    title = t("q_approve_reader_title", { id: r.id, who: r.display, name: reader });
    if (!(await ask(t("q_approve_reader_q", { who: r.display, name: reader }), { note: t("q_approve_reader_note"),
      go: t("q_approve_reader") }))) return;
  } else {
    const name = q.name.value.trim();
    if (!name) {
      refuse(q.box, t("i_need_name"));
      q.name.focus();
      return;
    }
    const chosen = Array.from(q.groups.querySelectorAll("input:checked")).map(c => c.value);
    body = { action: "approve", id: r.id, name: name, grant: q.grant.value.trim(), group: chosen,
      english: q.english.checked };
    title = t("q_approve_new_title", { id: r.id, who: r.display, name: name });
  }
  working(q.box);
  const res = await post("request", body);
  if (res.ok) closeApprove();
  await changed(res, title);
}

async function decline(r) {
  if (busy()) return;
  const vars = { id: r.id, who: r.display };
  if (!(await ask(t("q_decline_q", vars), { note: t("q_decline_note"), go: t("q_decline") }))) return;
  working(q.box);
  if (current && current.id === r.id) closeApprove();
  await changed(await post("request", { action: "decline", id: r.id }), t("q_decline_title", vars));
}

async function forget(r) {
  if (busy()) return;
  const vars = { id: r.id, who: r.display };
  if (!(await ask(t("q_forget_q", vars), { note: t("q_forget_note"), go: t("q_forget") }))) return;
  working(q.box);
  if (current && current.id === r.id) closeApprove();
  await changed(await post("request", { action: "forget", id: r.id }), t("q_forget_title", vars));
}

// ---------- general links ----------

function linkState(l) {
  if (l.state === "open") return t("gl_state_open", { time: stamp(l.expires), uses: l.uses_most });
  if (l.state === "expired") return t("gl_state_expired", { time: stamp(l.expires) });
  if (l.state === "full") return t("gl_state_full", { requests: plural(l.uses_most, "request") });
  return l.stopped ? t("gl_state_off_since", { time: stamp(l.stopped) }) : t("gl_state_off");
}

async function loadLinks() {
  const group = q.lGroup.value;
  const res = await get("general-links", group ? { group: group } : null);
  if (!res.ok) {
    links = [];
    clear(q.lCount).append(h("span", { class: "error" }, res.error));
  } else {
    links = res.result.links;
    const open = links.filter(l => l.state === "open").length;
    q.lCount.textContent = links.length ? t("gl_count", { links: plural(links.length, "general_link"), open: open })
      : t("gl_none");
  }
  fill(q.lTable, [t("gl_col_number"), t("gl_col_group"), t("gl_col_made"), t("gl_col_state"), t("gl_col_uses"),
    t("gl_col_waiting"), ""], links.map(l => h("tr", { class: l.state === "open" ? "" : "off", "data-link": String(l.id) },
    td(String(l.id), "num"), td(l.group, "name"), td(stamp(l.created), "nowrap"), td(linkState(l)),
    td(String(l.uses), "num"), td(String(l.waiting), "num"),
    td(l.active ? button(t("gl_off"), () => switchOff(l.group), { class: "act small danger", "data-gl-off": l.group })
      : null, "nowrap"))));
  q.lTable.hidden = links.length === 0;
}

function whole(input) {
  const v = input.value.trim();
  if (!v) return null;
  const n = Number(v);
  return n >= 1 && Math.floor(n) === n ? n : NaN;
}

async function makeLink() {
  if (busy()) return;
  const group = q.newGroup.value;
  const days = whole(q.days);
  const uses = whole(q.uses);
  if (!group) {
    refuse(q.lBox, t("gl_need_group"));
    return;
  }
  if ((days !== null && isNaN(days)) || (uses !== null && isNaN(uses))) {
    refuse(q.lBox, t("gl_need_numbers"));
    return;
  }
  // Whether the group has a link that takes requests now, which the new one stops: read now, since the list shown
  // may be another group's.
  const now = await get("general-links", { group: group });
  const open = now.ok && now.result.links.some(l => l.active);
  const vars = { group: group, days: days || defaults.general_days, uses: uses || defaults.general_uses };
  if (!(await ask(t("gl_new_q", vars), { note: t(open ? "gl_new_note_replaces" : "gl_new_note", vars), go: t("gl_new") }))) return;
  working(q.lBox);
  const body = { action: "new", group: group };
  if (days !== null) body.days = days;
  if (uses !== null) body.uses = uses;
  const res = await post("general-link", body);
  const shown = res.ok && res.result && res.result.link ? [{ name: group, link: res.result.link }] : [];
  answer(q.lBox, res, { title: t("gl_new_title", { group: group }), links: shown });
  if (res.ok) {
    q.days.value = "";
    q.uses.value = "";
  }
  await loadLinks();
}

async function switchOff(group) {
  if (busy()) return;
  if (!(await ask(t("gl_off_q", { group: group }), { note: t("gl_off_note"), go: t("gl_off") }))) return;
  working(q.lBox);
  answer(q.lBox, await post("general-link", { action: "off", group: group }), { title: t("gl_off_title", { group: group }) });
  await loadLinks();
}

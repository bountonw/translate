// Groups: the list, with the switch of each group, and create; for the group opened: switch it on or off, remove
// it, open or close chapters for the group, give each current member their own copy of chapters, its own English
// and features, its members (add them from the reader list or a CSV file, take them out, list them in the Readers
// section), and new links for every member. Each group choice is its own button and asks once, with the
// sentence of what it changes.
import { get, post, busy } from "./api.js";
import { h, clear, button, field, fill, td, answer, ask, refuse, working, stamp, compact, csvRows, readFile } from "./ui.js";
import { t, plural } from "./words.js";
import { featureSelect } from "./shared.js";
import { showGroup } from "./readers.js";

const g = {};
let built = false;
let groups = [];
let failed = "";
let current = "";
let memberSel = {};
let found = [];
let foundSel = {};
let seq = 0;
let timer = 0;

export async function show(root) {
  if (!built) {
    build(root);
    built = true;
  }
  await load();
}

function build(root) {
  g.count = h("p", { class: "count", id: "g-count" });
  g.table = h("table", { class: "list", id: "g-table" });
  g.newName = h("input", { type: "text", id: "g-new-name", autocomplete: "off", spellcheck: "false" });
  g.newGrant = h("input", { type: "text", id: "g-new-grant", placeholder: t("spec_placeholder_book"), autocomplete: "off",
    spellcheck: "false" });
  g.newEnglish = h("input", { type: "checkbox", id: "g-new-english" });
  g.newBox = h("div", { class: "answer", id: "g-new-answer", hidden: true, "aria-live": "polite" });
  g.listBox = h("div", { class: "answer", id: "g-list-answer", hidden: true, "aria-live": "polite" });
  root.append(h("h2", null, t("g_title")), g.count, h("div", { class: "scroll" }, g.table), g.listBox,
    h("h3", null, t("g_create_title")),
    h("div", { class: "row" },
      field(t("name"), g.newName, t("g_name_hint")),
      field(t("chapters"), g.newGrant, t("g_create_chapters_hint")),
      h("label", { class: "check" }, g.newEnglish, " " + t("english")),
      button(t("g_create"), create, { id: "g-create" })),
    g.newBox,
    buildPanel());
}

function buildPanel() {
  g.panel = h("div", { class: "panel", id: "g-panel", hidden: true });
  g.title = h("h3", { id: "g-title" });
  g.line = h("p", { id: "g-line" });
  g.toggle = button(t("g_switch_off"), () => groupAct(group(), "switch"), { id: "g-toggle" });
  g.spec = h("input", { type: "text", id: "g-spec", placeholder: t("spec_placeholder"), autocomplete: "off",
    spellcheck: "false" });
  g.feature = featureSelect("g-feature");
  g.members = h("table", { class: "list", id: "g-members" });
  g.memberCount = h("p", { class: "count", id: "g-member-count" });
  g.outFile = h("input", { type: "file", id: "g-out-file", accept: ".csv,text/csv" });
  g.find = h("input", { type: "search", id: "g-find", placeholder: t("r_name_placeholder"), autocomplete: "off" });
  g.found = h("table", { class: "list", id: "g-found" });
  g.foundCount = h("p", { class: "count", id: "g-found-count" });
  g.inFile = h("input", { type: "file", id: "g-in-file", accept: ".csv,text/csv" });
  g.box = h("div", { class: "answer", id: "g-answer", hidden: true, "aria-live": "polite" });
  g.find.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(findReaders, 200);
  });
  const act = (action, state) => () => groupAct(group(), action, state);
  g.panel.append(g.title, g.line, g.box,
    h("h4", null, t("g_itself")),
    h("div", { class: "row" }, g.toggle, button(t("g_remove"), act("remove"), { id: "g-remove", class: "act danger" })),
    h("div", { class: "row" }, field(t("chapters"), g.spec),
      button(t("g_open"), act("open"), { id: "g-open" }),
      button(t("g_close"), act("close"), { id: "g-close" }),
      button(t("g_give_each"), act("give-each"), { id: "g-give-each" })),
    h("p", { class: "hint" }, t("g_chapters_hint")),
    h("div", { class: "row" },
      button(t("english_on"), act("english", "on"), { id: "g-english-on" }),
      button(t("english_off"), act("english", "off"), { id: "g-english-off" }),
      h("span", { class: "gap" }), field(t("feature"), g.feature),
      button(t("on"), act("feature", "on"), { id: "g-feature-on" }),
      button(t("off"), act("feature", "off"), { id: "g-feature-off" })),
    h("h4", null, t("g_members")), g.memberCount, h("div", { class: "scroll short" }, g.members),
    h("div", { class: "row" }, button(t("g_take_out"), () => takeOut(), { id: "g-take-out" }),
      h("span", { class: "gap" }), field(t("g_csv"), g.outFile),
      button(t("g_take_out_file"), () => fromFile("take-out"), { id: "g-take-out-file" })),
    h("div", { class: "row" }, button(t("g_in_readers"), () => { const x = group(); if (x) showGroup(x.name); },
      { id: "g-in-readers", class: "plain" }), h("span", { class: "hint" }, t("g_in_readers_hint"))),
    h("h4", null, t("g_add_title")),
    h("div", { class: "row" }, field(t("g_find"), g.find),
      button(t("g_list_all"), () => { g.find.value = ""; findReaders(true); }, { id: "g-list-all", class: "plain" })),
    g.foundCount, h("div", { class: "scroll short" }, g.found),
    h("div", { class: "row" }, button(t("g_add"), () => addFound(), { id: "g-add" }),
      h("span", { class: "gap" }), field(t("g_csv"), g.inFile),
      button(t("g_add_file"), () => fromFile("add"), { id: "g-add-file" })),
    h("h4", null, t("g_relink_title")),
    h("p", { class: "hint" }, t("g_relink_hint")),
    h("div", { class: "row" }, button(t("g_relink"), () => relinkAll(), { id: "g-relink" })));
  return g.panel;
}

async function load() {
  const res = await get("groups");
  if (res.ok) {
    groups = res.result.groups;
    failed = "";
  } else {
    failed = res.error;
  }
  renderList();
  renderPanel();
}

function group() {
  for (let i = 0; i < groups.length; i++) if (groups[i].name === current) return groups[i];
  return null;
}

function describe(x) {
  return t("g_line", { name: x.name, state: x.active ? t("is_on") : t("is_off"), chapters: compact(x.grants) || t("nothing"),
    english: x.english ? t("is_on") : t("is_off"), members: plural(x.members.length, "member") });
}

function renderList() {
  if (failed) clear(g.count).append(h("span", { class: "error" }, failed));
  else g.count.textContent = groups.length ? t("g_count", { groups: plural(groups.length, "group") }) : t("g_none");
  fill(g.table, [t("g_col_name"), t("g_col_state"), t("g_col_chapters"), t("g_col_english"), t("g_col_members"),
    t("g_col_created"), ""], groups.map(x =>
    h("tr", { class: (x.active ? "" : "off") + (x.name === current ? " current" : ""), "data-group": x.name },
      td(x.name, "name"),
      // The group switch: on or off, for the whole group, from its row.
      td([x.active ? t("is_on") : t("is_off"), " ", button(x.active ? t("g_switch_off") : t("g_switch_on"),
        () => groupAct(x, "switch", null, g.listBox), { class: x.active ? "plain small" : "act small",
          "data-group-switch": x.name })], "nowrap"),
      td(compact(x.grants) || t("nothing")), td(x.english ? t("is_on") : t("is_off")),
      td(String(x.members.length), "num"), td(stamp(x.created), "nowrap"),
      td(button(x.name === current ? t("g_shown") : t("g_open_row"), () => openGroup(x.name),
        { class: "plain", id: "g-open-" + x.name })))));
}

function openGroup(name) {
  if (current !== name) {
    current = name;
    memberSel = {};
    found = [];
    foundSel = {};
    g.find.value = "";
    clear(g.box);
    g.box.hidden = true;
  }
  renderList();
  renderPanel();
  if (g.panel.scrollIntoView) g.panel.scrollIntoView({ block: "start" });
}

function renderPanel() {
  const x = group();
  g.panel.hidden = !x;
  if (!x) return;
  g.title.textContent = t("g_panel_title", { name: x.name });
  g.line.textContent = describe(x);
  g.toggle.textContent = x.active ? t("g_switch_off") : t("g_switch_on");
  const keep = {};
  x.members.forEach(m => { if (memberSel[m.id]) keep[m.id] = m; });
  memberSel = keep;
  const all = h("input", { type: "checkbox", id: "g-members-all", "aria-label": t("g_select_members") });
  all.checked = x.members.length > 0 && x.members.every(m => memberSel[m.id]);
  all.addEventListener("change", () => {
    memberSel = {};
    if (all.checked) x.members.forEach(m => { memberSel[m.id] = m; });
    renderPanel();
  });
  fill(g.members, [all, t("r_col_name"), t("r_col_link")], x.members.map(m => {
    const box = h("input", { type: "checkbox", "aria-label": t("select_one", { name: m.name }), "data-member": m.name });
    box.checked = !!memberSel[m.id];
    box.addEventListener("change", () => {
      if (box.checked) memberSel[m.id] = m;
      else delete memberSel[m.id];
      renderPanel();
    });
    return h("tr", { class: m.active ? "" : "revoked" }, td(box, "pick"), td(m.name, "name"),
      td(m.active ? t("r_works") : t("r_stopped")));
  }));
  const picked = Object.keys(memberSel).length;
  g.memberCount.textContent = t("g_member_count", { members: plural(x.members.length, "member") }) +
    (picked ? " " + t("n_selected", { n: picked }) : "");
  renderFound();
}

async function findReaders(everyone) {
  clearTimeout(timer);
  const text = g.find.value.trim();
  const mine = ++seq;
  if (!text && everyone !== true) {
    found = [];
    renderFound();
    return;
  }
  const res = await get("readers", text ? { name: text } : {});
  if (mine !== seq) return;
  found = res.ok ? res.result.readers : [];
  if (!res.ok) g.foundCount.textContent = res.error;
  renderFound();
}

function renderFound() {
  const x = group();
  if (!x) return;
  const inside = {};
  x.members.forEach(m => { inside[m.id] = true; });
  const list = found.filter(r => !inside[r.id]);
  const keep = {};
  list.forEach(r => { if (foundSel[r.id]) keep[r.id] = r; });
  foundSel = keep;
  const all = h("input", { type: "checkbox", id: "g-found-all", "aria-label": t("g_select_found") });
  all.checked = list.length > 0 && list.every(r => foundSel[r.id]);
  all.addEventListener("change", () => {
    foundSel = {};
    if (all.checked) list.forEach(r => { foundSel[r.id] = r; });
    renderFound();
  });
  fill(g.found, [all, t("r_col_name"), t("r_col_link"), t("r_col_groups")], list.map(r => {
    const box = h("input", { type: "checkbox", "aria-label": t("select_one", { name: r.name }), "data-found": r.name });
    box.checked = !!foundSel[r.id];
    box.addEventListener("change", () => {
      if (box.checked) foundSel[r.id] = r;
      else delete foundSel[r.id];
      renderFound();
    });
    return h("tr", { class: r.active ? "" : "revoked" }, td(box, "pick"), td(r.name, "name"),
      td(r.active ? t("r_works") : t("r_stopped")), td((r.groups || []).join(", ")));
  }));
  g.found.hidden = list.length === 0;
  const picked = Object.keys(foundSel).length;
  g.foundCount.textContent = g.find.value.trim() || found.length
    ? t("g_found", { readers: plural(list.length, "reader") }) + (picked ? " " + t("n_selected", { n: picked }) : "")
    : t("g_find_hint");
}

async function create() {
  if (busy()) return;
  const name = g.newName.value.trim();
  if (!name) {
    refuse(g.newBox, t("g_need_name"));
    return;
  }
  working(g.newBox);
  const res = await post("group", { action: "create", group: name, grant: g.newGrant.value.trim(),
    english: g.newEnglish.checked });
  answer(g.newBox, res, { title: t("g_create_answer", { name: name }) });
  if (res.ok) {
    g.newName.value = "";
    g.newGrant.value = "";
    g.newEnglish.checked = false;
    current = name;
  }
  await load();
}

// What each group choice asks, before it runs: the sentence of what the command changes.
function question(x, action, spec, state, feature) {
  const v = { group: x.name, spec: spec, feature: feature, members: plural(x.members.length, "member") };
  const off = x.active ? "" : " " + t("g_is_off_note");
  if (action === "open") return [t("g_open_q", v), t("g_open_note", v) + off];
  if (action === "close") return [t("g_close_q", v), t("g_close_note", v)];
  if (action === "give-each") return [t("g_give_each_q", v), t("g_give_each_note", v)];
  if (action === "on") return [t("g_on_q", v), t("g_on_note", v)];
  if (action === "off") return [t("g_off_q", v), t("g_off_note", v)];
  if (action === "remove") return [t("g_remove_q", v), t("g_remove_note", v)];
  if (action === "english") return [t(state === "on" ? "g_english_on_q" : "g_english_off_q", v), t("g_setting_note", v) + off];
  return [t(state === "on" ? "g_feature_on_q" : "g_feature_off_q", v), t("g_setting_note", v) + off];
}

async function groupAct(x, action, state, box) {
  if (busy() || !x) return;
  box = box || g.box;
  if (action === "switch") action = x.active ? "off" : "on";
  const spec = g.spec.value.trim();
  const feature = g.feature.value;
  let args = [];
  if (action === "open" || action === "close" || action === "give-each") {
    if (!spec) {
      refuse(box, t("need_spec"));
      g.spec.focus();
      return;
    }
    args = [spec];
  } else if (action === "english") {
    args = [state];
  } else if (action === "feature") {
    if (!feature) return;
    args = [feature, state];
  }
  const say = question(x, action, spec, state, feature);
  if (!(await ask(say[0], { note: say[1], go: t("go_on"), list: action === "give-each" ? x.members.map(m => m.name) : [] }))) return;
  working(box);
  const res = await post("group", { action: action, group: x.name, args: args });
  answer(box, res, { title: say[0].replace(/\?$/, ""), after: load, members: x.members.map(m => m.name) });
  await load();
}

async function changeMembers(action, list) {
  const x = group();
  if (!x || !list.length) return;
  const v = { readers: plural(list.length, "reader"), group: x.name };
  const q = action === "add" ? t("g_add_q", v) : t("g_take_out_q", v);
  if (list.length > 1 && !(await ask(q, { list: list, go: action === "add" ? t("g_add_go") : t("g_take_out_go"),
    note: action === "add" ? t("g_add_note") : t("g_take_out_note") }))) return;
  working(g.box);
  const res = await post("group", { action: action, group: x.name, args: list });
  answer(g.box, res, { title: q.replace(/\?$/, ""), after: load });
  memberSel = {};
  foundSel = {};
  await load();
}

function takeOut() {
  if (busy()) return;
  return changeMembers("take-out", Object.keys(memberSel).map(id => memberSel[id].name));
}

function addFound() {
  if (busy()) return;
  return changeMembers("add", Object.keys(foundSel).map(id => foundSel[id].name));
}

async function fromFile(action) {
  if (busy()) return;
  const x = group();
  if (!x) return;
  const input = action === "add" ? g.inFile : g.outFile;
  const file = await readFile(input);
  if (!file) {
    refuse(g.box, t("g_need_file"));
    return;
  }
  const n = csvRows(file.text);
  const v = { readers: plural(n, "reader"), file: file.name, group: x.name };
  const q = action === "add" ? t("g_add_file_q", v) : t("g_take_out_file_q", v);
  if (n > 1 && !(await ask(q, { go: action === "add" ? t("g_add_go") : t("g_take_out_go"), note: t("g_file_note") }))) return;
  working(g.box);
  const res = await post("group", { action: action, group: x.name, csv: file.text, filename: file.name });
  answer(g.box, res, { title: q.replace(/\?$/, ""), after: load });
  if (res.ok) input.value = "";
  await load();
}

async function relinkAll() {
  if (busy()) return;
  const x = group();
  if (!x) return;
  let count = x.members.length;
  if (!count) {
    refuse(g.box, t("g_relink_none", { group: x.name }));
    return;
  }
  if (!(await ask(t("g_relink_q", { members: plural(count, "member"), group: x.name }),
    { list: x.members.map(m => m.name), note: t("g_relink_note"), go: t("r_relink_go") }))) return;
  working(g.box);
  let res = await post("relink", { group: x.name, confirm: count });
  // The group changed after this page read it: the command names the number it now holds and changes nothing.
  const m = res.ok ? null : /This gives (\d+) readers/.exec(res.error);
  if (m && Number(m[1]) !== count) {
    count = Number(m[1]);
    if (await ask(t("g_relink_again_q", { group: x.name, members: plural(count, "member") }),
      { note: t("g_relink_note"), go: t("r_relink_go") })) {
      res = await post("relink", { group: x.name, confirm: count });
    }
  }
  answer(g.box, res, { title: t("g_relink_title_answer", { group: x.name }) });
  await load();
}

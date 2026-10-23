// Devices, in the Readers section (README.md, "Link signs in"): the devices of the links that sign in by themselves,
// with the two-device lock: the devices waiting for approval, as
// review.py devices lists them, or every device of one reader's link, and with "earlier links" those of the
// links the reader no longer has (devices NAME --all); approve and remove one device, or the devices ticked in one
// request (device approve|remove NUMBER [NUMBER ...]).
import { get, post, busy } from "./api.js";
import { h, clear, button, field, fill, td, answer, ask, working, stamp } from "./ui.js";
import { t, plural } from "./words.js";
import { showWaiting, countWaiting } from "./shared.js";

const v = {};
let rows = [];
let who = "";          // the reader whose devices are shown, or "" for the devices waiting for approval
let failed = "";
let selected = {};
let after = null;
let seq = 0;

// The panel, under the reader list; done() runs after a change, so the list shows the new counts.
export function build(root, done) {
  after = done;
  v.name = h("input", { type: "text", id: "v-name", list: "r-names", autocomplete: "off", placeholder: t("whole_name") });
  v.all = h("input", { type: "checkbox", id: "v-all" });
  v.count = h("p", { class: "count", id: "v-count", "aria-live": "polite" });
  v.table = h("table", { class: "list", id: "v-table" });
  v.box = h("div", { class: "answer", id: "v-answer", hidden: true, "aria-live": "polite" });
  v.approve = button(t("v_approve_selected"), () => act("approve", picked()), { id: "v-approve" });
  v.remove = button(t("v_remove_selected"), () => act("remove", picked()), { id: "v-remove", class: "act danger" });
  v.all.addEventListener("change", () => { if (who) load(); });
  v.name.addEventListener("keydown", e => { if (e.key === "Enter") ofReader(v.name.value.trim()); });
  v.panel = h("div", { id: "v-panel" },
    h("h3", null, t("v_title")),
    h("p", { class: "hint" }, t("v_hint")),
    h("div", { class: "row" },
      button(t("v_show_waiting"), () => { who = ""; load(); }, { id: "v-waiting", class: "plain" }),
      h("span", { class: "gap" }),
      field(t("reader"), v.name),
      h("label", { class: "check" }, v.all, " " + t("v_all")),
      button(t("v_show_reader"), () => ofReader(v.name.value.trim()), { id: "v-show" })),
    v.count,
    h("div", { class: "scroll short" }, v.table),
    h("div", { class: "row" }, v.approve, v.remove),
    v.box);
  root.append(v.panel);
}

// Show every device of one reader, as review.py devices NAME does.
export function ofReader(name) {
  if (!name) {
    v.name.focus();
    return;
  }
  v.name.value = name;
  who = name;
  load();
  if (v.panel.scrollIntoView) v.panel.scrollIntoView({ block: "start" });
}

export async function load() {
  const mine = ++seq;
  const res = who ? await get("devices", { name: who, all: v.all.checked }) : await get("devices");
  if (mine !== seq) return;
  if (res.ok) {
    rows = res.result.devices;
    failed = "";
    if (!who) showWaiting(rows.filter(d => d.state === "waiting").length);
  } else {
    rows = [];
    failed = res.error;
  }
  render();
}

function picked() {
  return rows.filter(d => selected[d.id]).map(d => d.id);
}

function stateText(d) {
  if (d.state === "ok") return t("v_state_ok");
  if (d.state === "waiting") return t("v_state_waiting");
  return t("v_state_removed");
}

function render() {
  const keep = {};
  rows.forEach(d => { if (selected[d.id]) keep[d.id] = true; });
  selected = keep;
  const all = h("input", { type: "checkbox", id: "v-select-all", "aria-label": t("v_select_all") });
  all.checked = rows.length > 0 && rows.every(d => selected[d.id]);
  all.addEventListener("change", () => {
    selected = {};
    if (all.checked) rows.forEach(d => { selected[d.id] = true; });
    render();
  });
  fill(v.table, [all, t("v_col_number"), t("v_col_reader"), t("v_col_device"), t("v_col_state"), t("v_col_first"),
    t("v_col_last"), t("v_col_link"), ""], rows.map(d => {
    const box = h("input", { type: "checkbox", "aria-label": t("select_one", { name: String(d.id) }),
      "data-device": String(d.id) });
    box.checked = !!selected[d.id];
    box.addEventListener("change", () => {
      if (box.checked) selected[d.id] = true;
      else delete selected[d.id];
      render();
    });
    const acts = [];
    if (d.state !== "ok") {
      acts.push(button(t("v_approve"), () => act("approve", [d.id]), { class: "act small", "data-approve": String(d.id) }));
    }
    if (d.state !== "removed") {
      acts.push(button(t("v_remove"), () => act("remove", [d.id]), { class: "act small danger",
        "data-remove": String(d.id) }));
    }
    return h("tr", { class: d.state, "data-device": String(d.id) }, td(box, "pick"), td(String(d.id), "num"),
      td(d.name, "name"), td(d.agent), td(stateText(d), "nowrap"), td(stamp(d.first_seen), "nowrap"),
      td(stamp(d.last_seen), "nowrap"), td(d.current ? t("v_link_current") : t("v_link_earlier"), "nowrap"),
      td(acts, "nowrap"));
  }));
  v.table.hidden = rows.length === 0;
  const n = picked().length;
  if (failed) {
    clear(v.count).append(h("span", { class: "error" }, failed));
  } else if (who) {
    v.count.textContent = rows.length ? t("v_count_reader", { devices: plural(rows.length, "device"), name: who })
      : t("v_none_reader", { name: who });
  } else {
    v.count.textContent = rows.length ? t("v_count_waiting", { devices: plural(rows.length, "device") })
      : t("v_none_waiting");
  }
  if (n) v.count.textContent += " " + t("n_selected", { n: n });
  v.approve.disabled = n === 0;
  v.remove.disabled = n === 0;
}

async function act(action, ids) {
  if (busy() || !ids.length) return;
  const n = plural(ids.length, "device");
  if (ids.length > 1) {
    const question = action === "approve" ? t("v_approve_q", { devices: n }) : t("v_remove_q", { devices: n });
    const list = rows.filter(d => ids.indexOf(d.id) >= 0).map(d => d.id + ". " + d.name + ": " + d.agent);
    if (!(await ask(question, { list: list, note: action === "approve" ? t("v_approve_note") : t("v_remove_note"),
      go: action === "approve" ? t("v_approve") : t("v_remove") }))) return;
  }
  working(v.box);
  const res = action === "approve" ? await post("device", { action: "approve", ids: ids })
    : await post("device", { action: "remove", ids: ids });
  answer(v.box, res, { title: action === "approve" ? t("v_approve_title", { devices: n }) : t("v_remove_title", { devices: n }) });
  selected = {};
  await load();
  if (who) await countWaiting();
  if (after) await after();
}

// What every section of the admin page shares: building elements, showing an answer, asking before a change
// to many readers, copying a link, and the small text helpers. Names and other data always go in as text.
import { get, post, busy } from "./api.js";
import { t, plural } from "./words.js";

export function h(tag, attrs) {
  const el = document.createElement(tag);
  if (attrs) {
    Object.keys(attrs).forEach(k => {
      const v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k.slice(0, 2) === "on" && typeof v === "function") el.addEventListener(k.slice(2), v);
      else if (k === "value" || k === "checked" || k === "disabled" || k === "hidden") el[k] = v;
      else el.setAttribute(k, v === true ? "" : String(v));
    });
  }
  for (let i = 2; i < arguments.length; i++) add(el, arguments[i]);
  return el;
}

function add(el, kid) {
  if (kid === null || kid === undefined || kid === false) return;
  if (Array.isArray(kid)) kid.forEach(k => add(el, k));
  else el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
}

export function field(label, input, hint) {
  return h("label", { class: "field" }, h("span", { class: "label" }, label), input,
    hint ? h("span", { class: "hint" }, hint) : null);
}

export function button(text, onclick, more) {
  return h("button", Object.assign({ type: "button", class: "act", onclick: onclick }, more || {}), text);
}

export function clear(el) {
  el.textContent = "";
  return el;
}

// A table's head and body; rows are <tr> elements.
export function fill(table, heads, rows) {
  clear(table);
  table.append(h("thead", null, h("tr", null, heads.map(x =>
    h("th", { scope: "col", class: x instanceof Element && x.type === "checkbox" ? "pick" : null }, x)))));
  table.append(h("tbody", null, rows));
}

export function td(content, cls) {
  return h("td", cls ? { class: cls } : null, content);
}

export function stamp(iso) {
  return iso ? t("stamp", { time: iso.slice(0, 16).replace("T", " ") }) : t("never");
}

// A UTC time of the server in Thailand time (UTC+7, with no summer time), as the commands write it.
export function thaiTime(iso) {
  const ms = Date.parse(iso);
  return isNaN(ms) ? String(iso) : new Date(ms + 7 * 3600 * 1000).toISOString().slice(0, 16).replace("T", " ");
}

export function size(bytes) {
  if (bytes < 1024) return plural(bytes, "byte");
  if (bytes < 1024 * 1024) return t("size_kib", { n: (bytes / 1024).toFixed(1) });
  return t("size_mib", { n: (bytes / 1024 / 1024).toFixed(1) });
}

export function pad(n) {
  return n < 10 ? "0" + n : String(n);
}

// Grant labels as review.py shows them: SC01, SC02, SC03 and SC05 become "SC01-03, SC05".
export function compact(labels) {
  const whole = [];
  const nums = {};
  labels.forEach(label => {
    const m = /^([A-Z]{1,10})(\d{1,3})$/.exec(label);
    if (m) (nums[m[1]] = nums[m[1]] || []).push(Number(m[2]));
    else whole.push(label);
  });
  const out = whole.slice();
  Object.keys(nums).sort().forEach(book => {
    const ns = Array.from(new Set(nums[book])).sort((a, b) => a - b);
    let start = ns[0];
    let prev = ns[0];
    for (let i = 1; i <= ns.length; i++) {
      if (i < ns.length && ns[i] === prev + 1) {
        prev = ns[i];
        continue;
      }
      out.push(book + pad(start) + (prev > start ? "-" + pad(prev) : ""));
      start = prev = ns[i];
    }
  });
  return out.join(", ");
}

// The number of records after the header line of a CSV file, without empty lines; quoted fields may hold commas
// and line breaks.
export function csvRows(text) {
  let rows = 0;
  let quoted = false;
  let filled = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === "\"") {
        if (text[i + 1] === "\"") i++;
        else quoted = false;
      }
      filled = true;
    } else if (c === "\"") {
      quoted = true;
      filled = true;
    } else if (c === "\n" || c === "\r") {
      if (filled) rows++;
      filled = false;
    } else if (c !== " " && c !== "\t" && c !== ",") {
      filled = true;
    }
  }
  if (filled) rows++;
  return Math.max(rows - 1, 0);
}

export function names(list, most) {
  most = most || 20;
  const shown = list.slice(0, most).join(", ");
  return list.length > most ? t("names_more", { names: shown, more: plural(list.length - most, "other") }) : shown;
}

// The words of a command line as a POSIX shell reads them, as review.py quotes names with shlex.quote:
// 'Mali Boon' is one word, and 'O'"'"'Brien' is O'Brien. null when a quote is left open.
export function shellWords(text) {
  const out = [];
  let word = null;
  let i = 0;
  while (i < text.length) {
    const c = text[i];
    if (c === " " || c === "\t") {
      if (word !== null) out.push(word);
      word = null;
      i++;
      continue;
    }
    if (word === null) word = "";
    if (c === "'") {
      const j = text.indexOf("'", i + 1);
      if (j < 0) return null;
      word += text.slice(i + 1, j);
      i = j + 1;
    } else if (c === "\"") {
      let j = i + 1;
      while (j < text.length && text[j] !== "\"") {
        if (text[j] === "\\" && j + 1 < text.length) j++;
        word += text[j];
        j++;
      }
      if (j >= text.length) return null;
      i = j + 1;
    } else if (c === "\\") {
      word += text[i + 1] || "";
      i += 2;
    } else {
      word += c;
      i++;
    }
  }
  if (word !== null) out.push(word);
  return out;
}

// ---------- asking first ----------

export function ask(message, more) {
  more = more || {};
  const dlg = document.getElementById("ask");
  const list = clear(document.getElementById("ask-list"));
  const go = document.getElementById("ask-go");
  const cancel = document.getElementById("ask-cancel");
  document.getElementById("ask-text").textContent = message;
  const items = more.list || [];
  items.slice(0, 20).forEach(n => list.append(h("li", null, n)));
  if (items.length > 20) list.append(h("li", null, t("and_more", { more: plural(items.length - 20, "other") })));
  list.hidden = items.length === 0;
  document.getElementById("ask-more").textContent = more.note || "";
  go.textContent = more.go || t("go_on");
  return new Promise(resolve => {
    function done(value) {
      go.onclick = null;
      cancel.onclick = null;
      dlg.oncancel = null;
      if (dlg.open) dlg.close();
      resolve(value);
    }
    go.onclick = () => done(true);
    cancel.onclick = () => done(false);
    dlg.oncancel = e => { e.preventDefault(); done(false); };
    dlg.showModal();
    cancel.focus();
  });
}

// ---------- copying a link ----------

function copyRow(item) {
  const input = h("input", { type: "text", readonly: true, value: item.link, class: "link", "aria-label": t("link") });
  const note = h("span", { class: "copied", "aria-live": "polite" });
  const copy = button(t("copy"), () => {
    function fallback() {
      input.focus();
      input.select();
      let done = false;
      try { done = document.execCommand("copy"); } catch (e) { done = false; }
      note.textContent = done ? t("copied") : t("copy_by_hand");
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(item.link).then(() => { note.textContent = t("copied"); }, fallback);
    } else {
      fallback();
    }
  }, { class: "copy" });
  // A line about the link itself, such as a reader whose link stays stopped (review.py relink).
  return h("div", { class: "linkrow" }, h("span", { class: "who" }, item.name), input, copy, note,
    item.note ? h("p", { class: "linknote" }, item.note) : null);
}

// ---------- the next command a command names ----------

// How many members a group has now, for the question before a step that changes them; -1 when not known.
async function memberCount(name) {
  const res = await get("groups");
  const list = res.ok ? res.result.groups : [];
  for (let i = 0; i < list.length; i++) {
    if (list[i].name.toLowerCase() === name.toLowerCase()) return list[i].members.length;
  }
  return -1;
}

function groupNote(group, n, note) {
  return (n >= 0 ? t("next_group_count", { group: group, members: plural(n, "member") }) + " " : "") + note;
}

// "N members of G still open SC01 or part of it through their own chapters: ... To close it for them:
// review.py close 'Own Reader' SC01": the same close for the readers named. The chapters are those the line
// names after "still open", which may be a list such as "SC01, SC03". With more than 20 readers the line names no
// command line of names, and the page takes the group's members, for whom close changes only those who hold the
// chapters as their own: the members the Groups section read before the change (members), which a removed group
// no longer has, or else the members it has now.
function closeOwn(m, members) {
  const group = m[1];
  const label = m[2];
  const spec = label.replace(/\s+/g, "");
  const more = /^NAME \[NAME \.\.\.\] (.+), with their names$/.exec(m[3]);
  const many = !!more && more[1].replace(/\s+/g, "") === spec;
  // The command writes the chapters as one argument, SC01,SC03; older lines wrote "SC01, SC03".
  const tail = [" " + spec, " " + label].find(x => m[3].slice(-x.length) === x);
  if (!many && !tail) return null;
  const list = many ? (members && members.length ? members : null) : shellWords(m[3].slice(0, -tail.length));
  if (!many && (!list || !list.length)) return null;
  return {
    label: many ? t("next_close_members", { spec: spec, group: group })
      : t("next_close_own", { spec: spec, readers: plural(list.length, "reader") }),
    names: list,
    spec: spec,
    prepare: list ? null : async () => {
      const res = await get("readers", { group: group });
      return { list: res.ok ? res.result.readers.map(r => r.name) : [], error: res.error };
    },
    question: n => t("next_close_own_q", { spec: spec, readers: plural(n, "reader") }),
    note: () => t("next_close_own_note"),
    send: list2 => post("close", { names: list2, spec: spec })
  };
}

const NEXT = [
  [/^\d+ members? of (\S+) still open (.+?) or part of it through their own chapters: .* To close it for them: review\.py close (.+)$/,
    closeOwn],
  [/To close it for the whole group: review\.py group close (\S+) (\S+)$/, m => ({
    label: t("next_group_close", { spec: m[2], group: m[1] }), group: m[1],
    question: () => t("g_close_q", { spec: m[2], group: m[1] }),
    note: n => groupNote(m[1], n, t("next_group_close_note")),
    send: () => post("group", { action: "close", group: m[1], args: [m[2]] }) })],
  [/review\.py group on (\S+)$/, m => ({
    label: t("next_group_on", { group: m[1] }), group: m[1],
    question: () => t("g_on_q", { group: m[1] }),
    note: n => groupNote(m[1], n, t("next_group_on_note")),
    send: () => post("group", { action: "on", group: m[1] }) })],
  [/review\.py groups\)?$/, () => ({ label: t("next_show_groups"), go: "#groups" })],
  [/review\.py group add \S+ NAME\)?$/, () => ({ label: t("next_show_groups"), go: "#groups" })],
  [/review\.py readers --name TEXT$/, () => ({ label: t("next_show_readers"), go: "#readers" })],
  [/review\.py export --round NAME\)?$/, () => ({ label: t("next_show_comments"), go: "#comments" })],
  // Signing in: a reader with no way left to sign in needs a new link, which is shown once with
  // a Copy button; a declined request is forgotten; the requests and general links are in the Requests section.
  [/review\.py relink ((?!NAME ).+)$/, m => {
    // Only a line that ends with the command: a ; outside quotes means more of the line follows the names.
    const list = /;/.test(m[1].replace(/'[^']*'/g, "")) ? null : shellWords(m[1]);
    if (!list || !list.length) return null;
    return {
      label: t("next_relink", { readers: list.length === 1 ? list[0] : plural(list.length, "reader") }), names: list,
      question: () => t("next_relink_q", { readers: list.length === 1 ? list[0] : plural(list.length, "reader") }),
      note: () => t("next_relink_note"),
      send: () => post("relink", { names: list }),
      links: res => res.ok && res.result && res.result.readers ? res.result.readers.map(r => ({ name: r.name, link: r.link,
        note: r.stopped || "" })) : []
    };
  }],
  [/review\.py request forget (\d+)$/, m => ({
    label: t("next_forget", { id: m[1] }), names: [],
    question: () => t("next_forget_q", { id: m[1] }),
    note: () => t("q_forget_note"),
    send: () => post("request", { action: "forget", id: Number(m[1]) }) })],
  [/review\.py general-link \S+ --new$/, () => ({ label: t("next_show_requests"), go: "#requests" })],
  [/List them with: review\.py requests$/, () => ({ label: t("next_show_requests"), go: "#requests" })]
];

// The steps the lines of an answer offer, as buttons or links; tests/test_admin_page.py reads them too. members
// are the names of a group's members before the change that made the lines, when the Groups section made it.
export function nextSteps(lines, members) {
  const seen = {};
  const out = [];
  lines.forEach(line => {
    NEXT.forEach(pair => {
      const m = pair[0].exec(line.trim().replace(/\.$/, ""));
      if (!m) return;
      const step = pair[1](m, members);
      if (!step || seen[step.label]) return;
      seen[step.label] = true;
      out.push(step);
    });
  });
  return out;
}

function nextButton(step, box, after) {
  if (step.go) return h("a", { class: "next", href: step.go }, step.label);
  const b = button(step.label, async () => {
    if (busy()) return;
    let list = step.names;
    if (step.prepare) {
      // The group's members, read now; a group removed since has none to read, and the answer says so.
      const got = await step.prepare();
      list = got.list;
      if (!list.length) {
        addAnswer(box, { ok: false, lines: [], error: got.error || t("next_no_readers") }, { title: step.label });
        return;
      }
    }
    const n = list ? list.length : await memberCount(step.group);
    if (!(await ask(step.question(n), { go: t("go_on"), note: step.note(n), list: list || [] }))) return;
    b.disabled = true;
    const res = await step.send(list);
    addAnswer(box, res, { title: step.label, after: after, links: step.links ? step.links(res) : [] });
    if (after) after();
  }, { class: "act next" });
  return b;
}

// ---------- answers ----------

function addAnswer(box, data, opts) {
  opts = opts || {};
  const block = h("div", { class: "reply " + (data.ok ? "ok" : "bad") });
  if (opts.title) block.append(h("p", { class: "what" }, opts.title));
  const links = opts.links || [];
  // A new link is shown once, in its own row with a Copy button, never also among the lines.
  const lines = data.lines.filter(l => !links.some(x => l.indexOf(x.link) >= 0));
  if (lines.length) block.append(h("pre", { class: "lines" }, lines.join("\n")));
  if (!data.ok && data.error) block.append(h("pre", { class: "error" }, data.error));
  if (links.length) {
    block.append(h("p", { class: "once" }, links.length === 1 ? t("link_once_1") : t("link_once_n")));
    links.forEach(l => block.append(copyRow(l)));
  }
  (opts.notes || []).forEach(n => block.append(h("p", { class: "note" }, n)));
  const steps = nextSteps(lines.concat(data.ok ? [] : data.error.split("\n")), opts.members);
  if (steps.length) block.append(h("div", { class: "steps" }, steps.map(s => nextButton(s, box, opts.after))));
  box.append(block);
  box.hidden = false;
  return block;
}

// Show one answer in a section's answer box, replacing the one before.
export function answer(box, data, opts) {
  clear(box);
  const block = addAnswer(box, data, opts);
  if (block.scrollIntoView) block.scrollIntoView({ block: "nearest" });
  return block;
}

// An answer the page gives itself, before or instead of a command.
export function refuse(box, message) {
  return answer(box, { ok: false, lines: [], error: message });
}

export function working(box) {
  clear(box).append(h("p", { class: "working" }, t("working")));
  box.hidden = false;
}

// Read a chosen file as text.
export function readFile(input) {
  const file = input.files && input.files[0];
  if (!file) return Promise.resolve(null);
  return file.text().then(text => ({ name: file.name, text: text }));
}

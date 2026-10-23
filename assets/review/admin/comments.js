// Comments: export what changed since the last export, everything, or one review round, with the filters;
// the review rounds, and starting one; the exports with their triage packets; triage; the confirmed replies;
// and marking comments processed. Each answer gives the counts and the paths the commands print.
import { get, post, busy } from "./api.js";
import { h, clear, button, field, fill, td, answer, refuse, working, ask, stamp, size, csvRows, readFile } from "./ui.js";
import { t, plural } from "./words.js";
import { state, bookIds } from "./shared.js";

const c = {};
let built = false;
let exports = [];
let rounds = [];

export async function show(root) {
  if (!built) {
    build(root);
    built = true;
  }
  await load();
}

function build(root) {
  c.book = h("select", { id: "e-book" }, h("option", { value: "" }, t("e_every_book")),
    bookIds().map(id => h("option", { value: id }, id)));
  c.ch = h("input", { type: "text", id: "e-ch", placeholder: t("e_ch_placeholder"), class: "short", autocomplete: "off" });
  c.reader = h("input", { type: "text", id: "e-reader", placeholder: t("whole_name"), autocomplete: "off" });
  c.unprocessed = h("input", { type: "checkbox", id: "e-unprocessed" });
  c.out = h("input", { type: "text", id: "e-out", placeholder: state.info ? state.info.export_dir : "", class: "wide",
    autocomplete: "off", spellcheck: "false" });
  c.round = h("select", { id: "e-round" });
  c.roundGo = button(t("e_round_go"), () => doExport("round"), { id: "e-round-go" });
  c.exportBox = h("div", { class: "answer", id: "e-answer", hidden: true, "aria-live": "polite" });
  c.oBook = h("select", { id: "o-book" }, h("option", { value: "" }, t("e_every_book")),
    bookIds().map(id => h("option", { value: id }, id)));
  c.oCount = h("p", { class: "count", id: "o-count" });
  c.oTable = h("table", { class: "list", id: "o-table" });
  c.oNewBook = h("select", { id: "o-new-book" }, bookIds().map(id => h("option", { value: id }, id)));
  c.oName = h("input", { type: "text", id: "o-name", autocomplete: "off", spellcheck: "false",
    placeholder: t("o_name_placeholder") });
  c.oBox = h("div", { class: "answer", id: "o-answer", hidden: true, "aria-live": "polite" });
  c.folder = h("h3", { id: "x-folder" }, t("x_title"));
  c.table = h("table", { class: "list", id: "x-table" });
  c.count = h("p", { class: "count", id: "x-count" });
  c.triageExport = h("select", { id: "t-export" });
  c.ref = h("input", { type: "text", id: "t-ref", placeholder: "main", class: "short", autocomplete: "off",
    spellcheck: "false" });
  c.triageBox = h("div", { class: "answer", id: "t-answer", hidden: true, "aria-live": "polite" });
  c.file = h("input", { type: "file", id: "p-file", accept: ".csv,.json,text/csv,application/json" });
  c.repliesBox = h("div", { class: "answer", id: "p-answer", hidden: true, "aria-live": "polite" });
  c.ids = h("input", { type: "text", id: "d-ids", placeholder: t("d_ids_placeholder"), autocomplete: "off",
    spellcheck: "false" });
  c.doneExport = h("select", { id: "d-export" });
  c.undo = h("input", { type: "checkbox", id: "d-undo" });
  c.doneBox = h("div", { class: "answer", id: "d-answer", hidden: true, "aria-live": "polite" });
  c.oBook.addEventListener("change", loadRounds);
  root.append(h("h2", null, t("e_section")),
    h("h3", null, t("e_title")),
    h("p", { class: "hint" }, t("e_hint")),
    h("div", { class: "row" }, field(t("e_book"), c.book), field(t("e_chapter"), c.ch), field(t("reader"), c.reader),
      h("label", { class: "check" }, c.unprocessed, " " + t("e_unprocessed"))),
    h("div", { class: "row" }, field(t("e_out"), c.out, t("e_out_hint"))),
    h("div", { class: "row" },
      button(t("e_go"), () => doExport("changed"), { id: "e-go" }),
      button(t("e_all"), () => doExport("all"), { id: "e-all" }),
      h("span", { class: "gap" }),
      field(t("e_round"), c.round), c.roundGo),
    c.exportBox,
    h("h3", null, t("o_title")),
    h("p", { class: "hint" }, t("o_hint")),
    h("div", { class: "row" }, field(t("o_list_book"), c.oBook)),
    c.oCount, h("div", { class: "scroll short" }, c.oTable),
    h("div", { class: "row" }, field(t("e_book"), c.oNewBook), field(t("o_name"), c.oName, t("o_name_hint")),
      button(t("o_go"), startRound, { id: "o-go" })),
    c.oBox,
    c.folder, c.count, h("div", { class: "scroll short" }, c.table),
    h("h3", null, t("t_title")),
    h("p", { class: "hint" }, t("t_hint")),
    h("div", { class: "row" }, field(t("t_export"), c.triageExport), field(t("t_ref"), c.ref, t("t_ref_hint")),
      button(t("t_go"), doTriage, { id: "t-go" })),
    c.triageBox,
    h("h3", null, t("p_title")),
    h("p", { class: "hint" }, t("p_hint")),
    h("div", { class: "row" }, field(t("p_file"), c.file), button(t("p_go"), doReplies, { id: "p-go" })),
    c.repliesBox,
    h("h3", null, t("d_title")),
    h("p", { class: "hint" }, t("d_hint")),
    h("div", { class: "row" }, field(t("d_ids"), c.ids), field(t("d_export"), c.doneExport),
      h("label", { class: "check" }, c.undo, " " + t("d_undo")),
      button(t("d_go"), doProcessed, { id: "d-go" })),
    c.doneBox);
}

async function load() {
  await Promise.all([loadExports(), loadRounds()]);
}

async function loadExports() {
  const res = await get("exports");
  if (!res.ok) {
    clear(c.count).append(h("span", { class: "error" }, res.error));
    return;
  }
  exports = res.result.exports;
  c.folder.textContent = t("x_folder", { folder: res.result.folder });
  c.count.textContent = exports.length ? t("x_count", { exports: plural(exports.length, "export") }) : t("x_none");
  const base = p => p.replace(/^.*\//, "");
  fill(c.table, [t("x_col_export"), t("x_col_written"), t("x_col_size"), t("x_col_markdown"), t("x_col_triage")],
    exports.map(x => h("tr", null,
      td(x.name, "name"), td(stamp(x.modified), "nowrap"), td(size(x.size), "nowrap"),
      td(x.markdown ? base(x.markdown) : t("none")),
      td(x.triage.length ? t("x_triage_in", { packets: x.triage.map(p => base(p).replace(/\.md$/, "")).join(", "),
        folder: base(x.triage[0].replace(/\/[^/]*$/, "")) }) : t("none")))));
  options(c.triageExport, t("t_newest"));
  options(c.doneExport, t("d_every_export"));
}

// The review rounds, of every book or of the book chosen (review.py rounds [BOOK]); the round list of Export
// always holds every round.
async function loadRounds() {
  const book = c.oBook.value;
  const res = await get("rounds", book ? { book: book } : null);
  const every = book ? await get("rounds") : res;
  if (every.ok) {
    rounds = every.result.rounds;
    // Each option keeps its book, since a round's name is unique only within its book; the comments written
    // before a book's first round are an option of their own (export --before-first-round).
    const choices = Object.keys(every.result.before || {}).sort().map(b => ({ value: "before " + b,
      text: t("e_round_before", { book: b }) })).concat(rounds.map(r => ({ value: "round " + r.book + " " + r.name,
      text: t(r.current ? "e_round_current" : "e_round_earlier", { name: r.name, book: r.book }) })));
    const keep = c.round.value;
    clear(c.round);
    if (!choices.length) c.round.append(h("option", { value: "" }, t("e_no_rounds")));
    choices.forEach(x => c.round.append(h("option", { value: x.value }, x.text)));
    if (choices.some(x => x.value === keep)) c.round.value = keep;
    c.roundGo.disabled = !choices.length;
  }
  if (!res.ok) {
    clear(c.oCount).append(h("span", { class: "error" }, res.error));
    return;
  }
  const list = res.result.rounds;
  const before = res.result.before || {};
  const firsts = Object.keys(before).sort().map(b => h("tr", { class: "before" },
    td(b, "name"), td(t("o_before")), td(""), td(""), td(String(before[b]), "num")));
  fill(c.oTable, [t("o_col_book"), t("o_col_round"), t("o_col_state"), t("o_col_started"), t("o_col_comments")],
    firsts.concat(list.map(r => h("tr", { class: r.current ? "current" : "", "data-round": r.book + " " + r.name },
      td(r.book, "name"), td(r.name), td(r.current ? t("o_current") : t("o_earlier")), td(stamp(r.started), "nowrap"),
      td(String(r.comments), "num")))));
  c.oCount.textContent = list.length ? t("o_count", { rounds: plural(list.length, "round") })
    : t("o_none", { book: book || t("o_any_book") });
}

function options(select, first) {
  const keep = select.value;
  clear(select).append(h("option", { value: "" }, first));
  exports.forEach(x => select.append(h("option", { value: x.path }, x.name)));
  select.value = exports.some(x => x.path === keep) ? keep : "";
}

// Export what changed since the last export made without a filter, everything (--all), or one review round
// (--round NAME) or the comments before a book's first round (--before-first-round), each with the filters. A
// round's book goes with it, in place of the book filter.
async function doExport(kind) {
  if (busy()) return;
  const pick = kind === "round" ? /^(round|before) (\S+)(?: (.+))?$/.exec(c.round.value) : null;
  if (kind === "round" && !pick) {
    refuse(c.exportBox, t("e_need_round"));
    return;
  }
  const round = pick && pick[1] === "round" ? pick[3] : "";
  const before = !!pick && pick[1] === "before";
  working(c.exportBox);
  const res = await post("export", { book: pick ? pick[2] : c.book.value, ch: c.ch.value.trim().toUpperCase(),
    reader: c.reader.value.trim(), unprocessed: c.unprocessed.checked, out: c.out.value.trim(), all: kind === "all",
    round: round, before_first_round: before });
  const title = kind === "all" ? t("e_all_title") : before ? t("e_before_title", { book: pick[2] })
    : kind === "round" ? t("e_round_title", { name: round }) : t("e_changed_title");
  answer(c.exportBox, res, { title: title });
  await loadExports();
}

async function startRound() {
  if (busy()) return;
  const book = c.oNewBook.value;
  const name = c.oName.value.trim();
  if (!book || !name) {
    refuse(c.oBox, t("o_need_name"));
    c.oName.focus();
    return;
  }
  if (!(await ask(t("o_q", { name: name, book: book }), { note: t("o_note", { book: book }), go: t("o_go") }))) return;
  working(c.oBox);
  const res = await post("round", { book: book, name: name });
  answer(c.oBox, res, { title: t("o_answer_title", { name: name, book: book }) });
  if (res.ok) c.oName.value = "";
  await loadRounds();
}

async function doTriage() {
  if (busy()) return;
  working(c.triageBox);
  const res = await post("triage", { export: c.triageExport.value, ref: c.ref.value.trim() });
  answer(c.triageBox, res, { title: t("t_answer_title") });
  await loadExports();
}

function countReplies(file) {
  if (/\.json$/i.test(file.name)) {
    try {
      let data = JSON.parse(file.text);
      if (data && !Array.isArray(data) && typeof data === "object" && "replies" in data) data = data.replies;
      if (Array.isArray(data)) return data.length;
      return data && typeof data === "object" ? Object.keys(data).length : -1;
    } catch (e) {
      return -1;
    }
  }
  return csvRows(file.text);
}

async function doReplies() {
  if (busy()) return;
  const file = await readFile(c.file);
  if (!file) {
    refuse(c.repliesBox, t("p_need_file"));
    return;
  }
  const n = countReplies(file);
  const q = n >= 0 ? t("p_q", { replies: plural(n, "reply"), file: file.name }) : t("p_q_unknown", { file: file.name });
  if (!(await ask(q, { go: t("p_go_yes"), note: t("p_note") }))) return;
  working(c.repliesBox);
  const json = /\.json$/i.test(file.name);
  const body = json ? { json: file.text, filename: file.name } : { csv: file.text, filename: file.name };
  const res = await post("replies", body);
  answer(c.repliesBox, res, { title: t("p_answer_title", { file: file.name }) });
  if (res.ok) c.file.value = "";
}

async function doProcessed() {
  if (busy()) return;
  const ids = c.ids.value.trim();
  if (!ids) {
    refuse(c.doneBox, t("d_need_ids"));
    c.ids.focus();
    return;
  }
  working(c.doneBox);
  const res = await post("processed", { ids: ids, export: c.doneExport.value, undo: c.undo.checked });
  answer(c.doneBox, res, { title: t(c.undo.checked ? "d_answer_undo" : "d_answer", { ids: ids }) });
}

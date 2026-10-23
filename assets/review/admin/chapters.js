// Chapters: every chapter of every book in books.json, on the site or only in the repository, with its version
// and the commit it came from; publish, withdraw and the alignment packet. Publish shows the commit it will
// read before it runs.
import { get, post, busy } from "./api.js";
import { h, clear, button, field, fill, td, answer, ask, working, stamp, pad, compact } from "./ui.js";
import { t, plural } from "./words.js";
import { state, bookIds, bookName } from "./shared.js";

const books = {};
let built = false;

export async function show(root) {
  if (!built) {
    build(root);
    built = true;
  }
  await load();
}

function build(root) {
  root.append(h("h2", null, t("c_title")), h("p", { class: "hint" }, t("c_hint")));
  bookIds().forEach(id => {
    const b = books[id] = { id: id, selected: {}, source: null, sourceError: "", site: [], rows: [] };
    b.tip = h("p", { class: "tip", id: "tip-" + id });
    b.ref = h("input", { type: "text", id: "ref-" + id, size: 16, spellcheck: "false", autocomplete: "off" });
    b.table = h("table", { class: "list", id: "chapters-" + id });
    b.count = h("p", { class: "count", id: "chapters-count-" + id });
    b.box = h("div", { class: "answer", id: "chapters-answer-" + id, hidden: true, "aria-live": "polite" });
    b.out = h("input", { type: "text", id: "align-out-" + id, class: "wide", autocomplete: "off", spellcheck: "false",
      placeholder: t("c_packet_default", { book: id }) });
    b.publish = button(t("c_publish"), () => publish(b), { id: "publish-" + id });
    b.withdraw = button(t("c_withdraw"), () => withdraw(b, false), { id: "withdraw-" + id });
    b.withdrawAll = button(t("c_withdraw_all"), () => withdraw(b, true), { id: "withdraw-all-" + id });
    b.align = button(t("c_align"), () => alignPacket(b), { id: "align-" + id });
    b.ref.addEventListener("keydown", e => { if (e.key === "Enter") readRef(b); });
    root.append(h("div", { class: "book", "data-book": id },
      h("h3", null, bookName(id)),
      b.tip,
      h("div", { class: "row" },
        field(t("c_ref"), b.ref, t("c_ref_hint")),
        button(t("c_read_ref"), () => readRef(b), { id: "readref-" + id })),
      h("div", { class: "scroll" }, b.table),
      b.count,
      h("div", { class: "bar" }, b.publish, b.withdraw, b.withdrawAll),
      h("div", { class: "row" }, field(t("c_packet_out"), b.out, t("c_packet_out_hint")), b.align),
      b.box));
  });
}

async function load() {
  const ids = bookIds();
  const answers = await Promise.all([get("chapters")].concat(ids.map(id => {
    const ref = books[id].ref.value.trim();
    return get("source", ref ? { book: id, ref: ref } : { book: id });
  })));
  const site = answers[0];
  ids.forEach((id, i) => {
    const b = books[id];
    b.site = site.ok ? site.result.chapters.filter(c => c.book === id) : [];
    takeSource(b, answers[i + 1]);
    render(b);
    if (!site.ok) answer(b.box, site, { title: t("c_site_list") });
  });
}

function takeSource(b, res) {
  if (res.ok) {
    b.source = res.result.books[0];
    b.sourceError = "";
    if (!b.ref.value.trim()) b.ref.value = b.source.ref;
  } else {
    b.source = null;
    b.sourceError = res.error;
  }
}

function same(a, b) {
  return !!a && !!b && (a.indexOf(b) === 0 || b.indexOf(a) === 0);
}

function render(b) {
  const tip = clear(b.tip);
  if (b.source) {
    tip.append(h("strong", null, t("c_tip_ref", { ref: b.source.ref, commit: b.source.commit })),
      t("c_tip_rest", { date: b.source.date, subject: b.source.subject }));
  } else {
    tip.append(h("span", { class: "error" }, b.sourceError || t("c_not_read")));
  }
  const rows = {};
  b.site.forEach(c => { rows[c.id] = { id: c.id, n: c.n, site: c, repo: null }; });
  (b.source ? b.source.chapters : []).forEach(c => {
    if (!rows[c.id]) rows[c.id] = { id: c.id, n: c.n, site: null, repo: null };
    rows[c.id].repo = c;
  });
  b.rows = Object.keys(rows).map(k => rows[k]).sort((x, y) => x.n - y.n);
  const keep = {};
  b.rows.forEach(r => { if (b.selected[r.id]) keep[r.id] = true; });
  b.selected = keep;
  const ref = b.source ? b.source.ref : t("c_the_ref");
  const all = h("input", { type: "checkbox", id: "chapters-all-" + b.id, "aria-label": t("c_select_all") });
  all.checked = b.rows.length > 0 && b.rows.every(r => b.selected[r.id]);
  all.addEventListener("change", () => {
    b.selected = {};
    if (all.checked) b.rows.forEach(r => { b.selected[r.id] = true; });
    render(b);
  });
  fill(b.table, [all, t("c_col_chapter"), t("c_col_title"), t("c_col_site"), t("c_col_version"), t("c_col_commit"),
    t("c_col_last", { ref: ref }), t("c_col_paragraphs"), t("c_col_comments"), t("c_col_open"), t("c_col_versions"),
    t("c_col_updated")], b.rows.map(r => row(b, r)));
  const published = b.rows.filter(r => r.site && r.site.published).length;
  const withdrawn = b.rows.filter(r => r.site && !r.site.published).length;
  const never = b.rows.filter(r => !r.site).length;
  const chosen = Object.keys(b.selected).length;
  b.count.textContent = t("c_count", { chapters: plural(b.rows.length, "chapter"), published: published,
    withdrawn: withdrawn, never: never }) + (chosen ? " " + t("n_selected", { n: chosen }) : "");
  b.publish.disabled = chosen === 0;
  b.withdraw.disabled = !b.rows.some(r => b.selected[r.id] && r.site && r.site.published);
  b.withdrawAll.disabled = published === 0;
  b.align.disabled = chosen !== 1;
}

function row(b, r) {
  const box = h("input", { type: "checkbox", value: r.id, "aria-label": t("select_one", { name: r.id }),
    "data-chapter": r.id });
  box.checked = !!b.selected[r.id];
  box.addEventListener("change", () => {
    if (box.checked) b.selected[r.id] = true;
    else delete b.selected[r.id];
    render(b);
  });
  const s = r.site;
  const book = state.info.books[b.id] || {};
  const title = s ? [s.title_en, s.title ? [" / ", h("span", { lang: book.language || null }, s.title)] : null]
    : h("span", { class: "muted" }, r.repo.source);
  let last = t("c_not_in", { ref: b.source ? b.source.ref : t("c_the_repo") });
  if (r.repo) {
    last = r.repo.commit || t("c_no_commit");
    if (s && s.commit && r.repo.commit && !same(s.commit, r.repo.commit)) last += " " + t("c_not_site_commit");
    if (!r.repo.english_found) last += t("c_english_missing");
  }
  const where = s ? (s.published ? t("c_published") : t("c_withdrawn")) : t("c_never");
  return h("tr", { "data-chapter": r.id, class: s ? (s.published ? "published" : "withdrawn") : "never" },
    td(box, "pick"), td(r.id, "name"), td(title, "title"), td(where, "nowrap"),
    td(s ? s.version : "", "mono"), td(s ? (s.commit || t("c_not_recorded")) : "", "mono"), td(last, "mono"),
    td(s ? String(s.paragraphs) : "", "num"), td(s ? String(s.comments) : "", "num"), td(s ? String(s.open) : "", "num"),
    td(s ? String(s.versions) : "", "num"), td(s ? stamp(s.updated) : "", "nowrap"));
}

function chosen(b) {
  return b.rows.filter(r => b.selected[r.id]);
}

async function readRef(b) {
  const ref = b.ref.value.trim();
  const res = await get("source", ref ? { book: b.id, ref: ref } : { book: b.id });
  takeSource(b, res);
  render(b);
}

async function publish(b) {
  if (busy() || !chosen(b).length) return;
  const ref = b.ref.value.trim();
  const before = b.source ? b.source.commit : "";
  const res = await get("source", ref ? { book: b.id, ref: ref } : { book: b.id });
  takeSource(b, res);
  render(b);
  if (!res.ok) {
    answer(b.box, res, { title: t("c_publish_go") });
    return;
  }
  const src = b.source;
  const rows = chosen(b);
  if (!rows.length) return;
  const absent = rows.filter(r => !r.repo).map(r => r.id);
  const note = [t("c_publish_reads", { ref: src.ref, commit: src.commit, date: src.date, subject: src.subject })]
    .concat(before && before !== src.commit ? [t("c_publish_moved", { ref: src.ref })] : [])
    .concat(absent.length ? [t("c_publish_absent", { ref: src.ref, chapters: absent.join(", ") })] : [])
    .concat([t("c_publish_note")]).join(" ");
  const ids = rows.map(r => r.id);
  if (!(await ask(t("c_publish_q", { chapters: plural(rows.length, "chapter"), book: b.id, ids: compact(ids) }),
    { note: note, go: t("c_publish_go") }))) return;
  working(b.box);
  const done = await post("publish", { book: b.id, chapters: rows.map(r => pad(r.n)).join(","), ref: src.ref });
  const notes = [];
  const m = /^Reading \S+ at (\S+),/.exec(done.lines[0] || "");
  if (m && !same(m[1], src.commit)) {
    notes.push(t("c_publish_read_other", { read: m[1], commit: src.commit, ref: src.ref }));
  }
  answer(b.box, done, { title: t("c_publish_title", { chapters: ids.join(", ") }), notes: notes });
  await load();
}

async function withdraw(b, whole) {
  if (busy()) return;
  const rows = whole ? b.rows.filter(r => r.site && r.site.published)
    : chosen(b).filter(r => r.site && r.site.published);
  if (!rows.length) return;
  const ids = rows.map(r => r.id);
  const question = whole
    ? t("c_withdraw_all_q", { book: b.id, chapters: plural(rows.length, "published_chapter"), ids: compact(ids) })
    : t("c_withdraw_q", { chapters: plural(rows.length, "chapter"), book: b.id, ids: compact(ids) });
  if (!(await ask(question, { note: t("c_withdraw_note"), go: t("c_withdraw_go") }))) return;
  working(b.box);
  const done = await post("withdraw", whole ? { book: b.id } : { book: b.id, chapters: rows.map(r => pad(r.n)).join(",") });
  answer(b.box, done, { title: t("c_withdraw_title", { chapters: whole ? b.id : ids.join(", ") }) });
  await load();
}

async function alignPacket(b) {
  if (busy()) return;
  const rows = chosen(b);
  if (rows.length !== 1) return;
  const ref = b.ref.value.trim();
  const out = b.out.value.trim();
  working(b.box);
  // An empty ref or out is left out of the body, as the command takes the book's ref and the default file.
  const done = await post("align-packet", { book: b.id, chapter: pad(rows[0].n), ref: ref || undefined,
    out: out || undefined });
  answer(b.box, done, { title: t("c_align_title", { chapter: rows[0].id }) });
}

/* Proofreading site: the chapter list (web/core/home.js). */

import { overlay } from "./outbox.js";
import { S } from "./state.js";
import { t, plural } from "./words.js";
import { h, $, shortA, drawn } from "./dom.js";
import { active, hintKey } from "./ext.js";
import { loadOb, keptComments } from "./net.js";
import { bookLang } from "./languages.js";
import { leaveChapter, openChapter } from "./chapter.js";
import { setBar, settingsBar } from "./screens.js";

export function showHome() {
  leaveChapter();
  S.view = "home";
  setBar(null);
  renderHome(true);
  window.scrollTo(0, S.homeY || 0);
}

function countComments(c, ob) {
  const list = keptComments(c.book, c.id);
  if (list) return overlay(list, ob, c.book, c.id, S.code).length;
  let n = c.comments;
  for (const o of ob) {
    if (o.code !== S.code || o.book !== c.book || o.ch !== c.id) continue;
    if (o.type === "create") n++;
    else if (o.type === "delete") n--;
  }
  return Math.max(0, n);
}

/* The lines features add under a chapter's title (ext.js, titleLine): English adds the English title. */
export function titleLines(chapter, where) {
  return active("titles", S.me).map(d => drawn(d, { chapter, me: S.me, where }));
}

export function renderHome(force) {
  const me = S.me;
  if (!me) return;
  const ob = loadOb();
  const rows = me.chapters.slice().sort((x, y) => x.n - y.n).map(c => {
    const status = c.finished ? "done" : c.place ? "reading" : "todo";
    const bits = [];
    if (c.place && !c.finished) bits.push(t("place", { a: shortA(c.place) }));
    if (c.count) bits.push(plural(c.count, "paras_one", "paras_many"));
    const n = countComments(c, ob);
    if (n) bits.push(plural(n, "comments_one", "comments_many"));
    return { c, status, meta: bits.join(" · ") };
  });
  const sig = JSON.stringify([S.lang, me.name, me.features, rows.map(r => [r.c.book, r.c.id, r.c.title_th, r.c.title_en, r.status, r.meta])]);
  if (!force && sig === S.homeSig) return;
  S.homeSig = sig;
  const statusText = { done: t("status_done"), reading: t("status_reading"), todo: t("status_new") };
  const main = $("main");
  main.textContent = "";
  main.append(h("header", { class: "home-head" },
    h("div", { class: "home-top" }, h("h1", { text: t("app_title") }), settingsBar("home")),
    me.name ? h("p", { class: "hello", text: t("hello", { name: me.name }) }) : null,
    h("p", { class: "lead", text: t(hintKey(me)) })));
  if (!rows.length) {
    main.append(h("p", { class: "lead empty", text: t("no_chapters") }));
    return;
  }
  const books = [...new Set(rows.map(r => r.c.book))];
  for (const book of books) {
    if (books.length > 1) main.append(h("h2", { class: "book", text: me.books[book] || book }));
    main.append(h("ul", { class: "shelf" }, rows.filter(r => r.c.book === book).map(r => h("li", null,
      h("button", { type: "button", class: "ch-row", onclick: () => { S.homeY = window.scrollY; openChapter(r.c.book, r.c.id, { resume: true, push: true }); } },
        h("span", { class: "ch-num", text: String(r.c.n) }),
        h("span", { class: "ch-names" },
          h("span", { class: "ch-title", lang: bookLang(r.c.book), text: r.c.title_th }),
          titleLines(r.c, "list")),
        h("span", { class: "chip " + r.status, text: statusText[r.status] }),
        r.meta ? h("span", { class: "ch-meta", text: r.meta }) : null)))));
  }
}

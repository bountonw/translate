/* Proofreading site: "My earlier comments" (web/core/earlier.js).

   Each time a book is opened for review, a new review round starts, and the reader's page shows only the
   comments of the current round. The reader's comments of earlier rounds stay on the site; this screen
   shows them on request, from GET /api/comments?earlier=1, grouped by book, then by round (newest first,
   and the comments written before the book's first round last), then by chapter and paragraph. They can be
   read but not changed, so the cards have no Change or Delete button; each shows the translator's reply.

   The chapter list offers the screen when /api/me counts comments of earlier rounds (`earlier` of a book).
   Its address is #earlier, so the browser's back button returns to the chapter list. */

import { groupEarlier } from "./model.js";
import { S } from "./state.js";
import { t, dateText } from "./words.js";
import { h } from "./dom.js";
import { fetchEarlier } from "./net.js";
import { bookLang } from "./languages.js";
import { setHash, setBar, showScreen, goHome } from "./screens.js";
import { readOnlyCard } from "./notes.js";

/* Whether the reader has comments of earlier rounds on chapters open now. */
export function hasEarlier(me) {
  return !!me && !!me.earlier && Object.keys(me.earlier).some(b => me.earlier[b] > 0);
}

/* The heading of one round: "Round 2026-11, from 1 November 2026", or the heading of the comments written
   before the book's first round. */
function roundTitle(r) {
  if (!r) return t("past_before");
  const date = dateText(r.started);
  return date ? t("past_round", { name: r.name, date }) : t("past_round_name", { name: r.name });
}

function chapterTitle(book, ch) {
  const c = S.me && S.me.chapters.find(x => x.book === book && x.id === ch);
  if (!c) return h("h3", { class: "past-ch", text: ch });
  return h("h3", { class: "past-ch" },
    h("span", { text: t("chapter_n", { n: c.n }) }),
    c.title ? " · " : null,
    c.title ? h("span", { lang: bookLang(book), text: c.title }) : null);
}

function draw(box, data) {
  box.textContent = "";
  const groups = groupEarlier(data.comments, data.rounds);
  if (!groups.length) {
    box.append(h("p", { class: "lead", text: t("past_none") }));
    return;
  }
  for (const g of groups) {
    if (groups.length > 1) box.append(h("h2", { class: "book", text: (S.me && S.me.books[g.book]) || g.book }));
    for (const r of g.rounds) {
      box.append(h("h2", { class: "past-round", text: roundTitle(r.round) }));
      for (const c of r.chapters) {
        box.append(chapterTitle(g.book, c.ch), h("div", { class: "notes" }, c.comments.map(x => readOnlyCard(x, g.book))));
      }
    }
  }
}

async function load(box) {
  box.textContent = "";
  box.append(h("p", { class: "lead loading", text: t("loading") }));
  const r = await fetchEarlier();
  if (S.view !== "earlier" || !box.isConnected || !r) return;   // null: the link or the device stopped working
  if (r.error) {
    box.textContent = "";
    box.append(h("p", { class: "lead", text: r.error === "offline" ? t("cannot_connect") : t("error_generic") }),
      h("div", { class: "row" }, h("button", { type: "button", class: "btn", text: t("retry_load"), onclick: () => load(box) })));
    return;
  }
  draw(box, r);
}

/* Show "My earlier comments". push is true when the reader opened it from the chapter list, so that the
   browser's back button returns there. */
export function showEarlier(push) {
  if (push) setHash("#earlier", true);
  const box = h("div", { class: "past" });
  showScreen("earlier", h("section", { class: "message past-screen" },
    h("h1", { text: t("past_open") }),
    h("p", { class: "lead", text: t("past_lead") }),
    box,
    h("div", { class: "row" }, h("button", { type: "button", class: "btn ghost", text: t("all_chapters"), onclick: goHome }))));
  setBar(null, t("past_open"));
  load(box);
}

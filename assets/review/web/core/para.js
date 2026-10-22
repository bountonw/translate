/* Proofreading site: a paragraph and its drawer (web/core/para.js).

   A tap on a paragraph opens its drawer: the panels features add (ext.js, drawerPanel; English is the
   first), the reader's comments on it, and the form for a new comment. Words the reader selects in the
   paragraph go into the form's quote box. */

import { S } from "./state.js";
import { t, plural } from "./words.js";
import { h, $, shortA, paraId, bookHtml, applyMarks, tapMark, drawn } from "./dom.js";
import { active } from "./ext.js";
import { bookLang } from "./languages.js";
import { currentComments, keepPosition, renderChapter, markJump } from "./chapter.js";
import { commentForm, renderNotes } from "./notes.js";

const drawerCtx = (art, p) => ({ p, art, chapter: S.chapter, me: S.me, book: S.book, lang: bookLang(S.book) });

export function renderPara(p, list) {
  const lg = bookLang(S.book);
  const art = h("article", { class: "para", id: paraId(p.a), "data-a": p.a, tabindex: "0", "aria-expanded": "false" },
    h("p", { class: "para-text", lang: lg }, bookHtml(p.th), h("span", { class: "tag", text: shortA(p.a) }), h("span", { class: "badge" })),
    p.fn.length ? h("ol", { class: "fns", lang: lg }, p.fn.map(f => h("li", null, bookHtml(f)))) : null);
  applyMarks(art, drawerCtx(art, p));
  art.addEventListener("click", ev => {
    // A button inside the drawer may redraw itself during its own click; once detached it is no longer inside art.
    if (!art.contains(ev.target) || ev.target.closest(".drawer")) return;
    if (tapMark(ev.target, drawerCtx(art, p))) return;
    const sel = selectionIn(art);
    if (!art.classList.contains("open")) openDrawer(art, p, sel);
    else if (sel) fillQuote(art, sel);
    else closeDrawer(art);
  });
  art.addEventListener("keydown", ev => {
    if (ev.target === art && (ev.key === "Enter" || ev.key === " ")) {
      ev.preventDefault();
      if (art.classList.contains("open")) closeDrawer(art); else openDrawer(art, p, null);
    } else if (ev.key === "Escape" && art.classList.contains("open")) {
      closeDrawer(art);
      art.focus();
    }
  });
  paintPara(art, list);
  return art;
}

export function paintPara(art, list) {
  const mine = list.filter(c => c.a === art.dataset.a);
  art.classList.toggle("has-notes", mine.length > 0);
  art.classList.toggle("has-failed", mine.some(c => c.state === "failed"));
  art.querySelector(".badge").textContent = mine.length ? plural(mine.length, "comments_one", "comments_many") : "";
  const box = art.querySelector(".drawer .notes");
  if (box) renderNotes(art, box, mine);
}

/* The words the reader selected inside this paragraph, without the paragraph number, the comment
   count and the footnote numbers, cut to the longest quote the server keeps. */
function quoteFromSelection(art) {
  const s = window.getSelection && window.getSelection();
  if (!s || s.isCollapsed || !s.rangeCount) return null;
  const inText = node => {
    const el = node && (node.nodeType === 1 ? node : node.parentElement);
    return !!el && art.contains(el) && !el.closest(".drawer");
  };
  if (!inText(s.anchorNode) || !inText(s.focusNode)) return null;
  const frag = s.getRangeAt(0).cloneContents();
  for (const x of frag.querySelectorAll(".tag, .badge, sup.fn")) x.remove();
  const most = S.me && S.me.limits ? S.me.limits.quote : 500;
  return Array.from(frag.textContent.replace(/\s+/g, " ").trim()).slice(0, most).join("") || null;
}

function selectionIn(art) {
  const q = quoteFromSelection(art);
  if (q) return q;
  // On a phone the selection is often gone by the time the paragraph is tapped.
  const last = S.lastSel;
  return last && last.a === art.dataset.a && Date.now() - last.t < 90000 ? last.text : null;
}

export function onSelection() {
  if (S.view !== "chapter") return;
  const s = window.getSelection();
  if (!s || s.isCollapsed || !s.anchorNode) return;
  const el = s.anchorNode.nodeType === 1 ? s.anchorNode : s.anchorNode.parentElement;
  const art = el && el.closest(".para");
  if (!art) return;
  const text = quoteFromSelection(art);
  if (!text) return;
  S.lastSel = { a: art.dataset.a, text, t: Date.now() };
  if (art.classList.contains("open")) fillQuote(art, text);
}

/* Put selected words in the quote box unless the reader typed something there. */
function fillQuote(art, text) {
  const q = art.querySelector(".drawer input[name=quote]");
  if (!q || (q.value && q.dataset.auto !== "1")) return;
  q.value = text;
  q.dataset.auto = "1";
  q.dispatchEvent(new Event("input", { bubbles: true }));
}

/* Open the comment drawer under a paragraph. The tapped paragraph stays where it was on the screen,
   even when an open drawer above it closes. When the new drawer would start low on the screen, the
   page scrolls so that it starts about a third of the way down; when the comment box would end below
   the screen, the page scrolls just enough to show it, and never moves the drawer above that third. */
export function openDrawer(art, p, quote) {
  const before = art.getBoundingClientRect().top;
  art.classList.add("open");
  art.setAttribute("aria-expanded", "true");
  for (const o of document.querySelectorAll("#main .para.open")) if (o !== art) closeDrawer(o);
  const ctx = drawerCtx(art, p);
  art.append(h("div", { class: "drawer" },
    active("panels", S.me).map(d => drawn(d, ctx)),
    h("section", { class: "notes-block" },
      h("p", { class: "label", text: t("your_comments") }),
      h("div", { class: "notes" })),
    commentForm(art, p, null, quote)));
  paintPara(art, currentComments());
  S.lastSel = null;
  let by = art.getBoundingClientRect().top - before;
  const drawer = art.querySelector(".drawer");
  const top = drawer.getBoundingClientRect().top - by;
  const box = drawer.querySelector("textarea").getBoundingClientRect().bottom - by;
  const want = Math.max($("bar").getBoundingClientRect().bottom + 8, window.innerHeight * 0.35);
  const low = window.innerHeight - 8;
  if (top > window.innerHeight - 160) by += top - want;
  else if (top > want && box > low) by += Math.min(top - want, box - low);
  if (by) { markJump(); window.scrollBy(0, by); }
}

export function closeDrawer(art) {
  art.classList.remove("open");
  art.setAttribute("aria-expanded", "false");
  const d = art.querySelector(".drawer");
  if (d) d.remove();
  if (S.waiting && !document.querySelector("#main .para.open")) {
    const data = S.waiting;
    keepPosition(() => renderChapter(data, false));
  }
}

/* Proofreading site: a paragraph and its drawer (web/core/para.js).

   A tap on a paragraph opens its drawer: the panels features add (ext.js, drawerPanel; English is the
   first), the reader's comments on it, and the form for a new comment. Words the reader selects in the
   paragraph go into the form's quote box, in place of words the page put there, never of words the reader
   typed. Closing a drawer, by any means, puts its paragraph back where it stood on the screen when the
   drawer opened; while a drawer is open, a round button at the bottom right of the screen closes it.

   The panels come first in the drawer, the English first among them (features/english.js, order 10, before
   "Show the earlier wording" at 20); a "Write a comment" button above them jumps to the comment form. When
   the drawer of a paragraph above closes because the reader tapped another paragraph, the tapped
   paragraph's first line shows below the top bar. When the drawer opens from a tapped Thai sentence, the
   page scrolls just enough to show its lit English, keeping the tapped sentence below the bar. */

import { DEFAULT_LIMITS } from "./model.js";
import { S } from "./state.js";
import { t, plural } from "./words.js";
import { h, $, shortA, paraId, bookHtml, applyMarks, tapMark, markedSpan, drawn, decorateText } from "./dom.js";
import { active } from "./ext.js";
import { bookLang } from "./languages.js";
import { currentComments, keepPosition, renderChapter, markJump } from "./chapter.js";
import { commentForm, renderNotes } from "./notes.js";
import { paintMark, paraOpened } from "./updates.js";

const drawerCtx = (art, p, span) => ({ p, art, chapter: S.chapter, me: S.me, book: S.book, lang: bookLang(S.book), span: span || null });

export function renderPara(p, list) {
  const lg = bookLang(S.book);
  const text = h("span", { class: "bt" }, bookHtml(p.text));
  const notes = p.fn.map(f => h("li", { class: "bt" }, bookHtml(f)));
  const art = h("article", { class: "para", id: paraId(p.a), "data-a": p.a, tabindex: "0", "aria-expanded": "false" },
    h("p", { class: "para-text", lang: lg }, h("span", { class: "upd", hidden: true }), text,
      h("span", { class: "tag", text: shortA(p.a) }), h("span", { class: "badge" })),
    notes.length ? h("ol", { class: "fns", lang: lg }, notes) : null);
  const ctx = drawerCtx(art, p);
  applyMarks(art, ctx);
  decorateText(text, ctx, "para");
  for (const li of notes) decorateText(li, ctx, "fn");
  art.addEventListener("click", ev => {
    // A button inside the drawer may redraw itself during its own click; once detached it is no longer inside art.
    if (!art.contains(ev.target) || ev.target.closest(".drawer")) return;
    const open = art.classList.contains("open");
    if (open) {
      // Words selected now go into the quote box; a tap that only took a selection away does nothing more.
      const live = quoteFromSelection(art);
      if (live) { fillQuote(art, live); return; }
      if (selectionJustEnded(art)) return;
    }
    const span = markedSpan(ev.target);
    if (tapMark(ev.target, drawerCtx(art, p, span))) return;
    if (!open) openDrawer(art, p, selectionIn(art), span);
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
  paintMark(art);
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
  for (const x of frag.querySelectorAll(".tag, .upd, .badge, sup.fn")) x.remove();
  const most = S.me && S.me.limits ? S.me.limits.quote : DEFAULT_LIMITS.quote;
  return Array.from(frag.textContent.replace(/\s+/g, " ").trim()).slice(0, most).join("") || null;
}

function selectionIn(art) {
  const q = quoteFromSelection(art);
  if (q) return q;
  // On a phone the selection is often gone by the time the paragraph is tapped.
  const last = S.lastSel;
  return last && last.a === art.dataset.a && Date.now() - last.t < 90000 ? last.text : null;
}

/* The paragraph that holds the reader's selection now, and when a selection in a paragraph last went away:
   a tap that takes a selection away should not also close the drawer. */
let selIn = null;
let selEnded = null;
const ENDED_MS = 600;

function selectionJustEnded(art) {
  return !!selEnded && selEnded.a === art.dataset.a && Date.now() - selEnded.t < ENDED_MS;
}

export function onSelection() {
  const s = window.getSelection && window.getSelection();
  if (!s || s.isCollapsed || !s.anchorNode) {
    if (selIn) { selEnded = { a: selIn, t: Date.now() }; selIn = null; }
    return;
  }
  if (S.view !== "chapter") return;
  const el = s.anchorNode.nodeType === 1 ? s.anchorNode : s.anchorNode.parentElement;
  const art = el && el.closest(".para");
  if (!art) return;
  const text = quoteFromSelection(art);
  if (!text) return;
  selIn = art.dataset.a;
  S.lastSel = { a: art.dataset.a, text, t: Date.now() };
  if (art.classList.contains("open")) fillQuote(art, text);
}

/* Put selected words in the quote box when it is empty or holds words the page put there (dataset.auto);
   never over words the reader typed. A draft keeps the mark, so a new selection replaces the words the
   page put there before the draft was kept, too. */
function fillQuote(art, text) {
  const q = art.querySelector(".drawer form.note-form input[name=quote]");
  if (!q || (q.value && q.dataset.auto !== "1")) return;
  if (q.value === text) return;
  q.value = text;
  q.dataset.auto = "1";
  q.dispatchEvent(new Event("input", { bubbles: true }));
}

/* The lowest a paragraph's first line may stand on the screen: just below the top bar. */
const barLine = () => $("bar").getBoundingClientRect().bottom + 8;

/* Scroll so that the drawer's comment form starts just below the top bar, and put the focus on its first
   choice, which opens no keyboard on a phone. */
function jumpToForm(art) {
  const f = art.querySelector(".drawer form.note-form");
  if (!f) return;
  const by = f.getBoundingClientRect().top - barLine();
  if (by) { markJump(); window.scrollBy(0, by); }
  const first = f.querySelector("input[name=kind]:checked") || f.querySelector("input, textarea");
  if (first) {
    try { first.focus({ preventScroll: true }); } catch (e) { first.focus(); }
  }
}

/* Open the comment drawer under a paragraph. The tapped paragraph stays where it was on the screen,
   even when an open drawer above it closes. When the new drawer would start low on the screen, the
   page scrolls so that it starts about a third of the way down; when the comment box would end below
   the screen, the page scrolls just enough to show it, and never moves the drawer above that third.
   When the drawer of a paragraph above closed, the tapped paragraph's first line always shows below the
   top bar: the page scrolls no further than that, and brings the first line back when the closing took it
   away. */
export function openDrawer(art, p, quote, span) {
  const before = art.getBoundingClientRect().top;
  openTops.set(art, before);
  art.classList.add("open");
  art.setAttribute("aria-expanded", "true");
  // The tapped paragraph stays where it is, so a drawer closed above it does not go back to its own place.
  let closedAbove = false;
  for (const o of document.querySelectorAll("#main .para.open")) {
    if (o === art) continue;
    if (o.compareDocumentPosition(art) & Node.DOCUMENT_POSITION_FOLLOWING) closedAbove = true;
    closeDrawer(o, true);
  }
  const ctx = drawerCtx(art, p, span);
  const panels = active("panels", S.me).map(d => drawn(d, ctx)).filter(Boolean);
  art.append(h("div", { class: "drawer" },
    panels.length ? h("div", { class: "drawer-top" },
      h("button", { type: "button", class: "btn ghost write-btn", text: t("write_comment"), onclick: () => jumpToForm(art) })) : null,
    panels,
    h("section", { class: "notes-block" },
      h("p", { class: "label", text: t("your_comments") }),
      h("div", { class: "notes" })),
    commentForm(art, p, null, quote)));
  paintPara(art, currentComments());
  S.lastSel = null;
  const cur = art.getBoundingClientRect().top;
  let by = cur - before;
  const drawer = art.querySelector(".drawer");
  const top = drawer.getBoundingClientRect().top - by;
  const box = drawer.querySelector("textarea").getBoundingClientRect().bottom - by;
  const line = barLine();
  const want = Math.max(line, window.innerHeight * 0.35);
  const low = window.innerHeight - 8;
  if (top > window.innerHeight - 160) by += top - want;
  else if (top > want && box > low) by += Math.min(top - want, box - low);
  // A drawer above closed: the tapped paragraph's first line shows below the bar.
  if (closedAbove && cur - by < line) by = cur - line;
  by += litShift(art, span, by, line, low, closedAbove ? cur : null);
  if (by) { markJump(); window.scrollBy(0, by); }
  paraOpened(art);
  paintFloat();
}

/* When the drawer opened from a tapped span, as a Thai sentence, and a panel lit what belongs to it (elements
   of the drawer with the class hl, as the sentence's English), how much further to scroll so that the lit part
   ends on the screen: no further than keeps the tapped span below the bar, nor, when a drawer above closed
   (keepTop, the paragraph's top before the scroll), its first line. When the scroll already planned took the
   tapped span above the bar, as in a tall paragraph, the lit part is shown, its top no higher than the bar.
   by is the scroll already planned. */
function litShift(art, span, by, line, low, keepTop) {
  if (!span || !art.contains(span)) return 0;
  const lit = art.querySelectorAll(".drawer .hl");
  if (!lit.length) return 0;
  let top = Infinity, bottom = -Infinity;
  for (const x of lit) {
    const r = x.getBoundingClientRect();
    top = Math.min(top, r.top - by);
    bottom = Math.max(bottom, r.bottom - by);
  }
  const need = bottom - low;
  if (need <= 0) return 0;
  let room = span.getBoundingClientRect().top - by - line;
  if (keepTop !== null) room = Math.min(room, keepTop - by - line);
  else if (room <= 0) room = top - line;
  return room > 0 ? Math.min(need, room) : 0;
}

/* Where each open paragraph stood on the screen when its drawer opened. */
const openTops = new WeakMap();

/* Close a paragraph's drawer and put the paragraph back where it stood on the screen when the drawer opened.
   keepPlace is true when another paragraph's drawer is opening, which keeps that paragraph in its place. */
export function closeDrawer(art, keepPlace) {
  art.classList.remove("open");
  art.setAttribute("aria-expanded", "false");
  const d = art.querySelector(".drawer");
  if (d) d.remove();
  const top = openTops.get(art);
  openTops.delete(art);
  if (!keepPlace && typeof top === "number" && art.isConnected) {
    const by = art.getBoundingClientRect().top - top;
    if (by) { markJump(); window.scrollBy(0, by); }
  }
  if (S.waiting && !document.querySelector("#main .para.open")) {
    const data = S.waiting;
    keepPosition(() => renderChapter(data, false));
  }
  paintFloat();
}

/* ---- the round button that closes the open drawer ---- */

let floatBtn = null;

/* Show the button while a drawer of the chapter on the screen is open, and hide it otherwise; off hides it,
   as when the reader leaves the chapter. */
export function paintFloat(off) {
  const open = !off && S.view === "chapter" ? document.querySelector("#main .para.open") : null;
  document.body.classList.toggle("drawer-open", !!open);
  if (!open && !floatBtn) return;
  if (!floatBtn) {
    floatBtn = h("button", { type: "button", class: "float-close", onclick: () => {
      const art = document.querySelector("#main .para.open");
      const hadFocus = document.activeElement === floatBtn;
      if (art) closeDrawer(art);
      else paintFloat();
      if (art && hadFocus) art.focus();
    } });
    document.body.append(floatBtn);
  }
  floatBtn.setAttribute("aria-label", t("close"));
  floatBtn.title = t("close");
  floatBtn.hidden = !open;
}

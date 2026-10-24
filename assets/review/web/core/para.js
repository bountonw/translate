/* Proofreading site: a paragraph (web/core/para.js).

   A paragraph's text, its footnotes and, when the reader shows it side by side on a wide screen, its English
   beside it (the lead section of the panel, core/panel.js). What the reader does with a paragraph goes to the panel:

     - a tap on a Thai sentence (a marked span a feature handles, as features/sentences.js's) opens the panel on
       the English with that sentence lit; a tap on the lit sentence closes it; a tap elsewhere in the paragraph
       opens the panel, or closes it when it shows this paragraph;
     - while the reader picks words (Pick words), a tap on the paragraph goes to the picker;
     - words the reader selects in the paragraph shown fill the quote box at once, and a selection that rests
       for a moment opens the comment box with the words in it and stays visible, because on a phone the tap
       that would open the box also clears the selection.

   It also paints what belongs on the paragraph: the mark of a changed paragraph (updates.js), the count of the
   reader's comments, a soft background on words one comment quotes and a deeper one where two or more quote them,
   the words the quote box holds from a pick or a selection, and the soft background of the paragraph opened last. */

import { DEFAULT_LIMITS } from "./model.js";
import { S } from "./state.js";
import { plural } from "./words.js";
import { h, shortA, paraId, bookHtml, applyMarks, tapMark, markedSpan, decorateText, drawn, readingText,
  readingOffset, wrapRanges, unwrap } from "./dom.js";
import { active, markFor } from "./ext.js";
import { bookLang } from "./languages.js";
import { locate, marks, quoteBetween } from "./quotes.js";
import { renderNotes } from "./notes.js";
import { currentComments } from "./chapter.js";
import { paintMark } from "./updates.js";
import { openPanel, focusPanel, closePanel, panelArt, panelFace, panelNotes, pickIn, picking, pickTap, besideOn,
  takeSelection, selectionRested, repaintPanel } from "./panel.js";

const paraCtx = (art, p, span) => ({ p, art, chapter: S.chapter, me: S.me, book: S.book, lang: bookLang(S.book),
  span: span || null, show: null, beside: false });

/* The element that holds a paragraph's text in the book's language: the reading text of quotes.js. */
export const bookTextOf = art => (art ? art.querySelector(".para-text > .bt") : null);

/* The line the reader tapped, which the panel keeps in view: a band around the tap's height. */
const tapLine = ev => (typeof ev.clientY === "number" && ev.clientY > 0 ? { top: ev.clientY - 22, bottom: ev.clientY + 22 } : null);

export function renderPara(p, list) {
  const lg = bookLang(S.book);
  const text = h("span", { class: "bt" }, bookHtml(p.text));
  const notes = p.fn.map(f => h("li", { class: "bt" }, bookHtml(f)));
  const art = h("article", { class: "para", id: paraId(p.a), "data-a": p.a, tabindex: "0", "aria-expanded": "false" },
    h("p", { class: "para-text", lang: lg }, h("span", { class: "upd", hidden: true }), text,
      h("span", { class: "tag", text: shortA(p.a) }), h("span", { class: "badge" })),
    notes.length ? h("ol", { class: "fns", lang: lg }, notes) : null);
  const ctx = paraCtx(art, p);
  applyMarks(art, ctx);
  decorateText(text, ctx, "para");
  for (const li of notes) decorateText(li, ctx, "fn");
  if (besideOn()) {
    const lead = active("panels", S.me).find(d => d.lead);
    const beside = lead ? drawn(lead, Object.assign({}, ctx, { beside: true })) : null;
    if (beside) { art.classList.add("with-side"); art.append(beside); }
  }
  art.addEventListener("click", ev => onTap(art, p, ev));
  // The panel stands at the end of the page. For the keyboard it stands right after its paragraph: Enter opens it
  // with the focus on its first button, and Tab on the open paragraph goes there, not past the rest of the chapter.
  art.addEventListener("keydown", ev => {
    if (ev.target !== art) return;
    if (ev.key === "Tab" && !ev.shiftKey && panelArt() === art) { ev.preventDefault(); focusPanel(); return; }
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      if (panelArt() === art) closePanel(true);
      else { openPanel(art, p, {}); focusPanel(); }
    }
  });
  paintPara(art, list);
  return art;
}

function onTap(art, p, ev) {
  if (!art.contains(ev.target)) return;
  if (picking()) { pickTap(art, ev); return; }
  const shown = panelArt() === art;
  // A tap that ends a selection, or takes one away, is not a tap on the paragraph: the selection is the reader's
  // choice of words (onSelection).
  if (selectionIn(art) || selectionJustEnded(art)) return;
  const span = markedSpan(ev.target);
  const handled = span && markFor(span.getAttribute("data-kind"), S.me);
  // A second tap on the lit sentence closes the panel, as the first opened it.
  if (shown && handled && span.classList.contains("hl") && (panelFace() === "en" || besideOn())) { closePanel(); return; }
  if (tapMark(ev.target, paraCtx(art, p, span))) return;
  if (handled) openPanel(art, p, { span, face: "en", point: tapLine(ev) });
  else if (shown) closePanel();
  else openPanel(art, p, { point: tapLine(ev) });
}

export function paintPara(art, list) {
  paintMark(art);
  const mine = list.filter(c => c.a === art.dataset.a);
  art.classList.toggle("has-notes", mine.length > 0);
  art.classList.toggle("has-failed", mine.some(c => c.state === "failed"));
  art.querySelector(".badge").textContent = mine.length ? plural(mine.length, "comments_one", "comments_many") : "";
  const box = panelNotes(art);
  if (box) { renderNotes(art, box, mine); repaintPanel(art); }
  paintQuotes(art, list);
}

/* The backgrounds of quoted words in a paragraph: soft where one of the reader's comments quotes them, deeper
   where two or more do, and the words the quote box holds from a pick or a selection. A comment's words are found
   where it says they start (`at`), else where they first stand. Nothing is painted while the reader selects in the
   paragraph, since changing the text would take the selection away. */
export function paintQuotes(art, list) {
  const bt = bookTextOf(art);
  if (!bt || selectionIn(art)) return;
  const text = readingText(bt);
  const quoted = list.filter(c => c.a === art.dataset.a && c.quote)
    .map(c => locate(text, c.quote, typeof c.at === "number" ? c.at : null)).filter(Boolean);
  const want = marks(quoted, pickIn(art));
  const key = JSON.stringify(want);
  if (bt.getAttribute("data-marks") === key) return;
  unwrap(bt, "span.qm");
  wrapRanges(bt, want.map(m => [m[0], m[1], m[2]]), cls => h("span", { class: "qm " + cls }));
  bt.setAttribute("data-marks", key);
}

/* ---- the reader's selection ---- */

/* The words the reader selected inside this paragraph's text, without the paragraph number, the comment count and
   the footnote numbers, cut to the longest quote the server keeps: {text, at, end, rect}, where at and end are
   offsets in the reading text (null when the words are in a footnote) and rect is where they stand on the screen.
   null when no words of this paragraph are selected. */
function quoteFromSelection(art) {
  const s = window.getSelection && window.getSelection();
  if (!s || s.isCollapsed || !s.rangeCount) return null;
  const inText = node => {
    const el = node && (node.nodeType === 1 ? node : node.parentElement);
    return !!el && art.contains(el) && !!el.closest(".para-text, .fns") && !el.closest(".tag, .badge, .upd");
  };
  if (!inText(s.anchorNode) || !inText(s.focusNode)) return null;
  const range = s.getRangeAt(0);
  const most = S.me && S.me.limits ? S.me.limits.quote : DEFAULT_LIMITS.quote;
  const r = range.getBoundingClientRect();
  const rect = r && r.height ? { top: r.top, bottom: r.bottom } : null;
  const bt = bookTextOf(art);
  if (bt && bt.contains(range.startContainer) && bt.contains(range.endContainer)) {
    const text = readingText(bt);
    const q = quoteBetween(text, readingOffset(bt, range.startContainer, range.startOffset),
      readingOffset(bt, range.endContainer, range.endOffset), most);
    return q ? { text: q.text, at: q.at, end: q.end, rect } : null;
  }
  // Words in a footnote, or across the text and a footnote: their place in the paragraph's text is not known.
  const frag = range.cloneContents();
  for (const x of frag.querySelectorAll(".tag, .upd, .badge, sup.fn")) x.remove();
  const text = Array.from(frag.textContent.replace(/\s+/g, " ").trim()).slice(0, most).join("");
  return text ? { text, at: null, end: null, rect } : null;
}

/* Whether words of this paragraph are selected now. */
const selectionIn = art => !!quoteFromSelection(art);

/* When a selection in a paragraph last went away: a tap that takes a selection away does nothing more. */
let selArt = null;
let selEnded = null;
const ENDED_MS = 600;
/* How long a selection must stay the same before it opens the comment box. */
const REST_MS = 700;
let restTimer = 0;

function selectionJustEnded(art) {
  return !!selEnded && selEnded.art === art && Date.now() - selEnded.t < ENDED_MS;
}

const typingNow = () => {
  const a = document.activeElement;
  return !!a && (a.tagName === "TEXTAREA" || (a.tagName === "INPUT" && a.type !== "radio"));
};

/* The selection changed (main.js, selectionchange). Words selected in the paragraph the panel shows go into the
   quote box at once; a selection that stays REST_MS opens the comment box of its paragraph with the words. */
export function onSelection() {
  clearTimeout(restTimer);
  const s = window.getSelection && window.getSelection();
  if (!s || s.isCollapsed || !s.anchorNode) {
    if (selArt) {
      const art = selArt;
      selEnded = { art, t: Date.now() };
      selArt = null;
      // The selection is gone: the words it put in the quote box get their mark now.
      if (art.isConnected) paintQuotes(art, currentComments());
    }
    return;
  }
  if (S.view !== "chapter" || typingNow()) return;
  const el = s.anchorNode.nodeType === 1 ? s.anchorNode : s.anchorNode.parentElement;
  const art = el && el.closest("#main .para");
  if (!art) return;
  const q = quoteFromSelection(art);
  if (!q) return;
  selArt = art;
  S.lastSel = { a: art.dataset.a, text: q.text, at: q.at, end: q.end, t: Date.now() };
  const range = typeof q.at === "number" ? [q.at, q.end] : null;
  takeSelection(art, { text: q.text, at: q.at }, range);
  restTimer = setTimeout(() => {
    const now = quoteFromSelection(art);
    if (!now || now.text !== q.text || typingNow() || S.view !== "chapter") return;
    const p = S.chapter && S.chapter.paras.find(x => x.a === art.dataset.a);
    if (!p) return;
    S.lastSel = null;
    selectionRested(art, p, { text: now.text, at: now.at }, typeof now.at === "number" ? [now.at, now.end] : null, now.rect);
  }, REST_MS);
}

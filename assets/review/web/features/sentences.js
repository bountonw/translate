/* Proofreading site: a Thai sentence and its English (web/features/sentences.js).

   A paragraph of a chapter may carry `al`, its sentence pairs: [{text: [start, end], en: [[start, end], ...]}],
   each range counting code points of the text the page shows, without the footnote numbers (EXTENDING.md,
   "Sentence alignment"); `text` is the range of the paragraph's text in the book's language. The server sends them
   only with the English, so this module adds its entries to the english feature of features/english.js rather
   than declaring a feature of its own:

     - bookText (where "para"): each Thai range of a pair becomes <span class="al-s" data-kind="sentence"
       data-value="i">, split where the text crosses a tag, so the words stay as they are;
     - bookText (where "en" and "side"): each English range of pair i becomes <span class="al-e" data-s="i">, and
       a range two pairs share names both, as data-s="0 2" (core/quotes.js, englishRanges); in the panel, the
       sentence the reader tapped is lit in both languages;
     - spanMark (kind "sentence"): a tap on a Thai sentence lights it and its English beside the paragraph, and
       the panel (core/panel.js) opens on the English with that sentence lit; a tap on the lit sentence closes it;
     - panelSection "steps", under the English in the panel: Previous sentence and Next sentence, which step
       through the chapter's sentence pairs, into the next paragraph after the last pair (core/quotes.js,
       stepList), with the count of the pair shown, as "3 / 8". A screen reader reads the count after the name of
       each button (aria-describedby), and not the arrows.

   A paragraph without pairs gets no span, and every tap on it opens the panel on its whole English. The light shows
   only while the paragraph's panel is open (app.css). */

import { spanMark, bookText, panelSection } from "../core/ext.js";
import { h, wrapRanges } from "../core/dom.js";
import { t } from "../core/words.js";
import { stepList, stepFrom, englishRanges, holdsPair } from "../core/quotes.js";

function thaiSpan(i) {
  const s = document.createElement("span");
  s.className = "al-s";
  s.setAttribute("data-kind", "sentence");
  s.setAttribute("data-value", String(i));
  return s;
}

function englishSpan(i) {
  const s = document.createElement("span");
  s.className = "al-e";
  s.setAttribute("data-s", String(i));
  return s;
}

/* Light pair i (a string, or null for none) in the Thai under art and the English under en. */
function light(art, en, i) {
  for (const x of art.querySelectorAll(".bt .al-s")) x.classList.toggle("hl", i !== null && x.getAttribute("data-value") === i);
  for (const x of en.querySelectorAll(".al-e")) x.classList.toggle("hl", holdsPair(x.getAttribute("data-s"), i));
}

const pairsOf = ctx => (ctx.p && Array.isArray(ctx.p.al) ? ctx.p.al : []);
/* The number of the pair the reader tapped, as a string, or null. */
const tappedPair = ctx => {
  const span = ctx.span && ctx.span.classList && ctx.span.classList.contains("al-s") && ctx.art && ctx.art.contains(ctx.span) ? ctx.span : null;
  return span ? span.getAttribute("data-value") : null;
};

bookText({
  name: "sentences",
  feature: "english",
  order: 10,
  decorate(el, ctx) {
    const al = pairsOf(ctx);
    if (!al.length) return;
    if (ctx.where === "para") {
      wrapRanges(el, al.map((x, i) => [x.text[0], x.text[1], i]), thaiSpan);
    } else if ((ctx.where === "en" || ctx.where === "side") && ctx.art) {
      wrapRanges(el, englishRanges(al), englishSpan);
      if (ctx.where === "en") light(ctx.art, el, tappedPair(ctx));
    }
  },
});

spanMark({
  name: "sentences",
  feature: "english",
  kind: "sentence",
  // The Thai sentence and the English beside the paragraph are lit here; the panel then opens with the sentence
  // in ctx.span and lights its own English (bookText above).
  tap(span, ctx) {
    if (span.classList.contains("al-s") && ctx.art) light(ctx.art, ctx.art, span.getAttribute("data-value"));
    return false;
  },
});

/* The pair i's first piece in the Thai of paragraph a, or null. */
function thaiPiece(a, i) {
  for (const art of document.querySelectorAll("#main .para")) {
    if (art.getAttribute("data-a") === a) return art.querySelector('.para-text .al-s[data-value="' + i + '"]');
  }
  return null;
}

panelSection({
  name: "steps",
  feature: "english",
  order: 15,
  render(ctx) {
    // Only under the English: beside the paragraphs, the English shows in place and the panel holds the comment box.
    if (!ctx.p.en || !ctx.show || ctx.face !== "en") return null;
    const list = stepList(ctx.chapter.paras);
    const i = tappedPair(ctx);
    const here = { a: ctx.p.a, s: i === null ? -1 : Number(i) };
    const n = pairsOf(ctx).length;
    const go = dir => {
      const to = stepFrom(list, here.a, here.s, dir);
      if (!to) return;
      const span = to.s >= 0 ? thaiPiece(to.a, to.s) : null;
      if (span) light(span.closest(".para"), span.closest(".para"), String(to.s));
      ctx.show(to.a, span);
    };
    const prev = stepFrom(list, here.a, here.s, -1), next = stepFrom(list, here.a, here.s, 1);
    // The arrows are hidden from screen readers, and the count describes both buttons, so a screen reader says
    // "Next sentence, 5 / 13" when the focus comes back to the button pressed.
    return h("div", { class: "steps" },
      h("button", { type: "button", class: "btn ghost step-btn", "data-focus": "prev", "aria-describedby": "step-count",
        disabled: !prev, onclick: () => go(-1) }, h("span", { "aria-hidden": "true", text: "‹ " }), t("prev_sentence")),
      h("span", { class: "step-count", id: "step-count", text: here.s >= 0 && n ? here.s + 1 + " / " + n : "" }),
      h("button", { type: "button", class: "btn ghost step-btn", "data-focus": "next", "aria-describedby": "step-count",
        disabled: !next, onclick: () => go(1) }, t("next_sentence"), h("span", { "aria-hidden": "true", text: " ›" })));
  },
});

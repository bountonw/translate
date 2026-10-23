/* Proofreading site: a Thai sentence and its English (web/features/sentences.js).

   A paragraph of a chapter may carry `al`, its sentence pairs: [{text: [start, end], en: [[start, end], ...]}],
   each range counting code points of the text the page shows, without the footnote numbers (EXTENDING.md,
   "Sentence alignment"); `text` is the range of the paragraph's text in the book's language. The server sends them only with the English, so this module adds its entries to
   the english feature of features/english.js rather than declaring a feature of its own:

     - bookText (where "para"): each Thai range of a pair becomes <span class="al-s" data-kind="sentence"
       data-value="i">, split where the text crosses a tag, so the words stay as they are;
     - bookText (where "en"): each English range of pair i becomes <span class="al-e" data-s="i">, and the
       sentence the reader tapped to open the drawer is lit in both;
     - spanMark (kind "sentence"): a tap on a Thai sentence opens the drawer with that sentence and its
       English lit; with the drawer open, a tap on another sentence lights it instead, and a tap on the lit
       sentence closes the drawer, as a tap on any paragraph does.

   A paragraph without pairs gets no span, and every tap on it does what it did before. The light shows
   only while the paragraph's drawer is open (app.css). */

import { spanMark, bookText } from "../core/ext.js";

/* How each text node of a text is cut by the ranges. lengths: the code points of each text node, in order;
   ranges: [[start, end, i], ...] over the whole text, end not included. Returns, for each node, its pieces
   [[from, to, i], ...] in the node's own code points, with i = -1 for text outside every range; where ranges
   overlap, the first one listed wins. Plain, for tests/core_test.js. */
export function pieces(lengths, ranges) {
  const out = [];
  let pos = 0;
  for (const len of lengths) {
    const cuts = [0, len];
    for (const r of ranges) {
      if (r[1] <= pos || r[0] >= pos + len) continue;
      cuts.push(Math.max(0, r[0] - pos), Math.min(len, r[1] - pos));
    }
    const sorted = cuts.filter((x, k) => cuts.indexOf(x) === k).sort((x, y) => x - y);
    const list = [];
    for (let k = 0; k + 1 < sorted.length; k++) {
      const from = sorted[k], to = sorted[k + 1];
      const at = pos + from;
      const r = ranges.find(x => x[0] <= at && at < x[1]);
      list.push([from, to, r ? r[2] : -1]);
    }
    out.push(list);
    pos += len;
  }
  return out;
}

/* The text nodes of root in document order, without those inside <sup class="fn">, the footnote numbers,
   which the ranges do not count. */
function textNodes(root) {
  const out = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    let skip = false;
    for (let e = n.parentNode; e && e !== root; e = e.parentNode) {
      if (e.tagName === "SUP" && e.getAttribute("class") === "fn") { skip = true; break; }
    }
    if (!skip) out.push(n);
  }
  return out;
}

/* Wrap each range of root's text in spans made by make(i), one span per piece of a text node. */
function wrap(root, ranges, make) {
  const nodes = textNodes(root);
  const plan = pieces(nodes.map(n => Array.from(n.data).length), ranges);
  nodes.forEach((n, k) => {
    const list = plan[k];
    if (list.every(x => x[2] < 0)) return;
    const chars = Array.from(n.data);
    const frag = document.createDocumentFragment();
    for (const x of list) {
      const text = chars.slice(x[0], x[1]).join("");
      if (x[2] < 0) { frag.append(text); continue; }
      const span = make(x[2]);
      span.textContent = text;
      frag.append(span);
    }
    n.parentNode.replaceChild(frag, n);
  });
}

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
  for (const x of en.querySelectorAll(".al-e")) x.classList.toggle("hl", i !== null && x.getAttribute("data-s") === i);
}

const pairsOf = ctx => (ctx.p && Array.isArray(ctx.p.al) ? ctx.p.al : []);

bookText({
  name: "sentences",
  feature: "english",
  order: 10,
  decorate(el, ctx) {
    const al = pairsOf(ctx);
    if (!al.length) return;
    if (ctx.where === "para") {
      wrap(el, al.map((x, i) => [x.text[0], x.text[1], i]), thaiSpan);
    } else if (ctx.where === "en" && ctx.art) {
      const ranges = [];
      al.forEach((x, i) => x.en.forEach(r => ranges.push([r[0], r[1], i])));
      wrap(el, ranges, englishSpan);
      const span = ctx.span && ctx.span.classList && ctx.span.classList.contains("al-s") && ctx.art.contains(ctx.span) ? ctx.span : null;
      light(ctx.art, el, span ? span.getAttribute("data-value") : null);
    }
  },
});

spanMark({
  name: "sentences",
  feature: "english",
  kind: "sentence",
  tap(span, ctx) {
    if (!span.classList.contains("al-s") || !ctx.art) return false;
    if (!ctx.art.classList.contains("open")) return false;   // the drawer opens with this sentence lit (ctx.span)
    if (span.classList.contains("hl")) return false;          // a second tap closes the drawer
    light(ctx.art, ctx.art, span.getAttribute("data-value"));
    return true;
  },
});

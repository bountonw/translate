/* Proofreading site: quoted words, picked words and sentence steps, as plain rules (web/core/quotes.js).

   Every offset here counts code points of a paragraph's reading text: the text the page shows, without the
   footnote numbers, with no line break for <br> and no space trimmed, the same text as align_text() of
   server/content.py and the sentence ranges of EXTENDING.md, "Sentence alignment". A comment's `at` is such an
   offset: where its quoted words start.

     - pieces(): how ranges cut the text nodes of a text, for wrapping them in spans (dom.js, wrapRanges);
     - wordRanges() and wordAt(): the words of a text, for picking the quoted words by tapping the first and the
       last word; charUnder() and clusters(): the character a tap lands on;
     - quoteBetween() and cleanQuote(): the quoted words between two offsets, as the quote box takes them;
     - locate(), marks(): where each comment's quoted words stand, and the soft and deeper backgrounds;
     - stepList() and stepFrom(): the order of Previous sentence and Next sentence;
     - englishRanges() and holdsPair(): the English ranges of the sentence pairs, one range for each stretch of
       the English, which names every pair it belongs to.

   No DOM: tests/core_test.js runs this module with node. */

/* How each text node of a text is cut by the ranges. lengths: the code points of each text node, in order;
   ranges: [[start, end, i], ...] over the whole text, end not included. Returns, for each node, its pieces
   [[from, to, i], ...] in the node's own code points, with i = -1 for text outside every range; where ranges
   overlap, the first one listed wins. */
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

const SPACE = /\s/;
/* A letter, a mark on a letter, or a digit. */
const LETTER = /[\p{L}\p{M}\p{N}]/u;

/* The words of a text as ranges [start, end) of code points. seg is an Intl.Segmenter of the book's language
   with granularity "word", or null. With it, a word is a segment that holds a letter or a digit, so a Thai run
   without spaces splits into its words, and spaces and punctuation are no words. The segmenter's own isWordLike
   is not enough: Firefox gives false for some Thai words, as โรม in "(โรม 7:24 TNCV)". Without a segmenter, as in
   Safari before iOS 14.5 or Firefox before 125, a word is a run of characters between white space, which in Thai
   is often a phrase. */
export function wordRanges(text, seg) {
  const chars = Array.from(text);
  const out = [];
  if (seg) {
    let pos = 0;
    for (const s of seg.segment(text)) {
      const n = Array.from(s.segment).length;
      if (s.isWordLike || LETTER.test(s.segment)) out.push([pos, pos + n]);
      pos += n;
    }
    if (out.length) return out;
  }
  let start = -1;
  for (let i = 0; i <= chars.length; i++) {
    const space = i === chars.length || SPACE.test(chars[i]);
    if (!space && start < 0) start = i;
    if (space && start >= 0) { out.push([start, i]); start = -1; }
  }
  return out;
}

/* The word that holds the character at offset i, the character under the reader's tap (charUnder); for a space
   or a punctuation mark, the word that ends just before it, or else the nearest word. null for a text without
   words. */
export function wordAt(words, i) {
  if (!words.length) return null;
  const inside = words.find(w => w[0] <= i && i < w[1]) || words.find(w => w[1] === i);
  if (inside) return inside;
  let best = words[0];
  for (const w of words) {
    const d = i < w[0] ? w[0] - i : i - w[1];
    const b = i < best[0] ? best[0] - i : i - best[1];
    if (d < b) best = w;
  }
  return best;
}

/* A character the screen draws together with the character before it: a combining mark (Unicode's class M), such
   as a Thai or Lao vowel written above or below, a tone mark or an accent; and the Thai and Lao vowel AM (U+0E33,
   U+0EB3), whose small circle stands over the letter before it. Unicode joins the same characters into one
   grapheme cluster, and the browser measures no part of a cluster alone. */
const JOINS = /[\p{M}\u0E33\u0EB3]/u;

/* The clusters of a text, as [start, end) of code points: each is one character with the characters after it
   that the screen draws on it (JOINS). */
export function clusters(text) {
  const chars = Array.from(text);
  const out = [];
  for (let i = 0; i < chars.length; i++) {
    if (out.length && JOINS.test(chars[i])) out[out.length - 1][1] = i + 1;
    else out.push([i, i + 1]);
  }
  return out;
}

/* The character under a tap at the point x, y of the screen: the offset where its cluster starts.

   The browser gives a caret, a place between two characters, and a tap on the right half of a letter puts the
   caret after that letter. Thai writes its words without spaces, so the caret after a word's last letter is also
   the start of the next word, and a word taken at the caret would often be the next one. So the boxes of the
   characters on the screen decide instead: the clusters within `around` clusters of the caret on each side are
   measured, and the one whose box holds the point wins, or else the one whose box is nearest to it.

   text is the reading text, caret the caret's offset in it, and boxes(start, end) gives the boxes on the screen of
   the characters from start to end, [{left, top, right, bottom}], one for each line they stand on. Returns caret
   itself when no box could be measured. */
export function charUnder(text, caret, boxes, x, y, around) {
  const all = clusters(text);
  const n = around || 2;
  let k = all.findIndex(c => caret < c[1]);
  if (k < 0) k = all.length;
  let best = null, bestD = Infinity, bestX = Infinity;
  for (const c of all.slice(Math.max(0, k - n), k + n)) {
    for (const b of boxes(c[0], c[1]) || []) {
      if (!(b.right > b.left)) continue;   // a box without width, as at the end of a line, holds no character
      const dx = x < b.left ? b.left - x : x > b.right ? x - b.right : 0;
      const dy = y < b.top ? b.top - y : y > b.bottom ? y - b.bottom : 0;
      const d = dx * dx + dy * dy;
      // Boxes may overlap, as a letter and the mark above it may; the box whose middle is nearer wins then.
      const mx = Math.abs(x - (b.left + b.right) / 2);
      if (d < bestD || (d === bestD && mx < bestX)) { best = c[0]; bestD = d; bestX = mx; }
    }
  }
  return best === null ? caret : best;
}

/* The quoted words as the quote box holds them: white space runs as one space, trimmed, at most `most` code
   points. */
export function cleanQuote(text, most) {
  const q = String(text || "").replace(/\s+/g, " ").trim();
  return most ? Array.from(q).slice(0, most).join("") : q;
}

/* The quoted words of the reading text between offsets start and end: {at, end, text}, where at is the offset
   of the first character that is not white space and end the offset after the last. null when nothing but white
   space lies between. */
export function quoteBetween(text, start, end, most) {
  const chars = Array.from(text);
  let s = Math.max(0, Math.min(start, end)), e = Math.min(chars.length, Math.max(start, end));
  while (s < e && SPACE.test(chars[s])) s++;
  while (e > s && SPACE.test(chars[e - 1])) e--;
  if (e <= s) return null;
  return { at: s, end: e, text: cleanQuote(chars.slice(s, e).join(""), most) };
}

/* The reading text with every run of white space as one space, and for each of its code points the offset of
   the same code point in the reading text. */
function squeezed(chars) {
  const out = [], map = [];
  for (let i = 0; i < chars.length; i++) {
    if (SPACE.test(chars[i])) {
      if (out.length && out[out.length - 1] === " ") continue;
      out.push(" ");
    } else out.push(chars[i]);
    map.push(i);
  }
  return { chars: out, map };
}

/* Where quote stands in the reading text: [start, end) of code points, or null when it is not there. White
   space in either counts as one space. When at is a number and the quote stands there, that place wins, so a
   word that occurs twice is marked where the reader chose it; otherwise the first place the quote stands. */
export function locate(text, quote, at) {
  const q = Array.from(cleanQuote(quote));
  if (!q.length) return null;
  const sq = squeezed(Array.from(text));
  const hay = sq.chars;
  const fits = k => {
    if (k < 0 || k + q.length > hay.length) return false;
    for (let j = 0; j < q.length; j++) if (hay[k + j] !== q[j]) return false;
    return true;
  };
  const span = k => [sq.map[k], sq.map[k + q.length - 1] + 1];
  if (typeof at === "number") {
    const k = sq.map.indexOf(at);
    if (k >= 0 && fits(k)) return span(k);
  }
  for (let k = 0; k + q.length <= hay.length; k++) if (fits(k)) return span(k);
  return null;
}

/* The backgrounds of a paragraph's quoted words: [[start, end, cls], ...], in order and not overlapping. quoted
   is the place of each comment's quote ([start, end]); cls is "q1" where one comment quotes the words and "q2"
   where two or more do. pick, the words picked or selected for the comment being written ([start, end] or
   null), wins over both with "pk". */
export function marks(quoted, pick) {
  const cuts = new Set();
  for (const r of quoted) { cuts.add(r[0]); cuts.add(r[1]); }
  if (pick) { cuts.add(pick[0]); cuts.add(pick[1]); }
  const pts = Array.from(cuts).sort((x, y) => x - y);
  const out = [];
  for (let k = 0; k + 1 < pts.length; k++) {
    const s = pts[k], e = pts[k + 1];
    let cls = "";
    if (pick && pick[0] <= s && e <= pick[1]) cls = "pk";
    else {
      const n = quoted.filter(r => r[0] <= s && e <= r[1]).length;
      cls = n >= 2 ? "q2" : n === 1 ? "q1" : "";
    }
    if (!cls) continue;
    const last = out[out.length - 1];
    if (last && last[1] === s && last[2] === cls) last[1] = e;
    else out.push([s, e, cls]);
  }
  return out;
}

/* The stops of Previous sentence and Next sentence through a chapter: [{a, s}], where s is the number of a
   sentence pair, or -1 for a paragraph that has English but no pairs, which is one stop showing its whole
   English. paras: [{a, en, al}] in the chapter's order. */
export function stepList(paras) {
  const out = [];
  for (const p of paras) {
    if (!p.en) continue;
    const n = Array.isArray(p.al) ? p.al.length : 0;
    if (!n) out.push({ a: p.a, s: -1 });
    for (let s = 0; s < n; s++) out.push({ a: p.a, s });
  }
  return out;
}

/* The stop before (dir -1) or after (dir 1) the stop {a, s}, or null at either end. From a paragraph opened
   without a sentence, which is no stop, Next goes to the paragraph's first sentence and Previous to the stop
   before the paragraph. */
export function stepFrom(list, a, s, dir) {
  let i = list.findIndex(x => x.a === a && x.s === s);
  if (i < 0) {
    i = list.findIndex(x => x.a === a);
    if (i < 0) return null;
    if (dir > 0) i -= 1;
  }
  const j = i + dir;
  return j >= 0 && j < list.length ? list[j] : null;
}

/* The English ranges of a paragraph's sentence pairs al ([{text, en: [[start, end], ...]}]), for wrapping them in
   spans: [[start, end, "i j"], ...], in the order of the pairs. Where two pairs list the same English range, as when
   one English sentence is rendered by two Thai sentences around a Bible reference, the range is listed once with
   both pair numbers, so that either Thai sentence lights it. */
export function englishRanges(al) {
  const out = [], seen = {};
  (al || []).forEach((x, i) => (x.en || []).forEach(r => {
    const k = r[0] + "-" + r[1];
    if (seen[k]) seen[k][2] += " " + i;
    else { seen[k] = [r[0], r[1], String(i)]; out.push(seen[k]); }
  }));
  return out;
}

/* Whether the pair numbers of an English span ("0 2") hold pair i (a string). */
export const holdsPair = (value, i) => i !== null && String(value || "").split(" ").indexOf(i) >= 0;

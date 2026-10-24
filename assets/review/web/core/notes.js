/* Proofreading site: the reader's comments (web/core/notes.js).

   The comment cards in a paragraph's panel (core/panel.js) and at the end of a chapter, the form for a new
   comment or a change, and the section at the end of a chapter that lists comments on paragraphs no longer in it.
   The form's quote box takes the words the reader selects or picks (Pick words), with where they start in the
   paragraph's reading text, `at`, which a comment keeps; words the reader types have no known place. A card
   the server refused says why (refusals.js) and offers the buttons that help. A card says when its
   paragraph changed after the comment was written, and shows the translator's reply under the comment.
   A comment held back by the daily limit says how long until the limit resets. The cards of "My earlier
   comments" (earlier.js) are read-only cards made here too. A draft is kept per paragraph and per reader
   (store.js, draftKey). */

import { queueCreate, queueEdit, queueDelete, queueRetry, randomId } from "./outbox.js";
import { DEFAULT_LIMITS } from "./model.js";
import { draftKey, draftHolds, ownerTag } from "./store.js";
import { S, store } from "./state.js";
import { t, durationText } from "./words.js";
import { h, shortA, copyButton, twoTapButton, readingText } from "./dom.js";
import { chapterSection } from "./ext.js";
import { mutateOb, flush, keptChapter, who } from "./net.js";
import { explain, waitNote, untilReset, checkComment, counter } from "./refusals.js";
import { bookLang } from "./languages.js";
import { currentComments, repaintComments } from "./chapter.js";
import { locate } from "./quotes.js";
import { bookTextOf } from "./para.js";
import { closePanel, panelForm, startPick, forgetPick, justSaved } from "./panel.js";

const limits = () => (S.me && S.me.limits) || DEFAULT_LIMITS;

/* The message of explain(): a key of ui-strings.json and its values; {edit} names the Change button. */
export function failText(why) {
  return t(why.key, Object.assign({ edit: t("edit") }, why.vars));
}

/* Replace the panel's form with the form that changes comment cid, and put the cursor in it. */
export function editNote(art, p, cid) {
  const c = currentComments().find(x => x.client_id === cid);
  const f = panelForm(art);
  if (!c || !f) return;
  const fresh = commentForm(art, p, c, null);
  f.replaceWith(fresh);
  fresh.querySelector("textarea").focus();
}

/* The reader's comments in a paragraph's panel (art is the paragraph), or at the chapter's end for paragraphs
   that are gone (art is null: no Change button, and each comment names its paragraph). */
export function renderNotes(art, box, list) {
  box.textContent = "";
  if (!list.length) { box.append(h("p", { class: "status", text: t("no_comments") })); return; }
  const p = art && S.chapter && S.chapter.paras.find(x => x.a === art.dataset.a);
  for (const c of list) box.append(noteCard(art, p, c));
}

/* The refusals after which the site refuses a delete as well: such a card offers no Delete. */
const NO_DELETE = ["failed_closed", "failed_round", "failed_delete_closed", "failed_delete_round"];

function noteCard(art, p, c) {
  const failed = c.state === "failed";
  const why = failed ? explain(c.failure, limits()) : null;
  const wait = c.state === "saving" ? waitNote(c.why) : "";
  const recent = c.state === "saved" && Date.now() - (S.saved.get(c.client_id) || 0) < 4000;
  // A comment the daily limit holds back is not being saved now: the line under it says when it goes. A delete
  // the site refused leaves a comment that is saved: the line under it says so.
  const held = wait === "wait_daily";
  const kept = failed && !!c.failure && c.failure.type === "delete";
  const stateText = c.state === "saving" ? (held ? "" : t("st_saving")) : failed ? (kept ? "" : t("st_failed"))
    : recent ? t("st_saved") : "";
  const words = h("div", { class: "note-words", lang: bookLang(S.book) },
    c.quote ? h("p", { class: "note-quote", text: "“" + c.quote + "”" }) : null,
    h("p", { class: "note-text", text: c.text || "" }));
  const all = (c.quote ? "“" + c.quote + "”\n" : "") + (c.text || "");
  const canChange = !!p && (!failed || why.change);
  const changedAfter = !!art && c.para_changed === true;
  const acts = h("span", { class: "note-acts" },
    failed && why.retry ? h("button", { type: "button", class: "link", text: t("retry"), onclick: () => retryComment(c) }) : null,
    canChange ? h("button", { type: "button", class: "link", text: t("edit"), onclick: () => editNote(art, p, c.client_id) }) : null,
    failed || !p ? copyButton(all, words) : null,
    failed && c.id != null && NO_DELETE.indexOf(why.key) >= 0 ? null : deleteButton(c));
  return h("div", { class: "note " + c.state },
    h("div", { class: "note-top" },
      h("span", { class: "chip " + (c.kind === "wording" ? "mine" : "flag"), text: c.kind === "wording" ? t("kind_wording") : t("kind_flag") }),
      c.processed ? h("span", { class: "chip done", text: t("processed") }) : null,
      stateText ? h("span", { class: "note-state", text: stateText }) : null,
      acts),
    art ? null : h("p", { class: "note-where", text: t("para_n", { a: shortA(c.a) }) }),
    words,
    changedAfter ? h("p", { class: "note-changed", text: t("comment_para_changed") }) : null,
    failed ? h("p", { class: "note-why", text: failText(why) }) : null,
    wait ? h("p", { class: "note-wait", text: t(wait, { n: limits().comments_per_day }) }) : null,
    wait === "wait_daily" ? resetLine(c) : null,
    replyBlock(c, S.book));
}

/* How long until the daily limit resets, under a comment the limit holds back. The line is drawn again
   every minute while it shows. */
let tick = 0;
function resetLine(c) {
  const left = untilReset(c.until, Date.now());
  if (!left) return null;
  if (!tick) tick = setTimeout(() => { tick = 0; repaintComments(); }, 60000);
  return h("p", { class: "note-wait reset", text: t("wait_daily_in", { time: durationText(left) }) });
}

/* The translator's reply under a comment, and a line when the reader changed the comment after it. */
export function replyBlock(c, book) {
  const reply = typeof c.reply === "string" ? c.reply.trim() : "";
  if (!reply) return null;
  const at = Date.parse(c.reply_at || ""), updated = Date.parse(c.updated || "");
  const after = at > 0 && updated > at;
  return h("div", { class: "note-reply" },
    h("p", { class: "label", text: t("reply_label") }),
    h("p", { class: "reply-text", lang: bookLang(book), text: reply }),
    after ? h("p", { class: "note-wait", text: t("reply_after") }) : null);
}

/* A comment of an earlier review round, which can be read but not changed: its kind, whether the translator
   noted it, its paragraph, its words, whether its paragraph changed after it was written or is no longer in the
   chapter as kept on the device, and the reply. */
export function readOnlyCard(c, book) {
  const kept = c.para_changed === true ? keptChapter(book, c.ch) : null;
  const gone = !!kept && !kept.paras.some(x => x.a === c.a);
  return h("div", { class: "note saved past" },
    h("div", { class: "note-top" },
      h("span", { class: "chip " + (c.kind === "wording" ? "mine" : "flag"), text: c.kind === "wording" ? t("kind_wording") : t("kind_flag") }),
      c.processed ? h("span", { class: "chip done", text: t("processed") }) : null),
    h("p", { class: "note-where", text: t("para_n", { a: shortA(c.a) }) }),
    h("div", { class: "note-words", lang: bookLang(book) },
      c.quote ? h("p", { class: "note-quote", text: "“" + c.quote + "”" }) : null,
      h("p", { class: "note-text", text: c.text || "" })),
    c.para_changed === true ? h("p", { class: "note-changed", text: t(gone ? "earlier_para_gone" : "comment_para_changed") }) : null,
    replyBlock(c, book));
}

function deleteButton(c) {
  return twoTapButton(t("delete"), t("delete_confirm"), () => {
    mutateOb(ob => queueDelete(ob, c, who(), Date.now()));
    repaintComments();
    flush();
  });
}

function retryComment(c) {
  mutateOb(ob => queueRetry(ob, c.client_id));
  repaintComments();
  flush();
}

/* ---- the form ---- */

let formSeq = 0;

/* A count of characters under a text box once the text nears the box's limit. */
function countLine(box, max) {
  const line = h("span", { class: "count", id: "count-" + ++formSeq, hidden: true });
  box.setAttribute("aria-describedby", line.id);
  const paint = () => {
    const k = counter(box.value, max);
    line.hidden = !k;
    if (!k) return;
    line.textContent = t("count_chars", { n: k.n, max: k.max });
    line.classList.toggle("over", k.over);
  };
  paint();
  return { line, paint };
}

/* The form for a new comment (c null) or for changing comment c. quote, when given, is {text, at}: words the
   reader selected, for the quote box. Save checks the comment first and says what to fix instead of sending one
   the server would refuse. */
export function commentForm(art, p, c, quote) {
  const seq = ++formSeq;
  const dKey = draftKey(ownerTag(who()), S.book, S.ch, p.a);
  // A draft of words the page put in the quote box alone, kept by a page before this rule, is not offered.
  const kept = c ? null : store.get(dKey);
  const draft = draftHolds(kept) ? kept : null;
  const kindNow = c ? c.kind : draft ? draft.kind : "flag";
  const L = limits();

  const kinds = h("fieldset", { class: "kinds" }, h("legend", { class: "label", text: c ? t("edit_comment") : t("new_comment") }));
  for (const [value, name, hint] of [["flag", t("kind_flag"), t("kind_flag_hint")], ["wording", t("kind_wording"), t("kind_wording_hint")]]) {
    const id = "kind-" + seq + "-" + value;
    kinds.append(h("label", { class: "kind", for: id },
      h("input", { type: "radio", name: "kind", value, id, checked: kindNow === value }),
      h("span", { class: "kind-text" }, h("span", { class: "kind-name", text: name }), h("span", { class: "kind-hint", text: hint }))));
  }
  const quoteLabel = h("span");
  const lg = bookLang(S.book);
  const quoteBox = h("input", { name: "quote", id: "quote-" + seq, type: "text", autocomplete: "off", lang: lg,
    value: c ? c.quote || "" : quote ? quote.text : (draft && draft.quote) || "" });
  // Words the page put in the box, from a selection or a pick, may be replaced by a new selection; a draft keeps
  // the mark. dataset.at keeps where the words start in the paragraph's reading text, while it is known.
  if (!c && (quote || (draft && draft.quote && draft.auto))) quoteBox.dataset.auto = "1";
  const at = c ? c.at : quote ? quote.at : draft && draft.quote ? draft.at : null;
  if (typeof at === "number") quoteBox.dataset.at = String(at);
  const pick = h("button", { type: "button", class: "btn ghost pick-btn", text: t("pick_words"), onclick: startPick });
  const textLabel = h("span");
  const textBox = h("textarea", { name: "text", rows: "4", lang: lg, value: c ? c.text || "" : (draft && draft.text) || "" });
  const quoteCount = countLine(quoteBox, L.quote);
  const textCount = countLine(textBox, L.text);
  const status = h("span", { class: "status", "aria-live": "polite" });
  const f = h("form", { class: "note-form", novalidate: true },
    kinds,
    h("div", { class: "field-wrap" }, h("label", { class: "field", for: "quote-" + seq }, quoteLabel),
      h("div", { class: "quote-row" }, quoteBox, pick), quoteCount.line),
    h("div", { class: "field-wrap" }, h("label", { class: "field" }, textLabel, textBox), textCount.line),
    h("div", { class: "row" },
      h("button", { type: "submit", class: "btn", text: t("save") }),
      h("button", { type: "button", class: "btn ghost", text: c ? t("cancel") : t("close"),
        onclick: ev => (c ? f.replaceWith(commentForm(art, p, null, null)) : closePanel(ev.detail === 0)) }),
      status));

  const kind = () => (f.querySelector("input[name=kind]:checked") || {}).value || "flag";
  const relabel = () => {
    const w = kind() === "wording";
    quoteLabel.textContent = w ? t("quote_label_wording") : t("quote_label_flag");
    textLabel.textContent = w ? t("text_label_wording") : t("text_label_flag");
  };
  const quoteAt = () => (quoteBox.value.trim() && quoteBox.dataset.at ? Number(quoteBox.dataset.at) : null);
  // A draft is kept only while it holds words the reader wrote (store.js, draftHolds).
  const keepDraft = () => {
    if (c) return;
    const d = { kind: kind(), quote: quoteBox.value, text: textBox.value, auto: quoteBox.dataset.auto === "1", at: quoteAt() };
    if (draftHolds(d)) store.set(dKey, d);
    else store.del(dKey);
  };
  // Where the quoted words start, sent with the comment only when they stand there in the paragraph's text on the
  // screen: a place kept from an earlier version of the paragraph (a draft, a comment changed, a selection of the
  // last 90 seconds) is not known any more. The server checks the place too, against the version it records.
  const placeNow = q => {
    const where = q ? quoteAt() : null;
    const bt = where === null ? null : bookTextOf(art);
    const found = bt ? locate(readingText(bt), q, where) : null;
    return found && found[0] === where ? where : null;
  };
  const say = (text, bad) => {
    status.textContent = text;
    status.classList.toggle("bad", !!bad);
  };
  relabel();
  f.addEventListener("change", () => { relabel(); keepDraft(); });
  f.addEventListener("input", () => {
    keepDraft();
    quoteCount.paint();
    textCount.paint();
    if (status.classList.contains("bad")) say("", false);
  });
  // Words the reader types are the reader's own: a new selection does not replace them, and their place is not known.
  quoteBox.addEventListener("input", ev => {
    if (!ev.isTrusted) return;
    delete quoteBox.dataset.auto;
    delete quoteBox.dataset.at;
    forgetPick(art);
    keepDraft();
  });

  f.addEventListener("submit", ev => {
    ev.preventDefault();
    const k = kind();
    const text = textBox.value.trim();
    const q = quoteBox.value.trim();
    const problem = checkComment({ kind: k, quote: q, text }, L);
    if (problem) {
      say(t(problem.key, problem.vars), true);
      if (problem.field === "quote") quoteBox.focus();
      else if (problem.field === "text") textBox.focus();
      return;
    }
    const now = Date.now();
    const where = placeNow(q);
    const cid = c ? c.client_id : randomId();
    if (c) mutateOb(ob => queueEdit(ob, c, { kind: k, quote: q, text, at: where }, who(), now));
    else {
      mutateOb(ob => queueCreate(ob, { client_id: cid, book: S.book, ch: S.ch, a: p.a, kind: k, quote: q, text, at: where }, who(), now));
      store.del(dKey);
    }
    f.replaceWith(commentForm(art, p, null, null));
    // The form is empty again: the line at the top of the comment box says that the comment is being saved.
    justSaved(art, cid);
    S.lastSel = null;   // the words just saved are not offered again as the quote of the next comment
    forgetPick(art);
    repaintComments();
    flush();
  });
  return f;
}

/* ---- the section at the end of a chapter for comments on paragraphs no longer in it ---- */

chapterSection({
  name: "gone",
  order: 10,
  refresh: true,
  render(ctx) {
    const known = new Set(ctx.chapter.paras.map(p => p.a));
    const gone = ctx.comments.filter(c => !known.has(c.a));
    const box = h("div", { class: "notes" });
    renderNotes(null, box, gone);
    return h("section", { class: "gone", id: "gone", hidden: !gone.length },
      h("h2", { text: t("gone_title") }),
      h("p", { class: "hint", text: t("gone_lead") }),
      box);
  },
});

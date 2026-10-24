/* Proofreading site: the panel of a paragraph (web/core/panel.js).

   One panel holds everything that belongs to the paragraph the reader opened: the English, with "Show the
   earlier wording" and any later section under it, and the comment box with the reader's comments under it. It
   is a sheet that rises from the bottom on a screen taller than it is wide or narrower than 640 pixels, and a
   column at the right on a screen wider than it is tall and at least 640 pixels wide (SIDE). Two buttons at its
   top switch between its two faces: the English (the lead section of ext.js, panelSection) and the comment box.
   A reader whose English is off, or who shows the English beside each paragraph, gets one face, the comment box.

     - The sheet rests at half the reading area for the English and at 62 percent for the comment box, grows to
       the whole area while a text box in it has focus and rests again 300 milliseconds after the text boxes
       lose it, and stays at the height the reader drags its bar or its head to, for both faces, until it is
       dragged again or the page is left; dragged below 15 percent it closes. A tap on the bar makes it whole,
       or brings it back. On iOS 12 the keyboard cannot be measured, so the sheet takes the whole area when a
       text box gets focus, and Safari scrolls the box into view.
     - In a column, the reading column never moves: in a chapter, the page keeps the column's room free at the
       right whether the panel is open or not (app.css, html.panel-side). A resize while the reader types keeps
       the layout until the typing ends (sideMode), and the layout then follows the window.
     - The text moves only when the panel would cover the words it keeps in view, and then only enough to show
       them: on the English the lit sentence, else the picked words; on the comment box the picked or selected
       words, else the tapped line, else the lit sentence. A passage taller than the free area shows from its
       first line. The note at the foot of the screen (#sync) covers words too. Closing the panel moves
       nothing. (The translator judges this on the finished site: README.md.)
     - Pick words, beside the quote box, drops the sheet to a strip that says "Tap the first word, then the
       last word."; the two taps fill the quote box and bring the comment box back. A first tap in another
       paragraph moves the panel to that paragraph's comment box. In a column, the strip's line shows at the
       column's top. Pressed from the keyboard, Pick words gives the focus to Cancel.
     - From the keyboard the panel stands right after its paragraph: Enter on a paragraph opens the panel with
       the focus on its first button, Tab on the open paragraph goes there, and Shift+Tab comes back.

   para.js sends the paragraph's taps and the reader's selections here; notes.js draws the form and the
   comments. */

import { S, store } from "./state.js";
import { K } from "./store.js";
import { t } from "./words.js";
import { h, $, shortA, paraId, drawn, readingText, tappedOffset } from "./dom.js";
import { active } from "./ext.js";
import { bookLang } from "./languages.js";
import { wordRanges, wordAt, quoteBetween } from "./quotes.js";
import { currentComments, markJump, keepPosition, renderChapter } from "./chapter.js";
import { commentForm, renderNotes } from "./notes.js";
import { paintPara, paintQuotes, bookTextOf } from "./para.js";
import { paraOpened } from "./updates.js";
import { DEFAULT_LIMITS } from "./model.js";

/* A column at the right: wider than tall and at least 640 pixels wide. The English beside each paragraph: wider
   than tall and at least 1200 pixels wide, which leaves the Thai and the English about 21rem each beside a column
   of 28rem. app.css keys its layout on the classes these set on <html> (watchLayout). */
const SIDE = "(min-width: 640px) and (orientation: landscape)";
const WIDE = "(min-width: 1200px) and (orientation: landscape)";
/* The sheet's resting heights, as parts of the reading area, by face; and the height below which a drag closes it. */
const REST = { en: 0.5, note: 0.62 };
const CLOSE_BELOW = 0.15;
const GAP = 8;   // the space kept between uncovered words and the bar or the panel's edge

/* What the panel shows: the paragraph's article and data, the marked span lit (or null), the face ("en" or
   "note"), how many faces it has, the key of the first face's button (the lead section's label), whether the
   sheet is whole (full: false, FOCUS while a text box has focus, or BAR after a tap on the bar), and the word
   picking under way: null, or {first} with the first word's range or null. pick is the range of the words the
   quote box holds from a pick or a selection, [start, end], which para.js marks. saved is the client_id of the
   comment saved last from this panel, whose state the line at the top of the comment box shows. */
const FOCUS = "focus", BAR = "bar";
const P = { art: null, p: null, span: null, face: "note", faces: 1, label: "", full: false, picking: null, pick: null,
  saved: null };
/* The height the reader dragged the sheet to, as a part of the reading area, or null. */
let dragged = null;
let el = null;   // the panel's element, made at the first open

const matches = q => !!(window.matchMedia && window.matchMedia(q).matches);
/* Whether the reader is typing in a text box of the open panel. */
const typing = () => !!el && !el.hidden && el.contains(document.activeElement) &&
  /^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName) && document.activeElement.type !== "radio";

/* ---- where the panel is ---- */

/* Whether the panel is a column at the right. While a text box in it has focus the answer stays as it was, so a
   keyboard that changes the window's height never moves the panel from the bottom to the side. */
let side = false;
export function sideMode() {
  if (!typing()) side = matches(SIDE);
  return side;
}

/* Whether the layout of the page (html.panel-side) no longer fits the window, after a resize while the reader
   typed. */
const stale = () => document.documentElement.classList.contains("panel-side") !== matches(SIDE);

/* The typing ended (the text boxes lost the focus, Save, or Close): a layout kept for the typing follows the
   window now, so the column never stays without its room, nor the room without its column. */
function afterTyping() {
  if (!typing() && stale()) watchLayout();
}

/* Whether the screen is wide enough for the Thai, the English beside it and the panel. */
export const wideEnough = () => matches(WIDE);

/* Whether each paragraph shows its English beside it: the reader's choice, kept on the device (rv.side), on a
   screen wide enough, with a lead section (the English) on for this reader. */
export function besideOn() {
  return store.get(K.side) === true && wideEnough() && active("panels", S.me).some(d => d.lead);
}

export function setBeside(on) {
  store.set(K.side, !!on);
}

/* Set the classes of <html> that app.css lays the page out by, and draw again what changes with them: the panel's
   place, and the chapter when the English beside the paragraphs comes or goes (chapter.js marks a chapter drawn
   with it by body.beside). main.js calls it at the start and on every resize. */
export function watchLayout() {
  const root = document.documentElement;
  const was = root.classList.contains("panel-side");
  root.classList.toggle("panel-side", sideMode());
  root.classList.toggle("wide", wideEnough());
  // Between the sheet and the column the text flows again at its new width: the words in view are found again.
  if (el && P.art) { place(); if (was !== side) uncover(null); }
  if (S.view === "chapter" && S.chapter && besideOn() !== document.body.classList.contains("beside")) {
    if (P.art) closePanel();
    const data = S.chapter;
    keepPosition(() => renderChapter(data, false));
  }
}

const barBottom = () => {
  const bar = $("bar");
  return bar && !bar.hidden ? Math.max(0, bar.getBoundingClientRect().bottom) : 0;
};
const areaHeight = () => Math.max(120, window.innerHeight - barBottom());

/* The sheet's height in pixels now, or null for the strip of word picking, whose height is its content's. */
function sheetHeight() {
  if (P.picking) return null;
  if (P.full) return areaHeight();
  const part = dragged !== null ? dragged : REST[P.face];
  return Math.round(areaHeight() * part);
}

/* A sheet whose body is lower than this keeps Previous and Next sentence in the flow of the English (app.css,
   .panel.short), so the English and its lit sentence are not hidden under them. */
const SHORT_BODY = 200;

/* Put the panel where it belongs now, at its height, and keep room at the foot of the chapter so its last words
   can be scrolled above the sheet. The room stays after the panel closes, so closing moves nothing. A sheet made
   whole for typing covers every word, so it asks for no room. */
function place() {
  const column = sideMode();
  el.classList.toggle("column", column);
  el.classList.toggle("sheet", !column);
  el.classList.toggle("strip", !!P.picking);
  el.style.height = column || P.picking ? "" : sheetHeight() + "px";
  const shown = column ? 0 : el.offsetHeight;
  document.body.style.setProperty("--sheet-h", shown + "px");
  const body = part(".panel-body");
  el.classList.toggle("short", !column && !P.picking && body.clientHeight < SHORT_BODY);
  const main = $("main");
  if (!column && main && !P.full) {
    const room = shown + 24;
    if ((parseFloat(main.style.paddingBottom) || 0) < room) main.style.paddingBottom = room + "px";
  }
}

/* The free area of the screen, where words are not covered: below the bar, above the sheet or left of the column,
   and above the note at the foot of the screen when it shows. */
function freeArea() {
  const top = barBottom() + GAP;
  let bottom = (sideMode() || !P.art ? window.innerHeight : el.getBoundingClientRect().top) - GAP;
  const note = $("sync");
  if (note && !note.hidden) {
    const r = note.getBoundingClientRect();
    if (r.height) bottom = Math.min(bottom, r.top - GAP);
  }
  return { top, bottom };
}

/* How far to scroll so that the passage {top, bottom} (screen pixels) shows in the free area: 0 when it shows
   already; a passage taller than the area shows from its first line. */
function uncoverBy(r) {
  if (!r) return 0;
  const f = freeArea();
  if (r.bottom - r.top > f.bottom - f.top) return r.top - f.top;
  if (r.bottom > f.bottom) return r.bottom - f.bottom;
  if (r.top < f.top) return r.top - f.top;
  return 0;
}

/* The screen rectangle around a list of elements, or null. */
function around(list) {
  let top = Infinity, bottom = -Infinity;
  for (const x of list) {
    for (const r of Array.from(x.getClientRects())) {
      if (!r.height) continue;
      top = Math.min(top, r.top);
      bottom = Math.max(bottom, r.bottom);
    }
  }
  return top === Infinity ? null : { top, bottom };
}

/* What the text should keep in view. On the English: the lit sentence, else the picked words, else the line the
   reader tapped. On the comment box the words being quoted are what the reader works on: the picked words, else
   point (the selection, or the line the reader tapped), else the lit sentence. */
function target(point) {
  const bt = bookTextOf(P.art);
  const lit = bt ? around(bt.querySelectorAll(".hl")) : null;
  const picked = bt ? around(bt.querySelectorAll(".pk")) : null;
  if (P.face === "note") return picked || point || lit || null;
  return lit || picked || point || null;
}

function uncover(point) {
  const by = uncoverBy(target(point));
  if (by) { markJump(); window.scrollBy(0, by); }
}

/* Run fn, which changes the size of the text (A− and A+), keeping the words the panel keeps in view where they
   stand on the screen, the English scrolled to its lit sentence again, and those words out from under the panel.
   false, without running fn, when the panel is closed or keeps no words in view. */
export function keepLit(fn) {
  const was = P.art ? target(null) : null;
  if (!was) return false;
  fn();
  const now = target(null);
  if (now && now.top !== was.top) { markJump(); window.scrollBy(0, now.top - was.top); }
  place();
  if (P.face === "en") scrollFace();
  uncover(null);
  return true;
}

/* The note at the foot of the screen came up while the panel is open: it may cover the words in view. */
export function noteShown() {
  if (el && P.art && !P.picking) uncover(null);
}

/* ---- the panel's element ---- */

function make() {
  el = h("aside", { class: "panel", id: "panel", hidden: true });
  const grab = h("div", { class: "grab-zone", "aria-hidden": "true" }, h("span", { class: "grab" }));
  const head = h("div", { class: "panel-head" },
    h("span", { class: "panel-where" }),
    h("div", { class: "faces", role: "group" },
      h("button", { type: "button", class: "face-btn", "data-face": "en", onclick: () => showFace("en", true) }),
      h("button", { type: "button", class: "face-btn", "data-face": "note", onclick: () => showFace("note", true) })),
    h("button", { type: "button", class: "panel-close", onclick: ev => closePanel(ev.detail === 0) }));
  const body = h("div", { class: "panel-body" },
    h("section", { class: "face face-en" }),
    h("section", { class: "face face-note" },
      h("p", { class: "status saved-line", "aria-live": "polite", hidden: true }),
      h("div", { class: "form-slot" }),
      h("div", { class: "under-form" }),
      h("section", { class: "notes-block" }, h("p", { class: "label your-label" }), h("div", { class: "notes" }))));
  const strip = h("div", { class: "pick-strip", role: "status" },
    h("span", { class: "pick-text" }),
    h("button", { type: "button", class: "link pick-cancel", onclick: () => stopPick(true) }));
  el.append(grab, head, body, strip);
  // A text box in the panel makes the sheet whole while the reader types; Save brings it back, and so does the
  // end of the typing (focusout), 300 milliseconds later, so that a tap on Save or Pick words lands first. A sheet
  // made whole by a tap on the bar stays whole.
  el.addEventListener("focusin", ev => {
    const x = ev.target;
    if (/^(INPUT|TEXTAREA)$/.test(x.tagName) && x.type !== "radio" && !P.full) { P.full = FOCUS; place(); }
  });
  el.addEventListener("focusout", () => {
    setTimeout(afterTyping, 0);
    setTimeout(() => {
      if (P.full === FOCUS && P.art && !P.picking && !typing()) { P.full = false; place(); uncover(null); }
    }, 300);
  });
  el.addEventListener("submit", () => setTimeout(() => {
    afterTyping();
    if (P.full && P.art && !typing()) { P.full = false; place(); }
  }, 0));
  // Shift+Tab on the panel's first button goes back to its paragraph, which stands before it for the keyboard.
  el.addEventListener("keydown", ev => {
    if (ev.key === "Tab" && ev.shiftKey && P.art && ev.target === firstButton()) { ev.preventDefault(); focusQuietly(P.art); }
  });
  wireDrag(grab, head);
  document.body.append(el);
}

/* Drag the sheet by its bar or by its head outside the head's buttons, as iOS and Android sheets drag by their
   whole top; a tap on the bar makes the sheet whole or brings it back. Touch and mouse events, since iOS 12 has
   no pointer events. */
function wireDrag(grab, head) {
  let y0 = null, h0 = 0, moved = false, byHead = false;
  const start = (y, fromHead) => { y0 = y; h0 = el.offsetHeight; moved = false; byHead = fromHead; el.classList.add("dragging"); };
  const move = y => {
    if (y0 === null) return;
    if (Math.abs(y - y0) > 4) moved = true;
    if (moved) el.style.height = Math.max(64, Math.min(areaHeight(), h0 + (y0 - y))) + "px";
  };
  const end = () => {
    if (y0 === null) return;
    y0 = null;
    el.classList.remove("dragging");
    const hNow = el.offsetHeight;
    if (!moved) {
      if (!byHead) { P.full = P.full ? false : BAR; place(); }
      return;
    }
    if (hNow < areaHeight() * CLOSE_BELOW) { dragged = null; P.full = false; closePanel(); return; }
    dragged = hNow / areaHeight();
    P.full = false;
    place();
    // The English comes back to its lit sentence at the new height.
    if (P.face === "en") scrollFace();
  };
  // The head drags only a sheet, and never from one of its buttons.
  const fromHead = ev => el.classList.contains("sheet") && !(ev.target.closest && ev.target.closest("button"));
  for (const [zone, isHead] of [[grab, false], [head, true]]) {
    zone.addEventListener("touchstart", ev => { if (!isHead || fromHead(ev)) start(ev.touches[0].clientY, isHead); }, { passive: true });
    zone.addEventListener("touchmove", ev => { if (y0 !== null) { ev.preventDefault(); move(ev.touches[0].clientY); } }, { passive: false });
    zone.addEventListener("touchend", end);
    zone.addEventListener("touchcancel", end);
    zone.addEventListener("mousedown", ev => { if (!isHead || fromHead(ev)) { ev.preventDefault(); start(ev.clientY, isHead); } });
  }
  document.addEventListener("mousemove", ev => { if (y0 !== null) move(ev.clientY); });
  document.addEventListener("mouseup", end);
}

const part = sel => el.querySelector(sel);

/* ---- what the panel shows ---- */

/* The article of the paragraph the panel shows, or null when it is closed. */
export const panelArt = () => P.art;
export const panelFace = () => P.face;
/* The comment form in the panel, when it belongs to art. */
export const panelForm = art => (P.art && P.art === art ? part(".form-slot form.note-form") : null);
/* The box of the reader's comments in the panel, when it shows art. */
export const panelNotes = art => (P.art && P.art === art ? part(".notes") : null);
/* The words the quote box holds from a pick or a selection in art, [start, end], or null. */
export const pickIn = art => (P.art === art ? P.pick : null);
export const picking = () => !!P.picking;

/* The context of a panel section (ext.js, panelSection). face says where the section stands: "en" on the lead's
   face, "note" under the comment form when the panel has no lead face. */
function sectionCtx(span, face) {
  return { p: P.p, art: P.art, chapter: S.chapter, me: S.me, book: S.book, lang: bookLang(S.book), span: span || null,
    show: showStop, beside: false, face };
}

/* Show paragraph a with span lit (null for none) on the English face, as Previous and Next sentence do. */
function showStop(a, span) {
  const p = S.chapter && S.chapter.paras.find(x => x.a === a);
  const art = p && document.getElementById(paraId(p.a));
  if (art) openPanel(art, p, { span, face: "en" });
}

/* Open the panel on paragraph p (its article art), or show it there anew. opts: {span, face, quote, point}:
   span is the marked span the reader tapped (lit, with its English); face is "en" or "note" (by default the
   English when there is one); quote is {text, at} for the quote box, from a selection; point is the line the
   reader tapped, {top, bottom} on the screen, which stays in view. */
export function openPanel(art, p, opts) {
  const o = opts || {};
  if (!el) make();
  const same = P.art === art;
  if (P.art && !same) leaveArt(P.art);
  for (const x of document.querySelectorAll("#main .para.was")) if (x !== art) x.classList.remove("was");
  if (!same) { P.pick = null; P.picking = null; P.saved = null; }
  P.art = art;
  P.p = p;
  P.span = o.span || null;
  if (!typing()) P.full = false;
  art.classList.add("open");
  art.classList.remove("was");
  art.setAttribute("aria-expanded", "true");
  const focusKey = document.activeElement && el.contains(document.activeElement) ? document.activeElement.getAttribute("data-focus") : null;
  fill(same);
  P.face = P.faces === 1 ? "note" : o.face || "en";
  if (o.quote) takeQuote(o.quote);
  el.hidden = false;
  el.setAttribute("aria-label", t("para_n", { a: shortA(p.a) }));
  paintFaces();
  place();
  paintPara(art, currentComments());
  paraOpened(art);
  scrollFace();
  uncover(o.point);
  if (focusKey) {
    const again = el.querySelector('[data-focus="' + focusKey + '"]');
    if (again && !again.disabled) again.focus();
  }
}

/* Draw the panel's sections for the paragraph shown. same: the panel showed this paragraph already, so its
   comment form, with what the reader typed, stays. */
function fill(same) {
  const beside = besideOn();
  const all = active("panels", S.me);
  const lead = beside ? [] : all.filter(d => d.lead).map(d => drawn(d, sectionCtx(P.span, "en"))).filter(Boolean);
  const where = lead.length ? "en" : "note";
  const rest = all.filter(d => !d.lead).map(d => drawn(d, sectionCtx(P.span, where))).filter(Boolean);
  P.faces = lead.length ? 2 : 1;
  const leadDef = all.find(d => d.lead);
  P.label = leadDef && leadDef.label ? leadDef.label : "lang_en";
  const faceEn = part(".face-en"), under = part(".under-form");
  faceEn.textContent = "";
  under.textContent = "";
  if (P.faces === 2) faceEn.append(...lead, ...rest);
  else under.append(...rest);
  const slot = part(".form-slot");
  if (!same || !slot.firstChild) {
    slot.textContent = "";
    slot.append(commentForm(P.art, P.p, null, remembered(P.art)));
  }
  part(".your-label").textContent = t("your_comments");
  part(".panel-where").textContent = shortA(P.p.a);
}

/* Words the reader selected in the paragraph shortly before, which a phone may have cleared by the time of the
   tap (para.js keeps them in S.lastSel for 90 seconds). */
function remembered(art) {
  const last = S.lastSel;
  if (!(last && last.a === art.dataset.a && Date.now() - last.t < 90000)) return null;
  S.lastSel = null;
  P.pick = typeof last.at === "number" ? [last.at, last.end] : null;
  return { text: last.text, at: last.at };
}

/* The words of the face buttons, which face shows, and the count of the reader's comments on the comment button. */
function paintFaces() {
  const n = currentComments().filter(c => c.a === P.art.dataset.a).length;
  const btnEn = part('.face-btn[data-face="en"]'), btnNote = part('.face-btn[data-face="note"]');
  btnEn.textContent = t(P.label);
  btnEn.hidden = P.faces === 1;
  btnNote.textContent = t("write_comment") + (n ? " · " + n : "");
  for (const b of [btnEn, btnNote]) b.setAttribute("aria-pressed", String(b.getAttribute("data-face") === P.face));
  part(".face-en").hidden = P.face !== "en";
  part(".face-note").hidden = P.face !== "note";
  el.classList.toggle("one-face", P.faces === 1);
  const close = part(".panel-close");
  close.textContent = t("close");
  part(".pick-text").textContent = t("pick_hint");
  part(".pick-cancel").textContent = t("cancel");
  paintSaved();
}

/* The line at the top of the comment box: the state of the comment just saved from this panel, as its card says
   it, "Saving…" while it is sent, "Saved" for 4 seconds after (net.js keeps the time in S.saved, and draws the
   comments again once the 4 seconds are over), or "Not saved"; the form under it is empty again, and the card
   stands below the form, often below the screen. */
const SAVED_MS = 4000;
function paintSaved() {
  const line = part(".saved-line");
  const c = P.saved ? currentComments().find(x => x.client_id === P.saved) : null;
  let text = "";
  if (c && c.state === "saving") text = t("st_saving");
  else if (c && c.state === "failed") text = t("st_failed");
  else if (c && c.state === "saved" && Date.now() - (S.saved.get(c.client_id) || 0) < SAVED_MS) text = t("st_saved");
  line.textContent = text;
  line.hidden = !text;
  line.classList.toggle("bad", !!c && c.state === "failed");
}

/* notes.js saved comment cid from the form of art's panel. */
export function justSaved(art, cid) {
  if (P.art !== art || !el) return;
  P.saved = cid;
  paintSaved();
}

/* The reader opened the panel from the keyboard: the focus goes to its first button, so that Tab goes on inside the
   panel and a screen reader says where the focus is. */
export function focusPanel() {
  focusQuietly(firstButton());
}

const firstButton = () => (el && !el.hidden ? Array.from(el.querySelectorAll(".panel-head button")).find(x => !x.hidden) : null);

function focusQuietly(x) {
  if (x) { try { x.focus({ preventScroll: true }); } catch (e) { x.focus(); } }
}

/* The panel again, on the same paragraph, light and face, as after a change of language. */
export function redrawPanel() {
  if (P.art) openPanel(P.art, P.p, { span: P.span, face: P.face });
}

/* The comment count on the comment button again, as after a comment was saved. */
export function repaintPanel(art) {
  if (P.art === art && el) paintFaces();
}

/* Scroll the face's body: the English to its lit sentence, the comment box to its top. */
function scrollFace() {
  const body = part(".panel-body");
  const lit = P.face === "en" ? part(".face-en .hl") : null;
  if (!lit) { body.scrollTop = 0; return; }
  body.scrollTop += lit.getBoundingClientRect().top - body.getBoundingClientRect().top - GAP;
}

/* Switch to the English ("en") or the comment box ("note"). The quote box keeps what it holds: it starts empty
   unless a selection, a pick or a draft filled it. byHand: the reader pressed the button, so the focus goes to the
   comment box's first choice, which opens no keyboard on a phone. point, when given, is the place of the words
   just selected, {top, bottom}, which the comment box keeps in view. */
export function showFace(face, byHand, point) {
  if (!P.art || (face === "en" && P.faces === 1)) return;
  if (P.picking) stopPick(false);
  P.face = face;
  P.full = false;
  paintFaces();
  place();
  scrollFace();
  uncover(point || null);
  if (byHand && face === "note") {
    const f = part(".form-slot form");
    const first = f && (f.querySelector("input[name=kind]:checked") || f.querySelector("input"));
    if (first) { try { first.focus({ preventScroll: true }); } catch (e) { first.focus(); } }
  }
}

/* The paragraph leaves the panel: no longer open, its light gone, and a soft background until another opens. */
function leaveArt(art) {
  art.classList.remove("open");
  art.classList.add("was");
  art.setAttribute("aria-expanded", "false");
  for (const x of Array.from(art.querySelectorAll(".hl"))) x.classList.remove("hl");
  const pickWas = P.pick;
  P.pick = null;
  if (pickWas) paintQuotes(art, currentComments());
}

/* Close the panel. Nothing moves. fromKeys: the reader closed it from the keyboard (Escape, or Close pressed with
   Enter, whose click has no count of clicks), so the focus goes back to the paragraph; after a tap the focus stays,
   since moving it could scroll the page on iOS 12, which ignores preventScroll. */
export function closePanel(fromKeys) {
  if (!P.art) return;
  const art = P.art;
  P.picking = null;
  document.body.classList.remove("picking");
  leaveArt(art);
  P.art = P.p = P.span = P.saved = null;
  P.full = false;
  el.hidden = true;
  el.classList.remove("strip");
  part(".form-slot").textContent = "";
  document.body.style.setProperty("--sheet-h", "0px");
  if (fromKeys && art.isConnected) { try { art.focus({ preventScroll: true }); } catch (e) { art.focus(); } }
  // A newer text of the chapter waited while the panel was open.
  if (S.waiting && S.view === "chapter") {
    const data = S.waiting;
    keepPosition(() => renderChapter(data, false));
  }
  // A resize while the reader typed: the layout follows the window now.
  afterTyping();
  // A paragraph drawn anew keeps the soft background of the paragraph opened last.
  const again = !art.isConnected && S.view === "chapter" ? document.getElementById(paraId(art.dataset.a)) : null;
  if (again) again.classList.add("was");
}

/* The chapter leaves the screen: the panel closes without drawing a newer text that waited for it (S.waiting),
   since the chapter is not shown any more, and forgets the dragged height. */
export function resetPanel() {
  S.waiting = null;
  if (P.art) closePanel();
  dragged = null;
  const main = $("main");
  if (main) main.style.paddingBottom = "";
}

/* ---- the quote box ---- */

/* Put words in the quote box when it is empty or holds words the page put there; never over words the reader
   typed. q = {text, at}: at is where the words start in the paragraph's reading text, or null. */
function takeQuote(q) {
  const box = part(".form-slot form input[name=quote]");
  if (!box || (box.value && box.dataset.auto !== "1")) return false;
  if (box.value !== q.text || box.dataset.at !== String(q.at)) {
    box.value = q.text;
    box.dataset.auto = "1";
    if (typeof q.at === "number") box.dataset.at = String(q.at); else delete box.dataset.at;
    box.dispatchEvent(new Event("input", { bubbles: true }));
  }
  return true;
}

/* Words selected in the paragraph the panel shows go into its quote box at once. range: [start, end] in the
   reading text, which para.js marks once the selection is gone. */
export function takeSelection(art, q, range) {
  if (P.art !== art) return;
  if (takeQuote(q)) P.pick = range;
}

/* A selection rested in a paragraph: the comment box opens with the words in it, and the selection stays. The
   selected words are kept in view, out from under the comment box. rect is where they stood when the selection
   was read; changing the face moves no text before it is used. */
export function selectionRested(art, p, q, range, rect) {
  if (P.art === art) {
    if (P.picking) stopPick(false);
    takeSelection(art, q, range);
    if (P.face !== "note") showFace("note", false, rect);
    else uncover(rect);
    return;
  }
  openPanel(art, p, { face: "note", quote: q, point: rect });
  P.pick = range;
}

/* The quote box no longer holds the words of a pick or a selection: the reader typed in it, or saved the comment.
   Their mark goes. */
export function forgetPick(art) {
  if (P.art !== art || !P.pick) return;
  P.pick = null;
  paintQuotes(art, currentComments());
}

/* ---- picking the quoted words by tapping the first and the last word ---- */

let segmenter;
/* An Intl.Segmenter of words for the book's language, or null where the browser has none (quotes.js says what
   a word is then). */
function wordSegmenter() {
  if (segmenter === undefined) {
    segmenter = null;
    try {
      if (typeof Intl === "object" && Intl.Segmenter) segmenter = new Intl.Segmenter(bookLang(S.book) || "th", { granularity: "word" });
    } catch (e) { segmenter = null; }
  }
  return segmenter;
}

/* Pick words: the sheet drops to a strip, so the paragraph shows whole for the two taps. ev is the click on Pick
   words: pressed from the keyboard (a click with no count of clicks), the focus waits on Cancel, since words are
   picked with a pointer, and Enter or Escape there brings the comment box back. */
export function startPick(ev) {
  if (!P.art) return;
  if (document.activeElement && el.contains(document.activeElement)) document.activeElement.blur();
  P.picking = { first: null };
  P.full = false;
  document.body.classList.add("picking");
  place();
  uncover(null);
  if (ev && ev.detail === 0) focusQuietly(part(".pick-cancel"));
}

/* Stop picking. back: the reader pressed Cancel, so the comment box comes back as it was. The focus that waited on
   Cancel goes back to Pick words. */
export function stopPick(back) {
  if (!P.picking) return;
  const fromCancel = document.activeElement === part(".pick-cancel");
  P.picking = null;
  document.body.classList.remove("picking");
  if (back && P.art) {
    P.pick = null;
    paintQuotes(P.art, currentComments());
  }
  if (P.art) { place(); paintFaces(); }
  if (fromCancel) focusQuietly(part(".form-slot .pick-btn"));
}

/* A tap on a paragraph while picking: true when it was for the picker. The first tap marks a word; the second fills
   the quote box with the words from the first to the last. A tap on a word of another paragraph shows which words
   the reader means: the panel moves to that paragraph's comment box, and the tap is its first word. The draft of
   the paragraph left stays on the device, as every draft does. */
export function pickTap(art, ev) {
  if (!P.picking) return false;
  const bt = bookTextOf(art);
  const i = bt ? tappedOffset(bt, ev.clientX, ev.clientY) : null;
  if (i === null) return true;
  const text = readingText(bt);
  const word = wordAt(wordRanges(text, wordSegmenter()), i);
  if (!word) return true;
  if (art !== P.art) {
    const p = S.chapter && S.chapter.paras.find(x => x.a === art.dataset.a);
    if (!p) return true;
    openPanel(art, p, { face: "note" });
    P.picking = { first: null };
    document.body.classList.add("picking");
    place();
  }
  if (!P.picking.first) {
    P.picking.first = word;
    P.pick = word.slice();
    paintQuotes(art, currentComments());
    return true;
  }
  const first = P.picking.first;
  const most = S.me && S.me.limits ? S.me.limits.quote : DEFAULT_LIMITS.quote;
  const q = quoteBetween(text, Math.min(first[0], word[0]), Math.max(first[1], word[1]), most);
  P.picking = null;
  document.body.classList.remove("picking");
  if (q) {
    // The reader chose these words now, so they take the place of words typed before.
    const box = part(".form-slot form input[name=quote]");
    if (box && box.value && box.dataset.auto !== "1") { box.value = ""; delete box.dataset.auto; }
    takeQuote(q);
    P.pick = [q.at, q.end];
  }
  paintQuotes(art, currentComments());
  P.face = "note";
  paintFaces();
  place();
  uncover(null);
  return true;
}

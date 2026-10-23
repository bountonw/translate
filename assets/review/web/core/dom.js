/* Proofreading site: building the page (web/core/dom.js).

   h() makes elements; bookHtml() rebuilds book text safely; decorateText() runs the bookText place and
   the dots of "Show spaces"; the small buttons every screen uses. */

import { markFor, safely, active } from "./ext.js";
import { K } from "./store.js";
import { S, store } from "./state.js";
import { t } from "./words.js";

export const $ = id => document.getElementById(id);
export const shortA = a => String(a || "").replace(/^\S+\s+/, "");          // "SC 9.1" -> "9.1"
export const paraId = a => "p-" + String(a).replace(/[^A-Za-z0-9]/g, "-");

/* An element with properties and children. "class", "text", "value" and "checked" are set as
   properties, "on..." as listeners, everything else as attributes; null and false are left out. */
export function h(tag, props, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "text") e.textContent = v;
    else if (k === "value" || k === "checked") e[k] = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : String(v));
  }
  for (const c of kids.flat()) if (c != null && c !== false) e.append(c);
  return e;
}

/* Book text arrives as HTML made by the server's parser. It is parsed in an inert template and
   rebuilt with a short list of tags and only the class attribute, plus data-kind and data-value on
   a span: the marked span of the content model (EXTENDING.md), which a feature may give a meaning
   through spanMark() in ext.js. Reader text never comes here. */
const BOOK_TAGS = new Set(["EM", "I", "STRONG", "B", "SUP", "SUB", "SMALL", "SPAN", "P", "BR"]);
const KIND_RE = /^[a-z][a-z0-9_-]{0,31}$/;
export function bookHtml(html) {
  const tpl = document.createElement("template");
  tpl.innerHTML = String(html || "");
  const out = document.createDocumentFragment();
  (function copy(from, to) {
    for (const n of from.childNodes) {
      if (n.nodeType === 3) to.append(n.data);
      if (n.nodeType !== 1 || n.tagName === "SCRIPT" || n.tagName === "STYLE") continue;
      let into = to;
      if (BOOK_TAGS.has(n.tagName)) {
        into = document.createElement(n.tagName.toLowerCase());
        const cls = n.getAttribute("class");
        if (cls) into.className = cls;
        const kind = n.tagName === "SPAN" ? n.getAttribute("data-kind") : null;
        if (kind && KIND_RE.test(kind)) {
          into.setAttribute("data-kind", kind);
          const value = n.getAttribute("data-value");
          if (value && value.length <= 200) into.setAttribute("data-value", value);
        }
        to.append(into);
      }
      copy(n, into);
    }
  })(tpl.content, out);
  return out;
}

/* Give each marked span under el to the feature that handles its kind. Until a feature does, a
   marked span shows its words like any span and does nothing on a tap. */
export function applyMarks(el, ctx) {
  for (const span of el.querySelectorAll("span[data-kind]")) {
    const def = markFor(span.getAttribute("data-kind"), S.me);
    if (def && def.decorate) safely(def, () => def.decorate(span, ctx));
  }
}

/* The marked span a tap landed on, or null. */
export const markedSpan = target => (target && target.closest ? target.closest("span[data-kind]") : null);

/* The feature's answer to a tap on a marked span: true when it handled the tap. */
export function tapMark(target, ctx) {
  const span = markedSpan(target);
  if (!span) return false;
  const def = markFor(span.getAttribute("data-kind"), S.me);
  return !!(def && def.tap && safely(def, () => def.tap(span, ctx), false) === true);
}

/* ---- book text once drawn: the bookText place, then the dots of "Show spaces" ----
   Every element that holds the book's own text (a paragraph, a footnote, a chapter title, the earlier
   wording) carries the class "bt". The English is the source, not the book text, and gets no dots. */

/* Run every bookText entry that is on over el, then put the dots on its spaces when they are shown. ctx is
   that of drawerPanel; where says what el holds (ext.js, bookText). */
export function decorateText(el, ctx, where) {
  const c = Object.assign({}, ctx, { where });
  for (const d of active("texts", S.me)) if (d.decorate) safely(d, () => d.decorate(el, c));
  if (el.classList.contains("bt") && spacesOn()) markSpaces(el);
}

export const spacesOn = () => store.get(K.spaces) === true;

/* Wrap every space of el's text in <span class="sp"> </span>. The dot is the span's ::after (app.css), which
   is not text, so selecting or copying the words gives the same text as without the dots. */
export function markSpaces(el) {
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
  const nodes = [];
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    if (n.data.indexOf(" ") >= 0 && !(n.parentNode.classList && n.parentNode.classList.contains("sp"))) nodes.push(n);
  }
  for (const n of nodes) {
    const frag = document.createDocumentFragment();
    const parts = n.data.split(" ");
    parts.forEach((part, i) => {
      if (i) frag.append(h("span", { class: "sp" }, " "));
      if (part) frag.append(part);
    });
    n.parentNode.replaceChild(frag, n);
  }
}

/* Take the spans of markSpaces() out again, leaving the text as it was. */
export function unmarkSpaces(el) {
  for (const sp of Array.from(el.querySelectorAll("span.sp"))) {
    const parent = sp.parentNode;
    while (sp.firstChild) parent.insertBefore(sp.firstChild, sp);
    parent.removeChild(sp);
  }
  el.normalize();
}

/* Show or hide the dots on every space of the book text on the screen, and remember the choice on this
   device. */
export function setSpaces(on) {
  store.set(K.spaces, !!on);
  for (const el of document.querySelectorAll(".bt")) {
    if (on) markSpaces(el);
    else unmarkSpaces(el);
  }
}

export function showNotice(text) {
  const n = $("notice");
  n.textContent = text;
  n.hidden = false;
}

/* A button that copies text; where the clipboard is blocked it selects the text for the reader instead. */
export function copyButton(text, target) {
  const b = h("button", { type: "button", class: "link", text: t("copy") });
  b.addEventListener("click", () => {
    const select = () => {
      const r = document.createRange();
      r.selectNodeContents(target);
      const s = window.getSelection();
      s.removeAllRanges();
      s.addRange(r);
    };
    const done = () => {
      b.textContent = t("copied");
      setTimeout(() => { if (b.isConnected) b.textContent = t("copy"); }, 2500);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, select);
    else select();
  });
  return b;
}

/* A button that acts on the second tap within 4 seconds. */
export function twoTapButton(label, confirmLabel, action) {
  const b = h("button", { type: "button", class: "link danger", text: label });
  let armedAt = 0;
  b.addEventListener("click", () => {
    if (Date.now() - armedAt > 4000) {
      armedAt = Date.now();
      b.textContent = confirmLabel;
      setTimeout(() => { if (b.isConnected) b.textContent = label; }, 4000);
      return;
    }
    action();
  });
  return b;
}

/* An element a feature draws, or null when it draws nothing or fails. */
export function drawn(def, ctx) {
  const el = safely(def, () => def.render(ctx), null);
  return el && el.nodeType ? el : null;
}

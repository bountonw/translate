/* Proofreading site: the English feature's part of the page (web/features/english.js).

   The server's feature server/features/english.py has one setting, english.on. When it is on for a
   reader, GET /api/me says {"features": {"english": {"on": true}}} and each paragraph of a chapter
   carries its English source. This module then shows:

     - the English face of the paragraph's panel (core/panel.js): the lead section, under the button "English"
       (lang_en), with the paragraph's English run through the bookText place (where "en"), so that
       features/sentences.js can mark and light its sentences;
     - on a screen wide enough, when the reader chooses it, each paragraph's English beside it (where "side");
       the choice "English beside the text" sits in the settings of the chapter list and is kept on the device;
     - the English title under each chapter's title, in the chapter list and at the head of a chapter;
     - the hint "Tap a sentence to see its English and leave a comment.", which also names selecting and Pick
       words (hint_english).

   When the setting is off, none of these shows, and the panel has the comment box alone. The variant "en" makes
   the page fetch a chapter kept on the device again when English is switched on or off, as the server's ETag
   ("<version>.en") does. */

import { feature, panelSection, titleLine, settingsItem } from "../core/ext.js";
import { h, bookHtml, applyMarks, decorateText } from "../core/dom.js";
import { t } from "../core/words.js";
import { store } from "../core/state.js";
import { K } from "../core/store.js";
import { setBeside } from "../core/panel.js";

feature({ name: "english", variant: "en" });

panelSection({
  name: "english",
  feature: "english",
  order: 10,
  lead: true,
  label: "lang_en",
  hint: "hint_english",
  render(ctx) {
    if (!ctx.p.en) return null;
    if (ctx.beside) {
      const side = h("div", { class: "en side-en", lang: "en" }, bookHtml(ctx.p.en));
      applyMarks(side, ctx);
      decorateText(side, ctx, "side");
      return side;
    }
    const text = h("div", { class: "en", lang: "en" }, bookHtml(ctx.p.en));
    applyMarks(text, ctx);
    decorateText(text, ctx, "en");
    return h("section", { class: "en-block" }, h("p", { class: "label", text: t("english") }), text);
  },
});

titleLine({
  name: "english",
  feature: "english",
  order: 10,
  render(ctx) {
    if (!ctx.chapter.title_en) return null;
    return h(ctx.where === "head" ? "p" : "span", { class: "ch-en", lang: "en", text: ctx.chapter.title_en });
  },
});

/* "English beside the text": a switch in the settings of the chapter list. app.css shows it only where the screen
   is wide enough for the Thai, the English and the panel (html.wide, core/panel.js). */
settingsItem({
  name: "english-beside",
  feature: "english",
  order: 20,
  render(ctx) {
    if (ctx.screen !== "home") return null;
    const b = h("button", { type: "button", class: "tool-btn wide-only", id: "beside-btn", text: t("english_beside"),
      "aria-pressed": String(store.get(K.side) === true) });
    b.addEventListener("click", () => {
      const on = store.get(K.side) !== true;
      setBeside(on);
      b.setAttribute("aria-pressed", String(on));
    });
    return b;
  },
});

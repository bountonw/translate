/* Proofreading site: the English feature's part of the page (web/features/english.js).

   The server's feature server/features/english.py has one setting, english.on. When it is on for a
   reader, GET /api/me says {"features": {"english": {"on": true}}} and each paragraph of a chapter
   carries its English source. This module then shows:

     - a panel in each paragraph's drawer with the paragraph's English, above the reader's comments, run
       through the bookText place (where "en"), so that features/sentences.js can mark its sentences;
     - the English title under each chapter's title, in the chapter list and at the head of a chapter;
     - the hint "Tap a paragraph to see the English and leave a comment." (hint_english).

   When the setting is off, none of these shows. The variant "en" makes the page fetch a chapter kept
   on the device again when English is switched on or off, as the server's ETag ("<version>.en") does. */

import { feature, drawerPanel, titleLine } from "../core/ext.js";
import { h, bookHtml, applyMarks, decorateText } from "../core/dom.js";
import { t } from "../core/words.js";

feature({ name: "english", variant: "en" });

drawerPanel({
  name: "english",
  feature: "english",
  order: 10,
  hint: "hint_english",
  render(ctx) {
    if (!ctx.p.en) return null;
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

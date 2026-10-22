/* Proofreading site: the reader's page (web/app.js), its entry point.

   Shows the chapters a reader may open, the chapter text, and the reader's own comments. The page's
   code is a set of ES modules loaded without a build step:

     core/      main.js (the start), state.js, store.js, words.js, languages.js, net.js, outbox.js,
                model.js, refusals.js, ext.js (the places where features plug in), dom.js, screens.js,
                home.js, chapter.js, para.js, notes.js
     features/  one module per feature: english.js

   This file stays a plain script, so a page saved on the device by an older version can still run
   it; it loads core/main.js and starts it. If that fails, as on a first visit without a connection,
   it shows the general error notice in the reader's language. EXTENDING.md, "The page side", says
   how the modules fit together and how a feature is added. */
(function () {
  "use strict";

  function failed(err) {
    console.error(err);
    var text = "Something went wrong. Please reload the page.";
    try {
      var words = JSON.parse(localStorage.getItem("rv.strings") || "null");
      var lang = JSON.parse(localStorage.getItem("rv.lang") || "null") || "th";
      var s = words && words.error_generic;
      if (s && (s[lang] || s.en)) text = s[lang] || s.en;
    } catch (e) { /* the English above stands */ }
    var n = document.getElementById("notice");
    if (n) { n.textContent = text; n.hidden = false; }
  }

  import("./core/main.js").then(function (m) { m.boot(); }).catch(failed);
})();

/* Probe for tests/admin_browser.py: drives every control of every section of the admin page in headless Firefox
   and logs "P ok ...", "P FAIL ...", "P TIME ..." and "P ROUTES ..." lines, ending with "P DONE".
   It is a classic script loaded before admin.js, so it sees every request the page makes.
   Query: mode (main, badkey, nokey, live, onceused), commit (main's commit), total (readers), ids (comment numbers),
   link (a reader's link), exports (the export folder), data (the dev data folder), home (the HOME of the run).
   tests/admin_browser.py signs Anan Chaiyo in with LINE on three browsers, Somchai Jaidee with an email code and the
   last reader of its file (query: last) with LINE through the link, and
   makes three requests to read through the general link of Pastors (kanya@example.org, pim@example.org, and LINE
   tester 3 with LINE) before the probe starts. */
(function () {
  "use strict";
  const params = new URLSearchParams(location.search);
  const MODE = params.get("mode") || "main";
  const log = m => console.log("P " + m);
  let fails = 0;
  const check = (cond, what) => {
    if (cond) log("ok " + what);
    else {
      fails++;
      log("FAIL " + what);
    }
  };
  const errors = [];
  window.addEventListener("error", e => errors.push("error: " + e.message + " @" + (e.filename || "") + ":" + e.lineno));
  window.addEventListener("unhandledrejection", e => errors.push("rejection: " + e.reason));
  document.addEventListener("securitypolicyviolation", e => errors.push("CSP: " + e.violatedDirective + " " + e.blockedURI));
  const hashAtStart = location.hash;

  const used = {};
  const calls = {};
  const bodies = {};     // the body of the last request of each route
  const urls = [];
  const times = [];
  const real = window.fetch.bind(window);
  window.fetch = (u, o) => {
    const m = /\/local\/([a-z-]+)/.exec(String(u));
    const route = m ? ((o && o.method) || "GET") + " " + m[1] : String(u);
    if (m) {
      urls.push(String(u));
      used[route] = true;
      calls[route] = (calls[route] || 0) + 1;
      bodies[route] = o && o.body;
    }
    const t0 = performance.now();
    return real(u, o).then(r => {
      times.push([route, performance.now() - t0]);
      return r;
    });
  };
  // How many requests a route got while fn ran.
  async function counted(route, fn) {
    const before = calls[route] || 0;
    const out = await fn();
    return [out, (calls[route] || 0) - before];
  }

  const sleep = ms => new Promise(r => setTimeout(r, ms));
  async function until(fn, ms) {
    const t0 = Date.now();
    while (Date.now() - t0 < (ms || 10000)) {
      let v = null;
      try { v = fn(); } catch (e) { v = null; }
      if (v) return v;
      await sleep(40);
    }
    return null;
  }
  const $ = s => document.querySelector(s);
  const $$ = s => Array.from(document.querySelectorAll(s));
  const text = s => { const el = $(s); return el ? el.textContent : ""; };
  function set(id, value) {
    const el = document.getElementById(id);
    el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }
  function tick(selector, on) {
    const el = $(selector);
    if (!el) return false;
    if (el.checked !== on) el.click();
    return true;
  }
  function file(id, name, body, type) {
    const dt = new DataTransfer();
    dt.items.add(new File([body], name, { type: type }));
    document.getElementById(id).files = dt.files;
  }
  async function go(hash, ready) {
    location.hash = hash;
    return until(ready, 10000);
  }
  // Click a button and return the answer box's text once the answer is in. With ask, the confirmation must
  // open and hold that text; without, it must not open.
  async function press(b, boxId, ask, name) {
    const box = document.getElementById(boxId);
    box.textContent = "";
    if (!b || b.disabled) {
      check(false, "button " + name + " can be pressed");
      return "";
    }
    b.click();
    const dlg = document.getElementById("ask");
    if (ask) {
      const opened = await until(() => dlg.open, 5000);
      const said = dlg.textContent.replace(/\s+/g, " ");
      check(opened && said.indexOf(ask) >= 0, name + " asks: " + ask + (opened ? "" : " (it did not ask)") +
        (opened && said.indexOf(ask) < 0 ? " (it asked: " + said.slice(0, 300) + ")" : ""));
      document.getElementById("ask-go").click();
    } else {
      await sleep(80);
      check(!dlg.open, name + " acts without asking" + (dlg.open ? " (it asked: " + dlg.textContent.replace(/\s+/g, " ").slice(0, 200) + ")" : ""));
      if (dlg.open) document.getElementById("ask-go").click();
    }
    await until(() => box.querySelector(".reply") && !document.documentElement.classList.contains("running"), 30000);
    await sleep(60);
    return box.textContent;
  }
  function run(buttonId, boxId, ask) {
    return press(document.getElementById(buttonId), boxId, ask, buttonId);
  }
  // One request to a local route without the page's controls, with the key the page keeps: the answer's JSON.
  async function local(route, body) {
    let key = "";
    try { key = sessionStorage.getItem("review-admin.key") || ""; } catch (e) { key = ""; }
    const res = await fetch("/local/" + route, { method: "POST", cache: "no-store", credentials: "same-origin",
      headers: { "X-Admin-Key": key, "Content-Type": "application/json" }, body: JSON.stringify(body) });
    return res.json();
  }
  // Today in Thailand (UTC+7), as a date field gives it.
  function thaiDay(offset) {
    return new Date(Date.now() + 7 * 3600 * 1000 + (offset || 0) * 86400 * 1000).toISOString().slice(0, 10);
  }

  function none() {
    tick("#chapters-all-SC", true);
    tick("#chapters-all-SC", false);
  }

  async function chapters() {
    const ready = await until(() => $$("#chapters-SC tbody tr").length >= 13);
    log("TIME first table drawn " + Math.round(performance.now()) + " ms after the page began to load");
    const nav = performance.getEntriesByType("navigation")[0];
    log("TIME page " + (nav ? Math.round(nav.responseEnd) + " ms to receive, DOMContentLoaded at " +
      Math.round(nav.domContentLoadedEventEnd) + " ms" : "not measured") + "; " +
      performance.getEntriesByType("resource").map(e => e.name.replace(/^.*\//, "").replace(/\?.*$/, "") + " " +
        Math.round(e.startTime) + "+" + Math.round(e.duration)).join(", "));
    check(ready, "the chapter table of SC is drawn with 13 rows");
    check(text("#tip-SC").indexOf("main is at " + params.get("commit")) === 0, "the commit publish reads is shown: " + text("#tip-SC"));
    const r1 = $("#chapters-SC tr[data-chapter='SC01']");
    check(r1 && r1.className === "published", "SC01 is published");
    const r4 = $("#chapters-SC tr[data-chapter='SC04']");
    check(r4 && r4.className === "never" && r4.textContent.indexOf("not published") >= 0, "SC04 is not published");
    check(r4 && r4.textContent.indexOf("SC04_th.typ") >= 0, "a chapter never published names its file in the book's language");
    const cells = r1 ? Array.from(r1.cells).map(c => c.textContent) : [];
    check(/^[0-9a-f]{7,}$/.test(cells[5] || "") && cells[6] === cells[5], "SC01 shows the commit it came from: " + cells[5]);
    check(/^[0-9a-f]{7,12}-[0-9a-f]+$/.test(cells[4] || ""), "SC01 shows its version: " + cells[4]);
    check(r1 && r1.querySelector("span[lang='th']") !== null, "SC01 shows its title in the book's language, marked as Thai");
    tick("#chapters-SC input[data-chapter='SC04']", true);
    tick("#chapters-SC input[data-chapter='SC05']", true);
    let out = await run("publish-SC", "chapters-answer-SC", "Publish 2 chapters of SC: SC04-05?");
    check($("#ask-more").textContent.indexOf("main at " + params.get("commit")) >= 0, "the question names the commit");
    check(out.indexOf("Reading main at " + params.get("commit")) >= 0 && out.indexOf("SC04: published") >= 0 &&
      out.indexOf("SC05: published") >= 0 && out.indexOf("SC04-05 have a new version.") >= 0,
      "publish answers with the commit it read, each chapter and the sentence of what changed");
    await until(() => ($("#chapters-SC tr[data-chapter='SC05']") || {}).className === "published");
    check(($("#chapters-SC tr[data-chapter='SC04']") || {}).className === "published", "the table shows SC04 published");
    tick("#chapters-SC input[data-chapter='SC04']", false);
    out = await run("withdraw-SC", "chapters-answer-SC", "Withdraw 1 chapter of SC: SC05?");
    check(out.indexOf("SC05: withdrawn") >= 0 && out.indexOf("SC05 is withdrawn: readers no longer see it") >= 0,
      "withdraw answers: SC05 withdrawn");
    await until(() => ($("#chapters-SC tr[data-chapter='SC05']") || {}).className === "withdrawn");
    check(($("#chapters-SC tr[data-chapter='SC05']") || {}).className === "withdrawn", "the table shows SC05 withdrawn");
    none();
    tick("#chapters-SC input[data-chapter='SC01']", true);
    out = await run("align-SC", "chapters-answer-SC", "");
    check(out.indexOf("The packet for SC01 is written: " + params.get("home") + "/claude-sandbox/review-align/SC01-packet.json") >= 0,
      "the alignment packet goes to the default file: " + out.slice(-200));
    set("align-out-SC", params.get("home") + "/probe-packet.json");
    out = await run("align-SC", "chapters-answer-SC", "");
    check(out.indexOf("The packet for SC01 is written: " + params.get("home") + "/probe-packet.json") >= 0,
      "align-packet --out writes the file named");
    set("align-out-SC", "");
    set("ref-SC", "nosuch");
    $("#readref-SC").click();
    await until(() => text("#tip-SC").indexOf("nosuch") >= 0);
    check(text("#tip-SC").indexOf("has no nosuch") >= 0, "a ref that does not exist is named plainly");
    set("ref-SC", "main");
    $("#readref-SC").click();
    await until(() => text("#tip-SC").indexOf("main is at") === 0);
    out = await run("withdraw-all-SC", "chapters-answer-SC", "Withdraw the whole book SC, its 4 published chapters: SC01-04?");
    check(out.indexOf("SC01: withdrawn") >= 0 && out.indexOf("SC04: withdrawn") >= 0, "the whole book is withdrawn");
    none();
    ["SC01", "SC02", "SC03"].forEach(id => tick("#chapters-SC input[data-chapter='" + id + "']", true));
    out = await run("publish-SC", "chapters-answer-SC", "Publish 3 chapters of SC: SC01-03?");
    check(out.indexOf("SC01-03 are published again.") >= 0 || out.indexOf("SC03: published") >= 0, "SC01-03 are published again: " + out.slice(-120));
    none();
  }

  const names = () => $$("#r-table tbody td.name").map(td => td.textContent).sort().join(", ");
  async function clearReaders(total) {
    $("#r-clear").click();
    await until(() => text("#r-count") === total + " readers.");
  }
  function pick(list) {
    tick("#r-all", true);
    tick("#r-all", false);
    list.forEach(n => tick("#r-table input[data-reader='" + n + "']", true));
  }

  async function readers() {
    const t0 = performance.now();
    const total = Number(params.get("total"));
    await go("#readers", () => text("#r-count") === total + " readers." && $$("#r-table tbody tr").length === total);
    log("TIME " + total + " readers listed in " + Math.round(performance.now() - t0) + " ms");
    check(text("#r-count") === total + " readers.", "the reader count is shown: " + text("#r-count"));
    await until(() => !$("#waiting").hidden);
    check(!$("#waiting").hidden && text("#waiting") === "1 device waiting", "the menu says a device waits: " + text("#waiting"));
    const boon = $("#r-table [data-flag='Boon Mee']");
    check(boon && boon.textContent === "3 devices, 1 waiting" && boon.className === "flag",
      "the link on a third device is flagged: " + (boon ? boon.textContent : "no flag"));
    check($$("#r-table .flag").length === 1, "only that link is flagged");
    // How each reader signs in (61-admin-contract.md 1.A), and the filter of readers --identity.
    const signin = n => text("#r-table [data-signin-of='" + n + "']");
    check(signin("Anan Chaiyo") === "LINE (LINE tester 1); 3 browsers signed in", "Anan Chaiyo signs in with LINE on 3 browsers: " + signin("Anan Chaiyo"));
    check(signin("Somchai Jaidee") === "somchai@example.org; 1 browser signed in", "Somchai Jaidee signs in with an address: " + signin("Somchai Jaidee"));
    check(signin("Mali Srisuk") === "not yet", "Mali Srisuk has not signed in: " + signin("Mali Srisuk"));
    const last = params.get("last");
    for (const [kind, want] of [["line", "Anan Chaiyo, " + last], ["email", "Somchai Jaidee"],
      ["any", "Anan Chaiyo, " + last + ", Somchai Jaidee"]]) {
      set("r-identity", kind);
      await until(() => text("#r-count").indexOf(" of ") > 0 && names() === want);
      check(names() === want, "readers --identity " + kind + ": " + names());
    }
    set("r-identity", "none");
    await until(() => text("#r-count") === (total - 3) + " of " + total + " readers.");
    check(text("#r-count") === (total - 3) + " of " + total + " readers.", "readers --identity none: " + text("#r-count"));
    await clearReaders(total);
    set("r-name", "chai");
    await until(() => text("#r-count").indexOf(" of ") > 0);
    check(text("#r-count") === "2 of " + total + " readers." && names() === "Anan Chaiyo, Somchai Jaidee",
      "a part of a name finds its readers: " + names());
    await clearReaders(total);
    set("r-group", "Pastors");
    await until(() => text("#r-count").indexOf(" of ") > 0);
    check(names() === "Anan Chaiyo, Somchai Jaidee", "the group filter: " + names());
    await clearReaders(total);
    set("r-inactive", "0");
    await until(() => text("#r-count").indexOf(" of ") > 0);
    check(text("#r-count") === (total - 3) + " of " + total + " readers.", "never active readers: " + text("#r-count"));
    await clearReaders(total);
    set("r-book", "SC");
    await until(() => text("#r-count").indexOf(" of ") > 0);
    check(/^\d+ of /.test(text("#r-count")), "the book filter: " + text("#r-count"));
    await clearReaders(total);
    tick("#r-revoked", true);
    await until(() => text("#r-count").indexOf(" of ") > 0);
    check(text("#r-count") === "0 of " + total + " readers.", "no link is stopped yet");
    await clearReaders(total);
    tick("#r-devices", true);
    await until(() => text("#r-count").indexOf(" of ") > 0);
    check(names() === "Boon Mee", "the filter of links on more than two devices (readers --devices): " + names());
    await clearReaders(total);
    set("r-link", params.get("link"));
    await until(() => text("#r-count").indexOf(" of ") > 0);
    check(names() === "Mali Srisuk", "a link finds its reader: " + names());
    await clearReaders(total);

    // The readers ticked, all in one request.
    pick(["Anan Chaiyo", "Mali Srisuk"]);
    check(text("#r-selected").indexOf("2 readers selected") === 0, "the selection is counted: " + text("#r-selected"));
    set("r-spec", "SC03");
    let res = await counted("POST open", () => run("r-open", "r-answer", "Open SC03 to 2 readers?"));
    let out = res[0];
    check(res[1] === 1, "Open chapters sends one request for two readers");
    check(out.indexOf("SC03 is now open to Anan Chaiyo and Mali Srisuk.") >= 0 &&
      out.indexOf("Mali Srisuk: active; own: SC01, SC03") >= 0, "open reaches both readers: " + out.slice(-160));
    res = await counted("POST close", () => run("r-close", "r-answer", "Close SC03 for 2 readers?"));
    out = res[0];
    check(res[1] === 1 && out.indexOf("SC03 is no longer among the own chapters of Anan Chaiyo and Mali Srisuk.") >= 0,
      "close reaches both readers in one request: " + out.slice(-160));
    out = await run("r-english-off", "r-answer", "Turn English off for 2 readers?");
    check(out.indexOf("Anan Chaiyo: English stays on through a group of theirs") >= 0 &&
      out.indexOf("Nothing changed: English is already off for Anan Chaiyo and Mali Srisuk, as their own setting.") >= 0,
      "English off names the group's English, and says that nothing changed: " + out.slice(0, 220));
    check($("#r-answer a.next[href='#groups']") !== null, "the answer offers the groups, as the line names review.py groups");
    out = await run("r-english-on", "r-answer", "Turn English on for 2 readers?");
    check(out.indexOf("English is now on for Anan Chaiyo and Mali Srisuk, as their own setting.") >= 0, "English on");
    await until(() => document.querySelector("#r-feature option"));
    set("r-feature", "english");
    out = await run("r-feature-off", "r-answer", "Turn english off for 2 readers?");
    check(out.indexOf("english.on is now off for Anan Chaiyo and Mali Srisuk") >= 0, "a feature off: " + out.slice(-120));
    out = await run("r-feature-on", "r-answer", "Turn english on for 2 readers?");
    check(out.indexOf("english.on is now on for Anan Chaiyo and Mali Srisuk") >= 0, "a feature on");
    res = await counted("POST revoke", () => run("r-revoke", "r-answer", "Stop the links of 2 readers?"));
    out = res[0];
    check(res[1] === 1 && out.indexOf("Anan Chaiyo and Mali Srisuk are stopped: the links, LINE and email open nothing now") >= 0,
      "revoke in one request: " + out.slice(-160));
    await until(() => $$("#r-table tr.revoked").length === 2);
    check($$("#r-table tr.revoked").length === 2, "the list shows 2 stopped links");
    out = await run("r-restore", "r-answer", "Restore the links of 2 readers?");
    check(out.indexOf("The link of Mali Srisuk works again.") >= 0 && out.indexOf("Anan Chaiyo can read again: ") >= 0 &&
      out.indexOf("Anan Chaiyo signs in with LINE or email.") >= 0, "restore: " + out.slice(-200));
    res = await counted("POST relink", () => run("r-relink", "r-answer", "Give 2 readers new links?"));
    out = res[0];
    const rows = $$("#r-answer .linkrow");
    check(res[1] === 1, "New links sends one request for two readers");
    check(rows.length === 2 && rows.every(r => r.querySelector("input.link").value.indexOf(params.get("site") + "/#k=") === 0 &&
      r.querySelector("button.copy")), "two new links are shown, each in its own row with a Copy button");
    check($$("#r-answer pre").every(p => p.textContent.indexOf("#k=") < 0), "the links are not repeated in the lines");
    pick(["Mali Srisuk"]);
    out = await run("r-relink", "r-answer", "Give Mali Srisuk a new link?");
    const one = $("#r-answer .linkrow input.link");
    check(one && one.value.indexOf(params.get("site") + "/#k=") === 0 && out.indexOf("shown only this once") >= 0,
      "one new link is shown once, with a Copy button");
    $("#r-answer button.copy").click();
    await until(() => text("#r-answer .copied"));
    log("note Copy answered: " + text("#r-answer .copied"));
    check(text("#r-answer .copied") !== "", "Copy says what it did");
    out = await run("r-open", "r-answer", "");
    check(out.indexOf("SC03 is now open to Mali Srisuk.") >= 0, "one reader is changed without a question");
    tick("#r-all", false);

    // The stop switch on a reader's row.
    out = await press($("#r-table button[data-switch='Mali Srisuk']"), "r-answer", "", "the stop switch of Mali Srisuk");
    check(out.indexOf("Mali Srisuk is stopped: the link, LINE and email open nothing now") >= 0, "the row's switch stops one link: " + out.slice(-120));
    await until(() => ($("#r-table tr[data-reader='Mali Srisuk']") || {}).className === "revoked");
    const sw = $("#r-table button[data-switch='Mali Srisuk']");
    check(sw && sw.textContent === "Restore", "the switch now offers Restore");
    // A new link of a stopped reader says, beside the link, that it stays stopped (46 ADV3-06).
    pick(["Mali Srisuk"]);
    out = await run("r-relink", "r-answer", "Give Mali Srisuk a new link?");
    check(text("#r-answer .linkrow .linknote").indexOf("The link of Mali Srisuk stays stopped, so the new link opens nothing " +
      "until: review.py restore 'Mali Srisuk'") === 0, "a stopped reader's new link says that it stays stopped: " +
      text("#r-answer .linkrow"));
    tick("#r-all", false);
    await until(() => $("#r-table button[data-switch='Mali Srisuk']"));
    out = await press($("#r-table button[data-switch='Mali Srisuk']"), "r-answer", "", "the restore switch of Mali Srisuk");
    check(out.indexOf("The link of Mali Srisuk works again.") >= 0, "the row's switch restores the link");

    // The switch Link signs in on a reader's row, and for the readers ticked (link-signs-in NAME ... on|off).
    out = await press($("#r-table button[data-link-signs-in='Mali Srisuk']"), "r-answer", "", "the Link signs in switch of Mali Srisuk");
    check(out.indexOf("Link signs in is now on for Mali Srisuk: the link signs in by itself, with the two-device lock.") >= 0,
      "the row's switch turns Link signs in on: " + out.slice(-160));
    await until(() => signin("Mali Srisuk") === "Link signs in");
    check(signin("Mali Srisuk") === "Link signs in" && text("#r-table button[data-link-signs-in='Mali Srisuk']") === "Link signs in: switch off",
      "the row says Link signs in and offers to switch it off");
    pick(["Mali Srisuk", "Boon Mee"]);
    res = await counted("POST link-signs-in", () => run("r-lsi-off", "r-answer", "Switch Link signs in off for 2 readers?"));
    out = res[0];
    check(res[1] === 1 && out.indexOf("Mali Srisuk has not signed in with LINE or email yet, so until then the link still signs in by itself.") >= 0 &&
      out.indexOf("Link signs in is now off for Mali Srisuk: Mali Srisuk signs in with LINE or email; it was already off for Boon Mee.") >= 0,
      "Link signs in off for the readers ticked, in one request: " + out.slice(-260));
    out = await run("r-lsi-on", "r-answer", "Switch Link signs in on for 2 readers?");
    check(out.indexOf("Link signs in is now on for Boon Mee and Mali Srisuk: the links sign in by themselves, with the two-device lock.") >= 0,
      "Link signs in on for the readers ticked: " + out.slice(-160));
    out = await run("r-lsi-off", "r-answer", "Switch Link signs in off for 2 readers?");
    check(out.indexOf("Link signs in is now off for Boon Mee and Mali Srisuk: they sign in with LINE or email.") >= 0,
      "Link signs in off again: " + out.slice(-160));
    tick("#r-all", false);

    // Devices: the one waiting, approve, the devices of one reader, remove and approve several, earlier links.
    await until(() => $$("#v-table tbody tr").length === 1);
    check(text("#v-count") === "1 device waiting for your approval." && text("#v-table").indexOf("Boon Mee") >= 0,
      "the device waiting is listed: " + text("#v-count"));
    const waitingId = ($("#v-table tbody tr") || { getAttribute: () => "" }).getAttribute("data-device");
    out = await press($("#v-table button[data-approve='" + waitingId + "']"), "v-answer", "", "Approve on the device's row");
    check(out.indexOf("Device " + waitingId + " is approved: the link of Boon Mee works on it.") >= 0, "approve one device: " + out.slice(-120));
    await until(() => $("#waiting").hidden);
    check($("#waiting").hidden, "the menu no longer says a device waits");
    check(text("#v-count") === "No device is waiting for your approval.", "no device waits now");
    $("#r-table button[data-devices='Boon Mee']").click();
    await until(() => text("#v-count") === "3 devices of Boon Mee.");
    check(text("#v-count") === "3 devices of Boon Mee." && $("#v-name").value === "Boon Mee", "the row's Devices button lists the reader's devices");
    const ids = $$("#v-table tbody tr").map(r => r.getAttribute("data-device"));
    tick("#v-table input[data-device='" + ids[0] + "']", true);
    tick("#v-table input[data-device='" + ids[1] + "']", true);
    res = await counted("POST device", () => run("v-remove", "v-answer", "Remove 2 devices?"));
    out = res[0];
    check(res[1] === 1 && out.indexOf("Devices " + ids[0] + " and " + ids[1] + " are removed: the link of Boon Mee no longer works on them.") >= 0,
      "remove two devices in one request: " + out.slice(-140));
    await until(() => $$("#v-table tr.removed").length === 2);
    tick("#v-select-all", true);
    out = await run("v-approve", "v-answer", "Approve 3 devices?");
    check(out.indexOf("Devices " + ids[0] + " and " + ids[1] + " are approved: the link of Boon Mee works on them; device " +
      ids[2] + " was already approved.") >= 0, "approve the devices ticked, naming the one already approved: " + out.slice(-160));
    await until(() => $("#v-table button[data-remove='" + ids[2] + "']"));
    out = await press($("#v-table button[data-remove='" + ids[2] + "']"), "v-answer", "", "Remove on a device's row");
    check(out.indexOf("Device " + ids[2] + " is removed: the link of Boon Mee no longer works on it.") >= 0, "remove one device from its row");
    await until(() => $("#v-table button[data-approve='" + ids[2] + "']"));
    out = await press($("#v-table button[data-approve='" + ids[2] + "']"), "v-answer", "", "Approve on the row of a removed device");
    check(out.indexOf("Device " + ids[2] + " is approved: the link of Boon Mee works on it.") >= 0, "a removed device is approved again");
    pick(["Boon Mee"]);
    out = await run("r-relink", "r-answer", "Give Boon Mee a new link?");
    tick("#r-all", false);
    $("#v-show").click();
    await until(() => text("#v-count").indexOf("No device has opened the link of Boon Mee yet.") === 0);
    check(text("#v-count") === "No device has opened the link of Boon Mee yet.", "a new link starts with no device");
    tick("#v-all", true);
    await until(() => text("#v-count") === "3 devices of Boon Mee.");
    check(text("#v-count") === "3 devices of Boon Mee." && $$("#v-table tbody tr").every(r => r.textContent.indexOf("an earlier link") >= 0),
      "devices --all lists the devices of the earlier link");
    tick("#v-all", false);
    $("#v-waiting").click();
    await until(() => text("#v-count") === "No device is waiting for your approval.");

    // A new link that also removes the reader's LINE accounts and addresses (relink NAME --unbind).
    pick(["Somchai Jaidee"]);
    tick("#r-unbind", true);
    out = await run("r-relink", "r-answer", "Give Somchai Jaidee a new link, and remove the LINE accounts and addresses of Somchai Jaidee?");
    check(out.indexOf("Somchai Jaidee has a new link; the old link no longer works, somchai@example.org no longer signs in, and 1 browser is signed out.") >= 0 &&
      JSON.parse(bodies["POST relink"] || "{}").unbind === true, "relink --unbind removes the address and signs the browser out: " + out.slice(-200));
    check(!$("#r-unbind").checked, "the unbind box is cleared after the new link");
    // Somchai Jaidee signed in before, so the row does not say "not yet" (70-verify.md item 6).
    await until(() => signin("Somchai Jaidee") === "none now; the next sign-in is through the link");
    check(signin("Somchai Jaidee") === "none now; the next sign-in is through the link",
      "the row shows no way of signing in now: " + signin("Somchai Jaidee"));
    tick("#r-all", false);

    // Sign-in and browsers: a row's Sign-in button, an address added and removed, browsers signed out.
    $("#r-table button[data-signin='Anan Chaiyo']").click();
    await until(() => text("#a-count") === "Anan Chaiyo: 1 way of signing in, 3 browsers signed in.");
    check(text("#a-count") === "Anan Chaiyo: 1 way of signing in, 3 browsers signed in." && $("#a-name").value === "Anan Chaiyo",
      "the row's Sign-in button shows the reader's sign-in: " + text("#a-count"));
    check($$("#a-ids tbody tr").length === 1 && text("#a-ids").indexOf("LINE (LINE tester 1)") >= 0, "the LINE account is listed");
    // The hint names the site's own auth.session_days (66-adversarial.md ADV4-08).
    check(!$("#a-hint").hidden && text("#a-hint").indexOf("stays signed in on each browser for 30 days after the last visit") >= 0,
      "the hint names the days of the site: " + text("#a-hint").slice(0, 160));
    check($$("#a-sessions tbody tr").length === 3 && $$("#a-sessions tbody tr").every(r =>
      r.textContent.indexOf("iPhone, Safari") >= 0 && r.textContent.indexOf("LINE as LINE tester 1") >= 0), "the three browsers are listed");
    set("a-address", "anan@example.org");
    out = await run("a-add", "a-answer", "");
    check(out.indexOf("Anan Chaiyo can now sign in with a code sent to anan@example.org.") >= 0, "identity add: " + out.slice(-120));
    await until(() => $$("#a-ids tbody tr").length === 2);
    const mailRow = $$("#a-ids tbody tr").filter(r => r.textContent.indexOf("anan@example.org") >= 0)[0];
    out = await press(mailRow && mailRow.querySelector("button[data-unbind]"), "a-answer", "Remove anan@example.org from Anan Chaiyo?", "Remove on an address's row");
    check(out.indexOf("anan@example.org no longer signs in to Anan Chaiyo, and no browser was signed in.") >= 0, "unbind: " + out.slice(-120));
    await until(() => $$("#a-ids tbody tr").length === 1);
    const sids = $$("#a-sessions tbody tr").map(r => r.getAttribute("data-session"));
    out = await press($("#a-sessions button[data-end='" + sids[0] + "']"), "a-answer", "", "Sign out on a browser's row");
    check(out.indexOf("Browser " + sids[0] + " of Anan Chaiyo (iPhone, Safari) is signed out.") >= 0, "session end: " + out.slice(-120));
    await until(() => $$("#a-sessions tbody tr").length === 2);
    tick("#a-select-all", true);
    res = await counted("POST session", () => run("a-end", "a-answer", "Sign out 2 browsers?"));
    out = res[0];
    check(res[1] === 1 && out.indexOf("Browsers " + sids[1] + " and " + sids[2] + " of Anan Chaiyo are signed out.") >= 0,
      "the browsers ticked are signed out in one request: " + out.slice(-160));
    await until(() => text("#a-count") === "Anan Chaiyo: 1 way of signing in, 0 browsers signed in.");
    tick("#a-all", true);
    await until(() => $$("#a-sessions tbody tr").length === 3);
    check($$("#a-sessions tbody tr.off").length === 3 && text("#a-sessions").indexOf("signed out by you") >= 0,
      "sessions --all lists the browsers signed out");
    tick("#a-all", false);
    out = await run("a-signout", "a-answer", "Sign Anan Chaiyo out on every browser (0 browsers signed in now)?");
    check(out.indexOf("Nothing changed: Anan Chaiyo is signed in on no browser.") >= 0, "signout: " + out.slice(-120));
    // The last way of signing in removed. Anan Chaiyo's link was renewed above and is unused, so it still signs in by
    // itself; the last reader of the file used the link, so the answer offers a new link, shown once.
    out = await press($("#a-ids button[data-unbind]"), "a-answer", "Remove LINE (LINE tester 1) from Anan Chaiyo?", "Remove the LINE account");
    check(out.indexOf("Anan Chaiyo has no LINE account or address left, and the link of Anan Chaiyo still signs in by itself.") >= 0 &&
      out.indexOf("LINE (LINE tester 1) no longer signs in to Anan Chaiyo, and no browser was signed in.") >= 0, "unbind the last way: " + out.slice(-260));
    check(!$("#a-answer .steps button"), "nothing more is offered");
    set("a-name", last);
    $("#a-show").click();
    await until(() => text("#a-count") === last + ": 1 way of signing in, 1 browser signed in.");
    check(text("#a-count") === last + ": 1 way of signing in, 1 browser signed in.", "Show this reader's: " + text("#a-count"));
    out = await press($("#a-ids button[data-unbind]"), "a-answer", "Remove LINE (LINE tester 2) from " + last + "?", "Remove the LINE account of " + last);
    check(out.indexOf(last + " has no LINE account or address left and can get in again only through a new link: review.py relink '" + last + "'") >= 0 &&
      out.indexOf("LINE (LINE tester 2) no longer signs in to " + last + ", and 1 browser is signed out.") >= 0, "unbind the last way of " + last + ": " + out.slice(-260));
    const again = $$("#a-answer .steps button").filter(b => b.textContent === "Give " + last + " a new link")[0];
    check(!!again, "the answer offers a new link");
    if (again) {
      again.click();
      const opened = await until(() => $("#ask").open, 5000);
      check(opened && text("#ask-text") === "Give " + last + " a new link?", "the offered new link asks first: " + text("#ask-text"));
      $("#ask-go").click();
      await until(() => $("#a-answer .linkrow input.link"));
      const fresh = $("#a-answer .linkrow input.link");
      check(fresh && fresh.value.indexOf(params.get("site") + "/#k=") === 0 && text("#a-answer").indexOf(last + " has a new link;") >= 0,
        "the offered new link is shown once, with a Copy button");
      check($$("#a-answer pre").every(x => x.textContent.indexOf("#k=") < 0), "the new link is not repeated in the lines");
    }
    $("#a-every").click();
    await until(() => text("#a-count").indexOf("Every reader: ") === 0);
    check(text("#a-count") === "Every reader: 0 ways of signing in, 0 browsers signed in.", "every reader's sign-in: " + text("#a-count"));

    // Deleting one reader's comments between two dates: the count first, one question, then the deletion.
    set("dc-name", "Boon Mee");
    set("dc-from", thaiDay(0));
    set("dc-to", thaiDay(0));
    res = await counted("POST delete-comments", () => run("dc-go", "dc-answer",
      "Delete the 2 comments that Boon Mee wrote from " + thaiDay(0) + " 00:00 to " + thaiDay(1) + " 00:00, Thailand time?"));
    out = res[0];
    check(res[1] === 2 && out.indexOf("2 comments that Boon Mee wrote from " + thaiDay(0) + " 00:00 to " + thaiDay(1) +
      " 00:00 Thailand time are deleted (SC01: 2); the next export names them.") >= 0, "delete-comments counts, asks once, deletes: " + out.slice(-200));
    const sentDelete = JSON.parse(bodies["POST delete-comments"] || "{}");
    check(sentDelete.yes === true && typeof sentDelete.upto === "number" && sentDelete.upto > 0,
      "the deletion sends the last comment the count found, so nothing written since is deleted (45 SEC3-8): " + bodies["POST delete-comments"]);
    out = await run("dc-go", "dc-answer", "");
    check(out.indexOf("Nothing was deleted: Boon Mee wrote no comment") >= 0, "a second time finds nothing and asks nothing");
    set("dc-from-time", "14:30");
    set("dc-to", thaiDay(-1));
    out = await run("dc-go", "dc-answer", "");
    check(out.indexOf("--from must come before --to.") >= 0 && $("#dc-answer .reply.bad"), "dates in the wrong order are refused: " + out.slice(-120));
    set("dc-from-time", "");

    // Inviting.
    set("i-name", "Probe Reader");
    set("i-grant", "SC01");
    tick("#i-groups input[data-group='Youth']", true);
    tick("#i-english", true);
    tick("#i-link-signs-in", true);
    out = await run("i-go", "i-answer", "");
    const link = $("#i-answer .linkrow input.link");
    check(link && link.value.indexOf(params.get("site") + "/#k=") === 0 && out.indexOf("Probe Reader can read SC01; groups Youth") >= 0 &&
      out.indexOf("Probe Reader is invited; the link signs in by itself and works on the first devices that open it.") >= 0,
      "invite --link-signs-in shows the new link once, with a Copy button: " + out.slice(-160));
    check(!$("#i-link-signs-in").checked, "the Link signs in box is cleared after the invite");
    await until(() => text("#r-count") === (total + 1) + " readers.");
    check(text("#r-count") === (total + 1) + " readers.", "the list counts the new reader");
    set("i-name", "Probe Reader");
    out = await run("i-go", "i-answer", "");
    check(out.indexOf("already exists") >= 0 && !$("#i-answer .linkrow"), "a second reader of that name is refused: " + out);
    file("m-file", "probe.csv", "name,groups,grants,english,email\nCsv One,Youth,,no,one@example.org\n" +
      "\"Csv, Two\",,SC01,yes,\nCsv Three,Pastors,SC02,no,\n", "text/csv");
    out = await run("m-go", "m-answer", "Invite 3 readers from probe.csv?");
    check(out.indexOf("The links are in " + params.get("data") + "/links-invite-") >= 0 && out.indexOf("3 readers invited.") >= 0,
      "invite from a file names the links file: " + out.slice(-160));
    check(out.indexOf("#k=") < 0 && !$("#m-answer .linkrow"), "invite from a file shows no link");
    await until(() => text("#r-count") === (total + 4) + " readers.");
    check(text("#r-count") === (total + 4) + " readers.", "the list counts the readers of the file");
  }

  async function groups() {
    const total = Number(params.get("total"));
    await go("#groups", () => text("#g-count") === "2 groups.");
    check(text("#g-count") === "2 groups.", "the groups are listed");
    set("g-new-name", "Probe");
    set("g-new-grant", "SC01");
    let out = await run("g-create", "g-new-answer", "");
    check(out.indexOf("Probe: on; reads SC01; English off; 0 members") >= 0 && out.indexOf("The group Probe is created and on") >= 0,
      "create a group");
    await until(() => !$("#g-panel").hidden && text("#g-title") === "Group Probe");
    check(text("#g-title") === "Group Probe", "the new group is open");
    set("g-find", "Reader 00");
    await until(() => $$("#g-found tbody tr").length === 9);
    check($$("#g-found tbody tr").length === 9, "readers are found by part of the name");
    tick("#g-found input[data-found='Reader 001']", true);
    tick("#g-found input[data-found='Reader 002']", true);
    out = await run("g-add", "g-answer", "Add 2 readers to the group Probe?");
    check(out.indexOf("2 readers added to Probe, which now has 2 members.") >= 0, "add the readers picked from the list");
    await until(() => $$("#g-members tbody tr").length === 2);
    check($$("#g-found input[data-found='Reader 001']").length === 0, "a member is no longer offered");
    $("#g-list-all").click();
    await until(() => $$("#g-found tbody tr").length > 9);
    check($$("#g-found tbody tr").length === total + 4 - 2, "every reader who is not a member can be listed");
    tick("#g-members input[data-member='Reader 002']", true);
    out = await run("g-take-out", "g-answer", "");
    check(out.indexOf("1 reader taken out of Probe, which now has 1 member.") >= 0, "take out one reader without a question");
    file("g-in-file", "add.csv", "name\nReader 003\nReader 004\n", "text/csv");
    out = await run("g-add-file", "g-answer", "Add the 2 readers of add.csv to the group Probe?");
    check(out.indexOf("2 readers added to Probe, which now has 3 members.") >= 0, "add readers from a file");
    file("g-out-file", "out.csv", "name,email\nReader 004,x@example.org\n", "text/csv");
    out = await run("g-take-out-file", "g-answer", "");
    check(out.indexOf("1 reader taken out of Probe, which now has 2 members.") >= 0, "take out readers from a file");

    // The two ways of giving a group chapters, each its own button, each asking once with the sentence.
    set("g-spec", "SC02");
    out = await run("g-open", "g-answer", "Open SC02 to the group Probe and its 2 members?");
    check(out.indexOf("Probe: on; reads SC01-02") >= 0 && out.indexOf("SC02 is now open to the group Probe and its 2 members.") >= 0,
      "open for this group");
    out = await run("g-close", "g-answer", "Close SC02 to the group Probe?");
    check(out.indexOf("Probe: on; reads SC01;") >= 0 && out.indexOf("SC02 is now closed to the group Probe.") >= 0, "close for this group");
    out = await run("g-give-each", "g-answer", "Give SC02 to each of the 2 members of Probe as their own chapters? Readers who join later do not get it.");
    check(out.indexOf("SC02 is now among the own chapters of 2 members of Probe; readers who join the group later do not get it.") >= 0,
      "give each current member their own copy");
    out = await run("g-english-on", "g-answer", "Turn the English of the group Probe on?");
    check(out.indexOf("English is now on for the group Probe and its 2 members.") >= 0, "the group's English on");
    out = await run("g-english-off", "g-answer", "Turn the English of the group Probe off?");
    check(out.indexOf("English is now off for the group Probe and its 2 members.") >= 0, "the group's English off");
    await until(() => document.querySelector("#g-feature option"));
    set("g-feature", "english");
    out = await run("g-feature-on", "g-answer", "Turn english on for the group Probe?");
    check(out.indexOf("english.on is now on for the group Probe and its 2 members.") >= 0, "a group feature on");
    out = await run("g-feature-off", "g-answer", "Turn english off for the group Probe?");
    check(out.indexOf("english.on is now off for the group Probe and its 2 members.") >= 0, "a group feature off");

    // The group switch on the group's row, and the commands its answer names.
    out = await press($("#g-table button[data-group-switch='Probe']"), "g-list-answer", "Switch the group Probe off?", "the switch on the row of Probe");
    check(out.indexOf("Probe: off;") >= 0 && out.indexOf("To close it for them: review.py close 'Reader 001' 'Reader 003' SC01") >= 0 &&
      out.indexOf("The group Probe is now off") >= 0, "switch off names the members who still open its chapters: " + out.slice(0, 300));
    const steps = $$("#g-list-answer .steps button").map(b => b.textContent);
    check(steps.indexOf("Close SC01 for these 2 readers") >= 0 && steps.indexOf("Switch the group Probe on") >= 0,
      "the page offers the commands the answer names: " + steps.join(" | "));
    let next = $$("#g-list-answer .steps button").filter(b => b.textContent === "Close SC01 for these 2 readers")[0];
    if (next) {
      const [, n] = await counted("POST close", async () => {
        next.click();
        const opened = await until(() => $("#ask").open, 5000);
        check(opened && text("#ask-text") === "Take SC01 out of the own chapters of 2 readers?" &&
          text("#ask-list") === "Reader 001Reader 003", "the offered close asks first, with the names: " + text("#ask-text") + " " + text("#ask-list"));
        $("#ask-go").click();
        return until(() => text("#g-list-answer").indexOf("SC01 is no longer among the own chapters of Reader 001 and Reader 003.") >= 0);
      });
      check(n === 1 && text("#g-list-answer").indexOf("SC01 is no longer among the own chapters of Reader 001 and Reader 003.") >= 0,
        "the offered close runs once, for both readers");
    }
    next = $$("#g-list-answer .steps button").filter(b => b.textContent === "Switch the group Probe on")[0];
    if (next) {
      next.click();
      const opened = await until(() => $("#ask").open, 5000);
      check(opened && text("#ask-text") === "Switch the group Probe on?" && text("#ask-more").indexOf("The group Probe has 2 members.") === 0,
        "the offered switch asks first, with the count");
      $("#ask-go").click();
      await until(() => text("#g-list-answer").indexOf("The group Probe is now on") >= 0);
      check(text("#g-list-answer").indexOf("The group Probe is now on") >= 0, "the offered switch runs");
    }
    await until(() => text("#g-toggle") === "Switch off");
    out = await run("g-toggle", "g-answer", "Switch the group Probe off?");
    check(out.indexOf("The group Probe is now off") >= 0, "the panel's switch turns the group off");
    await until(() => text("#g-toggle") === "Switch on" && text("#g-table tr[data-group='Probe']").indexOf("Switch on") >= 0);
    check(text("#g-table tr[data-group='Probe']").indexOf("off") >= 0, "the row shows the group off");
    out = await run("g-toggle", "g-answer", "Switch the group Probe on?");
    check(out.indexOf("The group Probe is now on") >= 0, "the panel's switch turns the group on");

    // The members in the Readers section, where the reader commands act on them.
    $("#g-in-readers").click();
    await until(() => location.hash === "#readers" && text("#r-count") === "2 of " + (total + 4) + " readers.");
    check($("#r-group").value === "Probe" && names() === "Reader 001, Reader 003", "List the members in Readers: " + names());
    await go("#groups", () => !$("#g-panel").hidden);
    out = await run("g-relink", "g-answer", "Give the 2 members of Probe new links?");
    check(out.indexOf("2 readers of Probe have new links") >= 0 && out.indexOf(params.get("data") + "/links-relink-") >= 0,
      "new links for every member go to a file");
    check(out.indexOf("#k=") < 0, "the group's new links are not shown");
    check(JSON.parse(bodies["POST relink"] || "{}").unbind === false, "without the box the members keep their LINE accounts and addresses");
    // relink --group G --unbind (70-verify.md item 5): the box beside the button removes every member's LINE accounts
    // and addresses with the new links. Reader 001 gets an address first, so one is removed.
    const added = await local("identity", { action: "add", name: "Reader 001", address: "reader001@example.org" });
    check(added.ok === true, "an address for Reader 001: " + (added.error || ""));
    check(text("#g-panel label.check").indexOf("and remove their LINE accounts and addresses") >= 0 && !$("#g-unbind").checked,
      "the box of --unbind stands beside New links for every member, not ticked");
    tick("#g-unbind", true);
    out = await run("g-relink", "g-answer", "Give the 2 members of Probe new links, and remove their LINE accounts and addresses?");
    check(out.indexOf("2 readers of Probe have new links; the old links no longer work; 1 LINE account or address no longer " +
      "signs in, and no browser was signed in.") >= 0 && out.indexOf(params.get("data") + "/links-relink-") >= 0 &&
      JSON.parse(bodies["POST relink"] || "{}").unbind === true, "relink --group --unbind removes the address: " + out.slice(-220));
    check(out.indexOf("#k=") < 0, "the group's new links are still not shown");
    check(!$("#g-unbind").checked, "the unbind box of the group is cleared after the new links");
    out = await run("g-remove", "g-answer", "Remove the group Probe?");
    check(out.indexOf("The group Probe is removed; its 2 members keep their own chapters.") >= 0, "remove the group");
    await until(() => text("#g-count") === "2 groups.");
    check($("#g-panel").hidden && !$("#g-table tr[data-group='Probe']"), "the removed group is gone from the page");

    // More than 20 members who hold the chapters as their own: the line lists no command line of names, and the
    // offered close takes the group's members. Youth then holds SC01 and SC03, so the line names "SC01, SC03".
    $("#g-open-Youth").click();
    await until(() => !$("#g-panel").hidden && text("#g-title") === "Group Youth");
    const youth = Number((/(\d+) members\./.exec(text("#g-member-count")) || [0, 0])[1]);
    set("g-spec", "SC01");
    out = await run("g-open", "g-answer", "Open SC01 to the group Youth and its " + youth + " members?");
    check(out.indexOf("SC01 is now open to the group Youth and its " + youth + " members.") >= 0, "open for a group of " + youth);
    out = await press($("#g-table button[data-group-switch='Youth']"), "g-list-answer", "Switch the group Youth off?", "the switch on the row of Youth");
    check(out.indexOf("To close it for them: review.py close NAME [NAME ...] SC01,SC03, with their names") >= 0,
      "with more than 20 such members the line names no names: " + out.slice(0, 260));
    next = $$("#g-list-answer .steps button").filter(b => b.textContent === "Close SC01,SC03 for the members of Youth who hold it as their own")[0];
    check(!!next, "the page offers the close for the members");
    if (next) {
      const t1 = performance.now();
      const [, n] = await counted("POST close", async () => {
        next.click();
        const opened = await until(() => $("#ask").open, 5000);
        check(opened && text("#ask-text") === "Take SC01,SC03 out of the own chapters of " + youth + " readers?" &&
          $$("#ask-list li").length === 21, "the offered close asks first, with the members: " + text("#ask-text"));
        $("#ask-go").click();
        return until(() => text("#g-list-answer").indexOf("SC01,SC03 is no longer among the own chapters of Probe Reader, Reader 002,") >= 0, 30000);
      });
      log("TIME the close for " + youth + " readers took " + Math.round(performance.now() - t1) + " ms");
      check(n === 1 && text("#g-list-answer").indexOf("SC01,SC03 is no longer among the own chapters of Probe Reader, Reader 002,") >= 0,
        "the offered close runs once, for every member who held SC01");
    }
    next = $$("#g-list-answer .steps button").filter(b => b.textContent === "Switch the group Youth on")[0];
    if (next) {
      next.click();
      await until(() => $("#ask").open, 5000);
      $("#ask-go").click();
      await until(() => text("#g-list-answer").indexOf("The group Youth is now on") >= 0);
    }
    check(text("#g-list-answer").indexOf("The group Youth is now on") >= 0, "Youth is on again");
    out = await run("g-close", "g-answer", "Close SC01 to the group Youth?");
    check(out.indexOf("SC01 is now closed to the group Youth.") >= 0, "Youth no longer holds SC01");
  }

  // Requests to read through a general link, and the general links (61-admin-contract.md section 5).
  async function requests() {
    await go("#requests", () => text("#q-count") === "3 requests waiting for you." && $$("#gl-table tbody tr").length === 1);
    check(text("#q-count") === "3 requests waiting for you.", "the requests waiting are listed: " + text("#q-count"));
    check(text("#asking") === "3 waiting" && !$("#asking").hidden, "the menu counts the requests waiting: " + text("#asking"));
    const row = who => $$("#q-table tbody tr").filter(r => (r.querySelector("td.name") || {}).textContent === who)[0];
    const id = who => (row(who) || { getAttribute: () => "" }).getAttribute("data-request");
    check(row("LINE tester 3") && row("LINE tester 3").textContent.indexOf("Pastors") >= 0, "a LINE request names its group");
    // Approve as a new reader: the name starts as the address, which the hint asks to change.
    row("kanya@example.org").querySelector("button[data-approve-request]").click();
    await until(() => !$("#q-panel").hidden);
    check($("#q-name").value === "kanya@example.org" && text("#q-name-hint").indexOf("would become the reader's name") >= 0,
      "approve offers the address as the name and asks for a name");
    check($("#q-groups input[data-group='Pastors']").checked, "the group of the general link is ticked");
    set("q-name", "Kanya");
    set("q-grant", "SC02");
    const kanya = id("kanya@example.org");
    let out = await run("q-approve-new", "q-answer", "");
    check(out.indexOf("kanya@example.org is now the reader Kanya, who reads SC02 and is in the group Pastors, and signs in with that address.") >= 0,
      "request approve --name --grant --group: " + out.slice(-200));
    check(JSON.parse(bodies["POST request"] || "{}").id === Number(kanya), "the approval names the request");
    await until(() => $("#q-panel").hidden && text("#q-count") === "2 requests waiting for you.");
    check(text("#asking") === "2 waiting", "the menu's count follows: " + text("#asking"));
    // Approve for a reader who exists.
    row("LINE tester 3").querySelector("button[data-approve-request]").click();
    await until(() => !$("#q-panel").hidden);
    set("q-reader", "Boon Mee");
    out = await run("q-approve-reader", "q-answer", "Let LINE tester 3 sign in to Boon Mee?");
    check(out.indexOf("The LINE account LINE tester 3 now signs in to Boon Mee.") >= 0, "request approve --reader: " + out.slice(-160));
    await until(() => text("#q-count") === "1 request waiting for you.");
    // Decline, then forget.
    const pim = id("pim@example.org");
    out = await press(row("pim@example.org").querySelector("button[data-decline]"), "q-answer", "Decline request " + pim + " of pim@example.org?", "Decline");
    check(out.indexOf("Request " + pim + " of pim@example.org is declined; that address cannot ask again until: review.py request forget " + pim) >= 0,
      "request decline: " + out.slice(-200));
    await until(() => text("#q-count") === "No request is waiting for you." && $("#asking").hidden);
    check($("#asking").hidden, "the menu no longer counts requests");
    set("q-state", "declined");
    await until(() => $$("#q-table tbody tr").length === 1);
    // The answer offers the forget it names; the list follows.
    const offered = $$("#q-answer .steps button").filter(b => b.textContent === "Forget request " + pim)[0];
    check(!!offered, "the answer offers: Forget request " + pim);
    if (offered) {
      offered.click();
      const opened = await until(() => $("#ask").open, 5000);
      check(opened && text("#ask-text") === "Forget request " + pim + "?", "the offered forget asks first: " + text("#ask-text"));
      $("#ask-go").click();
      await until(() => text("#q-answer").indexOf("Request " + pim + " is forgotten; pim@example.org may ask again.") >= 0);
      check(text("#q-answer").indexOf("Request " + pim + " is forgotten; pim@example.org may ask again.") >= 0, "request forget");
      await until(() => $$("#q-table tbody tr").length === 0);
      check($$("#q-table tbody tr").length === 0, "the declined list is empty after the forget");
    }
    set("q-state", "all");
    await until(() => text("#q-count") === "2 requests; 0 waiting for you.");
    check(text("#q-count") === "2 requests; 0 waiting for you." && text("#q-table").indexOf("now the reader Kanya") >= 0,
      "requests --all: " + text("#q-count"));
    set("q-state", "approved");
    await until(() => text("#q-count") === "2 requests; 0 waiting for you.");
    const tied = id("LINE tester 3");
    out = await press($("#q-table button[data-forget='" + tied + "']"), "q-answer", "Forget request " + tied + " of LINE tester 3?", "Forget on a row");
    check(out.indexOf("Request " + tied + " is forgotten; LINE tester 3 may ask again.") >= 0, "Forget on a request's row: " + out.slice(-120));
    await until(() => text("#q-count") === "1 request; 0 waiting for you.");
    check(text("#q-count") === "1 request; 0 waiting for you.", "requests --approved after the forget: " + text("#q-count"));
    set("q-state", "open");

    // General links: one of Pastors exists; make one of Youth, list one group's, switch it off, replace Pastors'.
    check(text("#gl-count") === "1 general link; 1 taking requests." && text("#gl-table").indexOf("Pastors") >= 0, "the general link of Pastors is listed");
    set("gl-new-group", "Youth");
    set("gl-days", "10");
    set("gl-uses", "3");
    out = await run("gl-new", "gl-answer", "Make a new general link of Youth, for 10 days or 3 requests?");
    const glink = $("#gl-answer .linkrow input.link");
    check(glink && glink.value.indexOf(params.get("site") + "/#join=") === 0 && out.indexOf("Youth has a new general link, which takes up to 3 requests until ") >= 0,
      "general-link --new shows the link once, with a Copy button: " + out.slice(-160));
    check($$("#gl-answer pre").every(x => x.textContent.indexOf("#join=") < 0), "the general link is not repeated in the lines");
    await until(() => $$("#gl-table tbody tr").length === 2);
    set("gl-group", "Youth");
    await until(() => $$("#gl-table tbody tr").length === 1);
    check(text("#gl-table").indexOf("Youth") >= 0 && text("#gl-table").indexOf("Pastors") < 0, "general-link Youth lists one group's");
    out = await press($("#gl-table button[data-gl-off='Youth']"), "gl-answer", "Switch off the general link of Youth?", "Switch off");
    check(out.indexOf("The general link of Youth no longer takes requests; a new one is made with: review.py general-link Youth --new") >= 0,
      "general-link --off: " + out.slice(-160));
    set("gl-group", "");
    await until(() => $$("#gl-table tbody tr").length === 2);
    set("gl-new-group", "Pastors");
    set("gl-days", "");
    set("gl-uses", "");
    out = await run("gl-new", "gl-answer", "Make a new general link of Pastors, for 90 days or 100 requests?");
    check($("#ask-more").textContent.indexOf("The link of Pastors before it stops taking requests now.") === 0, "the question says the old link stops");
    check(out.indexOf("; the link before it no longer takes requests.") >= 0, "a new link of Pastors replaces the old: " + out.slice(-160));
    await until(() => $$("#gl-table tbody tr").length === 3);
    check(text("#gl-count") === "3 general links; 1 taking requests.", "the list counts the links: " + text("#gl-count"));
  }

  async function comments() {
    await go("#comments", () => text("#x-count") !== "" && text("#o-count") !== "");
    const ids = params.get("ids").split(",");
    // Review rounds.
    check(text("#o-count") === "No review round has started for any book." &&
      text("#o-table").indexOf("SCbefore the first round") >= 0 && /before the first round3$/.test(text("#o-table")),
      "the rounds list the comments before the first round: " + text("#o-table"));
    check($("#e-round").value === "before SC" && !$("#e-round-go").disabled,
      "with no round yet, Export the round offers the comments before the first round: " + $("#e-round").value);
    set("o-name", "first");
    let out = await run("o-go", "o-answer", "Start the review round first of SC now?");
    check($("#ask-more").textContent.indexOf("every chapter of SC counts as not yet finished") >= 0, "the question says what a round changes");
    check(out.indexOf("The review round first of SC started") >= 0, "a round starts: " + out.slice(-160));
    await until(() => $("#o-table tr[data-round='SC first']"));
    check(text("#o-table tr[data-round='SC first']").indexOf("current round") >= 0 && text("#o-count") === "1 round.", "the new round is current");
    set("o-book", "SC");
    await until(() => urls.some(u => u.indexOf("/local/rounds?book=SC") >= 0) && text("#o-count") === "1 round.");
    check(urls.some(u => u.indexOf("/local/rounds?book=SC") >= 0), "the rounds of one book (rounds SC)");
    set("o-book", "");
    set("o-name", "first");
    out = await run("o-go", "o-answer", "Start the review round first of SC now?");
    check(out.indexOf("SC already has a round named first") >= 0 && $("#o-answer .reply.bad"), "a round name used before is refused");
    await until(() => $$("#e-round option").some(o => o.value === "round SC first"));
    check($$("#e-round option").map(o => o.value).join("|") === "before SC|round SC first",
      "the export offers the round with its book, and the comments before it");
    set("e-round", "round SC first");

    // Export: what changed, everything, one round.
    out = await run("e-go", "e-answer", "");
    check(out.indexOf("3 comments exported") >= 0 && out.indexOf("JSON: " + params.get("exports") + "/review-") >= 0 &&
      out.indexOf("holds no earlier export") >= 0, "the first export holds every comment and says so: " + out.slice(-200));
    await until(() => $$("#x-table tbody tr").length === 1);
    out = await run("e-go", "e-answer", "");
    check(out.indexOf("comments exported that are new or changed since a minute before the export review-") >= 0,
      "the next export brings what changed since a minute before the last: " + out.slice(-200));
    await until(() => $$("#x-table tbody tr").length === 2);
    check($$("#x-table tbody tr").length === 2, "two exports in the same second are both kept");
    let sent = urls.length;
    out = await run("e-round-go", "e-answer", "");
    check(out.indexOf("0 comments exported from the review round first, 0 not yet processed.") >= 0, "export --round: " + out.slice(-120));
    set("e-round", "before SC");
    out = await run("e-round-go", "e-answer", "");
    check(out.indexOf("3 comments exported written before the first review round, 3 not yet processed.") >= 0,
      "export --before-first-round: " + out.slice(-120));
    check(urls.length > sent, "the round exports went to the local server");
    set("e-reader", "Mali Srisuk");
    tick("#e-unprocessed", true);
    out = await run("e-all", "e-answer", "");
    check(out.indexOf("1 comment exported, 1 not yet processed.") >= 0, "export --all of one reader's comments not yet processed: " + out.slice(-120));
    set("e-reader", "");
    tick("#e-unprocessed", false);
    await until(() => $$("#x-table tbody tr").length === 5 && $$("#t-export option").length === 6);
    out = await run("t-go", "t-answer", "");
    check(out.indexOf("are written in " + params.get("exports") + "/review-") >= 0, "triage says where the packets went: " + out.slice(-160));
    await until(() => text("#x-table").indexOf("SC01 in review-") >= 0);
    check(text("#x-table").indexOf("SC01 in review-") >= 0, "the export list shows the packet: " + text("#x-table").slice(0, 300));
    file("p-file", "replies.json", JSON.stringify([{ id: Number(ids[0]), reply: "Thank you." },
      { id: Number(ids[1]), reply: "ขอบคุณครับ" }]), "application/json");
    out = await run("p-go", "p-answer", "Send 2 replies from replies.json?");
    check(out.indexOf("2 replies set, 0 cleared.") >= 0, "replies from a JSON file");
    file("p-file", "clear.csv", "id,reply\n" + ids[1] + ",\n", "text/csv");
    out = await run("p-go", "p-answer", "Send 1 reply from clear.csv?");
    check(out.indexOf("0 replies set, 1 cleared.") >= 0, "an empty reply in a CSV file clears one");
    set("d-ids", ids.join(" "));
    out = await run("d-go", "d-answer", "");
    check(out.indexOf(ids.length + " comments marked processed.") >= 0, "mark processed: " + out.slice(-160));
    tick("#d-undo", true);
    out = await run("d-go", "d-answer", "");
    check(out.indexOf(ids.length + " comments marked not processed.") >= 0, "undo processed");
    tick("#d-undo", false);
    set("d-ids", "999");
    out = await run("d-go", "d-answer", "");
    check(out.indexOf("Not in any export, so not marked: 999.") >= 0 && $("#d-answer .reply.bad"),
      "a number that was never exported is named");
  }

  async function site() {
    await go("#site", () => $$("#s-features tbody tr").length > 0);
    check(text("#s-info").indexOf("The dev server on this computer.") >= 0 && text("#s-info").indexOf(params.get("data") + "/admin-token") >= 0,
      "the site section names the server and the token file");
    check(text("#s-features").indexOf("english.on") >= 0, "the features are listed");
    set("s-keep", "3");
    let out = await run("s-backup", "s-answer", "");
    check(out.indexOf("Backup written: " + params.get("data") + "/backups/review-") >= 0, "backup of the dev data");
    out = await run("s-new-token", "s-answer", "Make a new admin token for the dev server?");
    check(out.indexOf("New admin token written to " + params.get("data") + "/admin-token") >= 0, "a new admin token");
    await go("#chapters", () => $$("#chapters-SC tbody tr").length >= 13);
    check($$("#chapters-SC tbody tr").length >= 13, "the page goes on working with the new token");
  }

  // Signing in, in the Site section: review.py signin, signin check and signin test-mail.
  async function siteSignin() {
    await go("#site", () => $$("#s-signin li").length > 5);
    check(text("#s-signin").indexOf("Sign-in with LINE: on, channel ") >= 0 && text("#s-signin").indexOf("This is the dev server") >= 0,
      "the sign-in settings are listed: " + text("#s-signin").slice(0, 200));
    check(text("#s-last-mail").indexOf("Last mail: a note to an approved requester, ") === 0 ||
      text("#s-last-mail").indexOf("Last mail: a sign-in code, ") === 0, "the last mail and its result: " + text("#s-last-mail"));
    // The menu marks Site only while the last mail failed (67-operations.md OPS4-10); here it was sent.
    check($("#mailbad") && $("#mailbad").hidden && text("#mailbad") === "", "the menu does not mark Site while mail works");
    check($$("#s-mail-log tbody tr").length >= 4, "the mails sent lately are listed: " + $$("#s-mail-log tbody tr").length);
    let out = await run("s-check", "s-signin-answer", "");
    check(out.indexOf("LINE: works. The API reached ") >= 0 && out.indexOf("Mail: works. Mail is written to files in ") >= 0,
      "signin check: " + out.slice(0, 200));
    out = await run("s-test-mail", "s-signin-answer", "");
    check(out.indexOf("Write the address the test mail goes to.") >= 0, "a test mail needs an address");
    set("s-test-to", "probe@example.org");
    out = await run("s-test-mail", "s-signin-answer", "");
    check(out.indexOf("A test mail went to probe@example.org.") >= 0, "signin test-mail: " + out.slice(-120));
    await until(() => text("#s-last-mail").indexOf("Last mail: a test mail, ") === 0);
    check(/^Last mail: a test mail, \d{4}-\d\d-\d\d \d\d:\d\d UTC: sent\.$/.test(text("#s-last-mail")), "the last mail is the test: " + text("#s-last-mail"));
    set("s-test-to", "probe");
    out = await run("s-test-mail", "s-signin-answer", "");
    check(out.indexOf("to must be an email address") >= 0 && $("#s-signin-answer .reply.bad"), "a wrong address is refused: " + out.slice(-120));
  }

  function header() {
    const bar = text("#server");
    check(bar.indexOf("Server: " + params.get("site")) === 0 && bar.indexOf("dev server") > 0, "the server is shown at the top: " + bar);
  }

  // Every word on the page comes from strings.json: no key of the file shows as it is.
  async function noKeys(where) {
    const res = await real("strings.json");
    const words = await res.json();
    const shown = document.body.innerText + " " + $$("[aria-label],[placeholder],[title]").map(el =>
      [el.getAttribute("aria-label"), el.getAttribute("placeholder"), el.getAttribute("title")].join(" ")).join(" ");
    const keys = Object.keys(words).filter(k => k.indexOf("_") > 0 && new RegExp("(^|[^a-z_])" + k + "($|[^a-z0-9_])").test(shown));
    check(keys.length === 0, "no key of strings.json shows as it is " + where + (keys.length ? ": " + keys.join(", ") : ""));
  }

  async function main() {
    check(/^#key=/.test(hashAtStart), "the page was opened with its key");
    await until(() => $$("#chapters-SC tbody tr").length > 0, 15000);
    check(location.hash === "#chapters" || location.hash === "", "the key left the address bar");
    let kept = "";
    try { kept = sessionStorage.getItem("review-admin.key") || ""; } catch (e) { kept = ""; }
    check(kept.length > 20, "the key is kept for a reload");
    check(text("nav a[data-section='readers']").indexOf("Readers") === 0 && $("#nav").getAttribute("aria-label") === "Sections",
      "the menu takes its words from strings.json");
    header();
    const steps = [["chapters", chapters], ["readers", readers], ["groups", groups], ["requests", requests],
      ["comments", comments], ["site signing in", siteSignin], ["site", site]];
    for (let i = 0; i < steps.length; i++) {
      try {
        await steps[i][1]();
        header();
        await noKeys("in " + steps[i][0]);
      } catch (e) {
        check(false, steps[i][0] + " threw " + e + " " + (e && e.stack));
      }
    }
    check($$("[style]").length === 0, "no element carries a style attribute");
    log("ROUTES " + Object.keys(used).filter(k => k.indexOf(" ") > 0).sort().join(","));
    const sorted = times.filter(t => t[0].indexOf(" ") > 0).map(t => t[1]).sort((a, b) => a - b);
    const slow = times.filter(t => t[0].indexOf("GET ") === 0).sort((a, b) => b[1] - a[1])[0];
    log("TIME " + sorted.length + " requests; median " + Math.round(sorted[Math.floor(sorted.length / 2)]) +
      " ms; slowest reading request " + (slow ? slow[0] + " " + Math.round(slow[1]) + " ms" : "none"));
    errors.forEach(e => check(false, e));
    log("DONE main " + fails + " failed");
    location.href = "probe.html?mode=badkey#key=wrong-key-for-the-test";
  }

  async function badkey() {
    const shown = await until(() => !$("#nokey").hidden && $("#nokey"));
    check(shown && text("#nokey").indexOf("Open the address that review.py admin printed.") >= 0, "a wrong key is told plainly: " + text("#nokey"));
    check($("#chapters").hidden && $("#readers").hidden, "nothing else is shown with a wrong key");
    errors.forEach(e => check(false, e));
    log("DONE badkey " + fails + " failed");
    try { sessionStorage.clear(); } catch (e) { /* nothing kept */ }
    location.href = "probe.html?mode=nokey";
  }

  async function nokey() {
    const shown = await until(() => !$("#nokey").hidden && $("#nokey"));
    check(shown && text("#nokey").indexOf("open the address it prints") >= 0, "no key is told plainly: " + text("#nokey"));
    check(!Object.keys(used).length, "no request is made without a key");
    errors.forEach(e => check(false, e));
    log("DONE nokey " + fails + " failed");
    log("DONE");
  }

  // The live site, through the SSH tunnel: the red server line on every screen, the chapters, readers, devices,
  // groups and rounds through the tunnel, the live export folder, and no backup or token button.
  async function live() {
    await until(() => $$("#chapters-SC tbody tr").length > 0, 20000);
    const sections = ["#chapters", "#readers", "#requests", "#groups", "#comments", "#site"];
    for (let i = 0; i < sections.length; i++) {
      await go(sections[i], () => !$(sections[i]).hidden && $(sections[i]).children.length > 0);
      const bar = $("#server");
      check(bar.classList.contains("live") && bar.textContent.indexOf("Server: " + params.get("site")) === 0 &&
        bar.textContent.indexOf("The live site") > 0, sections[i] + " shows the live server at the top: " + bar.textContent);
    }
    check($$("#chapters-SC tbody tr").length >= 13, "the chapters come through the tunnel");
    check(text("#s-info").indexOf(params.get("exports")) >= 0 && text("#s-info").indexOf("The live site") >= 0,
      "the site section names the live export folder");
    check(!$("#s-backup") && !$("#s-new-token") && text("#site").indexOf("review-backup.timer") >= 0,
      "backup and a new token point to the droplet");
    check(document.title === "Live site: admin", "the tab says Live: " + document.title);
    await go("#readers", () => /readers\.$/.test(text("#r-count")) && text("#v-count") !== "");
    check(/^\d+ readers\.$/.test(text("#r-count")), "the readers come through the tunnel: " + text("#r-count"));
    check(text("#v-count") === "No device is waiting for your approval.", "the devices come through the tunnel: " + text("#v-count"));
    await go("#comments", () => /round/.test(text("#o-count")));
    check(text("#o-count") === "1 round.", "the rounds come through the tunnel: " + text("#o-count"));
    await go("#requests", () => text("#q-count") !== "" && text("#gl-count") !== "");
    check(text("#q-count") === "No request is waiting for you." && text("#gl-count") === "3 general links; 1 taking requests.",
      "the requests and general links come through the tunnel: " + text("#q-count") + " " + text("#gl-count"));
    await go("#site", () => $$("#s-signin li").length > 5);
    check(text("#s-signin").indexOf("Sign-in with LINE: on") >= 0, "the sign-in settings come through the tunnel");
    // review.py admin opened the browser at a one-time code, which the page traded for the key (45 SEC3-7).
    check(/^#once=/.test(hashAtStart) && used["POST trade"], "the page traded the browser's one-time code for its key");
    log("ROUTES " + Object.keys(used).filter(k => k.indexOf(" ") > 0).sort().join(","));
    errors.forEach(e => check(false, e));
    log("DONE live " + fails + " failed");
    try { sessionStorage.clear(); } catch (e) { /* nothing kept */ }
    location.href = "probe.html?mode=onceused" + hashAtStart;
  }

  // The same one-time address opened again: the code works once, and the page says to open the printed address.
  async function onceused() {
    const shown = await until(() => !$("#nokey").hidden && $("#nokey"));
    check(shown && text("#nokey").indexOf("worked once") >= 0 && text("#nokey").indexOf("review.py admin printed") > 0,
      "a one-time address used again is told plainly: " + text("#nokey"));
    check(Object.keys(used).join(",") === "POST trade", "nothing but the trade is asked with a used code: " + Object.keys(used));
    errors.forEach(e => check(false, e));
    log("DONE onceused " + fails + " failed");
    log("DONE");
  }

  window.addEventListener("load", () => {
    ({ main: main, badkey: badkey, nokey: nokey, live: live, onceused: onceused })[MODE]().catch(e => {
      check(false, "the probe threw " + e);
      log("DONE");
    });
  });
})();

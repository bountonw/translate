// The admin page of the proofreading site: its entry point. review.py admin serves this folder on 127.0.0.1 and
// opens it with #key=...; every request goes through api.js, which sends the key. The page's words come from
// strings.json (words.js). Each section is a module with show(section), called each time the section is opened,
// so a section loads only what it shows, when it shows it.
import { takeKey, get, on, file } from "./api.js";
import { clear, h } from "./ui.js";
import { t, setWords, language } from "./words.js";
import { state, countWaiting, countRequests, loadAuth } from "./shared.js";
import * as chapters from "./chapters.js";
import * as readers from "./readers.js";
import * as requests from "./requests.js";
import * as groups from "./groups.js";
import * as comments from "./comments.js";
import * as site from "./site.js";

const SECTIONS = { chapters: chapters, readers: readers, requests: requests, groups: groups, comments: comments,
  site: site };
const START = "chapters";

function stop(message) {
  Object.keys(SECTIONS).forEach(id => { document.getElementById(id).hidden = true; });
  const p = document.getElementById("nokey");
  p.textContent = message;
  p.hidden = false;
}

// The line at the top of every section: the server every change goes to, red for the live site.
function serverLine(info) {
  const bar = document.getElementById("server");
  clear(bar);
  bar.classList.toggle("live", !info.local);
  bar.append(h("strong", null, t("server_line", { server: info.server })), " ",
    info.ssh ? t("server_live") : (info.local ? t("server_dev") : ""));
  document.title = info.local ? t("title_dev") : t("title_live");
}

function open() {
  const id = (location.hash || "").slice(1);
  const name = SECTIONS[id] ? id : START;
  document.querySelectorAll("#nav a").forEach(a => {
    if (a.getAttribute("data-section") === name) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  Object.keys(SECTIONS).forEach(s => { document.getElementById(s).hidden = s !== name; });
  SECTIONS[name].show(document.getElementById(name));
}

async function start() {
  on("busy", running => {
    document.getElementById("busy").hidden = !running;
    document.documentElement.classList.toggle("running", running);
  });
  on("badKey", () => stop(t("bad_key")));
  // The words and the server's description are fetched at once; only a page opened with its key asks the server.
  const words = file("strings.json");
  const noKey = await takeKey();
  const info = noKey ? null : get("info");
  // Without its words the page cannot speak: index.html holds that one message in English.
  if (!setWords(await words)) {
    stop(document.getElementById("nowords").textContent);
    return;
  }
  document.documentElement.lang = language();
  document.querySelectorAll("[data-t]").forEach(el => { el.textContent = t(el.getAttribute("data-t")); });
  document.querySelectorAll("[data-t-label]").forEach(el => { el.setAttribute("aria-label", t(el.getAttribute("data-t-label"))); });
  if (noKey) {
    stop(t(noKey));
    return;
  }
  const res = await info;
  if (!res.ok) {
    stop(res.refused === "bad_key" ? t("bad_key") : res.error);
    return;
  }
  state.info = res.result;
  serverLine(state.info);
  window.addEventListener("hashchange", open);
  open();
  countWaiting();
  countRequests();
  loadAuth();
}

start();

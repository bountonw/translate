// The admin page's only way to the local server of review.py admin. Every local route is listed here with its
// method; tests/test_admin_page.py checks that this list matches review_admin.routes() and that the page calls
// each route. The local server adds the admin token; the page sends only the key from the address it opened.
import { t } from "./words.js";

export const ROUTES = {
  info: "GET", chapters: "GET", source: "GET", readers: "GET", groups: "GET", features: "GET", exports: "GET",
  rounds: "GET", devices: "GET",
  publish: "POST", withdraw: "POST", "align-packet": "POST",
  invite: "POST", open: "POST", close: "POST", revoke: "POST", restore: "POST", relink: "POST",
  english: "POST", feature: "POST", group: "POST", device: "POST", "delete-comments": "POST",
  round: "POST", export: "POST", triage: "POST", replies: "POST", processed: "POST",
  backup: "POST", "new-token": "POST", trade: "POST"
};

const KEY_STORE = "review-admin.key";
let key = "";
let running = 0;
const watchers = { busy: [], badKey: [] };

// The key comes in the address as #key=..., the address review.py admin prints; the browser it opens gets
// #once=... instead, a one-time code that this page trades for the key (route trade), so the browser's command
// line never holds the key. The key is kept in sessionStorage so that a reload goes on working, and the address
// bar loses it. Resolves to "" when the page has its key, or to the key of the message that says why not.
export async function takeKey() {
  const m = /^#key=([A-Za-z0-9_-]+)/.exec(location.hash);
  const once = /^#once=([A-Za-z0-9_-]+)/.exec(location.hash);
  if (m || once) history.replaceState(null, "", location.pathname + location.search);
  if (m) {
    key = m[1];
  } else if (once) {
    const res = await post("trade", { code: once[1] });
    key = res.ok && res.result && typeof res.result.key === "string" ? res.result.key : "";
    if (!key) return res.refused === "bad_once" ? "once_used" : "no_key";
  } else {
    try { key = sessionStorage.getItem(KEY_STORE) || ""; } catch (e) { key = ""; }
    return key ? "" : "no_key";
  }
  try { sessionStorage.setItem(KEY_STORE, key); } catch (e) { /* the page still works until it is reloaded */ }
  return "";
}

export function on(event, fn) {
  watchers[event].push(fn);
}

function tell(event, value) {
  watchers[event].forEach(fn => fn(value));
}

function failed(message, code) {
  return { ok: false, lines: [], error: message, result: null, refused: code };
}

// A file of the page itself, such as strings.json, as JSON; null when it cannot be read. It needs no key.
export async function file(path) {
  try {
    const res = await fetch(path, { cache: "no-cache", credentials: "same-origin" });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}

async function send(route, method, body, params) {
  if (ROUTES[route] !== method) {
    return failed(t("api_no_route", { route: method + " /local/" + route }), "page_fault");
  }
  let url = "/local/" + route;
  if (params) {
    const q = new URLSearchParams();
    Object.keys(params).forEach(k => {
      const v = params[k];
      if (v !== undefined && v !== null && v !== "" && v !== false) q.set(k, v === true ? "1" : String(v));
    });
    const text = q.toString();
    if (text) url += "?" + text;
  }
  const init = { method: method, headers: { "X-Admin-Key": key }, cache: "no-store", credentials: "same-origin" };
  if (method === "POST") {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body || {});
    running += 1;
    tell("busy", running > 0);
  }
  try {
    let res;
    try {
      res = await fetch(url, init);
    } catch (e) {
      return failed(t("api_offline"), "offline");
    }
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    if (res.status === 200 && data && typeof data.ok === "boolean") {
      if (!Array.isArray(data.lines)) data.lines = [];
      if (typeof data.error !== "string") data.error = "";
      return data;
    }
    if (data && data.error === "bad_key") tell("badKey", data.message);
    return failed((data && data.message) || t("api_status", { status: res.status }),
      (data && data.error) || "status_" + res.status);
  } finally {
    if (method === "POST") {
      running -= 1;
      tell("busy", running > 0);
    }
  }
}

export function get(route, params) {
  return send(route, "GET", null, params);
}

export function post(route, body) {
  return send(route, "POST", body, null);
}

export function busy() {
  return running > 0;
}

// What several sections read: the server's description (the route info), loaded once at the start, the
// features, loaded once when a section first needs them, and the count of devices waiting for approval, which
// the Readers link of the menu shows.
import { get } from "./api.js";
import { h } from "./ui.js";
import { t, plural } from "./words.js";

export const state = { info: null, features: null };

export async function features() {
  if (!state.features) {
    const res = await get("features");
    state.features = res.ok ? res.result.features : null;
    return state.features || [];
  }
  return state.features;
}

// The on/off settings a reader or a group can hold: "english" for english.on, "name.setting" for any other.
export function switches(list) {
  const out = [];
  list.forEach(f => {
    Object.keys(f.settings || {}).forEach(s => {
      if (f.settings[s].type === "bool") out.push(s === "on" ? f.name : f.name + "." + s);
    });
  });
  return out;
}

export function featureSelect(id) {
  const select = h("select", { id: id, "aria-label": t("feature") });
  features().then(list => {
    switches(list).forEach(name => select.append(h("option", { value: name }, name)));
  });
  return select;
}

export function bookIds() {
  return state.info ? Object.keys(state.info.books) : [];
}

export function bookName(id) {
  const b = state.info && state.info.books[id];
  return b && b.title_en ? t("book_name", { title: b.title_en, id: id }) : id;
}

// The menu's note of the devices waiting for approval, as review.py devices lists them.
export function showWaiting(n) {
  const el = document.getElementById("waiting");
  if (!el) return;
  el.textContent = n ? plural(n, "nav_waiting") : "";
  el.hidden = !n;
}

export async function countWaiting() {
  const res = await get("devices");
  if (res.ok) showWaiting(res.result.devices.filter(d => d.state === "waiting").length);
  return res;
}

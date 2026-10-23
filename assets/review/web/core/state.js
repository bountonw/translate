/* Proofreading site: the page's shared state (web/core/state.js).

   S holds what the page shows now; `store` is the device store of store.js. on() and emit() carry
   news from the network part (net.js) to the parts that draw, so neither imports the other's
   screens. The events:

     sync       the outbox changed: the note at the foot of the screen is drawn again
     result     the server answered a write: {verdict, op, data, status}
     me         a new chapter list arrived from /api/me
     offline    /api/me failed and no chapter list is on the device
     auth       the reader's link stopped working
     device     the link does not work on this device until the translator approves it (403 device_waiting)
     chapter    a chapter text arrived: {book, id, data} or {book, id, gone: true} or {book, id, missing: true}
     comments   a comment list arrived: {book, id}
     lang       the interface language changed */

import { makeStore } from "./store.js";

let ls = null;
try { ls = window.localStorage; } catch (e) { ls = null; }
export const store = makeStore(ls);

export const S = {
  code: null, me: null, meAt: 0, view: "boot", authBlocked: false, lang: "th",
  deviceWaiting: false,  // true while the link waits for the translator's approval of this device
  deviceNumber: null,    // this device's number in the translator's lists, from the site's 403 device_waiting
  meStatus: null,        // the status of the last answer of /api/me: 0 when the site could not be reached
  book: null, ch: null, chapter: null, waiting: null,   // the open chapter; a newer text held back
  lastSel: null, saved: new Map(), homeY: 0, homeSig: "",
  from: null,          // the chapter the list of unsaved comments was opened from
  openNote: null,      // {a, cid}: a comment to open for a change once its chapter is drawn
  netFails: 0,
};

const handlers = {};
export function on(name, fn) {
  (handlers[name] = handlers[name] || []).push(fn);
}
/* Every handler runs even when one fails; a failure is thrown again afterwards, so the page's error
   notice still shows it. */
export function emit(name, data) {
  for (const fn of handlers[name] || []) {
    try { fn(data); } catch (e) { setTimeout(() => { throw e; }, 0); }
  }
}

// Site: what review.py admin works against, the backup of the dev data and a new dev admin token, the features
// with their settings, and signing in: the sign-in routes and the mailer of config.json, the notes to you, the last
// mails sent and their results, as review.py signin shows them; whether the API reaches LINE and the mailer
// (signin check); and a test mail (signin test-mail ADDRESS). The live site's backups and token are made on the
// droplet.
import { get, post, busy } from "./api.js";
import { h, clear, button, field, fill, td, answer, ask, refuse, working, stamp } from "./ui.js";
import { t } from "./words.js";
import { state, features, showMail } from "./shared.js";

const s = {};
let built = false;

export async function show(root) {
  if (!built) {
    build(root);
    built = true;
  }
  const signin = loadSignin();
  const list = await features();
  const rows = [];
  list.forEach(f => Object.keys(f.settings || {}).forEach(name => {
    const x = f.settings[name];
    const shown = x.type === "bool" ? (x["default"] ? t("is_on") : t("is_off")) : String(x["default"]);
    rows.push(h("tr", null, td(f.name, "name"), td(f.name + "." + name), td(x.type), td(shown), td(x.help || "")));
  }));
  fill(s.features, [t("s_col_feature"), t("s_col_setting"), t("s_col_type"), t("s_col_default"), t("s_col_help")], rows);
  await signin;
}

// The kinds of mail of the mail log (mail_log of GET /api/admin/auth).
const KINDS = { code: "s_mail_code", notify: "s_mail_notify", approved: "s_mail_approved", test: "s_mail_test" };

// The sign-in settings as review.py signin prints them, and the mails sent lately with their results.
async function loadSignin() {
  const res = await get("auth");
  clear(s.signin);
  if (!res.ok) {
    s.signin.append(h("li", { class: "error" }, res.error));
    s.last.textContent = "";
    return;
  }
  res.lines.forEach(line => s.signin.append(h("li", null, line)));
  state.auth = res.result;
  const log = res.result.mail_log || [];
  const last = res.result.last_mail;
  showMail(last);
  clear(s.last).append(last ? h("span", { class: last.ok ? null : "flag" }, last.ok
    ? t("s_last_mail_ok", { time: stamp(last.at), kind: t(KINDS[last.kind] || "s_mail_test") })
    : t("s_last_mail_bad", { time: stamp(last.at), kind: t(KINDS[last.kind] || "s_mail_test"), detail: last.detail }))
    : t("s_last_mail_none"));
  fill(s.log, [t("s_col_mail_at"), t("s_col_mail_kind"), t("s_col_mail_provider"), t("s_col_mail_result")],
    log.map(m => h("tr", { class: m.ok ? "" : "waiting" }, td(stamp(m.at), "nowrap"), td(t(KINDS[m.kind] || "s_mail_test")),
      td(m.provider), td(m.ok ? t("s_mail_sent") : t("s_mail_not_sent", { detail: m.detail })))));
  s.log.hidden = log.length === 0;
}

function build(root) {
  const info = state.info;
  const facts = [
    [t("s_server"), info.server],
    [t("s_what"), info.ssh ? t("server_live") : t("server_dev")],
    [t("s_token"), info.token_file],
    [t("s_repo"), info.repo || t("s_no_repo")],
    [t("s_exports"), info.export_dir],
    [t("s_dev_data"), info.dev_data || t("s_no_dev_data")]
  ];
  s.box = h("div", { class: "answer", id: "s-answer", hidden: true, "aria-live": "polite" });
  s.features = h("table", { class: "list", id: "s-features" });
  s.signin = h("ul", { class: "lines", id: "s-signin" });
  s.last = h("p", { id: "s-last-mail" });
  s.log = h("table", { class: "list", id: "s-mail-log" });
  s.to = h("input", { type: "text", id: "s-test-to", autocomplete: "off", spellcheck: "false",
    placeholder: t("a_address_placeholder") });
  s.signinBox = h("div", { class: "answer", id: "s-signin-answer", hidden: true, "aria-live": "polite" });
  root.append(h("h2", null, t("s_title")),
    h("dl", { class: "facts", id: "s-info" }, facts.map(f => [h("dt", null, f[0]), h("dd", null, f[1])])));
  if (info.dev_data) {
    s.keep = h("input", { type: "number", id: "s-keep", min: "0", step: "1", value: "14", class: "short" });
    root.append(h("h3", null, t("s_backup_title")),
      h("p", { class: "hint" }, t("s_backup_hint", { folder: info.dev_data + "/backups" })),
      h("div", { class: "row" }, field(t("s_keep"), s.keep), button(t("s_backup"), backup, { id: "s-backup" })),
      h("h3", null, t("s_token_title")),
      h("p", { class: "hint" }, t("s_token_hint", { file: info.token_file })),
      h("div", { class: "row" }, button(t("s_new_token"), newToken, { id: "s-new-token" })));
  } else {
    root.append(h("h3", null, t("s_live_title")), h("p", null, t("s_live_text")));
  }
  root.append(s.box, h("h3", null, t("s_signin_title")),
    h("p", { class: "hint" }, t("s_signin_hint")),
    s.signin,
    h("h4", null, t("s_mail_title")),
    s.last,
    h("div", { class: "scroll short" }, s.log),
    h("div", { class: "row" }, button(t("s_check"), check, { id: "s-check" }), h("span", { class: "hint" }, t("s_check_hint"))),
    h("div", { class: "row" }, field(t("s_test_to"), s.to), button(t("s_test"), testMail, { id: "s-test-mail" })),
    s.signinBox,
    h("h3", null, t("s_features_title")),
    h("p", { class: "hint" }, t("s_features_hint")),
    h("div", { class: "scroll" }, s.features));
}

// Whether the API reaches LINE and the mailer, without signing anyone in or sending a mail.
async function check() {
  if (busy()) return;
  working(s.signinBox);
  answer(s.signinBox, await post("signin", { action: "check" }), { title: t("s_check_title") });
}

async function testMail() {
  if (busy()) return;
  const to = s.to.value.trim();
  if (!to) {
    refuse(s.signinBox, t("s_test_need"));
    s.to.focus();
    return;
  }
  working(s.signinBox);
  answer(s.signinBox, await post("signin", { action: "test-mail", to: to }), { title: t("s_test_title", { to: to }) });
  await loadSignin();
}

async function backup() {
  if (busy()) return;
  const keep = Number(s.keep.value);
  if (!(keep >= 0) || Math.floor(keep) !== keep) {
    refuse(s.box, t("s_need_days"));
    return;
  }
  working(s.box);
  answer(s.box, await post("backup", { keep: keep }), { title: t("s_backup_answer") });
}

async function newToken() {
  if (busy()) return;
  if (!(await ask(t("s_token_q"), { go: t("s_token_go"), note: t("s_token_note") }))) return;
  working(s.box);
  answer(s.box, await post("new-token", {}), { title: t("s_token_answer") });
}

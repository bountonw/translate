// Site: what review.py admin works against, the backup of the dev data and a new dev admin token, and the
// features with their settings. The live site's backups and token are made on the droplet.
import { post, busy } from "./api.js";
import { h, button, field, fill, td, answer, ask, refuse, working } from "./ui.js";
import { t } from "./words.js";
import { state, features } from "./shared.js";

const s = {};
let built = false;

export async function show(root) {
  if (!built) {
    build(root);
    built = true;
  }
  const list = await features();
  const rows = [];
  list.forEach(f => Object.keys(f.settings || {}).forEach(name => {
    const x = f.settings[name];
    const shown = x.type === "bool" ? (x["default"] ? t("is_on") : t("is_off")) : String(x["default"]);
    rows.push(h("tr", null, td(f.name, "name"), td(f.name + "." + name), td(x.type), td(shown), td(x.help || "")));
  }));
  fill(s.features, [t("s_col_feature"), t("s_col_setting"), t("s_col_type"), t("s_col_default"), t("s_col_help")], rows);
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
  root.append(s.box, h("h3", null, t("s_features_title")),
    h("p", { class: "hint" }, t("s_features_hint")),
    h("div", { class: "scroll" }, s.features));
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

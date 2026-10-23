"""The admin routes of accounts, mixed into the App of server/app.py: the sign-in settings and the mailer, the
browsers signed in (session), the identities readers sign in with, the requests to read, and general links.

Each route answers through the SSH tunnel with the admin token, as every route under /api/admin/. The
commands of review.py and the admin page are built on them (README.md, "Admin routes").
"""
import json
import secrets
import sqlite3

from . import db
from .auth import SignInFailed, bind, general_state, http
from .common import ADMIN_LIMIT, HTTPError, bool_field, id_list
from .mail import address, both, describe, subject

BATCH_MOST = 2000


def session_json(r, now):
    return {"id": r["id"], "reader": r["account"], "name": r["name"], "via": r["via"],
            "identity": {"id": r["identity"], "provider": r["provider"], "display": r["display"]}
            if r["identity"] is not None and r["provider"] else None,
            "agent": r["agent"], "created": r["created"], "last_seen": r["last_seen"], "expires": r["expires"],
            "ended": r["ended"], "ended_by": r["ended_by"], "active": r["ended"] is None and r["expires"] > now}


SESSIONS_SQL = ("SELECT s.*, r.name, i.provider, i.display FROM session s JOIN reader r ON r.id = s.account"
                " LEFT JOIN identity i ON i.id = s.identity")
REQUESTS_SQL = ("SELECT q.*, t.name AS group_name, r.name AS reader_name FROM access_request q"
                " LEFT JOIN reader_group t ON t.id = q.grp LEFT JOIN reader r ON r.id = q.account")
LINKS_SQL = ("SELECT g.*, t.name AS group_name, (SELECT COUNT(*) FROM access_request q WHERE q.general_link = g.id"
             " AND q.decided IS NULL) AS waiting FROM general_link g JOIN reader_group t ON t.id = g.grp")


def request_json(r):
    return {"id": r["id"], "provider": r["provider"], "display": r["display"], "created": r["created"],
            "group": r["group_name"], "general_link": r["general_link"], "decided": r["decided"],
            "decision": r["decision"], "reader": r["account"], "name": r["reader_name"]}


def link_json(r):
    return {"id": r["id"], "group": r["group_name"], "group_id": r["grp"], "created": r["created"],
            "expires": r["expires"], "uses": r["uses"], "uses_most": r["uses_most"], "active": bool(r["active"]),
            "stopped": r["stopped"], "state": general_state(r), "waiting": r["waiting"]}


class Accounts:
    """The admin routes of accounts. Needs SignIn (server/auth.py) and People (server/people.py)."""

    # ---------- the sign-in settings and the mailer ----------

    def admin_auth_status(self, req):
        """GET /api/admin/auth: the sign-in routes switched on, the settings of config.json without any secret,
        the last mails sent and their results, the last LINE sign-in that came back, and two counts: requests
        waiting for the translator and browsers signed in."""
        a = self.auth
        conn = req.conn
        log = [{"at": r["at"], "kind": r["kind"], "provider": r["provider"], "ok": bool(r["ok"]),
                "detail": r["detail"]} for r in conn.execute("SELECT * FROM mail_log ORDER BY id DESC LIMIT 20")]
        line = None
        if a.line:
            line = {k: a.line[k] for k in ("channel_id", "issuer", "authorize_url", "token_url", "verify_url")}
            line["callback"] = self.callback_url(req)
        return 200, {
            "routes": a.routes, "require_identity": a.require_identity, "session_days": a.session_days,
            "line": line, "email": a.email, "mail": describe(a.mail),
            "notify": dict(a.notify, on=bool(a.notify["email"] and self.mailer)), "invite": dict(a.invite),
            "last_mail": log[0] if log else None, "mail_log": log, "last_line": self.last_line,
            "requests_open": conn.execute("SELECT COUNT(*) FROM access_request WHERE decided IS NULL").fetchone()[0],
            "sessions_active": conn.execute("SELECT COUNT(*) FROM session WHERE ended IS NULL AND expires > ?",
                                            (db.now(),)).fetchone()[0],
            "dev": self.dev}

    def admin_auth_check(self, req):
        """POST /api/admin/auth/check: whether the API reaches LINE (its OpenID configuration and its token
        endpoint) and the mail provider, without signing anyone in or sending a mail. {line, mail}, each
        {on, ok, detail}; ok is null for a route that is off."""
        out = {}
        if self.auth.line:
            line = self.auth.line
            try:
                status, _ = http("GET", line["issuer"] + "/.well-known/openid-configuration")
                http("GET", line["token_url"])
                ok = status == 200
                detail = (f"The API reached {line['issuer']} and {line['token_url']}." if ok else
                          f"{line['issuer']} answered {status} for its OpenID configuration.")
            except SignInFailed as e:
                ok, detail = False, str(e) + " Check the network settings of deploy/review.service."
            out["line"] = {"on": True, "ok": ok, "detail": detail}
        else:
            out["line"] = {"on": False, "ok": None, "detail": "Sign-in with LINE is off: config.json has no auth.line."}
        if self.mailer is not None:
            ok, detail = self.mailer.check(self.auth.notify["email"] or None)
            out["mail"] = {"on": True, "ok": ok, "detail": detail}
        else:
            out["mail"] = {"on": False, "ok": None, "detail": "No mailer: config.json has no \"mail\"."}
        return 200, out

    def admin_test_mail(self, req):
        """POST /api/admin/auth/test-mail {to}: send a test mail now. {sent, to, detail}; the send is recorded
        in the mail log, which GET /api/admin/auth shows."""
        to = address(req.json().get("to"))
        if not to:
            raise HTTPError(400, "bad_email", "to must be an email address, as name@example.com.")
        if self.mailer is None:
            raise HTTPError(409, "no_mailer", "No mailer is set: add \"mail\" to config.json (README.md, "
                            "\"Sign-in settings\").")
        sent, detail = self.send_mail("test", to, "A test mail from the proofreading site",
                                      "This is a test mail of the proofreading site. It reached you, so the site "
                                      "can send sign-in codes and notes to the translator.")
        return 200, {"sent": sent, "to": to, "detail": detail}

    # ---------- browsers signed in ----------

    def admin_sessions(self, req):
        """GET /api/admin/sessions?reader=ID&all=1: the browsers signed in now, of every reader or of one; all=1
        adds those that ended or expired in the last 90 days. Newest visit first."""
        q = req.query
        where, args = [], []
        if q.get("reader"):
            if not q["reader"].isdigit():
                raise HTTPError(400, "bad_field", "reader must be a reader's number.")
            where.append("s.account = ?")
            args.append(int(q["reader"]))
        now = db.now()
        if q.get("all") not in ("1", "true", "yes"):
            where.append("s.ended IS NULL AND s.expires > ?")
            args.append(now)
        sql = SESSIONS_SQL + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY s.last_seen DESC, s.id"
        return 200, {"sessions": [session_json(r, now) for r in req.conn.execute(sql, args)]}

    def admin_end_sessions(self, req):
        """PATCH /api/admin/sessions {ids?, readers?}: end the sessions named, or every session of the readers
        named; those browsers are signed out at their next request. {ended, missing, unchanged, sessions}:
        unchanged lists sessions that had ended or expired already."""
        data = req.json(ADMIN_LIMIT)
        ids = id_list(data.get("ids", []), "ids", BATCH_MOST)
        readers = id_list(data.get("readers", []), "readers", BATCH_MOST)
        if not ids and not readers:
            raise HTTPError(400, "bad_field", "Name the sessions (ids) or the readers (readers) to sign out.")
        known = {r[0] for r in req.conn.execute("SELECT id FROM reader")}
        absent = [str(r) for r in readers if r not in known]
        if absent:
            raise HTTPError(404, "no_reader", f"No reader with the number {', '.join(absent)}.")
        now = db.now()
        with db.tx(req.conn):
            rows = req.conn.execute(
                "SELECT id, ended, expires FROM session WHERE id IN (SELECT value FROM json_each(?))"
                " OR (account IN (SELECT value FROM json_each(?)) AND ended IS NULL AND expires > ?)",
                (json.dumps(ids), json.dumps(readers), now)).fetchall()
            live = [r["id"] for r in rows if r["ended"] is None and r["expires"] > now]
            req.conn.executemany("UPDATE session SET ended = ?, ended_by = 'translator' WHERE id = ?",
                                 [(now, i) for i in live])
        found = {r["id"] for r in rows}
        touched = sorted(found)
        return 200, {"ended": sorted(live), "missing": [i for i in ids if i not in found],
                     "unchanged": sorted(found - set(live)),
                     "sessions": [session_json(r, db.now()) for r in req.conn.execute(
                         SESSIONS_SQL + " WHERE s.id IN (SELECT value FROM json_each(?)) ORDER BY s.id",
                         (json.dumps(touched),))]}

    # ---------- identities ----------

    def identities_json(self, conn, where="", args=()):
        now = db.now()
        return [{"id": r["id"], "reader": r["account"], "name": r["name"], "provider": r["provider"],
                 "display": r["display"], "created": r["created"], "last_used": r["last_used"],
                 "sessions": r["sessions"]}
                for r in conn.execute(
                    "SELECT i.*, r.name, (SELECT COUNT(*) FROM session s WHERE s.identity = i.id AND s.ended IS NULL"
                    " AND s.expires > ?) AS sessions FROM identity i JOIN reader r ON r.id = i.account" + where
                    + " ORDER BY r.name COLLATE NOCASE, i.id", (now, *args))]

    def admin_identities(self, req):
        """GET /api/admin/identities?reader=ID: the LINE accounts and email addresses readers sign in with,
        each with its reader and the browsers it signed in that are signed in now."""
        reader = req.query.get("reader")
        if reader and not reader.isdigit():
            raise HTTPError(400, "bad_field", "reader must be a reader's number.")
        return 200, {"identities": self.identities_json(req.conn, " WHERE i.account = ?" if reader else "",
                                                        (int(reader),) if reader else ())}

    def admin_add_identity(self, req):
        """POST /api/admin/identities {reader, provider: "email", address}: the reader can sign in with a code
        sent to this address, without the link. A LINE account is tied only by signing in with it."""
        data = req.json()
        rid = data.get("reader")
        if type(rid) is not int:
            raise HTTPError(400, "bad_field", "reader must be a reader's number.")
        self.reader_json(req.conn, rid)
        if data.get("provider", "email") != "email":
            raise HTTPError(400, "bad_field", "Only an email address can be added here; a LINE account is tied "
                            "when the reader signs in with LINE.")
        email = address(data.get("address"))
        if not email:
            raise HTTPError(400, "bad_email", "address must be an email address, as name@example.com.")
        with db.tx(req.conn):
            held = req.conn.execute("SELECT i.account, r.name FROM identity i JOIN reader r ON r.id = i.account"
                                    " WHERE i.provider = 'email' AND i.subject = ?", (email,)).fetchone()
            if held is not None and held["account"] != rid:
                raise HTTPError(409, "identity_taken", f"The address {email} belongs to {held['name']} (reader "
                                f"{held['account']}).", details={"reader": held["account"], "name": held["name"]})
            if held is None:
                req.conn.execute("INSERT INTO identity (account, provider, subject, display, created)"
                                 " VALUES (?, 'email', ?, ?, ?)", (rid, email, email, db.now()))
        out = self.identities_json(req.conn, " WHERE i.provider = 'email' AND i.subject = ?", (email,))[0]
        return (200 if held is not None else 201), dict(out, added=held is None)

    def admin_remove_identity(self, req, iid):
        """DELETE /api/admin/identities/<id>: the LINE account or address no longer signs in to the reader, and
        the browsers it signed in are signed out. {deleted, reader, name, provider, display, sessions_ended,
        identities_left}."""
        iid = int(iid)
        found = self.identities_json(req.conn, " WHERE i.id = ?", (iid,))
        if not found:
            raise HTTPError(404, "no_identity", "No such identity.")
        ident = found[0]
        with db.tx(req.conn):
            ended = req.conn.execute("UPDATE session SET ended = ?, ended_by = 'unbind' WHERE identity = ? AND ended"
                                     " IS NULL", (db.now(), iid)).rowcount
            req.conn.execute("DELETE FROM identity WHERE id = ?", (iid,))
        left = req.conn.execute("SELECT COUNT(*) FROM identity WHERE account = ?", (ident["reader"],)).fetchone()[0]
        return 200, {"deleted": iid, "reader": ident["reader"], "name": ident["name"], "provider": ident["provider"],
                     "display": ident["display"], "sessions_ended": ended, "identities_left": left}

    # ---------- requests to read ----------

    def admin_requests(self, req):
        """GET /api/admin/requests?state=open|approved|declined|all: the requests made through general links,
        newest first; open (the default) are those waiting for the translator. open counts them."""
        state = req.query.get("state") or "open"
        where = {"open": " WHERE q.decided IS NULL", "approved": " WHERE q.decision = 'approved'",
                 "declined": " WHERE q.decision = 'declined'", "all": ""}.get(state)
        if where is None:
            raise HTTPError(400, "bad_field", "state must be open, approved, declined or all.")
        rows = req.conn.execute(REQUESTS_SQL + where + " ORDER BY q.id DESC").fetchall()
        n = req.conn.execute("SELECT COUNT(*) FROM access_request WHERE decided IS NULL").fetchone()[0]
        return 200, {"requests": [request_json(r) for r in rows], "open": n}

    def open_request(self, conn, qid):
        row = conn.execute(REQUESTS_SQL + " WHERE q.id = ?", (qid,)).fetchone()
        if row is None:
            raise HTTPError(404, "no_request", "No such request.")
        if row["decided"]:
            raise HTTPError(409, "request_decided", f"Request {qid} was {row['decision']} already.")
        return row

    def admin_approve_request(self, req, qid):
        """POST /api/admin/requests/<id>/approve {name?, grants?, groups?, english?, settings?, reader?}: the
        person becomes a reader who signs in with the identity of the request. With reader (a number), the
        identity is tied to that reader instead. Without grants and groups, the reader joins the group of the
        general link. {request, reader}."""
        qid = int(qid)
        data = req.json(ADMIN_LIMIT)
        row = self.open_request(req.conn, qid)
        stamp = db.now()
        held = req.conn.execute("SELECT i.account, r.name FROM identity i JOIN reader r ON r.id = i.account"
                                " WHERE i.provider = ? AND i.subject = ?", (row["provider"], row["subject"])).fetchone()

        def mark(conn, rid):
            bind(conn, rid, row["provider"], row["subject"], row["display"], stamp, used=False)
            done = conn.execute("UPDATE access_request SET decided = ?, decision = 'approved', account = ? WHERE id = ?"
                                " AND decided IS NULL", (stamp, rid, qid)).rowcount
            if not done:
                raise HTTPError(409, "request_decided", f"Request {qid} was decided already.")

        target = data.get("reader")
        if held is not None and held["account"] != target:
            raise HTTPError(409, "identity_taken", f"This {'LINE account' if row['provider'] == 'line' else 'address'} "
                            f"belongs to {held['name']} (reader {held['account']}) already. Approve it with reader "
                            f"{held['account']}, or decline it.", details={"reader": held["account"], "name": held["name"]})
        if target is not None:
            if type(target) is not int:
                raise HTTPError(400, "bad_field", "reader must be a reader's number.")
            self.reader_json(req.conn, target)
            with db.tx(req.conn):
                mark(req.conn, target)
            rid = target
        else:
            fields = {k: data[k] for k in ("grants", "groups", "english", "settings") if k in data}
            fields["name"] = data.get("name") or row["display"]
            if not fields.get("grants") and not fields.get("groups"):
                if not row["group_name"]:
                    raise HTTPError(400, "no_group", f"The group of request {qid}'s general link was removed. Give "
                                    f"chapters or a group: review.py request approve {qid} --grant SC01, or --group "
                                    "GROUP.", details={"request": qid})
                fields["groups"] = [row["group_name"]]
            try:
                ((rid, _),) = self.create_readers(req, [fields], bind_to=mark)
            except sqlite3.IntegrityError:
                raise HTTPError(409, "identity_taken", "This identity belongs to another reader already.")
        if row["provider"] == "email":
            self.send_later("approved", row["subject"], subject("approved_subject"),
                            both("approved_body", url=self.base_url(req) + "/"))
        out = request_json(req.conn.execute(REQUESTS_SQL + " WHERE q.id = ?", (qid,)).fetchone())
        return 200, {"request": out, "reader": self.reader_json(req.conn, rid)}

    def admin_decline_request(self, req, qid):
        """POST /api/admin/requests/<id>/decline: the request is declined, and the same identity cannot ask
        again until the request is forgotten (DELETE). {request}."""
        qid = int(qid)
        self.open_request(req.conn, qid)
        with db.tx(req.conn):
            req.conn.execute("UPDATE access_request SET decided = ?, decision = 'declined' WHERE id = ? AND decided"
                             " IS NULL", (db.now(), qid))
        return 200, {"request": request_json(req.conn.execute(REQUESTS_SQL + " WHERE q.id = ?", (qid,)).fetchone())}

    def admin_forget_request(self, req, qid):
        """DELETE /api/admin/requests/<id>: the request is removed, decided or not, so its identity may ask
        again. {deleted, display, provider}."""
        qid = int(qid)
        row = req.conn.execute("SELECT * FROM access_request WHERE id = ?", (qid,)).fetchone()
        if row is None:
            raise HTTPError(404, "no_request", "No such request.")
        with db.tx(req.conn):
            req.conn.execute("DELETE FROM access_request WHERE id = ?", (qid,))
        return 200, {"deleted": qid, "display": row["display"], "provider": row["provider"]}

    # ---------- general links ----------

    def admin_general_links(self, req):
        """GET /api/admin/general-links?group=G: every general link, or a group's, newest first, each with its
        state (open, off, expired or full), its uses and the requests through it that still wait."""
        where, args = "", ()
        if req.query.get("group"):
            (gid,) = self.group_ids(req.conn, [req.query["group"]])
            where, args = " WHERE g.grp = ?", (gid,)
        return 200, {"links": [link_json(r) for r in req.conn.execute(LINKS_SQL + where + " ORDER BY g.id DESC",
                                                                      args)]}

    def admin_new_general_link(self, req):
        """POST /api/admin/general-links {group, days?, uses?}: a new general link of the group, which stops the
        group's link before it. days (invite.general_days, 90) and uses (invite.general_uses, 100) bound it.
        201 with the link and its code, shown only this once, and replaced, the links it stopped."""
        data = req.json()
        if not isinstance(data.get("group"), str):
            raise HTTPError(400, "bad_field", "group must be a group's name.")
        (gid,) = self.group_ids(req.conn, [data["group"]])
        days = data.get("days", self.auth.invite["general_days"])
        uses = data.get("uses", self.auth.invite["general_uses"])
        for name, value, most in (("days", days, 3650), ("uses", uses, 100000)):
            if type(value) is not int or not 1 <= value <= most:
                raise HTTPError(400, "bad_field", f"{name} must be a whole number from 1 to {most}.")
        code = secrets.token_urlsafe(24)
        stamp = db.now()
        with db.tx(req.conn):
            replaced = [r[0] for r in req.conn.execute("SELECT id FROM general_link WHERE grp = ? AND active = 1",
                                                       (gid,))]
            req.conn.execute("UPDATE general_link SET active = 0, stopped = ? WHERE grp = ? AND active = 1",
                             (stamp, gid))
            cur = req.conn.execute("INSERT INTO general_link (grp, code_hash, created, expires, uses_most)"
                                   " VALUES (?, ?, ?, ?, ?)", (gid, db.sha256(code), stamp, db.later(stamp, days), uses))
        row = req.conn.execute(LINKS_SQL + " WHERE g.id = ?", (cur.lastrowid,)).fetchone()
        return 201, dict(link_json(row), code=code, link=self.link(req, code, "join"), replaced=replaced)

    def admin_edit_general_link(self, req, lid):
        """PATCH /api/admin/general-links/<id> {active: false}: the link stops taking requests. A stopped link
        never opens again; a new one does (POST). {link..., changed}."""
        lid = int(lid)
        row = req.conn.execute(LINKS_SQL + " WHERE g.id = ?", (lid,)).fetchone()
        if row is None:
            raise HTTPError(404, "no_link", "No such general link.")
        if bool_field(req.json(), "active"):
            raise HTTPError(400, "bad_field", "A general link can only be switched off. Make a new one to take "
                            "requests again.")
        with db.tx(req.conn):
            changed = req.conn.execute("UPDATE general_link SET active = 0, stopped = ? WHERE id = ? AND active = 1",
                                       (db.now(), lid)).rowcount
        row = req.conn.execute(LINKS_SQL + " WHERE g.id = ?", (lid,)).fetchone()
        return 200, dict(link_json(row), changed=bool(changed))

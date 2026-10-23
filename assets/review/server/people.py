"""The admin routes for readers and groups, mixed into the App of server/app.py.

A reader has a link (only its hash is stored), a name, own grants, own
settings and any number of groups. A group has a name, its own grants and
settings, and can be switched off. The chapters a reader can open are the
published chapters covered by the reader's own grants or by the grants of any
group the reader belongs to that is switched on; a revoked reader opens
nothing. Every list is built with one query per table, so the cost grows with
the number of rows, never with readers times groups.

The site counts the devices that open each link (reader_device, filled by
server/app.py, device_state): a link works on the first limits.devices_per_link
devices that open it, and a further device waits until the translator approves
it here. The reader list gives each reader's counts for their current link.
"""
import json
import secrets
import sqlite3

from . import db, specs
from .common import (ADMIN_LIMIT, GROUP_NAME_RE, NAME_LIMIT, WAITING_MOST, HTTPError, bool_field, clean, id_list,
                     name_key, reader_name)

BATCH_MOST = 2000


def labels(rows):
    """Grant rows (book, chapter) as sorted labels: the whole book first, then its chapters."""
    return [specs.grant_label(b, c) for b, c in sorted(rows, key=lambda g: (g[0], g[1] != "*", g[1]))]


def parse_grants(value):
    if not isinstance(value, list) or not all(isinstance(g, str) for g in value):
        raise HTTPError(400, "bad_grants", "grants must be a list such as [\"SC01-08\"] or [\"SC\"].")
    out = []
    try:
        for g in value:
            out.extend(specs.parse_grant(g))
    except specs.SpecError as e:
        raise HTTPError(400, "bad_grants", str(e))
    return list(dict.fromkeys(out))


def ids_in(column, ids):
    """A WHERE clause and its argument limiting column to ids, or nothing for every row."""
    if ids is None:
        return "", ()
    return f" WHERE {column} IN (SELECT value FROM json_each(?))", (json.dumps(list(ids)),)


class People:
    """Readers and groups. Needs self.registry (server/features), self.public_url and self.data."""

    # ---------- shared ----------

    def link(self, req, code):
        base = self.public_url or db.read_config(self.data).get("public_url")
        if not base:
            scheme = req.header("X-Forwarded-Proto") or req.environ.get("wsgi.url_scheme", "http")
            base = f"{scheme}://{req.header('Host') or 'localhost'}"
        return f"{base.rstrip('/')}/#k={code}"

    def settings_field(self, data):
        """settings from a request, with english (true or false) as a shortcut for english.on."""
        values = dict(data.get("settings") or {}) if isinstance(data.get("settings") or {}, dict) else None
        if values is None:
            raise HTTPError(400, "bad_setting", 'settings must be an object such as {"english.on": true}.')
        if "english" in data:
            values["english.on"] = bool_field(data, "english")
        try:
            return self.registry.check(values)
        except KeyError as e:
            raise HTTPError(400, "unknown_setting", f"No feature has the setting {e.args[0]}. "
                            f"Settings: {', '.join(sorted(self.registry.settings)) or 'none'}.")
        except ValueError as e:
            raise HTTPError(400, "bad_setting", str(e))

    def group_ids(self, conn, names):
        """Group names to ids; an unknown name is 400 no_group."""
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            raise HTTPError(400, "bad_field", "groups must be a list of group names.")
        known = {r[1].casefold(): r[0] for r in conn.execute("SELECT id, name FROM reader_group")}
        missing = [n for n in names if n.casefold() not in known]
        if missing:
            raise HTTPError(400, "no_group", f"No group named {', '.join(missing)}. Run: review.py groups")
        return list(dict.fromkeys(known[n.casefold()] for n in names))

    @staticmethod
    def write_settings(conn, table, owner_col, owner, settings):
        conn.executemany(
            f"INSERT INTO {table} ({owner_col}, name, value) VALUES (?, ?, ?)"
            f" ON CONFLICT ({owner_col}, name) DO UPDATE SET value = excluded.value",
            [(owner, k, json.dumps(v)) for k, v in settings.items()])

    # ---------- readers: reading ----------

    def groups_data(self, conn):
        """{group id: {name, active, grants: [(book, chapter)], settings}} for every group."""
        groups = {r[0]: {"id": r[0], "name": r[1], "active": bool(r[2]), "created": r[3], "grants": [],
                         "settings": {}} for r in conn.execute("SELECT id, name, active, created FROM reader_group")}
        for g, book, ch in conn.execute("SELECT grp, book, chapter FROM group_grant"):
            groups[g]["grants"].append((book, ch))
        for g, name, value in conn.execute("SELECT grp, name, value FROM group_setting"):
            groups[g]["settings"][name] = json.loads(value)
        return groups

    def readers_json(self, conn, ids=None):
        """Readers as the admin routes show them, in name order; ids limits the list. books names the books
        of which the reader can open a published chapter now: none for a revoked reader."""
        groups = self.groups_data(conn)
        published = {}
        for book, ch in conn.execute("SELECT book, id FROM chapter WHERE published = 1"):
            published.setdefault(book, set()).add(ch)

        def rows(sql, column):
            where, args = ids_in(column, ids)
            return conn.execute(sql.format(where=where), args)

        out = {r[0]: {"id": r[0], "name": r[1], "active": bool(r[2]), "created": r[3], "grants": [],
                      "groups": [], "settings": {}, "comments": 0, "last_active": None}
               for r in rows("SELECT id, name, active, created FROM reader{where} ORDER BY name", "id")}
        for rid, book, ch in rows('SELECT reader, book, chapter FROM "grant"{where}', "reader"):
            out[rid]["grants"].append((book, ch))
        for rid, gid in rows("SELECT reader, grp FROM group_member{where}", "reader"):
            out[rid]["groups"].append(gid)
        for rid, name, value in rows("SELECT reader, name, value FROM reader_setting{where}", "reader"):
            out[rid]["settings"][name] = json.loads(value)
        for rid, n, last in rows("SELECT reader, COUNT(*), MAX(updated) FROM comment{where} GROUP BY reader", "reader"):
            out[rid]["comments"], out[rid]["last_active"] = n, last
        for sql in ("SELECT reader, MAX(updated) FROM place{where} GROUP BY reader",
                    "SELECT reader, MAX(at) FROM finished{where} GROUP BY reader"):
            for rid, last in rows(sql, "reader"):
                if last and (out[rid]["last_active"] or "") < last:
                    out[rid]["last_active"] = last
        for r in out.values():
            r["devices"] = {"total": 0, "ok": 0, "waiting": 0, "removed": 0}
        # The devices of each reader's current link only: a new link starts a new count.
        for rid, state, n in rows("SELECT d.reader, d.state, COUNT(*) FROM reader_device d JOIN reader x"
                                  " ON x.id = d.reader AND x.code_hash = d.link{where} GROUP BY d.reader, d.state",
                                  "d.reader"):
            out[rid]["devices"][state] = n
            out[rid]["devices"]["total"] += n
        # A link with WAITING_MOST devices waiting refuses further new devices unrecorded (server/app.py,
        # device_state): it was tried on too many devices, and the reader needs a new link.
        for r in out.values():
            r["devices"]["full"] = r["devices"]["waiting"] >= WAITING_MOST
        result = []
        for r in out.values():
            mine = [groups[g] for g in r["groups"]]
            on = [g for g in mine if g["active"]]
            effective = self.registry.resolve(r["settings"], [kv for g in on for kv in g["settings"].items()])
            reach = set(r["grants"]).union(*[g["grants"] for g in on]) if r["active"] else set()
            books = {b for b, c in reach if c in published.get(b, ()) or (c == "*" and published.get(b))}
            result.append(dict(r, grants=labels(r["grants"]), groups=sorted(g["name"] for g in mine),
                               effective=effective, english=bool(effective.get("english.on")),
                               books=sorted(books)))
        return result

    def reader_json(self, conn, rid):
        found = self.readers_json(conn, [rid])
        if not found:
            raise HTTPError(404, "no_reader", "No such reader.")
        return found[0]

    def admin_readers(self, req):
        """Every reader, or those matching ?name= (the whole name), ?contains= (part of the name), ?code_hash=
        (the SHA-256 of a link's code), ?group=, ?book=, ?idle=DAYS (0: never active), ?revoked=1, ?devices=1
        (a link opened on more devices than limits.devices_per_link, or with a device waiting for approval)."""
        q = req.query
        total = req.conn.execute("SELECT COUNT(*) FROM reader").fetchone()[0]
        ids = None
        if q.get("code_hash"):
            ids = [r[0] for r in req.conn.execute("SELECT id FROM reader WHERE code_hash = ?",
                                                  (q["code_hash"].lower(),))]
        readers = self.readers_json(req.conn, ids)
        if q.get("name"):
            readers = [r for r in readers if name_key(r["name"]) == name_key(q["name"])]
        if q.get("contains"):
            part = " ".join(q["contains"].split()).casefold()
            readers = [r for r in readers if part in " ".join(r["name"].split()).casefold()]
        if q.get("group"):
            self.group_ids(req.conn, [q["group"]])
            readers = [r for r in readers if q["group"].casefold() in (g.casefold() for g in r["groups"])]
        if q.get("book"):
            readers = [r for r in readers if q["book"].upper() in r["books"]]
        if q.get("revoked") in ("1", "true", "yes"):
            readers = [r for r in readers if not r["active"]]
        if q.get("devices") in ("1", "true", "yes"):
            most = self.limits["devices_per_link"]
            readers = [r for r in readers if r["devices"]["total"] > most or r["devices"]["waiting"]]
        if q.get("idle"):
            if not q["idle"].isdigit() or len(q["idle"]) > 5:
                raise HTTPError(400, "bad_field", "idle must be a number of days.")
            days = int(q["idle"])
            since = db.ago(days) if days else None
            readers = [r for r in readers if not r["last_active"] or (since and r["last_active"] < since)]
        return 200, {"readers": readers, "total": total, "devices_per_link": self.limits["devices_per_link"]}

    # ---------- readers: writing ----------

    def reader_fields(self, conn, data, creating):
        """The fields of one reader's create or change, checked: name, active, grants, groups, settings."""
        if not isinstance(data, dict):
            raise HTTPError(400, "bad_field", "Each reader must be an object.")
        out = {}
        if creating or "name" in data:
            out["name"] = reader_name(clean(data.get("name"), "name", NAME_LIMIT, True))
        if "active" in data:
            out["active"] = bool_field(data, "active")
        if creating or "grants" in data:
            out["grants"] = parse_grants(data.get("grants", []))
        if creating or "groups" in data:
            out["groups"] = self.group_ids(conn, data.get("groups", []))
        out["settings"] = self.settings_field(data)
        return out

    def write_reader(self, conn, rid, f):
        if "name" in f:
            conn.execute("UPDATE reader SET name = ? WHERE id = ?", (f["name"], rid))
        if "active" in f:
            conn.execute("UPDATE reader SET active = ? WHERE id = ?", (int(f["active"]), rid))
        if "grants" in f:
            conn.execute('DELETE FROM "grant" WHERE reader = ?', (rid,))
            conn.executemany('INSERT INTO "grant" (reader, book, chapter) VALUES (?, ?, ?)',
                             [(rid, b, c) for b, c in f["grants"]])
        if "groups" in f:
            conn.execute("DELETE FROM group_member WHERE reader = ?", (rid,))
            conn.executemany("INSERT INTO group_member (reader, grp) VALUES (?, ?)", [(rid, g) for g in f["groups"]])
        self.write_settings(conn, "reader_setting", "reader", rid, f["settings"])

    def create_readers(self, req, rows):
        """Check every row, then create them all in one transaction. Returns [(id, code)]."""
        fields, problems, seen, taken_names = [], [], set(), 0
        # A name already taken is refused whatever its case and its spaces: "Mali  Boon" is "Mali Boon".
        holders = {name_key(r[0]): r[0] for r in req.conn.execute("SELECT name FROM reader")}
        taken = set(holders)
        for i, row in enumerate(rows, 1):
            where = f"Row {i}: " if len(rows) > 1 else ""
            try:
                f = self.reader_fields(req.conn, row, True)
            except HTTPError as e:
                if len(rows) == 1:
                    raise
                problems.append(where + e.message)
                continue
            key = name_key(f["name"])
            if key in taken:
                problems.append(f"{where}A reader named {holders[key]} already exists.")
                taken_names += 1
            elif key in seen:
                problems.append(f"{where}The name {f['name']} appears twice.")
            seen.add(key)
            fields.append(f)
        if problems:
            status, code = (409, "name_taken") if taken_names == len(problems) else (400, "bad_readers")
            raise HTTPError(status, code, " ".join(problems[:20]) + (
                f" And {len(problems) - 20} more." if len(problems) > 20 else ""), details={"problems": problems})
        made = []
        try:
            with db.tx(req.conn):
                stamp = db.now()
                for f in fields:
                    code = secrets.token_urlsafe(24)
                    cur = req.conn.execute("INSERT INTO reader (name, code_hash, active, created) VALUES (?, ?, 1, ?)",
                                           (f["name"], db.sha256(code), stamp))
                    self.write_reader(req.conn, cur.lastrowid, {k: v for k, v in f.items() if k != "name"})
                    made.append((cur.lastrowid, code))
        except sqlite3.IntegrityError:
            raise HTTPError(409, "name_taken", "A reader with one of these names already exists.")
        return made

    def admin_invite(self, req):
        data = req.json(ADMIN_LIMIT)
        (rid, code), = self.create_readers(req, [data])
        return 201, dict(self.reader_json(req.conn, rid), code=code, link=self.link(req, code))

    def admin_invite_batch(self, req):
        """{"readers": [{name, grants, groups, english, settings}]}: all are created, or none."""
        rows = req.json(ADMIN_LIMIT).get("readers")
        if not isinstance(rows, list) or not 1 <= len(rows) <= BATCH_MOST:
            raise HTTPError(400, "bad_field", f"readers must be a list of 1 to {BATCH_MOST} readers.")
        made = self.create_readers(req, rows)
        names = {r["id"]: r["name"] for r in self.readers_json(req.conn, [i for i, _ in made])}
        return 201, {"readers": [{"id": i, "name": names[i], "code": c, "link": self.link(req, c)} for i, c in made]}

    def change_readers(self, req, changes):
        """[(id, fields)] applied in one transaction; returns the readers after. A new name that is another
        reader's name, whatever its case and its spaces, is 409 name_taken."""
        known = {r[0]: r[1] for r in req.conn.execute("SELECT id, name FROM reader")}
        missing = [str(i) for i, _ in changes if i not in known]
        if missing:
            raise HTTPError(404, "no_reader", f"No reader with the number {', '.join(missing)}.")
        names = {i: name_key(n) for i, n in known.items()}
        for rid, f in changes:
            if "name" in f:
                names[rid] = name_key(f["name"])
        renamed = {rid for rid, f in changes if "name" in f}
        for rid in renamed:
            twins = [i for i, k in names.items() if k == names[rid] and i != rid]
            if twins:
                raise HTTPError(409, "name_taken", f"Another reader (number {twins[0]}) has the name "
                                f"{dict(changes)[rid]['name']}, whatever its case and spaces.")
        try:
            with db.tx(req.conn):
                for rid, f in changes:
                    self.write_reader(req.conn, rid, f)
        except sqlite3.IntegrityError:
            raise HTTPError(409, "name_taken", "Another reader has that name.")
        return self.readers_json(req.conn, [i for i, _ in changes])

    def admin_edit_reader(self, req, rid):
        data = req.json(ADMIN_LIMIT)
        rid = int(rid)
        self.reader_json(req.conn, rid)
        self.change_readers(req, [(rid, self.reader_fields(req.conn, data, False))])
        return 200, self.reader_json(req.conn, rid)

    def admin_edit_readers(self, req):
        """{"changes": [{id, active, grants, groups, settings, english}]}: all are applied, or none."""
        changes = req.json(ADMIN_LIMIT).get("changes")
        if not isinstance(changes, list) or not 1 <= len(changes) <= BATCH_MOST:
            raise HTTPError(400, "bad_field", f"changes must be a list of 1 to {BATCH_MOST} changes.")
        parsed = []
        for c in changes:
            rid = c.get("id") if isinstance(c, dict) else None
            if not isinstance(rid, int) or isinstance(rid, bool):
                raise HTTPError(400, "bad_field", "Each change needs the reader's id.")
            parsed.append((rid, self.reader_fields(req.conn, {k: v for k, v in c.items() if k != "id"}, False)))
        return 200, {"readers": self.change_readers(req, parsed)}

    def new_codes(self, req, ids):
        known = {r[0]: r[1] for r in req.conn.execute("SELECT id, name FROM reader")}
        missing = [str(i) for i in ids if i not in known]
        if missing:
            raise HTTPError(404, "no_reader", f"No reader with the number {', '.join(missing)}.")
        out = []
        with db.tx(req.conn):
            for rid in ids:
                code = secrets.token_urlsafe(24)
                req.conn.execute("UPDATE reader SET code_hash = ? WHERE id = ?", (db.sha256(code), rid))
                out.append({"id": rid, "name": known[rid], "code": code, "link": self.link(req, code)})
        return out

    def admin_new_code(self, req, rid):
        rid = int(rid)
        out = self.reader_json(req.conn, rid)
        (new,) = self.new_codes(req, [rid])
        return 200, dict(out, code=new["code"], link=new["link"])

    def admin_new_codes(self, req):
        """{"ids": [...]}: a new link for each reader; every old link stops working."""
        ids = id_list(req.json(ADMIN_LIMIT).get("ids"), "ids", BATCH_MOST)
        if not ids:
            raise HTTPError(400, "bad_field", "ids must name at least one reader.")
        return 200, {"readers": self.new_codes(req, ids)}

    # ---------- groups ----------

    def groups_json(self, conn, only=None):
        groups = self.groups_data(conn)
        members = {}
        for gid, rid, name, active in conn.execute(
                "SELECT m.grp, r.id, r.name, r.active FROM group_member m JOIN reader r ON r.id = m.reader"
                " ORDER BY r.name"):
            members.setdefault(gid, []).append({"id": rid, "name": name, "active": bool(active)})
        out = []
        for g in sorted(groups.values(), key=lambda g: g["name"].casefold()):
            if only is not None and g["id"] != only:
                continue
            out.append(dict(g, grants=labels(g["grants"]), english=bool(g["settings"].get("english.on")),
                            members=members.get(g["id"], [])))
        return out

    def group_json(self, conn, gid):
        found = self.groups_json(conn, gid)
        if not found:
            raise HTTPError(404, "no_group", "No such group.")
        return found[0]

    def group_fields(self, data, creating):
        out = {}
        if creating or "name" in data:
            name = data.get("name")
            if not isinstance(name, str) or not GROUP_NAME_RE.fullmatch(name):
                raise HTTPError(400, "bad_group_name", "A group name is 1 to 40 letters, digits, dots, hyphens or "
                                "underscores, starting with a letter or digit, as Pastors or youth-2026.")
            out["name"] = name
        if "active" in data:
            out["active"] = bool_field(data, "active")
        if creating or "grants" in data:
            out["grants"] = parse_grants(data.get("grants", []))
        out["settings"] = self.settings_field(data)
        return out

    def write_group(self, conn, gid, f):
        if "name" in f:
            conn.execute("UPDATE reader_group SET name = ? WHERE id = ?", (f["name"], gid))
        if "active" in f:
            conn.execute("UPDATE reader_group SET active = ? WHERE id = ?", (int(f["active"]), gid))
        if "grants" in f:
            conn.execute("DELETE FROM group_grant WHERE grp = ?", (gid,))
            conn.executemany("INSERT INTO group_grant (grp, book, chapter) VALUES (?, ?, ?)",
                             [(gid, b, c) for b, c in f["grants"]])
        self.write_settings(conn, "group_setting", "grp", gid, f["settings"])

    def admin_groups(self, req):
        return 200, {"groups": self.groups_json(req.conn)}

    def admin_new_group(self, req):
        f = self.group_fields(req.json(ADMIN_LIMIT), True)
        try:
            with db.tx(req.conn):
                cur = req.conn.execute("INSERT INTO reader_group (name, active, created) VALUES (?, 1, ?)",
                                       (f.pop("name"), db.now()))
                self.write_group(req.conn, cur.lastrowid, f)
        except sqlite3.IntegrityError:
            raise HTTPError(409, "group_taken", "A group with that name already exists.")
        return 201, self.group_json(req.conn, cur.lastrowid)

    def admin_edit_group(self, req, gid):
        gid = int(gid)
        self.group_json(req.conn, gid)
        f = self.group_fields(req.json(ADMIN_LIMIT), False)
        try:
            with db.tx(req.conn):
                self.write_group(req.conn, gid, f)
        except sqlite3.IntegrityError:
            raise HTTPError(409, "group_taken", "Another group has that name.")
        return 200, self.group_json(req.conn, gid)

    def admin_remove_group(self, req, gid):
        """Removes the group, its grants and settings; its members keep their own grants."""
        g = self.group_json(req.conn, int(gid))
        with db.tx(req.conn):
            req.conn.execute("DELETE FROM reader_group WHERE id = ?", (g["id"],))
        return 200, {"deleted": g["id"], "name": g["name"], "members": len(g["members"])}

    def admin_group_members(self, req, gid):
        """{"add": [reader ids], "remove": [reader ids]}. The answer is the group, with what changed: added,
        already (asked to be added but already members), removed, and not_members (asked to be taken out
        but not members), each a list of reader ids."""
        gid = int(gid)
        self.group_json(req.conn, gid)
        data = req.json(ADMIN_LIMIT)
        add = id_list(data.get("add", []), "add", BATCH_MOST)
        remove = id_list(data.get("remove", []), "remove", BATCH_MOST)
        known = {r[0] for r in req.conn.execute("SELECT id FROM reader")}
        missing = [str(i) for i in add + remove if i not in known]
        if missing:
            raise HTTPError(404, "no_reader", f"No reader with the number {', '.join(missing)}.")
        with db.tx(req.conn):
            members = {r[0] for r in req.conn.execute("SELECT reader FROM group_member WHERE grp = ?", (gid,))}
            added = [r for r in add if r not in members]
            removed = [r for r in remove if r in members or r in added]
            req.conn.executemany("INSERT OR IGNORE INTO group_member (reader, grp) VALUES (?, ?)",
                                 [(r, gid) for r in add])
            req.conn.executemany("DELETE FROM group_member WHERE reader = ? AND grp = ?", [(r, gid) for r in remove])
        return 200, dict(self.group_json(req.conn, gid), added=added, already=[r for r in add if r in members],
                         removed=removed, not_members=[r for r in remove if r not in removed])

    def admin_features(self, req):
        return 200, {"features": self.registry.describe()}

    # ---------- devices ----------

    def devices_json(self, conn, where="", args=()):
        """Devices as the admin routes show them: {id, reader, name, state, agent, first_seen, last_seen, changed,
        current}; current is true for a device of the reader's current link."""
        return [{"id": r["id"], "reader": r["reader"], "name": r["name"], "state": r["state"], "agent": r["agent"],
                 "first_seen": r["first_seen"], "last_seen": r["last_seen"], "changed": r["changed"],
                 "current": bool(r["current"])}
                for r in conn.execute(
                    "SELECT d.*, x.name, d.link = x.code_hash AS current FROM reader_device d JOIN reader x"
                    " ON x.id = d.reader" + where + " ORDER BY x.name COLLATE NOCASE, d.id", args)]

    def admin_devices(self, req):
        """GET /api/admin/devices?reader=ID&state=waiting&all=1: the devices of each reader's current link, or of
        one reader, or in one state; all=1 adds the devices of links the reader no longer has."""
        q = req.query
        where, args = [], []
        if q.get("reader"):
            if not q["reader"].isdigit():
                raise HTTPError(400, "bad_field", "reader must be a reader's number.")
            where.append("d.reader = ?")
            args.append(int(q["reader"]))
        if q.get("state"):
            if q["state"] not in ("ok", "waiting", "removed"):
                raise HTTPError(400, "bad_field", "state must be ok, waiting or removed.")
            where.append("d.state = ?")
            args.append(q["state"])
        if q.get("all") not in ("1", "true", "yes"):
            where.append("d.link = x.code_hash")
        return 200, {"devices": self.devices_json(req.conn, " WHERE " + " AND ".join(where) if where else "", args),
                     "devices_per_link": self.limits["devices_per_link"]}

    def admin_set_devices(self, req):
        """PATCH /api/admin/devices {ids, state}: state ok approves the devices, so the link works on them;
        removed stops the link on them, and a removed device waits for approval again if it comes back
        (server/app.py, device_state). The answer is {devices, missing, unchanged}: unchanged lists the devices
        that were in that state already."""
        data = req.json(ADMIN_LIMIT)
        ids = id_list(data.get("ids"), "ids", BATCH_MOST)
        if not ids:
            raise HTTPError(400, "bad_field", "ids must name at least one device.")
        state = data.get("state")
        if state not in ("ok", "removed"):
            raise HTTPError(400, "bad_field", "state must be ok (approve) or removed (remove).")
        with db.tx(req.conn):
            known = {r[0]: r[1] for r in req.conn.execute(
                "SELECT id, state FROM reader_device WHERE id IN (SELECT value FROM json_each(?))", (json.dumps(ids),))}
            req.conn.executemany("UPDATE reader_device SET state = ?, changed = ? WHERE id = ? AND state != ?",
                                 [(state, db.now(), i, state) for i in ids if i in known])
        found = self.devices_json(req.conn, " WHERE d.id IN (SELECT value FROM json_each(?))", (json.dumps(ids),))
        return 200, {"devices": found, "missing": [i for i in ids if i not in known],
                     "unchanged": [i for i in ids if known.get(i) == state]}

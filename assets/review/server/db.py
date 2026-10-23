"""Database and data-directory code for the proofreading site.

The data directory holds review.sqlite3 (SQLite in WAL mode), the admin
token's SHA-256 hash in admin-token.sha256, config.json (the public URL),
and backups/. Nothing in it belongs in the code folder or in git.

schema.sql is version 1 of the database. Every later change is a numbered
entry in MIGRATIONS. init_db brings any database, new or old, to the newest
version in one transaction when the server starts. To change the database,
add an entry with the next number; never edit an entry that has shipped.
Version 3 adds groups (reader_group, group_grant, group_member) and feature
settings (reader_setting, group_setting), and moves each reader's English
into the setting english.on. Version 4 adds each book's title in its own
language (book.title_th). Version 5 keeps every published version of a
chapter (chapter_version), records the version of each chapter a reader last
opened (reader_opened), adds the translator's reply to a comment (comment.reply
and comment.reply_at), and counts each reader's new comments of the last day
(comment_made). Version 6 gives the fields that hold the translation's text
neutral names (book.title, chapter.title, chapter.source, chapter_version.title,
and "text" for each paragraph's text in the stored JSON), adds review rounds
(review_round, comment.round), the devices that use each link (reader_device),
and the comments deleted, for the export of what changed (comment_gone).
Version 7 records the client_id of each comment deleted. Version 8 adds accounts
(server/auth.py): the identities a reader signs in with (identity), the browsers
signed in (session), the sign-ins under way (auth_flow), general links and the
requests made through them (general_link, access_request), the mails sent
(mail_log), and on each reader link_used, first_signin and link_signs_in. Today
every account is a reader, so "account" holds a reader's number. An entry may hold a
Python function beside its SQL, for a change SQL cannot make. init_db refuses a
database of a version newer than its last entry, which newer code made.

The reader's day, for the daily limit and for the dates of commands, runs from
midnight to midnight Thailand time (Asia/Bangkok, UTC+7 all year).

A feature in server/features/ brings its own numbered migrations for its own
tables; init_db applies them after the core ones, in the same transaction,
and feature_schema records the version each feature has reached.
"""
import contextlib
import hashlib
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")
DB_NAME = "review.sqlite3"
TOKEN_HASH = "admin-token.sha256"
TOKEN_FILE = "admin-token"
CONFIG = "config.json"


STAMP = "%Y-%m-%dT%H:%M:%SZ"
# Thailand keeps UTC+7 all year, with no summer time, so a fixed offset is Asia/Bangkok and needs no tz database.
BANGKOK = timezone(timedelta(hours=7), "Asia/Bangkok")


def now():
    """The current UTC time as 2026-10-21T20:30:00Z."""
    return datetime.now(timezone.utc).strftime(STAMP)


def ago(days=0, minutes=0):
    """The UTC time days (and minutes) ago, in the form of now()."""
    return (datetime.now(timezone.utc) - timedelta(days=days, minutes=minutes)).strftime(STAMP)


def parse_stamp(stamp):
    """A time in the form of now() as an aware datetime."""
    return datetime.strptime(stamp, STAMP).replace(tzinfo=timezone.utc)


def stamp_of(when):
    """An aware datetime in the form of now()."""
    return when.astimezone(timezone.utc).strftime(STAMP)


def day_start(stamp):
    """The UTC time, in the form of now(), of the Thailand midnight that began the day holding stamp."""
    local = parse_stamp(stamp).astimezone(BANGKOK)
    return stamp_of(local.replace(hour=0, minute=0, second=0, microsecond=0))


def next_midnight(stamp):
    """The UTC time, in the form of now(), of the Thailand midnight that ends the day holding stamp."""
    local = parse_stamp(stamp).astimezone(BANGKOK)
    return stamp_of(local.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))


def thai_time(stamp):
    """A time in the form of now() as Thailand time: 2026-10-22 07:30."""
    return parse_stamp(stamp).astimezone(BANGKOK).strftime("%Y-%m-%d %H:%M")


def later(stamp, days=0, minutes=0):
    """A time in the form of now(), days (and minutes) after stamp (another such time)."""
    return stamp_of(parse_stamp(stamp) + timedelta(days=days, minutes=minutes))


def seconds_until(stamp):
    """Whole seconds from now until stamp (a time in the form of now()), at least 1."""
    return max(1, int((parse_stamp(stamp) - datetime.now(timezone.utc)).total_seconds()) + 1)


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()


def connect(path):
    """Open the database with foreign keys on and a short busy wait; autocommit outside tx()."""
    conn = sqlite3.connect(path, timeout=5, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


@contextlib.contextmanager
def tx(conn):
    """One write transaction, taken at once so two writers never deadlock."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


COMMENT_COLUMNS = "id, client_id, reader, book, ch, a, kind, quote, text, version, created, updated, processed"


def neutral_paragraphs(paras):
    """Stored paragraphs with the neutral name of version 6: each paragraph's "th" becomes "text", and so does
    the "th" range of each sentence pair; every other key keeps its place."""
    def rename(d):
        return {("text" if k == "th" else k): v for k, v in d.items()} if isinstance(d, dict) else d
    out = []
    for p in paras:
        q = rename(p)
        if isinstance(q, dict) and isinstance(q.get("al"), list):
            q["al"] = [rename(pair) for pair in q["al"]]
        out.append(q)
    return out


def content_hash(title, title_en, paras):
    """The fingerprint publish gives a chapter's content (server/app.py, admin_publish)."""
    return sha256(json.dumps([title, title_en, paras], ensure_ascii=False, sort_keys=True))[:12]


def _migrate_paragraph_text(conn):
    """Version 6: the paragraphs of every chapter and every kept version get the key "text", and each chapter's
    content_hash is worked out again with that key, so publishing the same text again keeps its version."""
    for row in conn.execute("SELECT book, id, title, title_en, paragraphs FROM chapter").fetchall():
        paras = neutral_paragraphs(json.loads(row["paragraphs"]))
        conn.execute("UPDATE chapter SET paragraphs = ?, content_hash = ? WHERE book = ? AND id = ?",
                     (json.dumps(paras, ensure_ascii=False), content_hash(row["title"], row["title_en"], paras),
                      row["book"], row["id"]))
    for row in conn.execute("SELECT book, ch, version, paragraphs FROM chapter_version").fetchall():
        paras = neutral_paragraphs(json.loads(row["paragraphs"]))
        conn.execute("UPDATE chapter_version SET paragraphs = ? WHERE book = ? AND ch = ? AND version = ?",
                     (json.dumps(paras, ensure_ascii=False), row["book"], row["ch"], row["version"]))


# (version, statements). Each entry brings the database from the version before it to this one.
MIGRATIONS = [
    (2, [
        # Comment ids are never used twice, so an id in an export always names the same comment.
        """CREATE TABLE comment_new (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id TEXT NOT NULL,
  reader    INTEGER NOT NULL REFERENCES reader(id) ON DELETE CASCADE,
  book      TEXT NOT NULL,
  ch        TEXT NOT NULL,
  a         TEXT NOT NULL,
  kind      TEXT NOT NULL CHECK (kind IN ('flag', 'wording')),
  quote     TEXT NOT NULL DEFAULT '',
  text      TEXT NOT NULL,
  version   TEXT NOT NULL DEFAULT '',
  created   TEXT NOT NULL,
  updated   TEXT NOT NULL,
  processed INTEGER NOT NULL DEFAULT 0,
  UNIQUE (reader, client_id),
  FOREIGN KEY (book, ch) REFERENCES chapter(book, id)
)""",
        f"INSERT INTO comment_new ({COMMENT_COLUMNS}) SELECT {COMMENT_COLUMNS} FROM comment",
        "DROP TABLE comment",
        "ALTER TABLE comment_new RENAME TO comment",
        "CREATE INDEX comment_by_reader ON comment(reader, book, ch)",
        "CREATE INDEX comment_by_chapter ON comment(book, ch)",
        # The repository files and the revision a chapter was published from.
        "ALTER TABLE chapter ADD COLUMN source_th TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE chapter ADD COLUMN source_en TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE chapter ADD COLUMN source_commit TEXT NOT NULL DEFAULT ''",
    ]),
    (3, [
        # Groups of readers: each has its own grants and settings and can be switched off.
        """CREATE TABLE reader_group (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  name    TEXT NOT NULL UNIQUE COLLATE NOCASE,
  active  INTEGER NOT NULL DEFAULT 1,
  created TEXT NOT NULL
)""",
        """CREATE TABLE group_grant (
  grp     INTEGER NOT NULL REFERENCES reader_group(id) ON DELETE CASCADE,
  book    TEXT NOT NULL,
  chapter TEXT NOT NULL,
  PRIMARY KEY (grp, book, chapter)
)""",
        """CREATE TABLE group_member (
  reader INTEGER NOT NULL REFERENCES reader(id) ON DELETE CASCADE,
  grp    INTEGER NOT NULL REFERENCES reader_group(id) ON DELETE CASCADE,
  PRIMARY KEY (reader, grp)
)""",
        "CREATE INDEX group_member_by_group ON group_member(grp)",
        # Feature settings (server/features/) for one reader or one group: name is feature.setting,
        # as english.on; value is JSON.
        """CREATE TABLE reader_setting (
  reader INTEGER NOT NULL REFERENCES reader(id) ON DELETE CASCADE,
  name   TEXT NOT NULL,
  value  TEXT NOT NULL,
  PRIMARY KEY (reader, name)
)""",
        """CREATE TABLE group_setting (
  grp   INTEGER NOT NULL REFERENCES reader_group(id) ON DELETE CASCADE,
  name  TEXT NOT NULL,
  value TEXT NOT NULL,
  PRIMARY KEY (grp, name)
)""",
        # The migration version each feature's own tables have reached.
        """CREATE TABLE feature_schema (
  feature TEXT PRIMARY KEY,
  version INTEGER NOT NULL
)""",
        # The English setting moves from its column into the settings of the english feature.
        "INSERT INTO reader_setting (reader, name, value) SELECT id, 'english.on', 'true' FROM reader WHERE english != 0",
        "ALTER TABLE reader DROP COLUMN english",
        # The reader list shows when each reader last wrote; this keeps that quick for many comments.
        "CREATE INDEX comment_by_reader_updated ON comment(reader, updated)",
    ]),
    (4, [
        # The book's title in its own language, for the chapter list of a reader with several books.
        # Like the chapter's title_th, it holds the book's language, whatever that is.
        "ALTER TABLE book ADD COLUMN title_th TEXT NOT NULL DEFAULT ''",
    ]),
    (5, [
        # Every published version of a chapter, so a reader can see what changed since the version they
        # last opened, and the earlier wording of a paragraph. published is when the version went out, and
        # seq its place in the chapter's history: 1 for the first, and the next number each time a version
        # is published, also when an earlier one is published again.
        """CREATE TABLE chapter_version (
  book          TEXT NOT NULL,
  ch            TEXT NOT NULL,
  version       TEXT NOT NULL,
  title_th      TEXT NOT NULL,
  title_en      TEXT NOT NULL,
  paragraphs    TEXT NOT NULL,
  source_commit TEXT NOT NULL DEFAULT '',
  published     TEXT NOT NULL,
  seq           INTEGER NOT NULL,
  PRIMARY KEY (book, ch, version),
  FOREIGN KEY (book, ch) REFERENCES chapter(book, id)
)""",
        "INSERT INTO chapter_version (book, ch, version, title_th, title_en, paragraphs, source_commit, published, seq)"
        " SELECT book, id, version, title_th, title_en, paragraphs, source_commit, updated, 1 FROM chapter",
        # The version of each chapter that a reader last opened.
        """CREATE TABLE reader_opened (
  reader  INTEGER NOT NULL REFERENCES reader(id) ON DELETE CASCADE,
  book    TEXT NOT NULL,
  ch      TEXT NOT NULL,
  version TEXT NOT NULL,
  at      TEXT NOT NULL,
  PRIMARY KEY (reader, book, ch)
)""",
        # The translator's confirmed reply to a comment, which its reader sees under it.
        "ALTER TABLE comment ADD COLUMN reply TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE comment ADD COLUMN reply_at TEXT",
        # When a reader made each new comment in the last day, for the daily limit. Deleting a comment
        # leaves its row, so a delete never gives back a place in the day's count.
        """CREATE TABLE comment_made (
  reader INTEGER NOT NULL REFERENCES reader(id) ON DELETE CASCADE,
  at     TEXT NOT NULL
)""",
        "CREATE INDEX comment_made_by_reader ON comment_made(reader, at)",
    ]),
    (6, [
        # The fields that hold the translation's text get neutral names; the book's language code (book.language)
        # says which language they hold: th Thai, lo Lao, ium Mien. The English keeps its _en names.
        "ALTER TABLE book RENAME COLUMN title_th TO title",
        "ALTER TABLE chapter RENAME COLUMN title_th TO title",
        "ALTER TABLE chapter RENAME COLUMN source_th TO source",
        "ALTER TABLE chapter_version RENAME COLUMN title_th TO title",
        _migrate_paragraph_text,
        # Review rounds. Each time a book is opened for review a named round starts; the newest round of a book is
        # its current round. A comment carries the round it was written in, or NULL when it was written before
        # the book's first round.
        """CREATE TABLE review_round (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  book    TEXT NOT NULL,
  name    TEXT NOT NULL COLLATE NOCASE,
  started TEXT NOT NULL,
  UNIQUE (book, name)
)""",
        "ALTER TABLE comment ADD COLUMN round INTEGER REFERENCES review_round(id)",
        # The devices that use each link. link is the code_hash of the link the device opened, so a new link
        # starts a new count; device is the SHA-256 of the random key the page makes on the device. state is ok
        # (the link works there), waiting (for the translator's approval) or removed (by the translator).
        """CREATE TABLE reader_device (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  reader     INTEGER NOT NULL REFERENCES reader(id) ON DELETE CASCADE,
  link       TEXT NOT NULL,
  device     TEXT NOT NULL,
  state      TEXT NOT NULL CHECK (state IN ('ok', 'waiting', 'removed')),
  agent      TEXT NOT NULL DEFAULT '',
  first_seen TEXT NOT NULL,
  last_seen  TEXT NOT NULL,
  changed    TEXT,
  UNIQUE (reader, link, device)
)""",
        # Comments deleted by their reader or by the translator, so an export of what changed can name them.
        """CREATE TABLE comment_gone (
  id     INTEGER PRIMARY KEY,
  reader INTEGER NOT NULL,
  book   TEXT NOT NULL,
  ch     TEXT NOT NULL,
  at     TEXT NOT NULL
)""",
        "CREATE INDEX comment_gone_by_time ON comment_gone(at)",
        "CREATE INDEX comment_by_updated ON comment(updated)",
    ]),
    (7, [
        # The client_id of each comment deleted, so a device that sends a deleted comment again, after its
        # first answer was lost, is told that it was deleted instead of making it anew. Comments deleted before
        # this version have none.
        "ALTER TABLE comment_gone ADD COLUMN client_id TEXT",
        "CREATE INDEX comment_gone_by_client ON comment_gone(reader, client_id)",
    ]),
    (8, [
        # One person per account (server/auth.py). Today every account is a reader: the columns named account
        # hold a reader's number, so an editor's or the translator's account can join later without changing
        # these tables (EXTENDING.md, "Accounts and roles").
        # link_used: when the reader's current link was used to sign in with LINE or email; the link then neither
        # signs in nor binds again, and a new link (relink) clears it. first_signin: the reader's first sign-in
        # with LINE or email, which the translator is told of; never cleared. link_signs_in: the switch "Link
        # signs in", which keeps the personal link and the two-device lock for this reader alone.
        "ALTER TABLE reader ADD COLUMN link_used TEXT",
        "ALTER TABLE reader ADD COLUMN first_signin TEXT",
        "ALTER TABLE reader ADD COLUMN link_signs_in INTEGER NOT NULL DEFAULT 0",
        # The ways an account signs in: a LINE user id (provider line, subject the ID token's sub, display the
        # LINE display name, never the picture) or an email address (provider email, subject and display the
        # address in lower case). One identity belongs to one account.
        """CREATE TABLE identity (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  account   INTEGER NOT NULL REFERENCES reader(id) ON DELETE CASCADE,
  provider  TEXT NOT NULL CHECK (provider IN ('line', 'email')),
  subject   TEXT NOT NULL,
  display   TEXT NOT NULL DEFAULT '',
  created   TEXT NOT NULL,
  last_used TEXT,
  UNIQUE (provider, subject)
)""",
        "CREATE INDEX identity_by_account ON identity(account)",
        # A browser signed in: the cookie's value is kept only as its SHA-256. expires moves on at each visit
        # (auth.session_days from the last visit); ended is set when the reader or the translator ends it.
        """CREATE TABLE session (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  account    INTEGER NOT NULL REFERENCES reader(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  identity   INTEGER REFERENCES identity(id) ON DELETE SET NULL,
  via        TEXT NOT NULL,
  agent      TEXT NOT NULL DEFAULT '',
  created    TEXT NOT NULL,
  last_seen  TEXT NOT NULL,
  expires    TEXT NOT NULL,
  ended      TEXT,
  ended_by   TEXT
)""",
        "CREATE INDEX session_by_account ON session(account)",
        # A sign-in under way, for ten minutes, tied to its browser by a cookie whose SHA-256 is token_hash.
        # purpose: signin, claim (through a personal link; link is that link's code_hash), join (through a
        # general link) or add (one more identity for the account signed in). LINE keeps state, nonce and the
        # PKCE verifier; the email code keeps the address, the SHA-256 of the code with the cookie, and the tries.
        """CREATE TABLE auth_flow (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  token_hash   TEXT NOT NULL UNIQUE,
  kind         TEXT NOT NULL CHECK (kind IN ('line', 'email')),
  purpose      TEXT NOT NULL CHECK (purpose IN ('signin', 'claim', 'join', 'add')),
  account      INTEGER,
  link         TEXT,
  general_link INTEGER,
  state        TEXT UNIQUE,
  nonce        TEXT,
  verifier     TEXT,
  email        TEXT,
  code_hash    TEXT,
  sent         INTEGER NOT NULL DEFAULT 0,
  tries        INTEGER NOT NULL DEFAULT 0,
  created      TEXT NOT NULL,
  expires      TEXT NOT NULL,
  used         TEXT
)""",
        "CREATE INDEX auth_flow_by_email ON auth_flow(email, created)",
        # A general link of a group: it only asks for access. Making a new one stops the group's old one.
        """CREATE TABLE general_link (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  grp       INTEGER NOT NULL REFERENCES reader_group(id) ON DELETE CASCADE,
  code_hash TEXT NOT NULL UNIQUE,
  created   TEXT NOT NULL,
  expires   TEXT NOT NULL,
  uses_most INTEGER NOT NULL,
  uses      INTEGER NOT NULL DEFAULT 0,
  active    INTEGER NOT NULL DEFAULT 1,
  stopped   TEXT
)""",
        # A request to read, made by signing in through a general link. One identity has at most one open
        # request. account is the reader the translator made or chose when he approved it.
        """CREATE TABLE access_request (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  general_link INTEGER REFERENCES general_link(id) ON DELETE SET NULL,
  grp          INTEGER REFERENCES reader_group(id) ON DELETE SET NULL,
  provider     TEXT NOT NULL CHECK (provider IN ('line', 'email')),
  subject      TEXT NOT NULL,
  display      TEXT NOT NULL DEFAULT '',
  created      TEXT NOT NULL,
  decided      TEXT,
  decision     TEXT CHECK (decision IN ('approved', 'declined')),
  account      INTEGER REFERENCES reader(id) ON DELETE SET NULL
)""",
        "CREATE UNIQUE INDEX access_request_open ON access_request(provider, subject) WHERE decided IS NULL",
        "CREATE INDEX access_request_by_link ON access_request(general_link, created)",
        # The mails the site sent, newest 200: their kind and result, never the address or the words.
        """CREATE TABLE mail_log (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  at       TEXT NOT NULL,
  kind     TEXT NOT NULL,
  provider TEXT NOT NULL,
  ok       INTEGER NOT NULL,
  detail   TEXT NOT NULL DEFAULT ''
)""",
    ]),
]


class TooNew(ValueError):
    """The database was moved to a version this code does not know, by newer code."""


def statements(script):
    """Split an SQL script into single statements."""
    out, buf = [], ""
    for line in script.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            out.append(buf.strip())
            buf = ""
    return out


def init_db(path, features=None):
    """Create the database if needed and apply every migration it lacks, all in one transaction:
    first the core MIGRATIONS, then each feature's own (features: [(name, migrations)], by default
    every module in server/features/)."""
    if features is None:
        from . import features as registry
        features = [(f.name, f.migrations) for f in registry.load()]
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        with tx(conn):
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            newest = MIGRATIONS[-1][0]
            if version > newest:
                # Code older than the database cannot read it: it would answer the health check and fail on
                # every reader's request (deploy/DEPLOY.md, "Rolling back").
                raise TooNew(f"The database {path} is at version {version}, and this code knows versions up to "
                             f"{newest}. Newer code moved it. Run the newer code again, or put back the backup taken "
                             "before that update (deploy/DEPLOY.md, \"Rolling back\").")
            steps = [] if version else [(1, statements(SCHEMA.read_text()))]
            steps += [(n, sqls) for n, sqls in MIGRATIONS if n > version]
            for n, sqls in steps:
                for sql in sqls:
                    if callable(sql):
                        sql(conn)
                    else:
                        conn.execute(sql)
                conn.execute(f"PRAGMA user_version = {int(n)}")
            apply_feature_migrations(conn, features)
    finally:
        conn.close()


def apply_feature_migrations(conn, features):
    """Each feature's migrations (version, statements) that the database lacks, in order.
    feature_schema records the version each feature has reached."""
    have = {r[0]: r[1] for r in conn.execute("SELECT feature, version FROM feature_schema")}
    for name, migrations in features:
        done = have.get(name, 0)
        for n, sqls in migrations:
            if n > done:
                for sql in sqls:
                    conn.execute(sql)
                done = n
        if done != have.get(name, 0):
            conn.execute("INSERT INTO feature_schema (feature, version) VALUES (?, ?)"
                         " ON CONFLICT (feature) DO UPDATE SET version = excluded.version", (name, done))


# The entries config.json may hold; README.md, "Sign-in settings", describes each.
CONFIG_ENTRIES = ("public_url", "limits", "auth", "mail", "notify", "invite")


def _config_file(data_dir):
    """config.json of the data directory: {} when there is none. A file that cannot be read, is not valid JSON,
    is not an object or holds an unknown entry raises ValueError with one plain sentence naming config.json, so
    that the server refuses to start rather than run without the settings it holds."""
    path = Path(data_dir) / CONFIG
    where = f"{CONFIG} in {data_dir}"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError) as e:
        raise ValueError(f"{where} cannot be read ({e}).")
    try:
        cfg = json.loads(text)
    except ValueError as e:
        where_in = f"line {e.lineno}, column {e.colno}: {e.msg}" if isinstance(e, json.JSONDecodeError) else str(e)
        raise ValueError(f"{where} is not valid JSON ({where_in}). Check it with: python3 -m json.tool {path}")
    if not isinstance(cfg, dict):
        raise ValueError(f"{where} must hold one JSON object, {{...}}.")
    unknown = sorted(set(cfg) - set(CONFIG_ENTRIES))
    if unknown:
        raise ValueError(f'{where} has no entry named "{unknown[0]}". Its entries are {", ".join(CONFIG_ENTRIES)}.')
    return cfg


def read_config(data_dir):
    """config.json from the data directory, with REVIEW_PUBLIC_URL taking precedence."""
    cfg = _config_file(data_dir)
    if os.environ.get("REVIEW_PUBLIC_URL"):
        cfg["public_url"] = os.environ["REVIEW_PUBLIC_URL"]
    return cfg


def setup(data_dir, public_url=None, new_token=False):
    """Create the data directory, database, config and admin token.

    Returns (token_file or None, created): the plain token is written to
    data_dir/admin-token only when a new token is made; only its hash stays
    needed on the server.
    """
    data = Path(data_dir)
    data.mkdir(parents=True, exist_ok=True)
    os.chmod(data, 0o700)
    init_db(data / DB_NAME)
    cfg = _config_file(data)
    if public_url or "public_url" not in cfg:
        cfg["public_url"] = (public_url or "http://127.0.0.1:8087").rstrip("/")
        (data / CONFIG).write_text(json.dumps(cfg, indent=2) + "\n")
    hash_path = data / TOKEN_HASH
    if hash_path.exists() and not new_token:
        return None, False
    token = secrets.token_urlsafe(32)
    token_path = data / TOKEN_FILE
    fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(token + "\n")
    hash_path.write_text(sha256(token) + "\n")
    os.chmod(hash_path, 0o600)
    return token_path, True


def admin_hash(data_dir):
    try:
        return (Path(data_dir) / TOKEN_HASH).read_text().strip()
    except OSError:
        return ""


BACKUP_RE = re.compile(r"review-(\d{4}-\d\d-\d\d)(?:-(\d{6}))?(?:-\d+)?\.sqlite3")


def backup_time(path):
    """The UTC time in a backup's name: review-2026-10-22-033000.sqlite3, or the older review-2026-10-22.sqlite3
    (taken as midnight). None for any other file."""
    m = BACKUP_RE.fullmatch(path.name)
    if not m:
        return None
    return datetime.strptime(m.group(1) + (m.group(2) or "000000"), "%Y-%m-%d%H%M%S").replace(tzinfo=timezone.utc)


def backup(data_dir, keep=14):
    """Copy the live database to backups/review-YYYY-MM-DD-HHMMSS.sqlite3 (UTC), never over another backup.
    A copy older than keep days is deleted, but the newest keep copies always stay."""
    data = Path(data_dir)
    out_dir = data / "backups"
    out_dir.mkdir(exist_ok=True)
    os.chmod(out_dir, 0o700)
    stamp = datetime.now(timezone.utc)
    name = f"review-{stamp:%Y-%m-%d-%H%M%S}"
    target = out_dir / f"{name}.sqlite3"
    n = 1
    while target.exists():
        n += 1
        target = out_dir / f"{name}-{n}.sqlite3"
    tmp = target.with_suffix(".tmp")
    src = connect(data / DB_NAME)
    dst = sqlite3.connect(tmp)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    os.chmod(tmp, 0o600)
    tmp.replace(target)
    if keep > 0:
        copies = sorted(((t, p) for p in out_dir.glob("review-*.sqlite3") if (t := backup_time(p))),
                        key=lambda x: (x[0], x[1].name))
        cutoff = stamp - timedelta(days=keep)
        for t, old in copies[:-keep]:
            if t < cutoff and old != target:
                old.unlink()
    return target

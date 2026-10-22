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
language (book.title_th).

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


def now():
    """The current UTC time as 2026-10-21T20:30:00Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ago(days):
    """The UTC time days ago, in the form of now()."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


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
]


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
            steps = [] if version else [(1, statements(SCHEMA.read_text()))]
            steps += [(n, sqls) for n, sqls in MIGRATIONS if n > version]
            for n, sqls in steps:
                for sql in sqls:
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


def _config_file(data_dir):
    try:
        return json.loads((Path(data_dir) / CONFIG).read_text())
    except (OSError, ValueError):
        return {}


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

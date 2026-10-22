"""Database and data-directory code for the proofreading site.

The data directory holds review.sqlite3 (SQLite in WAL mode), the admin
token's SHA-256 hash in admin-token.sha256, config.json (the public URL),
and backups/. Nothing in it belongs in the code folder or in git.

schema.sql is version 1 of the database. Every later change is a numbered
entry in MIGRATIONS. init_db brings any database, new or old, to the newest
version in one transaction when the server starts. To change the database,
add an entry with the next number; never edit an entry that has shipped.
"""
import contextlib
import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")
DB_NAME = "review.sqlite3"
TOKEN_HASH = "admin-token.sha256"
TOKEN_FILE = "admin-token"
CONFIG = "config.json"


def now():
    """The current UTC time as 2026-10-21T20:30:00Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def init_db(path):
    """Create the database if needed and apply every migration it lacks, all in one transaction."""
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
    finally:
        conn.close()


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


def backup(data_dir, keep=14):
    """Copy the live database to backups/review-YYYY-MM-DD.sqlite3 and keep the newest copies."""
    data = Path(data_dir)
    out_dir = data / "backups"
    out_dir.mkdir(exist_ok=True)
    os.chmod(out_dir, 0o700)
    target = out_dir / f"review-{now()[:10]}.sqlite3"
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
    copies = sorted(out_dir.glob("review-*.sqlite3"))
    for old in copies[:-keep] if keep > 0 else []:
        old.unlink()
    return target

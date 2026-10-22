-- Database of the proofreading site, version 1. server/db.py applies this file to a new database
-- and then every entry of its MIGRATIONS list. Migration 2 makes comment ids AUTOINCREMENT, so an
-- id is never used twice, and adds source_th, source_en and source_commit to chapter.

CREATE TABLE IF NOT EXISTS book (
  id       TEXT PRIMARY KEY,
  title_en TEXT NOT NULL DEFAULT '',
  language TEXT NOT NULL DEFAULT 'th'   -- th or lo: the language of the translation
);

-- A chapter row is never deleted: withdrawing clears "published" and keeps its comments.
CREATE TABLE IF NOT EXISTS chapter (
  book         TEXT NOT NULL REFERENCES book(id),
  id           TEXT NOT NULL,
  n            INTEGER NOT NULL,
  title_th     TEXT NOT NULL,
  title_en     TEXT NOT NULL,
  version      TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  published    INTEGER NOT NULL DEFAULT 1,
  count        INTEGER NOT NULL,
  paragraphs   TEXT NOT NULL,          -- JSON [{a, th, fn, en}]
  updated      TEXT NOT NULL,
  PRIMARY KEY (book, id)
);

CREATE TABLE IF NOT EXISTS reader (
  id        INTEGER PRIMARY KEY,
  name      TEXT NOT NULL UNIQUE COLLATE NOCASE,
  code_hash TEXT NOT NULL UNIQUE,     -- SHA-256 hex of the reader's code
  active    INTEGER NOT NULL DEFAULT 1,
  english   INTEGER NOT NULL DEFAULT 0,
  created   TEXT NOT NULL
);

-- chapter is a chapter id, or "*" for every published chapter of the book, now and later.
CREATE TABLE IF NOT EXISTS "grant" (
  reader  INTEGER NOT NULL REFERENCES reader(id) ON DELETE CASCADE,
  book    TEXT NOT NULL,
  chapter TEXT NOT NULL,
  PRIMARY KEY (reader, book, chapter)
);

CREATE TABLE IF NOT EXISTS comment (
  id        INTEGER PRIMARY KEY,
  client_id TEXT NOT NULL,
  reader    INTEGER NOT NULL REFERENCES reader(id) ON DELETE CASCADE,
  book      TEXT NOT NULL,
  ch        TEXT NOT NULL,
  a         TEXT NOT NULL,
  kind      TEXT NOT NULL CHECK (kind IN ('flag', 'wording')),
  quote     TEXT NOT NULL DEFAULT '',
  text      TEXT NOT NULL,
  version   TEXT NOT NULL DEFAULT '',  -- the chapter version the reader saw
  created   TEXT NOT NULL,
  updated   TEXT NOT NULL,
  processed INTEGER NOT NULL DEFAULT 0,
  UNIQUE (reader, client_id),
  FOREIGN KEY (book, ch) REFERENCES chapter(book, id)
);
CREATE INDEX IF NOT EXISTS comment_by_reader ON comment(reader, book, ch);
CREATE INDEX IF NOT EXISTS comment_by_chapter ON comment(book, ch);

CREATE TABLE IF NOT EXISTS place (
  reader  INTEGER NOT NULL REFERENCES reader(id) ON DELETE CASCADE,
  book    TEXT NOT NULL,
  ch      TEXT NOT NULL,
  a       TEXT NOT NULL,
  updated TEXT NOT NULL,
  PRIMARY KEY (reader, book, ch)
);

CREATE TABLE IF NOT EXISTS finished (
  reader   INTEGER NOT NULL REFERENCES reader(id) ON DELETE CASCADE,
  book     TEXT NOT NULL,
  ch       TEXT NOT NULL,
  finished INTEGER NOT NULL,
  at       TEXT NOT NULL,
  PRIMARY KEY (reader, book, ch)
);

PRAGMA user_version = 1;

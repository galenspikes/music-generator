# Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
# https://github.com/galenspikes/music-generator
"""SQLite-backed store for saved chord progressions (the ChordBuilder library).

Replaces the one-JSON-file-per-progression layout: a single ``sqlite3``
database gives transactional saves (no torn writes), safe concurrent access
from parallel web requests, and real queries (name/title/tag search) —
with zero new dependencies.

Legacy ``*.json`` files in the store's directory are imported on first use
(insert-if-missing, so a DB row always wins) and left on disk untouched;
they simply stop being the source of truth. The stored record shape is
exactly what :mod:`generator_api` historically wrote to JSON::

    {"title": str, "tags": [str], "keys": str,
     "tempo": int | None, "voicing": str | None, "saved": iso8601}

:mod:`generator_api` wraps this in module-level facades
(``list_progressions`` / ``load_progression`` / ``save_progression`` /
``delete_progression`` / ``search_progressions``); use those unless you
need a store at a custom path.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

__all__ = ["ProgressionStore"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS progressions (
    name    TEXT PRIMARY KEY,
    title   TEXT NOT NULL DEFAULT '',
    tags    TEXT NOT NULL DEFAULT '[]',   -- JSON array of strings
    keys    TEXT NOT NULL DEFAULT '',
    tempo   INTEGER,
    voicing TEXT,
    saved   TEXT NOT NULL DEFAULT ''
);
"""


class ProgressionStore:
    """CRUD + search over the progression library, safe for concurrent use.

    Each operation opens a short-lived connection (SQLite's own file locking
    then serialises writers), so instances can be shared freely across
    threads. The one-time schema creation and legacy-JSON import are guarded
    by an instance lock.
    """

    def __init__(self, db_path: str | Path,
                 legacy_dir: str | Path | None = None) -> None:
        self._db_path = Path(db_path)
        self._legacy_dir = Path(legacy_dir) if legacy_dir is not None else None
        self._init_lock = threading.Lock()
        self._initialized = False

    # -- lifecycle ---------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        self._ensure_ready()
        con = sqlite3.connect(self._db_path, timeout=10.0)
        con.row_factory = sqlite3.Row
        return con

    def _ensure_ready(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(self._db_path, timeout=10.0)
            try:
                # WAL lets readers proceed during a write; harmless fallback
                # on filesystems that refuse it.
                con.execute("PRAGMA journal_mode=WAL")
                con.execute(_SCHEMA)
                con.commit()
                self._import_legacy(con)
            finally:
                con.close()
            self._initialized = True

    def _import_legacy(self, con: sqlite3.Connection) -> None:
        """One-time import of the old one-file-per-progression layout.

        Insert-if-missing: an existing DB row always beats a stray file. The
        files are left in place (they may be seed data under version
        control) but are no longer read after this."""
        if self._legacy_dir is None or not self._legacy_dir.exists():
            return
        for f in sorted(self._legacy_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue  # unreadable legacy file: skip, don't block the store
            if not isinstance(data, dict):
                continue
            con.execute(
                "INSERT OR IGNORE INTO progressions "
                "(name, title, tags, keys, tempo, voicing, saved) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f.stem,
                 str(data.get("title") or f.stem),
                 json.dumps(data.get("tags") or []),
                 str(data.get("keys") or ""),
                 data.get("tempo"),
                 data.get("voicing"),
                 str(data.get("saved") or "")))
        con.commit()

    # -- record shaping ----------------------------------------------------

    @staticmethod
    def _summary(row: sqlite3.Row) -> dict:
        """The list/search entry shape (matches the old list_progressions)."""
        return {
            "name": row["name"],
            "title": row["title"],
            "tags": json.loads(row["tags"] or "[]"),
            "keys": row["keys"],
            "tempo": row["tempo"],
            "saved": row["saved"],
        }

    @staticmethod
    def _record(row: sqlite3.Row) -> dict:
        """The full load shape (matches the old per-file JSON payload)."""
        return {
            "title": row["title"],
            "tags": json.loads(row["tags"] or "[]"),
            "keys": row["keys"],
            "tempo": row["tempo"],
            "voicing": row["voicing"],
            "saved": row["saved"],
        }

    # -- CRUD + search -----------------------------------------------------

    def list(self) -> list[dict]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM progressions ORDER BY name").fetchall()
        return [self._summary(r) for r in rows]

    def load(self, name: str) -> dict | None:
        with self._connect() as con:
            row = con.execute("SELECT * FROM progressions WHERE name = ?",
                              (name,)).fetchone()
        return self._record(row) if row else None

    def save(self, name: str, keys: str, title: str = "",
             tags: list[str] | None = None, tempo: int | None = None,
             voicing: str | None = None) -> dict:
        data = {
            "title": title or name,
            "tags": tags or [],
            "keys": keys,
            "tempo": tempo,
            "voicing": voicing,
            "saved": datetime.now().isoformat(),
        }
        with self._connect() as con:
            con.execute(
                "INSERT INTO progressions "
                "(name, title, tags, keys, tempo, voicing, saved) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET "
                "title=excluded.title, tags=excluded.tags, "
                "keys=excluded.keys, tempo=excluded.tempo, "
                "voicing=excluded.voicing, saved=excluded.saved",
                (name, data["title"], json.dumps(data["tags"]), keys,
                 tempo, voicing, data["saved"]))
        return data

    def delete(self, name: str) -> None:
        """Delete a progression. No-op (not an error) if it doesn't exist."""
        with self._connect() as con:
            con.execute("DELETE FROM progressions WHERE name = ?", (name,))

    def search(self, query: str = "", tag: str | None = None) -> list[dict]:
        """Progressions whose name/title/keys contain ``query``
        (case-insensitive), optionally restricted to an exact ``tag``.
        Empty query + no tag = everything (same as :meth:`list`)."""
        like = f"%{(query or '').strip().lower()}%"
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM progressions WHERE "
                "(lower(name) LIKE ? OR lower(title) LIKE ? "
                " OR lower(keys) LIKE ?) ORDER BY name",
                (like, like, like)).fetchall()
        out = [self._summary(r) for r in rows]
        if tag is not None:
            out = [p for p in out if tag in p["tags"]]
        return out

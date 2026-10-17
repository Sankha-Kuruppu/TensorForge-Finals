"""SQLite store for prediction logs, the human-review queue and drift alerts.

Raw text is never stored: only a redacted version (contact details removed)
and a hash, in line with Sri Lanka's PDPA.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone

import numpy as np

from jobshield.config import LOG_DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, text_hash TEXT, text_redacted TEXT, lang TEXT,
    prob REAL, decision TEXT, confidence REAL, nearest_sim REAL, is_unknown INTEGER,
    flags TEXT, model_version TEXT, channel TEXT, emb BLOB
);
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER UNIQUE, ts TEXT, reason TEXT,
    status TEXT DEFAULT 'pending', label INTEGER, reviewed_at TEXT
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, level TEXT, signals TEXT, message TEXT, model_version TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, kind TEXT, detail TEXT
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path=LOG_DB):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.conn.executescript(SCHEMA)

    def _exec(self, sql, params=()):
        with self.lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur

    def _query(self, sql, params=()):
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    # -- predictions ------------------------------------------------------
    def log_prediction(self, rec: dict, emb: np.ndarray) -> int:
        cur = self._exec(
            "INSERT INTO predictions (ts, text_hash, text_redacted, lang, prob, decision, confidence,"
            " nearest_sim, is_unknown, flags, model_version, channel, emb)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (now(), rec["text_hash"], rec["text_redacted"], rec["lang"], rec["prob"], rec["decision"],
             rec["confidence"], rec["nearest_sim"], int(rec["is_unknown"]), json.dumps(rec["flags"]),
             rec["model_version"], rec.get("channel", "api"), emb.astype(np.float16).tobytes()))
        return cur.lastrowid

    def recent_predictions(self, n: int, with_emb: bool = False) -> list[dict]:
        cols = "*" if with_emb else ("id, ts, text_hash, text_redacted, lang, prob, decision, confidence,"
                                     " nearest_sim, is_unknown, flags, model_version, channel")
        rows = self._query(f"SELECT {cols} FROM predictions ORDER BY id DESC LIMIT ?", (n,))
        if with_emb:
            for r in rows:
                r["emb"] = np.frombuffer(r["emb"], dtype=np.float16).astype(np.float32)
        return rows

    def count_predictions(self) -> int:
        return self._query("SELECT COUNT(*) AS n FROM predictions")[0]["n"]

    # -- review queue -----------------------------------------------------
    def enqueue_review(self, prediction_id: int, reason: str) -> None:
        self._exec("INSERT OR IGNORE INTO reviews (prediction_id, ts, reason) VALUES (?,?,?)",
                   (prediction_id, now(), reason))

    def review_queue(self, status: str = "pending", limit: int = 100) -> list[dict]:
        return self._query(
            "SELECT r.id, r.prediction_id, r.ts, r.reason, r.status, r.label, p.text_redacted, p.text_hash,"
            " p.prob, p.lang, p.flags FROM reviews r JOIN predictions p ON p.id = r.prediction_id"
            " WHERE r.status = ? ORDER BY r.id LIMIT ?", (status, limit))

    def submit_review(self, review_id: int, label: int) -> None:
        self._exec("UPDATE reviews SET status='labelled', label=?, reviewed_at=? WHERE id=?",
                   (int(label), now(), review_id))

    def review_counts(self) -> dict:
        rows = self._query("SELECT status, COUNT(*) AS n FROM reviews GROUP BY status")
        return {r["status"]: r["n"] for r in rows}

    def labelled_reviews(self) -> list[dict]:
        return self.review_queue("labelled", limit=100_000)

    def mark_reviews_used(self, ids: list[int]) -> None:
        with self.lock:
            self.conn.executemany("UPDATE reviews SET status='used' WHERE id=?", [(i,) for i in ids])
            self.conn.commit()

    # -- alerts and events ------------------------------------------------
    def add_alert(self, level: str, signals: dict, message: str, model_version: str) -> None:
        self._exec("INSERT INTO alerts (ts, level, signals, message, model_version) VALUES (?,?,?,?,?)",
                   (now(), level, json.dumps(signals), message, model_version))

    def alerts(self, limit: int = 50) -> list[dict]:
        return self._query("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))

    def add_event(self, kind: str, detail: dict) -> None:
        self._exec("INSERT INTO events (ts, kind, detail) VALUES (?,?,?)", (now(), kind, json.dumps(detail)))

    def events(self, limit: int = 50) -> list[dict]:
        return self._query("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))

    def reset(self) -> None:
        with self.lock:
            self.conn.executescript("DELETE FROM predictions; DELETE FROM reviews;"
                                    " DELETE FROM alerts; DELETE FROM events;")

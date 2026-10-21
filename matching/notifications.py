"""Per-lost-report subscriptions and in-app notifications.

A subscriber is a lost report, not a keyword: when a found item is registered,
the same evidence ranking used by the match page decides whether the report's
owner should be told. Notifications never contain contact details; they only
point at the unmatched found item and the lost report it may belong to.

The score threshold is a ranking heuristic, not a probability.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import numpy as np

from .engine import rank_candidates
from .fingerprint import fingerprint_from_text

NOTIFY_THRESHOLD = 0.40


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if not denominator:
        return 0.0
    return float(np.dot(left, right) / denominator)


class Notifications:
    """Create and read the two extension tables; existing tables are untouched."""

    def __init__(self, db_path: str | Path = "items.db") -> None:
        self.path = str(db_path)
        with sqlite3.connect(self.path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK (kind IN ('lost_item', 'search')),
                    lost_item_id INTEGER NOT NULL DEFAULT 0,
                    keyword TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT '',
                    location TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL,
                    UNIQUE (username, kind, lost_item_id, keyword, category, location)
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    found_item_id INTEGER NOT NULL,
                    lost_item_id INTEGER,
                    subscription_id INTEGER NOT NULL,
                    score REAL,
                    created_at INTEGER NOT NULL,
                    read_at INTEGER,
                    UNIQUE (username, found_item_id, subscription_id)
                )
            """)

    # ---------- subscriptions ----------

    def subscribe_item(self, username: str, lost_item_id: int) -> bool:
        with sqlite3.connect(self.path) as con:
            cursor = con.execute(
                "INSERT OR IGNORE INTO subscriptions "
                "(username, kind, lost_item_id, keyword, category, location, created_at) "
                "VALUES (?, 'lost_item', ?, '', '', '', ?)",
                (username, int(lost_item_id), int(time.time())),
            )
            return cursor.rowcount == 1

    def unsubscribe_item(self, username: str, lost_item_id: int) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute(
                "DELETE FROM subscriptions WHERE username=? AND kind='lost_item' AND lost_item_id=?",
                (username, int(lost_item_id)),
            )

    def is_subscribed(self, username: str, lost_item_id: int) -> bool:
        with sqlite3.connect(self.path) as con:
            row = con.execute(
                "SELECT 1 FROM subscriptions WHERE username=? AND kind='lost_item' AND lost_item_id=?",
                (username, int(lost_item_id)),
            ).fetchone()
        return row is not None

    def toggle_item(self, username: str, lost_item_id: int) -> bool:
        """Flip the subscription and return its new state."""
        if self.is_subscribed(username, lost_item_id):
            self.unsubscribe_item(username, lost_item_id)
            return False
        self.subscribe_item(username, lost_item_id)
        return True

    def item_subscriptions(self) -> list[dict]:
        with sqlite3.connect(self.path) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT id, username, lost_item_id FROM subscriptions "
                "WHERE kind='lost_item' ORDER BY id"
            ).fetchall()
        return [dict(row) for row in rows]

    # ---------- notifications ----------

    def add(self, username: str, found_item_id: int, lost_item_id: int | None,
            subscription_id: int, score: float | None) -> bool:
        with sqlite3.connect(self.path) as con:
            cursor = con.execute(
                "INSERT OR IGNORE INTO notifications "
                "(username, found_item_id, lost_item_id, subscription_id, score, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (username, int(found_item_id), lost_item_id, int(subscription_id),
                 score, int(time.time())),
            )
            return cursor.rowcount == 1

    def unread_count(self, username: str) -> int:
        with sqlite3.connect(self.path) as con:
            row = con.execute(
                "SELECT COUNT(*) FROM notifications WHERE username=? AND read_at IS NULL",
                (username,),
            ).fetchone()
        return int(row[0]) if row else 0

    def list(self, username: str, limit: int = 100) -> list[dict]:
        with sqlite3.connect(self.path) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("""
                SELECT n.id, n.found_item_id, n.lost_item_id, n.score,
                       n.created_at, n.read_at,
                       f.description AS found_desc,
                       f.location AS found_location,
                       f.time AS found_time,
                       l.description AS lost_desc
                FROM notifications n
                JOIN items f ON f.id = n.found_item_id
                LEFT JOIN items l ON l.id = n.lost_item_id
                WHERE n.username = ?
                ORDER BY (n.read_at IS NULL) DESC, n.created_at DESC, n.id DESC
                LIMIT ?
            """, (username, int(limit))).fetchall()
        return [dict(row) for row in rows]

    def mark_read(self, username: str, notification_id: int) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute(
                "UPDATE notifications SET read_at=? WHERE id=? AND username=? AND read_at IS NULL",
                (int(time.time()), int(notification_id), username),
            )

    def mark_all_read(self, username: str) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute(
                "UPDATE notifications SET read_at=? WHERE username=? AND read_at IS NULL",
                (int(time.time()), username),
            )

    def delete_for_item(self, item_id: int) -> None:
        """Withdrawals remove the item; drop subscriptions and alerts that point at it."""
        with sqlite3.connect(self.path) as con:
            con.execute("DELETE FROM notifications WHERE found_item_id=? OR lost_item_id=?",
                        (int(item_id), int(item_id)))
            con.execute("DELETE FROM subscriptions WHERE lost_item_id=?", (int(item_id),))


def unread_count(username: str, db_path: str | Path = "items.db") -> int:
    """Convenience for the top bar; creates the tables if this is the first run."""
    return Notifications(db_path).unread_count(username)


def notify_for_found_item(found_item, fingerprint: dict, db, store,
                          owner: str, notifications: Notifications | None = None,
                          threshold: float = NOTIFY_THRESHOLD) -> int:
    """Create alerts for subscribed lost reports that the new found item may match.

    Uses the same `rank_candidates` formula as the match page. Missing vectors,
    matched reports, and the finder's own reports are skipped. Returns the number
    of notifications actually inserted.
    """
    notifications = notifications or Notifications()
    subscriptions = notifications.item_subscriptions()
    if not subscriptions:
        return 0

    if found_item.emb is None:
        return 0
    found_vector = np.asarray(found_item.emb, dtype=np.float32).reshape(-1)
    if not found_vector.size or not np.isfinite(found_vector).all():
        return 0

    created = 0
    for subscription in subscriptions:
        if subscription["username"] == owner:
            continue
        lost_id = int(subscription["lost_item_id"])
        if lost_id == found_item.id or not db.item_exists(lost_id):
            continue
        # A report that is already matched or closed has nothing left to claim.
        if db.get_lost_item_matches(lost_id):
            continue
        if db.get_item_status(lost_id):
            continue
        lost = db.get_item(lost_id)
        if lost.emb is None:
            continue
        lost_vector = np.asarray(lost.emb, dtype=np.float32).reshape(-1)
        if lost_vector.shape != found_vector.shape or not np.isfinite(lost_vector).all():
            continue

        semantic = max(0.0, min(1.0, _cosine(found_vector, lost_vector)))
        lost_fingerprint = store.get(lost_id) or fingerprint_from_text(
            lost.description or "", generate=False)
        candidate = {
            "item_id": found_item.id,
            "semantic_score": semantic,
            "fingerprint": fingerprint,
            "description": found_item.description or "",
            "time": getattr(found_item, "time", None),
            "location": getattr(found_item, "location", None),
        }
        ranked = rank_candidates(
            lost_fingerprint, [candidate],
            query_time=getattr(lost, "time", None),
            query_location=getattr(lost, "location", None),
        )
        if not ranked:
            continue
        score = ranked[0]["score"]
        if score < threshold:
            continue
        if notifications.add(subscription["username"], found_item.id, lost_id,
                              subscription["id"], score):
            created += 1
    return created

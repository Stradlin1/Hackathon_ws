"""Mutual confirmation before contact details are shared.

Lifecycle rules:
- a found item can have at most `MAX_PENDING_PER_FOUND` pending requests;
- rejecting a pair starts a `REJECT_COOLDOWN_SECONDS` cooldown; after it passes
  the same pair may request again (the old rejected row is replaced, a history
  row keeps the prior attempt);
- accepting one request closes every other pending request touching either
  item and inserts the match; an item can never be accepted twice.

`match_requests` keeps its original columns and status values. `request_history`
is a new extension table; it is what makes the cooldown and audit possible
without changing an existing table.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

MAX_PENDING_PER_FOUND = 3
REJECT_COOLDOWN_SECONDS = 24 * 60 * 60


def pair_ids(direction: str, query_item_id: int, candidate_item_id: int) -> tuple[int, int]:
    """Return (found_item_id, lost_item_id) for either request direction."""
    if direction == "lost":
        return candidate_item_id, query_item_id
    if direction == "found":
        return query_item_id, candidate_item_id
    raise ValueError("无效的报告方向")


def cooldown_text(seconds: int) -> str:
    hours = max(1, (int(seconds) + 3599) // 3600)
    return f"{hours} 小时"


class MatchRequests:
    def __init__(self, db_path: str | Path = "items.db"):
        self.path = str(db_path)
        with sqlite3.connect(self.path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS match_requests (
                    found_item_id INTEGER NOT NULL,
                    lost_item_id INTEGER NOT NULL,
                    requester TEXT NOT NULL,
                    responder TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'accepted', 'rejected')),
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY (found_item_id, lost_item_id)
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS request_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    found_item_id INTEGER NOT NULL,
                    lost_item_id INTEGER NOT NULL,
                    requester TEXT NOT NULL,
                    responder TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('accepted', 'rejected')),
                    created_at INTEGER NOT NULL,
                    ended_at INTEGER NOT NULL
                )
            """)

    @staticmethod
    def _is_matched(con, found: int, lost: int) -> bool:
        found_match = con.execute(
            "SELECT 1 FROM matches WHERE item1_id=? OR item2_id=?", (found, found)
        ).fetchone()
        if found_match:
            return True
        return con.execute(
            "SELECT 1 FROM matches WHERE item1_id=? OR item2_id=?", (lost, lost)
        ).fetchone() is not None

    def create(self, direction: str, query_item_id: int, candidate_item_id: int,
               username: str) -> str:
        found, lost = pair_ids(direction, query_item_id, candidate_item_id)
        now = int(time.time())
        with sqlite3.connect(self.path) as con:
            found_owner = con.execute(
                "SELECT user_id FROM found_items WHERE item_id=?", (found,)
            ).fetchone()
            lost_owner = con.execute(
                "SELECT user_id FROM lost_items WHERE item_id=?", (lost,)
            ).fetchone()
            if found_owner is None or lost_owner is None:
                raise ValueError("无法获取物品所有者")
            requester = lost_owner[0] if direction == "lost" else found_owner[0]
            responder = found_owner[0] if direction == "lost" else lost_owner[0]
            if requester != username:
                raise PermissionError("不能为其他用户的物品发起匹配请求")

            row = con.execute(
                "SELECT status FROM match_requests WHERE found_item_id=? AND lost_item_id=?",
                (found, lost),
            ).fetchone()
            if row is not None:
                status = row[0]
                if status in ("pending", "accepted"):
                    return status
                last = con.execute(
                    "SELECT MAX(ended_at) FROM request_history "
                    "WHERE found_item_id=? AND lost_item_id=? AND status='rejected'",
                    (found, lost),
                ).fetchone()[0]
                remaining = max(0, (last or 0) + REJECT_COOLDOWN_SECONDS - now)
                if remaining > 0:
                    raise ValueError(
                        f"对方已拒绝；{cooldown_text(remaining)}后可重新发起。")
                con.execute(
                    "DELETE FROM match_requests WHERE found_item_id=? AND lost_item_id=?",
                    (found, lost),
                )

            if self._is_matched(con, found, lost):
                raise ValueError("该物品已经配对，不能再发起请求。")
            pending = con.execute(
                "SELECT COUNT(*) FROM match_requests "
                "WHERE found_item_id=? AND status='pending'", (found,)
            ).fetchone()[0]
            if pending >= MAX_PENDING_PER_FOUND:
                raise ValueError(
                    f"这件拾获已有 {MAX_PENDING_PER_FOUND} 个待确认请求，请等待对方处理。")

            con.execute(
                "INSERT INTO match_requests "
                "(found_item_id,lost_item_id,requester,responder,status,created_at) "
                "VALUES (?,?,?,?,'pending',?)",
                (found, lost, requester, responder, now),
            )
        return "pending"

    def incoming(self, username: str) -> list[dict]:
        with sqlite3.connect(self.path) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("""
                SELECT r.found_item_id, r.lost_item_id, r.requester,
                       f.description AS found_desc, l.description AS lost_desc
                FROM match_requests r
                JOIN items f ON f.id = r.found_item_id
                JOIN items l ON l.id = r.lost_item_id
                WHERE r.responder = ? AND r.status = 'pending'
                ORDER BY r.created_at DESC
            """, (username,)).fetchall()
            return [dict(row) for row in rows]

    def outgoing(self, username: str) -> list[dict]:
        with sqlite3.connect(self.path) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("""
                SELECT found_item_id, lost_item_id, status
                FROM match_requests
                WHERE requester = ? ORDER BY created_at DESC
            """, (username,)).fetchall()
            return [dict(row) for row in rows]

    def accepted(self, username: str) -> list[dict]:
        with sqlite3.connect(self.path) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("""
                SELECT r.found_item_id, r.lost_item_id,
                       u.username AS contact_username, u.email AS contact_email
                FROM match_requests r
                JOIN users u ON u.username = CASE
                  WHEN r.requester = ? THEN r.responder ELSE r.requester END
                WHERE r.status = 'accepted' AND (r.requester = ? OR r.responder = ?)
                ORDER BY r.created_at DESC
            """, (username, username, username)).fetchall()
            return [dict(row) for row in rows]

    def statuses_for_item(self, item_id: int) -> list[str]:
        with sqlite3.connect(self.path) as con:
            rows = con.execute(
                "SELECT status FROM match_requests WHERE found_item_id=? OR lost_item_id=?",
                (item_id, item_id),
            ).fetchall()
        return [row[0] for row in rows]

    def state(self, direction: str, query_item_id: int,
              candidate_item_id: int) -> dict:
        found, lost = pair_ids(direction, query_item_id, candidate_item_id)
        return self.state_pair(found, lost)

    def state_pair(self, found: int, lost: int) -> dict:
        """Current request state plus the remaining rejection cooldown."""
        with sqlite3.connect(self.path) as con:
            row = con.execute(
                "SELECT status FROM match_requests WHERE found_item_id=? AND lost_item_id=?",
                (found, lost),
            ).fetchone()
            if row is None:
                return {"status": None, "cooldown": 0, "can_request": True}
            status = row[0]
            if status != "rejected":
                return {"status": status, "cooldown": 0, "can_request": False}
            last = con.execute(
                "SELECT MAX(ended_at) FROM request_history "
                "WHERE found_item_id=? AND lost_item_id=? AND status='rejected'",
                (found, lost),
            ).fetchone()[0]
        remaining = (max(0, (last or 0) + REJECT_COOLDOWN_SECONDS - int(time.time()))
                     if last else 0)
        return {"status": status, "cooldown": remaining, "can_request": remaining == 0}

    def cancel_for_item(self, item_id: int) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute(
                "DELETE FROM match_requests WHERE found_item_id=? OR lost_item_id=?",
                (item_id, item_id),
            )
            con.execute(
                "DELETE FROM request_history WHERE found_item_id=? OR lost_item_id=?",
                (item_id, item_id),
            )
            try:
                con.execute(
                    "DELETE FROM matches WHERE item1_id=? OR item2_id=?", (item_id, item_id))
            except sqlite3.OperationalError:
                pass  # matches is created by Database; nothing to clean up yet

    def respond(self, username: str, found: int, lost: int, accept: bool) -> bool:
        now = int(time.time())
        with sqlite3.connect(self.path) as con:
            row = con.execute(
                "SELECT requester, responder, status, created_at FROM match_requests "
                "WHERE found_item_id=? AND lost_item_id=?",
                (found, lost),
            ).fetchone()
            if row is None or row[2] != "pending" or row[1] != username:
                return False
            requester, responder, _, created_at = row
            if accept and self._is_matched(con, found, lost):
                return False

            result = con.execute(
                "UPDATE match_requests SET status=? WHERE found_item_id=? AND lost_item_id=? "
                "AND responder=? AND status='pending'",
                ("accepted" if accept else "rejected", found, lost, username),
            )
            if result.rowcount != 1:
                return False

            if accept:
                con.execute(
                    "INSERT OR IGNORE INTO matches (item1_id, item2_id) VALUES (?, ?)",
                    (found, lost),
                )
                # One found item and one lost item can only be confirmed once.
                others = con.execute(
                    "SELECT found_item_id, lost_item_id, requester, responder, created_at "
                    "FROM match_requests WHERE status='pending' "
                    "AND (found_item_id=? OR lost_item_id=?)",
                    (found, lost),
                ).fetchall()
                if others:
                    con.execute(
                        "UPDATE match_requests SET status='rejected' "
                        "WHERE status='pending' AND (found_item_id=? OR lost_item_id=?)",
                        (found, lost),
                    )
                    for other in others:
                        con.execute(
                            "INSERT INTO request_history "
                            "(found_item_id, lost_item_id, requester, responder, status,"
                            " created_at, ended_at) VALUES (?,?,?,?,?,?,?)",
                            (other[0], other[1], other[2], other[3], "rejected",
                             other[4], now),
                        )

            con.execute(
                "INSERT INTO request_history "
                "(found_item_id, lost_item_id, requester, responder, status,"
                " created_at, ended_at) VALUES (?,?,?,?,?,?,?)",
                (found, lost, requester, responder,
                 "accepted" if accept else "rejected", created_at, now),
            )
        return True

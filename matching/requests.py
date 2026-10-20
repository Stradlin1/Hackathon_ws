"""Mutual confirmation before contact details are shared."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path


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

    def create(self, direction: str, query_item_id: int, candidate_item_id: int, username: str) -> str:
        if direction not in ("lost", "found"):
            raise ValueError("无效的报告方向")
        found = candidate_item_id if direction == "lost" else query_item_id
        lost = query_item_id if direction == "lost" else candidate_item_id
        with sqlite3.connect(self.path) as con:
            found_owner = con.execute("SELECT user_id FROM found_items WHERE item_id=?", (found,)).fetchone()
            lost_owner = con.execute("SELECT user_id FROM lost_items WHERE item_id=?", (lost,)).fetchone()
            if found_owner is None or lost_owner is None:
                raise ValueError("无法获取物品所有者")
            requester = lost_owner[0] if direction == "lost" else found_owner[0]
            responder = found_owner[0] if direction == "lost" else lost_owner[0]
            if requester != username:
                raise PermissionError("不能为其他用户的物品发起匹配请求")
            con.execute(
                "INSERT OR IGNORE INTO match_requests "
                "(found_item_id,lost_item_id,requester,responder,status,created_at) "
                "VALUES (?,?,?,?,'pending',?)",
                (found, lost, requester, responder, int(time.time())),
            )
            row = con.execute(
                "SELECT status FROM match_requests WHERE found_item_id=? AND lost_item_id=?",
                (found, lost),
            ).fetchone()
        return row[0]

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

    def respond(self, username: str, found: int, lost: int, accept: bool) -> bool:
        with sqlite3.connect(self.path) as con:
            result = con.execute(
                "UPDATE match_requests SET status=? WHERE found_item_id=? "
                "AND lost_item_id=? AND responder=? AND status='pending'",
                ("accepted" if accept else "rejected", found, lost, username),
            )
            if result.rowcount != 1:
                return False
            if accept:
                con.execute(
                    "INSERT OR IGNORE INTO matches (item1_id, item2_id) VALUES (?, ?)",
                    (found, lost),
                )
        return True

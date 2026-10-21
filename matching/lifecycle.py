"""Non-destructive completion states for reports.

A report can be marked `returned` (the item went back to its owner) or
`archived` (the owner closed it for another reason) without deleting the row.
Items with a status leave the candidate pool and the browse page, but stay in
"我的记录" under 已处理 and can be restored.

The table is a new extension table; the existing five tables are untouched.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

STATUSES = ("returned", "archived")


def status_label(status: str | None, lost: bool | None = None) -> str:
    """Human label; a lost report is "found back", a found item is "returned"."""
    if status == "returned":
        return "已找回" if lost else "已归还"
    if status == "archived":
        return "已归档"
    return "进行中"


class Lifecycle:
    def __init__(self, db_path: str | Path = "items.db") -> None:
        self.path = str(db_path)
        with sqlite3.connect(self.path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS item_status (
                    item_id INTEGER PRIMARY KEY,
                    status TEXT NOT NULL CHECK (status IN ('returned', 'archived')),
                    updated_by TEXT NOT NULL,
                    updated_at INTEGER NOT NULL,
                    note TEXT NOT NULL DEFAULT ''
                )
            """)

    def set_status(self, item_id: int, status: str, updated_by: str, note: str = "") -> None:
        if status not in STATUSES:
            raise ValueError("未知的处理状态")
        with sqlite3.connect(self.path) as con:
            con.execute("""
                INSERT INTO item_status (item_id, status, updated_by, updated_at, note)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    status=excluded.status,
                    updated_by=excluded.updated_by,
                    updated_at=excluded.updated_at,
                    note=excluded.note
            """, (int(item_id), status, updated_by, int(time.time()), (note or "")[:80]))

    def clear(self, item_id: int) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute("DELETE FROM item_status WHERE item_id=?", (int(item_id),))

    def get(self, item_id: int) -> dict | None:
        with sqlite3.connect(self.path) as con:
            con.row_factory = sqlite3.Row
            row = con.execute(
                "SELECT item_id, status, updated_by, updated_at, note "
                "FROM item_status WHERE item_id=?",
                (int(item_id),),
            ).fetchone()
        return dict(row) if row else None

    def status(self, item_id: int) -> str | None:
        record = self.get(item_id)
        return record["status"] if record else None

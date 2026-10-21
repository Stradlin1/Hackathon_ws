"""Publication time and public-feed visibility for reports.

`items.time` is the date the item was lost or found, not the moment the report
was published. The public feed needs the latter to show "first published"
without touching the existing `items` table, so this extension table stores
`published_at` and the owner's public/private choice.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path


class ReportMeta:
    def __init__(self, db_path: str | Path = "items.db") -> None:
        self.path = str(db_path)
        with sqlite3.connect(self.path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS report_meta (
                    item_id INTEGER PRIMARY KEY,
                    published_at INTEGER NOT NULL,
                    public INTEGER NOT NULL DEFAULT 1
                )
            """)

    def publish(self, item_id: int, public: bool = True) -> None:
        """Record the first publication time; later calls only change visibility."""
        with sqlite3.connect(self.path) as con:
            con.execute("""
                INSERT INTO report_meta (item_id, published_at, public)
                VALUES (?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET public=excluded.public
            """, (int(item_id), int(time.time()), 1 if public else 0))

    def set_public(self, item_id: int, public: bool) -> None:
        with sqlite3.connect(self.path) as con:
            cursor = con.execute(
                "UPDATE report_meta SET public=? WHERE item_id=?",
                (1 if public else 0, int(item_id)),
            )
            if cursor.rowcount == 0:
                con.execute(
                    "INSERT INTO report_meta (item_id, published_at, public) VALUES (?, ?, ?)",
                    (int(item_id), int(time.time()), 1 if public else 0),
                )

    def get(self, item_id: int) -> dict | None:
        with sqlite3.connect(self.path) as con:
            con.row_factory = sqlite3.Row
            row = con.execute(
                "SELECT item_id, published_at, public FROM report_meta WHERE item_id=?",
                (int(item_id),),
            ).fetchone()
        return dict(row) if row else None

    def is_public(self, item_id: int) -> bool:
        """Rows without metadata predate the feature and stay public."""
        record = self.get(item_id)
        return True if record is None else bool(record["public"])

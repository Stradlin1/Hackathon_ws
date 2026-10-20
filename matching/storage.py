"""Additional SQLite tables; compatible with the existing item database."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class FingerprintStore:
    def __init__(self, db_path: str | Path = "items.db") -> None:
        self.path = str(db_path)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS item_fingerprints ("
                "item_id INTEGER PRIMARY KEY, fingerprint_json TEXT NOT NULL)"
            )

    def put(self, item_id: int, fingerprint: dict) -> None:
        payload = json.dumps(fingerprint, ensure_ascii=False)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT INTO item_fingerprints (item_id, fingerprint_json) VALUES (?, ?) "
                "ON CONFLICT(item_id) DO UPDATE SET fingerprint_json=excluded.fingerprint_json",
                (item_id, payload),
            )

    def get(self, item_id: int) -> dict | None:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT fingerprint_json FROM item_fingerprints WHERE item_id = ?", (item_id,)
            ).fetchone()
        if row is None:
            return None
        try:
            value = json.loads(row[0])
            return value if isinstance(value, dict) else None
        except (TypeError, ValueError):
            return None

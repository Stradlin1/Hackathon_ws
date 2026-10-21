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

    def delete(self, item_id: int) -> None:
        """Drop the stored fingerprint, e.g. when an owner withdraws a report."""
        with sqlite3.connect(self.path) as connection:
            connection.execute("DELETE FROM item_fingerprints WHERE item_id = ?", (item_id,))

    def merge(self, item_id: int, values: dict, source: str = 'user') -> dict:
        """Merge confirmed attribute values into a stored fingerprint.

        Only normalised attribute values are written; the question text and the
        user's raw wording are never stored. Merged fields are recorded in
        `confirmed` so the UI can tell user-supplied values from extracted ones.
        """
        fingerprint = self.get(item_id) or {'attributes': {}, 'method': 'rules'}
        attributes = dict(fingerprint.get('attributes') or {})
        used = []
        for field, value in values.items():
            if isinstance(value, str) and value:
                attributes[field] = value
                used.append(field)
        fingerprint['attributes'] = attributes
        if used:
            confirmed = set(fingerprint.get('confirmed') or [])
            confirmed.update(used)
            fingerprint['confirmed'] = sorted(confirmed)
        self.put(item_id, fingerprint)
        return fingerprint

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

"""Copy detection and traceability helpers.

A browser cannot be prevented from taking screenshots or saving files, so this
module does not pretend to block copying. It makes reuse visible:

- a short text fingerprint and publication time for every post;
- a perceptual dHash of uploaded images, compared against existing posts;
- near-duplicate text detection;
- a visible watermark on images shown in public/listing pages.

The watermark is generated for display only; the stored image and the embedding
stay clean.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HASH_SIZE = 8
NEAR_IMAGE_DISTANCE = 6
SIMILAR_TEXT_THRESHOLD = 0.92
SIMILAR_TEXT_MIN_CHARS = 12


def _normalise(text: str) -> str:
    return "".join((text or "").lower().split())


def text_fingerprint(text: str) -> str:
    """Short, stable hash of the normalised description."""
    return hashlib.sha256(_normalise(text).encode("utf-8")).hexdigest()[:10]


def _as_image(image) -> Image.Image:
    return image if isinstance(image, Image.Image) else Image.fromarray(np.asarray(image))


def image_dhash(image, hash_size: int = HASH_SIZE) -> str:
    """64-bit difference hash as hex; robust to scaling and small brightness shifts."""
    gray = _as_image(image).convert("L").resize(
        (hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = np.asarray(gray, dtype=np.int16)
    bits = pixels[:, 1:] > pixels[:, :-1]
    return np.packbits(bits.flatten()).tobytes().hex()


def hamming_distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def watermark(image, item_id, published_at=None) -> Image.Image:
    """Bottom band with the post id and (when it fits) the publish date."""
    base = _as_image(image).convert("RGB").copy()
    width, height = base.size
    band = max(18, height // 12)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([(0, height - band), (width, height)], fill=(0, 0, 0, 130))
    when = datetime.fromtimestamp(published_at).strftime("%Y-%m-%d") if published_at else ""
    text = f"404NotFound · #{str(item_id)[-6:]}"
    if when and width >= 240:
        text += f" · {when}"
    draw.text((6, height - band + 3), text, fill=(255, 255, 255, 235),
              font=ImageFont.load_default())
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


def publication_text(item_id: int, description: str, published_at) -> str:
    when = (datetime.fromtimestamp(published_at).strftime("%Y-%m-%d %H:%M")
            if published_at else "发布时间未记录")
    return f"首次发布于：{when} · 内容指纹 {text_fingerprint(description)}"


def find_similar_text(description: str, items, threshold: float = SIMILAR_TEXT_THRESHOLD,
                      min_chars: int = SIMILAR_TEXT_MIN_CHARS) -> dict | None:
    """Return the closest existing description above the threshold."""
    target = _normalise(description)
    if len(target) < min_chars:
        return None
    best = None
    for item in items:
        other = _normalise(getattr(item, "description", "") or "")
        if len(other) < min_chars:
            continue
        ratio = SequenceMatcher(None, target, other).ratio()
        if ratio >= threshold and (best is None or ratio > best["ratio"]):
            best = {"item_id": item.id, "ratio": ratio}
    return best


class ImageHashes:
    """Per-item perceptual hash; a new table, no changes to existing tables."""

    def __init__(self, db_path: str | Path = "items.db") -> None:
        self.path = str(db_path)
        with sqlite3.connect(self.path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS image_hashes (
                    item_id INTEGER PRIMARY KEY,
                    dhash TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
            """)

    def put(self, item_id: int, image) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute("""
                INSERT INTO image_hashes (item_id, dhash, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    dhash=excluded.dhash, created_at=excluded.created_at
            """, (int(item_id), image_dhash(image), int(time.time())))

    def delete(self, item_id: int) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute("DELETE FROM image_hashes WHERE item_id=?", (int(item_id),))

    def get(self, item_id: int) -> str | None:
        with sqlite3.connect(self.path) as con:
            row = con.execute(
                "SELECT dhash FROM image_hashes WHERE item_id=?", (int(item_id),)
            ).fetchone()
        return row[0] if row else None

    def find_near(self, image, exclude_item_id: int | None = None,
                  max_distance: int = NEAR_IMAGE_DISTANCE) -> list[dict]:
        target = image_dhash(image)
        with sqlite3.connect(self.path) as con:
            rows = con.execute("SELECT item_id, dhash FROM image_hashes").fetchall()
        hits = []
        for item_id, stored in rows:
            if exclude_item_id is not None and item_id == exclude_item_id:
                continue
            try:
                distance = hamming_distance(target, stored)
            except (TypeError, ValueError):
                continue
            if distance <= max_distance:
                hits.append({"item_id": item_id, "distance": distance})
        return sorted(hits, key=lambda hit: hit["distance"])

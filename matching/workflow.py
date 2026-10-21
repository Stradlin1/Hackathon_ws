"""Retrieve cross-modal candidates and start an interactive match session."""

from __future__ import annotations

import numpy as np

from . import models
from .fingerprint import fingerprint_from_text
from .storage import FingerprintStore


def counterpart_fingerprints(direction: str, db, store: FingerprintStore) -> list[dict]:
    """Fingerprints of the unmatched reports on the other side of the match.

    Used to pick pre-registration questions and to enrich an existing report.
    """
    if direction == "lost":
        items = db.get_unmatched_found_items()
    elif direction == "found":
        items = db.get_unmatched_lost_items()
    else:
        raise ValueError("未知的报告类型")
    pool = []
    for item in items:
        fingerprint = store.get(item.id)
        if fingerprint is None:
            fingerprint = fingerprint_from_text(item.description or "", generate=False)
        pool.append(fingerprint)
    return pool


def build_session(*, direction: str, item_id: int, query_embedding, fingerprint: dict,
                  username: str, db, store: FingerprintStore,
                  query_time=None, query_location=None,
                  include_matched: bool = False) -> dict:
    """Create a Streamlit-serializable session without persisting personal answers.

    `include_matched=True` is for offline evaluation: it ranks all reports on the
    other side, not just the unmatched pool.
    """
    if direction not in ("lost", "found"):
        raise ValueError("未知的报告类型")

    if direction == "lost":
        records = db.get_found_items() if include_matched else db.get_unmatched_found_items()
    else:
        records = db.get_lost_items() if include_matched else db.get_unmatched_lost_items()
    query = np.asarray(query_embedding, dtype=np.float32).reshape(-1)
    if not query.size or not np.isfinite(query).all():
        raise ValueError("无效的查询向量")
    candidates = []
    vectors = []
    for item in records:
        if item.id == item_id:
            continue
        emb = item.emb
        if emb is None:
            # Support legacy database rows whose embeddings were never stored.
            if direction == "lost" and item.image is not None:
                emb = models.encode_image(item.image)
            elif direction == "found" and item.description:
                emb = models.encode_text(item.description)
        if emb is None:
            continue
        vec = np.asarray(emb, dtype=np.float32).reshape(-1)
        if vec.shape != query.shape or not np.isfinite(vec).all():
            continue
        vectors.append(vec)
        known_fp = store.get(item.id)
        if known_fp is None:
            known_fp = fingerprint_from_text(item.description, generate=False)
            store.put(item.id, known_fp)
        candidates.append({
            "item_id": item.id,
            "fingerprint": known_fp,
            "description": item.description or "",
            "time": getattr(item, "time", None),
            "location": getattr(item, "location", None),
        })

    selected = []
    if vectors:
        # Cosine scores are returned from the public Sentence Transformers API.
        from sentence_transformers import util
        hits = util.semantic_search(query.reshape(1, -1), np.stack(vectors), top_k=min(8, len(vectors)))[0]
        for hit in hits:
            choice = dict(candidates[int(hit["corpus_id"])])
            choice["semantic_score"] = float(hit["score"])
            selected.append(choice)

    return {
        "direction": direction,
        "item_id": item_id,
        "user": username,
        "fingerprint": fingerprint,
        "candidates": selected,
        "answers": {},
        "asked": [],
        "query_time": query_time,
        "query_location": query_location,
    }

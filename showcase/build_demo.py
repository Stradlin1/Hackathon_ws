"""Build the static showcase data from the live items.db.

Reads only: it never writes to the database. Output is showcase/data/demo.json
plus the photos the slides reference and a QR code for the local app.

    python showcase/build_demo.py

The page does no scoring; every number comes from matching.engine.rank_candidates,
the same code the app and evaluate.py use.
"""

from __future__ import annotations

import json
import re
import shutil
import socket
import sys
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import qrcode  # noqa: E402

from db_manager import Database  # noqa: E402
from evaluate import evaluate_pair, summarize  # noqa: E402
from matching.engine import (  # noqa: E402
    DISPLAY, QUESTIONS, WEIGHTS, choose_question, rank_candidates,
)
from matching.fingerprint import FIELDS, display_value  # noqa: E402
from matching.storage import FingerprintStore  # noqa: E402
from matching.workflow import build_session  # noqa: E402
from seed_demo import SAMPLES  # noqa: E402

OUT = Path(__file__).resolve().parent
IMG = OUT / "assets" / "img"
FIELD_OF = {label: field for field, label in DISPLAY.items()}

# Hand-written English gloss of the lost description. Only used to check that the
# Chinese sentence lands where its English twin lands; the app itself never
# translates zh->en, and this line is never stored with an item.
EN_GLOSS = ("a white power bank with a red label on top, plastic, "
            "one Type-C port and one USB port")


def lan_address() -> str:
    """Best-effort LAN address so a phone can scan the QR on the same Wi-Fi."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def find_id(db: Database, description: str) -> int:
    row = db.cur.execute("SELECT id FROM items WHERE description=?", (description,)).fetchone()
    if row is None:
        raise SystemExit(f"数据库里找不到这条描述，先运行 seed_demo.py：{description[:24]}")
    return int(row[0])


def evidence_of(candidate: dict) -> tuple[float, float]:
    """Rebuild the evidence part of the score from the published match lists.

    rank_candidates already decided which fields agree or conflict; this only
    turns those lists back into weight sums so the page can re-mix them with
    the semantic score without re-implementing the comparison.
    """
    agreement = sum(WEIGHTS[FIELD_OF[name]] for name in candidate["matches"])
    conflict = sum(WEIGHTS[FIELD_OF[name]] for name in candidate["conflicts"])
    comparable = agreement + conflict
    if not comparable:
        return 0.0, 0.5
    evidence = (agreement - 0.8 * conflict) / comparable
    return evidence, (evidence + 1) / 2


class Analyse:
    """One lost/found pair: session, ranking and payload rows."""

    def __init__(self, db, store, lost_desc: str, found_desc: str):
        self.db = db
        self.lost_id = find_id(db, lost_desc)
        self.found_id = find_id(db, found_desc)
        self.lost = db.get_item(self.lost_id)
        self.fingerprint = store.get(self.lost_id)
        self.session = build_session(
            direction="lost", item_id=self.lost_id, query_embedding=self.lost.emb,
            fingerprint=self.fingerprint, username="showcase", db=db, store=store,
            query_time=self.lost.time, query_location=self.lost.location,
        )
        self.ranked = self.rank(self.session["fingerprint"], None)

    def rank(self, fingerprint, answers):
        return rank_candidates(
            fingerprint, self.session["candidates"], answers,
            query_time=self.session.get("query_time"),
            query_location=self.session.get("query_location"),
        )

    def rows(self, ranked, copied: dict[str, str], limit: int = 6) -> list[dict]:
        rows = []
        for row in ranked[:limit]:
            evidence, evidence01 = evidence_of(row)
            attrs = row.get("fingerprint") or {}
            attrs = attrs.get("attributes", attrs) if isinstance(attrs, dict) else {}
            photo = None
            for sample in SAMPLES:
                if sample["found"] == row["description"]:
                    source = sample["file"]
                    if source not in copied:
                        copied[source] = f"found-{len(copied) + 1:02d}.jpg"
                        shutil.copyfile(ROOT / "demo" / "photos" / source, IMG / copied[source])
                    photo = f"assets/img/{copied[source]}"
                    break
            rows.append({
                "id": row["item_id"],
                "desc": row["description"],
                "photo": photo,
                "score": round(float(row["score"]), 3),
                "base": round(float(row["base_score"]), 3),
                "prior": round(float(row["prior_bonus"]), 3),
                "semantic": round(float(row["semantic_score"]), 3),
                "evidence": round(evidence, 3),
                "evidence01": round(evidence01, 3),
                "matches": row["matches"],
                "conflicts": row["conflicts"],
                "attrs": {DISPLAY[field]: display_value(field, value)
                          for field, value in attrs.items() if field in FIELDS and value},
                "expected": row["item_id"] == self.found_id,
            })
        return rows


def option_label(field: str, value: str, description: str) -> str:
    """A human answer for the stand-in user, e.g. 有，是「AKG」标志."""
    display = display_value(field, value)
    hint = ""
    if field == "mark" and display == "标志":
        found = re.search(r"([A-Za-z]{2,12})\s*标志", description)
        hint = found.group(1) if found else ""
    return f"有，是「{hint}」{display}" if hint else f"有，是「{display}」"


def unit(vector) -> np.ndarray:
    arr = np.asarray(vector, dtype=float).reshape(-1)
    norm = float(np.linalg.norm(arr))
    return arr / norm if norm else arr


def similarity_matrix(db, candidates: list[dict]) -> dict:
    """Cosine between the candidate embeddings shown on the page.

    This is the image tower's own geometry: it explains why an absolute cosine
    cannot be read as a probability. Labels are the display categories.
    """
    labels, vectors = [], []
    for row in candidates:
        item = db.get_item(row["id"])
        labels.append(row["attrs"].get("类型") or row["desc"][:4])
        vectors.append(unit(item.emb))
    stacked = np.stack(vectors, axis=0)
    matrix = stacked @ stacked.T
    off_diagonal = matrix[~np.eye(len(vectors), dtype=bool)]
    return {
        "labels": labels,
        "values": [[round(float(value), 3) for value in line] for line in matrix],
        "band": {
            "min": round(float(off_diagonal.min()), 3),
            "max": round(float(off_diagonal.max()), 3),
            "mean": round(float(off_diagonal.mean()), 3),
        },
    }


def text_bridge(db, description: str, candidates: list[dict]) -> dict | None:
    """Compare the Chinese sentence with its English gloss in the shared space.

    Both rows score the same six images; if the orders agree, the multilingual
    text tower really is standing where the image tower expects. Optional: with
    no cached text encoder this returns None and the page hides the numbers
    instead of inventing them.
    """
    try:
        from matching.models import encode_text
        zh = unit(encode_text(description))
        en = unit(encode_text(EN_GLOSS))
    except (ImportError, OSError, RuntimeError, ValueError):
        return None
    vectors = [unit(db.get_item(row["id"]).emb) for row in candidates]
    zh_scores = [round(float(np.dot(zh, vec)), 3) for vec in vectors]
    en_scores = [round(float(np.dot(en, vec)), 3) for vec in vectors]
    zh_order = sorted(range(len(zh_scores)), key=lambda i: -zh_scores[i])
    en_order = sorted(range(len(en_scores)), key=lambda i: -en_scores[i])
    return {
        "zh": description,
        "en": EN_GLOSS,
        "zh_en": round(float(np.dot(zh, en)), 3),
        "zh_scores": zh_scores,
        "en_scores": en_scores,
        "same_order": zh_order == en_order,
        "dim": int(zh.size),
    }


def main() -> int:
    IMG.mkdir(parents=True, exist_ok=True)
    data_dir = OUT / "data"
    data_dir.mkdir(exist_ok=True)

    db = Database()
    try:
        store = FingerprintStore()
        copied: dict[str, str] = {}

        primary = Analyse(db, store, SAMPLES[0]["lost"], SAMPLES[0]["found"])
        candidates = primary.rows(primary.ranked, copied)

        # A real miss: semantic retrieval puts the suitcase first and the
        # headphones third. Answering the mark question demotes the decoy.
        miss = Analyse(db, store,
                       next(s["lost"] for s in SAMPLES if s["file"] == "耳机.jpg"),
                       next(s["found"] for s in SAMPLES if s["file"] == "耳机.jpg"))
        field = choose_question(miss.fingerprint, miss.ranked)
        target = next(r for r in miss.ranked if r["item_id"] == miss.found_id)
        answer = ((target.get("fingerprint") or {}).get("attributes") or {}).get(field)
        after = miss.rank(miss.fingerprint, {field: answer}) if (field and answer) else miss.ranked

        def position(ranked, item_id):
            return next((i for i, row in enumerate(ranked, 1) if row["item_id"] == item_id), None)

        clarify = {
            "lost": miss.lost.description,
            "question": QUESTIONS.get(field, "") if field else "",
            "field": field,
            "answer": display_value(field, answer) if (field and answer) else "",
            "options": ([option_label(field, answer, target["description"])]
                        if (field and answer) else []) + ["没有特别标记"],
            "before": miss.rows(miss.ranked, copied, 4),
            "after": miss.rows(after, copied, 4),
            "before_rank": position(miss.ranked, miss.found_id),
            "after_rank": position(after, miss.found_id),
            "target": miss.found_id,
        }

        pairs = [(find_id(db, s["lost"]), find_id(db, s["found"])) for s in SAMPLES]
        summary_on = summarize([evaluate_pair(db, store, l, f, use_priors=True) for l, f in pairs])
        summary_off = summarize([evaluate_pair(db, store, l, f, use_priors=False) for l, f in pairs])

        # Real embeddings for the "what is semantic" slide: the first 32 of the
        # 512 dimensions, scaled together so the bars are comparable.
        lost_vec = np.asarray(primary.lost.emb, dtype=float).reshape(-1)
        found_item = db.get_item(primary.found_id)
        found_vec = np.asarray(found_item.emb, dtype=float).reshape(-1)
        cosine = float(np.dot(lost_vec, found_vec) /
                       (np.linalg.norm(lost_vec) * np.linalg.norm(found_vec)))
        head = 32
        scale = float(max(np.abs(lost_vec[:head]).max(), np.abs(found_vec[:head]).max())) or 1.0
        semantic = {
            "dim": int(lost_vec.size),
            "head": head,
            "text": [round(float(v) / scale, 3) for v in lost_vec[:head]],
            "image": [round(float(v) / scale, 3) for v in found_vec[:head]],
            "cosine": round(cosine, 3),
        }

        principles = {
            "models": {
                "image": "sentence-transformers/clip-ViT-B-32",
                "text": "sentence-transformers/clip-ViT-B-32-multilingual-v1",
            },
            "dim": int(lost_vec.size),
            "matrix": similarity_matrix(db, candidates),
            "bridge": text_bridge(db, primary.lost.description, candidates),
        }

        def weights_of(row: dict) -> tuple[float, float]:
            agree = sum(WEIGHTS[FIELD_OF[name]] for name in row["matches"])
            conflict = sum(WEIGHTS[FIELD_OF[name]] for name in row["conflicts"])
            return round(agree, 2), round(conflict, 2)

        examples = []
        for index in (0, 1):
            row = primary.ranked[index]
            agree, conflict = weights_of(row)
            examples.append({
                "name": row["description"][:16],
                "agree": agree,
                "conflict": conflict,
                "evidence": round((agree - 0.8 * conflict) / (agree + conflict), 3)
                              if (agree + conflict) else 0.0,
                "semantic": round(float(row["semantic_score"]), 3),
                "prior": round(float(row["prior_bonus"]), 3),
                "score": round(float(row["score"]), 3),
                "candidate": index,
            })

        lan = lan_address()
        app_lan = f"http://{lan}:8501"
        qrcode.make(app_lan).save(IMG / "qr.png")

        payload = {
            "meta": {
                "built_at": date.today().isoformat(),
                "items": len(db.get_items()),
                "users": len(db.get_users()),
                "pairs": summary_on["pairs"],
                "top1_on": summary_on["top1"],
                "top1_off": summary_off["top1"],
                "mrr_on": round(summary_on["mrr"], 3),
                "mrr_off": round(summary_off["mrr"], 3),
                "app_local": "http://127.0.0.1:8501",
                "app_lan": app_lan,
            },
            "pair": {
                "lost": {"desc": primary.lost.description, "location": primary.lost.location,
                         "attrs": {DISPLAY[field]: display_value(field, value)
                                   for field, value in ((primary.fingerprint or {}).get("attributes") or {}).items()
                                   if field in FIELDS and value}},
                "found": {"desc": next(s["found"] for s in SAMPLES if s["file"] == SAMPLES[0]["file"]),
                          "photo": next((c["photo"] for c in candidates if c["expected"]), None)},
            },
            "weights": {"semantic": 0.72, "evidence": 0.28},
            "candidates": candidates,
            "semantic": semantic,
            "principles": principles,
            "formula": {"weights": WEIGHTS, "examples": examples},
            "clarify": clarify,
            "privacy": {"from": "alice", "to": "bob",
                        "email": "bob@example.invalid", "phone": "138 0000 0000"},
        }
        (data_dir / "demo.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"candidates={len(candidates)} photos={len(copied)}")
        print(f"top1 on/off = {summary_on['top1']}/{summary_off['top1']} of {summary_on['pairs']}")
        print(f"clarify field={clarify['field']} answer={clarify['answer']!r} "
              f"rank {clarify['before_rank']} -> {clarify['after_rank']}")
        bridge = principles["bridge"]
        print("bridge:", "missing" if bridge is None
              else f"zh-en={bridge['zh_en']} same_order={bridge['same_order']}")
        print(f"wrote {data_dir / 'demo.json'}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

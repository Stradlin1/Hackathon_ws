"""Offline retrieval evaluation.

By default the script uses the demo pairs from `seed_demo.SAMPLES` and
matches them by exact description in `items.db`. Custom labels use:

    [{"lost_id": 123, "found_id": 456, "note": "optional"}, ...]

Run from the repository root:

    python evaluate.py
    python evaluate.py --labels my_labels.json --verbose
    python evaluate.py --json

It ranks **all** found reports (including already matched ones), so history can
be evaluated. Both the with-prior and without-prior runs are printed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from db_manager import Database
from matching.engine import rank_candidates
from matching.fingerprint import fingerprint_from_text
from matching.storage import FingerprintStore
from matching.workflow import build_session
from seed_demo import SAMPLES


def demo_pairs(db) -> list[dict]:
    pairs = []
    for sample in SAMPLES:
        lost = db.cur.execute(
            "SELECT id FROM items WHERE description=?", (sample["lost"],)
        ).fetchone()
        found = db.cur.execute(
            "SELECT id FROM items WHERE description=?", (sample["found"],)
        ).fetchone()
        if lost is None or found is None:
            continue
        pairs.append({"lost_id": lost[0], "found_id": found[0], "note": sample["file"]})
    return pairs


def load_pairs(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("labels 文件必须是数组")
    pairs = []
    for row in data:
        if "lost_id" not in row or "found_id" not in row:
            raise ValueError("labels 每条需要 lost_id 与 found_id")
        pairs.append({
            "lost_id": int(row["lost_id"]),
            "found_id": int(row["found_id"]),
            "note": str(row.get("note", "")),
        })
    return pairs


def evaluate_pair(db, store, lost_id: int, found_id: int, use_priors: bool = True) -> dict:
    if not db.item_exists(lost_id) or not db.item_exists(found_id):
        raise ValueError(f"物品不存在：lost={lost_id} found={found_id}")
    lost = db.get_item(lost_id)
    if lost.emb is None:
        raise ValueError(f"失物 #{lost_id} 没有向量，无法评估")
    fingerprint = store.get(lost_id) or fingerprint_from_text(
        lost.description or "", generate=False)
    session = build_session(
        direction="lost", item_id=lost_id, query_embedding=lost.emb,
        fingerprint=fingerprint, username="evaluation", db=db, store=store,
        query_time=lost.time, query_location=lost.location, include_matched=True,
    )
    ranked = rank_candidates(
        session["fingerprint"], session["candidates"], None,
        query_time=session.get("query_time"),
        query_location=session.get("query_location"),
        use_priors=use_priors,
    )

    rank = None
    expected_score = None
    for index, row in enumerate(ranked, 1):
        if row["item_id"] == found_id:
            rank = index
            expected_score = row["score"]
            break
    top = ranked[0] if ranked else None
    return {
        "lost_id": lost_id,
        "found_id": found_id,
        "lost_desc": lost.description or "",
        "rank": rank,
        "expected_score": expected_score,
        "top_id": top["item_id"] if top else None,
        "top_desc": top["description"] if top else "",
        "top_score": top["score"] if top else None,
        "candidates": len(ranked),
    }


def summarize(results: list[dict]) -> dict:
    total = len(results)
    top1 = sum(1 for row in results if row["rank"] == 1)
    top5 = sum(1 for row in results if row["rank"] and row["rank"] <= 5)
    reciprocal = sum(1.0 / row["rank"] for row in results if row["rank"])
    return {
        "pairs": total,
        "top1": top1,
        "top5": top5,
        "mrr": (reciprocal / total) if total else 0.0,
        "missed": total - top1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", help="自定义 labels JSON；默认使用 seed_demo 的演示对")
    parser.add_argument("--verbose", action="store_true", help="逐对输出 rank 与 top-1")
    parser.add_argument("--json", action="store_true", help="输出 JSON，便于脚本消费")
    args = parser.parse_args()

    db = Database()
    try:
        store = FingerprintStore()
        pairs = load_pairs(args.labels) if args.labels else demo_pairs(db)
        if not pairs:
            print("没有可评估的配对：先运行 seed_demo.py，或用 --labels 指定。",
                  file=sys.stderr)
            return 1

        payload = {}
        for use_priors, label in ((True, "on"), (False, "off")):
            results = []
            for pair in pairs:
                row = evaluate_pair(db, store, pair["lost_id"], pair["found_id"],
                                    use_priors=use_priors)
                row["note"] = pair["note"]
                results.append(row)
            summary = summarize(results)
            payload[label] = {"summary": summary, "results": results}
            if not args.json:
                print(f"prior={label}  pairs={summary['pairs']}  "
                      f"Recall@1={summary['top1']}/{summary['pairs']}  "
                      f"Recall@5={summary['top5']}/{summary['pairs']}  "
                      f"MRR={summary['mrr']:.3f}  missed@1={summary['missed']}")
                if args.verbose:
                    for row in results:
                        rank = row["rank"] if row["rank"] else "miss"
                        print(f"  {row['note'] or row['lost_id']}: rank={rank}  "
                              f"top={row['top_desc']}  score={row['top_score']:.3f}"
                              if row["top_score"] is not None else
                              f"  {row['note'] or row['lost_id']}: rank={rank}")
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

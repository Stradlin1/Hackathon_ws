"""Deterministic reranking and information-gain-driven clarification."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Mapping

from .fingerprint import FIELDS, normalize_answer

WEIGHTS = {"category": 1.3, "color": 1.2, "material": 1.0, "shape": 1.1, "brand": 1.1, "mark": 2.0}
QUESTIONS = {
    "category": "你还记得丢失物品的具体类型吗？",
    "color": "你记得物品主要是什么颜色吗？",
    "material": "物品主要是什么材质的？",
    "shape": "你记得物品的外形或手柄形状吗？",
    "brand": "物品是什么品牌？不确定可以跳过。",
    "mark": "你还记得物品上的划痕、贴纸、挂绳等独特标记吗？请描述，不确定可跳过。",
}
DISPLAY = {"category": "类型", "color": "颜色", "material": "材质", "shape": "形状", "brand": "品牌", "mark": "特殊标记"}
MAX_QUESTIONS = 4


def _attrs(fp: Mapping | None) -> dict[str, str]:
    if not isinstance(fp, Mapping):
        return {}
    source = fp.get("attributes", fp)
    if not isinstance(source, Mapping):
        return {}
    return {key: value for key, value in source.items() if key in FIELDS and isinstance(value, str) and value}


def rank_candidates(query_fp: Mapping, candidates: list[dict], answers: Mapping[str, str] | None = None) -> list[dict]:
    """Rank candidates using CLIP similarity and literal matching evidence.

    Missing attributes are neutral. Positive and contradictory evidence have
    different effects; the resulting score is a ranking metric, not a probability.
    """
    query = {**_attrs(query_fp), **{k: v for k, v in (answers or {}).items() if v and k in FIELDS}}
    output: list[dict] = []
    for original in candidates:
        other = _attrs(original.get("fingerprint"))
        agreement = conflict = 0.0
        matches, contradictions = [], []
        for key, weight in WEIGHTS.items():
            if not query.get(key) or not other.get(key):
                continue
            if query[key].casefold() == other[key].casefold():
                agreement += weight
                matches.append(DISPLAY[key])
            else:
                conflict += weight
                contradictions.append(DISPLAY[key])
        comparable = agreement + conflict
        evidence = ((agreement - 0.8 * conflict) / comparable) if comparable else 0.0
        semantic = min(1.0, max(0.0, float(original["semantic_score"])))
        score = max(0.0, min(1.0, 0.72 * semantic + 0.28 * ((evidence + 1) / 2)))
        output.append({**original, "score": round(score, 5), "matches": matches, "conflicts": contradictions})
    return sorted(output, key=lambda candidate: (-candidate["score"], candidate["item_id"]))


def choose_question(query_fp: Mapping, ranked: list[dict], asked: list[str] | None = None) -> str | None:
    """Select the unknown attribute with maximum posterior-weighted information gain.

    Questions never expose the actual candidate attribute values.
    """
    query = _attrs(query_fp)
    asked_set = set(asked or [])
    if len(ranked) < 2 or len(asked_set) >= MAX_QUESTIONS:
        return None
    candidates = ranked[:8]
    max_score = max(item["score"] for item in candidates)
    weights = [math.exp(7 * (item["score"] - max_score)) for item in candidates]
    total = sum(weights)
    weights = [w / total for w in weights]
    best: tuple[float, str] | None = None
    for key in FIELDS:
        if key in asked_set or key in query:
            continue
        distribution = defaultdict(float)
        coverage = 0.0
        for cand, weight in zip(candidates, weights):
            value = _attrs(cand.get("fingerprint")).get(key)
            if value:
                distribution[value] += weight
                coverage += weight
        if len(distribution) < 2 or coverage < 0.45:
            continue
        # For a deterministic feature partition, mutual information equals
        # the entropy of its values, discounted by missing observations.
        entropy = -sum((v / coverage) * math.log2(v / coverage) for v in distribution.values())
        gain = coverage * entropy * (1 + 0.05 * WEIGHTS[key])
        if best is None or gain > best[0]:
            best = (gain, key)
    return best[1] if best else None


def add_answer(session: dict, field: str, raw_answer: str) -> str | None:
    if field not in QUESTIONS:
        raise ValueError("Unknown question")
    if field in session["asked"]:
        raise ValueError("Question already asked")
    normalized = normalize_answer(field, raw_answer)
    session["asked"].append(field)
    if normalized is not None:
        session["answers"][field] = normalized
    return normalized

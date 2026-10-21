"""Deterministic reranking and information-gain-driven clarification."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Mapping

from .fingerprint import FIELDS, display_value, normalize_answer

WEIGHTS = {"category": 1.3, "color": 1.2, "material": 1.0, "shape": 1.1, "brand": 1.1, "mark": 2.0}
ABSENT_MARK = "no special mark"

# Values that describe the same thing at a different granularity. Treated as a
# conflict, "水杯" (cup) versus "水瓶" (water bottle) cancelled a real match.
FAMILIES = {
    "category": {"cup": "drinkware", "water bottle": "drinkware",
                 "bag": "carry", "backpack": "carry"},
    "shape": {"round": "roundish", "cylindrical": "roundish", "oval": "roundish"},
}


def _related(field: str, left: str, right: str) -> bool:
    family = FAMILIES.get(field, {})
    return family.get(left) is not None and family.get(left) == family.get(right)
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
UNSURE = "不确定"

# Questions for the person holding the item, asked before retrieval instead of after.
INTAKE_QUESTIONS = {
    "category": "这件东西属于哪一类？",
    "color": "东西整体是什么颜色？",
    "material": "表面是什么材质？",
    "shape": "外形更接近哪一种？",
    "brand": "上面有品牌或型号字样吗？",
    "mark": "有没有贴纸、划痕、名字或序列号这类标记？",
}


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
            left, right = query.get(key), other.get(key)
            if not left or not right:
                continue
            if left.casefold() == right.casefold():
                # "Neither has a mark" is true of most objects, so two confirmed
                # absences say nothing about ownership. It stays neutral.
                if left.casefold() == ABSENT_MARK:
                    continue
                agreement += weight
                matches.append(DISPLAY[key])
            elif _related(key, left.casefold(), right.casefold()):
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


def _intake_options(field: str, pool: list[dict], limit: int = 5) -> list[tuple[str, str]]:
    counts: dict[str, int] = defaultdict(int)
    for attrs in pool:
        value = attrs.get(field)
        if value:
            counts[value] += 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    options = [(value, display_value(field, value)) for value, _ in ranked]
    if field == "mark" and all(value != ABSENT_MARK for value, _ in options):
        # "Nothing special" is a real answer the finder can give, and it prunes
        # candidates whose lost report claims a sticker, scratch or engraving.
        options.append((ABSENT_MARK, display_value("mark", ABSENT_MARK)))
    return options


def propose_intake_questions(query_fp: Mapping, pool_fingerprints: list, limit: int = 2) -> list[dict]:
    """Pick the questions worth asking the person who is holding the item.

    A field is worth asking only when the report does not know it yet and the pool
    of unmatched reports actually splits on it, so the answer changes the ranking.
    Questions are ranked by coverage x entropy x field weight, the same measure
    choose_question uses later, but over the whole pool and before any retrieval.
    """
    query = _attrs(query_fp)
    pool = [_attrs(fp) for fp in pool_fingerprints]
    if len(pool) < 2:
        return []
    scored: list[tuple[float, str]] = []
    for key in FIELDS:
        if key in query:
            continue
        distribution: dict[str, int] = defaultdict(int)
        coverage = 0
        for attrs in pool:
            value = attrs.get(key)
            if value:
                distribution[value] += 1
                coverage += 1
        if coverage < 2 or len(distribution) < 2:
            continue
        entropy = -sum((count / coverage) * math.log2(count / coverage)
                       for count in distribution.values())
        gain = (coverage / len(pool)) * entropy * (1 + 0.05 * WEIGHTS[key])
        scored.append((gain, key))
    scored.sort(reverse=True)
    picked = [key for _, key in scored[:limit]]
    # "Does it have a mark?" is the highest-weight dimension and only the person
    # holding the object can answer it, so it is worth one extra question whenever
    # any lost report mentions a mark, even if that field has no spread yet.
    if "mark" not in query and "mark" not in picked and any(attrs.get("mark") for attrs in pool):
        picked.append("mark")
    return [
        {"field": key, "question": INTAKE_QUESTIONS[key], "options": _intake_options(key, pool)}
        for key in picked
    ]


def add_answer(session: dict, field: str, raw_answer: str) -> str | None:
    if field not in QUESTIONS:
        raise ValueError("未知的问题")
    if field in session["asked"]:
        raise ValueError("该问题已经问过")
    normalized = normalize_answer(field, raw_answer)
    session["asked"].append(field)
    if normalized is not None:
        session["answers"][field] = normalized
    return normalized

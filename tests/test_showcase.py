"""The stand-alone showcase page: data contract, assets and offline rules."""

from __future__ import annotations

import json
import re
from pathlib import Path

SHOW = Path("showcase")
ALLOWED_URLS = {"http://127.0.0.1:8501", "http://www.w3.org/2000/svg"}


def payload() -> dict:
    return json.loads((SHOW / "data" / "demo.json").read_text(encoding="utf-8"))


def test_demo_data_shape():
    data = payload()
    assert set(data) == {"meta", "pair", "weights", "candidates", "semantic",
                         "principles", "formula", "clarify", "privacy"}
    assert data["meta"]["pairs"] >= 10
    assert len(data["candidates"]) == 6
    assert sum(1 for row in data["candidates"] if row["expected"]) == 1
    assert data["weights"] == {"semantic": 0.72, "evidence": 0.28}


def test_candidates_are_ranked_and_bounded():
    scores = [row["score"] for row in payload()["candidates"]]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= score <= 1.0 for score in scores)
    for row in payload()["candidates"]:
        assert 0.0 <= row["semantic"] <= 1.0
        assert -1.0 <= row["evidence"] <= 1.0
        assert set(row["matches"]) & set(row["conflicts"]) == set()


def test_every_referenced_photo_exists():
    data = payload()
    rows = list(data["candidates"]) + list(data["clarify"]["before"]) + list(data["clarify"]["after"])
    photos = [row["photo"] for row in rows if row["photo"]]
    assert photos
    for photo in photos:
        assert (SHOW / photo).is_file(), photo


def test_clarify_is_a_real_rerank():
    block = payload()["clarify"]
    assert block["field"] == "mark"
    assert block["options"]
    assert block["after_rank"] < block["before_rank"]
    same = {row["id"] for row in block["before"]} == {row["id"] for row in block["after"]}
    assert same, "the same candidates must be reordered, not swapped for new ones"


def test_html_assets_exist():
    html = (SHOW / "index.html").read_text(encoding="utf-8")
    assert html.count('class="slide') >= 13
    for rel in re.findall(r'(?:src|href)="(assets/[^"]+)"', html):
        assert (SHOW / rel).is_file(), rel


def test_page_has_no_network_dependencies():
    for name in ("index.html", "assets/stage.css", "assets/stage.js"):
        text = (SHOW / name).read_text(encoding="utf-8")
        for url in re.findall(r"https?://[^\s\"')]+", text):
            assert url.rstrip("/") in ALLOWED_URLS, f"{name} references {url}"


def test_semantic_block_is_real():
    data = payload()
    semantic = data["semantic"]
    assert semantic["dim"] == 512
    assert len(semantic["text"]) == len(semantic["image"]) == semantic["head"]
    assert all(-1.0 <= value <= 1.0 for value in semantic["text"] + semantic["image"])
    assert abs(semantic["cosine"] - data["candidates"][0]["semantic"]) < 0.002


def test_similarity_matrix_is_a_real_symmetric_gram():
    principles = payload()["principles"]
    matrix = principles["matrix"]
    values = matrix["values"]
    labels = matrix["labels"]
    assert len(labels) == len(values) == 6
    assert all(labels), "every row needs a label"
    for i, row in enumerate(values):
        assert len(row) == 6
        assert row[i] == 1.0, "a vector is identical to itself"
        for j, value in enumerate(row):
            assert -1.0 <= value <= 1.0
            assert abs(value - values[j][i]) < 1e-9, "cosine is symmetric"
    off = [values[i][j] for i in range(6) for j in range(6) if i != j]
    assert abs(min(off) - matrix["band"]["min"]) < 1e-9
    assert abs(max(off) - matrix["band"]["max"]) < 1e-9
    assert abs(sum(off) / len(off) - matrix["band"]["mean"]) < 0.001


def test_text_bridge_matches_the_semantic_block():
    data = payload()
    bridge = data["principles"]["bridge"]
    if bridge is None:  # no cached text encoder: the page hides these numbers
        return
    assert bridge["zh"] == data["pair"]["lost"]["desc"], "the aligned sentence is the one on screen"
    assert bridge["dim"] == data["principles"]["dim"] == 512
    count = len(data["candidates"])
    assert len(bridge["zh_scores"]) == len(bridge["en_scores"]) == count
    assert -1.0 <= bridge["zh_en"] <= 1.0
    zh_order = sorted(range(count), key=lambda i: -bridge["zh_scores"][i])
    en_order = sorted(range(count), key=lambda i: -bridge["en_scores"][i])
    assert (zh_order == en_order) is bridge["same_order"]
    # the Chinese sentence is the one that produced the semantic score on slide 04
    target = next(i for i, row in enumerate(data["candidates"]) if row["expected"])
    assert abs(bridge["zh_scores"][target] - data["semantic"]["cosine"]) < 0.001


def test_formula_examples_add_up():
    for example in payload()["formula"]["examples"]:
        expected = (0.72 * example["semantic"]
                    + 0.28 * ((example["evidence"] + 1) / 2)
                    + example["prior"])
        assert abs(expected - example["score"]) < 0.002


def test_open_demo_button_points_at_the_local_app():  # replaces the removed QR test
    html = (SHOW / "index.html").read_text(encoding="utf-8")
    assert 'id="openApp"' in html
    assert "qr.png" not in html
    assert payload()["meta"]["app_lan"].startswith("http://")

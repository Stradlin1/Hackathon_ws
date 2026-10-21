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
    assert set(data) == {"meta", "pair", "weights", "candidates", "clarify", "privacy"}
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
    assert html.count('class="slide') >= 9
    for rel in re.findall(r'(?:src|href)="(assets/[^"]+)"', html):
        assert (SHOW / rel).is_file(), rel


def test_page_has_no_network_dependencies():
    for name in ("index.html", "assets/stage.css", "assets/stage.js"):
        text = (SHOW / name).read_text(encoding="utf-8")
        for url in re.findall(r"https?://[^\s\"')]+", text):
            assert url in ALLOWED_URLS, f"{name} references {url}"


def test_qr_still_points_at_the_local_app():
    assert (SHOW / "assets" / "img" / "qr.png").is_file()
    assert payload()["meta"]["app_lan"].startswith("http://")

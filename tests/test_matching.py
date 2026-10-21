import sqlite3
import sys
import types

import numpy as np
import pytest

from matching.engine import add_answer, choose_question, rank_candidates
from matching.fingerprint import display_value, extract_known, fingerprint_from_text, normalize_answer
from matching.requests import MatchRequests
from matching.storage import FingerprintStore
from matching.workflow import build_session


def fp(**kw):
    return {"attributes": kw, "method": "rules"}


def candidate(cid, score, **kw):
    return {"item_id": cid, "semantic_score": score, "fingerprint": fp(**kw), "description": f"item-{cid}"}


def test_chinese_english_attribute_extraction():
    attrs = extract_known("黑色耳机，充电盒有红色贴纸")
    assert attrs["category"] == "earbuds"
    assert attrs["color"] == "black"
    assert attrs["mark"] == "red sticker"
    assert extract_known("a blue umbrella with curved handle")["shape"] == "curved handle"
    assert extract_known("白色充电宝")["category"] == "power bank"
    assert extract_known("机械键盘")["category"] == "keyboard"
    assert extract_known("无线鼠标")["category"] == "mouse"
    assert extract_known("FUGUANG 水杯")["brand"] == "fuguang"


def test_translate_caption_falls_back_to_english(monkeypatch):
    from matching import models

    monkeypatch.setattr(models, "_caption_translator", lambda: (_ for _ in ()).throw(OSError("no model")))
    assert models.translate_caption("a white cup") == "a white cup"


def test_display_value_translates_canonical_values():
    assert display_value("category", "umbrella") == "雨伞"
    assert display_value("color", "black") == "黑色"
    assert display_value("mark", "red sticker") == "红色贴纸"
    assert display_value("mark", "no special mark") == "无特殊标记"
    assert display_value("brand", "acme") == "acme"


def test_fingerprint_rejects_hallucinated_attributes():
    def fake_generator(prompt, **kwargs):
        return [{"generated_text": '{"category":"phone","color":"purple","brand":"apple"}'}]
    value = fingerprint_from_text("黑色雨伞", generator=fake_generator)
    assert value["attributes"] == {"category": "umbrella", "color": "black"}
    assert value["method"] == "rules"


def test_fingerprint_verifies_supported_generations():
    def fake_generator(prompt, **kwargs):
        return [{"generated_text": '{"category":"umbrella","color":"black"}'}]
    value = fingerprint_from_text("黑色雨伞", generator=fake_generator)
    assert value["method"] == "generative_verified"
    assert value["attributes"]["category"] == "umbrella"


def test_generated_open_vocabulary_brand_requires_literal_evidence():
    def fake_generator(prompt, **kwargs):
        return [{"generated_text": '{"brand":"Acme","color":"green"}'}]
    value = fingerprint_from_text("Acme牌黑色雨伞", generator=fake_generator)
    assert value["attributes"]["brand"] == "acme"
    assert value["attributes"]["color"] == "black"
    assert value["method"] == "generative_verified"
    assert normalize_answer("brand", "Acme") == "acme"


def test_visual_caption_and_manual_description_priority():
    actual = fingerprint_from_text("蓝色水杯", "a red cup with a scratch", generate=False)
    assert actual["attributes"]["color"] == "blue"
    assert actual["attributes"]["mark"] == "scratch"
    assert actual["method"] == "vision_caption_rules"


def test_unknown_answer_and_normalization():
    assert normalize_answer("color", "不记得") is None
    assert normalize_answer("color", "红色") == "red"
    assert normalize_answer("color", "???") is None
    with pytest.raises(ValueError):
        normalize_answer("username", "admin")


def test_active_question_uses_information_gain_without_answer_leak():
    query = fp(category="umbrella")
    candidates = [candidate(1, .82, category="umbrella", color="black", mark="red sticker"),
                  candidate(2, .81, category="umbrella", color="black", mark="blue sticker"),
                  candidate(3, .80, category="umbrella", color="black", mark="scratch")]
    ranked = rank_candidates(query, candidates)
    assert choose_question(query, ranked) == "mark"
    session = {"asked": [], "answers": {}}
    assert add_answer(session, "mark", "红色贴纸") == "red sticker"
    reranked = rank_candidates(query, candidates, session["answers"])
    assert reranked[0]["item_id"] == 1
    assert reranked[0]["score"] > reranked[1]["score"]
    assert choose_question(query, reranked, session["asked"]) is None


def test_missing_fields_not_penalized_as_conflicts():
    query = fp(category="cup", color="red")
    listed = rank_candidates(query, [candidate(1, .7, category="cup"),
                                     candidate(2, .7, category="cup", color="blue")])
    assert listed[0]["item_id"] == 1
    assert listed[0]["conflicts"] == []
    assert listed[1]["conflicts"] == ["颜色"]


def test_question_is_not_repeated():
    query = fp(category="umbrella")
    candidates = [candidate(1, .82, color="black"), candidate(2, .82, color="red")]
    ranked = rank_candidates(query, candidates)
    assert choose_question(query, ranked) == "color"
    session = {"asked": [], "answers": {}}
    assert add_answer(session, "color", "不记得") is None
    with pytest.raises(ValueError):
        add_answer(session, "color", "red")
    assert choose_question(query, ranked, session["asked"]) is None


def init_db(path):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, description TEXT)")
        db.execute("CREATE TABLE users (username TEXT PRIMARY KEY, email TEXT)")
        db.execute("CREATE TABLE found_items (item_id INTEGER, user_id TEXT)")
        db.execute("CREATE TABLE lost_items (item_id INTEGER, user_id TEXT)")
        db.execute("CREATE TABLE matches (item1_id INTEGER, item2_id INTEGER, PRIMARY KEY(item1_id,item2_id))")
        db.executemany("INSERT INTO items VALUES (?, ?)", [(100, "red umbrella"), (200, "red umbrella")])
        db.executemany("INSERT INTO users VALUES (?, ?)", [("finder", "finder@example.invalid"), ("owner", "owner@example.invalid")])
        db.execute("INSERT INTO found_items VALUES (100, 'finder')")
        db.execute("INSERT INTO lost_items VALUES (200, 'owner')")


def test_request_needs_mutual_confirmation(tmp_path):
    path = tmp_path / "items.db"
    init_db(path)
    request = MatchRequests(path)
    with pytest.raises(PermissionError):
        request.create("lost", 200, 100, "stranger")
    assert request.create("lost", 200, 100, "owner") == "pending"
    assert request.create("lost", 200, 100, "owner") == "pending"
    assert request.incoming("finder")[0]["requester"] == "owner"
    assert request.accepted("owner") == []
    assert request.respond("owner", 100, 200, True) is False
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 0
    assert request.respond("finder", 100, 200, True) is True
    assert request.respond("finder", 100, 200, True) is False
    assert request.accepted("owner")[0]["contact_username"] == "finder"
    assert request.accepted("finder")[0]["contact_username"] == "owner"
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT item1_id,item2_id FROM matches").fetchone() == (100, 200)


def test_request_rejection_blocks_contact(tmp_path):
    path = tmp_path / "items.db"
    init_db(path)
    request = MatchRequests(path)
    request.create("found", 100, 200, "finder")
    assert request.respond("owner", 100, 200, False)
    assert request.accepted("finder") == []
    assert request.outgoing("finder")[0]["status"] == "rejected"


def test_fingerprint_database_upsert(tmp_path):
    store = FingerprintStore(tmp_path / "test.db")
    store.put(5, fp(color="black"))
    assert store.get(5)["attributes"]["color"] == "black"
    store.put(5, fp(color="red"))
    assert store.get(5)["attributes"]["color"] == "red"
    assert store.get(999) is None


def test_workflow_retrieval_with_fake_embeddings(tmp_path, monkeypatch):
    class Entry:
        def __init__(self, id, emb, description="red umbrella", image=None):
            self.id, self.emb, self.description, self.image = id, emb, description, image

    class Database:
        def get_unmatched_found_items(self):
            return [Entry(1, np.array([1., 0.]), "red umbrella"),
                    Entry(2, np.array([0.3, 0.95]), "blue cup")]

    def semantic_search(q, c, top_k):
        q = np.asarray(q)[0]
        c = np.asarray(c)
        similarities = (c @ q) / (np.linalg.norm(c, axis=1) * np.linalg.norm(q))
        ids = np.argsort(-similarities)[:top_k]
        return [[{"corpus_id": int(i), "score": float(similarities[i])} for i in ids]]

    monkeypatch.setitem(sys.modules, "sentence_transformers", types.SimpleNamespace(util=types.SimpleNamespace(semantic_search=semantic_search)))
    session = build_session(direction="lost", item_id=42, query_embedding=np.array([1., 0.]),
                            fingerprint=fp(category="umbrella"), username="owner", db=Database(),
                            store=FingerprintStore(tmp_path / "test.db"))
    assert session["candidates"][0]["item_id"] == 1
    assert session["candidates"][0]["semantic_score"] == pytest.approx(1.0)
    assert session["answers"] == {}
    assert session["asked"] == []


def test_workflow_empty_candidates(tmp_path):
    class Database:
        def get_unmatched_found_items(self):
            return []
    session = build_session(direction="lost", item_id=42, query_embedding=np.array([1., 0.]),
                            fingerprint=fp(category="umbrella"), username="owner", db=Database(),
                            store=FingerprintStore(tmp_path / "test.db"))
    assert session["candidates"] == []

import pytest

from db_manager import Database, Item, User
from matching.lifecycle import Lifecycle, status_label


def test_status_roundtrip_and_restore(tmp_path):
    lifecycle = Lifecycle(tmp_path / "items.db")
    assert lifecycle.get(7) is None
    assert lifecycle.status(7) is None

    lifecycle.set_status(7, "returned", "alice", "已还给失主")
    record = lifecycle.get(7)
    assert record["status"] == "returned"
    assert record["updated_by"] == "alice"
    assert record["note"] == "已还给失主"

    lifecycle.set_status(7, "archived", "alice")
    assert lifecycle.status(7) == "archived"
    assert lifecycle.get(7)["note"] == ""

    lifecycle.clear(7)
    assert lifecycle.get(7) is None


def test_unknown_status_is_rejected(tmp_path):
    lifecycle = Lifecycle(tmp_path / "items.db")
    with pytest.raises(ValueError):
        lifecycle.set_status(1, "lost", "alice")


def test_status_labels():
    assert status_label("returned", lost=True) == "已找回"
    assert status_label("returned", lost=False) == "已归还"
    assert status_label("archived") == "已归档"
    assert status_label(None) == "进行中"


def test_closed_items_leave_the_unmatched_pools(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = Database()
    try:
        alice = User("alice", "", "alice@example.invalid")
        bob = User("bob", "", "bob@example.invalid")
        db.insert_user(alice)
        db.insert_user(bob)
        lost = Item(100, None, None, "lost mouse", 1, "图书馆")
        found = Item(200, None, None, "found mouse", 1, "图书馆")
        db.insert_item(lost)
        db.insert_item(found)
        db.insert_lost_item(lost, alice)
        db.insert_found_item(found, bob)

        assert [item.id for item in db.get_unmatched_lost_items()] == [100]
        assert [item.id for item in db.get_unmatched_found_items()] == [200]

        lifecycle = Lifecycle()
        lifecycle.set_status(100, "returned", "alice")
        lifecycle.set_status(200, "archived", "bob")
        assert db.get_item_status(100) == "returned"
        assert db.get_unmatched_lost_items() == []
        assert db.get_unmatched_found_items() == []

        lifecycle.clear(100)
        assert [item.id for item in db.get_unmatched_lost_items()] == [100]
    finally:
        db.close()

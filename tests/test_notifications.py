import sqlite3

import numpy as np

from db_manager import Item
from matching.notifications import Notifications, notify_for_found_item
from matching.storage import FingerprintStore


def make_item(item_id, emb, description="绿色鼠标", location="图书馆"):
    return Item(item_id, None, np.asarray(emb, dtype=np.float32), description, 1, location)


def fingerprint(**attributes):
    return {"attributes": attributes, "method": "rules"}


class FakeDB:
    def __init__(self, items, matched=(), statuses=None):
        self.items = {item.id: item for item in items}
        self.matched = set(matched)
        self.statuses = statuses or {}

    def item_exists(self, item_id):
        return item_id in self.items

    def get_item(self, item_id):
        return self.items[item_id]

    def get_lost_item_matches(self, item_id):
        return [1] if item_id in self.matched else []

    def get_item_status(self, item_id):
        return self.statuses.get(item_id)


def test_subscribe_is_idempotent_and_toggles(tmp_path):
    store = Notifications(tmp_path / "items.db")
    assert store.subscribe_item("alice", 10) is True
    assert store.subscribe_item("alice", 10) is False
    assert store.is_subscribed("alice", 10) is True
    assert store.toggle_item("alice", 10) is False
    assert store.is_subscribed("alice", 10) is False
    assert store.toggle_item("alice", 10) is True


def test_notifications_are_deduplicated_and_read(tmp_path):
    path = tmp_path / "items.db"
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE items "
                    "(id INTEGER PRIMARY KEY, description TEXT, location TEXT, time INTEGER)")
        con.execute("INSERT INTO items VALUES (100, '绿色鼠标', '图书馆', 1)")
    store = Notifications(path)
    store.subscribe_item("alice", 10)
    subscription = store.item_subscriptions()[0]

    assert store.add("alice", 100, 10, subscription["id"], 0.5) is True
    assert store.add("alice", 100, 10, subscription["id"], 0.5) is False
    assert store.unread_count("alice") == 1
    record = store.list("alice")[0]
    assert record["found_desc"] == "绿色鼠标"
    assert record["lost_item_id"] == 10

    store.mark_read("alice", record["id"])
    assert store.unread_count("alice") == 0
    assert store.list("alice")[0]["read_at"] is not None


def test_mark_all_and_delete_for_item(tmp_path):
    path = tmp_path / "items.db"
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE items "
                    "(id INTEGER PRIMARY KEY, description TEXT, location TEXT, time INTEGER)")
        con.executemany("INSERT INTO items VALUES (?, ?, ?, ?)",
                        [(100, "found", "图书馆", 1), (101, "found2", "食堂", 2)])
    store = Notifications(path)
    store.subscribe_item("alice", 10)
    subscription = store.item_subscriptions()[0]["id"]
    store.add("alice", 100, 10, subscription, 0.5)
    store.add("alice", 101, 10, subscription, 0.6)

    assert store.unread_count("alice") == 2
    store.mark_all_read("alice")
    assert store.unread_count("alice") == 0

    store.delete_for_item(10)
    assert store.item_subscriptions() == []
    assert store.list("alice") == []


def test_notify_creates_alert_above_threshold(tmp_path):
    path = tmp_path / "items.db"
    store = FingerprintStore(path)
    notifications = Notifications(path)
    lost = make_item(10, [1.0, 0.0])
    found = make_item(20, [1.0, 0.0])
    store.put(10, fingerprint(category="mouse", color="green"))
    notifications.subscribe_item("alice", 10)

    created = notify_for_found_item(
        found, fingerprint(category="mouse", color="green"), FakeDB([lost, found]),
        store, "bob", notifications=notifications)

    assert created == 1
    assert notifications.unread_count("alice") == 1


def test_notify_skips_low_scores_missing_vectors_and_self(tmp_path):
    path = tmp_path / "items.db"
    store = FingerprintStore(path)
    notifications = Notifications(path)
    lost = make_item(10, [0.0, 1.0], "白色水杯")
    found = make_item(20, [1.0, 0.0], "绿色鼠标")
    store.put(10, fingerprint(category="cup", color="white"))
    notifications.subscribe_item("alice", 10)

    created = notify_for_found_item(
        found, fingerprint(category="mouse", color="green"), FakeDB([lost, found]),
        store, "bob", notifications=notifications)
    assert created == 0

    matched = notify_for_found_item(
        make_item(30, [1.0, 0.0]), fingerprint(category="cup", color="white"),
        FakeDB([lost, make_item(30, [1.0, 0.0])], matched={10}),
        store, "bob", notifications=Notifications(path))
    assert matched == 0

    self_alert = notify_for_found_item(
        make_item(40, [1.0, 0.0]), fingerprint(category="cup", color="white"),
        FakeDB([lost, make_item(40, [1.0, 0.0])]),
        store, "alice", notifications=Notifications(path))
    assert self_alert == 0


def test_notify_skips_lost_items_without_vectors(tmp_path):
    path = tmp_path / "items.db"
    store = FingerprintStore(path)
    notifications = Notifications(path)
    lost = Item(10, None, None, "绿色鼠标", 1, "图书馆")
    found = make_item(20, [1.0, 0.0])
    notifications.subscribe_item("alice", 10)

    created = notify_for_found_item(
        found, fingerprint(category="mouse"), FakeDB([lost, found]),
        store, "bob", notifications=notifications)
    assert created == 0


def test_notify_skips_closed_lost_items(tmp_path):
    path = tmp_path / "items.db"
    store = FingerprintStore(path)
    notifications = Notifications(path)
    lost = make_item(10, [1.0, 0.0])
    found = make_item(20, [1.0, 0.0])
    store.put(10, fingerprint(category="mouse", color="green"))
    notifications.subscribe_item("alice", 10)

    created = notify_for_found_item(
        found, fingerprint(category="mouse", color="green"),
        FakeDB([lost, found], statuses={10: "returned"}),
        store, "bob", notifications=notifications)
    assert created == 0

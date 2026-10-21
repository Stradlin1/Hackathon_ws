import sqlite3
import time

import pytest

from matching.requests import (MAX_PENDING_PER_FOUND, REJECT_COOLDOWN_SECONDS,
                               MatchRequests, pair_ids)


def init_db(path, lost=2):
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, description TEXT)")
        con.execute("CREATE TABLE users (username TEXT PRIMARY KEY, email TEXT)")
        con.execute("CREATE TABLE found_items (item_id INTEGER, user_id TEXT)")
        con.execute("CREATE TABLE lost_items (item_id INTEGER, user_id TEXT)")
        con.execute("CREATE TABLE matches "
                    "(item1_id INTEGER, item2_id INTEGER, PRIMARY KEY (item1_id, item2_id))")
        con.execute("INSERT INTO items VALUES (100, 'found umbrella')")
        con.execute("INSERT INTO users VALUES ('finder', 'finder@example.invalid')")
        con.execute("INSERT INTO found_items VALUES (100, 'finder')")
        for index in range(lost):
            item_id = 200 + index
            owner = f'owner{index + 1}'
            con.execute("INSERT INTO items VALUES (?, 'lost umbrella')", (item_id,))
            con.execute("INSERT INTO users VALUES (?, ?)", (owner, f'{owner}@example.invalid'))
            con.execute("INSERT INTO lost_items VALUES (?, ?)", (item_id, owner))


def test_pair_ids_for_both_directions():
    assert pair_ids('lost', 200, 100) == (100, 200)
    assert pair_ids('found', 100, 200) == (100, 200)
    with pytest.raises(ValueError):
        pair_ids('sideways', 1, 2)


def test_new_pair_is_requestable(tmp_path):
    path = tmp_path / 'items.db'
    init_db(path)
    requests = MatchRequests(path)
    assert requests.state_pair(100, 200) == {'status': None, 'cooldown': 0,
                                             'can_request': True}


def test_rejection_can_be_retried_after_cooldown(tmp_path):
    path = tmp_path / 'items.db'
    init_db(path, lost=1)
    requests = MatchRequests(path)

    assert requests.create('lost', 200, 100, 'owner1') == 'pending'
    assert requests.respond('finder', 100, 200, False) is True
    state = requests.state_pair(100, 200)
    assert state['status'] == 'rejected'
    assert state['can_request'] is False
    assert state['cooldown'] > 0

    with pytest.raises(ValueError):
        requests.create('lost', 200, 100, 'owner1')

    with sqlite3.connect(path) as con:
        con.execute(
            "UPDATE request_history SET ended_at=? "
            "WHERE found_item_id=100 AND lost_item_id=200",
            (int(time.time()) - REJECT_COOLDOWN_SECONDS - 1,),
        )
    assert requests.create('lost', 200, 100, 'owner1') == 'pending'
    assert requests.state_pair(100, 200)['status'] == 'pending'


def test_pending_requests_are_capped_per_found_item(tmp_path):
    path = tmp_path / 'items.db'
    init_db(path, lost=4)
    requests = MatchRequests(path)

    for index in range(MAX_PENDING_PER_FOUND):
        assert requests.create('lost', 200 + index, 100, f'owner{index + 1}') == 'pending'

    with pytest.raises(ValueError):
        requests.create('lost', 200 + MAX_PENDING_PER_FOUND, 100,
                        f'owner{MAX_PENDING_PER_FOUND + 1}')


def test_accept_closes_other_pending_requests(tmp_path):
    path = tmp_path / 'items.db'
    init_db(path, lost=2)
    requests = MatchRequests(path)
    assert requests.create('lost', 200, 100, 'owner1') == 'pending'
    assert requests.create('lost', 201, 100, 'owner2') == 'pending'

    assert requests.respond('finder', 100, 200, True) is True
    assert requests.state_pair(100, 201)['status'] == 'rejected'
    assert requests.respond('finder', 100, 201, True) is False
    assert requests.accepted('owner2') == []
    assert requests.accepted('owner1')[0]['contact_username'] == 'finder'

    with sqlite3.connect(path) as con:
        assert con.execute("SELECT item1_id, item2_id FROM matches").fetchall() == [(100, 200)]


def test_matched_item_cannot_be_requested_again(tmp_path):
    path = tmp_path / 'items.db'
    init_db(path, lost=3)
    requests = MatchRequests(path)
    requests.create('lost', 200, 100, 'owner1')
    assert requests.respond('finder', 100, 200, True) is True

    with pytest.raises(ValueError, match='已经配对'):
        requests.create('lost', 202, 100, 'owner3')

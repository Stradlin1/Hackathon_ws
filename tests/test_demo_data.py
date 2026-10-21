"""Demo accounts and demo photos are reproducible from the repository."""

from __future__ import annotations

from pathlib import Path

import bcrypt

from create_demo_users import ACCOUNTS, build_config
from seed_demo import SAMPLES, SOURCE_DIRS


def test_every_demo_account_gets_a_bcrypt_hash():
    config = build_config()
    users = config['credentials']['usernames']
    assert set(users) == set(ACCOUNTS)
    for username, (display, email, password) in ACCOUNTS.items():
        entry = users[username]
        assert entry['name'] == display
        assert entry['email'] == email
        assert entry['password'].startswith('$2')
        assert bcrypt.checkpw(password.encode(), entry['password'].encode())


def test_cookie_key_is_fresh_each_run():
    first = build_config()['cookie']
    second = build_config()['cookie']
    assert first['name'] == second['name'] == 'lost_found_auth'
    assert first['key'] != second['key']
    assert len(first['key']) >= 32


def test_committed_demo_photos_cover_every_sample():
    assert SOURCE_DIRS[0] == Path('demo/photos')
    missing = [sample['file'] for sample in SAMPLES
               if not (SOURCE_DIRS[0] / sample['file']).exists()]
    assert missing == []

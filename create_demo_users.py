"""Create config_auth.yaml with the three demo accounts.

The passwords are public on purpose: this file only ever backs a local demo. A
fresh random cookie key is generated on every run, so the file stays local and
does not need to be shared between machines.

    python create_demo_users.py           # refuses to overwrite
    python create_demo_users.py --force   # replace an existing config_auth.yaml
"""

from __future__ import annotations

import argparse
import secrets
from pathlib import Path

import bcrypt
import yaml

CONFIG = Path('config_auth.yaml')

ACCOUNTS = {
    'alice': ('Alice', 'alice@example.invalid', 'demo-pass-alice'),
    'bob': ('Bob', 'bob@example.invalid', 'demo-pass-bob'),
    'demo': ('Demo User', 'demo@example.invalid', 'Demo@1234'),
}


def build_config() -> dict:
    """Same shape as config_auth.example.yaml, with hashed demo passwords."""
    usernames = {}
    for username, (display, email, password) in ACCOUNTS.items():
        usernames[username] = {
            'email': email,
            'name': display,
            'password': bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode(),
        }
    return {
        'credentials': {'usernames': usernames},
        'cookie': {
            'name': 'lost_found_auth',
            'key': secrets.token_urlsafe(32),
            'expiry_days': 7,
        },
        'preauthorized': {'emails': []},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--force', action='store_true',
                        help='覆盖已有的 config_auth.yaml（会丢掉现有账号）')
    args = parser.parse_args()

    if CONFIG.exists() and not args.force:
        raise SystemExit('config_auth.yaml 已存在；确认要覆盖请加 --force。')

    CONFIG.write_text(
        yaml.safe_dump(build_config(), allow_unicode=True, sort_keys=False),
        encoding='utf-8',
    )
    CONFIG.chmod(0o600)
    print('已写入 config_auth.yaml：alice / bob / demo')
    print('密码见 README「3. 配置账号」；cookie key 每次随机生成。')


if __name__ == '__main__':
    main()

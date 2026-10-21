"""Seed demo lost/found items from the photos in demo/photos (fallback: input/).

Four photos become found items owned by bob; matching lost descriptions
become lost items owned by alice. Run from the repository root:

    HF_HUB_OFFLINE=1 python seed_demo.py

The photos under demo/photos are committed so a fresh clone reproduces the same
demo; input/ stays a private fallback that is never committed. The script refuses
to run when items.db already contains items.
"""

from __future__ import annotations

import secrets
import time
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

from db_manager import Database, Item, User
from matching.fingerprint import fingerprint_from_text
from matching.models import clean_image, encode_image, encode_text
from matching.storage import FingerprintStore

SOURCE_DIRS = (Path('demo/photos'), Path('input'))
SAMPLES = [
    {
        'file': '充电宝.jpg',
        'found': '白色长方形充电宝，塑料外壳，顶部有红色标签贴纸，侧面有 USB-C 和 USB-A 接口',
        'lost': '白色长方形充电宝，塑料外壳，顶部贴着红色标签，带 USB-C 和 USB-A 接口',
        'location': '图书馆',
    },
    {
        'file': '水杯.jpg',
        'found': '透明圆柱形塑料水杯，亮绿色杯盖，杯身印有 FUGUANG',
        'lost': '透明圆柱形塑料水杯，亮绿色杯盖，杯身下部有 FUGUANG 字母',
        'location': '自习区',
    },
    {
        'file': '键盘.jpg',
        'found': '白色长方形机械键盘，塑料键帽，带白色数据线',
        'lost': '白色长方形机械键盘，塑料键帽，带一根白色数据线',
        'location': '实验室',
    },
    {
        'file': '鼠标.jpg',
        'found': '浅绿色椭圆形无线鼠标，塑料外壳，中间有电量显示屏',
        'lost': '浅绿色椭圆形无线鼠标，塑料外壳，滚轮下方有电量显示',
        'location': '图书馆',
    },
]


def main() -> None:
    config = yaml.safe_load(Path('config_auth.yaml').read_text(encoding='utf-8'))
    accounts = config.get('credentials', {}).get('usernames', {})

    db = Database()
    try:
        if db.get_items():
            raise SystemExit('items.db 里已经有物品；为避免重复，先备份并清空后再运行。')

        def owner(username: str) -> User:
            user = db.get_user(username)
            if user is None:
                account = accounts.get(username, {})
                user = User(username, '', account.get('email', ''))
                db.insert_user(user)
            return user

        alice = owner('alice')
        bob = owner('bob')
        store = FingerprintStore()
        used: set[int] = set()
        stamp = int(time.time())

        for sample in SAMPLES:
            path = next((base / sample['file'] for base in SOURCE_DIRS
                         if (base / sample['file']).exists()), None)
            if path is None:
                raise SystemExit(f"缺少图片：{sample['file']}（找过 demo/photos 与 input）")

            with Image.open(path) as raw:
                picture = clean_image(raw)
            image = np.asarray(picture)
            found_fingerprint = fingerprint_from_text(sample['found'], generate=False)
            lost_fingerprint = fingerprint_from_text(sample['lost'], generate=False)

            def new_id() -> int:
                while True:
                    value = secrets.randbits(62)
                    if value and value not in used and not db.item_exists(value):
                        used.add(value)
                        return value

            found = Item(new_id(), image, encode_image(picture), sample['found'], stamp, sample['location'])
            db.insert_item(found)
            db.insert_found_item(found, bob)
            store.put(found.id, found_fingerprint)

            lost = Item(new_id(), None, encode_text(sample['lost']), sample['lost'], stamp, sample['location'])
            db.insert_item(lost)
            db.insert_lost_item(lost, alice)
            store.put(lost.id, lost_fingerprint)

            print(f"found #{found.id} @bob  {sample['found']}")
            print(f"lost  #{lost.id} @alice {sample['lost']}")

        print(f'完成：{len(SAMPLES)} 件拾获（bob）+ {len(SAMPLES)} 件失物（alice）。')
    finally:
        db.close()


if __name__ == '__main__':
    main()

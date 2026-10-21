"""Seed demo lost/found items from the photos in demo/photos (fallback: input/).

Twelve photos become found items owned by bob; matching lost descriptions
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
from matching.content_hash import ImageHashes
from matching.fingerprint import fingerprint_from_text
from matching.models import clean_image, encode_image, encode_text
from matching.report_meta import ReportMeta
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
    {
        'file': '耳机.jpg',
        'found': '黑色头戴式耳机，塑料耳罩，耳罩外侧印有白色 AKG 标志，带一根黑色线缆',
        'lost': '黑色头戴式耳机，耳罩侧面有白色 AKG 字母，耳机线是黑色的',
        'location': '图书馆',
    },
    {
        'file': '钱包.jpg',
        'found': '米色老花图案长款拉链钱包，棕色皮革包边，顶部挂着一串金属钥匙扣',
        'lost': '米色花纹长钱包，拉链款，棕色皮边，上面挂着一串钥匙',
        'location': '食堂',
    },
    {
        'file': '棒球帽.jpg',
        'found': '青绿色棒球帽，正面绣有 CHARLOTTE HORNETS 字样和紫色黄蜂图案，帽顶有紫色扣子',
        'lost': '墨绿色棒球帽，正面绣着 CHARLOTTE HORNETS 和一只黄蜂，帽顶有个紫色小扣',
        'location': '体育中心',
    },
    {
        'file': '背包.jpg',
        'found': '黑色拉杆双肩包，布料外壳，底部有两个滚轮，前面有拉链袋和提手',
        'lost': '黑色带轮子的双肩背包，可以拉着走，底部两个轮子，黑色布面',
        'location': '教室',
    },
    {
        'file': '围巾.jpg',
        'found': '橙红色针织围巾，表面有细密纹理，两端是长流苏，挂在模特架上',
        'lost': '橙红色毛线围巾，两头有流苏，颜色偏砖红',
        'location': '自习区',
    },
    {
        'file': '手提包.jpg',
        'found': '米色翻盖单肩包，翻盖上印着绿色植物图案，包身和肩带是黑色',
        'lost': '米色帆布单肩包，盖子上有绿色小花印花，配黑色背带',
        'location': '礼堂',
    },
    {
        'file': '行李箱.jpg',
        'found': '黑色布面行李箱，带拉链、顶部提手和底部滚轮，放在室内地板上',
        'lost': '黑色行李箱，布面的，有拉链和拉杆，轮子有点响',
        'location': '停车场',
    },
    {
        'file': '雨伞.jpg',
        'found': '彩色条纹雨伞，伞面由红黄蓝绿相间的放射状条纹组成',
        'lost': '彩虹条纹雨伞，打开后是红黄蓝绿的放射状色块',
        'location': '主入口',
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
        meta = ReportMeta()
        hashes = ImageHashes()
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
            meta.publish(found.id)
            hashes.put(found.id, picture)

            lost = Item(new_id(), None, encode_text(sample['lost']), sample['lost'], stamp, sample['location'])
            db.insert_item(lost)
            db.insert_lost_item(lost, alice)
            store.put(lost.id, lost_fingerprint)
            meta.publish(lost.id)

            print(f"found #{found.id} @bob  {sample['found']}")
            print(f"lost  #{lost.id} @alice {sample['lost']}")

        print(f'完成：{len(SAMPLES)} 件拾获（bob）+ {len(SAMPLES)} 件失物（alice）。')
    finally:
        db.close()


if __name__ == '__main__':
    main()

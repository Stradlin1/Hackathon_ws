"""Seed a multi-user demo from the photos in demo/photos (fallback: input/).

Twenty-two photos become found items spread over six accounts; every account also
owns a few text-only lost reports, so each user has both sides of the flow:
3–4 found and 4–5 lost per account, 22 found and 28 lost in total.

The found reports read like a finder typing quickly; the matching lost reports
describe the same object with different words, which is what makes retrieval
and the evidence rerank interesting. Six extra lost reports have no matching
photo and act as distractors.

    HF_HUB_OFFLINE=1 python seed_demo.py

Existing items make the script refuse to run: back up and remove items.db
first. demo/photos is committed; input/ stays a private, uncommitted fallback.
"""

from __future__ import annotations

import secrets
import time
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

from create_demo_users import ACCOUNTS
from db_manager import Database, Item, User
from matching.content_hash import ImageHashes
from matching.fingerprint import fingerprint_from_text
from matching.models import clean_image, encode_image, encode_text
from matching.report_meta import ReportMeta
from matching.storage import FingerprintStore

SOURCE_DIRS = (Path('demo/photos'), Path('input'))

# Every entry links one photo (owned by found_owner) with the report a
# different user filed for the same object (owned by lost_owner).
SAMPLES = [
    {
        'file': '充电宝.jpg',
        'found_owner': 'alice', 'lost_owner': 'bob',
        'found': '在图书馆三楼捡到的，一个白色充电宝，塑料外壳，顶部贴了红色小标签，有 Type-C 和 USB 口',
        'lost': '白色充电宝丢了，塑料的，顶部贴着红色标签，一个 Type-C 一个 USB 接口',
        'location': '图书馆',
    },
    {
        'file': '水杯.jpg',
        'found_owner': 'bob', 'lost_owner': 'carol',
        'found': '自习区捡到一个透明塑料水杯，绿色杯盖，杯身上印着 FUGUANG',
        'lost': '透明塑料水杯忘在自习区了，亮绿色杯盖，杯身下面有 FUGUANG 字母',
        'location': '自习区',
    },
    {
        'file': '键盘.jpg',
        'found_owner': 'carol', 'lost_owner': 'david',
        'found': '实验室捡到的白色机械键盘，塑料键帽，连着一根白色数据线',
        'lost': '白色机械键盘落在实验室，塑料键帽，带一根白色数据线',
        'location': '实验室',
    },
    {
        'file': '鼠标.jpg',
        'found_owner': 'david', 'lost_owner': 'erin',
        'found': '图书馆捡到一个浅绿色的无线鼠标，塑料壳，滚轮下面有个电量显示屏',
        'lost': '浅绿色无线鼠标不见了，塑料外壳，滚轮下方有电量显示',
        'location': '图书馆',
    },
    {
        'file': '耳机.jpg',
        'found_owner': 'erin', 'lost_owner': 'frank',
        'found': '在图书馆捡到黑色头戴耳机，耳罩上有白色 AKG 标志，带黑色线',
        'lost': '黑色头戴式耳机丢了，耳罩侧面印着 AKG，线也是黑色的',
        'location': '图书馆',
    },
    {
        'file': '钱包.jpg',
        'found_owner': 'frank', 'lost_owner': 'alice',
        'found': '食堂捡到一个米色老花图案的长钱包，拉链款，棕色皮边，上面挂着钥匙扣',
        'lost': '米色花纹长钱包落在食堂，拉链的，棕色包边，钥匙扣还挂在上面',
        'location': '食堂',
    },
    {
        'file': '棒球帽.jpg',
        'found_owner': 'alice', 'lost_owner': 'carol',
        'found': '体育中心捡到一顶青绿色棒球帽，正面绣着 CHARLOTTE HORNETS 和一只黄蜂，帽顶有紫色扣子',
        'lost': '青绿色棒球帽丢了，正面有 CHARLOTTE HORNETS 刺绣和紫色黄蜂，帽顶一个紫色小扣',
        'location': '体育中心',
    },
    {
        'file': '背包.jpg',
        'found_owner': 'bob', 'lost_owner': 'david',
        'found': '教室捡到一个黑色拉杆双肩包，布面，底部有轮子，前面有拉链袋',
        'lost': '黑色拉杆双肩背包丢了，布的，能拉着走，底部两个轮子',
        'location': '教室',
    },
    {
        'file': '围巾.jpg',
        'found_owner': 'carol', 'lost_owner': 'erin',
        'found': '自习区捡到一条橙红色针织围巾，有细密纹理，两头是长流苏',
        'lost': '橙红色毛线围巾忘在自习区，两头有流苏，颜色偏砖红',
        'location': '自习区',
    },
    {
        'file': '手提包.jpg',
        'found_owner': 'david', 'lost_owner': 'frank',
        'found': '礼堂捡到一个米色翻盖单肩包，盖子上印着绿色植物图案，包身和肩带是黑色',
        'lost': '米色帆布单肩包丢了，盖子上有绿色植物印花，黑色背带',
        'location': '礼堂',
    },
    {
        'file': '行李箱.jpg',
        'found_owner': 'erin', 'lost_owner': 'alice',
        'found': '停车场捡到一个黑色布面行李箱，有拉链、顶部提手和滚轮',
        'lost': '黑色行李箱落在停车场，布面的，有拉链和拉杆，轮子有点响',
        'location': '停车场',
    },
    {
        'file': '雨伞.jpg',
        'found_owner': 'frank', 'lost_owner': 'bob',
        'found': '主入口捡到一把彩色条纹雨伞，伞面是红黄蓝绿相间的放射状条纹',
        'lost': '彩虹条纹雨伞丢了，打开是红黄蓝绿的放射状条纹',
        'location': '主入口',
    },
    {
        'file': '梅森杯.jpg',
        'found_owner': 'alice', 'lost_owner': 'carol',
        'found': '食堂桌上捡到一个蓝色玻璃水杯，梅森杯样式，灰色金属旋盖，杯身有 Ball 和 PERFECT MASON 浮雕，里面还泡着柠檬片和薄荷叶',
        'lost': '蓝色玻璃水杯忘在食堂了，灰色金属盖，杯身上有 Ball 字样，泡过柠檬和薄荷',
        'location': '食堂',
    },
    {
        'file': '绿色双肩包.jpg',
        'found_owner': 'bob', 'lost_owner': 'david',
        'found': '图书馆椅子上捡到一个绿色方形双肩包，正面缝着红白圆形标志，肩带很细，前面有个拉链小袋',
        'lost': '绿色方形帆布双肩包丢了，正面有红白圆标，肩带很细，前袋是拉链的',
        'location': '图书馆',
    },
    {
        'file': 'Volvic矿泉水.jpg',
        'found_owner': 'carol', 'lost_owner': 'erin',
        'found': '食堂桌上捡到一瓶 Volvic 矿泉水，透明塑料水瓶，深蓝色瓶盖，蓝色标签，瓶里还剩半瓶',
        'lost': 'Volvic 矿泉水忘在食堂了，透明塑料水瓶，深蓝色盖子，喝了一半',
        'location': '食堂',
    },
    {
        'file': 'Cisowianka矿泉水.jpg',
        'found_owner': 'david', 'lost_owner': 'frank',
        'found': '图书馆桌上捡到一瓶 CISOWIANKA 矿泉水，透明塑料水瓶，浅蓝色瓶盖，蓝色标签',
        'lost': 'CISOWIANKA 矿泉水丢在图书馆，透明塑料水瓶，浅蓝盖子，蓝色标签',
        'location': '图书馆',
    },
    {
        'file': '巧克力马克杯.jpg',
        'found_owner': 'erin', 'lost_owner': 'alice',
        'found': '自习区捡到一个白色陶瓷马克杯，杯身印着粉色和棕色爱心，里面写着 choc',
        'lost': '白色陶瓷马克杯忘在自习区，杯身上有粉棕爱心和 choc 字样',
        'location': '自习区',
    },
    {
        'file': '天际线马克杯.jpg',
        'found_owner': 'frank', 'lost_owner': 'bob',
        'found': '教室捡到一个白色陶瓷马克杯，杯身有一圈棕色城市天际线，杯口一圈细棕线',
        'lost': '白色陶瓷马克杯落在教室，杯身印着棕色城市天际线，杯口有细棕边',
        'location': '教室',
    },
    {
        'file': '红黑双肩包.jpg',
        'found_owner': 'alice', 'lost_owner': 'carol',
        'found': '体育中心捡到一个红黑拼色双肩包，布面，正面一大块红色，黑色肩带和拉链',
        'lost': '红黑拼色双肩包丢在体育中心，布的，正面是红色，黑色背带',
        'location': '体育中心',
    },
    {
        'file': '迷彩双肩包.jpg',
        'found_owner': 'bob', 'lost_owner': 'david',
        'found': '停车场捡到一个军绿色迷彩双肩包，长方形包身，帆布面料，正面有两个拉链袋',
        'lost': '军绿色迷彩双肩包落在停车场，长方形包身，帆布面料，前面有拉链袋',
        'location': '停车场',
    },
    {
        'file': '动漫展双肩包.jpg',
        'found_owner': 'carol', 'lost_owner': 'erin',
        'found': '主入口捡到一个橄榄绿双肩包，正面印着 ANIMEEXPO 和 AX 标志',
        'lost': '橄榄绿双肩包丢了，正面有 ANIMEEXPO 字母和 AX 标',
        'location': '主入口',
    },
    {
        'file': '黑色电脑双肩包.jpg',
        'found_owner': 'david', 'lost_owner': 'frank',
        'found': '礼堂捡到一个黑色电脑双肩包，正面有电脑隔层的拉链，黑色肩带',
        'lost': '黑色电脑双肩包忘在礼堂，前面有电脑隔层拉链，黑色背带',
        'location': '礼堂',
    },
]

# Lost reports with no matching photo: they keep the pool from being a perfect
# one-to-one puzzle and give the reranker something to reject.
DISTRACTORS = [
    {'owner': 'alice', 'location': '教室', 'lost': '蓝色保温杯，杯身有一圈白色贴纸'},
    {'owner': 'bob', 'location': '主入口', 'lost': '黑色折叠伞，伞柄是木头的'},
    {'owner': 'carol', 'location': '食堂', 'lost': '一串钥匙，挂着银色小熊挂件'},
    {'owner': 'david', 'location': '教室', 'lost': '红色硬皮笔记本，封面上有手写名字'},
    {'owner': 'erin', 'location': '图书馆', 'lost': '黑色眼镜盒，里面是金属框眼镜'},
    {'owner': 'frank', 'location': '实验室', 'lost': '白色 Type-C 充电线，接头处缠了胶带'},
]


def main() -> None:
    config = yaml.safe_load(Path('config_auth.yaml').read_text(encoding='utf-8'))
    accounts = config.get('credentials', {}).get('usernames', {})

    db = Database()
    try:
        if db.get_items():
            raise SystemExit('items.db 里已经有物品；先备份并删除 items.db 再运行。')

        missing = [name for name in ACCOUNTS if name not in accounts]
        if missing:
            raise SystemExit('config_auth.yaml 缺少账号：' + '、'.join(missing) +
                             '；先运行 python create_demo_users.py --force。')

        def owner(username: str) -> User:
            user = db.get_user(username)
            if user is None:
                user = User(username, '', accounts[username].get('email', ''))
                db.insert_user(user)
            return user

        users = {name: owner(name) for name in ACCOUNTS}
        store = FingerprintStore()
        meta = ReportMeta()
        hashes = ImageHashes()
        used: set[int] = set()
        stamp = int(time.time())

        def new_id() -> int:
            while True:
                value = secrets.randbits(62)
                if value and value not in used and not db.item_exists(value):
                    used.add(value)
                    return value

        for sample in SAMPLES:
            path = next((base / sample['file'] for base in SOURCE_DIRS
                         if (base / sample['file']).exists()), None)
            if path is None:
                raise SystemExit(f"缺少图片：{sample['file']}（找过 demo/photos 与 input）")

            with Image.open(path) as raw:
                picture = clean_image(raw)
            image = np.asarray(picture)

            found_fp = fingerprint_from_text(sample['found'], generate=False)
            lost_fp = fingerprint_from_text(sample['lost'], generate=False)

            found = Item(new_id(), image, encode_image(picture), sample['found'], stamp, sample['location'])
            db.insert_item(found)
            db.insert_found_item(found, users[sample['found_owner']])
            store.put(found.id, found_fp)
            meta.publish(found.id)
            hashes.put(found.id, picture)

            lost = Item(new_id(), None, encode_text(sample['lost']), sample['lost'], stamp, sample['location'])
            db.insert_item(lost)
            db.insert_lost_item(lost, users[sample['lost_owner']])
            store.put(lost.id, lost_fp)
            meta.publish(lost.id)

            print(f"found #{found.id} @{sample['found_owner']}  {sample['found']}")
            print(f"lost  #{lost.id} @{sample['lost_owner']}  {sample['lost']}")

        for extra in DISTRACTORS:
            lost = Item(new_id(), None, encode_text(extra['lost']), extra['lost'], stamp, extra['location'])
            db.insert_item(lost)
            db.insert_lost_item(lost, users[extra['owner']])
            store.put(lost.id, fingerprint_from_text(extra['lost'], generate=False))
            meta.publish(lost.id)
            print(f"lost  #{lost.id} @{extra['owner']}  {extra['lost']} （无对应拾获）")

        counts = {name: (len(db.get_user_found_items(name)), len(db.get_user_lost_items(name)))
                  for name in users}
        for name, (found_count, lost_count) in counts.items():
            print(f'{name}: {found_count} 件拾获 + {lost_count} 件失物')
        print(f'完成：{len(SAMPLES)} 件拾获 + {len(SAMPLES) + len(DISTRACTORS)} 件失物，{len(users)} 个账号。')
    finally:
        db.close()


if __name__ == '__main__':
    main()

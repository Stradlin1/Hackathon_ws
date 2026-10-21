"""Reset the local database and populate synthetic example records."""

import os

import yaml
from PIL import Image

from db_manager import Database, Item, User
from matching.report_meta import ReportMeta


with open('config_auth.yaml', encoding='utf-8') as file:
    auth = yaml.safe_load(file)
account_config = auth.get('credentials', {}).get('usernames', {})

# Reset the local database. Never check items.db into version control.
if os.path.exists('items.db'):
    os.remove('items.db')

db = Database()
users = []
for username, account in account_config.items():
    user = User(username, '', account.get('email', ''))
    db.insert_user(user)
    users.append(user)

# Generate sample graphics locally, avoiding photographs or image metadata.
samples = [
    ('钥匙串', '接待处', '#7d9bb5'),
    ('水瓶', '图书馆', '#89bfa8'),
    ('耳机', '自习区', '#d4ae7c'),
    ('小笔记本', '主入口', '#b8a0cc'),
]
items = []
meta = ReportMeta()
for i, (description, location, color) in enumerate(samples):
    image = Image.new('RGB', (128, 128), color=color)
    item = Item(i + 10, image, None, description, 0, location)
    db.insert_item(item)
    meta.publish(item.id)
    items.append(item)

if users:
    user = users[0]
    db.insert_lost_item(items[0], user)
    db.insert_lost_item(items[1], user)
    db.insert_found_item(items[2], user)
    db.insert_found_item(items[3], user)
    db.insert_match(items[2].id, items[0].id)

db.close()
print('本地数据库已重建，并写入合成样例物品。')

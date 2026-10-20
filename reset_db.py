"""Reset the local database and populate synthetic example records."""

import os

import yaml
from PIL import Image

from db_manager import Database, Item, User


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
    ('Set of keys', 'Reception', '#7d9bb5'),
    ('Water bottle', 'Library', '#89bfa8'),
    ('Headphones', 'Study Area', '#d4ae7c'),
    ('Small notebook', 'Main Entrance', '#b8a0cc'),
]
items = []
for i, (description, location, color) in enumerate(samples):
    image = Image.new('RGB', (128, 128), color=color)
    item = Item(i + 10, image, None, description, 0, location)
    db.insert_item(item)
    items.append(item)

if users:
    user = users[0]
    db.insert_lost_item(items[0], user)
    db.insert_lost_item(items[1], user)
    db.insert_found_item(items[2], user)
    db.insert_found_item(items[3], user)
    db.insert_match(items[2].id, items[0].id)

db.close()
print('Local database initialized with synthetic sample items.')

from db_manager import *
import os
import yaml
from PIL import Image

# read users from config_auth.yaml
with open('config_auth.yaml') as f:
    auth = yaml.load(f, Loader=yaml.FullLoader)
users = auth['credentials']['usernames'].keys()
mails = [auth['credentials']['usernames'][user]['email'] for user in users]

# recreate database
if os.path.exists('items.db'):
    os.remove('items.db')
db = Database()

# populate users
users_tmp = []
for user, mail in zip(users, mails):
    u = User(user, None, mail)
    db.insert_user(u)
    users_tmp.append(u)
print('added users')

# populate items
description = 'lore ipsum dolor sit amet, consectetur adipiscing elit. lore ipsum dolor sit amet, consectetur adipiscing elit. lore ipsum dolor sit amet, consectetur adipiscing elit. lore ipsum dolor sit amet, consectetur adipiscing elit. lore ipsum dolor sit amet, consectetur adipiscing elit. lore ipsum dolor sit amet, consectetur adipiscing elit. lore ipsum dolor sit amet, consectetur adipiscing elit. '
imgs = [
    Image.open('static/item1.jpg'),
    Image.open('static/item2.jpg'),
    Image.open('static/item3.jpg'),
    Image.open('static/item4.jpg'),
]
items = [
    Item(10, imgs[0], None, description, 0, 'b'),
    Item(11, imgs[1], None, description, 1, 'd'),
    Item(12, imgs[2], None, description, 2, 'f'),
    Item(13, imgs[3], None, description, 3, 'h'),
]
for item in items:
    db.insert_item(item)
print('added items')

# Add demonstration items only when a configured account exists.
if users_tmp:
    demo_user = users_tmp[0]
    db.insert_lost_item(items[0], demo_user)
    db.insert_lost_item(items[1], demo_user)
    db.insert_found_item(items[2], demo_user)
    db.insert_found_item(items[3], demo_user)
    print('added demonstration associations')
    db.insert_match(12, 10)
    print('added demonstration match')
else:
    print('no configured users; skipped demonstration associations')

# close database
db.close()
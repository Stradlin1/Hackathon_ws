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
jsmith_index = 0
for user, mail in zip(users, mails):
    if user == 'jsmith':
        jsmith_index = len(users_tmp)
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

# populate lost found
db.insert_lost_item(items[0], users_tmp[jsmith_index])
db.insert_lost_item(items[1], users_tmp[jsmith_index])
db.insert_found_item(items[2], users_tmp[jsmith_index])
db.insert_found_item(items[3], users_tmp[jsmith_index])
print('added lost found')

# populate matches
db.insert_match(12, 10)
print('added matches')

# close database
db.close()
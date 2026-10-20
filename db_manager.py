# create item class that stores an image, description, time and location
import numpy as np
import sqlite3
import pickle

class Item:
    def __init__(self, id:int, image:np.ndarray, emb:np.ndarray, description:str, time:int, location:str):
        self.id = id
        self.image = image
        self.emb = emb
        self.description = description
        self.time = time
        self.location = location
    
    def __str__(self):
        return f'{self.description} found at {self.location} at {self.time}'
    
    def __repr__(self):
        return self.__str__()

class User:
    def __init__(self, username:str, password:str, email:str):
        self.username = username
        self.password = password
        self.email = email
    
    def __str__(self):
        return f'{self.username} with email {self.email}'
    
    def __repr__(self):
        return self.__str__()

class Database:
    def __init__(self):
        self.con = sqlite3.connect('items.db')
        self.cur = self.con.cursor()
        self.create_table()
    
    def create_table(self):
        # create table for matches where one item is in found_items and the other is in lost_items
        self.cur.execute('CREATE TABLE IF NOT EXISTS matches (item1_id INTEGER, item2_id INTEGER, PRIMARY KEY (item1_id, item2_id))')
        self.cur.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, image BLOB, emb BLOB, description TEXT, time INTEGER, location TEXT)')
        self.cur.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, email TEXT)')
        self.cur.execute('CREATE TABLE IF NOT EXISTS lost_items (item_id INTEGER, user_id TEXT, PRIMARY KEY (item_id, user_id))')
        self.cur.execute('CREATE TABLE IF NOT EXISTS found_items (item_id INTEGER, user_id TEXT, PRIMARY KEY (item_id, user_id))')
    

    # check if exists
    def item_exists(self, id:int) -> bool:
        self.cur.execute('SELECT * FROM items WHERE id = ?', (id,))
        return self.cur.fetchone() is not None
    
    def username_exists(self, username:str) -> bool:
        self.cur.execute('SELECT * FROM users WHERE username = ?', (username,))
        return self.cur.fetchone() is not None
    
    def lost_item_exists(self, item_id:int, user_id:str) -> bool:
        self.cur.execute('SELECT * FROM lost_items WHERE item_id = ? AND user_id = ?', (item_id, user_id))
        return self.cur.fetchone() is not None
    
    def found_item_exists(self, item_id:int, user_id:str) -> bool:
        self.cur.execute('SELECT * FROM found_items WHERE item_id = ? AND user_id = ?', (item_id, user_id))
        return self.cur.fetchone() is not None
    
    def match_exists(self, item1_id:int, item2_id:int) -> bool:
        self.cur.execute('SELECT * FROM matches WHERE item1_id = ? AND item2_id = ?', (item1_id, item2_id))
        return self.cur.fetchone() is not None
    
    
    # insert single
    def insert_item(self, item:Item):
        if self.item_exists(item.id):
            return
        img = pickle.dumps(item.image) if item.image is not None else None
        emb = pickle.dumps(item.emb) if item.emb is not None else None
        self.cur.execute('INSERT INTO items (id, image, emb, description, time, location) VALUES (?, ?, ?, ?, ?, ?)', 
                         (item.id, img, emb, item.description, item.time, item.location))
        self.con.commit()

    def insert_user(self, user:User):
        if self.username_exists(user.username):
            return
        self.cur.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)', (user.username, user.password, user.email))
        self.con.commit()
    
    def insert_lost_item(self, item:Item, user:User):
        if self.lost_item_exists(item.id, user.username):
            return
        self.cur.execute('INSERT INTO lost_items (item_id, user_id) VALUES (?, ?)', (item.id, user.username))
        self.con.commit()
    
    def insert_found_item(self, item:Item, user:User):
        if self.found_item_exists(item.id, user.username):
            return
        self.cur.execute('INSERT INTO found_items (item_id, user_id) VALUES (?, ?)', (item.id, user.username))
        self.con.commit()
    
    def insert_match(self, found_item_id:int, lost_item_id:int):
        if self.match_exists(found_item_id, lost_item_id):
            return
        self.cur.execute('INSERT INTO matches (item1_id, item2_id) VALUES (?, ?)', (found_item_id, lost_item_id))
        self.con.commit()

    # remove single item from the database
    def remove_item(self, id: int) -> None:
        self.cur.execute('DELETE FROM items WHERE id = ?', (id,))
        self.con.commit()

    # remove single user from the database
    def remove_user(self, username: str) -> None:
        self.cur.execute('DELETE FROM users WHERE username = ?', (username,))
        self.con.commit()

    # remove lost item association from the database
    def remove_lost_item(self, item_id: int) -> None:
        self.cur.execute('DELETE FROM lost_items WHERE item_id = ?', (item_id,))
        self.con.commit()

    # remove found item association from the database
    def remove_found_item(self, item_id: int) -> None:
        self.cur.execute('DELETE FROM found_items WHERE item_id = ?', (item_id,))
        self.con.commit()

    # remove match from the database
    def remove_match(self, found_item_id: int, lost_item_id: int) -> None:
        self.cur.execute('DELETE FROM matches WHERE item1_id = ? AND item2_id = ?', (found_item_id, lost_item_id))
        self.con.commit()


    def get_item(self, id: int) -> Item:
        self.cur.execute('SELECT * FROM items WHERE id = ?', (id,))
        item = self.cur.fetchone()  # Fetches the first matching row
        return Item(
            item[0],
            pickle.loads(item[1]) if item[1] else None,
            pickle.loads(item[2]) if item[2] else None,
            item[3],
            item[4],
            item[5]
        )

    # get collections
    def get_items(self) -> list:
        self.cur.execute('SELECT * FROM items')
        items = self.cur.fetchall()
        return [Item(item[0], pickle.loads(item[1]) if item[1] else None, pickle.loads(item[2]) if item[2] else None, item[3], item[4], item[5]) for item in items]
    
    def get_users(self) -> list:
        self.cur.execute('SELECT * FROM users')
        users = self.cur.fetchall()
        return [User(*user) for user in users]
    
    def get_lost_items(self) -> list:
        self.cur.execute('SELECT li.item_id, image, emb, description, time, location FROM lost_items li JOIN items it ON (li.item_id = it.id)')
        lost_items = self.cur.fetchall()
        return [Item(item[0], pickle.loads(item[1]) if item[1] else None, pickle.loads(item[2]) if item[2] else None, item[3], item[4], item[5]) for item in lost_items]
    
    def get_found_items(self) -> list:
        self.cur.execute('SELECT fi.item_id, image, emb, description, time, location FROM found_items fi JOIN items it ON (fi.item_id = it.id)')
        found_items = self.cur.fetchall()        
        return [Item(item[0], pickle.loads(item[1]) if item[1] else None, pickle.loads(item[2]) if item[2] else None, item[3], item[4], item[5]) for item in found_items]

    def get_matches(self) -> list:
        self.cur.execute('SELECT * FROM matches')
        matches = self.cur.fetchall()
        return [(match[0], match[1]) for match in matches]

    # retrieve lost items that do not have a match
    def get_unmatched_lost_items(self) -> list:
        self.cur.execute('''
            SELECT li.item_id, image, emb, description, time, location
            FROM lost_items li
            JOIN items it ON li.item_id = it.id
            LEFT JOIN matches m ON li.item_id = m.item2_id
            WHERE m.item2_id IS NULL
        ''')
        lost_items = self.cur.fetchall()
        return [Item(item[0], pickle.loads(item[1]) if item[1] else None, 
                    pickle.loads(item[2]) if item[2] else None, item[3], item[4], item[5]) for item in lost_items]

    # retrieve found items that do not have a match
    def get_unmatched_found_items(self) -> list:
        self.cur.execute('''
            SELECT fi.item_id, image, emb, description, time, location
            FROM found_items fi
            JOIN items it ON fi.item_id = it.id
            LEFT JOIN matches m ON fi.item_id = m.item1_id
            WHERE m.item1_id IS NULL
        ''')
        found_items = self.cur.fetchall()
        return [Item(item[0], pickle.loads(item[1]) if item[1] else None, 
                    pickle.loads(item[2]) if item[2] else None, item[3], item[4], item[5]) for item in found_items]


    # get single
    def get_user(self, username:str) -> User:
        self.cur.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = self.cur.fetchone()
        if user:
            return User(*user)
        return None
    
    # get user items
    def get_user_lost_items(self, username:str) -> list[Item]:
        self.cur.execute('SELECT li.item_id, image, emb, description, time, location FROM lost_items li JOIN items it ON (li.item_id = it.id) WHERE user_id = ?', (username,))
        lost_items = self.cur.fetchall()
        return [Item(item[0], pickle.loads(item[1]) if item[1] else None, pickle.loads(item[2]) if item[2] else None, item[3], item[4], item[5]) for item in lost_items]

    def get_user_found_items(self, username:str) -> list[Item]:
        self.cur.execute('SELECT fi.item_id, image, emb, description, time, location FROM found_items fi JOIN items it ON (fi.item_id = it.id) WHERE user_id = ?', (username,))
        found_items = self.cur.fetchall()
        return [Item(item[0], pickle.loads(item[1]) if item[1] else None, pickle.loads(item[2]) if item[2] else None, item[3], item[4], item[5]) for item in found_items]
    
    # get item matches
    def get_found_item_matches(self, item_id:int) -> list[int]:
        self.cur.execute('SELECT item2_id FROM matches WHERE item1_id = ?', (item_id,))
        matches = self.cur.fetchall()
        return [match[0] for match in matches]
    
    def get_lost_item_matches(self, item_id:int) -> list[int]:
        self.cur.execute('SELECT item1_id FROM matches WHERE item2_id = ?', (item_id,))
        matches = self.cur.fetchall()
        return [match[0] for match in matches]
    

    # close connection
    def close(self):
        self.con.close()

    
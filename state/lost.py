import random
import streamlit as st
from PIL import Image
# import folium
# from streamlit_folium import st_folium
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
from datetime import datetime
from db_manager import *
from sentence_transformers import SentenceTransformer, util
import torch


import json
from db_manager import *

def change_state(state):
    if 'state' in st.session_state:
        st.session_state.state = state

def find_match(img, description, time, location):

    # Insert lost item into database
    id = random.getrandbits(32)
    item = Item(id, None, None, description, time, location)
    db = Database()
    db.insert_item(item)
    u = db.get_user(st.session_state.username)
    db.insert_lost_item(item, u)
    
    # get description embedding
    match_found = False
    model = SentenceTransformer('clip-ViT-B-32-multilingual-v1')
    desc_emb = model.encode([description])

    # retrieve all items embedding
    found_items = [item for item in db.get_unmatched_found_items() if item.image is not None and item.emb is not None]
    filter(lambda x: x.time == time, found_items)
    
    if len(found_items) > 0:
        imgs_emb = [torch.from_numpy(item.emb) for item in found_items]

        # get top 10 items
        hits = util.semantic_search(torch.from_numpy(desc_emb), imgs_emb, top_k=10)[0]
        
        st.session_state['hit_img'] = found_items[hits[0]['corpus_id']].image
        st.session_state['hit_id'] = found_items[hits[0]['corpus_id']].id
        st.session_state['it_id'] = item.id
        if hits[0]['score'] > 0.25:
            match_found = True
            

    # change state
    db.close()
    if match_found:
        change_state('this_your_item')
    else:
        change_state('profile')

def lost(authenticator):

    # sidebar stuff
    st.sidebar.markdown(st.session_state.username)
    st.sidebar.button(
        label = 'Your Profile',
        on_click=change_state, 
        args=['profile'],
    )
    authenticator.logout(location='sidebar', callback=lambda _: change_state("login"))
    st.sidebar.write('Other Options')
    st.sidebar.button(
        label = 'Report an Item',
        on_click=change_state, 
        args=['lost_or_found'],
    )

    # title
    st.title("Describe the item you lost")
    
    # get description of lost item
    st.subheader("What")
    description = st.text_area(
        label="yea",
        value="Provide a description",
        label_visibility='collapsed'
    )

    # get last known location of lost item
    with open('rooms.json', 'r') as file:
        locs = json.load(file)
    st.subheader('Where')
    location = st.selectbox(
        label = 'yea',
        options = locs,
        label_visibility='collapsed'
    )

    # get date it was lost
    st.subheader("When")
    date = st.date_input(
        label="yea",
        value='today',
        max_value=datetime.now().date(),
        min_value=datetime.now().date() - timedelta(days=30),
        label_visibility='collapsed'
    )
    time = int(datetime.combine(date, datetime.min.time()).timestamp())
            
    # Find match
    st.button('Find Match', on_click=find_match, args=[None, description, time, location])
    
    
    
    
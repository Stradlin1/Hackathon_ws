import streamlit as st
from db_manager import *
import pickle
import random
from sentence_transformers import SentenceTransformer, util
from PIL import Image
import json
import datetime
from datetime import datetime, timedelta
import random
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration


def change_state(state):        
    if 'state' in st.session_state:
        st.session_state.state = state

def find_match(img, description, time, location):
    
        # evaluate embedding
        img_model = SentenceTransformer('clip-ViT-B-32')
        img_emb = img_model.encode(img)

        # description embedder
        desc_model = SentenceTransformer('clip-ViT-B-32-multilingual-v1')


        img_emb = img_emb
        # Insert found item into database
        id = random.getrandbits(32)
        item = Item(id, img, img_emb, description, time, location)
        db = Database()
        db.insert_item(item)
        u = db.get_user(st.session_state.username)
        db.insert_found_item(item, u)

        # TODO: Find match
        match_found = False

        # retrieve all items embedding not matched
        lost_items = db.get_unmatched_lost_items()
        filter(lambda x: x.time == time, lost_items)
        
        if len(lost_items) > 0:
            descs_emb = [torch.from_numpy(desc_model.encode(item.description)) for item in lost_items]

            # get top 10 items
            hits = util.semantic_search([torch.from_numpy(img_emb)], descs_emb, top_k=10)[0]
            
            st.session_state['hit_desc'] = lost_items[hits[0]['corpus_id']].description
            st.session_state['hit_id'] = lost_items[hits[0]['corpus_id']].id
            st.session_state['it_id'] = item.id

            if hits[0]['score'] > 0.25:
                match_found = True


        db.close()

        if match_found:
            change_state('this_description_matches')
        else:
            change_state('profile')

def found(authenticator):

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
    st.title('Describe the item you found')

    # get image of found item
    st.subheader("What")
    img = None
    file = st.file_uploader("yea", type=["png", "jpg", "jpeg", "HEIC"], label_visibility='collapsed')

    description = None
    
    if file is not None:
        img = Image.open(file)
        st.image(img)
        
        processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

        raw_image = img.convert('RGB')

        # conditional image captioning
        text = "The image contains "
        inputs = processor(raw_image, text, return_tensors="pt")

        out = model.generate(**inputs)
        processor.decode(out[0], skip_special_tokens=True)
        description = st.text_area(
            label="yeah",
            value=processor.decode(out[0], skip_special_tokens=True),
            label_visibility='collapsed'
        )

    # get location of found item
    with open('rooms.json', 'r') as file:
        locs = json.load(file)
    st.subheader('Where')
    location = st.selectbox(
        label = 'yea',
        options = locs,
        label_visibility='collapsed'
    )

    # get date it was found
    st.subheader("When")
    date = st.date_input(
        label="yea",
        value='today',
        max_value=datetime.now().date(),
        min_value=datetime.now().date() - timedelta(days=30),
        label_visibility='collapsed'
    )
    time = int(datetime.combine(date, datetime.min.time()).timestamp())
    
    st.button('Submit', on_click=find_match, args=[img, description, time, location])
    
    # # go back to profile page
    # st.button('Profile', on_click=change_state, args=['profile'])

    # # if match go to someone_lost page
    # st.button('found match', on_click=change_state, args=['someone_lost'])

    # # if not match go to profile page
    # st.button('not found match', on_click=change_state, args=['profile'])
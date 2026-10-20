"""Found-item report: image caption, generative fingerprint, CLIP retrieval."""

from __future__ import annotations

import io
import json
import secrets
from datetime import datetime, timedelta

import streamlit as st
from PIL import Image, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 20_000_000

from db_manager import Database, Item
from matching.fingerprint import fingerprint_from_text
from matching.models import caption_image, clean_image, encode_image
from matching.storage import FingerprintStore
from matching.workflow import build_session


@st.cache_data(show_spinner=False)
def _cached_caption(image_bytes: bytes) -> str:
    picture = clean_image(Image.open(io.BytesIO(image_bytes)))
    return caption_image(picture)


def found(authenticator):
    st.sidebar.button('Back to menu', on_click=lambda: st.session_state.update(state='lost_or_found'))
    authenticator.logout(location='sidebar')
    st.title('Report a found item')
    uploaded = st.file_uploader('Upload an item photograph', type=['png', 'jpg', 'jpeg'])
    if uploaded is None:
        st.info('Upload an item photo to start an AI-assisted report.')
        return
    image_bytes = uploaded.getvalue()
    if len(image_bytes) > 8 * 1024 * 1024:
        st.error('Please choose an image under 8 MB.')
        return
    try:
        image = clean_image(Image.open(io.BytesIO(image_bytes)))
    except (OSError, UnidentifiedImageError, ValueError, Image.DecompressionBombError):
        st.error('This image format could not be opened.')
        return
    st.image(image, caption='Item photo', width=350)
    try:
        with st.spinner('Generating an image caption...'):
            caption = _cached_caption(image_bytes)
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        caption = ''
        st.warning(f'Automatic image caption is unavailable ({exc}). Please describe the item manually.')

    with st.form('found_report'):
        description = st.text_area('Description (you may correct the generated caption)',
                                   value=caption, max_chars=1000)
        with open('rooms.json', encoding='utf-8') as file:
            locations = json.load(file)
        location = st.selectbox('Where was it found?', locations)
        date = st.date_input('Date found', value='today', max_value=datetime.now().date(),
                             min_value=datetime.now().date() - timedelta(days=30))
        submitted = st.form_submit_button('Submit and find possible matches')
    if not submitted:
        return
    if not description.strip():
        st.error('Please provide a short description of the item.')
        return
    with st.spinner('Creating fingerprint and searching for candidate items...'):
        try:
            vector = encode_image(image)
            fingerprint = fingerprint_from_text(description, caption=caption)
            stamp = int(datetime.combine(date, datetime.min.time()).timestamp())
            item = Item(secrets.randbits(62), image, vector, description.strip(), stamp, location)
            db = Database()
            try:
                db.insert_item(item)
                owner = db.get_user(st.session_state.username)
                if owner is None:
                    raise ValueError('Please log in again to create a report.')
                db.insert_found_item(item, owner)
                store = FingerprintStore()
                store.put(item.id, fingerprint)
                session = build_session(direction='found', item_id=item.id,
                                        query_embedding=vector, fingerprint=fingerprint,
                                        username=owner.username, db=db, store=store)
            finally:
                db.close()
        except (OSError, ValueError, RuntimeError, ImportError) as error:
            st.error(f'The report could not be processed: {error}')
            return
    st.session_state.match_session = session
    st.session_state.state = 'interactive_match'
    st.rerun()

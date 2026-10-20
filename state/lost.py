"""Lost-item report: generative fingerprint and cross-modal retrieval."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta

import streamlit as st

from db_manager import Database, Item
from matching.fingerprint import fingerprint_from_text
from matching.models import encode_text
from matching.storage import FingerprintStore
from matching.workflow import build_session


def lost(authenticator):
    st.sidebar.button('Back to menu', on_click=lambda: st.session_state.update(state='lost_or_found'))
    authenticator.logout(location='sidebar')
    st.title('Report a lost item')

    with st.form('lost_report'):
        description = st.text_area('Describe the item, including any distinctive markings', max_chars=1000)
        with open('rooms.json', encoding='utf-8') as file:
            locations = json.load(file)
        location = st.selectbox('Last known location', locations)
        date = st.date_input('Date lost', value='today', max_value=datetime.now().date(),
                             min_value=datetime.now().date() - timedelta(days=30))
        submitted = st.form_submit_button('Find possible matches')

    if not submitted:
        return
    if not description.strip():
        st.error('Please describe the lost item before searching.')
        return
    with st.spinner('Creating fingerprint and searching for candidate items...'):
        try:
            vector = encode_text(description)
            fingerprint = fingerprint_from_text(description)
            stamp = int(datetime.combine(date, datetime.min.time()).timestamp())
            item = Item(secrets.randbits(62), None, vector, description.strip(), stamp, location)
            db = Database()
            try:
                db.insert_item(item)
                owner = db.get_user(st.session_state.username)
                if owner is None:
                    raise ValueError('Please log in again to create a report.')
                db.insert_lost_item(item, owner)
                store = FingerprintStore()
                store.put(item.id, fingerprint)
                session = build_session(direction='lost', item_id=item.id,
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

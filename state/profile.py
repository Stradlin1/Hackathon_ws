"""Item history and two-party approval of proposed matches."""

from __future__ import annotations

import streamlit as st

from db_manager import Database
from matching.requests import MatchRequests


def profile(authenticator):
    authenticator.logout(location='sidebar')
    username = st.session_state.username
    st.title('My items and requests')
    db = Database()
    try:
        lost_items = db.get_user_lost_items(username)
        found_items = db.get_user_found_items(username)
        st.subheader('Lost items')
        for item in lost_items:
            st.write(f'#{item.id}: {item.description}')
            st.caption(f'Location: {item.location} | Date: {item.time}')
        st.subheader('Found items')
        for item in found_items:
            st.write(f'#{item.id}: {item.description}')
            if item.image is not None:
                st.image(item.image, width=250)
    finally:
        db.close()

    requests = MatchRequests()
    st.subheader('Requests waiting for your confirmation')
    incoming = requests.incoming(username)
    if not incoming:
        st.write('No pending requests.')
    for req in incoming:
        found, lost = req['found_item_id'], req['lost_item_id']
        st.write(f'Found: {req["found_desc"]} | Lost: {req["lost_desc"]}')
        a, b = st.columns(2)
        with a:
            if st.button('Accept match', key=f'accept-{found}-{lost}'):
                if requests.respond(username, found, lost, True):
                    st.rerun()
        with b:
            if st.button('Reject match', key=f'reject-{found}-{lost}'):
                if requests.respond(username, found, lost, False):
                    st.rerun()

    st.subheader('Requests you sent')
    for req in requests.outgoing(username):
        st.write(f'Found #{req["found_item_id"]} / Lost #{req["lost_item_id"]}: {req["status"]}')

    st.subheader('Confirmed matches')
    accepted = requests.accepted(username)
    if not accepted:
        st.write('No mutually confirmed matches.')
    for req in accepted:
        st.write(f'Found #{req["found_item_id"]} / Lost #{req["lost_item_id"]}')
        st.write(f'Contact: {req["contact_username"]} ({req["contact_email"]})')

    if st.button('Report another item'):
        st.session_state.state = 'lost_or_found'
        st.rerun()

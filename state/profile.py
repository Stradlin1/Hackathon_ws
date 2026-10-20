from html import escape

import streamlit as st
from db_manager import Database


def change_state(state):
    if 'state' in st.session_state:
        st.session_state.state = state


def profile(authenticator):
    st.sidebar.markdown(st.session_state.username)
    authenticator.logout(location='sidebar', callback=lambda _: change_state('login'))
    st.sidebar.write('Other Options')
    st.sidebar.button('Report an Item', on_click=change_state, args=['lost_or_found'])

    st.title(st.session_state.username)

    db = Database()
    lost_items = db.get_user_lost_items(st.session_state.username)
    lost_item_matches = [db.get_lost_item_matches(item.id) for item in lost_items]
    found_items = db.get_user_found_items(st.session_state.username)
    found_item_matches = [db.get_found_item_matches(item.id) for item in found_items]
    db.close()

    st.subheader('Items you lost')
    for item, matches in zip(lost_items, lost_item_matches):
        status = 'found' if matches else 'not found yet'
        st.markdown(
            '<div style="border: 1px solid black; padding: 10px; margin: 10px; border-radius: 10px;">'
            f'<p><strong>Description:</strong> {escape(item.description or "")}</p>'
            f'<p><strong>Status:</strong> {status}</p>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.subheader('Items you found')
    for item, matches in zip(found_items, found_item_matches):
        status = 'claimed' if matches else 'not claimed yet'
        if item.image is not None:
            st.image(item.image, use_column_width=True)
        else:
            st.write('No image available')
        st.markdown(
            '<div style="border: 1px solid black; padding: 10px; margin: 10px; border-radius: 10px;">'
            f'<p><strong>Description:</strong> {escape(item.description or "")}</p>'
            f'<p><strong>Status:</strong> {status}</p>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.subheader('Report a lost or found item')
    st.button('Report', on_click=change_state, args=['lost_or_found'])

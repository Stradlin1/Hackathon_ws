"""Main menu for creating an item report."""

import streamlit as st


def lost_or_found(authenticator):
    authenticator.logout(location='sidebar')
    st.title('404NotFound')
    st.write('Report a missing or found item and use AI-assisted matching to find possible owners.')
    left, right = st.columns(2)
    with left:
        if st.button('I lost something', use_container_width=True):
            st.session_state.state = 'lost'
            st.rerun()
    with right:
        if st.button('I found something', use_container_width=True):
            st.session_state.state = 'found'
            st.rerun()
    if st.button('My items and requests'):
        st.session_state.state = 'profile'
        st.rerun()

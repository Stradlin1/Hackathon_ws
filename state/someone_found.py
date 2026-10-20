import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from db_manager import *


def change_state(state):
    if 'state' in st.session_state:
        st.session_state.state = state

def someone_found(authenticator):
    db = Database()

     # go back to profile page
    st.sidebar.markdown(st.session_state.username)
    st.sidebar.button(
        label = 'Your Profile',
        on_click=change_state, 
        args=['profile'],
    )
    
    authenticator.logout(location='sidebar', callback=lambda _: change_state("login"))

    st.title('Someone Found Your Item')
        
    # First column with label for the image
    with stylable_container(
        key="image_container",
        css_styles=""""""
            ):
        st.image(db.get_item(st.session_state['hit_id']).image)
        st.write(db.get_item(st.session_state['it_id']).description)


    st.subheader("Contact the person who found your item")
    owner = db.get_found_item_owner(st.session_state['hit_id'])
    if owner is not None:
        st.write(owner.username)
        st.write(owner.email)
    else:
        st.warning('Contact information is unavailable.')
    db.close()

    # go back to profile page
    st.button('Profile', on_click=change_state, args=['profile'])

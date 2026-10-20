import streamlit as st

from streamlit_extras.stylable_container import stylable_container

from db_manager import *

def change_state(state):
    if 'state' in st.session_state:
        st.session_state.state = state

def someone_lost(authenticator):
    db = Database()

    # go back to profile page
    st.sidebar.markdown(st.session_state.username)
    st.sidebar.button(
        label = 'Your Profile',
        on_click=change_state, 
        args=['profile'],
    )
    
    authenticator.logout(location='sidebar', callback=lambda _: change_state("login"))

    st.title('Someone Lost the Item you Found') 

    # First column with label for the image
    with stylable_container(
        key="image_container",
        css_styles=""""""
            ):
        st.image(db.get_item(st.session_state['it_id']).image)
        st.write(db.get_item(st.session_state['hit_id']).description)
    
    # get user who lost the item with it_id
    st.subheader("Contact the user who lost the item")
    st.write(db.get_users()[0].username)
    st.write(db.get_users()[0].email)
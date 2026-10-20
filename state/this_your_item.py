import streamlit as st
from db_manager import *

from streamlit_extras.stylable_container import stylable_container

from db_manager import *


def change_state(state):
    # add match to db
    if 'someone_found' in state:
        db = Database()
        st.session_state['hit_id']
        db.insert_match(st.session_state['hit_id'], st.session_state['it_id'])
        db.close()


    if 'state' in st.session_state:
        st.session_state.state = state

def this_your_item(authenticator):
    
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
    
    st.title('Is This Your Item ?')
    
    # First column with label for the image
    db = Database()
    with stylable_container(
            key="image_container",
            css_styles=""""""
                ):
            st.image(db.get_item(st.session_state['hit_id']).image)
            st.write(db.get_item(st.session_state['it_id']).description)
    db.close()

    # Second column with label for buttons
    with stylable_container(key="yes_button",
        css_styles="""
            button {
                background-color: #34A853;  /* Set background color to white */
                color: white;  /* Use black text for contrast */
                border-radius: 10px;
                padding: 30px 60px;  /* Increase padding for a larger button */
                font-size: 224px;  /* Set font size */
                font-family: 'Inter', san-serif;
                text-align: center;
                display: inline-block;  /* Allows width adjustment */
                width: 100%;  /* Full width of the column */
                height: 80px;  /* Set fixed height for the button */
                border: 3px solid lightgray;  /* Optional: add border to match the design */
            }"""):
        st.button('Yes', on_click=change_state, args=['someone_found'])
    with stylable_container(key="no_button",
        css_styles="""
            button {
                background-color: #EA4335;  /* Set background color to white */
                color: white;  /* Use black text for contrast */
                border-radius: 10px;
                padding: 30px 60px;  /* Increase padding for a larger button */
                font-size: 224px;  /* Set font size */
                font-family: 'Inter', san-serif;
                text-align: center;
                display: inline-block;  /* Allows width adjustment */
                width: 100%;  /* Full width of the column */
                height: 80px;  /* Set fixed height for the button */
                border: 3px solid lightgray;  /* Optional: add border to match the design */
            }
                            """):
        st.button("No", on_click=change_state, args=['profile'])